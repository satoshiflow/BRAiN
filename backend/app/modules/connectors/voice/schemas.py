"""
Voice Services - Schemas

Models for STT/TTS configuration, audio formats, transcription
results, and synthesis requests.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Audio Formats
# ============================================================================


class AudioFormat(str, Enum):
    """Supported audio formats."""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    OGG_OPUS = "ogg_opus"   # Telegram voice messages
    WEBM = "webm"
    FLAC = "flac"
    PCM = "pcm"
    M4A = "m4a"


class AudioEncoding(str, Enum):
    """Audio encoding types for streaming."""
    LINEAR16 = "linear16"
    OPUS = "opus"
    MP3 = "mp3"
    FLAC = "flac"


# ============================================================================
# STT (Speech-to-Text)
# ============================================================================


class STTProvider(str, Enum):
    """Available STT providers."""
    WHISPER_API = "whisper_api"          # OpenAI Whisper API
    WHISPER_LOCAL = "whisper_local"      # Local Whisper model
    GOOGLE_SPEECH = "google_speech"      # Google Cloud Speech-to-Text
    AZURE_SPEECH = "azure_speech"        # Azure Cognitive Services
    MOCK = "mock"                        # For testing


class STTConfig(BaseModel):
    """Configuration for STT provider."""
    provider: STTProvider = STTProvider.WHISPER_API
    api_key: str = ""
    api_url: Optional[str] = None
    model: str = "whisper-1"             # Whisper model name
    language: Optional[str] = None       # ISO 639-1 (e.g., "de", "en")
    temperature: float = 0.0
    max_audio_duration_s: float = 300.0  # 5 minutes max
    max_file_size_mb: float = 25.0       # 25 MB max (OpenAI limit)
    timeout_s: float = 30.0
    extra: Dict[str, Any] = Field(default_factory=dict)


class TranscriptionResult(BaseModel):
    """Result from STT transcription."""
    text: str
    language: Optional[str] = None
    confidence: Optional[float] = None
    duration_s: Optional[float] = None
    provider: STTProvider = STTProvider.WHISPER_API
    model: Optional[str] = None
    segments: List[TranscriptionSegment] = Field(default_factory=list)
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TranscriptionSegment(BaseModel):
    """A segment of transcribed audio with timing."""
    text: str
    start_s: float
    end_s: float
    confidence: Optional[float] = None


# Fix forward reference
TranscriptionResult.model_rebuild()


# ============================================================================
# TTS (Text-to-Speech)
# ============================================================================


class TTSProvider(str, Enum):
    """Available TTS providers."""
    OPENAI_TTS = "openai_tts"            # OpenAI TTS API
    ELEVENLABS = "elevenlabs"            # ElevenLabs
    AZURE_TTS = "azure_tts"              # Azure Cognitive Services
    GOOGLE_TTS = "google_tts"            # Google Cloud TTS
    MOCK = "mock"                        # For testing


class TTSVoice(BaseModel):
    """Voice configuration for TTS."""
    voice_id: str                        # Provider-specific voice ID
    name: str = ""
    language: str = "en"
    gender: Optional[str] = None         # male, female, neutral
    description: str = ""


class TTSConfig(BaseModel):
    """Configuration for TTS provider."""
    provider: TTSProvider = TTSProvider.OPENAI_TTS
    api_key: str = ""
    api_url: Optional[str] = None
    voice: TTSVoice = Field(
        default_factory=lambda: TTSVoice(voice_id="alloy", name="Alloy")
    )
    model: str = "tts-1"                 # Provider model
    output_format: AudioFormat = AudioFormat.MP3
    speed: float = 1.0                   # 0.25 to 4.0 for OpenAI
    max_text_length: int = 4096
    timeout_s: float = 30.0
    extra: Dict[str, Any] = Field(default_factory=dict)


class SynthesisResult(BaseModel):
    """Result from TTS synthesis."""
    audio_data: bytes
    format: AudioFormat
    duration_s: Optional[float] = None
    size_bytes: int = 0
    provider: TTSProvider = TTSProvider.OPENAI_TTS
    voice_id: str = ""
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


# ============================================================================
# Voice Pipeline
# ============================================================================


class VoicePipelineConfig(BaseModel):
    """Configuration for the full voice pipeline (STT + TTS)."""
    stt: STTConfig = Field(default_factory=STTConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    enable_stt: bool = True
    enable_tts: bool = True
    cache_tts: bool = True               # Cache TTS results
    cache_ttl_s: float = 3600.0          # 1 hour cache


class VoicePipelineStats(BaseModel):
    """Runtime statistics for voice pipeline."""
    stt_requests: int = 0
    stt_errors: int = 0
    stt_total_audio_s: float = 0.0
    stt_avg_processing_ms: float = 0.0
    tts_requests: int = 0
    tts_errors: int = 0
    tts_total_chars: int = 0
    tts_avg_processing_ms: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
