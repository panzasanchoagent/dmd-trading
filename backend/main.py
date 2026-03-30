"""
Trading Journal Backend
FastAPI application for personal trading execution system.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings

app = FastAPI(
    title="Trading Journal",
    description="Personal trading execution system with AI coaching",
    version="0.1.0"
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "trading-journal"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Trading Journal API",
        "version": "0.1.0",
        "docs": "/docs"
    }


# Router imports (uncomment as implemented)
# from routers import trades, portfolio, journal, principles, coach
# app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
# app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
# app.include_router(journal.router, prefix="/api/journal", tags=["journal"])
# app.include_router(principles.router, prefix="/api/principles", tags=["principles"])
# app.include_router(coach.router, prefix="/api/coach", tags=["coach"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
