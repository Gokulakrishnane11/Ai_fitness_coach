"""
FastAPI Main Application Entry Point.
Configures CORS middleware, registers routers, and sets up health check endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.modules.profile import router as profile_router
from app.modules.planning import router as planning_router
from app.modules.simulation import router as simulation_router
from app.modules.progress import router as progress_router
from app.modules.coaching import router as coaching_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Production-grade decoupled REST API backend for AI Fitness Application V1",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(profile_router, prefix=settings.API_V1_STR)
app.include_router(planning_router, prefix=settings.API_V1_STR)
app.include_router(simulation_router, prefix=settings.API_V1_STR)
app.include_router(progress_router, prefix=settings.API_V1_STR)
app.include_router(coaching_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for container monitoring."""
    return {"status": "online", "app": settings.PROJECT_NAME, "version": "1.0.0"}
