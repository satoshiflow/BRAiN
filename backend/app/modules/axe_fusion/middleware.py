"""
AXE Fusion Middleware

Injects AXE identity system prompt into chat requests.
Knowledge integration will be added in TASK-003.
"""

from typing import List, Dict
from app.modules.axe_identity.service import AXEIdentityService
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


class SystemPromptMiddleware:
    """Injects AXE identity system prompt into chat requests"""

    def __init__(self, db: AsyncSession):
        self.identity_service = AXEIdentityService(db)
        self.db = db

    async def inject_system_prompt(
        self,
        messages: List[Dict],
        include_knowledge: bool = False,  # Disabled until TASK-003
        max_knowledge_docs: int = 3
    ) -> List[Dict]:
        """
        Inject active AXE identity system prompt into messages.

        Args:
            messages: Original chat messages
            include_knowledge: Include knowledge docs (requires TASK-003)
            max_knowledge_docs: Max knowledge documents to include

        Returns:
            Messages with system prompt injected
        """
        try:
            # Get active identity
            active_identity = await self.identity_service.get_active()
            if not active_identity:
                active_identity = await self.identity_service.get_default()

            # Build system content
            system_content = active_identity.system_prompt

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

            logger.info(f"Injected system prompt: {active_identity.name}")
            return messages

        except Exception as e:
            logger.error(f"Failed to inject system prompt: {e}", exc_info=True)
            # Fail-safe: return original messages
            return messages
