from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# Basis: modules-Verzeichnis
BASE_DIR = Path(__file__).resolve().parents[1]
MODULES_DIR = BASE_DIR / "modules"


class UIModuleRoute(BaseModel):
    path: str
    label: str
    icon: Optional[str] = None


class ModuleManifest(BaseModel):
    """
    Gemeinsames Manifest-Modell, das sowohl vom Core
    als auch vom Control-Deck genutzt werden kann.
    """
    name: str
    label: str
    category: Optional[str] = None
    routes: List[UIModuleRoute] = []


def load_ui_manifests() -> List[ModuleManifest]:
    """
    Lädt UI_MANIFEST aus allen Modulen und gibt sie als ModuleManifest-Liste zurück.
    Erwartet in jedem Modul eine ui_manifest.py mit einem UI_MANIFEST-Dict.
    """
    manifests: List[ModuleManifest] = []

    if not MODULES_DIR.exists():
        return manifests

    for mod_dir in MODULES_DIR.iterdir():
        if not mod_dir.is_dir():
            continue

        manifest_py = mod_dir / "ui_manifest.py"
        if not manifest_py.exists():
            continue

        scope: Dict[str, Any] = {}
        try:
            exec(manifest_py.read_text(), scope)
        except Exception:
            # Fehler in einem Modul-Manifest sollen nicht das ganze System killen
            continue

        raw_manifest = scope.get("UI_MANIFEST")
        if not raw_manifest:
            continue

        try:
            manifests.append(ModuleManifest(**raw_manifest))
        except Exception:
            # Falls Felder fehlen/inkompatibel sind – Modul einfach überspringen
            continue

    return manifests


class ModuleRegistry:
    """
    Registry, die Module-Informationen (insb. UI-Manifeste) sammelt.
    Dient als zentrale Anlaufstelle für API-Routen wie app.api.routes.core.
    """

    def __init__(self) -> None:
        self._ui_manifests: List[ModuleManifest] = []
        self.reload()

    def reload(self) -> None:
        """Lädt die UI-Manifeste neu von der Platte."""
        self._ui_manifests = load_ui_manifests()

    # neue, explizite Methode
    def list_ui_manifests(self) -> List[ModuleManifest]:
        return list(self._ui_manifests)

    # Alias für mögliche ältere Benennungen
    def list_modules(self) -> List[ModuleManifest]:
        return self.list_ui_manifests()

    def get_module(self, name: str) -> Optional[ModuleManifest]:
        for m in self._ui_manifests:
            if m.name == name:
                return m
        return None


# Singleton-Registry, damit bestehender Code einfach get_registry() nutzen kann
_registry: Optional[ModuleRegistry] = None


def get_registry() -> ModuleRegistry:
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry