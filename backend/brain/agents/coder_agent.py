from .base_agent import BaseAgent, AgentConfig, AgentResult

class CoderAgent(BaseAgent):
    def __init__(self, llm_client, config: AgentConfig):
        super().__init__(llm_client, config)
        # Beispiel-Tool registrieren
        self.register_tool("create_file", self.create_file)

    def create_file(self, path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    async def implement_feature(self, spec: str) -> AgentResult:
        # hier würdest du LLM + Tools kombinieren
        return await self.run(f"Implementiere folgenden Feature-Wunsch:\n\n{spec}")


# Ende von coder_agent.py Beispiel coder_agent.py (nur als Mini-Skizze):