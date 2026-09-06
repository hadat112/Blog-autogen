import sqlite3

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base

from app.db.migrations import run_migrations
from app.db.models import Account, Article, ContentDraft, Job, Language, Pipeline, ThemeRule  # noqa: F401


def test_migration_upgrades_current_schema_backs_up_and_is_repeatable(tmp_path):
    database = tmp_path / "current.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE pipelines (id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL, type VARCHAR NOT NULL, language VARCHAR, step_accounts JSON NOT NULL, is_active BOOLEAN, created_at DATETIME);
            CREATE TABLE jobs (id VARCHAR PRIMARY KEY, pipeline_id VARCHAR, start_time DATETIME, status VARCHAR, progress INTEGER, logs JSON);
            CREATE TABLE languages (code VARCHAR PRIMARY KEY, display_name VARCHAR NOT NULL, prompt_name VARCHAR, is_active BOOLEAN, created_at DATETIME);
            INSERT INTO pipelines VALUES ('p1', 'Legacy', 'story', 'English', '{}', 1, CURRENT_TIMESTAMP);
            """
        )
    engine = create_engine(f"sqlite:///{database}")
    from app.db.session import Base

    backup = run_migrations(engine, Base.metadata, tmp_path / "backups")
    assert backup and backup.exists()
    with sqlite3.connect(backup) as backup_connection:
        assert backup_connection.execute("SELECT name FROM pipelines WHERE id='p1'").fetchone() == ("Legacy",)
    assert "workflow_type" in {item["name"] for item in inspect(engine).get_columns("jobs")}
    assert {"content_drafts", "articles", "theme_rules", "schema_migrations"}.issubset(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.execute(text("SELECT name FROM pipelines WHERE id='p1'")).scalar() == "Legacy"
        assert connection.execute(text("SELECT COUNT(*) FROM schema_migrations")).scalar() == 4
        assert connection.execute(text("SELECT COUNT(*) FROM theme_rules")).scalar() >= 1
    assert run_migrations(engine, Base.metadata, tmp_path / "backups") is None
    assert len(list((tmp_path / "backups").glob("*.db"))) == 1
