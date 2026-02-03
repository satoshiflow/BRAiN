"""
Voice Services - Text-to-Speech Providers

Abstract base + concrete implementations for TTS.
Each provider converts text to audio bytes via its API.

Providers:
- OpenAITTSProvider: OpenAI TTS API
- ElevenLabsProvider: ElevenLabs API (placeholder)
- MockTTSProvider: For testing
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from app.modules.connectors.voice.schemas import (
    AudioFormat,
    SynthesisResult,
    TTSConfig,
    TTSProvider,
)


class BaseTTSProvider(ABC):
    """Abstract base class for TTS providers."""

    provider_type: TTSProvider

    def __init__(self, config: TTSConfig) -> None:
        self.config = config

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        output_format: Optional[AudioFormat] = None,
    ) -> SynthesisResult:
        """
        Synthesize text to audio.

        Args:
            text: Text to synthesize
            output_format: Override output format (or use config default)

        Returns:
            SynthesisResult with audio data and metadata
        """
        ...

    def _validate_text(self, text: str) -> None:
        """Validate text before synthesis."""
        if not text or not text.strip():
            raise ValueError("Text is empty")
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text too long: {len(text)} chars "
                f"(max {self.config.max_text_length})"
            )

    def _format_to_api_format(self, fmt: AudioFormat) -> str:
        """Map AudioFormat to provider-specific format string."""
        mapping = {
            AudioFormat.MP3: "mp3",
            AudioFormat.OGG_OPUS: "opus",
            AudioFormat.WAV: "wav",
            AudioFormat.FLAC: "flac",
            AudioFormat.PCM: "pcm",
        }
        return mapping.get(fmt, "mp3")


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS API provider."""

    provider_type = TTSProvider.OPENAI_TTS

    async def synthesize(
        self,
        text: str,
        output_format: Optional[AudioFormat] = None,
    ) -> SynthesisResult:
        self._validate_text(text)

        fmt = output_format or self.config.output_format
        start_time = time.time()
        api_url = self.config.api_url or "https://api.openai.com/v1/audio/speech"

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_s) as client:
                payload = {
                    "model": self.config.model,
                    "input": text,
                    "voice": self.config.voice.voice_id,
                    "response_format": self._format_to_api_format(fmt),
                    "speed": self.config.speed,
                }

                response = await client.post(
                    api_url,
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                processing_ms = (time.time() - start_time) * 1000

                if response.status_code != 200:
                    raise RuntimeError(
                        f"OpenAI TTS error {response.status_code}: {response.text}"
                    )

                audio_data = response.content

                return SynthesisResult(
                    audio_data=audio_data,
                    format=fmt,
                    size_bytes=len(audio_data),
                    provider=self.provider_type,
                    voice_id=self.config.voice.voice_id,
                    processing_time_ms=processing_ms,
                )

        except httpx.ConnectError as e:
            raise RuntimeError(f"Cannot connect to OpenAI TTS API: {e}")


class MockTTSProvider(BaseTTSProvider):
    """Mock TTS provider for testing."""

    provider_type = TTSProvider.MOCK

    def __init__(
        self,
        config: Optional[TTSConfig] = None,
        fail: bool = False,
    ) -> None:
        super().__init__(config or TTSConfig(provider=TTSProvider.MOCK))
        self.fail = fail
        self.call_count = 0
        self.last_text: Optional[str] = None

    async def synthesize(
        self,
        text: str,
        output_format: Optional[AudioFormat] = None,
    ) -> SynthesisResult:
        self._validate_text(text)
        self.call_count += 1
        self.last_text = text

        if self.fail:
            raise RuntimeError("Mock TTS failure")

        fmt = output_format or self.config.output_format
        # Generate fake audio data (size proportional to text length)
        fake_audio = b"\x00\xff" * len(text) * 10

        return SynthesisResult(
            audio_data=fake_audio,
            format=fmt,
            duration_s=len(text) * 0.06,  # ~60ms per char
            size_bytes=len(fake_audio),
            provider=self.provider_type,
            voice_id=self.config.voice.voice_id,
            processing_time_ms=5.0,
        )


def create_tts_provider(config: TTSConfig) -> BaseTTSProvider:
    """Factory function to create TTS provider from config."""
    providers = {
        TTSProvider.OPENAI_TTS: OpenAITTSProvider,
        TTSProvider.MOCK: MockTTSProvider,
    }
    provider_cls = providers.get(config.provider)
    if not provider_cls:
        raise ValueError(
            f"Unsupported TTS provider: {config.provider}. "
            f"Available: {list(providers.keys())}"
        )
    return provider_cls(config)
