"""
Odoo Connection Pool
===================

Thread-safe PostgreSQL Connection Pool für Odoo Datenbank.
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2 import pool
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

from .config import OdooAdapterConfig, get_odoo_config

logger = logging.getLogger(__name__)


class OdooConnectionPool:
    """
    Thread-safe Connection Pool für Odoo PostgreSQL Datenbank.
    
    Bietet:
    - Connection Pooling für hohe Last
    - Automatisches Connection Management
    - Query Execution mit Dict Results
    """
    
    def __init__(self, config: Optional[OdooAdapterConfig] = None):
        self.config = config or get_odoo_config()
        self._pool: Optional[ThreadedConnectionPool] = None
        self._initialized = False
    
    def _ensure_pool(self) -> None:
        """Lazy Initialization - verbindet nur bei Bedarf"""
        if self._initialized:
            return
        try:
            self._pool = ThreadedConnectionPool(
                self.config.pool_min,
                self.config.pool_max,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                client_encoding='UTF8',
                application_name='brain-odoo-adapter'
            )
            self._initialized = True
            logger.info(
                f"🎯 Odoo Connection Pool initialized: "
                f"{self.config.host}:{self.config.port}/{self.config.database}"
            )
        except psycopg2.OperationalError as e:
            logger.warning(f"⚠️ Odoo Connection Pool not available: {e}")
            self._pool = None
    
    @contextmanager
    def get_connection(self):
        """Kontext-Manager für eine Connection"""
        self._ensure_pool()
        if self._pool is None:
            raise RuntimeError("Odoo Connection pool not available")
        
        conn = None
        try:
            conn = self._pool.getconn()
            conn.autocommit = False
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Query failed: {e}")
            raise
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, cursor_factory=None):
        """Kontext-Manager für einen Cursor"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory or RealDictCursor)
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Führt eine Query aus und gibt Ergebnisse als List[Dict] zurück.
        
        Args:
            query: SQL Query (parametrized)
            params: Query Parameter (Tuple)
            fetch: Ob Ergebnisse abgerufen werden sollen
            
        Returns:
            List of dicts mit Spalten als Keys
        """
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            
            if not fetch:
                return []
            
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                results = cursor.fetchall()
                return [dict(zip(columns, row)) for row in results]
            
            return []
    
    def execute_scalar(self, query: str, params: Optional[Tuple] = None) -> Any:
        """Führt Query aus und gibt ersten Wert zurück"""
        results = self.execute_query(query, params, fetch=True)
        if results and results[0]:
            return list(results[0].values())[0]
        return None
    
    def execute_single(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Führt Query aus und gibt ersten Row zurück"""
        results = self.execute_query(query, params, fetch=True)
        return results[0] if results else None
    
    def test_connection(self) -> bool:
        """Testet die Connection"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                return result.get('test') == 1 if result else False
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def get_odoo_version(self) -> str:
        """Holt Odoo Version aus ir_config_parameter"""
        query = "SELECT value FROM ir_config_parameter WHERE key = 'database.version'"
        return self.execute_scalar(query) or "unknown"
    
    def close_all(self) -> None:
        """Schließt alle Connections"""
        if self._pool:
            self._pool.closeall()
            logger.info("🔌 Odoo Connection Pool closed")


# Global pool instance
_pool: Optional[OdooConnectionPool] = None


def get_odoo_pool(config: Optional[OdooAdapterConfig] = None) -> OdooConnectionPool:
    """Holt oder erstellt den globalen Connection Pool"""
    global _pool
    if _pool is None:
        _pool = OdooConnectionPool(config)
    return _pool


def reset_pool() -> None:
    """Resets den Connection Pool (für Tests)"""
    global _pool
    if _pool:
        _pool.close_all()
        _pool = None
