import logging
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import inspect, text


logger = logging.getLogger(__name__)

MIGRATIONS = (
    (1, "legacy compatibility columns"),
    (2, "content workflow tables and job columns"),
    (3, "seed initial theme rules"),
    (4, "add workflow query indexes"),
    (5, "add direct WordPress account to content drafts"),
    (6, "add job and article pagination indexes"),
    (7, "add application settings table"),
    (8, "add article source slug identity"),
    (9, "archive fetched article source data"),
    (10, "add article enrichment records"),
)


def _sqlite_path(engine):
    if engine.dialect.name != "sqlite":
        return None
    database = engine.url.database
    if not database or database == ":memory:":
        return None
    return Path(database).expanduser().resolve()


def _backup_existing_sqlite(engine, backup_dir=None):
    source = _sqlite_path(engine)
    if source is None:
        logger.info("Database backup is operator-managed for non-file databases")
        return None
    if not source.exists() or source.stat().st_size == 0:
        return None

    target_dir = Path(backup_dir or source.parent / "backups")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{source.stem}-{datetime.utcnow():%Y%m%d-%H%M%S-%f}.db"
    with sqlite3.connect(str(source)) as src, sqlite3.connect(str(target)) as dst:
        src.backup(dst)
    logger.info("Created pre-migration database backup at %s", target)
    return target


def _column_names(connection, table):
    return {column["name"] for column in inspect(connection).get_columns(table)}


def _add_column(connection, table, definition):
    name = definition.split()[0]
    if name not in _column_names(connection, table):
        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {definition}"))


def _migration_1(connection):
    tables = set(inspect(connection).get_table_names())
    if "languages" in tables and "prompt_name" in _column_names(connection, "languages"):
        try:
            connection.execute(text("ALTER TABLE languages DROP COLUMN prompt_name"))
        except Exception:
            logger.warning("Could not remove deprecated languages.prompt_name", exc_info=True)
    if "pipelines" in tables:
        _add_column(connection, "pipelines", "settings JSON DEFAULT '{}'")
    if "jobs" in tables:
        _add_column(connection, "jobs", "input_text VARCHAR")
        _add_column(connection, "jobs", "input_type VARCHAR")
        _add_column(connection, "jobs", "rerun_at DATETIME")
        _add_column(connection, "jobs", "rerun_job_id VARCHAR")


def _migration_2(connection):
    if "jobs" not in set(inspect(connection).get_table_names()):
        return
    _add_column(connection, "jobs", "workflow_type VARCHAR NOT NULL DEFAULT 'legacy'")
    _add_column(connection, "jobs", "parent_job_id VARCHAR")
    _add_column(connection, "jobs", "draft_id VARCHAR")
    _add_column(connection, "jobs", "outputs JSON NOT NULL DEFAULT '{}'")


def _migration_3(connection):
    if "theme_rules" in set(inspect(connection).get_table_names()):
        existing = connection.execute(text("SELECT COUNT(*) FROM theme_rules")).scalar() or 0
        if existing == 0:
            now = datetime.utcnow()
            seeds = {
                "family": ["family", "mother", "father", "daughter", "son"],
                "betrayal": ["betrayal", "cheated", "secret", "lied"],
                "revenge": ["revenge", "payback", "justice"],
                "inheritance": ["inheritance", "will", "estate", "heir"],
            }
            for tag, keywords in seeds.items():
                connection.execute(
                    text(
                        "INSERT INTO theme_rules(id, tag, keywords, is_active, created_at, updated_at) "
                        "VALUES (:id, :tag, :keywords, 1, :created_at, :updated_at)"
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "tag": tag,
                        "keywords": json.dumps(keywords),
                        "created_at": now,
                        "updated_at": now,
                    },
                )


def _migration_4(connection):
    statements = (
        "CREATE INDEX IF NOT EXISTS ix_jobs_workflow_status ON jobs(workflow_type, status)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_parent_job_id ON jobs(parent_job_id)",
        "CREATE INDEX IF NOT EXISTS ix_content_drafts_kind_state ON content_drafts(kind, state)",
        "CREATE INDEX IF NOT EXISTS ix_content_drafts_updated_at ON content_drafts(updated_at)",
        "CREATE INDEX IF NOT EXISTS ix_articles_analysis_processed ON articles(analysis_status, processed_at)",
    )
    tables = set(inspect(connection).get_table_names())
    for statement in statements:
        table = statement.split(" ON ", 1)[1].split("(", 1)[0]
        if table in tables:
            connection.execute(text(statement))


def _migration_5(connection):
    if "content_drafts" in set(inspect(connection).get_table_names()):
        _add_column(connection, "content_drafts", "wp_account_id VARCHAR")


def _migration_6(connection):
    statements = (
        "CREATE INDEX IF NOT EXISTS ix_jobs_status_start_time ON jobs(status, start_time)",
        "CREATE INDEX IF NOT EXISTS ix_jobs_workflow_start_time ON jobs(workflow_type, start_time)",
        "CREATE INDEX IF NOT EXISTS ix_articles_status_updated_at ON articles(analysis_status, updated_at)",
    )
    tables = set(inspect(connection).get_table_names())
    for statement in statements:
        table = statement.split(" ON ", 1)[1].split("(", 1)[0]
        if table in tables:
            connection.execute(text(statement))


def _migration_7(connection):
    connection.execute(text(
        "CREATE TABLE IF NOT EXISTS app_settings "
        "(key VARCHAR PRIMARY KEY, value JSON NOT NULL)"
    ))


def _migration_8(connection):
    if "articles" in set(inspect(connection).get_table_names()):
        _add_column(connection, "articles", "source_slug VARCHAR")
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_articles_source_slug ON articles(source_slug)"))


def _migration_9(connection):
    if "articles" not in set(inspect(connection).get_table_names()):
        return
    for definition in (
        "source_title VARCHAR NOT NULL DEFAULT ''",
        "source_content TEXT NOT NULL DEFAULT ''",
        "source_image_url VARCHAR NOT NULL DEFAULT ''",
        "source_language VARCHAR NOT NULL DEFAULT ''",
        "source_content_hash VARCHAR NOT NULL DEFAULT ''",
        "source_fetched_at DATETIME",
    ):
        _add_column(connection, "articles", definition)


def _migration_10(connection):
    connection.execute(text(
        "CREATE TABLE IF NOT EXISTS article_enrichments ("
        "id VARCHAR PRIMARY KEY, article_id VARCHAR NOT NULL UNIQUE, "
        "summary TEXT, plot_beats JSON, characters JSON, setting JSON, "
        "conflict JSON, emotional_arc JSON, creative_dna JSON, "
        "summary_status VARCHAR NOT NULL DEFAULT 'missing', "
        "analysis_status VARCHAR NOT NULL DEFAULT 'missing', "
        "dna_status VARCHAR NOT NULL DEFAULT 'missing', "
        "summary_error TEXT, analysis_error TEXT, dna_error TEXT, "
        "ai_account_id VARCHAR, model VARCHAR NOT NULL DEFAULT '', "
        "updated_at DATETIME NOT NULL)"
    ))
    connection.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_article_enrichments_article_id "
        "ON article_enrichments(article_id)"
    ))


MIGRATION_FUNCTIONS = {
    1: _migration_1,
    2: _migration_2,
    3: _migration_3,
    4: _migration_4,
    5: _migration_5,
    6: _migration_6,
    7: _migration_7,
    8: _migration_8,
    9: _migration_9,
    10: _migration_10,
}


def run_migrations(engine, metadata, backup_dir=None):
    existing_tables = set(inspect(engine).get_table_names())
    needs_initial_backup = bool(existing_tables) and "schema_migrations" not in existing_tables
    backup_path = _backup_existing_sqlite(engine, backup_dir) if needs_initial_backup else None

    metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, name VARCHAR NOT NULL, applied_at DATETIME NOT NULL)"
        ))
        applied = {
            row[0] for row in connection.execute(text("SELECT version FROM schema_migrations"))
        }

        # A database from before schema_migrations is upgraded directly to the
        # current schema in one bootstrap pass. The individual migration
        # functions are reused for their idempotent column/index/data checks,
        # but intermediate versions are not persisted as separate upgrades.
        if needs_initial_backup:
            for version, name in MIGRATIONS:
                MIGRATION_FUNCTIONS[version](connection)
                connection.execute(
                    text("INSERT INTO schema_migrations(version, name, applied_at) VALUES (:version, :name, :at)"),
                    {"version": version, "name": name, "at": datetime.utcnow()},
                )
            return backup_path

        for version, name in MIGRATIONS:
            if version in applied:
                continue
            MIGRATION_FUNCTIONS[version](connection)
            connection.execute(
                text("INSERT INTO schema_migrations(version, name, applied_at) VALUES (:version, :name, :at)"),
                {"version": version, "name": name, "at": datetime.utcnow()},
            )
    return backup_path
