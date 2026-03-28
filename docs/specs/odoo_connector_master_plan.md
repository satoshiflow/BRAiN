# Odoo 19 Connector Master Plan

**Version:** 1.0  
**Status:** Draft  
**Erstellt:** 2026-03-27  
**Letzte Änderung:** 2026-03-27  
**Owner:** BRAiN Architecture Team

---

## Inhaltsverzeichnis

1. [Executive Summary](#1-executive-summary)
2. [Anforderungen & Prämissen](#2-anforderungen--prämissen)
3. [Odoo 19 Kommunikationsmöglichkeiten](#3-odoo-19-kommunikationsmöglichkeiten)
4. [Architekturübersicht](#4-architekturübersicht)
5. [Odoo Adapter Layer](#5-odoo-adapter-layer)
6. [Multi-Company & Holding-Struktur](#6-multi-company--holding-struktur)
7. [Domain-Spezifische Skills](#7-domain-spezifische-skills)
8. [Brain + Strapi Integration](#8-brain--strapi-integration)
9. [Phasenplan](#9-phasenplan)
10. [Technische Details](#10-technische-details)
11. [Kosten & Lizenzen](#11-kosten--lizenzen)
12. [Risiken & Mitigations](#12-risiken--mitigations)

---

## 1. Executive Summary

Dieses Dokument definiert die Integration von BRAiN mit Odoo 19 als primärem ERP-System.

**Ziel:** BRAiN orchestriert Odoo vollständig - 20-30 Firmen in Holding-Struktur - als autonomes Gehirn mit direkter Kontrolle über alle operativen und administrativen Prozesse.

**Kernprinzipien:**
- Brain 3 (Neural Core) trifft alle Entscheidungen
- Odoo 19 dient als ausführende Datenbank (Executor)
- Direkter PostgreSQL-Zugriff für maximale Performance
- Multi-Company Fähigkeit von Anfang an eingeplant
- Skalierbar von 0 auf 100+ Firmen

---

## 2. Anforderungen & Prämissen

### 2.1 Technische Prämissen

| Prämissen | Details |
|-----------|---------|
| **Odoo Version** | Ausschließlich Version 19 |
| **Hosting** | Self-Hosted auf Hetzner Servern |
| **Datenbank** | PostgreSQL (Odoo Backend) |
| **Ziel-Firmen** | 20-30 Firmen (Holding-Struktur) |
| **Firmen-Typ** | Operative + Verwaltungsfirmen |
| **Odoo Status** | Noch nicht produktiv - muss noch aufgesetzt werden |
| **Lizenz** | Erst Community, später Enterprise |
| **Module** | Erst Community-Module, später Premium |

### 2.2 Funktionale Anforderungen

```
┌─────────────────────────────────────────────────────────────────┐
│                    FUNKTIONALE ANFORDERUNGEN                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✓ Multi-Company Management (20-30 Firmen parallel)            │
│  ✓ Buchhaltung (Accounting) - Rechnungen, Buchungssätze         │
│  ✓ Vertrieb (Sales) - Angebote, Aufträge, Kunden              │
│  ✓ Einkauf (Purchase) - Bestellungen, Lieferanten              │
│  ✓ Lager (Inventory) - Produkte, Bestände                      │
│  ✓ Fertigung (Manufacturing) - Produktion, Stücklisten         │
│  ✓ Projekte (Projects) - Projektmanagement                     │
│  ✓ HR - Personalverwaltung                                     │
│  ✓ Website/eCommerce - Headless mit Strapi                    │
│  ✓ Volle Datenbankkontrolle für komplexe Queries               │
│  ✓ Autonomous Agent Clusters pro Domain                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Nicht-Anforderungen

- Odoo eigene AI Features (BRAiN übernimmt)
- Odoo Native Frontend (Headless via BRAiN + Strapi)
- Odoo Workflows (BRAiN orchestriert)

---

## 3. Odoo 19 Kommunikationsmöglichkeiten

### 3.1 Übersicht der Möglichkeiten

| Methode | Status | Performance | Empfohlen |
|---------|--------|-------------|-----------|
| **External JSON-2 API** | ✅ Neu in 19.0 | ⭐⭐⭐ | ✅ Standard |
| **REST API (Community)** | ✅ Verfügbar | ⭐⭐⭐ | ✅ Gut |
| **XML-RPC** | ⚠️ Deprecated | ⭐⭐ | ❌ Nicht nutzen |
| **JSON-RPC (Alt)** | ⚠️ Deprecated | ⭐⭐ | ❌ Nicht nutzen |
| **Direkter PostgreSQL Zugriff** | ✅ Volle Kontrolle | ⭐⭐⭐⭐⭐ | ✅ **Bevorzugt** |

### 3.2 External JSON-2 API (Odoo 19 Standard)

**Wichtig:** Die alten `/xmlrpc` und `/jsonrpc` Endpunkte werden **in Odoo 22 entfernt**!

```python
# Odoo 19 External JSON-2 API
import requests

url = "https://your-odoo.com/jsonrpc"
headers = {"Content-Type": "application/json"}

# Authentifizierung
payload = {
    "jsonrpc": "2.0",
    "method": "call",
    "params": {
        "service": "object",
        "method": "execute_kw",
        "args": [
            "database_name",
            user_id,
            "password",
            "res.partner",  # Model
            "search_read",   # Method
            [[["customer", "=", True]]],  # Domain
            {"fields": ["name", "email", "phone"]}  # Options
        ]
    }
}

response = requests.post(url, json=payload, headers=headers)
```

### 3.3 Direkter PostgreSQL Zugriff ⭐⭐⭐

**Empfohlene Methode für BRAiN:**

```python
import psycopg2
from psycopg2 import sql

class OdooDatabase:
    def __init__(self, host, port, database, user, password):
        self.conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
    
    def execute(self, query, params=None):
        """Direkte Query-Ausführung"""
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    
    def get_partners(self, company_ids=None):
        """Kunden mit Company-Filter"""
        if company_ids:
            query = """
                SELECT id, name, email, customer, company_id
                FROM res_partner
                WHERE customer = true AND company_id IN %s
            """
            return self.execute(query, (tuple(company_ids),))
        else:
            query = """
                SELECT id, name, email, customer, company_id
                FROM res_partner
                WHERE customer = true
            """
            return self.execute(query)
    
    def get_invoices(self, company_id, state='posted'):
        """Rechnungen einer Firma"""
        query = """
            SELECT id, name, date, amount_total, state, partner_id
            FROM account_move
            WHERE company_id = %s AND move_type = 'out_invoice' AND state = %s
            ORDER BY date DESC
            LIMIT 100
        """
        return self.execute(query, (company_id, state))
```

**Vorteile Direkt-SQL:**
- 🚀 Höchste Performance (kein API-Overhead)
- 🔒 Volle Kontrolle über komplexe Queries
- 📊 Multi-Company Filterung direkt in SQL
- 🎯 Für BRAiN Neural Core optimiert

### 3.4 Vergleichstabelle

```
┌────────────────────┬────────────┬────────────┬────────────┬──────────────────┐
│ Kriterium         │ JSON-2 API │ REST API   │ Direkt-SQL │ XML-RPC          │
├────────────────────┼────────────┼────────────┼────────────┼──────────────────┤
│ Performance       │ Gut        │ Gut        │ Exzellent  │ Mittel           │
│ Komplexe Queries  │ Begrenzt   │ Begrenzt   │ Volle      │ Begrenzt        │
│ Multi-Company    │ Manuell    │ Manuell    │ Direkt     │ Manuell          │
│ Wartungsaufwand   │ Mittel     │ Mittel     │ Niedrig    │ Hoch (deprecated)│
│ Odoo Updates      │ Kompatibel │ Kompatibel │ Unabhängig │ Riskant         │
│ Für BRAiN         │ ⚠️         │ ⚠️         │ ✅          │ ❌               │
└────────────────────┴────────────┴────────────┴────────────┴──────────────────┘
```

---

## 4. Architekturübersicht

### 4.1 Gesamtarchitektur

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          BRAiN + Odoo 19 ARCHITEKTUR                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                         USER LAYER                                   │    │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │    │
│   │   │   AXE       │  │ ControlDeck │  │  Strapi (Websites)      │   │    │
│   │   │  (Chat UI)  │  │  (Admin)   │  │  Landingpages/WebApps   │   │    │
│   │   └─────────────┘  └─────────────┘  └─────────────────────────┘   │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                    BRAIN 3 (Neural Core)                            │    │
│   │   ┌──────────────────────────────────────────────────────────────┐  │    │
│   │   │  • Entscheidungen treffen                                     │  │    │
│   │   │  • Parameter (creativity, caution, speed)                   │  │    │
│   │   │  • Learning & Adaptation                                     │  │    │
│   │   │  • Synapse-Routing                                            │  │    │
│   │   │  • Company Context Resolution                                 │  │    │
│   │   └──────────────────────────────────────────────────────────────┘  │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                 BRAIN 2 (Executor Layer)                           │    │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │    │
│   │   │ skill_engine │  │   memory   │  │  Odoo Adapter Layer   │   │    │
│   │   └─────────────┘  └─────────────┘  └─────────────────────────┘   │    │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                    ODOO CONNECTOR LAYER                           │    │
│   │   ┌─────────────────────────────────────────────────────────────┐  │    │
│   │   │  OdooAdapter                                                │  │    │
│   │   │  ├── Connection Pool                                        │  │    │
│   │   │  ├── Query Builder                                          │  │    │
│   │   │  ├── Company Resolver                                       │  │    │
│   │   │  ├── Model Mapper                                           │  │    │
│   │   │  └── Transaction Manager                                    │  │    │
│   │   └─────────────────────────────────────────────────────────────┘  │    │
│   │                                                                       │
│   │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│   │   │ Accounting  │  │   Sales    │  │Manufacturing│              │
│   │   │  Adapter   │  │   Adapter  │  │   Adapter   │              │
│   │   └─────────────┘  └─────────────┘  └─────────────┘              │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                      │                                           │
│                                      ▼                                           │
│   ┌─────────────────────────────────────────────────────────────────────┐    │
│   │                    ODOO 19 DATABASE (PostgreSQL)                  │    │
│   │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │    │
│   │   │ Holding  │ │ Firma A  │ │ Firma B  │ │ Firma C  │  ...      │    │
│   │   │ (Root)   │ │          │ │          │ │          │           │    │
│   │   └──────────┘ └──────────┘ └──────────┘ └──────────┘           │    │
│   │                                                                       │
│   │   res_company  ──►  company_id Foreign Keys                       │
│   │                                                                       │
│   └─────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Datenfluss

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            DATENFLUSS                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  1. USER INPUT                                                               │
│     "Erstelle eine Rechnung für Firma X"                                      │
│            │                                                                  │
│            ▼                                                                  │
│  2. AXE CHAT                                                                 │
│     └─► Session + Intent + Context                                            │
│            │                                                                  │
│            ▼                                                                  │
│  3. BRAIN 3 (Neural Core)                                                   │
│     ├─► DecisionContext erstellen                                            │
│     ├─► PurposeEvaluation (accept/reject)                                     │
│     ├─► Company Resolution (Firma X = company_id)                            │
│     ├─► Parameter laden (creativity, caution, speed)                         │
│     └─► Routing → synapse: odoo_invoice_create                             │
│            │                                                                  │
│            ▼                                                                  │
│  4. BRAIN 2 (Executor)                                                      │
│     └─► skill_engine → OdooAdapter                                           │
│            │                                                                  │
│            ▼                                                                  │
│  5. ODOO CONNECTOR                                                          │
│     ├─► Company Context setzen                                               │
│     ├─► Invoice Adapter                                                      │
│     ├─► SQL Query ausführen                                                 │
│     └─► Result + Metadata                                                    │
│            │                                                                  │
│            ▼                                                                  │
│  6. LEARNING LOOP                                                           │
│     ├─► Execution loggen                                                     │
│     ├─► Synapse weight anpassen                                             │
│     ├─► Parameter optimieren                                                 │
│     └─► State wechseln wenn nötig                                           │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Odoo Adapter Layer

### 5.1 Modulstruktur

```
backend/app/modules/
├── odoo_adapter/
│   ├── __init__.py
│   ├── router.py              # API Endpoints
│   ├── service.py             # Hauptservice
│   ├── config.py              # Konfiguration
│   ├── connection.py           # DB Connection Pool
│   ├── models/
│   │   ├── __init__.py
│   │   ├── company.py         # Company Resolver
│   │   ├── partner.py         # Partner/Customer
│   │   ├── account.py         # Buchhaltung
│   │   ├── sale.py            # Vertrieb
│   │   ├── purchase.py         # Einkauf
│   │   ├── inventory.py        # Lager
│   │   ├── manufacturing.py    # Fertigung
│   │   └── project.py         # Projekte
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py            # Basis Adapter
│   │   ├── accounting.py       # Buchhaltungs-Adapter
│   │   ├── sales.py           # Vertriebs-Adapter
│   │   ├── manufacturing.py    # Fertigungs-Adapter
│   │   └── inventory.py       # Lager-Adapter
│   └── migrations/
│       └── 001_odoo_adapter.sql
```

### 5.2 Connection Pool

```python
# backend/app/modules/odoo_adapter/connection.py
from contextlib import contextmanager
from psycopg2 import pool
from psycopg2.pool import ThreadedConnectionPool
import logging

logger = logging.getLogger(__name__)

class OdooConnectionPool:
    """
    Connection Pool für Odoo PostgreSQL Datenbank.
    Thread-safe und für hohe Last optimiert.
    """
    
    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_connections: int = 2,
        max_connections: int = 20
    ):
        self.pool = ThreadedConnectionPool(
            min_connections,
            max_connections,
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        logger.info(f"🎯 Odoo Connection Pool initialized: {host}/{database}")
    
    @contextmanager
    def get_connection(self):
        """Kontext-Manager für Connections"""
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Query failed: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    def execute_query(self, query: str, params: tuple = None):
        """Query ausführen und Ergebnisse zurückgeben"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if cur.description:
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in cur.fetchall()]
                return []
    
    def close_all(self):
        """Alle Connections schließen"""
        self.pool.closeall()
```

### 5.3 Company Resolver

```python
# backend/app/modules/odoo_adapter/models/company.py
from typing import Optional, List, Dict, Any

class CompanyResolver:
    """
    Resolve Company IDs und Names für Multi-Company Setup.
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def resolve_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Firma nach Name finden"""
        query = """
            SELECT id, name, street, zip, city, country_id, currency_id
            FROM res_company
            WHERE name ILIKE %s
            LIMIT 1
        """
        results = self.db.execute_query(query, (f"%{name}%",))
        return results[0] if results else None
    
    def resolve_by_id(self, company_id: int) -> Optional[Dict[str, Any]]:
        """Firma nach ID finden"""
        query = """
            SELECT id, name, street, zip, city, country_id, currency_id
            FROM res_company
            WHERE id = %s
        """
        results = self.db.execute_query(query, (company_id,))
        return results[0] if results else None
    
    def get_all_companies(self) -> List[Dict[str, Any]]:
        """Alle Firmen abrufen"""
        query = """
            SELECT id, name, street, zip, city, country_id
            FROM res_company
            ORDER BY name
        """
        return self.db.execute_query(query)
    
    def get_children(self, parent_id: int) -> List[Dict[str, Any]]:
        """Tochterfirmen einer Holding abrufen"""
        query = """
            SELECT id, name, street, zip, city, country_id
            FROM res_company
            WHERE parent_path LIKE %s
            ORDER BY name
        """
        return self.db.execute_query(query, (f"%{parent_id}/%",))
```

### 5.4 Accounting Adapter

```python
# backend/app/modules/odoo_adapter/adapters/accounting.py
from typing import Optional, List, Dict, Any
from datetime import datetime

class AccountingAdapter:
    """
    Adapter für Odoo Buchhaltung.
    Unterstützt: Rechnungen, Buchungssätze, Zahlungen
    """
    
    def __init__(self, db_connection, company_id: int):
        self.db = db_connection
        self.company_id = company_id
    
    def create_invoice(
        self,
        partner_id: int,
        lines: List[Dict],
        invoice_date: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rechnung erstellen
        
        Args:
            partner_id: Kunden-ID
            lines: [{'product_id': int, 'quantity': float, 'price_unit': float}]
            invoice_date: Rechnungsdatum (YYYY-MM-DD)
            due_date: Fälligkeitsdatum (YYYY-MM-DD)
        
        Returns:
            {'invoice_id': int, 'number': str, 'state': str}
        """
        # SQL Insert für account.move
        query = """
            INSERT INTO account_move (
                name, partner_id, move_type, invoice_date, 
                invoice_date_due, company_id, state
            ) VALUES (
                (SELECT COALESCE(MAX(SUBSTRING(name FROM '[^0-9]+$')::int), 0) + 1
                 FROM account_move 
                 WHERE move_type = 'out_invoice' AND company_id = %s
                 AND name ~ '^[A-Z0-9/-]+$') || '/INV/2026',
                %s, 'out_invoice', %s, %s, %s, 'draft'
            )
            RETURNING id, name, state
        """
        
        result = self.db.execute_query(
            query,
            (
                self.company_id,
                partner_id,
                invoice_date or datetime.now().date(),
                due_date,
                self.company_id
            )
        )
        
        invoice_id = result[0]['id']
        
        # Positionen hinzufügen
        for line in lines:
            self._add_invoice_line(invoice_id, line)
        
        return result[0]
    
    def _add_invoice_line(self, invoice_id: int, line: Dict):
        """Rechnungsposition hinzufügen"""
        # Berechne Steuern (vereinfacht)
        tax_amount = line.get('price_unit', 0) * line.get('quantity', 1) * 0.19
        
        query = """
            INSERT INTO account_move_line (
                move_id, account_id, partner_id, name,
                quantity, price_unit, company_id, debit, credit
            )
            SELECT 
                %s, 
                (SELECT id FROM account_account 
                 WHERE code = '400000' AND company_id = %s LIMIT 1),
                (SELECT partner_id FROM account_move WHERE id = %s),
                %s, %s, %s, %s, %s, 0
        """
        
        amount = line.get('price_unit', 0) * line.get('quantity', 1)
        
        self.db.execute_query(query, (
            invoice_id,
            self.company_id,
            invoice_id,
            line.get('name', 'Position'),
            line.get('quantity', 1),
            line.get('price_unit', 0),
            self.company_id,
            amount
        ))
    
    def get_open_invoices(
        self,
        partner_id: Optional[int] = None,
        date_from: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Offene Rechnungen abrufen"""
        query = """
            SELECT 
                am.id, am.name, am.invoice_date, am.invoice_date_due,
                am.amount_total, am.amount_residual, am.state, rp.name as partner
            FROM account_move am
            LEFT JOIN res_partner rp ON am.partner_id = rp.id
            WHERE am.move_type = 'out_invoice'
            AND am.state = 'posted'
            AND am.company_id = %s
        """
        
        params = [self.company_id]
        
        if partner_id:
            query += " AND am.partner_id = %s"
            params.append(partner_id)
        
        if date_from:
            query += " AND am.invoice_date >= %s"
            params.append(date_from)
        
        query += " ORDER BY am.invoice_date DESC LIMIT 100"
        
        return self.db.execute_query(query, tuple(params))
```

---

## 6. Multi-Company & Holding-Struktur

### 6.1 Odoo Company Modell

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ODOO MULTI-COMPANY MODELL                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   res_company Table:                                                        │
│   ┌──────┬─────────────┬────────────┬─────────────┬───────────────┐       │
│   │  id  │    name     │  parent_id │ parent_path │  currency_id  │       │
│   ├──────┼─────────────┼────────────┼─────────────┼───────────────┤       │
│   │  1   │ Holding GmbH│    NULL    │     1/     │      1        │       │
│   │  2   │ Firma A    │      1     │    1/2/    │      1        │       │
│   │  3   │ Firma B    │      1     │    1/3/    │      1        │       │
│   │  4   │ Ops GmbH   │      1     │    1/4/    │      1        │       │
│   │  5   │ Produktion │      4     │   1/4/5/   │      1        │       │
│   └──────┴─────────────┴────────────┴─────────────┴───────────────┘       │
│                                                                              │
│   Verknüpfung über company_id in allen Transaktions-Tabellen:              │
│   - account_move (Buchhaltung)                                            │
│   - sale_order (Vertrieb)                                                 │
│   - purchase_order (Einkauf)                                               │
│   - stock_picking (Lager)                                                 │
│   - mrp_production (Fertigung)                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 BRAiN Company Context

```python
# Company Context für BRAiN Neural Core
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class CompanyContext:
    """
    Kontext für Company-spezifische Operationen in BRAiN.
    """
    company_id: int
    company_name: str
    currency: str
    country_code: str
    parent_company_id: Optional[int]
    is_holding: bool
    
    @classmethod
    def from_odoo(cls, db_result: dict) -> 'CompanyContext':
        return cls(
            company_id=db_result['id'],
            company_name=db_result['name'],
            currency=db_result.get('currency_id', 'EUR'),
            country_code=db_result.get('country_code', 'DE'),
            parent_company_id=db_result.get('parent_id'),
            is_holding=db_result.get('parent_id') is None
        )
    
    def get_accessible_companies(self, db) -> List[int]:
        """
        Alle Firmen die diese Firma sehen kann (inkl. Töchter).
        """
        if self.is_holding:
            # Holding sieht alle
            query = "SELECT id FROM res_company"
            results = db.execute_query(query)
            return [r['id'] for r in results]
        else:
            # Normale Firma sieht nur sich selbst
            return [self.company_id]
```

### 6.3 Holding-Architektur in BRAiN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BRAiN HOLDING MANAGEMENT                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  HOLDING (Brain)                                                            │
│  ├── Strategy & Governance                                                   │
│  ├── Cross-Company Reporting                                                │
│  ├── Consolidated Accounting                                                │
│  └── Resource Allocation                                                    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    OPERATIVE UNITS                                   │    │
│  │                                                                       │    │
│  │   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐       │    │
│  │   │   FIRMA A    │   │   FIRMA B    │   │   FIRMA C    │       │    │
│  │   │  (Sales)     │   │  (Produktion)│   │  (Verwaltung)│       │    │
│  │   │              │   │              │   │              │       │    │
│  │   │ • Vertrieb   │   │ • Fertigung  │   │ • HR        │       │    │
│  │   │ • Marketing  │   │ • QC        │   │ • Finanzen   │       │    │
│  │   │ • CRM        │   │ • Einkauf   │   │ • Legal     │       │    │
│  │   └───────────────┘   └───────────────┘   └───────────────┘       │    │
│  │                                                                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  BRAiN Agent Clusters:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  • holding_orchestrator (Strategy)                                   │    │
│  │  • accounting_cluster (Buchhaltung)                                  │    │
│  │  • sales_cluster (Vertrieb)                                         │    │
│  │  • manufacturing_cluster (Fertigung)                               │    │
│  │  • hr_cluster (Personal)                                            │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Domain-Spezifische Skills

### 7.1 Skill Registry für Odoo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ODOO SKILL REGISTRY                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  accounting_skills:                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ skill: odoo.invoice.create                                        │    │
│  │ skill: odoo.invoice.send                                          │    │
│  │ skill: odoo.invoice.register_payment                              │    │
│  │ skill: odoo.journal_entry.create                                  │    │
│  │ skill: odoo.payment.collect                                       │    │
│  │ skill: odoo.bank_statement.import                                 │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  sales_skills:                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ skill: odoo.quote.create                                          │    │
│  │ skill: odoo.quote.send                                            │    │
│  │ skill: odoo.order.confirm                                         │    │
│  │ skill: odoo.delivery.create                                       │    │
│  │ skill: odoo.customer.onboard                                      │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  manufacturing_skills:                                                      │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ skill: odoo.workorder.start                                       │    │
│  │ skill: odoo.workorder.complete                                    │    │
│  │ skill: odoo.bom.create                                            │    │
│  │ skill: odoo.production.start                                      │    │
│  │ skill: odoo.quality.check                                         │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  inventory_skills:                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ skill: odoo.stock.count                                           │    │
│  │ skill: odoo.stock.transfer                                        │    │
│  │ skill: odoo.replenish.trigger                                     │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Skill Definition Beispiel

```yaml
# skill: odoo.invoice.create
name: odoo.invoice.create
description: Erstelle eine Kundenrechnung in Odoo
version: 1.0.0
domain: accounting

parameters:
  required:
    - company_id: int
      description: Odoo Company ID
    - partner_id: int
      description: Kunden-ID
    - lines: list
      description: Rechnungspositionen
  optional:
    - invoice_date: date
      description: Rechnungsdatum
    - due_date: date
      description: Fälligkeitsdatum
    - payment_term_id: int
      description: Zahlungsziel

returns:
  invoice_id: int
  invoice_number: str
  state: str
  amount_total: float

neural_parameters:
  - creativity: 0.3  # Niedrig für Buchhaltung
  - caution: 0.95   # Sehr hoch!
  - speed: 0.7

governance:
  requires_approval: true
  approval_threshold: 10000  # Euro
  audit_level: high
```

---

## 8. Brain + Strapi Integration

### 8.1 Architektur

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BRAIN + STRAPI + ODOO                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         USER                                                 │
│              (Landingpage, WebApp, Dashboard)                                │
│                           │                                                  │
│                           ▼                                                  │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                        STRAPI (Headless CMS)                      │    │
│   │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  │    │
│   │   │  Pages    │  │  Forms     │  │   Shop    │  │  API    │  │    │
│   │   └────────────┘  └────────────┘  └────────────┘  └──────────┘  │    │
│   │                           │                                          │    │
│   │                    BRAiN AXE                                         │    │
│   │                           │                                          │    │
│   └───────────────────────────┼──────────────────────────────────────────┘    │
│                               │                                              │
│                               ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                    BRAiN (Neural Core)                             │    │
│   │   • Intent Recognition                                            │    │
│   │   • Business Logic                                                │    │
│   │   • Parameter (creativity, caution, speed)                       │    │
│   └───────────────────────────┬──────────────────────────────────────────┘    │
│                               │                                              │
│                               ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                    ODOO CONNECTOR                                 │    │
│   │   • Accounting Adapter                                            │    │
│   │   • Sales Adapter                                                 │    │
│   │   • Manufacturing Adapter                                         │    │
│   └───────────────────────────┬──────────────────────────────────────────┘    │
│                               │                                              │
│                               ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                    ODOO 19 DATABASE                               │    │
│   └────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Strapi Integration Points

| Komponente | Integration | Beschreibung |
|-----------|-------------|--------------|
| **Forms** | BRAiN Skill | Formulare → Odoo Daten |
| **Shop** | Odoo eCommerce | Produkte aus Odoo |
| **Pages** | Static + Dynamic | Branchenspezifisch |
| **API** | REST/GraphQL | Für Custom Apps |

### 8.3 Beispiel: Strapi Form → Odoo Invoice

```
1. User füllt Formular auf Website (Strapi)
         │
         ▼
2. Strapi sendet an BRAiN AXE
   POST /api/axe/chat
   {
     "message": "Ich möchte eine Rechnung für...",
     "context": {
       "form_id": "invoice_request_001",
       "company": "Firma A"
     }
   }
         │
         ▼
3. BRAiN Neural Core
   - Intent: "create_invoice"
   - Entity: partner_id aus Formular
   - Parameters: company_id, lines, etc.
         │
         ▼
4. Odoo Connector
   - Company Resolution
   - Invoice Creation
   - SQL Execution
         │
         ▼
5. Response an Strapi
   { "invoice_id": 123, "number": "INV/2026/001" }
         │
         ▼
6. Strapi zeigt Bestätigung
```

---

## 9. Phasenplan

### Phase 1: Foundation (Monat 1-2)

```
✓ 9.1.1 Connection Pool
       - Thread-safe PostgreSQL connections
       - Config via Environment Variables

✓ 9.1.2 Company Resolver
       - Multi-Company Support
       - Tenant → Odoo Company Mapping

✓ 9.1.3 Neural Core Integration
       - Odoo Synapsen registriert
       - Brain → Odoo Decision Flow

✓ 9.1.4 Database Tables
       - brain_company_mapping
       - odoo_skills
       - odoo_skill_runs
```

### Phase 2: Core Modules (Monat 3-4)

```
✓ 9.2.1 Accounting Adapter
       - Rechnungen (Invoices) ✓
       - Buchungen (Entries)
       - Zahlungen (Payments)

✓ 9.2.2 Sales Adapter
       - Kunden (Partners) ✓
       - Angebote (Quotes)
       - Aufträge (Orders) ✓

✓ 9.2.3 Skills Registry
       - Odoo Skills als BRAiN Skills ✓
       - Skill Execution API ✓

✓ 9.2.4 AXE Integration
       - Chat Commands für Odoo
       - Response Formatter
```

### Phase 3: Erweiterung (Monat 5-6)

```
✓ 9.3.1 Manufacturing Adapter
       - Stücklisten (BoM) ✓
       - Fertigungsaufträge ✓
       - Arbeitspläne

✓ 9.3.2 Inventory Adapter
       - Lagerbestände ✓
       - Wareneingänge ✓
       - Umlagerungen ✓

✓ 9.3.3 Purchase Adapter
       - Bestellungen ✓
       - Lieferanten

□ 9.3.4 Strapi Integration
       - Formulare
       - Shop-Anbindung
```
□ 9.1.1 Odoo 19 Installation auf Hetzner
       - PostgreSQL Datenbank aufsetzen
       - Odoo 19 installieren
       - Basis-Konfiguration

□ 9.1.2 Odoo Adapter Layer Basis
       - Connection Pool
       - Company Resolver
       - Basis-Modelle

□ 9.1.3 Multi-Company Setup
       - Holding-Struktur anlegen
       - Company-IDs dokumentieren
       - Test-Firmen erstellen

□ 9.1.4 Brain Integration
       - Neural Core → Odoo Adapter
       - Synapse: odoo_execute
       - Learning Loop aktivieren
```

### Phase 2: Core Modules (Monat 3-4)

```
□ 9.2.1 Accounting Adapter
       - Rechnungen erstellen
       - Buchungssätze
       - Offene Posten
       - Zahlungen

□ 9.2.2 Sales Adapter
       - Angebote
       - Aufträge
       - Kunden

□ 9.2.3 Skills registrieren
       - odoo.invoice.*
       - odoo.quote.*
       - odoo.order.*

□ 9.2.4 AXE Integration
       - Chat Commands für Odoo
       - Response Formatter
```

### Phase 3: Erweiterung (Monat 5-6)

```
□ 9.3.1 Manufacturing Adapter
       - Stücklisten (BoM)
       - Fertigungsaufträge
       - Arbeitspläne

□ 9.3.2 Inventory Adapter
       - Lagerbestände
       - Wareneingänge
       - Umlagerungen

□ 9.3.3 Purchase Adapter
       - Bestellungen
       - Lieferanten

□ 9.3.4 Strapi Integration
       - Formulare
       - Shop-Anbindung
```

### Phase 4: Agent Clusters (Monat 7-8)

```
□ 9.4.1 Domain Agent Clusters
       - accounting_cluster
       - sales_cluster
       - manufacturing_cluster

□ 9.4.2 Autonomous Skills
       - Self-Approval Rules
       - Escalation Logic
       - Budget Limits

□ 9.4.3 Learning & Optimization
       - Success Rate Tracking
       - Parameter Optimization
       - Pattern Recognition
```

### Phase 5: Scale (Monat 9-12)

```
□ 9.5.1 20-30 Firmen onboarad
       - Company Templates
       - Import Scripts
       - Validation

□ 9.5.2 Premium Modules
       - Odoo Enterprise Upgrade
       - Field Service
       - Quality Management

□ 9.5.3 Advanced Features
       - Predictive Analytics
       - Automated Reporting
       - Cross-Company Consolidation
```

---

## 10. Technische Details

### 10.1 Umgebungsvariablen

```bash
# .env.brain

# Odoo Database
ODOO_DB_HOST=localhost
ODOO_DB_PORT=5432
ODOO_DB_NAME=odoo_production
ODOO_DB_USER=odoo
ODOO_DB_PASSWORD=your_secure_password

# Odoo Adapter
ODOO_ADAPTER_POOL_MIN=2
ODOO_ADAPTER_POOL_MAX=20
ODOO_ADAPTER_TIMEOUT=30

# Company Defaults
DEFAULT_COMPANY_ID=1
AUTO_COMPANY_DETECTION=true

# Features
ENABLE_DIRECT_SQL=true
ENABLE_JSON_API_FALLBACK=false
```

### 10.2 Datenbank-Schema

```sql
-- Brain Odoo Mapping Tables

-- Company Mapping (BRAiN ↔ Odoo)
CREATE TABLE brain_company_mapping (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brain_tenant_id UUID NOT NULL,
    odoo_company_id INTEGER NOT NULL,
    company_name VARCHAR(255),
    is_holding BOOLEAN DEFAULT false,
    parent_company_id INTEGER,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(brain_tenant_id, odoo_company_id)
);

-- Odoo Skill Registry
CREATE TABLE odoo_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_key VARCHAR(100) NOT NULL UNIQUE,
    odoo_model VARCHAR(100),
    odoo_method VARCHAR(100),
    description TEXT,
    parameters JSONB,
    returns JSONB,
    neural_parameters JSONB,
    governance JSONB,
    is_active BOOLEAN DEFAULT true,
    version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Execution Logging
CREATE TABLE odoo_skill_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_key VARCHAR(100) NOT NULL,
    company_id INTEGER NOT NULL,
    input_payload JSONB,
    output_payload JSONB,
    execution_time_ms FLOAT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 10.3 API Endpoints

```python
# backend/app/modules/odoo_adapter/router.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/odoo", tags=["odoo"])

# Company Management
@router.get("/companies")
async def list_companies():
    """Alle Odoo Firmen auflisten"""
    pass

@router.get("/companies/{company_id}")
async def get_company(company_id: int):
    """Firma Details"""
    pass

# Accounting
@router.post("/invoices")
async def create_invoice(request: InvoiceCreateRequest):
    """Rechnung erstellen"""
    pass

@router.get("/invoices")
async def list_invoices(
    company_id: int,
    partner_id: Optional[int] = None,
    state: Optional[str] = None
):
    """Rechnungen auflisten"""
    pass

# Sales
@router.post("/orders")
async def create_order(request: OrderCreateRequest):
    """Auftrag erstellen"""
    pass

# Manufacturing
@router.post("/production")
async def create_production(request: ProductionCreateRequest):
    """Fertigungsauftrag erstellen"""
    pass
```

---

## 11. Kosten & Lizenzen

### 11.1 Odoo Lizenzen

| Version | Kosten | Module |
|---------|--------|--------|
| **Community** | Kostenlos | Basis-Module |
| **Enterprise** | 195€/Monat/Basis | Alle Module |
| **Odoo Online** | Ab 25€/Monat | SaaS |

**Empfehlung:**
- Phase 1-4: Community Version
- Phase 5+: Enterprise für Premium-Module

### 11.2 Geschätzte Kosten (Self-Hosted)

| Komponente | Einmalig | Monatlich |
|-----------|----------|-----------|
| **Hetzner Server** (CCX13) | - | ~150€ |
| **Odoo Community** | Kostenlos | - |
| **Odoo Enterprise** (später) | - | ~390€ |
| **BRAiN Infrastruktur** | - | ~50€ |
| **Strapi Cloud/Server** | - | ~30€ |
| **Domänen & SSL** | ~20€ | ~10€ |

### 11.3 Lizenz-Strategie

```
Phase 1-2 (Monat 1-4): 
  └─► Community Version
      └── Buchhaltung, Vertrieb, Einkauf, Lager, Projekte
      
Phase 3-4 (Monat 5-8):
  └─► Community + eigene Entwicklungen
      └── Brain Agent Clusters
      
Phase 5 (Monat 9+):
  └─► Enterprise Upgrade
      └── Field Service, Quality, Maintenance
      └── Advanced Reporting
```

---

## 12. Risiken & Mitigations

### 12.1 Technische Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|------------------|--------|------------|
| **Odoo 19 API Breaking Changes** | Mittel | Hoch | Direkt-SQL statt API; Abstraktionslayer |
| **Performance bei 30 Firmen** | Niedrig | Hoch | Connection Pooling; Query Optimization |
| **Data Consistency** | Mittel | Hoch | Transaktionsmanagement; Validierung |
| **Schema Updates** | Mittel | Mittel | Migration Scripts; Versionierung |

### 12.2 Operative Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|------------------|--------|------------|
| **Firmen-Übergreifende Daten** | Niedrig | Kritisch | Company Context Validation; RBAC |
| **Massive Writes** | Niedrig | Mittel | Batch Processing; Queue |
| **Parallel Access** | Niedrig | Mittel | PostgreSQL MVCC |

### 12.3 Migrations-Risiken

| Risiko | Mitigation |
|--------|------------|
| **Daten-Migration von Alt-System** | Staged Migration; Validation |
| **Benutzer-Akzeptanz** | Training; FAQ; AXE Chat Interface |
| **Performance Learning Curve** | Monitoring; Optimization Cycles |

---

## 13. Anhang

### 13.1 Odoo 19 Wichtige Tabellen

| Odoo Model | Tabelle | Beschreibung |
|------------|---------|--------------|
| Company | res_company | Firmen |
| Partner | res_partner | Kunden/Lieferanten |
| User | res_users | Benutzer |
| Invoice | account_move | Rechnungen |
| Journal | account_journal | Journalbücher |
| Account | account_account | Kontenplan |
| Sale Order | sale_order | Aufträge |
| Purchase Order | purchase_order | Bestellungen |
| Product | product_product | Produkte |
| Stock | stock_picking | Lagerbewegungen |
| Manufacturing | mrp_production | Fertigungsaufträge |
| Project | project_project | Projekte |

### 13.2 Nützliche Queries

```sql
-- Alle Firmen mit ihren Töchtern
SELECT 
    rc1.id as company_id,
    rc1.name as company_name,
    rc2.id as child_id,
    rc2.name as child_name
FROM res_company rc1
LEFT JOIN res_company rc2 ON rc2.parent_path LIKE rc1.id || '/%'
WHERE rc1.parent_id IS NULL
ORDER BY rc1.name, rc2.name;

-- Offene Posten einer Firma
SELECT 
    am.name as invoice,
    am.invoice_date,
    am.invoice_date_due,
    am.amount_total,
    am.amount_residual,
    rp.name as partner
FROM account_move am
JOIN res_partner rp ON am.partner_id = rp.id
WHERE am.move_type = 'out_invoice'
AND am.state = 'posted'
AND am.company_id = 1
AND am.amount_residual > 0
ORDER BY am.invoice_date_due;

-- Top-Kunden nach Umsatz
SELECT 
    rp.id,
    rp.name,
    SUM(am.amount_total) as total_revenue
FROM res_partner rp
JOIN account_move am ON am.partner_id = rp.id
WHERE am.move_type = 'out_invoice'
AND am.state = 'posted'
AND am.company_id = 1
GROUP BY rp.id, rp.name
ORDER BY total_revenue DESC
LIMIT 10;
```

---

## 14. Dokument-Historie

| Version | Datum | Autor | Änderungen |
|---------|-------|-------|------------|
| 1.0 | 2026-03-27 | BRAiN Team | Initiales Dokument |

---

**Nächste Schritte:**
1. Odoo 19 auf Hetzner aufsetzen
2. Datenbank-Struktur planen
3. Company-Setup definieren
4. Adapter Development starten

---

*Dieses Dokument ist Teil der BRAiN Architecture Documentation*
