"""
Tests for Voice Services - Phase 4

Covers:
- Voice schemas (audio formats, configs, results)
- STT providers (MockSTTProvider, factory, validation)
- TTS providers (MockTTSProvider, factory, validation)
- TTSCache (get, put, eviction, expiry)
- VoiceService (transcribe, synthesize, pipeline, stats, format detection)
"""

from __future__ import annotations

import time
from typing import Optional

import pytest

from app.modules.connectors.voice.schemas import (
    AudioFormat,
    AudioEncoding,
    STTConfig,
    STTProvider,
    SynthesisResult,
    TTSConfig,
    TTSProvider,
    TTSVoice,
    TranscriptionResult,
    TranscriptionSegment,
    VoicePipelineConfig,
    VoicePipelineStats,
)
from app.modules.connectors.voice.stt_providers import (
    BaseSTTProvider,
    MockSTTProvider,
    create_stt_provider,
)
from app.modules.connectors.voice.tts_providers import (
    BaseTTSProvider,
    MockTTSProvider,
    create_tts_provider,
)
from app.modules.connectors.voice.service import (
    TTSCache,
    VoiceService,
)


# ============================================================================
# Test Schemas
# ============================================================================


class TestVoiceSchemas:
    def test_audio_format_values(self) -> None:
        assert AudioFormat.OGG_OPUS == "ogg_opus"
        assert AudioFormat.MP3 == "mp3"
        assert AudioFormat.WAV == "wav"

    def test_stt_config_defaults(self) -> None:
        config = STTConfig()
        assert config.provider == STTProvider.WHISPER_API
        assert config.model == "whisper-1"
        assert config.max_file_size_mb == 25.0

    def test_tts_config_defaults(self) -> None:
        config = TTSConfig()
        assert config.provider == TTSProvider.OPENAI_TTS
        assert config.voice.voice_id == "alloy"
        assert config.output_format == AudioFormat.MP3
        assert config.speed == 1.0

    def test_transcription_result(self) -> None:
        result = TranscriptionResult(text="Hello world", language="en")
        assert result.text == "Hello world"
        assert result.confidence is None

    def test_transcription_segment(self) -> None:
        seg = TranscriptionSegment(text="Hello", start_s=0.0, end_s=0.5)
        assert seg.end_s == 0.5

    def test_synthesis_result(self) -> None:
        result = SynthesisResult(
            audio_data=b"\x00\xff", format=AudioFormat.MP3, size_bytes=2
        )
        assert result.size_bytes == 2

    def test_tts_voice(self) -> None:
        voice = TTSVoice(voice_id="nova", name="Nova", language="en", gender="female")
        assert voice.voice_id == "nova"

    def test_pipeline_config(self) -> None:
        config = VoicePipelineConfig()
        assert config.enable_stt is True
        assert config.enable_tts is True
        assert config.cache_tts is True

    def test_pipeline_stats(self) -> None:
        stats = VoicePipelineStats()
        assert stats.stt_requests == 0
        assert stats.tts_requests == 0


# ============================================================================
# Test STT Providers
# ============================================================================


class TestMockSTTProvider:
    @pytest.mark.asyncio
    async def test_transcribe(self) -> None:
        provider = MockSTTProvider(mock_text="Hello world")
        result = await provider.transcribe(b"\x00" * 100)
        assert result.text == "Hello world"
        assert result.provider == STTProvider.MOCK
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_transcribe_with_language(self) -> None:
        provider = MockSTTProvider()
        result = await provider.transcribe(b"\x00" * 100, language="de")
        assert result.language == "de"

    @pytest.mark.asyncio
    async def test_transcribe_empty_audio(self) -> None:
        provider = MockSTTProvider()
        with pytest.raises(ValueError, match="empty"):
            await provider.transcribe(b"")

    @pytest.mark.asyncio
    async def test_transcribe_failure(self) -> None:
        provider = MockSTTProvider(fail=True)
        with pytest.raises(RuntimeError, match="Mock STT failure"):
            await provider.transcribe(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_transcribe_file_too_large(self) -> None:
        config = STTConfig(provider=STTProvider.MOCK, max_file_size_mb=0.001)
        provider = MockSTTProvider(config=config)
        big_data = b"\x00" * 2000  # >0.001 MB
        with pytest.raises(ValueError, match="too large"):
            await provider.transcribe(big_data)


class TestSTTFactory:
    def test_create_mock(self) -> None:
        config = STTConfig(provider=STTProvider.MOCK)
        provider = create_stt_provider(config)
        assert isinstance(provider, MockSTTProvider)

    def test_create_whisper(self) -> None:
        config = STTConfig(provider=STTProvider.WHISPER_API, api_key="test")
        provider = create_stt_provider(config)
        assert provider.provider_type == STTProvider.WHISPER_API

    def test_create_unsupported(self) -> None:
        config = STTConfig(provider=STTProvider.GOOGLE_SPEECH)
        with pytest.raises(ValueError, match="Unsupported"):
            create_stt_provider(config)


# ============================================================================
# Test TTS Providers
# ============================================================================


class TestMockTTSProvider:
    @pytest.mark.asyncio
    async def test_synthesize(self) -> None:
        provider = MockTTSProvider()
        result = await provider.synthesize("Hello world")
        assert len(result.audio_data) > 0
        assert result.provider == TTSProvider.MOCK
        assert provider.call_count == 1
        assert provider.last_text == "Hello world"

    @pytest.mark.asyncio
    async def test_synthesize_format_override(self) -> None:
        provider = MockTTSProvider()
        result = await provider.synthesize("Hi", output_format=AudioFormat.WAV)
        assert result.format == AudioFormat.WAV

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self) -> None:
        provider = MockTTSProvider()
        with pytest.raises(ValueError, match="empty"):
            await provider.synthesize("")

    @pytest.mark.asyncio
    async def test_synthesize_text_too_long(self) -> None:
        config = TTSConfig(provider=TTSProvider.MOCK, max_text_length=10)
        provider = MockTTSProvider(config=config)
        with pytest.raises(ValueError, match="too long"):
            await provider.synthesize("x" * 20)

    @pytest.mark.asyncio
    async def test_synthesize_failure(self) -> None:
        provider = MockTTSProvider(fail=True)
        with pytest.raises(RuntimeError, match="Mock TTS failure"):
            await provider.synthesize("Hello")


class TestTTSFactory:
    def test_create_mock(self) -> None:
        config = TTSConfig(provider=TTSProvider.MOCK)
        provider = create_tts_provider(config)
        assert isinstance(provider, MockTTSProvider)

    def test_create_openai(self) -> None:
        config = TTSConfig(provider=TTSProvider.OPENAI_TTS, api_key="test")
        provider = create_tts_provider(config)
        assert provider.provider_type == TTSProvider.OPENAI_TTS

    def test_create_unsupported(self) -> None:
        config = TTSConfig(provider=TTSProvider.ELEVENLABS)
        with pytest.raises(ValueError, match="Unsupported"):
            create_tts_provider(config)


# ============================================================================
# Test TTSCache
# ============================================================================


class TestTTSCache:
    def test_put_and_get(self) -> None:
        cache = TTSCache()
        result = SynthesisResult(
            audio_data=b"\x00", format=AudioFormat.MP3, size_bytes=1
        )
        cache.put("hello", "alloy", AudioFormat.MP3, result)
        cached = cache.get("hello", "alloy", AudioFormat.MP3)
        assert cached is not None
        assert cached.audio_data == b"\x00"

    def test_cache_miss(self) -> None:
        cache = TTSCache()
        assert cache.get("hello", "alloy", AudioFormat.MP3) is None
        assert cache.misses == 1

    def test_cache_hit_counter(self) -> None:
        cache = TTSCache()
        result = SynthesisResult(audio_data=b"\x00", format=AudioFormat.MP3)
        cache.put("hi", "alloy", AudioFormat.MP3, result)
        cache.get("hi", "alloy", AudioFormat.MP3)
        cache.get("hi", "alloy", AudioFormat.MP3)
        assert cache.hits == 2

    def test_cache_expiry(self) -> None:
        cache = TTSCache(ttl_s=0.0)  # Immediate expiry
        result = SynthesisResult(audio_data=b"\x00", format=AudioFormat.MP3)
        cache.put("hi", "alloy", AudioFormat.MP3, result)
        # Should be expired
        assert cache.get("hi", "alloy", AudioFormat.MP3) is None

    def test_cache_eviction(self) -> None:
        cache = TTSCache(max_size=2)
        r = SynthesisResult(audio_data=b"\x00", format=AudioFormat.MP3)
        cache.put("a", "v", AudioFormat.MP3, r)
        cache.put("b", "v", AudioFormat.MP3, r)
        cache.put("c", "v", AudioFormat.MP3, r)  # Should evict "a"
        assert cache.size == 2
        assert cache.get("a", "v", AudioFormat.MP3) is None

    def test_cache_clear(self) -> None:
        cache = TTSCache()
        r = SynthesisResult(audio_data=b"\x00", format=AudioFormat.MP3)
        cache.put("a", "v", AudioFormat.MP3, r)
        cache.clear()
        assert cache.size == 0

    def test_different_format_different_key(self) -> None:
        cache = TTSCache()
        r1 = SynthesisResult(audio_data=b"\x01", format=AudioFormat.MP3)
        r2 = SynthesisResult(audio_data=b"\x02", format=AudioFormat.WAV)
        cache.put("hi", "alloy", AudioFormat.MP3, r1)
        cache.put("hi", "alloy", AudioFormat.WAV, r2)
        assert cache.get("hi", "alloy", AudioFormat.MP3).audio_data == b"\x01"
        assert cache.get("hi", "alloy", AudioFormat.WAV).audio_data == b"\x02"


# ============================================================================
# Test VoiceService
# ============================================================================


class TestVoiceService:
    @pytest.fixture
    def service(self) -> VoiceService:
        svc = VoiceService()
        svc.set_stt_provider(MockSTTProvider(mock_text="Transcribed text"))
        svc.set_tts_provider(MockTTSProvider())
        return svc

    @pytest.mark.asyncio
    async def test_transcribe(self, service: VoiceService) -> None:
        result = await service.transcribe(b"\x00" * 100)
        assert result.text == "Transcribed text"
        assert service.stats.stt_requests == 1

    @pytest.mark.asyncio
    async def test_transcribe_no_provider(self) -> None:
        svc = VoiceService()
        with pytest.raises(RuntimeError, match="STT provider not configured"):
            await svc.transcribe(b"\x00" * 100)

    @pytest.mark.asyncio
    async def test_transcribe_error_tracking(self) -> None:
        svc = VoiceService()
        svc.set_stt_provider(MockSTTProvider(fail=True))
        with pytest.raises(RuntimeError):
            await svc.transcribe(b"\x00" * 100)
        assert svc.stats.stt_errors == 1

    @pytest.mark.asyncio
    async def test_synthesize(self, service: VoiceService) -> None:
        result = await service.synthesize("Hello")
        assert len(result.audio_data) > 0
        assert service.stats.tts_requests == 1

    @pytest.mark.asyncio
    async def test_synthesize_no_provider(self) -> None:
        svc = VoiceService()
        with pytest.raises(RuntimeError, match="TTS provider not configured"):
            await svc.synthesize("Hello")

    @pytest.mark.asyncio
    async def test_synthesize_caching(self, service: VoiceService) -> None:
        r1 = await service.synthesize("Hello")
        r2 = await service.synthesize("Hello")
        assert service.stats.cache_hits >= 1
        # Provider called only once
        assert service._tts_provider.call_count == 1

    @pytest.mark.asyncio
    async def test_synthesize_cache_disabled(self) -> None:
        config = VoicePipelineConfig(cache_tts=False)
        svc = VoiceService(config=config)
        svc.set_tts_provider(MockTTSProvider())
        await svc.synthesize("Hello")
        await svc.synthesize("Hello")
        assert svc._tts_provider.call_count == 2

    @pytest.mark.asyncio
    async def test_synthesize_error_tracking(self) -> None:
        svc = VoiceService()
        svc.set_tts_provider(MockTTSProvider(fail=True))
        with pytest.raises(RuntimeError):
            await svc.synthesize("Hello")
        assert svc.stats.tts_errors == 1

    @pytest.mark.asyncio
    async def test_audio_to_text(self, service: VoiceService) -> None:
        text = await service.audio_to_text(b"\x00" * 100)
        assert text == "Transcribed text"

    @pytest.mark.asyncio
    async def test_text_to_audio(self, service: VoiceService) -> None:
        audio = await service.text_to_audio("Hello")
        assert len(audio) > 0

    def test_detect_wav(self, service: VoiceService) -> None:
        assert service.detect_audio_format(b"RIFF" + b"\x00" * 100) == AudioFormat.WAV

    def test_detect_mp3_id3(self, service: VoiceService) -> None:
        assert service.detect_audio_format(b"ID3" + b"\x00" * 100) == AudioFormat.MP3

    def test_detect_mp3_sync(self, service: VoiceService) -> None:
        assert service.detect_audio_format(b"\xff\xfb" + b"\x00" * 100) == AudioFormat.MP3

    def test_detect_ogg(self, service: VoiceService) -> None:
        assert service.detect_audio_format(b"OggS" + b"\x00" * 100) == AudioFormat.OGG_OPUS

    def test_detect_flac(self, service: VoiceService) -> None:
        assert service.detect_audio_format(b"fLaC" + b"\x00" * 100) == AudioFormat.FLAC

    def test_detect_webm(self, service: VoiceService) -> None:
        assert service.detect_audio_format(b"\x1aE\xdf\xa3" + b"\x00" * 100) == AudioFormat.WEBM

    def test_detect_unknown_defaults_ogg(self, service: VoiceService) -> None:
        assert service.detect_audio_format(b"\x00\x00\x00\x00") == AudioFormat.OGG_OPUS

    def test_get_provider_info(self, service: VoiceService) -> None:
        info = service.get_provider_info()
        assert info["stt"]["enabled"] is True
        assert info["tts"]["enabled"] is True
        assert "cache" in info

    def test_clear_cache(self, service: VoiceService) -> None:
        service._cache.put("a", "v", AudioFormat.MP3,
                           SynthesisResult(audio_data=b"\x00", format=AudioFormat.MP3))
        service.clear_cache()
        assert service._cache.size == 0

    def test_initialize_with_mock_config(self) -> None:
        config = VoicePipelineConfig(
            stt=STTConfig(provider=STTProvider.MOCK),
            tts=TTSConfig(provider=TTSProvider.MOCK),
        )
        svc = VoiceService(config=config)
        svc.initialize()
        assert svc._stt_provider is not None
        assert svc._tts_provider is not None

    @pytest.mark.asyncio
    async def test_stats_accumulation(self, service: VoiceService) -> None:
        await service.transcribe(b"\x00" * 100)
        await service.transcribe(b"\x00" * 200)
        await service.synthesize("Hello")
        await service.synthesize("World")
        stats = service.stats
        assert stats.stt_requests == 2
        assert stats.tts_requests == 2
        assert stats.stt_avg_processing_ms > 0
        assert stats.tts_total_chars == 10  # "Hello" + "World"
