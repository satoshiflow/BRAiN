from typing import List

from fastapi import APIRouter

from app.core.module_registry import load_ui_manifests, ModuleManifest

router = APIRouter(prefix="/api/modules", tags=["Modules"])


@router.get("/ui-manifests", response_model=List[ModuleManifest])
def get_ui_manifests() -> List[ModuleManifest]:
    return load_ui_manifests()