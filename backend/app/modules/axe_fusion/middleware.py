"""
AXE Fusion Middleware

Injects AXE identity system prompt into chat requests.
Includes session context and preference injection for memory.
"""

from typing import List, Dict, Optional
from app.modules.axe_identity.service import AXEIdentityService
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


class SystemPromptMiddleware:
    """Injects AXE identity system prompt into chat requests with context"""

    def __init__(self, db: AsyncSession):
        self.identity_service = AXEIdentityService(db)
        self.db = db

    async def inject_system_prompt(
        self,
        messages: List[Dict],
        include_knowledge: bool = False,
        max_knowledge_docs: int = 3,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[Dict]:
        """
        Inject active AXE identity system prompt with session context.

        Args:
            messages: Original chat messages
            include_knowledge: Include knowledge docs
            max_knowledge_docs: Max knowledge documents
            session_id: Session ID for context retrieval
            tenant_id: Tenant ID for data isolation

        Returns:
            Messages with system prompt injected
        """
        try:
            # Get active identity
            active_identity = await self.identity_service.get_active()
            if not active_identity:
                active_identity = await self.identity_service.get_default()

            # Build base system content
            system_content = active_identity.system_prompt

            # Add session context if available
            if session_id:
                context_info = await self._build_session_context(session_id, tenant_id)
                if context_info:
                    system_content = self._inject_context_into_prompt(
                        system_content,
                        context_info
                    )

            # TODO: Add knowledge documents when TASK-003 is complete
            # if include_knowledge and knowledge_service_available:
            #     from app.modules.axe_knowledge.service import AXEKnowledgeService
            #     knowledge_service = AXEKnowledgeService(self.db)
            #     top_docs = await knowledge_service.get_top_documents(...)

            # Create system message
            system_message = {"role": "system", "content": system_content}

            # Prepend or replace existing system message
            if messages and messages[0].get("role") == "system":
                messages[0] = system_message
            else:
                messages.insert(0, system_message)

            logger.info(f"Injected system prompt: {active_identity.name}" + 
                       (f" with session context" if session_id else ""))
            return messages

        except Exception as e:
            logger.error(f"Failed to inject system prompt: {e}", exc_info=True)
            try:
                await self.db.rollback()
            except Exception:
                logger.debug("Skipping AXE system prompt rollback cleanup", exc_info=True)
            # Fail-safe: return original messages
            return messages

    async def _build_session_context(
        self,
        session_id: str,
        tenant_id: Optional[str]
    ) -> Optional[Dict]:
        """Build session context from Memory Bridge."""
        try:
            from .memory_bridge import get_axe_memory_bridge
            
            bridge = get_axe_memory_bridge(self.db)
            
            # Get conversation history (last 5 turns)
            context_messages = await bridge.get_session_context(session_id, max_turns=5)
            
            # Get preferences
            preferences = await bridge.get_preferences(session_id)
            
            if not context_messages and not preferences:
                return None
            
            return {
                "messages": context_messages,
                "preferences": preferences,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.debug(f"Failed to build session context: {e}")
            return None

    def _inject_context_into_prompt(
        self,
        base_prompt: str,
        context_info: Dict
    ) -> str:
        """Injects session context into the system prompt."""
        lines = []
        
        # Add context header
        lines.append("\n[SESSION CONTEXT]")
        
        # Add preferences
        prefs = context_info.get("preferences", {})
        if prefs.get("name"):
            lines.append(f"- User prefers to be called: {prefs['name']}")
        if prefs.get("tone"):
            lines.append(f"- Preferred tone: {prefs['tone']}")
        if prefs.get("topics"):
            lines.append(f"- Interested in: {', '.join(prefs['topics'])}")
        
        # Add recent conversation summary
        messages = context_info.get("messages", [])
        if messages:
            recent = messages[-3:]  # Last 3 messages
            summary_parts = []
            for msg in recent:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:50]  # Truncate
                if content:
                    summary_parts.append(f"{role}: {content}")
            
            if summary_parts:
                lines.append("\n[RECENT CONVERSATION]")
                lines.extend(summary_parts)
        
        context_block = "\n".join(lines)
        
        return f"{base_prompt}\n\n{context_block}"
