"""
Odoo Bridge für AXE Chat
========================

Integriert Odoo-Commands in den AXE Chat Flow.
"""

import logging
from typing import Any, Dict, Optional

from app.modules.odoo_adapter.config import get_odoo_config
from app.modules.odoo_adapter.connection import get_odoo_pool
from app.modules.odoo_adapter.intent_parser import (
    OdooIntentParser,
    get_odoo_intent_parser,
)
from app.modules.odoo_adapter.service import OdooSkillsRegistry

logger = logging.getLogger(__name__)


class OdooChatBridge:
    """
    Bridge zwischen AXE Chat und Odoo.
    
    Fängt Odoo-Commands ab und führt sie direkt aus,
    ohne den LLM zu bemühen.
    """
    
    def __init__(self):
        self.parser = get_odoo_intent_parser()
    
    async def handle_message(self, message: str) -> Optional[str]:
        """
        Prüft ob die Nachricht ein Odoo-Command ist und führt ihn aus.
        
        Args:
            message: Die Benutzernachricht
            
        Returns:
            Antwort-Text wenn Odoo-Command erkannt, sonst None
        """
        # Check if it's an Odoo command
        intent = self.parser.parse(message)
        if not intent:
            return None
        
        logger.info(f"🎯 Odoo Intent erkannt: {intent.skill_key}")
        
        try:
            # Get Odoo resources
            config = get_odoo_config()
            pool = get_odoo_pool()
            
            if pool._pool is None:
                return "❌ Odoo ist nicht konfiguriert. Bitte configure die Odoo-Verbindung."
            
            # Build skill payload
            payload = self.parser.get_skill_payload(intent)
            
            # Map intent to actual skill key
            skill_mapping = {
                "invoice_create": "odoo.invoice.create",
                "invoice_list_open": "odoo.invoice.list",
                "invoice_list": "odoo.invoice.list",
                "partner_create": "odoo.partner.create",
                "partner_search": "odoo.partner.search",
                "partner_list": "odoo.partner.search",
                "order_create": "odoo.order.create",
                "order_confirm": "odoo.order.confirm",
                "order_list": "odoo.order.list",
                "purchase_create": "odoo.purchase.create",
                "purchase_list": "odoo.purchase.list",
                "workorder_create": "odoo.manufacturing.workorder",
                "workorder_list": "odoo.manufacturing.workorders",
                "stock_list": "odoo.inventory.stock",
                "company_list": "odoo.company.list",
            }
            
            skill_key = skill_mapping.get(intent.skill_key, intent.skill_key)
            
            if intent.skill_key == "help":
                return self.parser.HELP_TEXT
            
            # Execute skill
            result = await OdooSkillsRegistry.execute_skill(
                skill_key=skill_key,
                payload=payload,
                pool=pool,
                company_id=config.default_company_id,
            )
            
            # Format response
            response = self.parser.format_response(intent, result)
            return response
            
        except Exception as e:
            logger.error(f"❌ Odoo Command failed: {e}")
            return f"❌ Fehler bei der Odoo-Operation: {str(e)}"
    
    def is_odoo_command(self, message: str) -> bool:
        """Prüft ob die Nachricht ein Odoo-Command ist"""
        return self.parser.is_odoo_command(message)


# Global instance
_bridge: Optional[OdooChatBridge] = None


def get_odoo_chat_bridge() -> OdooChatBridge:
    """Holt den globalen Odoo Chat Bridge"""
    global _bridge
    if _bridge is None:
        _bridge = OdooChatBridge()
    return _bridge
