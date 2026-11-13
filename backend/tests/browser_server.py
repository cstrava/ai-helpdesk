"""Isolated browser-test server. Never imports or loads ML weights."""

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from backend.app import main
from backend.app.manage import migrate
from backend.app.auth import password_hash

# The database name cannot be overridden to point at the application database.
settings = dict(
    host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
    port=int(os.getenv("POSTGRES_PORT", "55434")),
    dbname="ai_helpdesk_test",
    user=os.getenv("POSTGRES_USER", "helpdesk"),
    password=os.getenv("POSTGRES_PASSWORD", "test-only"),
    connect_timeout=5,
)
schema = "browser_" + uuid4().hex


def connect():
    return psycopg.connect(
        **settings, options=f"-c search_path={schema}", row_factory=dict_row
    )


@asynccontextmanager
async def lifespan(app):
    with psycopg.connect(**settings, autocommit=True) as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        migrate()
        with connect() as db:
            db.execute(
                "INSERT INTO users(email,password_hash,role) VALUES (%s,%s,'support')",
                (
                    "browser-support@example.test",
                    password_hash("browser-support-password"),
                ),
            )
        yield
    finally:
        with psycopg.connect(**settings, autocommit=True) as db:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


main.connect_db = connect
main.app.router.lifespan_context = lifespan
main.classify = lambda text, request: main.Prediction(
    category="Access", model_version="browser-test"
)


def fake_chat(messages, system_prompt=None, response_format=None):
    if response_format:
        return json.dumps(
            {
                "title": "Cont pontaj blocat",
                "description": "Utilizatorul nu se poate conecta la pontaj.",
            }
        )
    return "Ce mesaj de eroare apare?"


main.generate_chat_reply = fake_chat

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        main.app, host="127.0.0.1", port=8001, log_level="warning", access_log=False
    )
