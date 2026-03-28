"""
Odoo Adapter Service
===================

Hauptservice für Odoo Integration.
Bietet Company Resolution, Accounting und Sales Adapter.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .config import OdooAdapterConfig, get_odoo_config
from .connection import OdooConnectionPool, get_odoo_pool

logger = logging.getLogger(__name__)


@dataclass
class Company:
    """Odoo Company Representation"""
    id: int
    name: str
    parent_id: Optional[int] = None
    currency_id: Optional[int] = None
    country_id: Optional[int] = None
    street: Optional[str] = None
    zip: Optional[str] = None
    city: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Company":
        return cls(
            id=data.get("id", 0),
            name=data.get("name", ""),
            parent_id=data.get("parent_id"),
            currency_id=data.get("currency_id"),
            country_id=data.get("country_id"),
            street=data.get("street"),
            zip=data.get("zip"),
            city=data.get("city"),
        )


class CompanyResolver:
    """
    Company Resolution für Multi-Company Setup.
    """
    
    def __init__(self, pool: OdooConnectionPool):
        self.pool = pool
    
    def get_all(self) -> List[Company]:
        """Alle Firmen abrufen"""
        query = """
            SELECT id, name, parent_id, currency_id, country_id, street, zip, city
            FROM res_company
            ORDER BY name
        """
        results = self.pool.execute_query(query)
        return [Company.from_dict(r) for r in results]
    
    def get_by_id(self, company_id: int) -> Optional[Company]:
        """Firma nach ID abrufen"""
        query = """
            SELECT id, name, parent_id, currency_id, country_id, street, zip, city
            FROM res_company
            WHERE id = %s
        """
        result = self.pool.execute_single(query, (company_id,))
        return Company.from_dict(result) if result else None
    
    def get_by_name(self, name: str) -> Optional[Company]:
        """Firma nach Name suchen"""
        query = """
            SELECT id, name, parent_id, currency_id, country_id, street, zip, city
            FROM res_company
            WHERE name ILIKE %s
            LIMIT 1
        """
        result = self.pool.execute_single(query, (f"%{name}%",))
        return Company.from_dict(result) if result else None
    
    def get_children(self, parent_id: int) -> List[Company]:
        """Tochterfirmen abrufen"""
        query = """
            SELECT id, name, parent_id, currency_id, country_id, street, zip, city
            FROM res_company
            WHERE parent_id = %s
            ORDER BY name
        """
        results = self.pool.execute_query(query, (parent_id,))
        return [Company.from_dict(r) for r in results]
    
    def get_root_companies(self) -> List[Company]:
        """Root-Firmen (ohne Parent) abrufen"""
        query = """
            SELECT id, name, parent_id, currency_id, country_id, street, zip, city
            FROM res_company
            WHERE parent_id IS NULL
            ORDER BY name
        """
        results = self.pool.execute_query(query)
        return [Company.from_dict(r) for r in results]


class AccountingAdapter:
    """
    Adapter für Odoo Buchhaltung.
    """
    
    def __init__(self, pool: OdooConnectionPool, company_id: int):
        self.pool = pool
        self.company_id = company_id
    
    def create_invoice(
        self,
        partner_id: int,
        lines: List[Dict[str, Any]],
        invoice_date: Optional[str] = None,
        due_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Rechnung erstellen (Draft)"""
        today = invoice_date or datetime.now().strftime("%Y-%m-%d")
        
        # Generate invoice number
        query = """
            SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
            FROM account_move
            WHERE move_type = 'out_invoice'
            AND company_id = %s
            AND name LIKE %s
        """
        result = self.pool.execute_scalar(
            query,
            (self.company_id, f"INV/{datetime.now().year}/%")
        )
        seq = result or 1
        invoice_name = f"INV/{datetime.now().year}/{seq:04d}"
        
        # Create invoice header
        query = """
            INSERT INTO account_move (
                name, partner_id, move_type, invoice_date,
                company_id, state, create_uid, create_date
            ) VALUES (
                %s, %s, 'out_invoice', %s,
                %s, 'draft', 1, NOW()
            )
            RETURNING id
        """
        invoice_id = self.pool.execute_scalar(
            query,
            (invoice_name, partner_id, today, self.company_id)
        )
        
        if not invoice_id:
            raise RuntimeError("Failed to create invoice")
        
        # Add invoice lines
        for line in lines:
            self._add_invoice_line(invoice_id, line)
        
        return {
            "invoice_id": invoice_id,
            "name": invoice_name,
            "state": "draft",
        }
    
    def _add_invoice_line(self, invoice_id: int, line: Dict[str, Any]):
        """Rechnungsposition hinzufügen"""
        product_id = line.get("product_id")
        quantity = line.get("quantity", 1)
        price_unit = line.get("price_unit", 0)
        
        # Get account from product
        query = """
            SELECT property_account_income_id
            FROM product_product pp
            JOIN product_template pt ON pp.product_tmpl_id = pt.id
            WHERE pp.id = %s
        """
        account_id = self.pool.execute_scalar(query, (product_id,))
        
        if not account_id:
            # Default to 400000 (Revenue)
            query = "SELECT id FROM account_account WHERE code = '400000' LIMIT 1"
            account_id = self.pool.execute_scalar(query)
        
        amount = quantity * price_unit
        
        query = """
            INSERT INTO account_move_line (
                move_id, account_id, partner_id, name,
                quantity, price_unit, company_id, debit, credit
            ) VALUES (
                %s, %s, (SELECT partner_id FROM account_move WHERE id = %s),
                %s, %s, %s, %s, %s, 0
            )
        """
        self.pool.execute_query(
            query,
            (account_id, invoice_id, line.get("name", "Position"),
             quantity, price_unit, self.company_id, amount)
        )
    
    def get_invoices(
        self,
        state: Optional[str] = None,
        partner_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Rechnungen abrufen"""
        query = """
            SELECT 
                am.id, am.name, am.invoice_date, am.invoice_date_due,
                am.amount_total, am.amount_residual, am.state,
                rp.name as partner_name
            FROM account_move am
            LEFT JOIN res_partner rp ON am.partner_id = rp.id
            WHERE am.move_type = 'out_invoice'
            AND am.company_id = %s
        """
        params = [self.company_id]
        
        if state:
            query += " AND am.state = %s"
            params.append(state)
        
        if partner_id:
            query += " AND am.partner_id = %s"
            params.append(partner_id)
        
        query += " ORDER BY am.invoice_date DESC LIMIT %s"
        params.append(limit)
        
        return self.pool.execute_query(query, tuple(params))
    
    def get_open_invoices(self, partner_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Offene Rechnungen abrufen"""
        return self.get_invoices(state="posted", partner_id=partner_id)


class SalesAdapter:
    """
    Adapter für Odoo Vertrieb.
    """
    
    def __init__(self, pool: OdooConnectionPool, company_id: int):
        self.pool = pool
        self.company_id = company_id
    
    def create_partner(
        self,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        customer: bool = True,
    ) -> int:
        """Kunde/Lieferant erstellen"""
        query = """
            INSERT INTO res_partner (
                name, email, phone, customer, supplier,
                company_id, create_uid, create_date
            ) VALUES (
                %s, %s, %s, %s, %s, %s, 1, NOW()
            )
            RETURNING id
        """
        partner_id = self.pool.execute_scalar(
            query,
            (name, email, phone, customer, not customer, self.company_id)
        )
        return partner_id
    
    def search_partners(
        self,
        query: str = "",
        customer: bool = True,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Partner suchen"""
        sql = """
            SELECT id, name, email, phone, customer, supplier
            FROM res_partner
            WHERE company_id IN (SELECT id FROM res_company WHERE parent_path LIKE %s)
        """
        params = [f"%/{self.company_id}/%"]
        
        if customer:
            sql += " AND customer = true"
        
        if query:
            sql += " AND (name ILIKE %s OR email ILIKE %s)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        sql += " ORDER BY name LIMIT %s"
        params.append(limit)
        
        return self.pool.execute_query(sql, tuple(params))
    
    def create_order(
        self,
        partner_id: int,
        lines: List[Dict[str, Any]],
    ) -> int:
        """Auftrag erstellen"""
        query = """
            INSERT INTO sale_order (
                partner_id, state, company_id, date_order,
                create_uid, create_date
            ) VALUES (
                %s, 'draft', %s, NOW(), 1, NOW()
            )
            RETURNING id
        """
        order_id = self.pool.execute_scalar(query, (partner_id, self.company_id))
        
        # Add order lines
        for line in lines:
            self._add_order_line(order_id, line)
        
        return order_id
    
    def _add_order_line(self, order_id: int, line: Dict[str, Any]):
        """Auftragsposition hinzufügen"""
        query = """
            INSERT INTO sale_order_line (
                order_id, name, product_id, product_uom_qty,
                price_unit, company_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
        """
        self.pool.execute_query(
            query,
            (order_id, line.get("name", "Position"),
             line.get("product_id"), line.get("quantity", 1),
             line.get("price_unit", 0), self.company_id)
        )
    
    def confirm_order(self, order_id: int) -> bool:
        """Auftrag bestätigen"""
        query = """
            UPDATE sale_order
            SET state = 'sale', commit_confirmation_date = NOW()
            WHERE id = %s AND state = 'draft'
        """
        self.pool.execute_query(query, (order_id,))
        return True


class OdooAdapter:
    """
    Hauptdapter für Odoo Integration.
    """
    
    def __init__(self, pool: Optional[OdooConnectionPool] = None):
        self.pool = pool or get_odoo_pool()
        self.company_resolver = CompanyResolver(self.pool)
    
    def accounting(self, company_id: int) -> AccountingAdapter:
        """Erstellt Accounting Adapter für eine Firma"""
        return AccountingAdapter(self.pool, company_id)
    
    def sales(self, company_id: int) -> SalesAdapter:
        """Erstellt Sales Adapter für eine Firma"""
        return SalesAdapter(self.pool, company_id)
    
    def test_connection(self) -> Dict[str, Any]:
        """Testet die Verbindung"""
        try:
            connected = self.pool.test_connection()
            version = self.pool.get_odoo_version() if connected else None
            return {
                "connected": connected,
                "version": version,
                "companies": len(self.company_resolver.get_all()),
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
            }


# Global adapter instance
_adapter: Optional[OdooAdapter] = None


def get_odoo_adapter() -> OdooAdapter:
    """Holt oder erstellt den globalen Adapter"""
    global _adapter
    if _adapter is None:
        _adapter = OdooAdapter()
    return _adapter


class ManufacturingAdapter:
    """
    Adapter für Odoo Fertigung.
    """
    
    def __init__(self, pool: OdooConnectionPool, company_id: int):
        self.pool = pool
        self.company_id = company_id
    
    def create_bom(
        self,
        product_id: int,
        lines: List[Dict[str, Any]],
    ) -> int:
        """Stückliste (BoM) erstellen"""
        query = """
            INSERT INTO mrp_bom (
                product_id, product_tmpl_id, company_id,
                create_uid, create_date
            ) VALUES (
                %s, (SELECT product_tmpl_id FROM product_product WHERE id = %s),
                %s, 1, NOW()
            )
            RETURNING id
        """
        bom_id = self.pool.execute_scalar(query, (product_id, product_id, self.company_id))
        
        for line in lines:
            self._add_bom_line(bom_id, line)
        
        return bom_id
    
    def _add_bom_line(self, bom_id: int, line: Dict[str, Any]):
        """BoM Position hinzufügen"""
        query = """
            INSERT INTO mrp_bom_line (
                bom_id, product_id, product_qty, company_id
            ) VALUES (%s, %s, %s, %s)
        """
        self.pool.execute_query(
            query,
            (bom_id, line.get("product_id"), line.get("quantity", 1), self.company_id)
        )
    
    def create_workorder(
        self,
        product_id: int,
        quantity: int = 1,
    ) -> int:
        """Fertigungsauftrag erstellen"""
        query = """
            INSERT INTO mrp_production (
                product_id, product_qty, company_id,
                state, date_planned_start, create_uid, create_date
            ) VALUES (%s, %s, %s, 'draft', NOW(), 1, NOW())
            RETURNING id
        """
        return self.pool.execute_scalar(
            query,
            (product_id, quantity, self.company_id)
        )
    
    def get_workorders(
        self,
        state: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fertigungsaufträge abrufen"""
        query = """
            SELECT mp.id, mp.name, mp.product_qty, mp.state,
                   mp.date_planned_start, mp.date_finished,
                   pp.name_template as product_name
            FROM mrp_production mp
            JOIN product_product pp ON mp.product_id = pp.id
            WHERE mp.company_id = %s
        """
        params = [self.company_id]
        
        if state:
            query += " AND mp.state = %s"
            params.append(state)
        
        query += " ORDER BY mp.date_planned_start DESC LIMIT %s"
        params.append(limit)
        
        return self.pool.execute_query(query, tuple(params))


class InventoryAdapter:
    """
    Adapter für Odoo Lagerverwaltung.
    """
    
    def __init__(self, pool: OdooConnectionPool, company_id: int):
        self.pool = pool
        self.company_id = company_id
    
    def get_stock(self, product_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Lagerbestände abrufen"""
        query = """
            SELECT 
                sm.product_id, pp.name_template as product_name,
                sm.location_id, sl.name as location_name,
                SUM(sm.quantity) as quantity
            FROM stock_quant sq
            JOIN stock_move sm ON sq.product_id = sm.product_id
            JOIN product_product pp ON sm.product_id = pp.id
            JOIN stock_location sl ON sm.location_id = sl.id
            WHERE sm.company_id = %s
        """
        params = [self.company_id]
        
        if product_id:
            query += " AND sm.product_id = %s"
            params.append(product_id)
        
        query += " GROUP BY sm.product_id, pp.name_template, sm.location_id, sl.name ORDER BY quantity DESC"
        
        return self.pool.execute_query(query, tuple(params))
    
    def create_receipt(
        self,
        partner_id: int,
        lines: List[Dict[str, Any]],
    ) -> int:
        """Wareneingang erstellen"""
        query = """
            INSERT INTO stock_picking (
                partner_id, picking_type_id, location_id, location_dest_id,
                company_id, state, create_uid, create_date
            ) VALUES (
                %s, 1, 
                (SELECT id FROM stock_location WHERE usage = 'supplier' LIMIT 1),
                (SELECT id FROM stock_location WHERE usage = 'internal' LIMIT 1),
                %s, 'draft', 1, NOW()
            )
            RETURNING id
        """
        picking_id = self.pool.execute_scalar(query, (partner_id, self.company_id))
        
        for line in lines:
            self._add_picking_line(picking_id, line)
        
        return picking_id
    
    def _add_picking_line(self, picking_id: int, line: Dict[str, Any]):
        """Picking Position hinzufügen"""
        query = """
            INSERT INTO stock_move (
                picking_id, product_id, product_uom_qty,
                location_id, location_dest_id, company_id, state,
                create_uid, create_date
            ) VALUES (
                %s, %s, %s,
                (SELECT id FROM stock_location WHERE usage = 'supplier' LIMIT 1),
                (SELECT id FROM stock_location WHERE usage = 'internal' LIMIT 1),
                %s, 'draft', 1, NOW()
            )
        """
        self.pool.execute_query(
            query,
            (picking_id, line.get("product_id"), line.get("quantity", 1), self.company_id)
        )
    
    def create_transfer(
        self,
        location_from: int,
        location_to: int,
        lines: List[Dict[str, Any]],
    ) -> int:
        """Lagerumschlag erstellen"""
        query = """
            INSERT INTO stock_picking (
                picking_type_id, location_id, location_dest_id,
                company_id, state, create_uid, create_date
            ) VALUES (
                5, %s, %s, %s, 'draft', 1, NOW()
            )
            RETURNING id
        """
        picking_id = self.pool.execute_scalar(query, (location_from, location_to, self.company_id))
        
        for line in lines:
            query = """
                INSERT INTO stock_move (
                    picking_id, product_id, product_uom_qty,
                    location_id, location_dest_id, company_id, state
                ) VALUES (%s, %s, %s, %s, %s, %s, 'draft')
            """
            self.pool.execute_query(
                query,
                (picking_id, line.get("product_id"), line.get("quantity", 1),
                 location_from, location_to, self.company_id)
            )
        
        return picking_id


class PurchaseAdapter:
    """
    Adapter für Odoo Einkauf.
    """
    
    def __init__(self, pool: OdooConnectionPool, company_id: int):
        self.pool = pool
        self.company_id = company_id
    
    def create_order(
        self,
        partner_id: int,
        lines: List[Dict[str, Any]],
    ) -> int:
        """Bestellung erstellen"""
        query = """
            INSERT INTO purchase_order (
                partner_id, company_id, state, date_order,
                create_uid, create_date
            ) VALUES (%s, %s, 'draft', NOW(), 1, NOW())
            RETURNING id
        """
        order_id = self.pool.execute_scalar(query, (partner_id, self.company_id))
        
        for line in lines:
            self._add_order_line(order_id, line)
        
        return order_id
    
    def _add_order_line(self, order_id: int, line: Dict[str, Any]):
        """Bestellposition hinzufügen"""
        query = """
            INSERT INTO purchase_order_line (
                order_id, product_id, product_qty, price_unit,
                company_id, date_planned
            ) VALUES (%s, %s, %s, %s, %s, NOW())
        """
        self.pool.execute_query(
            query,
            (order_id, line.get("product_id"), line.get("quantity", 1),
             line.get("price_unit", 0), self.company_id)
        )
    
    def confirm_order(self, order_id: int) -> bool:
        """Bestellung bestätigen"""
        query = """
            UPDATE purchase_order
            SET state = 'purchase', write_uid = 1, write_date = NOW()
            WHERE id = %s AND state = 'draft'
        """
        self.pool.execute_query(query, (order_id,))
        return True
    
    def get_orders(
        self,
        state: Optional[str] = None,
        partner_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Bestellungen abrufen"""
        query = """
            SELECT po.id, po.name, po.date_order, po.state,
                   po.amount_total, rp.name as partner_name
            FROM purchase_order po
            LEFT JOIN res_partner rp ON po.partner_id = rp.id
            WHERE po.company_id = %s
        """
        params = [self.company_id]
        
        if state:
            query += " AND po.state = %s"
            params.append(state)
        
        if partner_id:
            query += " AND po.partner_id = %s"
            params.append(partner_id)
        
        query += " ORDER BY po.date_order DESC LIMIT %s"
        params.append(limit)
        
        return self.pool.execute_query(query, tuple(params))


class OdooSkillsRegistry:
    """
    Registry für Odoo Skills.
    Macht Odoo Operationen als BRAiN Skills verfügbar.
    """
    
    DEFAULT_SKILLS = [
        {
            "skill_key": "odoo.invoice.create",
            "odoo_model": "account.move",
            "odoo_method": "create",
            "description": "Create invoice in Odoo",
            "input_schema": {
                "type": "object",
                "properties": {
                    "partner_id": {"type": "integer"},
                    "lines": {"type": "array"},
                    "invoice_date": {"type": "string"},
                },
                "required": ["partner_id", "lines"],
            },
            "risk_tier": "medium",
        },
        {
            "skill_key": "odoo.invoice.list",
            "odoo_model": "account.move",
            "odoo_method": "search_read",
            "description": "List invoices from Odoo",
            "input_schema": {
                "type": "object",
                "properties": {
                    "state": {"type": "string"},
                    "partner_id": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
            },
            "risk_tier": "low",
        },
        {
            "skill_key": "odoo.partner.create",
            "odoo_model": "res.partner",
            "odoo_method": "create",
            "description": "Create customer/supplier in Odoo",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "customer": {"type": "boolean"},
                },
                "required": ["name"],
            },
            "risk_tier": "medium",
        },
        {
            "skill_key": "odoo.partner.search",
            "odoo_model": "res.partner",
            "odoo_method": "search_read",
            "description": "Search partners in Odoo",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "customer": {"type": "boolean"},
                    "limit": {"type": "integer"},
                },
            },
            "risk_tier": "low",
        },
        {
            "skill_key": "odoo.order.create",
            "odoo_model": "sale.order",
            "odoo_method": "create",
            "description": "Create sales order in Odoo",
            "input_schema": {
                "type": "object",
                "properties": {
                    "partner_id": {"type": "integer"},
                    "lines": {"type": "array"},
                },
                "required": ["partner_id", "lines"],
            },
            "risk_tier": "medium",
        },
        {
            "skill_key": "odoo.order.confirm",
            "odoo_model": "sale.order",
            "odoo_method": "action_confirm",
            "description": "Confirm sales order in Odoo",
            "input_schema": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                },
                "required": ["order_id"],
            },
            "risk_tier": "high",
        },
        {
            "skill_key": "odoo.company.list",
            "odoo_model": "res.company",
            "odoo_method": "search_read",
            "description": "List companies from Odoo",
            "input_schema": {
                "type": "object",
                "properties": {
                    "root_only": {"type": "boolean"},
                },
            },
            "risk_tier": "low",
        },
    ]
    
    @classmethod
    def get_all_skills(cls) -> List[Dict[str, Any]]:
        """Alle verfügbaren Odoo Skills zurückgeben"""
        return cls.DEFAULT_SKILLS
    
    @classmethod
    def get_skill(cls, skill_key: str) -> Optional[Dict[str, Any]]:
        """Skill nach Key holen"""
        for skill in cls.DEFAULT_SKILLS:
            if skill["skill_key"] == skill_key:
                return skill
        return None
    
    @classmethod
    async def execute_skill(
        cls,
        skill_key: str,
        payload: Dict[str, Any],
        pool: "OdooConnectionPool",
        company_id: int,
        log_execution: bool = True,
    ) -> Dict[str, Any]:
        """Führt einen Odoo Skill aus"""
        import time
        start_time = time.time()
        
        skill = cls.get_skill(skill_key)
        if not skill:
            return {"error": f"Skill {skill_key} not found"}
        
        model = skill["odoo_model"]
        method = skill["odoo_method"]
        success = True
        error_msg = None
        result = None
        
        try:
            if model == "account.move":
                adapter = AccountingAdapter(pool, company_id)
                if method == "create":
                    result = adapter.create_invoice(
                        partner_id=payload.get("partner_id"),
                        lines=payload.get("lines", []),
                        invoice_date=payload.get("invoice_date"),
                    )
                elif method == "search_read":
                    result = adapter.get_invoices(
                        state=payload.get("state"),
                        partner_id=payload.get("partner_id"),
                        limit=payload.get("limit", 100),
                    )
            
            elif model == "res.partner":
                adapter = SalesAdapter(pool, company_id)
                if method == "create":
                    partner_id = adapter.create_partner(
                        name=payload.get("name"),
                        email=payload.get("email"),
                        phone=payload.get("phone"),
                        customer=payload.get("customer", True),
                    )
                    result = {"partner_id": partner_id}
                elif method == "search_read":
                    result = adapter.search_partners(
                        query=payload.get("query", ""),
                        customer=payload.get("customer", True),
                        limit=payload.get("limit", 50),
                    )
            
            elif model == "sale.order":
                adapter = SalesAdapter(pool, company_id)
                if method == "create":
                    order_id = adapter.create_order(
                        partner_id=payload.get("partner_id"),
                        lines=payload.get("lines", []),
                    )
                    result = {"order_id": order_id}
                elif method == "action_confirm":
                    result = adapter.confirm_order(payload.get("order_id"))
                    result = {"confirmed": result}
            
            elif model == "res.company":
                resolver = CompanyResolver(pool)
                if method == "search_read":
                    if payload.get("root_only"):
                        companies = resolver.get_root_companies()
                    else:
                        companies = resolver.get_all()
                    result = [{"id": c.id, "name": c.name} for c in companies]
            
            else:
                result = {"error": f"Unknown model/method: {model}.{method}"}
        
        except Exception as e:
            success = False
            error_msg = str(e)
            result = {"error": error_msg}
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        if log_execution:
            await cls._log_execution(
                skill_key=skill_key,
                model=model,
                method=method,
                company_id=company_id,
                input_data=payload,
                output_data=result,
                success=success,
                error_message=error_msg,
                execution_time_ms=execution_time_ms,
            )
        
        return result
    
    @classmethod
    async def _log_execution(
        cls,
        skill_key: str,
        model: str,
        method: str,
        company_id: int,
        input_data: Dict,
        output_data: Dict,
        success: bool,
        error_message: Optional[str],
        execution_time_ms: int,
    ) -> None:
        """Loggt Odoo Skill Execution für Learning Loop"""
        logger.info(
            f"Odoo skill executed: {skill_key} "
            f"(model={model}, method={method}, company={company_id}, "
            f"success={success}, time={execution_time_ms}ms)"
        )
