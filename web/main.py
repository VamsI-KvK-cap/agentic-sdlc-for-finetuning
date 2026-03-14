from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from web.database import engine, Base
from web.executions.router import router
from web.agents.router import router as agent_router

# -------------------------------------------------------------------
# Application lifespan context
# -------------------------------------------------------------------
# FastAPI allows defining startup/shutdown logic using a lifespan context.
# Here, we create database tables automatically on startup if they don't exist.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Begin an async connection to the database
    async with engine.begin() as conn:
        # Create all tables defined in Base.metadata (if they don't exist)
        await conn.run_sync(Base.metadata.create_all)
    # Yield control back to FastAPI; app runs until shutdown
    yield

# -------------------------------------------------------------------
# FastAPI app instance
# -------------------------------------------------------------------
# Basic app metadata for documentation (Swagger UI, ReDoc)
app = FastAPI(
    title="Agentic SDLC API",
    description="API to trigger and track agent executions",
    version="1.0.0",
    lifespan=lifespan,  # use lifespan context to handle startup DB init
)

# ── CORS ───────────────────────────────────────────────────────────────────
# Allows the Next.js dev server (localhost:3000) to call the API (localhost:8000)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://172.21.165.124:3000",
    ],
    allow_credentials=False,  # must be False when using wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# -------------------------------------------------------------------
# Include the executions router
# -------------------------------------------------------------------
# Routes from web.executions.router will be available under /api/v1
# 'tags' is used to group endpoints in the OpenAPI docs
app.include_router(router, prefix='/api/v1', tags=["executions"])
app.include_router(agent_router,prefix='/api/v1', tags=["agents"])

# -------------------------------------------------------------------
# Health check endpoint
# -------------------------------------------------------------------
# Simple GET endpoint to verify the API is running, used by docker, kubernetes etc. for health check.
@app.get("/health")
async def health_check():
    return {"status": "ok"}