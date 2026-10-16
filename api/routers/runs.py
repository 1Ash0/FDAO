from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.db import get_all_runs, get_run_steps, get_run_meta
from api.events import bus, format_sse
from api.schemas import RunSummarySchema, RunDetailSchema, StepSchema

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=list[RunSummarySchema])
def list_runs():
    return get_all_runs()


@router.get("/{run_id}", response_model=RunDetailSchema)
def get_run(run_id: str):
    meta = get_run_meta(run_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = get_run_steps(run_id)
    return {
        **meta,
        "steps": steps,
    }


@router.get("/{run_id}/steps", response_model=list[StepSchema])
def get_steps(run_id: str):
    steps = get_run_steps(run_id)
    if not steps:
        raise HTTPException(status_code=404, detail="Run not found or has no steps")
    return steps


@router.get("/{run_id}/stream")
async def stream_run(run_id: str):
    """SSE endpoint — streams step events as the run executes."""
    async def generate():
        async for event in bus.subscribe(run_id):
            yield format_sse(event)
        yield format_sse({"event": "done", "run_id": run_id})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
