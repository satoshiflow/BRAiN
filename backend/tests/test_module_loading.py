from importlib import import_module
from pathlib import Path


def test_all_modules_have_router():
    base = Path(__file__).resolve().parents[1] / "modules"
    assert base.exists()
    for mod_dir in base.iterdir():
        if not mod_dir.is_dir():
            continue
        module_name = f"app.modules.{mod_dir.name}.router"
        try:
            mod = import_module(module_name)
            assert hasattr(mod, "router"), f"{module_name} has no 'router'"
        except ModuleNotFoundError:
            assert False, f"{module_name} not found"