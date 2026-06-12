import asyncio
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api import schemas
from application.translation_benchmark_service import (
    TranslationBenchmarkService,
    execute_benchmark_run,
)
from infrastructure.db.session import get_db


router = APIRouter()


@router.get(
    "/translation-benchmarks",
    response_model=List[schemas.TranslationBenchmarkResponse],
)
def list_translation_benchmarks(limit: int = 20, db: Session = Depends(get_db)):
    return TranslationBenchmarkService(db).list_runs(limit)


@router.get(
    "/translation-benchmarks/{run_id}",
    response_model=schemas.TranslationBenchmarkResponse,
)
def get_translation_benchmark(run_id: str, db: Session = Depends(get_db)):
    run = TranslationBenchmarkService(db).get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    return run


@router.post(
    "/translation-benchmarks",
    response_model=schemas.TranslationBenchmarkResponse,
)
async def create_translation_benchmark(
    payload: schemas.TranslationBenchmarkCreate,
    db: Session = Depends(get_db),
):
    if len(set(payload.account_ids)) < 2:
        raise HTTPException(status_code=400, detail="Select at least two AI accounts")
    try:
        run = TranslationBenchmarkService(db).create_run(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    asyncio.create_task(asyncio.to_thread(execute_benchmark_run, run.id))
    return run


@router.post(
    "/translation-benchmarks/{run_id}/ratings",
    response_model=schemas.TranslationBenchmarkResponse,
)
def rate_translation_benchmark(
    run_id: str,
    payload: schemas.TranslationBenchmarkRating,
    db: Session = Depends(get_db),
):
    try:
        run = TranslationBenchmarkService(db).save_rating(
            run_id,
            payload.account_id,
            payload.score,
            payload.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not run:
        raise HTTPException(status_code=404, detail="Benchmark run not found")
    return run
