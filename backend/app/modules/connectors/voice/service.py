"""
Voice Services - VoiceService

Orchestrates STT and TTS providers with caching, format detection,
and statistics tracking. Singleton via get_voice_service().

Pipeline:
    Audio -> STT Provider -> text -> [BRAIN] -> text -> TTS Provider -> Audio
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.modules.connectors.voice.schemas import (
    AudioFormat,
    STTConfig,
    STTProvider,
    SynthesisResult,
    TTSConfig,
    TTSProvider,
    TranscriptionResult,
    VoicePipelineConfig,
    VoicePipelineStats,
)
from app.modules.connectors.voice.stt_providers import (
    BaseSTTProvider,
    create_stt_provider,
)
from app.modules.connectors.voice.tts_providers import (
    BaseTTSProvider,
    create_tts_provider,
)


class TTSCache:
    """Simple in-memory LRU cache for TTS results."""

    def __init__(self, max_size: int = 100, ttl_s: float = 3600.0) -> None:
        self._cache: Dict[str, Tuple[SynthesisResult, float]] = {}
        self.max_size = max_size
        self.ttl_s = ttl_s
        self.hits = 0
        self.misses = 0

    def _make_key(self, text: str, voice_id: str, fmt: AudioFormat) -> str:
        raw = f"{text}:{voice_id}:{fmt.value}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, text: str, voice_id: str, fmt: AudioFormat) -> Optional[SynthesisResult]:
        key = self._make_key(text, voice_id, fmt)
        entry = self._cache.get(key)
        if entry is None:
            self.misses += 1
            return None
        result, created_at = entry
        if time.time() - created_at > self.ttl_s:
            del self._cache[key]
            self.misses += 1
            return None
        self.hits += 1
        return result

    def put(self, text: str, voice_id: str, fmt: AudioFormat, result: SynthesisResult) -> None:
        key = self._make_key(text, voice_id, fmt)
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_size and key not in self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = (result, time.time())

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)


class VoiceService:
    """
    Central service for voice processing (STT + TTS).

    Manages provider instances, caching, and statistics.
    """

    def __init__(self, config: Optional[VoicePipelineConfig] = None) -> None:
        self.config = config or VoicePipelineConfig()
        self._stt_provider: Optional[BaseSTTProvider] = None
        self._tts_provider: Optional[BaseTTSProvider] = None
        self._cache = TTSCache(
            ttl_s=self.config.cache_ttl_s,
        )
        self._stats = VoicePipelineStats()
        self._initialized = False
        logger.info("VoiceService initialized")

    # ========================================================================
    # Initialization
    # ========================================================================

    def initialize(self) -> None:
        """Initialize STT and TTS providers from config."""
        if self.config.enable_stt:
            self._stt_provider = create_stt_provider(self.config.stt)
            logger.info(f"STT provider: {self.config.stt.provider.value}")

        if self.config.enable_tts:
            self._tts_provider = create_tts_provider(self.config.tts)
            logger.info(f"TTS provider: {self.config.tts.provider.value}")

        self._initialized = True

    def set_stt_provider(self, provider: BaseSTTProvider) -> None:
        """Set STT provider directly (useful for testing)."""
        self._stt_provider = provider
        self._initialized = True

    def set_tts_provider(self, provider: BaseTTSProvider) -> None:
        """Set TTS provider directly (useful for testing)."""
        self._tts_provider = provider
        self._initialized = True

    # ========================================================================
    # STT
    # ========================================================================

    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: AudioFormat = AudioFormat.OGG_OPUS,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio to text using the configured STT provider.

        Args:
            audio_data: Raw audio bytes
            audio_format: Format of the audio
            language: Optional language hint

        Returns:
            TranscriptionResult with text
        """
        if not self._stt_provider:
            raise RuntimeError("STT provider not configured. Call initialize() first.")

        start_time = time.time()
        self._stats.stt_requests += 1

        try:
            result = await self._stt_provider.transcribe(
                audio_data=audio_data,
                audio_format=audio_format,
                language=language,
            )

            processing_ms = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_ms

            if result.duration_s:
                self._stats.stt_total_audio_s += result.duration_s

            # Update average
            total = self._stats.stt_avg_processing_ms * (self._stats.stt_requests - 1)
            self._stats.stt_avg_processing_ms = (total + processing_ms) / self._stats.stt_requests

            logger.debug(
                f"STT transcription: {len(result.text)} chars, "
                f"{processing_ms:.0f}ms, lang={result.language}"
            )
            return result

        except Exception as e:
            self._stats.stt_errors += 1
            logger.error(f"STT transcription failed: {e}")
            raise

    # ========================================================================
    # TTS
    # ========================================================================

    async def synthesize(
        self,
        text: str,
        output_format: Optional[AudioFormat] = None,
    ) -> SynthesisResult:
        """
        Synthesize text to audio using the configured TTS provider.

        Args:
            text: Text to synthesize
            output_format: Override output format

        Returns:
            SynthesisResult with audio data
        """
        if not self._tts_provider:
            raise RuntimeError("TTS provider not configured. Call initialize() first.")

        fmt = output_format or self.config.tts.output_format
        voice_id = self.config.tts.voice.voice_id

        # Check cache
        if self.config.cache_tts:
            cached = self._cache.get(text, voice_id, fmt)
            if cached:
                self._stats.cache_hits += 1
                logger.debug(f"TTS cache hit: {len(text)} chars")
                return cached
            self._stats.cache_misses += 1

        start_time = time.time()
        self._stats.tts_requests += 1

        try:
            result = await self._tts_provider.synthesize(
                text=text,
                output_format=fmt,
            )

            processing_ms = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_ms
            self._stats.tts_total_chars += len(text)

            # Update average
            total = self._stats.tts_avg_processing_ms * (self._stats.tts_requests - 1)
            self._stats.tts_avg_processing_ms = (total + processing_ms) / self._stats.tts_requests

            # Cache result
            if self.config.cache_tts:
                self._cache.put(text, voice_id, fmt, result)

            logger.debug(
                f"TTS synthesis: {len(text)} chars -> {result.size_bytes} bytes, "
                f"{processing_ms:.0f}ms"
            )
            return result

        except Exception as e:
            self._stats.tts_errors += 1
            logger.error(f"TTS synthesis failed: {e}")
            raise

    # ========================================================================
    # Full Pipeline
    # ========================================================================

    async def audio_to_text(
        self,
        audio_data: bytes,
        audio_format: AudioFormat = AudioFormat.OGG_OPUS,
        language: Optional[str] = None,
    ) -> str:
        """Convenience: transcribe audio and return just the text."""
        result = await self.transcribe(audio_data, audio_format, language)
        return result.text

    async def text_to_audio(
        self,
        text: str,
        output_format: Optional[AudioFormat] = None,
    ) -> bytes:
        """Convenience: synthesize text and return just the audio bytes."""
        result = await self.synthesize(text, output_format)
        return result.audio_data

    # ========================================================================
    # Utilities
    # ========================================================================

    def detect_audio_format(self, data: bytes) -> AudioFormat:
        """Detect audio format from file header bytes."""
        if data[:4] == b"RIFF":
            return AudioFormat.WAV
        if data[:3] == b"ID3" or (data[:2] == b"\xff\xfb"):
            return AudioFormat.MP3
        if data[:4] == b"OggS":
            return AudioFormat.OGG_OPUS
        if data[:4] == b"fLaC":
            return AudioFormat.FLAC
        if data[:4] == b"\x1aE\xdf\xa3":
            return AudioFormat.WEBM
        # Default
        return AudioFormat.OGG_OPUS

    @property
    def stats(self) -> VoicePipelineStats:
        self._stats.cache_hits = self._cache.hits
        self._stats.cache_misses = self._cache.misses
        return self._stats

    def clear_cache(self) -> None:
        """Clear TTS cache."""
        self._cache.clear()

    def get_provider_info(self) -> Dict[str, Any]:
        """Get info about configured providers."""
        return {
            "stt": {
                "enabled": self.config.enable_stt,
                "provider": self.config.stt.provider.value if self.config.enable_stt else None,
                "model": self.config.stt.model if self.config.enable_stt else None,
            },
            "tts": {
                "enabled": self.config.enable_tts,
                "provider": self.config.tts.provider.value if self.config.enable_tts else None,
                "model": self.config.tts.model if self.config.enable_tts else None,
                "voice": self.config.tts.voice.voice_id if self.config.enable_tts else None,
            },
            "cache": {
                "enabled": self.config.cache_tts,
                "size": self._cache.size,
                "hits": self._cache.hits,
                "misses": self._cache.misses,
            },
        }


# ============================================================================
# Singleton
# ============================================================================

_voice_service: Optional[VoiceService] = None


def get_voice_service() -> VoiceService:
    """Get the singleton VoiceService instance."""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceService()
    return _voice_service
