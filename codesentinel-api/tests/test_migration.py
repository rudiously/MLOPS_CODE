from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

def test_initial_migration_applies_to_fresh_database(tmp_path, monkeypatch):
    db_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    assert {"repos", "users", "repo_access", "pr_scans", "findings"}.issubset(inspect(create_engine(db_url)).get_table_names())
