from fastapi import FastAPI
from .api import router

def register_module(app: FastAPI):
    app.include_router(router, prefix="/api/missions", tags=["missions"])
