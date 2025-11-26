from fastapi import APIRouter

from .services import registry

router = APIRouter(tags=["connectors"])


@router.get("/info")
def connectors_info():
    """
    High-Level Infos zum Connector-Hub.
    Tests erwarten: name, version, connectors.
    """
    return {
        "name": "Connector Hub",
        "version": "1.0.0",
        "connectors": registry.summary(),
    }


@router.get("/list")
def connectors_list():
    """
    Detail-Liste aller registrierten Connectoren.
    Tests erwarten: Feld 'connectors'.
    """
    return {"connectors": registry.list_connectors_as_dicts()}
