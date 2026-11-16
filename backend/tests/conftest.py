import json
import os
from contextlib import asynccontextmanager
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.rows import dict_row

from backend.app import main as api


@pytest.fixture
def test_db(monkeypatch):
    settings = {
        "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
        "port": int(os.getenv("POSTGRES_PORT", "5434")),
        "dbname": "ai_helpdesk_test",
        "user": os.getenv("POSTGRES_USER", "helpdesk"),
        "password": os.environ["POSTGRES_PASSWORD"],
        "connect_timeout": 5,
    }

    schema = f"test_{uuid4().hex}"

    try:
        with psycopg.connect(**settings, autocommit=True) as connection:
            connection.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema))
            )
    except psycopg.OperationalError:
        pytest.fail(
            "Baza ai_helpdesk_test nu este disponibilă. Verifică variabilele POSTGRES_* și portul de test.",
            pytrace=False,
        )

    try:

        def connect_test_db():
            return psycopg.connect(
                **settings,
                options=f"-c search_path={schema}",
                row_factory=dict_row,
            )

        monkeypatch.setattr(api, "connect_db", connect_test_db)
        from backend.app.manage import migrate

        migrate()
        yield connect_test_db

    finally:
        with psycopg.connect(**settings, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )


@pytest.fixture
def anonymous_client(test_db, monkeypatch):
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
            return json.dumps(
                {
                    "title": "Cont SAP blocat",
                    "description": "Utilizatorul nu se poate conecta la SAP.",
                }
            )

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


@pytest.fixture
def client(anonymous_client):
    response = anonymous_client.post(
        "/auth/register",
        json={"email": "owner@example.test", "password": "test-password-only"},
    )
    assert response.status_code == 201
    response = anonymous_client.post(
        "/auth/login",
        json={"email": "owner@example.test", "password": "test-password-only"},
    )
    assert response.status_code == 200
    anonymous_client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    yield anonymous_client
