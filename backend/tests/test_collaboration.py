from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from backend.app import main as api
from test_security import login, ticket


@pytest.fixture
def support(client, test_db):
    with TestClient(api.app) as actor:
        login(actor, "agent@example.test")
        with test_db() as db:
            db.execute(
                "UPDATE users SET role='support' WHERE email='agent@example.test'"
            )
        yield actor


def body(content="A public reply", **extra):
    return {"content": content, "request_id": str(uuid4()), **extra}


def test_public_thread_idempotency_and_validation(client, support):
    conversation, _, created = ticket(client)
    path = f"/tickets/{created['id']}/messages"
    payload = body()
    first = client.post(path, json=payload)
    assert first.status_code == 201
    assert client.post(path, json=payload).json()["id"] == first.json()["id"]
    assert UUID(first.json()["id"])
    assert (
        client.post(path, json={**payload, "content": "different"}).status_code == 409
    )
    for content in (" ", "x" * 4001):
        assert client.post(path, json=body(content)).status_code == 422
    assert (
        client.post(path, json=body("secret", visibility="internal")).status_code == 403
    )
    assert support.post(path, json=body("Support answer")).status_code == 201
    messages = client.get(path).json()
    assert [m["content"] for m in messages] == ["A public reply", "Support answer"]
    assert (
        client.get(path, params={"after_id": messages[0]["id"]}).json() == messages[1:]
    )
    assert client.get(f"/tickets/{created['id']}").json()["status"] == "open"
    assert (
        client.post(
            f"/conversations/{conversation}/messages", json={"content": "closed"}
        ).status_code
        == 409
    )


def test_internal_notes_never_appear_in_user_responses(client, support):
    conversation, _, created = ticket(client)
    path = f"/tickets/{created['id']}/messages"
    before = client.get(f"/tickets/{created['id']}").json()
    note = support.post(
        path, json=body("CONFIDENTIAL-INTERNAL-NOTE", visibility="internal")
    )
    assert note.status_code == 201
    assert client.get(f"/tickets/{created['id']}").json() == before
    assert support.get(path).json()[0]["visibility"] == "internal"
    for endpoint in (
        path,
        "/tickets",
        f"/tickets/{created['id']}",
        f"/tickets/{created['id']}/events",
        f"/conversations/{conversation}",
    ):
        response = client.get(endpoint)
        assert response.status_code == 200
        assert "CONFIDENTIAL" not in response.text
        assert note.json()["id"] not in response.text
    assert client.get(path).json() == []
    assert client.get(path, params={"after_id": note.json()["id"]}).status_code == 404
    assert client.get(f"/tickets/{created['id']}/events").json() == []
    public = support.post(path, json=body("Public answer"))
    assert client.get(path).json() == [public.json()]


def test_other_user_cannot_access_thread_or_reopen(client, support):
    _, _, created = ticket(client)
    with TestClient(api.app) as other:
        login(other)
        assert other.get(f"/tickets/{created['id']}/messages").status_code == 404
        assert (
            other.post(f"/tickets/{created['id']}/messages", json=body()).status_code
            == 404
        )
        assert (
            other.post(
                f"/tickets/{created['id']}/reopen",
                json={
                    "reason": "Still broken",
                    "request_id": str(uuid4()),
                    "expected_version": 0,
                },
            ).status_code
            == 404
        )
        assert other.get("/support/agents").status_code == 403


def test_assignment_permissions_validation_and_audit(client, support):
    _, _, created = ticket(client)
    path = f"/tickets/{created['id']}/assignment"
    agent = support.get("/auth/me").json()["id"]
    owner = client.get("/auth/me").json()["id"]
    assert (
        client.put(path, json={"assignee_id": agent, "expected_version": 0}).status_code
        == 403
    )
    assert (
        support.put(
            path, json={"assignee_id": owner, "expected_version": 0}
        ).status_code
        == 422
    )
    assert (
        support.put(
            path, json={"assignee_id": str(uuid4()), "expected_version": 0}
        ).status_code
        == 422
    )
    assigned = support.put(path, json={"assignee_id": agent, "expected_version": 0})
    assert assigned.status_code == 200
    assert assigned.json()["assignee_id"] == agent
    assert assigned.json()["version"] == 1
    assert (
        support.put(path, json={"assignee_id": None, "expected_version": 0}).status_code
        == 409
    )
    assert (
        support.put(path, json={"assignee_id": agent, "expected_version": 1}).json()[
            "version"
        ]
        == 1
    )
    assert (
        support.put(path, json={"assignee_id": None, "expected_version": 1}).status_code
        == 200
    )
    events = client.get(f"/tickets/{created['id']}/events").json()
    assert len(events) == 2
    assert all(e["field"] == "assignee_id" for e in events)
    assert support.get("/support/agents").json() == [
        {"id": agent, "email": "agent@example.test"}
    ]


def test_concurrent_claims_do_not_overwrite_assignee(client, support, test_db):
    _, _, created = ticket(client)
    with TestClient(api.app) as second:
        login(second, "second-agent@example.test")
        with test_db() as db:
            db.execute(
                "UPDATE users SET role='support' WHERE email='second-agent@example.test'"
            )
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda actor: actor.post(
                        f"/tickets/{created['id']}/claim", json={"expected_version": 0}
                    ),
                    [support, second],
                )
            )
        assert sorted(r.status_code for r in results) == [200, 409]
        winner = next(r.json()["assignee_id"] for r in results if r.status_code == 200)
        assert client.get(f"/tickets/{created['id']}").json()["assignee_id"] == winner
        assert len(client.get(f"/tickets/{created['id']}/events").json()) == 1


def test_resolution_and_reopening_preserve_first_resolution(client, support):
    _, _, created = ticket(client)
    path = f"/tickets/{created['id']}"
    assert support.patch(path, json={"status": "resolved"}).status_code == 422
    assert (
        support.patch(
            path, json={"status": "resolved", "expected_version": 0}
        ).status_code
        == 422
    )
    resolved = support.patch(
        path,
        json={
            "status": "resolved",
            "expected_version": 0,
            "resolution_message": "Access restored",
            "request_id": str(uuid4()),
        },
    )
    assert resolved.status_code == 200
    first = resolved.json()["first_resolved_at"]
    assert first is not None
    assert (
        client.patch(path, json={"status": "open", "expected_version": 1}).status_code
        == 403
    )
    assert (
        support.patch(path, json={"status": "open", "expected_version": 1}).status_code
        == 409
    )
    assert client.post(path + "/messages", json=body("Still broken")).status_code == 201
    assert client.get(path).json()["status"] == "resolved"
    payload = {
        "reason": "Access is blocked again",
        "expected_version": 1,
        "request_id": str(uuid4()),
    }
    reopened = client.post(path + "/reopen", json=payload)
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"
    assert reopened.json()["first_resolved_at"] == first
    assert client.post(path + "/reopen", json=payload).status_code == 200
    assert (
        client.post(
            path + "/reopen",
            json={**payload, "request_id": str(uuid4()), "expected_version": 2},
        ).status_code
        == 409
    )
    assert (
        support.patch(
            path,
            json={
                "status": "resolved",
                "expected_version": 2,
                "resolution_message": "Fixed permanently",
                "request_id": str(uuid4()),
            },
        ).json()["first_resolved_at"]
        == first
    )
    messages = client.get(path + "/messages").json()
    assert [m["kind"] for m in messages] == [
        "resolution",
        "reply",
        "reopen",
        "resolution",
    ]
    assert len(client.get(path + "/events").json()) == 3


def test_concurrent_public_retry_saves_one_message(client, support):
    _, _, created = ticket(client)
    payload = body()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda _: support.post(
                    f"/tickets/{created['id']}/messages", json=payload
                ),
                range(2),
            )
        )
    assert [r.status_code for r in responses] == [201, 201]
    assert responses[0].json()["id"] == responses[1].json()["id"]
    assert len(client.get(f"/tickets/{created['id']}/messages").json()) == 1


def test_status_conflict_rolls_back_message_and_audit(client, support):
    _, _, created = ticket(client)
    path = f"/tickets/{created['id']}"
    assert (
        support.patch(
            path, json={"status": "in_progress", "expected_version": 0}
        ).status_code
        == 200
    )
    result = support.patch(
        path,
        json={
            "status": "resolved",
            "expected_version": 0,
            "resolution_message": "Stale write",
            "request_id": str(uuid4()),
        },
    )
    assert result.status_code == 409
    assert client.get(path + "/messages").json() == []
    assert len(client.get(path + "/events").json()) == 1
    assert (
        client.post(
            path + "/reopen",
            json={"reason": " ", "expected_version": 1, "request_id": str(uuid4())},
        ).status_code
        == 422
    )


def test_upgrade_v4_preserves_data_and_unknown_timestamps(test_db, monkeypatch):
    from pathlib import Path
    from psycopg import sql
    from backend.app.manage import migrate

    schema = "upgrade_" + uuid4().hex
    with test_db() as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))

    def connection():
        db = test_db()
        db.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
        return db

    try:
        with connection() as db:
            db.execute(
                "CREATE TABLE schema_migrations(version TEXT PRIMARY KEY,applied_at TIMESTAMPTZ DEFAULT now())"
            )
            for path in sorted(
                (Path(__file__).resolve().parents[1] / "migrations").glob(
                    "00[1-4]*.sql"
                )
            ):
                db.execute(
                    path.read_text().replace("BEGIN;", "").replace("COMMIT;", "")
                )
                db.execute(
                    "INSERT INTO schema_migrations(version) VALUES (%s)", (path.name,)
                )
            agent = db.execute(
                "INSERT INTO users(email,password_hash,role) VALUES ('synthetic@example.test','unused','support') RETURNING id"
            ).fetchone()["id"]
            ids = [
                db.execute(
                    "INSERT INTO tickets(text,predicted_category,final_category,model_version,status) VALUES ('Synthetic historical ticket','Access','Access','v1','resolved') RETURNING id"
                ).fetchone()["id"]
                for _ in range(2)
            ]
            db.execute(
                "INSERT INTO ticket_events(ticket_id,actor_id,field,old_value,new_value,created_at) VALUES (%s,%s,'status','open','resolved','2020-01-01T00:00:00Z')",
                (ids[0], agent),
            )
        monkeypatch.setattr(api, "connect_db", connection)
        migrate()
        migrate()
        with connection() as db:
            known = db.execute(
                "SELECT * FROM tickets WHERE id=%s", (ids[0],)
            ).fetchone()
            unknown = db.execute(
                "SELECT * FROM tickets WHERE id=%s", (ids[1],)
            ).fetchone()
            assert known["first_resolved_at"].year == 2020
            assert unknown["first_resolved_at"] is None
            assert known["updated_at"] is None
            assert unknown["text"] == "Synthetic historical ticket"
            assert unknown["model_version"] == "v1"
            assert unknown["owner_id"] is None
            assert unknown["priority"] == "normal"
            assert unknown["version"] == 0
    finally:
        with test_db() as db:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_concurrent_resolution_and_reopening_have_one_winner(client, support):
    _, _, created = ticket(client)
    path = f"/tickets/{created['id']}"
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: support.patch(
                    path,
                    json={
                        "status": "resolved",
                        "expected_version": 0,
                        "resolution_message": "Fixed",
                        "request_id": str(uuid4()),
                    },
                ),
                range(2),
            )
        )
    assert sorted(r.status_code for r in results) == [200, 409]
    assert len(client.get(path + "/messages").json()) == 1
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda actor: actor.post(
                    path + "/reopen",
                    json={
                        "reason": "Issue returned",
                        "expected_version": 1,
                        "request_id": str(uuid4()),
                    },
                ),
                [client, support],
            )
        )
    assert sorted(r.status_code for r in results) == [200, 409]
    assert len(client.get(path + "/messages").json()) == 2
    assert len(client.get(path + "/events").json()) == 2


def test_public_pagination_does_not_include_internal_notes(client, support):
    _, _, created = ticket(client)
    path = f"/tickets/{created['id']}/messages"
    first = client.post(path, json=body("First")).json()
    support.post(path, json=body("Hidden", visibility="internal"))
    second = support.post(path, json=body("Second")).json()
    assert client.get(path, params={"limit": 1}).json() == [first]
    assert client.get(path, params={"limit": 1, "after_id": first["id"]}).json() == [
        second
    ]
    assert client.get(path, params={"after_id": second["id"]}).json() == []
