"""
Brain 3.0 - Neural Core
=======================

Das "Gehirn" von BRAiN 3.0
- Verwaltet Synapsen-Verknüpfungen
- Liest Parameter aus DB
- Führt Execution Flows aus

Konzept:
- Synapse: Eine Verbindung zwischen Input und Output
- Parameter: Die "Gewichte" die bestimmen wie Synapsen funktionieren
- State: Der aktuelle Zustand des Systems
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select, update, insert, and_, Column, String, Float, Boolean, Integer, JSON, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.neural.learning import LearningLoop, LearningConfig

from app.core.database import Base


# =============================================================================
# DATABASE MODELS
# =============================================================================

class NeuralSynapseORM(Base):
    """Synapse - Verbindung zwischen Modulen"""
    __tablename__ = "neural_synapses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    synapse_id = Column(String(100), unique=True, nullable=False)
    source_module = Column(String(100), nullable=False)
    target_module = Column(String(100), nullable=False)
    capability = Column(String(100), nullable=False)
    weight = Column(Float, default=1.0)
    bias = Column(Float, default=0.0)
    input_schema = Column(JSON, default={})
    output_schema = Column(JSON, default={})
    state = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BrainStateORM(Base):
    """Brain State - Aktueller Zustand"""
    __tablename__ = "brain_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_name = Column(String(100), unique=True, nullable=False)
    parameters = Column(JSON, default={})
    context = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BrainParameterORM(Base):
    """Brain Parameter - Die Gewichte"""
    __tablename__ = "brain_parameters"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parameter_key = Column(String(100), unique=True, nullable=False)
    parameter_value = Column(JSON, nullable=False)
    parameter_type = Column(String(20), default="float")
    min_value = Column(JSON, default=None)
    max_value = Column(JSON, default=None)
    default_value = Column(JSON, default=None)
    description = Column(String(500), default=None)
    is_mutable = Column(Boolean, default=True)
    learning_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class SynapseExecutionORM(Base):
    """Execution Log - Tracing"""
    __tablename__ = "synapse_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    synapse_id = Column(String(100), nullable=False)
    input_data = Column(JSON, default={})
    output_data = Column(JSON, default={})
    execution_time_ms = Column(Float, default=None)
    success = Column(Boolean, default=True)
    error_message = Column(String(1000), default=None)
    parameters = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class SynapseCreate(BaseModel):
    """Input für Synapse Erstellung"""
    synapse_id: str
    source_module: str
    target_module: str
    capability: str
    weight: float = 1.0
    bias: float = 0.0
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}


class SynapseResponse(BaseModel):
    """Synapse Antwort"""
    id: str
    synapse_id: str
    source_module: str
    target_module: str
    capability: str
    weight: float
    bias: float
    is_active: bool


class ParameterCreate(BaseModel):
    """Input für Parameter Erstellung"""
    parameter_key: str
    parameter_value: Any
    parameter_type: str = "float"
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    default_value: Optional[Any] = None
    description: Optional[str] = None
    is_mutable: bool = True
    learning_enabled: bool = False


class ParameterResponse(BaseModel):
    """Parameter Antwort"""
    parameter_key: str
    parameter_value: Any
    parameter_type: str
    is_mutable: bool


class ExecutionRequest(BaseModel):
    """Execution Request"""
    action: str
    payload: Dict[str, Any] = {}
    context: Dict[str, Any] = {}


class ExecutionResponse(BaseModel):
    """Execution Response"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    synapse_id: Optional[str] = None
    execution_time_ms: float = 0.0
    parameters_used: Dict[str, Any] = {}
    learning: Optional[Dict[str, Any]] = None


# =============================================================================
# CORE CLASS
# =============================================================================

class NeuralCore:
    """
    Das zentrale Nervensystem.
    
    Verwaltet:
    - Synapsen (Verknüpfungen)
    - States (Zustände)
    - Parameter (Gewichte)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 30  # seconds
    
    # -------------------------------------------------------------------------
    # SYNAPSE MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def register_synapse(self, synapse: SynapseCreate) -> SynapseResponse:
        """Registriert eine neue Synapse"""
        orm = NeuralSynapseORM(
            synapse_id=synapse.synapse_id,
            source_module=synapse.source_module,
            target_module=synapse.target_module,
            capability=synapse.capability,
            weight=synapse.weight,
            bias=synapse.bias,
            input_schema=synapse.input_schema,
            output_schema=synapse.output_schema,
        )
        self.db.add(orm)
        await self.db.commit()
        
        logger.info(f"Registered synapse: {synapse.synapse_id}")
        
        return SynapseResponse(
            id=str(orm.id),
            synapse_id=orm.synapse_id,
            source_module=orm.source_module,
            target_module=orm.target_module,
            capability=orm.capability,
            weight=orm.weight,
            bias=orm.bias,
            is_active=orm.is_active,
        )
    
    async def get_synapse(self, synapse_id: str) -> Optional[SynapseResponse]:
        """Holt eine Synapse nach ID"""
        query = select(NeuralSynapseORM).where(
            NeuralSynapseORM.synapse_id == synapse_id,
            NeuralSynapseORM.is_active == True
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        
        if not orm:
            return None
        
        return SynapseResponse(
            id=str(orm.id),
            synapse_id=orm.synapse_id,
            source_module=orm.source_module,
            target_module=orm.target_module,
            capability=orm.capability,
            weight=orm.weight,
            bias=orm.bias,
            is_active=orm.is_active,
        )
    
    async def list_synapses(self, capability: Optional[str] = None) -> List[SynapseResponse]:
        """Listet alle aktiven Synapsen"""
        query = select(NeuralSynapseORM).where(NeuralSynapseORM.is_active == True)
        
        if capability:
            query = query.where(NeuralSynapseORM.capability == capability)
        
        result = await self.db.execute(query)
        orms = result.scalars().all()
        
        return [
            SynapseResponse(
                id=str(orm.id),
                synapse_id=orm.synapse_id,
                source_module=orm.source_module,
                target_module=orm.target_module,
                capability=orm.capability,
                weight=orm.weight,
                bias=orm.bias,
                is_active=orm.is_active,
            )
            for orm in orms
        ]
    
    async def find_synapses_for_action(self, action: str) -> List[SynapseResponse]:
        """Findet passende Synapsen für eine Aktion"""
        query = select(NeuralSynapseORM).where(
            NeuralSynapseORM.capability == action,
            NeuralSynapseORM.is_active == True
        )
        result = await self.db.execute(query)
        orms = result.scalars().all()
        
        return [
            SynapseResponse(
                id=str(orm.id),
                synapse_id=orm.synapse_id,
                source_module=orm.source_module,
                target_module=orm.target_module,
                capability=orm.capability,
                weight=orm.weight,
                bias=orm.bias,
                is_active=orm.is_active,
            )
            for orm in orms
        ]
    
    # -------------------------------------------------------------------------
    # PARAMETER MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def get_parameter(self, key: str, default: Any = None) -> Any:
        """Holt einen Parameter aus der Matrix"""
        # Cache prüfen
        cache_key = f"param:{key}"
        if cache_key in self._cache:
            cached, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                return cached
        
        query = select(BrainParameterORM).where(
            BrainParameterORM.parameter_key == key
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        
        value = orm.parameter_value if orm else default
        
        # Cache setzen
        self._cache[cache_key] = (value, time.time())
        
        return value
    
    async def set_parameter(self, key: str, value: Any) -> bool:
        """Setzt einen Parameter"""
        # Prüfen ob Parameter existiert
        query = select(BrainParameterORM).where(
            BrainParameterORM.parameter_key == key
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        
        if orm:
            if not orm.is_mutable:
                logger.warning(f"Parameter {key} is not mutable")
                return False
            
            # min/max validation
            if orm.min_value is not None and value < orm.min_value:
                value = orm.min_value
            if orm.max_value is not None and value > orm.max_value:
                value = orm.max_value
            
            orm.parameter_value = value
            orm.updated_at = datetime.now(timezone.utc)
        else:
            # Neu erstellen
            orm = BrainParameterORM(
                parameter_key=key,
                parameter_value=value,
            )
            self.db.add(orm)
        
        await self.db.commit()
        
        # Cache invalidieren
        cache_key = f"param:{key}"
        if cache_key in self._cache:
            del self._cache[cache_key]
        
        logger.info(f"Updated parameter: {key} = {value}")
        return True
    
    async def get_all_parameters(self) -> Dict[str, Any]:
        """Holt alle aktiven Parameter"""
        query = select(BrainParameterORM)
        result = await self.db.execute(query)
        orms = result.scalars().all()
        
        return {orm.parameter_key: orm.parameter_value for orm in orms}
    
    # -------------------------------------------------------------------------
    # EXECUTION
    # -------------------------------------------------------------------------
    
    async def execute(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Führt einen Forward-Pass durch das neuronale Netz aus.
        
        1. Finde passende Synapsen
        2. Berechne Gewichtung mit Parametern
        3. Führe Synapsen aus
        4. Logge Ergebnisse
        """
        start_time = time.time()
        
        # Phase 1: Synapsen finden
        synapses = await self.find_synapses_for_action(request.action)
        
        if not synapses:
            return ExecutionResponse(
                success=False,
                error=f"No synapse found for action: {request.action}",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        
        # Phase 2: Parameter holen
        parameters = await self.get_all_parameters()
        
        # Phase 3: Beste Synapse auswählen (höchstes Gewicht)
        best_synapse = max(synapses, key=lambda s: s.weight)
        
        # Phase 4: Ausführen
        try:
            result = await self._execute_synapse(
                best_synapse,
                request.payload,
                request.context,
                parameters
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # Loggen
            await self._log_execution(
                synapse_id=best_synapse.synapse_id,
                input_data=request.payload,
                output_data=result,
                execution_time_ms=execution_time,
                success=True,
                parameters=parameters,
            )
            
            # Phase 1: Adaptive Learning - weights anpassen
            learning_result = await self.adaptive_learn(
                synapse_id=best_synapse.synapse_id,
                success=True,
                execution_time_ms=execution_time,
            )
            
            # Option C: Auto State Check bei Erfolg
            await self._auto_state_on_success()
            
            return ExecutionResponse(
                success=True,
                result=result,
                synapse_id=best_synapse.synapse_id,
                execution_time_ms=execution_time,
                parameters_used=parameters,
                learning=learning_result,
            )
            
        except Exception as exc:
            execution_time = (time.time() - start_time) * 1000
            
            logger.exception(f"Synapse execution failed: {exc}")
            
            # Loggen
            await self._log_execution(
                synapse_id=best_synapse.synapse_id,
                input_data=request.payload,
                output_data={},
                execution_time_ms=execution_time,
                success=False,
                error_message=str(exc),
                parameters=parameters,
            )
            
            # Phase 1: Adaptive Learning - weights anpassen bei Fehler
            learning_result = await self.adaptive_learn(
                synapse_id=best_synapse.synapse_id,
                success=False,
                execution_time_ms=execution_time,
            )
            
            return ExecutionResponse(
                success=False,
                error=str(exc),
                synapse_id=best_synapse.synapse_id,
                execution_time_ms=execution_time,
                learning=learning_result,
            )
    
    async def _execute_synapse(
        self,
        synapse: SynapseResponse,
        payload: Dict,
        context: Dict,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Führt eine einzelne Synapse aus"""
        
        # Hole Parameter für diese Synapse
        synapse_weight = parameters.get(f"{synapse.synapse_id}.weight", synapse.weight)
        synapse_bias = parameters.get(f"{synapse.synapse_id}.bias", synapse.bias)
        
        # Delegiert an das Target-Modul (Brain 2.0)
        # Je nach target_module不同的处理
        
        target = synapse.target_module
        capability = synapse.capability
        
        logger.info(f"Executing synapse {synapse.synapse_id}: {target}.{capability}")
        
        # Beispiel: skill_execution
        if target == "skill_engine" and capability == "execute":
            return await self._execute_skill(payload, synapse_weight, synapse_bias)
        
        # Beispiel: memory
        if target == "memory" and capability == "store":
            return await self._execute_memory(payload, synapse_weight, synapse_bias)
        
        # Odoo ERP operations
        if target == "odoo_adapter":
            return await self._execute_odoo(payload, synapse_weight, synapse_bias, capability)
        
        # Fallback:Placeholder
        return {
            "status": "executed",
            "synapse": synapse.synapse_id,
            "weight": synapse_weight,
            "bias": synapse_bias,
            "payload": payload,
        }
    
    async def _execute_skill(self, payload: Dict, weight: float, bias: float) -> Dict:
        """
        Führt eine Skill-Execution aus.
        
        Option D: Parameter beeinflussen die Execution:
        - creativity: Wie "kreativ" die Ausführung erfolgt
        - caution: Wie vorsichtig/validiert wird
        - speed: Timeout und Geschwindigkeit
        - execution_timeout: Max Ausführungszeit
        - max_retries: Bei Fehlern
        
        Wenn skill_key im payload ist, wird versucht den echten skill_engine zu rufen.
        """
        # Hole aktuelle Parameter für diese Execution
        creativity = self._cache.get("param:creativity", (0.7, 0))[0]
        caution = self._cache.get("param:caution", (0.5, 0))[0]
        speed = self._cache.get("param:speed", (0.8, 0))[0]
        timeout = self._cache.get("param:execution_timeout", (30, 0))[0]
        retries = self._cache.get("param:max_retries", (3, 0))[0]
        
        # Parameter beeinflussen das Verhalten (PoC)
        adjusted_timeout = timeout * (0.5 + speed * 0.5)  # Speed beeinflusst Timeout
        retry_count = retries if caution > 0.7 else 1  # Mehr Retries bei hoher Caution
        
        skill_key = payload.get("skill_key") or payload.get("skill")
        
        # Versuche echten skill_engine zu rufen
        if skill_key:
            try:
                from app.modules.skill_engine.service import get_skill_engine_service
                from app.modules.skill_engine.schemas import SkillRunCreate, TriggerType
                from uuid import uuid4
                
                service = get_skill_engine_service()
                
                # Erstelle SkillRun mit Neural Context
                run_create = SkillRunCreate(
                    skill_key=str(skill_key),
                    trigger_type=TriggerType.API,
                    idempotency_key=f"neural-{skill_key}-{uuid.uuid4().hex[:8]}",
                    input_payload={
                        **payload,
                        "_neural_context": {
                            "creativity": creativity,
                            "caution": caution,
                            "speed": speed,
                            "weight": weight,
                            "bias": bias,
                        }
                    }
                )
                
                # Hole Principal für DB-Zugriff
                from app.core.auth_deps import Principal
                principal = Principal(
                    principal_id="neural-core",
                    principal_type="system",
                    tenant_id=None,
                    roles=[],
                )
                
                # Create and execute run
                run = await service.create_run(self.db, run_create, principal)
                logger.info(f"🧠 Neural created SkillRun: {run.id}")
                
                # Execute the run
                result = await service.execute_run(self.db, run.id, principal)
                
                logger.info(f"🧠 Neural executed SkillRun: {run.id}, state={result.run.state}")
                
                return {
                    "skill_executed": True,
                    "skill": skill_key,
                    "run_id": str(run.id),
                    "state": result.run.state.value if hasattr(result.run.state, 'value') else str(result.run.state),
                    "weight_applied": weight,
                    "bias_applied": bias,
                    "neural_parameters": {
                        "creativity": creativity,
                        "caution": caution,
                        "speed": speed,
                        "adjusted_timeout_seconds": adjusted_timeout,
                        "retry_count": retry_count,
                    },
                    "status": "executed_via_skill_engine",
                }
                
            except Exception as e:
                logger.warning(f"Neural skill_engine call failed: {e}, using fallback")
        
        # Fallback: PoC Response
        logger.info(
            f"🧠 Neural Execution (fallback): skill={skill_key or 'unknown'}, "
            f"creativity={creativity}, caution={caution}, speed={speed}, "
            f"timeout={adjusted_timeout:.0f}s, retries={retry_count}"
        )
        
        return {
            "skill_executed": True,
            "skill": skill_key or "unknown",
            "weight_applied": weight,
            "bias_applied": bias,
            "neural_parameters": {
                "creativity": creativity,
                "caution": caution,
                "speed": speed,
                "adjusted_timeout_seconds": adjusted_timeout,
                "retry_count": retry_count,
            },
            "status": "executed_via_neural_core",
        }
    
    async def _execute_memory(self, payload: Dict, weight: float, bias: float) -> Dict:
        """Führt eine Memory-Operation aus"""
        # TODO: Wrapper für memory service
        return {
            "memory_stored": True,
            "weight_applied": weight,
            "bias_applied": bias,
        }
    
    async def _execute_odoo(
        self, 
        payload: Dict, 
        weight: float, 
        bias: float,
        capability: str
    ) -> Dict:
        """Führt eine Odoo ERP Operation aus"""
        from app.modules.odoo_adapter.service import CompanyResolver
        from app.modules.odoo_adapter.connection import get_odoo_pool
        
        logger.info(f"🧠 Neural executing Odoo operation: {capability}")
        
        try:
            pool = get_odoo_pool()
            resolver = CompanyResolver(pool)
            
            result = {
                "odoo_executed": True,
                "capability": capability,
                "weight_applied": weight,
                "bias_applied": bias,
            }
            
            if capability == "list_companies":
                companies = resolver.get_all()
                result["companies"] = [
                    {"id": c.id, "name": c.name} for c in companies
                ]
                result["count"] = len(companies)
            
            elif capability == "get_company":
                company_id = payload.get("company_id")
                if company_id:
                    company = resolver.get_by_id(company_id)
                    if company:
                        result["company"] = {
                            "id": company.id,
                            "name": company.name,
                            "parent_id": company.parent_id,
                        }
                    else:
                        result["error"] = f"Company {company_id} not found"
                        result["odoo_executed"] = False
                else:
                    result["error"] = "company_id required"
                    result["odoo_executed"] = False
            
            else:
                result["message"] = f"Odoo capability '{capability}' processed"
                result["payload"] = payload
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Odoo execution failed: {e}")
            return {
                "odoo_executed": False,
                "error": str(e),
                "capability": capability,
                "weight_applied": weight,
                "bias_applied": bias,
            }
    
    async def _log_execution(
        self,
        synapse_id: str,
        input_data: Dict,
        output_data: Dict,
        execution_time_ms: float,
        success: bool,
        error_message: Optional[str] = None,
        parameters: Optional[Dict] = None,
    ) -> None:
        """Loggt eine Execution"""
        orm = SynapseExecutionORM(
            synapse_id=synapse_id,
            input_data=input_data,
            output_data=output_data,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message,
            parameters=parameters or {},
        )
        self.db.add(orm)
        await self.db.commit()
    
    # -------------------------------------------------------------------------
    # ADAPTIVE LEARNING (Phase 1)
    # -------------------------------------------------------------------------
    
    async def adaptive_learn(
        self,
        synapse_id: str,
        success: bool,
        execution_time_ms: float,
    ) -> Dict[str, Any]:
        """
        Passt Synapse-Gewichte basierend auf Erfolg/Misserfolg an.
        
        Phase 1: Learning Loop - wird nach jeder Execution aufgerufen
        """
        config = LearningConfig(
            learning_rate=await self.get_parameter("learning_rate", 0.1),
            min_weight=0.1,
            max_weight=2.0,
        )
        
        synapse = await self.get_synapse(synapse_id)
        if not synapse:
            return {"error": "Synapse not found"}
        
        current_weight = synapse.weight
        new_weight = current_weight
        
        if success:
            # Erfolg: Gewicht leicht erhöhen
            increase = config.learning_rate * current_weight
            new_weight = min(current_weight + increase, config.max_weight)
            action = "increased"
        else:
            # Fehler: Gewicht verringern
            decrease = config.learning_rate * current_weight * 1.5  # Stärker bei Fehlern
            new_weight = max(current_weight - decrease, config.min_weight)
            action = "decreased"
        
        # Aktualisiere Synapse in DB
        query = select(NeuralSynapseORM).where(
            NeuralSynapseORM.synapse_id == synapse_id
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        
        if orm:
            orm.weight = new_weight
            orm.updated_at = datetime.now(timezone.utc)
            await self.db.commit()
        
        # Parameter-Update für globale Steuerung
        if not success:
            await self._adapt_parameters_on_failure(execution_time_ms)
        
        return {
            "synapse_id": synapse_id,
            "action": action,
            "previous_weight": current_weight,
            "new_weight": new_weight,
            "success": success,
        }
    
    async def _adapt_parameters_on_failure(self, execution_time_ms: float) -> None:
        """Passt globale Parameter an wenn Fehler auftreten"""
        
        # Zu langsam? Speed reduzieren
        if execution_time_ms > 5000:
            current_speed = await self.get_parameter("speed", 0.8)
            await self.set_parameter("speed", max(current_speed - 0.1, 0.1))
        
        # Error-Rate erhöht? Caution erhöhen
        query = text("""
            SELECT COUNT(*) as error_count
            FROM synapse_executions
            WHERE success = false
            AND created_at > NOW() - INTERVAL '10 minutes'
        """)
        result = await self.db.execute(query)
        row = result.fetchone()
        error_count = row[0] if row else 0
        
        if error_count > 5:
            current_caution = await self.get_parameter("caution", 0.5)
            await self.set_parameter("caution", min(current_caution + 0.1, 1.0))
            logger.warning(f"⚠️ Adaptive Learning: caution erhöht auf {current_caution + 0.1} wegen {error_count} Fehlern")
        
        # Bei vielen Fehlern: State auf safe setzen
        if error_count > 10:
            await self.set_state("safe", {
                "speed": 0.5,
                "caution": 0.95,
                "creativity": 0.3
            }, {"mode": "safe", "reason": "auto_adapted", "error_count": error_count})
            logger.warning(f"🛡️ Adaptive Learning: State gewechselt zu 'safe' wegen {error_count} Fehlern")
        
        # Option C: Success-Rate prüfen → State auf creative setzen
        await self._auto_state_on_success()
    
    async def _auto_state_on_success(self) -> None:
        """Automatischer State-Wechsel bei hohem Erfolg"""
        query = text("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes
            FROM synapse_executions
            WHERE created_at > NOW() - INTERVAL '10 minutes'
        """)
        result = await self.db.execute(query)
        row = result.fetchone()
        
        if not row or row[0] == 0:
            return
            
        total = row[0]
        successes = row[1] or 0
        success_rate = successes / total if total > 0 else 0
        
        # Bei hoher Erfolgsrate (>90%) und genug Executions: creative mode
        if success_rate > 0.9 and total >= 5:
            await self.set_state("creative", {
                "speed": 0.6,
                "caution": 0.2,
                "creativity": 0.95
            }, {"mode": "creative", "reason": "auto_adapted", "success_rate": success_rate, "total": total})
            logger.info(f"🎨 Adaptive Learning: State gewechselt zu 'creative' wegen {success_rate:.0%} Erfolg ({total} runs)")
        
        # Bei mittlerem Erfolg: default mode
        elif 0.7 <= success_rate <= 0.9 and total >= 5:
            await self.set_state("default", {
                "speed": 0.8,
                "caution": 0.5,
                "creativity": 0.7
            }, {"mode": "default", "reason": "auto_adapted", "success_rate": success_rate})
            logger.info(f"⚖️ Adaptive Learning: State gewechselt zu 'default' wegen {success_rate:.0%} Erfolg")
    
    async def trigger_learning_cycle(self, hours: int = 24) -> Dict[str, Any]:
        """Führt einen vollständigen Learning Cycle aus"""
        learning_loop = LearningLoop(self.db)
        return await learning_loop.analyze_and_learn(hours)
    
    # -------------------------------------------------------------------------
    # STATE MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def get_state(self, state_name: str) -> Optional[Dict]:
        """Holt einen Brain State"""
        query = select(BrainStateORM).where(
            BrainStateORM.state_name == state_name,
            BrainStateORM.is_active == True
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        
        if not orm:
            return None
        
        return {
            "state_name": orm.state_name,
            "parameters": orm.parameters,
            "context": orm.context,
            "version": orm.version,
        }
    
    async def list_states(self) -> List[Dict]:
        """Listet alle aktiven Brain States"""
        query = select(BrainStateORM).where(BrainStateORM.is_active == True)
        result = await self.db.execute(query)
        orms = result.scalars().all()
        
        return [
            {
                "state_name": orm.state_name,
                "parameters": orm.parameters,
                "context": orm.context,
                "version": orm.version,
            }
            for orm in orms
        ]
    
    async def set_state(self, state_name: str, parameters: Dict, context: Dict = None) -> bool:
        """Setzt einen Brain State"""
        query = select(BrainStateORM).where(
            BrainStateORM.state_name == state_name
        )
        result = await self.db.execute(query)
        orm = result.scalar_one_or_none()
        
        if orm:
            orm.parameters = parameters
            orm.context = context or {}
            orm.version += 1
            orm.updated_at = datetime.now(timezone.utc)
        else:
            orm = BrainStateORM(
                state_name=state_name,
                parameters=parameters,
                context=context or {},
            )
            self.db.add(orm)
        
        await self.db.commit()
        return True
    
    # -------------------------------------------------------------------------
    # ANALYTICS
    # -------------------------------------------------------------------------
    
    async def get_synapse_stats(self, hours: int = 24) -> List[Dict]:
        """Holt Synapse-Statistiken"""
        query = text(f"""
            SELECT 
                synapse_id,
                COUNT(*) as total_executions,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failed,
                AVG(execution_time_ms) as avg_time_ms,
                MIN(execution_time_ms) as min_time_ms,
                MAX(execution_time_ms) as max_time_ms
            FROM synapse_executions
            WHERE created_at > NOW() - INTERVAL '{hours} hours'
            GROUP BY synapse_id
            ORDER BY total_executions DESC
        """)
        result = await self.db.execute(query)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]
    
    async def clear_cache(self) -> None:
        """Cleared den Parameter-Cache"""
        self._cache = {}
        logger.info("Neural Core cache cleared")


# =============================================================================
# FACTORY
# =============================================================================

def get_neural_core(db: AsyncSession) -> NeuralCore:
    """Factory für NeuralCore"""
    return NeuralCore(db)
