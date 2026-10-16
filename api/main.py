"""FDAO FastAPI application.

Start with:
    uvicorn api.main:app --reload --port 8000

Interactive docs at: http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import experiments, live, metrics, runs, tasks

app = FastAPI(
    title="FDAO API",
    description="Feedback-Driven Agent Optimizer — observability and control API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],   # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router)
app.include_router(experiments.router)
app.include_router(tasks.router)
app.include_router(metrics.router)
app.include_router(live.router)


@app.get("/health")
def health():
    return {"status": "ok"}
