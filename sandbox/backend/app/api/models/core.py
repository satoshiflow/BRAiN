from pydantic import BaseModel
from typing import List


class ModuleSecurityDTO(BaseModel):
    required_roles: List[str] = []


class ModuleGovernanceDTO(BaseModel):
    level: int = 0


class ModuleUIDTO(BaseModel):
    group: str = "Core"
    icon: str = "Circle"


class ModuleManifestDTO(BaseModel):
    name: str
    version: str
    router_prefix: str
    status: str = "experimental"

    security: ModuleSecurityDTO
    governance: ModuleGovernanceDTO
    ui: ModuleUIDTO

    class Config:
        from_attributes = True