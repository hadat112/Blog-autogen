from app.domain.workflow_threads import run_workflow_blocking
"""Discover models and start a fixed Polish translation timing job."""

import asyncio
import requests

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.domain.model_benchmark_sample import SAMPLE_ID, SAMPLE_TEXT
from app.domain.workflow_runner import workflow_runner
from app.services.account_service import fetch_ai_models
from app.services.model_benchmark_service import ModelBenchmarkService
from app.services.workflow_job_service import WorkflowJobService


router = APIRouter(prefix="/model-benchmarks", tags=["model benchmark"])


class BenchmarkInput(BaseModel):
    account_id: str
    model_ids: list[str] = Field(min_length=2, max_length=5)


def _ai_account(db: Session, account_id: str):
    account = db.get(models.Account, account_id)
    if not account or account.type != "ai":
        raise HTTPException(404, "AI account not found")
    return account


def _models(account):
    try:
        return fetch_ai_models(account.config or {})
    except requests.Timeout as exc:
        raise HTTPException(502, "Timed out while fetching models from AI account") from exc
    except requests.ConnectionError as exc:
        raise HTTPException(502, "Could not connect to AI account Base URL") from exc
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else None
        detail = f"AI account returned HTTP {code} while fetching models" if code else "AI account returned an HTTP error while fetching models"
        raise HTTPException(502, detail) from exc
    except ValueError as exc:
        raise HTTPException(502, "AI account returned invalid models data") from exc
    except Exception as exc:
        raise HTTPException(502, "Could not fetch models from AI account") from exc


@router.get("/sample")
def get_sample():
    return {
        "id": SAMPLE_ID,
        "source_language": "English",
        "target_language": "Polish",
        "word_count": len(SAMPLE_TEXT.split()),
        "text": SAMPLE_TEXT,
    }


@router.get("/accounts/{account_id}/models")
def get_models(account_id: str, db: Session = Depends(get_db)):
    return _models(_ai_account(db, account_id))


@router.post("")
async def start_benchmark(data: BenchmarkInput, db: Session = Depends(get_db)):
    account = _ai_account(db, data.account_id)
    if any(not model_id.strip() for model_id in data.model_ids) or len(set(data.model_ids)) != len(data.model_ids):
        raise HTTPException(400, "Choose distinct nonblank model IDs")
    available = {item["id"] for item in _models(account)}
    if any(model_id not in available for model_id in data.model_ids):
        raise HTTPException(400, "Selected model is not available from this AI account")

    job = WorkflowJobService(db).create(None, "model_benchmark")
    job.outputs = {
        "account_id": account.id,
        "sample_id": SAMPLE_ID,
        "model_ids": data.model_ids,
        "results": [{"model_id": model_id, "status": "waiting", "elapsed_seconds": None} for model_id in data.model_ids],
    }
    db.commit()

    async def operation():
        await run_workflow_blocking(ModelBenchmarkService.execute, job.id)

    workflow_runner.start(job.id, operation)
    return {"job_id": job.id, "status": job.status}
