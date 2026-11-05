import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.rows import dict_row

from backend.app import main as api

MIGRATIONS = Path(__file__).resolve().parents[1] / "migrations"


@pytest.fixture
def test_db(monkeypatch):
    settings = {
        "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.getenv("POSTGRES_PORT", "5433")),
        "dbname": "ai_helpdesk_test",
        "user": os.getenv("POSTGRES_USER", "helpdesk"),
        "password": os.environ["POSTGRES_PASSWORD"],
        "connect_timeout": 5,
    }

    schema = f"test_{uuid4().hex}"

    with psycopg.connect(**settings, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
        )

    try:
        with psycopg.connect(**settings, autocommit=True) as connection:
            connection.execute(
                sql.SQL("SET search_path TO {}").format(
                    sql.Identifier(schema)
                )
            )

            migrations = sorted(MIGRATIONS.glob("*.sql"))
            assert migrations, "Nu au fost găsite migrările."

            for migration in migrations:
                connection.execute(migration.read_text(encoding="utf-8"))

        def connect_test_db():
            return psycopg.connect(
                **settings,
                options=f"-c search_path={schema}",
                row_factory=dict_row,
            )

        monkeypatch.setattr(api, "connect_db", connect_test_db)
        yield connect_test_db

    finally:
        with psycopg.connect(**settings, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(
                    sql.Identifier(schema)
                )
            )


@pytest.fixture
def client(test_db, monkeypatch):
    @asynccontextmanager
    async def test_lifespan(app):
        yield

    def fake_classify(text, request):
        return api.Prediction(
            category="Access",
            model_version="test-classifier",
        )

    def fake_chat(messages, system_prompt=None, response_format=None):
        if response_format is not None:
            return json.dumps({
                "title": "Cont SAP blocat",
                "description": "Utilizatorul nu se poate conecta la SAP.",
            })

        return "Ce mesaj de eroare apare?"

    monkeypatch.setattr(
        api.app.router,
        "lifespan_context",
        test_lifespan,
    )
    monkeypatch.setattr(api, "classify", fake_classify)
    monkeypatch.setattr(api, "generate_chat_reply", fake_chat)

    with TestClient(api.app) as test_client:
        yield test_client