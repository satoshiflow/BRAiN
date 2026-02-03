"""
Voice Services - Speech-to-Text Providers

Abstract base + concrete implementations for STT.
Each provider converts audio bytes to text via its API.

Providers:
- WhisperAPIProvider: OpenAI Whisper API (cloud)
- WhisperLocalProvider: Local Whisper model (placeholder for Phase 4+)
- GoogleSpeechProvider: Google Cloud Speech-to-Text (placeholder)
- MockSTTProvider: For testing
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from app.modules.connectors.voice.schemas import (
    AudioFormat,
    STTConfig,
    STTProvider,
    TranscriptionResult,
    TranscriptionSegment,
)


class BaseSTTProvider(ABC):
    """Abstract base class for STT providers."""

    provider_type: STTProvider

    def __init__(self, config: STTConfig) -> None:
        self.config = config

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: AudioFormat = AudioFormat.OGG_OPUS,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio data to text.

        Args:
            audio_data: Raw audio bytes
            audio_format: Format of the audio data
            language: Optional language hint (ISO 639-1)

        Returns:
            TranscriptionResult with text and metadata
        """
        ...

    def _validate_audio(self, audio_data: bytes) -> None:
        """Validate audio data before sending to provider."""
        size_mb = len(audio_data) / (1024 * 1024)
        if size_mb > self.config.max_file_size_mb:
            raise ValueError(
                f"Audio file too large: {size_mb:.1f}MB "
                f"(max {self.config.max_file_size_mb}MB)"
            )
        if len(audio_data) == 0:
            raise ValueError("Audio data is empty")

    def _format_to_extension(self, fmt: AudioFormat) -> str:
        """Map AudioFormat to file extension."""
        mapping = {
            AudioFormat.WAV: "wav",
            AudioFormat.MP3: "mp3",
            AudioFormat.OGG: "ogg",
            AudioFormat.OGG_OPUS: "ogg",
            AudioFormat.WEBM: "webm",
            AudioFormat.FLAC: "flac",
            AudioFormat.M4A: "m4a",
        }
        return mapping.get(fmt, "ogg")

    def _format_to_mime(self, fmt: AudioFormat) -> str:
        """Map AudioFormat to MIME type."""
        mapping = {
            AudioFormat.WAV: "audio/wav",
            AudioFormat.MP3: "audio/mpeg",
            AudioFormat.OGG: "audio/ogg",
            AudioFormat.OGG_OPUS: "audio/ogg",
            AudioFormat.WEBM: "audio/webm",
            AudioFormat.FLAC: "audio/flac",
            AudioFormat.M4A: "audio/mp4",
        }
        return mapping.get(fmt, "audio/ogg")


class WhisperAPIProvider(BaseSTTProvider):
    """OpenAI Whisper API provider."""

    provider_type = STTProvider.WHISPER_API

    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: AudioFormat = AudioFormat.OGG_OPUS,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        self._validate_audio(audio_data)

        start_time = time.time()
        api_url = self.config.api_url or "https://api.openai.com/v1/audio/transcriptions"
        ext = self._format_to_extension(audio_format)
        mime = self._format_to_mime(audio_format)
        lang = language or self.config.language

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                files = {
                    "file": (f"audio.{ext}", audio_data, mime),
                }
                data: Dict[str, Any] = {
                    "model": self.config.model,
                    "response_format": "verbose_json",
                }
                if lang:
                    data["language"] = lang
                if self.config.temperature > 0:
                    data["temperature"] = str(self.config.temperature)

                response = await client.post(
                    api_url,
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                    files=files,
                    data=data,
                )

                processing_ms = (time.time() - start_time) * 1000

                if response.status_code != 200:
                    raise RuntimeError(
                        f"Whisper API error {response.status_code}: {response.text}"
                    )

                result = response.json()

                segments = []
                for seg in result.get("segments", []):
                    segments.append(
                        TranscriptionSegment(
                            text=seg.get("text", ""),
                            start_s=seg.get("start", 0.0),
                            end_s=seg.get("end", 0.0),
                            confidence=seg.get("avg_logprob"),
                        )
                    )

                return TranscriptionResult(
                    text=result.get("text", ""),
                    language=result.get("language"),
                    duration_s=result.get("duration"),
                    provider=self.provider_type,
                    model=self.config.model,
                    segments=segments,
                    processing_time_ms=processing_ms,
                )

        except httpx.ConnectError as e:
            raise RuntimeError(f"Cannot connect to Whisper API: {e}")

    async def check_health(self) -> bool:
        """Check if the Whisper API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False


class MockSTTProvider(BaseSTTProvider):
    """Mock STT provider for testing."""

    provider_type = STTProvider.MOCK

    def __init__(
        self,
        config: Optional[STTConfig] = None,
        mock_text: str = "This is a mock transcription.",
        mock_language: str = "en",
        fail: bool = False,
    ) -> None:
        super().__init__(config or STTConfig(provider=STTProvider.MOCK))
        self.mock_text = mock_text
        self.mock_language = mock_language
        self.fail = fail
        self.call_count = 0

    async def transcribe(
        self,
        audio_data: bytes,
        audio_format: AudioFormat = AudioFormat.OGG_OPUS,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        self._validate_audio(audio_data)
        self.call_count += 1

        if self.fail:
            raise RuntimeError("Mock STT failure")

        return TranscriptionResult(
            text=self.mock_text,
            language=language or self.mock_language,
            confidence=0.95,
            duration_s=len(audio_data) / 16000,  # Approximate
            provider=self.provider_type,
            model="mock-whisper",
            processing_time_ms=10.0,
        )


def create_stt_provider(config: STTConfig) -> BaseSTTProvider:
    """Factory function to create STT provider from config."""
    providers = {
        STTProvider.WHISPER_API: WhisperAPIProvider,
        STTProvider.MOCK: MockSTTProvider,
    }
    provider_cls = providers.get(config.provider)
    if not provider_cls:
        raise ValueError(
            f"Unsupported STT provider: {config.provider}. "
            f"Available: {list(providers.keys())}"
        )
    return provider_cls(config)
