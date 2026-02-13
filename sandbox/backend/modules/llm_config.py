# backend/modules/llm_config.py
"""
LLM-Konfiguration für BRAiN
---------------------------

Zentrale Stelle für:
- Provider (z.B. ollama)
- Host (OLLAMA_HOST)
- Model (OLLAMA_MODEL)
- Temperatur
- Max Tokens
- enabled-Flag

Die Config wird in-memory gehalten und zusätzlich in einer JSON-Datei
persistiert (standard: storage/llm_config.json), damit Änderungen
über Neustarts hinweg erhalten bleiben.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import RLock
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    provider: str = Field(
        default="ollama",
        description="LLM-Provider (z.B. 'ollama', 'openai', 'lmstudio').",
    )
    host: str = Field(
        default_factory=lambda: os.getenv(
            "OLLAMA_HOST", "http://host.docker.internal:11434"
        ),
        description="Basis-URL des LLM-Backends.",
    )
    model: str = Field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL", "phi3"),
        description="Standardmodell (z.B. 'phi3').",
    )
    temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Sampling-Temperatur.",
    )
    max_tokens: int = Field(
        default=1024,
        ge=1,
        le=8192,
        description="Maximale Tokenanzahl für Antworten.",
    )
    enabled: bool = Field(
        default=True,
        description="Globaler Schalter: LLM-Nutzung erlaubt/verbieten.",
    )

    @field_validator("host")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


class LLMConfigUpdate(BaseModel):
    provider: Optional[str] = None
    host: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    enabled: Optional[bool] = None


# -------------------------------------------------------------------
# Interner Store + Persistence
# -------------------------------------------------------------------

_CONFIG_LOCK = RLock()
_CONFIG: Optional[LLMConfig] = None

_CONFIG_PATH = Path(
    os.getenv("LLM_CONFIG_PATH", "storage/llm_config.json")
)


def _ensure_storage_dir() -> None:
    if not _CONFIG_PATH.parent.exists():
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_config_from_disk() -> LLMConfig:
    if _CONFIG_PATH.is_file():
        try:
            raw = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            return LLMConfig(**raw)
        except Exception:
            # Fallback auf Defaults, wenn Datei korrupt ist
            pass

    # Defaults aus ENV
    return LLMConfig()


def _save_config_to_disk(config: LLMConfig) -> None:
    _ensure_storage_dir()
    _CONFIG_PATH.write_text(
        config.model_dump_json(indent=2),
        encoding="utf-8",
    )


def get_llm_config() -> LLMConfig:
    """
    Liefert die aktuelle LLM-Konfiguration.
    Lazy-Load aus JSON/ENV beim ersten Zugriff.
    """
    global _CONFIG
    with _CONFIG_LOCK:
        if _CONFIG is None:
            _CONFIG = _load_config_from_disk()
        return _CONFIG


def update_llm_config(update: LLMConfigUpdate) -> LLMConfig:
    """
    Aktualisiert die Konfiguration mit den (optional) gesetzten Feldern
    im Update-Objekt, persistiert sie auf Disk und liefert das neue Objekt.
    """
    global _CONFIG
    with _CONFIG_LOCK:
        current = get_llm_config()
        data = current.model_dump()

        for field_name, value in update.model_dump(exclude_unset=True).items():
            if value is not None:
                data[field_name] = value

        new_config = LLMConfig(**data)
        _CONFIG = new_config
        _save_config_to_disk(new_config)
        return new_config


def reset_llm_config() -> LLMConfig:
    """
    Setzt die Config auf Default (ENV/Hardcoded) zurück und überschreibt
    die bestehende JSON-Datei.
    """
    global _CONFIG
    with _CONFIG_LOCK:
        new_config = LLMConfig()
        _CONFIG = new_config
        _save_config_to_disk(new_config)
        return new_config
# Ende backend/modules/llm_config.py
