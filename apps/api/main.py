from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import accounts, jobs, pipelines
from infrastructure.db.session import Base, engine


Base.metadata.create_all(bind=engine)

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


@app.get("/")
def read_root():
    return {"status": "ok"}
