"""
BRAIN Mission System V1 - Redis Priority Queue
===============================================

Redis-basierte Priority Queue für Missions.
Nutzt Redis ZSET für Score-basiertes Sorting.

Features:
- Priority Scoring (kombiniert Priority + Age + Credits)
- Atomic Operations
- Stats & Monitoring
- Dead Letter Queue

Author: Claude (Chief Developer)
Created: 2025-11-11
"""

import json
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis

from .models import Mission, MissionStatus, QueueStats


class MissionQueue:
    """
    Redis-basierte Priority Queue für Missions.
    
    Verwendet Redis ZSET mit Score-basiertem Sorting.
    Score = f(priority, age, credits)
    """
    
    # Queue Keys
    MAIN_QUEUE = "mission_queue"
    PROCESSING_SET = "mission_processing"
    DEAD_LETTER_QUEUE = "mission_dlq"
    STATS_KEY = "mission_queue_stats"
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize Queue Manager.
        
        Args:
            redis_client: Async Redis Client
        """
        self.redis = redis_client
    
    
    async def enqueue(self, mission: Mission) -> bool:
        """
        Fügt Mission in Priority Queue ein.
        
        Args:
            mission: Mission Object
            
        Returns:
            True wenn erfolgreich
        """
        try:
            # Calculate Priority Score
            score = mission.calculate_priority_score()
            
            # Serialize Mission
            mission_json = mission.model_dump_json()
            
            # Add to ZSET (atomic)
            await self.redis.zadd(
                self.MAIN_QUEUE,
                {mission_json: score}
            )
            
            # Update Stats
            await self._update_stats("enqueued", mission.type)
            
            # Update Mission Status
            mission.update_status(
                MissionStatus.QUEUED,
                f"Added to queue with score {score:.2f}"
            )
            
            return True
            
        except Exception as e:
            print(f"Error enqueueing mission {mission.id}: {e}")
            return False
    
    
    async def dequeue(
        self, 
        blocking: bool = False,
        timeout: int = 5
    ) -> Optional[Mission]:
        """
        Holt Mission mit höchster Priorität aus Queue.
        
        Args:
            blocking: Wenn True, warte bis Mission verfügbar
            timeout: Max Wartezeit in Sekunden (nur bei blocking=True)
            
        Returns:
            Mission oder None
        """
        try:
            if blocking:
                # BZPOPMAX: Blocking Pop mit Timeout
                result = await self.redis.bzpopmax(
                    self.MAIN_QUEUE,
                    timeout=timeout
                )
                
                if not result:
                    return None
                
                _, mission_json, score = result
                
            else:
                # ZPOPMAX: Non-blocking Pop
                result = await self.redis.zpopmax(self.MAIN_QUEUE, count=1)
                
                if not result:
                    return None
                
                mission_json, score = result[0]
            
            # Deserialize Mission
            mission_dict = json.loads(mission_json)
            mission = Mission(**mission_dict)
            
            # Move to Processing Set
            await self._mark_processing(mission)
            
            # Update Stats
            await self._update_stats("dequeued", mission.type)
            
            return mission
            
        except Exception as e:
            print(f"Error dequeuing mission: {e}")
            return None
    
    
    async def get_pending_count(self) -> int:
        """Anzahl wartender Missions."""
        return await self.redis.zcard(self.MAIN_QUEUE)
    
    
    async def get_processing_count(self) -> int:
        """Anzahl aktuell bearbeiteter Missions."""
        return await self.redis.scard(self.PROCESSING_SET)
    
    
    async def peek(self, count: int = 10) -> List[Mission]:
        """
        Zeigt Top-N Missions ohne sie zu entfernen.
        
        Args:
            count: Anzahl zu returnen
            
        Returns:
            List von Mission Objects
        """
        try:
            # ZREVRANGE: Get highest scores
            results = await self.redis.zrevrange(
                self.MAIN_QUEUE,
                0,
                count - 1,
                withscores=True
            )
            
            missions = []
            for mission_json, score in results:
                mission_dict = json.loads(mission_json)
                mission = Mission(**mission_dict)
                missions.append(mission)
            
            return missions
            
        except Exception as e:
            print(f"Error peeking queue: {e}")
            return []
    
    
    async def complete_mission(self, mission: Mission) -> bool:
        """
        Markiert Mission als abgeschlossen.
        
        Entfernt aus Processing Set.
        
        Args:
            mission: Abgeschlossene Mission
            
        Returns:
            True wenn erfolgreich
        """
        try:
            # Remove from Processing
            await self.redis.srem(
                self.PROCESSING_SET,
                mission.id
            )
            
            # Update Stats
            await self._update_stats("completed", mission.type)
            
            return True
            
        except Exception as e:
            print(f"Error completing mission {mission.id}: {e}")
            return False
    
    
    async def fail_mission(
        self, 
        mission: Mission,
        retry: bool = True
    ) -> bool:
        """
        Markiert Mission als fehlgeschlagen.
        
        Args:
            mission: Fehlgeschlagene Mission
            retry: Wenn True und retries verfügbar, re-enqueue
            
        Returns:
            True wenn erfolgreich
        """
        try:
            # Remove from Processing
            await self.redis.srem(
                self.PROCESSING_SET,
                mission.id
            )
            
            # Check Retry Logic
            if retry and mission.retry_count < mission.max_retries:
                mission.retry_count += 1
                mission.update_status(
                    MissionStatus.QUEUED,
                    f"Retry {mission.retry_count}/{mission.max_retries}"
                )
                
                # Re-enqueue with lower priority
                await self.enqueue(mission)
                await self._update_stats("retried", mission.type)
                
            else:
                # Move to Dead Letter Queue
                await self._move_to_dlq(mission)
                await self._update_stats("failed", mission.type)
            
            return True
            
        except Exception as e:
            print(f"Error failing mission {mission.id}: {e}")
            return False
    
    
    async def get_stats(self) -> QueueStats:
        """
        Holt Queue-Statistiken.
        
        Returns:
            QueueStats Object
        """
        try:
            # Basic Counts
            total_pending = await self.get_pending_count()
            total_processing = await self.get_processing_count()
            
            # Status Breakdown
            by_status = {
                "queued": total_pending,
                "processing": total_processing
            }
            
            # Get Missions for detailed stats
            missions = await self.peek(count=100)
            
            # By Priority
            by_priority = {}
            for mission in missions:
                pri = mission.priority.name
                by_priority[pri] = by_priority.get(pri, 0) + 1
            
            # By Type
            by_type = {}
            for mission in missions:
                by_type[mission.type] = by_type.get(mission.type, 0) + 1
            
            # Oldest Mission
            oldest_age = None
            if missions:
                oldest = max(missions, key=lambda m: m.created_at)
                age_delta = datetime.utcnow() - oldest.created_at
                oldest_age = age_delta.total_seconds() / 60
            
            return QueueStats(
                total_missions=total_pending + total_processing,
                by_status=by_status,
                by_priority=by_priority,
                by_type=by_type,
                oldest_mission_age_minutes=oldest_age
            )
            
        except Exception as e:
            print(f"Error getting stats: {e}")
            return QueueStats(
                total_missions=0,
                by_status={},
                by_priority={},
                by_type={}
            )
    
    
    # Internal Helper Methods
    
    async def _mark_processing(self, mission: Mission):
        """Markiert Mission als in Bearbeitung."""
        await self.redis.sadd(
            self.PROCESSING_SET,
            mission.id
        )
        
        # Set TTL als Timeout-Protection
        # Wenn Mission nach 1h noch in Processing, ist was schief
        await self.redis.expire(
            f"{self.PROCESSING_SET}:{mission.id}",
            3600  # 1 Stunde
        )
    
    
    async def _move_to_dlq(self, mission: Mission):
        """Verschiebt Mission in Dead Letter Queue."""
        mission_json = mission.model_dump_json()
        
        await self.redis.zadd(
            self.DEAD_LETTER_QUEUE,
            {mission_json: time.time()}
        )
    
    
    async def _update_stats(self, event: str, mission_type: str):
        """Updated Queue-Statistiken."""
        stats_key = f"{self.STATS_KEY}:{event}:{mission_type}"
        
        await self.redis.incr(stats_key)
        
        # Set TTL auf Stats (7 Tage)
        await self.redis.expire(stats_key, 604800)
    
    
    async def cleanup_stale_processing(self, max_age_hours: int = 2):
        """
        Cleanup für hängende Processing-Missions.
        
        Sollte regelmäßig (z.B. hourly) aufgerufen werden.
        
        Args:
            max_age_hours: Max Alter bevor Mission als stale gilt
        """
        # TODO: Implementierung für Stale-Detection
        # Würde alle Processing-Missions checken und
        # die zu alten zurück in Queue oder DLQ verschieben
        pass


# Convenience Functions

async def create_queue(redis_url: str = "redis://redis:6379/0") -> MissionQueue:
    """
    Factory Function für MissionQueue.
    
    Args:
        redis_url: Redis Connection URL
        
    Returns:
        Configured MissionQueue
    """
    redis_client = await redis.from_url(redis_url)
    return MissionQueue(redis_client)
