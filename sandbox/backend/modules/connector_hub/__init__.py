from fastapi import FastAPI
from .api import router


def register_module(app: FastAPI):
    """
    Wird vom module_loader aufgerufen.
    Hängt alle /api/connectors/... Routen an.
    """
    app.include_router(router, prefix="/api/connectors", tags=["connectors"])
