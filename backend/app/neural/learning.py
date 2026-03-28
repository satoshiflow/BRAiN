"""
Brain 3.0 - Learning Loop
=========================

Automatisches Lernen basierend auf Erfolg/Misserfolg

Das Gehirn lernt durch:
1. Erfolg -> Gewicht erhöhen
2. Misserfolg -> Gewicht verringern
3. Regelmäßige Anpassung basierend auf Erfolgsrate
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class LearningConfig:
    """Konfiguration für das Lernen"""
    learning_rate: float = 0.1  # Wie schnell gelernt wird
    min_weight: float = 0.1  # Minimum Gewicht
    max_weight: float = 2.0  # Maximum Gewicht
    success_threshold: float = 0.8  # Ab welcher Erfolgsrate lernen?
    failure_threshold: float = 0.3  # Ab welcher Misserfolgsrate zurücksetzen?
    decay_factor: float = 0.95  # Vergessens-Faktor


class LearningLoop:
    """
    Automatischer Learning Loop für Brain 3.0
    
    Lernt aus vergangenen Execution-Ergebnissen und passt:
    - Synapsen-Gewichte
    - Parameter an
    """
    
    def __init__(self, db: AsyncSession, config: Optional[LearningConfig] = None):
        self.db = db
        self.config = config or LearningConfig()
        # Lazy import to avoid circular dependency
        from .core import NeuralCore
        self.core = NeuralCore(db)
    
    async def analyze_and_learn(self, hours: int = 24) -> Dict[str, Any]:
        """
        Analysiert vergangene Executions und lernt
        
        Returns:
            Dict mit Lern-Ergebnissen
        """
        results = {
            "synapses_updated": [],
            "parameters_adjusted": [],
            "insights": []
        }
        
        # Hole alle Executions der letzten Stunden
        query = f"""
            SELECT 
                synapse_id,
                COUNT(*) as total,
                SUM(CASE WHEN success THEN 1 ELSE 0 END) as successes,
                AVG(execution_time_ms) as avg_time,
                MAX(execution_time_ms) as max_time
            FROM synapse_executions
            WHERE created_at > NOW() - INTERVAL '{hours} hours'
            GROUP BY synapse_id
        """
        
        from sqlalchemy import text
        result = await self.db.execute(text(query))
        executions = result.fetchall()
        
        if not executions:
            results["insights"].append("Keine Executions in den letzten {hours} Stunden")
            return results
        
        # Analysiere jede Synapse
        for exec in executions:
            synapse_id = exec[0]
            total = exec[1]
            successes = exec[2]
            avg_time = exec[3] or 0
            max_time = exec[4] or 0
            
            success_rate = successes / total if total > 0 else 0
            
            # Entscheidung basierend auf Erfolgsrate
            if success_rate >= self.config.success_threshold:
                # Erfolgreich -> Gewicht erhöhen
                new_weight = await self._increase_weight(synapse_id)
                results["synapses_updated"].append({
                    "synapse_id": synapse_id,
                    "action": "increased",
                    "success_rate": success_rate,
                    "new_weight": new_weight
                })
                results["insights"].append(
                    f"Synapse {synapse_id}: Erfolgsrate {success_rate:.1%} → Gewicht erhöht"
                )
                
            elif success_rate <= self.config.failure_threshold:
                # Misserfolg -> Gewicht verringern
                new_weight = await self._decrease_weight(synapse_id)
                results["synapses_updated"].append({
                    "synapse_id": synapse_id,
                    "action": "decreased",
                    "success_rate": success_rate,
                    "new_weight": new_weight
                })
                results["insights"].append(
                    f"Synapse {synapse_id}: Erfolgsrate {success_rate:.1%} → Gewicht verringert"
                )
            else:
                # Neutral -> Keine Änderung
                results["insights"].append(
                    f"Synapse {synapse_id}: Erfolgsrate {success_rate:.1%} → stabil"
                )
            
            # Performance-Analyse
            if avg_time > 1000:  # > 1 Sekunde
                results["insights"].append(
                    f"⚠️ {synapse_id}: Lange Ausführungszeit: {avg_time:.0f}ms"
                )
        
        # Parameter-Optimierung basierend auf Verhalten
        await self._optimize_parameters(results)
        
        logger.info(f"🧠 Learning Loop abgeschlossen: {len(results['synapses_updated'])} Synapsen aktualisiert")
        
        return results
    
    async def _increase_weight(self, synapse_id: str) -> float:
        """Erhöht das Gewicht einer Synapse"""
        current = await self.core.get_parameter(f"{synapse_id}.weight", default=1.0)
        
        if current is None:
            current = 1.0
        
        new_weight = min(
            current * (1 + self.config.learning_rate),
            self.config.max_weight
        )
        
        await self.core.set_parameter(f"{synapse_id}.weight", new_weight)
        
        return new_weight
    
    async def _decrease_weight(self, synapse_id: str) -> float:
        """Verringert das Gewicht einer Synapse"""
        current = await self.core.get_parameter(f"{synapse_id}.weight", default=1.0)
        
        if current is None:
            current = 1.0
        
        new_weight = max(
            current * (1 - self.config.learning_rate),
            self.config.min_weight
        )
        
        await self.core.set_parameter(f"{synapse_id}.weight", new_weight)
        
        return new_weight
    
    async def _optimize_parameters(self, results: Dict) -> None:
        """Optimiert globale Parameter basierend auf Verhalten"""
        
        # Speed-Parameter anpassen wenn zu viele Timeouts
        query = """
            SELECT COUNT(*) FROM synapse_executions 
            WHERE execution_time_ms > 5000 
            AND created_at > NOW() - INTERVAL '1 hours'
        """
        
        from sqlalchemy import text
        result = await self.db.execute(text(query))
        timeout_count = result.scalar() or 0
        
        if timeout_count > 10:
            current_timeout = await self.core.get_parameter("execution_timeout", 30)
            await self.core.set_parameter("execution_timeout", min(current_timeout * 1.5, 300))
            results["parameters_adjusted"].append({
                "parameter": "execution_timeout",
                "action": "increased",
                "reason": f"{timeout_count} Timeouts in der letzten Stunde"
            })
        
        # Learning rate anpassen wenn viele Fehler
        query_errors = """
            SELECT COUNT(*) FROM synapse_executions 
            WHERE success = false
            AND created_at > NOW() - INTERVAL '1 hours'
        """
        
        result = await self.db.execute(text(query_errors))
        error_count = result.scalar() or 0
        
        if error_count > 20:
            current_lr = await self.core.get_parameter("learning_rate", 0.3)
            await self.core.set_parameter("learning_rate", max(current_lr * 0.8, 0.05))
            results["parameters_adjusted"].append({
                "parameter": "learning_rate",
                "action": "decreased",
                "reason": f"{error_count} Fehler in der letzten Stunde"
            })
    
    async def reset_learned_weights(self) -> None:
        """Setzt alle gelernten Gewichte auf Standard zurück"""
        # Alle Synapsen-Parameter zurücksetzen
        query = select(BrainParameterORM).where(
            BrainParameterORM.parameter_key.like("%.weight")
        )
        
        result = await self.db.execute(query)
        params = result.scalars().all()
        
        for param in params:
            # Extrahiere Synapse-ID
            synapse_id = param.parameter_key.replace(".weight", "")
            # Setze auf Standard zurück
            await self.core.set_parameter(param.parameter_key, 1.0)
        
        logger.info(f"🧠 Gelernte Gewichte zurückgesetzt: {len(params)} Parameter")


# Factory
def get_learning_loop(db: AsyncSession, config: Optional[LearningConfig] = None) -> LearningLoop:
    """Factory für LearningLoop"""
    return LearningLoop(db, config)
