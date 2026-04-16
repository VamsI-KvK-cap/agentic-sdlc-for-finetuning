"""
Agentic SDLC API Application Module.

This module initializes and configures the FastAPI application for the Agentic SDLC system.
It sets up the database context manager for automatic table creation, configures CORS middleware
for cross-origin requests, and includes routers for executions and agents endpoints.

The application provides REST API endpoints to trigger and track agent executions in the
fine-tuning pipeline.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web.database import Base, engine
from web.agents.router import router as agent_router
from web.executions.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events (startup and shutdown).

    This context manager handles database initialization on startup. It establishes an async
    connection to the database engine and creates all SQLAlchemy ORM model tables defined in
    Base.metadata if they don't already exist. After yielding control to FastAPI, the
    application runs normally until shutdown is triggered.

    Args:
        app (FastAPI): The FastAPI application instance being initialized.

    Yields:
        None: Yields control to allow the FastAPI application to run.

    Example:
        The lifespan context is passed to the FastAPI app constructor to automatically
        initialize the database when the server starts.
    """
    # Establish async database connection for initialization
    async with engine.begin() as conn:
        # Create all SQLAlchemy tables from metadata if they don't exist (idempotent)
        await conn.run_sync(Base.metadata.create_all)
    # Yield control to FastAPI; application runs until shutdown is triggered
    yield

# Initialize FastAPI application with metadata and lifespan manager
app: FastAPI = FastAPI(
    title="Agentic SDLC API",
    description="API to trigger and track agent executions in the fine-tuning pipeline",
    version="1.0.0",
    lifespan=lifespan,  # Lifecycle context manager handles database initialization on startup
)
# Configure CORS middleware to allow cross-origin requests from the Next.js frontend
# Allows requests from localhost:3000 (development), 127.0.0.1:3000 (loopback), and 172.21.165.124:3000 (Docker network)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",          # Development frontend (localhost)
        "http://127.0.0.1:3000",          # Development frontend (loopback)
        "http://172.21.165.124:3000",     # Development frontend (Docker bridge network)
    ],
    allow_credentials=False,  # Must be False when allow_origins is not a wildcard
    allow_methods=["*"],      # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],      # Allow all request headers
)

# Include API routers with versioning and grouping
# Executions router provides endpoints for managing execution workflows (/api/v1/executions/...)
app.include_router(router, prefix='/api/v1', tags=["executions"])
# Agents router provides endpoints for agent management (/api/v1/agents/...)
app.include_router(agent_router, prefix='/api/v1', tags=["agents"])

@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint for application availability verification.

    This endpoint is used by load balancers, Kubernetes probes, Docker health checks, and
    monitoring systems to verify that the API is running and responsive. Returns a simple
    JSON response with status information.

    Returns:
        dict[str, str]: A dictionary containing the application health status.
            - "status" (str): The health status string, returns "ok" if service is running.

    Example:
        GET /health
        Response: {"status": "ok"}
    """
    # Return success status indicating the API is operational
    return {"status": "ok"}