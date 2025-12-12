# BRAiN – Lokale Dev-Umgebung

## Architektur

- `backend/`
  - `main.py` – zentrale FastAPI-App, Autodiscovery der Router
  - `api/routes/` – REST-Endpunkte
    - `missions.py` – Missions-Queue (Redis)
    - `agent_manager.py` – Agenten-Chat API
    - `axe.py` – Execution Engine (Gateway + LLM-Fallback)
    - `connectors.py` – Infos zu verfügbaren Connectoren
    - `debug_llm.py` – LLM-Debug / Healthcheck
  - `modules/`
    - `llm_client.py` – zentraler LLM-Client (Ollama)
    - `connector_hub/` – Gateway-Logik (Stub / zukünftige Erweiterung)

- `frontend/`
  - `brain_control_ui/` – Control Deck (Admin / Debug)
    - Bietet u. a.:
      - `/brain/debug` – Backend-Integrations-Tests (Health, Missions, AXE)
      - `/debug/llm` – End-to-End LLM-Test (UI → Backend → Ollama)
  - `brain_ui/` – User-Facing Chat UI (später Hauptinterface für BRAiN)

## Start (Dev)

```bash
# Projekt-Root
docker compose down
docker compose up -d --build
