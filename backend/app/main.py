from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.lifecycle import lifespan
from app.api.routes import include_all_routers

from app.modules.dna.router import router as dna_router
from app.modules.karma.router import router as karma_router
from app.modules.immune.router import router as immune_router


settings = get_settings()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    include_all_routers(app)

    # Module-Router explizit einhängen
    app.include_router(dna_router)
    app.include_router(karma_router)
    app.include_router(immune_router)

    return app

app = create_app()
