"""
Odoo Adapter Configuration
==========================

Konfiguration für Odoo PostgreSQL Verbindung.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class OdooAdapterConfig:
    """Konfiguration für Odoo Adapter"""
    
    host: str
    port: int
    database: str
    user: str
    password: str
    
    pool_min: int = 2
    pool_max: int = 20
    timeout: int = 30
    
    default_company_id: int = 1
    
    @classmethod
    def from_env(cls) -> "OdooAdapterConfig":
        """Erstellt Config aus Environment Variablen"""
        return cls(
            host=os.getenv("ODOO_DB_HOST", "localhost"),
            port=int(os.getenv("ODOO_DB_PORT", "5432")),
            database=os.getenv("ODOO_DB_NAME", "odoo"),
            user=os.getenv("ODOO_DB_USER", "odoo"),
            password=os.getenv("ODOO_DB_PASSWORD", ""),
            pool_min=int(os.getenv("ODOO_ADAPTER_POOL_MIN", "2")),
            pool_max=int(os.getenv("ODOO_ADAPTER_POOL_MAX", "20")),
            timeout=int(os.getenv("ODOO_ADAPTER_TIMEOUT", "30")),
            default_company_id=int(os.getenv("DEFAULT_COMPANY_ID", "1")),
        )
    
    @property
    def connection_string(self) -> str:
        """PostgreSQL Connection String"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


_config: Optional[OdooAdapterConfig] = None


def get_odoo_config() -> OdooAdapterConfig:
    """Holt die globale Config"""
    global _config
    if _config is None:
        _config = OdooAdapterConfig.from_env()
    return _config


def set_odoo_config(config: OdooAdapterConfig) -> None:
    """Setzt die Config (für Tests)"""
    global _config
    _config = config
