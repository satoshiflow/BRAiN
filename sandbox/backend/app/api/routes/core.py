from typing import List

from fastapi import APIRouter, HTTPException, Request

from app.core.module_registry import get_registry, ModuleManifest

# WICHTIG:
# Wir verwenden hier KEIN prefix im APIRouter,
# sondern schreiben die vollständigen Pfade in die Decorators,
# damit es mit include_all_routers garantiert funktioniert.
router = APIRouter()


@router.get("/api/core/modules/ui-manifest", response_model=List[ModuleManifest])
def get_modules_ui_manifest():
    """
    Liefert die UI-Manifeste aller Module.
    Wird vom Control-Deck genutzt.
    """
    registry = get_registry()
    modules = registry.list_ui_manifests()
    # KEIN HTTP 404 hier – leere Liste ist ok
    return modules


@router.get("/api/core/modules/{name}", response_model=ModuleManifest)
def get_single_module(name: str):
    """
    Optionaler Detail-Endpoint.
    Hier ist ein 404 'Module not found' sinnvoll.
    """
    registry = get_registry()
    module = registry.get_module(name)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    return module


@router.get("/debug/routes")
def debug_routes(request: Request):
    """
    Hilfsroute zur Fehlersuche:
    listet alle registrierten Routen des FastAPI-Apps.
    """
    routes_info = []
    for r in request.app.routes:
        methods = getattr(r, "methods", None)
        routes_info.append(
            {
                "path": getattr(r, "path", None),
                "name": getattr(r, "name", None),
                "methods": list(methods) if methods else None,
            }
        )
    return routes_info