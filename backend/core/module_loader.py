import importlib
from pathlib import Path
from loguru import logger


MODULES_PATH = Path(__file__).resolve().parent.parent / "modules"


def load_modules(app) -> None:
    """
    Lädt alle Module unter backend/modules/*
    und ruft deren register_module(app) auf, falls vorhanden.
    """
    if not MODULES_PATH.exists():
        logger.warning(f"Modules path not found: {MODULES_PATH}")
        return

    for pkg in MODULES_PATH.iterdir():
        if not pkg.is_dir():
            continue

        module_name = f"backend.modules.{pkg.name}"

        try:
            mod = importlib.import_module(module_name)
            register = getattr(mod, "register_module", None)
            if callable(register):
                register(app)
                logger.info(f"[modules] Registered module: {module_name}")
            else:
                logger.debug(f"[modules] No register_module in {module_name}")
        except Exception as e:
            logger.error(f"[modules] Failed to load module {module_name}: {e}")
