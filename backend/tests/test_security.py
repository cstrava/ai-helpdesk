from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app import main as api
from backend.app.auth import password_hash, verify_password
from backend.app.manage import migrate
from test_api import start_conversation, add_message, get_draft, confirmation_body


def login(client, email="second@example.test"):
    assert (
        client.post(
            "/auth/register", json={"email": email, "password": "test-password-only"}
        ).status_code
        == 201
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "test-password-only"}
    )
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return response


def ticket(client):
    conversation = start_conversation(client)
    add_message(client, conversation)
    draft = get_draft(client, conversation)
    response = client.post(
        f"/conversations/{conversation}/tickets", json=confirmation_body(draft)
    )
    assert response.status_code == 201
    return conversation, draft, response.json()


def test_password_hash_is_salted():
    first = password_hash("a-long-test-password")
    assert first != password_hash("a-long-test-password")
    assert verify_password("a-long-test-password", first)
    assert not verify_password("incorrect-password", first)


def test_authentication_logout_csrf_and_expiry(anonymous_client, test_db):
    client = anonymous_client
    assert client.get("/tickets").status_code == 401
    assert client.post("/conversations").status_code == 401
    response = login(client)
    cookie = response.headers["set-cookie"].lower()
    assert (
        "httponly" in cookie and "samesite=lax" in cookie and "max-age=28800" in cookie
    )
    assert client.get("/auth/me").json()["role"] == "user"
    csrf = client.headers.pop("X-CSRF-Token")
    assert client.post("/conversations").status_code == 403
    client.headers["X-CSRF-Token"] = "wrong"
    assert client.post("/auth/logout").status_code == 403
    client.headers["X-CSRF-Token"] = csrf
    assert (
        client.post(
            "/conversations", headers={"Origin": "https://attacker.test"}
        ).status_code
        == 403
    )
    stolen_cookie = client.cookies.get("helpdesk_session")
    assert client.post("/auth/logout").status_code == 200
    client.cookies.set("helpdesk_session", stolen_cookie)
    assert client.get("/auth/me").status_code == 401
    login_response = client.post(
        "/auth/login",
        json={"email": "second@example.test", "password": "test-password-only"},
    )
    assert login_response.status_code == 200
    with test_db() as db:
        db.execute(
            "UPDATE sessions SET expires_at=%s",
            (datetime.now(timezone.utc) - timedelta(seconds=1),),
        )
    assert client.get("/tickets").status_code == 401


def test_no_public_support_and_login_validation(anonymous_client):
    client = anonymous_client
    assert (
        client.post(
            "/auth/register",
            json={
                "email": "bad@example.test",
                "password": "test-password-only",
                "role": "support",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/auth/register",
            json={"email": "invalid", "password": "test-password-only"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/auth/login",
            json={"email": "missing@example.test", "password": "test-password-only"},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/auth/register",
            json={"email": "a@example.test", "password": "test-password-only"},
            headers={"Origin": "https://attacker.test"},
        ).status_code
        == 403
    )
    login(client)
    assert (
        client.post(
            "/auth/register",
            json={"email": "SECOND@example.test", "password": "test-password-only"},
        ).status_code
        == 409
    )


def test_account_isolation_and_support_audit(client, test_db):
    conversation, draft, original = ticket(client)
    with TestClient(api.app) as second:
        login(second)
        assert second.get("/conversations").json() == []
        assert second.get("/tickets").json() == []
        for suffix in ("", "/messages"):
            assert (
                second.get(f"/conversations/{conversation}{suffix}").status_code == 404
            )
        assert (
            second.post(
                f"/conversations/{conversation}/messages", json={"content": "hello"}
            ).status_code
            == 404
        )
        assert (
            second.post(f"/conversations/{conversation}/ticket-draft").status_code
            == 404
        )
        assert (
            second.post(
                f"/conversations/{conversation}/tickets", json=confirmation_body(draft)
            ).status_code
            == 404
        )
        assert second.get(f"/tickets/{original['id']}").status_code == 404
        assert second.get(f"/tickets/{original['id']}/events").status_code == 404
        assert (
            second.patch(
                f"/tickets/{original['id']}", json={"status": "resolved"}
            ).status_code
            == 403
        )
        with test_db() as db:
            db.execute(
                "UPDATE users SET role='support' WHERE email='second@example.test'"
            )
        assert len(second.get("/tickets").json()) == 1
        changed = second.patch(
            f"/tickets/{original['id']}",
            json={"status": "resolved", "final_category": "Hardware"},
        )
        assert changed.status_code == 200
        assert changed.json()["predicted_category"] == "Access"
        assert (
            second.patch(
                f"/tickets/{original['id']}", json={"status": "resolved"}
            ).status_code
            == 200
        )
    events = client.get(f"/tickets/{original['id']}/events").json()
    assert len(events) == 2
    assert all(e["actor"] == "second@example.test" for e in events)
    assert {(e["field"], e["old_value"], e["new_value"]) for e in events} == {
        ("status", "open", "resolved"),
        ("final_category", "Access", "Hardware"),
    }
    assert (
        client.get(f"/conversations/{conversation}").json()["ticket"]["id"]
        == original["id"]
    )
    assert client.get("/conversations").json()[0]["ticket_id"] == original["id"]


def test_server_filters_pagination_and_legacy_privacy(client, test_db):
    _, _, first = ticket(client)
    ticket(client)
    with test_db() as db:
        db.execute(
            "INSERT INTO tickets(text,predicted_category,final_category,model_version) VALUES ('legacy','Access','Access','legacy')"
        )
        legacy = db.execute(
            "INSERT INTO conversations DEFAULT VALUES RETURNING id"
        ).fetchone()["id"]
    assert len(client.get("/tickets").json()) == 2
    assert client.get(f"/conversations/{legacy}").status_code == 404
    assert (
        client.get("/tickets", params={"search": first["id"]}).json()[0]["id"]
        == first["id"]
    )
    assert client.get("/tickets", params={"category": "Hardware"}).json() == []
    assert (
        len(
            client.get(
                "/tickets", params={"category": "Access", "status": "open"}
            ).json()
        )
        == 2
    )
    first_page = client.get("/tickets?limit=1").json()
    second_page = client.get("/tickets?limit=1&offset=1").json()
    assert first_page[0]["id"] != second_page[0]["id"]
    assert (
        client.post("/tickets", json={"text": "bypass", "confirmed": True}).status_code
        == 410
    )


def test_concurrent_confirmation(client, monkeypatch):
    conversation = start_conversation(client)
    add_message(client, conversation)
    draft = get_draft(client, conversation)
    entered, release = Event(), Event()
    original = api.classify

    def slow_classify(text, request):
        entered.set()
        assert release.wait(10)
        return original(text, request)

    monkeypatch.setattr(api, "classify", slow_classify)

    def confirm():
        with TestClient(api.app) as other:
            other.cookies.update(client.cookies)
            other.headers.update(client.headers)
            return other.post(
                f"/conversations/{conversation}/tickets", json=confirmation_body(draft)
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(confirm)
        try:
            assert entered.wait(10)
            assert confirm().status_code == 409
        finally:
            release.set()
        assert first.result().status_code == 201
    assert len(client.get("/tickets").json()) == 1


def test_migrations_adopt_existing_schema_and_repeat(client, test_db):
    _, _, original = ticket(client)
    with test_db() as db:
        db.execute(
            "DELETE FROM schema_migrations WHERE version LIKE '001%' OR version LIKE '002%' OR version LIKE '003%'"
        )
    migrate()
    migrate()
    with test_db() as db:
        assert (
            db.execute("SELECT count(*) AS n FROM schema_migrations").fetchone()["n"]
            == 4
        )
        assert db.execute(
            "SELECT id FROM tickets WHERE id=%s", (original["id"],)
        ).fetchone()


@pytest.mark.parametrize(
    "failure, expected",
    [(httpx.ConnectError("offline"), 502), (httpx.ReadTimeout("timeout"), 504)],
)
def test_ollama_transport_errors(monkeypatch, failure, expected):
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            raise failure

    monkeypatch.setattr(httpx, "Client", FakeClient)
    with pytest.raises(api.HTTPException) as exc:
        api.generate_chat_reply([])
    assert exc.value.status_code == expected


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": {"content": ""}},
        {"message": {"content": "partial"}, "done_reason": "length"},
    ],
)
def test_ollama_invalid_response(monkeypatch, payload):
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, *args, **kwargs):
            return httpx.Response(
                200,
                json=payload,
                request=httpx.Request("POST", "http://ollama/api/chat"),
            )

    monkeypatch.setattr(httpx, "Client", FakeClient)
    with pytest.raises(api.HTTPException) as exc:
        api.generate_chat_reply([])
    assert exc.value.status_code == 502


def test_upgrade_original_schema_preserves_unowned_data(test_db, monkeypatch):
    from pathlib import Path
    from psycopg import sql

    schema = "legacy_" + uuid4().hex
    with test_db() as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    def legacy_connect():
        db = test_db()
        db.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        return db

    try:
        with legacy_connect() as db:
            for path in sorted(
                (Path(__file__).resolve().parents[1] / "migrations").glob(
                    "00[1-3]*.sql"
                )
            ):
                db.execute(
                    path.read_text().replace("BEGIN;", "").replace("COMMIT;", "")
                )
            conversation = db.execute(
                "INSERT INTO conversations DEFAULT VALUES RETURNING id"
            ).fetchone()["id"]
            ticket_id = db.execute(
                "INSERT INTO tickets(title,text,conversation_id,predicted_category,final_category,model_version) VALUES ('Historical title','Historical text',%s,'Access','Hardware','original-model') RETURNING id",
                (conversation,),
            ).fetchone()["id"]
        monkeypatch.setattr(api, "connect_db", legacy_connect)
        migrate()
        migrate()
        with legacy_connect() as db:
            row = db.execute(
                "SELECT * FROM tickets WHERE id=%s", (ticket_id,)
            ).fetchone()
            assert row["owner_id"] is None
            assert row["text"] == "Historical text"
            assert row["predicted_category"] == "Access"
            assert row["final_category"] == "Hardware"
            assert row["model_version"] == "original-model"
            assert (
                db.execute(
                    "SELECT owner_id FROM conversations WHERE id=%s", (conversation,)
                ).fetchone()["owner_id"]
                is None
            )
    finally:
        with test_db() as db:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_invalid_draft_and_database_failure(client, monkeypatch):
    import psycopg

    conversation = start_conversation(client)
    add_message(client, conversation)
    monkeypatch.setattr(
        api, "generate_chat_reply", lambda *args, **kwargs: '{"title":"only title"}'
    )
    assert client.post(f"/conversations/{conversation}/ticket-draft").status_code == 502
    assert client.get("/tickets").json() == []

    def unavailable():
        raise psycopg.OperationalError("test database offline")

    monkeypatch.setattr(api, "connect_db", unavailable)
    response = client.get("/tickets")
    assert response.status_code == 503
    assert "momentan indisponibilă" in response.json()["detail"]


def test_auth_rate_limit(anonymous_client, test_db):
    from backend.app.auth import token_hash

    with test_db() as db:
        db.execute(
            "INSERT INTO auth_rate_limits(key,attempts) VALUES (%s,30)",
            (token_hash("login:testclient"),),
        )
    response = anonymous_client.post(
        "/auth/login",
        json={"email": "none@example.test", "password": "test-password-only"},
    )
    assert response.status_code == 429


def test_draft_receives_only_user_facts(client, monkeypatch):
    import json

    conversation = start_conversation(client)
    add_message(client, conversation, "Nu merge microfonul USB.")
    add_message(client, conversation, "Corectez: este un headset, nu microfon.")
    captured = []

    def generate(messages, system_prompt=None, response_format=None):
        captured.extend(json.loads(messages[0]["content"]))
        return json.dumps(
            {"title": "Headset USB", "description": "Nu funcționează headsetul USB."}
        )

    monkeypatch.setattr(api, "generate_chat_reply", generate)
    assert client.post(f"/conversations/{conversation}/ticket-draft").status_code == 200
    assert [item["role"] for item in captured] == ["user", "user"]
    assert captured[-1]["content"] == "Corectez: este un headset, nu microfon."


@pytest.mark.parametrize(
    "damage",
    [
        "ALTER TABLE tickets DROP COLUMN model_version",
        "ALTER TABLE tickets ALTER COLUMN text TYPE varchar(1000)",
        "ALTER TABLE tickets ALTER COLUMN status SET DEFAULT 'resolved'",
        "ALTER TABLE conversation_messages ALTER COLUMN id DROP IDENTITY",
        "ALTER TABLE tickets ALTER COLUMN text DROP NOT NULL",
        "ALTER TABLE tickets DROP CONSTRAINT tickets_status_check",
        "ALTER TABLE conversation_messages DROP CONSTRAINT conversation_messages_conversation_id_fkey",
        "ALTER TABLE tickets DROP CONSTRAINT tickets_conversation_id_unique",
        "DROP INDEX idx_conversation_messages_conversation_id_id",
        "DROP TABLE conversation_messages",
        "ALTER TABLE tickets DROP CONSTRAINT tickets_title_check",
    ],
)
def test_legacy_adoption_rejects_partial_schema(test_db, damage):
    with test_db() as db:
        db.execute("DELETE FROM schema_migrations WHERE version < '004'")
        db.execute(damage)
    with pytest.raises(RuntimeError, match="Incompatible legacy schema"):
        migrate()
    with test_db() as db:
        assert (
            db.execute(
                "SELECT count(*) AS n FROM schema_migrations WHERE version < '004'"
            ).fetchone()["n"]
            == 0
        )
        assert (
            db.execute(
                "SELECT count(*) AS n FROM information_schema.schemata WHERE schema_name LIKE 'migration_reference_%'"
            ).fetchone()["n"]
            == 0
        )


def test_confirmation_retry_recovers_existing_ticket(client, test_db):
    conversation, draft, created = ticket(client)
    # A client can lose the first HTTP response after this committed transaction.
    recovered = client.get(f"/conversations/{conversation}").json()["ticket"]
    assert recovered["id"] == created["id"]
    assert (
        client.post(
            f"/conversations/{conversation}/tickets", json=confirmation_body(draft)
        ).status_code
        == 409
    )
    with test_db() as db:
        assert (
            db.execute(
                "SELECT count(*) AS n FROM tickets WHERE conversation_id=%s",
                (conversation,),
            ).fetchone()["n"]
            == 1
        )
