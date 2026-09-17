from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.api.routes import accounts, article_workflows, content_drafts, generation_jobs, jobs, languages, pattern_collection_sources, patterns, pipelines, rewrite_jobs, settings, theme_rules
from app.services.language_service import LanguageService
from app.db.session import Base, engine
from app.db.session import SessionLocal
from app.db.migrations import run_migrations
from app.services.workflow_job_service import WorkflowJobService
from app.services.job_retention_service import JobRetentionService
from app.services.error_sanitizer import sanitize_error


run_migrations(engine, Base.metadata)
with SessionLocal() as db:
    LanguageService(db).ensure_defaults()
    WorkflowJobService(db).recover_interrupted()
    JobRetentionService(db).prune()

app = FastAPI(title="Story Autogen API")


def _error_code(status_code: int):
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        502: "upstream_error",
    }.get(status_code, "request_error")


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    detail = sanitize_error(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={"code": _error_code(exc.status_code), "message": detail, "detail": detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"code": "validation_error", "message": "Request validation failed", "detail": exc.errors()}),
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(pipelines.router)
app.include_router(jobs.router)
app.include_router(languages.router)
app.include_router(settings.router)
app.include_router(content_drafts.router)
app.include_router(patterns.router)
app.include_router(theme_rules.router)
app.include_router(pattern_collection_sources.router)
app.include_router(rewrite_jobs.router)
app.include_router(generation_jobs.router)
app.include_router(article_workflows.router)


FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"

if FRONTEND_ASSETS.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS)), name="assets")


@app.get("/")
def read_root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "ok"}


@app.get("/{path:path}", include_in_schema=False)
def serve_frontend(path: str):
    if path.startswith((
        "accounts", "pipelines", "jobs", "languages", "settings",
        "content-drafts", "patterns", "theme-rules",
        "rewrite-jobs", "generation-jobs", "pattern-analysis-pipelines",
        "article-workflows",
    )):
        return {"status": "not_found"}

    requested_file = FRONTEND_DIST / path
    if requested_file.is_file():
        return FileResponse(requested_file)

    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return {"status": "ok"}
