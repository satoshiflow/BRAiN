# Minimal BRAiN Mock Server for Frontend Development
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="BRAiN Mock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {"status": "healthy", "version": "0.3.0-mock"}

@app.get("/api/agents")
def list_agents():
    return [
        {"id": "agent-1", "name": "Health Monitor", "type": "health", "status": "running"},
        {"id": "agent-2", "name": "Test Agent", "type": "test", "status": "idle"}
    ]

@app.post("/api/agents/{agent_id}/execute")
def execute_agent(agent_id: str):
    return {"success": True, "agent_id": agent_id, "result": "Task executed"}

@app.get("/api/missions")
def list_missions():
    return [
        {"id": "mission-1", "name": "Test Mission", "status": "completed", "progress": 100}
    ]

@app.post("/api/missions/create")
def create_mission():
    return {"success": True, "mission_id": "mission-new", "status": "created"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
