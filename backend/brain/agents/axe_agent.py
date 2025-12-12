
# backend/brain/agents/axe_agent.py

from typing import Any, Dict
from .base_agent import BaseAgent


class AxeAgent(BaseAgent):
    """
    Axe – der Chat-Agent für das Control Deck.

    Aufgabe:
    - Freies Chatten über Systemstatus, Missionen, Agenten.
    - Kann später Missionen anlegen, Logs lesen etc.
    """

    def __init__(self, llm_client, *args, **kwargs):
        super().__init__(
            name="Axe",
            description="Conversational System Assistant für das BRAIN Control Deck",
            role="CHAT_ASSISTANT",
            llm_client=llm_client,
            *args,
            **kwargs,
        )

        # Basis-Systemprompt
        self.system_prompt = (
            "Du bist Axe, der System-Assistent im BRAIN Control Deck. "
            "Du kennst das BRAIN-Framework, Missionen, Agenten und den technischen Stack. "
            "Sprich klar, präzise und freundlich. Wenn du etwas nicht weißt, sag es offen."
        )

    async def chat(self, message: str, context: Dict[str, Any] | None = None) -> str:
        """
        Einfache Chat-Schnittstelle.
        """
        context = context or {}
        user_message = f"User: {message}\n\nKontext: {context}"

        result = await self.call_llm(
            system_prompt=self.system_prompt,
            user_message=user_message,
        )

        return result.text  # abhängig davon, wie dein LLM-Client antwortet
