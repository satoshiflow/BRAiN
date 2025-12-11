import importlib
import pkgutil
from fastapi import FastAPI, APIRouter

def include_all_routers(app: FastAPI, base_prefix: str = "") -> None:
    from . import health  # noqa: F401 - ensure package is discovered
    from app.api import routes

    for _, module_name, _ in pkgutil.iter_modules(routes.__path__):
        module = importlib.import_module(f"app.api.routes.{module_name}")
        router = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            app.include_router(router)
