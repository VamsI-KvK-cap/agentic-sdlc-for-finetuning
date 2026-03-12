from fastapi import FastAPI
from contextlib import asynccontextmanager
from web.database import engine, Base
from web.executions.router import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Agentic SDLC API",
    description="API to trigger and track coding agent executions",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router, prefix="/api/v1", tags=["executions"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
