from __future__ import annotations

from fastapi import APIRouter

from api.db import get_aggregate_metrics
from api.schemas import AggregateMetricsSchema

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/aggregate", response_model=AggregateMetricsSchema)
def aggregate_metrics():
    return get_aggregate_metrics()
