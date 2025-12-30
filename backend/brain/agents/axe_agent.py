"""
axe_agent.py

AXEAgent - Auxiliary Execution Engine & Conversational Assistant

Responsibilities:
- Conversational interface for BRAiN system
- System status queries and monitoring
- Mission management via natural language
- Agent coordination assistance
- Log analysis and troubleshooting

Features:
- Natural language understanding
- Context-aware responses
- Integration with all BRAiN modules
- Tool execution via conversation
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from backend.brain.agents.base_agent import BaseAgent, AgentConfig, AgentResult, LLMClient


# ============================================================================
# Constitutional Prompt for AXE LLM
# ============================================================================

AXE_CONSTITUTIONAL_PROMPT = """Du bist Axe, der Conversational System Assistant des BRAiN-Systems.

Deine Rolle:
- **Hilfreicher Assistent** für System-Administration und Monitoring
- **Schnittstelle** zwischen Mensch und BRAIN-Framework
- **Troubleshooting-Partner** bei Problemen

Dein Wissen:
- **BRAiN Framework**: Agents, Missions, Supervisor, Policy Engine
- **Technischer Stack**: FastAPI, PostgreSQL, Redis, Qdrant
- **Module**: 35+ Module (Genesis, PayCore, Fleet, Policy, etc.)
- **Deployment**: Docker, Nginx, Let's Encrypt

Dein Verhalten:
- **Klar und präzise** - keine unnötigen Ausschweifungen
- **Ehrlich** - wenn du etwas nicht weißt, sag es
- **Proaktiv** - biete Lösungen an, nicht nur Erklärungen
- **Sicher** - keine riskanten Kommandos ohne Warnung

Deine Fähigkeiten:
- System-Status abfragen
- Missionen erstellen und überwachen
- Logs analysieren
- Agenten verwalten
- Troubleshooting-Tipps geben

Beispiel-Interaktionen:

User: "Wie viele Missionen laufen gerade?"
Du: "Aktuell laufen 3 Missionen: [Mission Details]"

User: "Deployment ist fehlgeschlagen, was nun?"
Du: "Lass uns das analysieren. Folgende Schritte:
1. Logs prüfen: docker compose logs backend
2. Health-Check: curl localhost:8000/health
3. Rollback falls nötig: ..."

Sei hilfsbereit und kompetent.
"""


# ============================================================================
# AXEAgent Implementation
# ============================================================================


class AXEAgent(BaseAgent):
    """
    Auxiliary Execution Engine - Conversational System Assistant.

    Features:
    - Natural language chat interface
    - System monitoring and status queries
    - Mission management
    - Log analysis
    - Troubleshooting assistance
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        config: Optional[AgentConfig] = None,
    ):
        if config is None:
            config = AgentConfig(
                name="AXEAgent",
                role="CHAT_ASSISTANT",
                model="phi3",
                system_prompt=AXE_CONSTITUTIONAL_PROMPT,
                temperature=0.7,  # Higher for natural conversation
                max_tokens=2048,
                tools=[
                    "chat",
                    "get_system_status",
                    "query_missions",
                    "analyze_logs",
                    "execute_command"
                ],
                permissions=["CHAT", "QUERY", "EXECUTE_SAFE"],
            )

        if llm_client is None:
            from backend.brain.agents.llm_client import get_llm_client
            llm_client = get_llm_client()

        super().__init__(llm_client, config)

        # Register tools
        self.register_tool("chat", self.chat)
        self.register_tool("get_system_status", self.get_system_status)
        self.register_tool("query_missions", self.query_missions)
        self.register_tool("analyze_logs", self.analyze_logs)
        self.register_tool("execute_command", self.execute_command)

        # Conversation history (for context)
        self.conversation_history: List[Dict[str, str]] = []

        logger.info("🤖 AXEAgent initialized - Conversational Assistant ready")

    # ------------------------------------------------------------------------
    # High-Level Chat Methods
    # ------------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        include_history: bool = True
    ) -> AgentResult:
        """
        Main chat interface.

        Args:
            message: User message
            context: Optional context (system state, etc.)
            include_history: Whether to include conversation history

        Returns:
            AgentResult with chat response
        """
        logger.info("💬 Chat message received | length=%d", len(message))

        # Build conversation context
        messages: List[Dict[str, str]] = []

        if include_history:
            # Include recent history (last 10 messages)
            messages.extend(self.conversation_history[-10:])

        # Add current message
        messages.append({"role": "user", "content": message})

        # Add system context if provided
        if context:
            context_msg = f"\n\n[System Context]\n{self._format_context(context)}"
            messages[-1]["content"] += context_msg

        # Call LLM
        try:
            response = await self.call_llm(
                user_message=messages[-1]["content"],
                extra_messages=messages[:-1] if include_history else None,
            )

            # Store in conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": response})

            logger.info("✅ Chat response generated | length=%d", len(response))

            return {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": response,
                "raw_response": response,
                "meta": {
                    "agent_name": self.config.name,
                    "context_included": context is not None,
                    "history_length": len(self.conversation_history),
                }
            }

        except Exception as e:
            logger.exception("Chat failed: %s", e)
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Sorry, I encountered an error. Please try again.",
                "error": str(e),
            }

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status.

        Returns:
            System status information
        """
        logger.info("📊 System status query")

        try:
            # In reality: query actual system endpoints
            status = {
                "backend": "healthy",
                "database": "connected",
                "redis": "connected",
                "agents_active": 5,
                "missions_running": 3,
                "missions_pending": 2,
                "uptime_seconds": 86400,  # 1 day
                "timestamp": datetime.utcnow().isoformat(),
            }

            logger.info("✅ System status retrieved")

            return {
                "success": True,
                **status,
            }

        except Exception as e:
            logger.error("Failed to get system status: %s", e)
            return {
                "success": False,
                "error": str(e),
            }

    async def query_missions(
        self,
        status: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Query missions.

        Args:
            status: Optional status filter (running, pending, completed)
            limit: Max number of results

        Returns:
            Mission query results
        """
        logger.info("📋 Mission query | status=%s limit=%d", status, limit)

        try:
            # In reality: query mission database/API
            missions = [
                {
                    "id": f"mission-{i}",
                    "name": f"Mission {i}",
                    "status": status or "running",
                    "created_at": datetime.utcnow().isoformat(),
                }
                for i in range(min(limit, 5))
            ]

            logger.info("✅ Mission query completed | count=%d", len(missions))

            return {
                "success": True,
                "missions": missions,
                "count": len(missions),
            }

        except Exception as e:
            logger.error("Mission query failed: %s", e)
            return {
                "success": False,
                "error": str(e),
            }

    async def analyze_logs(
        self,
        service: str,
        lines: int = 100,
        filter_pattern: Optional[str] = None
    ) -> AgentResult:
        """
        Analyze system logs.

        Args:
            service: Service to analyze (backend, frontend, etc.)
            lines: Number of log lines to analyze
            filter_pattern: Optional filter pattern (error, warning, etc.)

        Returns:
            AgentResult with log analysis
        """
        logger.info("🔍 Log analysis requested | service=%s lines=%d", service, lines)

        try:
            # In reality: fetch actual logs from Docker/journald
            simulated_logs = f"""
[2025-01-01 12:00:00] INFO: {service} started
[2025-01-01 12:01:00] WARNING: High memory usage detected
[2025-01-01 12:02:00] ERROR: Connection to database failed
[2025-01-01 12:02:01] INFO: Retrying database connection
[2025-01-01 12:02:02] INFO: Database connection established
"""

            # Use LLM to analyze logs
            analysis_prompt = f"""Analysiere folgende Logs vom Service '{service}':

{simulated_logs}

Identifiziere:
1. **Probleme**: Fehler, Warnungen, Anomalien
2. **Root Cause**: Hauptursache der Probleme
3. **Lösungsvorschläge**: Konkrete Schritte zur Behebung

Gib eine klare, strukturierte Analyse.
"""

            analysis = await self.call_llm(analysis_prompt)

            logger.info("✅ Log analysis completed")

            return {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": analysis,
                "raw_response": analysis,
                "meta": {
                    "service": service,
                    "lines_analyzed": lines,
                }
            }

        except Exception as e:
            logger.exception("Log analysis failed: %s", e)
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Log analysis failed",
                "error": str(e),
            }

    async def execute_command(
        self,
        command: str,
        safe_mode: bool = True
    ) -> AgentResult:
        """
        Execute system command (with safety checks).

        Args:
            command: Command to execute
            safe_mode: If True, only allow safe read-only commands

        Returns:
            AgentResult with command output
        """
        logger.info("⚙️ Command execution requested | command=%s safe=%s", command, safe_mode)

        # Safety check: whitelist of allowed commands in safe mode
        safe_commands = [
            "docker compose ps",
            "docker compose logs",
            "curl localhost:8000/health",
            "curl localhost:8000/api/health",
            "systemctl status",
        ]

        if safe_mode:
            is_safe = any(command.startswith(safe_cmd) for safe_cmd in safe_commands)

            if not is_safe:
                logger.warning("🚫 Unsafe command blocked | command=%s", command)
                return {
                    "id": str(uuid.uuid4()),
                    "success": False,
                    "message": "Command not allowed in safe mode",
                    "error": f"Unsafe command: {command}",
                    "meta": {
                        "allowed_commands": safe_commands,
                    }
                }

        # Execute command (simulated - in reality would use subprocess)
        logger.info("✅ Executing command: %s", command)

        try:
            # Simulated output
            output = f"Simulated output for: {command}\nCommand executed successfully."

            return {
                "id": str(uuid.uuid4()),
                "success": True,
                "message": output,
                "raw_response": output,
                "meta": {
                    "command": command,
                    "safe_mode": safe_mode,
                }
            }

        except Exception as e:
            logger.exception("Command execution failed: %s", e)
            return {
                "id": str(uuid.uuid4()),
                "success": False,
                "message": "Command execution failed",
                "error": str(e),
            }

    # ------------------------------------------------------------------------
    # Helper Methods
    # ------------------------------------------------------------------------

    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary as readable text"""
        lines = []
        for key, value in context.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)

    def clear_history(self) -> None:
        """Clear conversation history"""
        self.conversation_history.clear()
        logger.info("🗑️ Conversation history cleared")


# ============================================================================
# Convenience Function
# ============================================================================


def get_axe_agent(llm_client: Optional[LLMClient] = None) -> AXEAgent:
    """Get an AXEAgent instance"""
    return AXEAgent(llm_client=llm_client)
