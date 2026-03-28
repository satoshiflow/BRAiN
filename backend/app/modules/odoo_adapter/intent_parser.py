"""
Odoo Intent Parser für AXE Chat
===============================

Erkennt Odoo-Operationen in natürlicher Sprache und führt sie aus.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OdooIntent:
    """Repräsentiert einen erkannten Odoo Intent"""
    
    def __init__(
        self,
        skill_key: str,
        action: str,
        confidence: float,
        entities: Dict[str, Any],
        response_template: str,
    ):
        self.skill_key = skill_key
        self.action = action
        self.confidence = confidence
        self.entities = entities
        self.response_template = response_template


class OdooIntentParser:
    """
    Parser für Odoo-Commands im AXE Chat.
    
    ErkenntPatterns wie:
    - "erstelle Rechnung für Kunde X"
    - "zeige offene Rechnungen"
    - "neuer Kunde: Max Mustermann"
    - "bestätige Auftrag 12345"
    """
    
    # Intent Patterns - German
    INTENT_PATTERNS = [
        # Invoice patterns
        (
            r"erstelle?\s+(?:eine\s+)?rechnung(?:ung)?\s+(?:für|an)\s+(?:kunde\s+)?(.+)",
            "invoice_create",
            "invoice",
            "create",
            0.9,
            "Rechnung {partner} wird erstellt",
        ),
        (
            r"rechnung(?:ung)?\s+erstellen\s+(?:für|an)\s+(?:kunde\s+)?(.+)",
            "invoice_create",
            "invoice",
            "create",
            0.95,
            "Rechnung für {partner} wird erstellt",
        ),
        (
            r"zeige?\s+(?:mir\s+)?(?:die\s+)?offenen?\s+rechnung(?:en)?",
            "invoice_list_open",
            "invoice",
            "list_open",
            0.85,
            "Hier sind die offenen Rechnungen",
        ),
        (
            r"zeige?\s+(?:mir\s+)?(?:die\s+)?rechnung(?:en)?(?:\s+von\s+(.+))?",
            "invoice_list",
            "invoice",
            "list",
            0.8,
            "Hier sind die Rechnungen",
        ),
        
        # Partner/Customer patterns
        (
            r"(?:neuer\s+)?kunde(?:\s+|:)\s*(.+)",
            "partner_create",
            "partner",
            "create",
            0.9,
            "Kunde {partner} wird erstellt",
        ),
        (
            r"erstelle?\s+(?:einen\s+)?(?:neuen\s+)?kunden(?:\s+|:)\s*(.+)",
            "partner_create",
            "partner",
            "create",
            0.95,
            "Kunde {partner} wird erstellt",
        ),
        (
            r"suche?\s+(?:nach\s+)?kunde(?:\s+|:)\s*(.+)",
            "partner_search",
            "partner",
            "search",
            0.85,
            "Suche nach Kunde {partner}",
        ),
        (
            r"zeige?\s+(?:mir\s+)?(?:die\s+)?kunden",
            "partner_list",
            "partner",
            "list",
            0.8,
            "Hier sind die Kunden",
        ),
        
        # Order patterns
        (
            r"erstelle?\s+(?:einen\s+)?auftrag(?:\s+|:)\s*(?:für\s+)?(.+)",
            "order_create",
            "order",
            "create",
            0.9,
            "Auftrag für {partner} wird erstellt",
        ),
        (
            r"bestätige?\s+(?:den\s+)?auftrag\s*(?:nr\.?|nummer|#)?\s*(\d+)",
            "order_confirm",
            "order",
            "confirm",
            0.95,
            "Auftrag #{order_id} wird bestätigt",
        ),
        (
            r"zeige?\s+(?:mir\s+)?(?:die\s+)?aufträge",
            "order_list",
            "order",
            "list",
            0.8,
            "Hier sind die Aufträge",
        ),
        
        # Purchase patterns
        (
            r"erstelle?\s+(?:eine\s+)?bestellung(?:\s+|:)\s*(?:bei\s+)?(.+)",
            "purchase_create",
            "purchase",
            "create",
            0.9,
            "Bestellung bei {partner} wird erstellt",
        ),
        (
            r"zeige?\s+(?:mir\s+)?(?:die\s+)?bestellungen",
            "purchase_list",
            "purchase",
            "list",
            0.8,
            "Hier sind die Bestellungen",
        ),
        
        # Manufacturing patterns
        (
            r"erstelle?\s+(?:einen\s+)?fertigungsauftrag(?:\s+|:)\s*(?:für\s+)?(.+)",
            "workorder_create",
            "manufacturing",
            "workorder_create",
            0.9,
            "Fertigungsauftrag für {product} wird erstellt",
        ),
        (
            r"zeige?\s+(?:mir\s+)?(?:die\s+)?fertigungsaufträge",
            "workorder_list",
            "manufacturing",
            "list",
            0.8,
            "Hier sind die Fertigungsaufträge",
        ),
        
        # Inventory patterns
        (
            r"zeige?\s+(?:mir\s+)?(?:den\s+)?lagerbestand(?:\s+von\s+(.+))?",
            "stock_list",
            "inventory",
            "stock",
            0.85,
            "Hier ist der Lagerbestand",
        ),
        
        # Company patterns
        (
            r"zeige?\s+(?:mir\s+)?(?:die\s+)?unternehmen",
            "company_list",
            "company",
            "list",
            0.9,
            "Hier sind die Unternehmen",
        ),
        
        # Help patterns
        (
            r"(?:was|kannst du|help|hilfe)\s+(?:kannst du|can you)\s+mit\s+odoo",
            "help",
            "system",
            "help",
            1.0,
            "help",
        ),
    ]
    
    # Skill mappings
    SKILL_MAPPINGS = {
        "invoice_create": {
            "skill_key": "odoo.invoice.create",
            "requires": ["partner_id"],
        },
        "invoice_list_open": {
            "skill_key": "odoo.invoice.list",
            "params": {"state": "open"},
        },
        "invoice_list": {
            "skill_key": "odoo.invoice.list",
        },
        "partner_create": {
            "skill_key": "odoo.partner.create",
            "requires": ["name"],
        },
        "partner_search": {
            "skill_key": "odoo.partner.search",
            "requires": ["query"],
        },
        "partner_list": {
            "skill_key": "odoo.partner.search",
            "params": {"customer": True},
        },
        "order_create": {
            "skill_key": "odoo.order.create",
            "requires": ["partner_id"],
        },
        "order_confirm": {
            "skill_key": "odoo.order.confirm",
            "requires": ["order_id"],
        },
        "order_list": {
            "skill_key": "odoo.order.list",
        },
        "purchase_create": {
            "skill_key": "odoo.purchase.create",
            "requires": ["partner_id"],
        },
        "purchase_list": {
            "skill_key": "odoo.purchase.list",
        },
        "workorder_create": {
            "skill_key": "odoo.workorder.create",
            "requires": ["product_id"],
        },
        "workorder_list": {
            "skill_key": "odoo.workorder.list",
        },
        "stock_list": {
            "skill_key": "odoo.inventory.stock",
        },
        "company_list": {
            "skill_key": "odoo.company.list",
        },
    }
    
    HELP_TEXT = """
Ich kann dir bei folgenden Odoo-Operationen helfen:

📄 **Rechnungen**
- "zeige mir offene Rechnungen"
- "erstelle Rechnung für Kunde Acme"

👥 **Kunden**
- "zeige mir die Kunden"
- "neuer Kunde: Max Mustermann"
- "suche Kunde Müller"

📦 **Aufträge**
- "zeige mir die Aufträge"
- "erstelle Auftrag für Kunde X"
- "bestätige Auftrag 12345"

🏭 **Fertigung**
- "zeige mir die Fertigungsaufträge"
- "erstelle Fertigungsauftrag für Produkt X"

📦 **Lager**
- "zeige mir den Lagerbestand"

🏢 **Unternehmen**
- "zeige mir die Unternehmen"

Sag mir einfach, was du tun möchtest!
"""
    
    def __init__(self):
        self._patterns = self.INTENT_PATTERNS
    
    def parse(self, message: str) -> Optional[OdooIntent]:
        """
        Parst eine Benutzernachricht und erkennt Odoo-Intents.
        
        Args:
            message: Die Benutzernachricht
            
        Returns:
            OdooIntent oder None wenn kein Intent erkannt wurde
        """
        message_lower = message.lower().strip()
        
        for pattern, intent_name, _, action, confidence, response_template in self._patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                entities = {}
                if match.groups():
                    # Extract entities from regex groups
                    if intent_name in ["invoice_create", "partner_create", "partner_search", 
                                       "order_create", "purchase_create", "workorder_create"]:
                        entities["name"] = match.group(1).strip()
                    elif intent_name == "order_confirm":
                        entities["order_id"] = match.group(1).strip()
                    elif intent_name == "invoice_list":
                        partner = match.group(1).strip() if match.group(1) else None
                        if partner:
                            entities["partner"] = partner
                
                return OdooIntent(
                    skill_key=intent_name,
                    action=action,
                    confidence=confidence,
                    entities=entities,
                    response_template=response_template,
                )
        
        return None
    
    def get_skill_payload(self, intent: OdooIntent) -> Dict[str, Any]:
        """Erstellt das Payload für den Odoo Skill"""
        mapping = self.SKILL_MAPPINGS.get(intent.skill_key, {})
        
        payload = mapping.get("params", {}).copy()
        
        # Add entity values
        for key, value in intent.entities.items():
            payload[key] = value
        
        return payload
    
    def format_response(self, intent: OdooIntent, result: Any) -> str:
        """Formatiert das Ergebnis für die Chat-Antwort"""
        if intent.skill_key == "help":
            return self.HELP_TEXT
        
        # Default success response
        if isinstance(result, dict):
            if "error" in result:
                return f"❌ Fehler: {result['error']}"
            
            # Format based on result type
            if "invoice_id" in result or "name" in result:
                return f"✅ Erfolgreich ausgeführt!"
            elif isinstance(result, list):
                if len(result) == 0:
                    return "Keine Ergebnisse gefunden."
                return f"✅ {len(result)} Ergebnisse gefunden."
        
        return "✅ Aktion erfolgreich ausgeführt!"
    
    def is_odoo_command(self, message: str) -> bool:
        """Prüft ob die Nachricht ein Odoo-Command ist"""
        return self.parse(message) is not None


# Global instance
_parser: Optional[OdooIntentParser] = None


def get_odoo_intent_parser() -> OdooIntentParser:
    """Holt den globalen Intent Parser"""
    global _parser
    if _parser is None:
        _parser = OdooIntentParser()
    return _parser
