"""
Odoo Adapter Router
===================

REST API Endpoints für Odoo Integration.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from .config import OdooAdapterConfig, get_odoo_config
from .connection import OdooConnectionPool, get_odoo_pool
from .service import Company, CompanyResolver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/odoo", tags=["odoo"])


class HealthResponse(BaseModel):
    status: str
    database: str
    companies: int


class CompanyResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
    currency_id: Optional[int] = None
    country_id: Optional[int] = None
    street: Optional[str] = None
    zip: Optional[str] = None
    city: Optional[str] = None

    class Config:
        from_attributes = True


def get_company_resolver(
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> CompanyResolver:
    return CompanyResolver(pool)


@router.get("/health", response_model=HealthResponse)
async def health_check(
    config: OdooAdapterConfig = Depends(get_odoo_config),
    resolver: CompanyResolver = Depends(get_company_resolver),
) -> HealthResponse:
    """
    Health Check für Odoo Adapter.
    """
    try:
        companies = resolver.get_all()
        return HealthResponse(
            status="healthy",
            database=config.database,
            companies=len(companies),
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Odoo database unavailable: {str(e)}",
        )


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    parent_id: Optional[int] = Query(None, description="Filter by parent company"),
    root_only: bool = Query(False, description="Only root companies"),
    resolver: CompanyResolver = Depends(get_company_resolver),
) -> list[CompanyResponse]:
    """
    Liste aller Odoo Firmen.
    """
    try:
        if root_only:
            companies = resolver.get_root_companies()
        elif parent_id is not None:
            companies = resolver.get_children(parent_id)
        else:
            companies = resolver.get_all()
        
        return [CompanyResponse.model_validate(c) for c in companies]
    except Exception as e:
        logger.error(f"Failed to list companies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch companies: {str(e)}",
        )


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    resolver: CompanyResolver = Depends(get_company_resolver),
) -> CompanyResponse:
    """
    Einzelne Firma nach ID abrufen.
    """
    company = resolver.get_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company {company_id} not found",
        )
    return CompanyResponse.model_validate(company)


@router.get("/companies/search/{name}", response_model=CompanyResponse)
async def search_company(
    name: str,
    resolver: CompanyResolver = Depends(get_company_resolver),
) -> CompanyResponse:
    """
    Firma nach Name suchen.
    """
    company = resolver.get_by_name(name)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company '{name}' not found",
        )
    return CompanyResponse.model_validate(company)


# =============================================================================
# Accounting Endpoints
# =============================================================================

class InvoiceCreateRequest(BaseModel):
    partner_id: int
    lines: list[dict]
    invoice_date: Optional[str] = None


class InvoiceResponse(BaseModel):
    invoice_id: int
    name: str
    state: str


@router.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(
    request: InvoiceCreateRequest,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> InvoiceResponse:
    """Rechnung erstellen"""
    from .service import AccountingAdapter
    
    config = get_odoo_config()
    adapter = AccountingAdapter(pool, config.default_company_id)
    
    result = adapter.create_invoice(
        partner_id=request.partner_id,
        lines=request.lines,
        invoice_date=request.invoice_date,
    )
    return InvoiceResponse(**result)


@router.get("/invoices")
async def list_invoices(
    state: Optional[str] = Query(None, description="Filter by state"),
    partner_id: Optional[int] = Query(None, description="Filter by partner"),
    limit: int = Query(100, le=500),
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> list[dict]:
    """Rechnungen auflisten"""
    from .service import AccountingAdapter
    
    config = get_odoo_config()
    adapter = AccountingAdapter(pool, config.default_company_id)
    
    return adapter.get_invoices(state=state, partner_id=partner_id, limit=limit)


@router.get("/invoices/open")
async def list_open_invoices(
    partner_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> list[dict]:
    """Offene Rechnungen abrufen"""
    from .service import AccountingAdapter
    
    config = get_odoo_config()
    adapter = AccountingAdapter(pool, config.default_company_id)
    
    return adapter.get_open_invoices(partner_id=partner_id)


# =============================================================================
# Sales Endpoints
# =============================================================================

class PartnerCreateRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    customer: bool = True


@router.post("/partners", response_model=dict)
async def create_partner(
    request: PartnerCreateRequest,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Kunde/Lieferant erstellen"""
    from .service import SalesAdapter
    
    config = get_odoo_config()
    adapter = SalesAdapter(pool, config.default_company_id)
    
    partner_id = adapter.create_partner(
        name=request.name,
        email=request.email,
        phone=request.phone,
        customer=request.customer,
    )
    return {"partner_id": partner_id, "name": request.name}


@router.get("/partners")
async def search_partners(
    q: str = Query("", description="Search query"),
    customer: bool = Query(True, description="Only customers"),
    limit: int = Query(50, le=200),
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> list[dict]:
    """Partner suchen"""
    from .service import SalesAdapter
    
    config = get_odoo_config()
    adapter = SalesAdapter(pool, config.default_company_id)
    
    return adapter.search_partners(query=q, customer=customer, limit=limit)


class OrderCreateRequest(BaseModel):
    partner_id: int
    lines: list[dict]


@router.post("/orders", response_model=dict)
async def create_order(
    request: OrderCreateRequest,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Auftrag erstellen"""
    from .service import SalesAdapter
    
    config = get_odoo_config()
    adapter = SalesAdapter(pool, config.default_company_id)
    
    order_id = adapter.create_order(
        partner_id=request.partner_id,
        lines=request.lines,
    )
    return {"order_id": order_id, "state": "draft"}


@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: int,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Auftrag bestätigen"""
    from .service import SalesAdapter
    
    config = get_odoo_config()
    adapter = SalesAdapter(pool, config.default_company_id)
    
    success = adapter.confirm_order(order_id)
    return {"order_id": order_id, "confirmed": success}


# =============================================================================
# Skills Registry Endpoints
# =============================================================================

@router.get("/skills")
async def list_skills() -> list[dict]:
    """Liste aller verfügbaren Odoo Skills"""
    from .service import OdooSkillsRegistry
    return OdooSkillsRegistry.get_all_skills()


@router.get("/skills/{skill_key}")
async def get_skill(skill_key: str) -> dict:
    """Einzelner Skill nach Key"""
    from .service import OdooSkillsRegistry
    skill = OdooSkillsRegistry.get_skill(skill_key)
    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill {skill_key} not found",
        )
    return skill


@router.post("/skills/{skill_key}/execute")
async def execute_skill(
    skill_key: str,
    payload: dict,
    company_id: Optional[int] = Query(None),
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Odoo Skill ausführen"""
    from .service import OdooSkillsRegistry
    
    config = get_odoo_config()
    company = company_id or config.default_company_id
    
    return await OdooSkillsRegistry.execute_skill(skill_key, payload, pool, company)


@router.post("/skills/register")
async def register_skills_in_registry() -> dict:
    """Odoo Skills im BRAiN Skills Registry registrieren"""
    from .service import OdooSkillsRegistry
    
    registered = []
    for skill in OdooSkillsRegistry.get_all_skills():
        registered.append(skill["skill_key"])
    
    return {
        "message": f"Registered {len(registered)} Odoo skills",
        "skills": registered,
        "note": "Skills can be invoked via /api/skills/execute or AXE chat",
    }


# =============================================================================
# Manufacturing Endpoints
# =============================================================================

class BomCreateRequest(BaseModel):
    product_id: int
    lines: list[dict]


@router.post("/manufacturing/bom")
async def create_bom(
    request: BomCreateRequest,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Stückliste erstellen"""
    from .service import ManufacturingAdapter
    
    config = get_odoo_config()
    adapter = ManufacturingAdapter(pool, config.default_company_id)
    
    bom_id = adapter.create_bom(request.product_id, request.lines)
    return {"bom_id": bom_id}


@router.post("/manufacturing/workorders")
async def create_workorder(
    product_id: int,
    quantity: int = 1,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Fertigungsauftrag erstellen"""
    from .service import ManufacturingAdapter
    
    config = get_odoo_config()
    adapter = ManufacturingAdapter(pool, config.default_company_id)
    
    workorder_id = adapter.create_workorder(product_id, quantity)
    return {"workorder_id": workorder_id}


@router.get("/manufacturing/workorders")
async def list_workorders(
    state: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> list[dict]:
    """Fertigungsaufträge auflisten"""
    from .service import ManufacturingAdapter
    
    config = get_odoo_config()
    adapter = ManufacturingAdapter(pool, config.default_company_id)
    
    return adapter.get_workorders(state=state, limit=limit)


# =============================================================================
# Inventory Endpoints
# =============================================================================

@router.get("/inventory/stock")
async def get_stock(
    product_id: Optional[int] = Query(None),
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> list[dict]:
    """Lagerbestände abrufen"""
    from .service import InventoryAdapter
    
    config = get_odoo_config()
    adapter = InventoryAdapter(pool, config.default_company_id)
    
    return adapter.get_stock(product_id=product_id)


class ReceiptCreateRequest(BaseModel):
    partner_id: int
    lines: list[dict]


@router.post("/inventory/receipts")
async def create_receipt(
    request: ReceiptCreateRequest,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Wareneingang erstellen"""
    from .service import InventoryAdapter
    
    config = get_odoo_config()
    adapter = InventoryAdapter(pool, config.default_company_id)
    
    receipt_id = adapter.create_receipt(request.partner_id, request.lines)
    return {"receipt_id": receipt_id}


class TransferCreateRequest(BaseModel):
    location_from: int
    location_to: int
    lines: list[dict]


@router.post("/inventory/transfers")
async def create_transfer(
    request: TransferCreateRequest,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Lagerumschlag erstellen"""
    from .service import InventoryAdapter
    
    config = get_odoo_config()
    adapter = InventoryAdapter(pool, config.default_company_id)
    
    transfer_id = adapter.create_transfer(
        request.location_from, request.location_to, request.lines
    )
    return {"transfer_id": transfer_id}


# =============================================================================
# Purchase Endpoints
# =============================================================================

class PurchaseOrderCreateRequest(BaseModel):
    partner_id: int
    lines: list[dict]


@router.post("/purchase/orders")
async def create_purchase_order(
    request: PurchaseOrderCreateRequest,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Bestellung erstellen"""
    from .service import PurchaseAdapter
    
    config = get_odoo_config()
    adapter = PurchaseAdapter(pool, config.default_company_id)
    
    order_id = adapter.create_order(request.partner_id, request.lines)
    return {"order_id": order_id, "state": "draft"}


@router.get("/purchase/orders")
async def list_purchase_orders(
    state: Optional[str] = Query(None),
    partner_id: Optional[int] = Query(None),
    limit: int = Query(100, le=500),
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> list[dict]:
    """Bestellungen auflisten"""
    from .service import PurchaseAdapter
    
    config = get_odoo_config()
    adapter = PurchaseAdapter(pool, config.default_company_id)
    
    return adapter.get_orders(state=state, partner_id=partner_id, limit=limit)


@router.post("/purchase/orders/{order_id}/confirm")
async def confirm_purchase_order(
    order_id: int,
    pool: OdooConnectionPool = Depends(get_odoo_pool),
) -> dict:
    """Bestellung bestätigen"""
    from .service import PurchaseAdapter
    
    config = get_odoo_config()
    adapter = PurchaseAdapter(pool, config.default_company_id)
    
    success = adapter.confirm_order(order_id)
    return {"order_id": order_id, "confirmed": success}
