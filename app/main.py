from fastapi import FastAPI
from app.api.routes import router
from app.db.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PO Backlog Architect Agent API",
    description="Enterprise PO agent backend supporting grounded criteria generation, epic decomposition, Definition of Ready enforcement, deterministic prioritization, and human approval gating.",
    version="1.0.0"
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "PO Backlog Architect Agent API is running",
        "docs": "/docs",
        "health": "OK"
    }
