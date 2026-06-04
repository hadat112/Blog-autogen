from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from sqlalchemy import inspect, text

from apps.api.routes import accounts, jobs, pipelines
from infrastructure.db.session import Base, engine


Base.metadata.create_all(bind=engine)

if "settings" not in [column["name"] for column in inspect(engine).get_columns("pipelines")]:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE pipelines ADD COLUMN settings JSON DEFAULT '{}'"))

job_columns = [column["name"] for column in inspect(engine).get_columns("jobs")]
with engine.begin() as conn:
    if "input_text" not in job_columns:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN input_text VARCHAR"))
    if "input_type" not in job_columns:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN input_type VARCHAR"))
    if "rerun_at" not in job_columns:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN rerun_at DATETIME"))
    if "rerun_job_id" not in job_columns:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN rerun_job_id VARCHAR"))

app = FastAPI(title="Story Autogen API")

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
    if path.startswith(("accounts", "pipelines", "jobs")):
        return {"status": "not_found"}

    requested_file = FRONTEND_DIST / path
    if requested_file.is_file():
        return FileResponse(requested_file)

    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return {"status": "ok"}
