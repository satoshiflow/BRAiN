from __future__ import annotations

from app.api.routes.auth import _build_invitation_url
from app.core.config import get_settings


def test_build_invitation_url_uses_configured_control_deck_base(monkeypatch) -> None:
    monkeypatch.setenv("CONTROL_DECK_BASE_URL", "https://control.example.test/")
    monkeypatch.setenv("BRAIN_RUNTIME_MODE", "remote")
    get_settings.cache_clear()

    try:
        invitation_url = _build_invitation_url("invite-token")
    finally:
        get_settings.cache_clear()

    assert invitation_url == "https://control.example.test/auth/register?token=invite-token"


def test_build_invitation_url_uses_local_default_in_local_mode(monkeypatch) -> None:
    monkeypatch.delenv("CONTROL_DECK_BASE_URL", raising=False)
    monkeypatch.setenv("BRAIN_RUNTIME_MODE", "local")
    get_settings.cache_clear()

    try:
        invitation_url = _build_invitation_url("invite-token")
    finally:
        get_settings.cache_clear()

    assert invitation_url == "http://127.0.0.1:3000/auth/register?token=invite-token"
