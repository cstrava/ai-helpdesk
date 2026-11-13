from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.app import main as api


def start_conversation(client):
    response = client.post("/conversations")
    assert response.status_code == 201
    return response.json()["id"]


def add_message(client, conversation_id, content="Contul SAP este blocat."):
    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": content},
    )
    assert response.status_code == 201
    return response.json()


def get_draft(client, conversation_id):
    response = client.post(f"/conversations/{conversation_id}/ticket-draft")
    assert response.status_code == 200
    return response.json()


def confirmation_body(draft):
    return {
        "title": draft["title"],
        "description": draft["description"],
        "last_message_id": draft["last_message_id"],
        "confirmed": True,
    }


def test_conversation_to_ticket(client, test_db):
    conversation_id = start_conversation(client)
    turn = add_message(client, conversation_id)

    history = client.get(f"/conversations/{conversation_id}/messages")
    assert history.status_code == 200
    assert [item["role"] for item in history.json()] == ["user", "assistant"]

    draft = get_draft(client, conversation_id)
    assert draft["last_message_id"] == turn["assistant_message"]["id"]
    assert client.get("/tickets").json() == []

    body = confirmation_body(draft)
    body["title"] = "Acces SAP blocat pe laptop"

    response = client.post(
        f"/conversations/{conversation_id}/tickets",
        json=body,
    )
    assert response.status_code == 201

    ticket = response.json()
    assert ticket["title"] == body["title"]
    assert ticket["text"] == body["description"]
    assert ticket["conversation_id"] == conversation_id
    assert ticket["predicted_category"] == "Access"
    assert ticket["model_version"] == "test-classifier"
    assert ticket["status"] == "open"

    with test_db() as connection:
        saved = connection.execute(
            "SELECT * FROM tickets WHERE id = %s",
            (ticket["id"],),
        ).fetchone()

    assert saved["title"] == body["title"]
    assert str(saved["conversation_id"]) == conversation_id

    repeated = client.post(
        f"/conversations/{conversation_id}/tickets",
        json=body,
    )
    assert repeated.status_code == 409

    message = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Încă un mesaj."},
    )
    assert message.status_code == 409
    assert len(client.get("/tickets").json()) == 1

    history = client.get(f"/conversations/{conversation_id}/messages")
    assert len(history.json()) == 2


def test_stale_draft_is_rejected(client):
    conversation_id = start_conversation(client)
    add_message(client, conversation_id)
    draft = get_draft(client, conversation_id)

    add_message(client, conversation_id, "Problema a început azi.")

    response = client.post(
        f"/conversations/{conversation_id}/tickets",
        json=confirmation_body(draft),
    )

    assert response.status_code == 409
    assert client.get("/tickets").json() == []


@pytest.mark.parametrize("confirmed", [False, None, "true", 1])
def test_confirmation_must_be_boolean_true(client, confirmed):
    conversation_id = start_conversation(client)
    add_message(client, conversation_id)
    draft = get_draft(client, conversation_id)
    body = confirmation_body(draft)
    body["confirmed"] = confirmed

    response = client.post(
        f"/conversations/{conversation_id}/tickets",
        json=body,
    )

    assert response.status_code == 422
    assert client.get("/tickets").json() == []


def test_missing_confirmation_is_rejected(client):
    conversation_id = start_conversation(client)
    add_message(client, conversation_id)
    body = confirmation_body(get_draft(client, conversation_id))
    del body["confirmed"]

    response = client.post(
        f"/conversations/{conversation_id}/tickets",
        json=body,
    )

    assert response.status_code == 422
    assert client.get("/tickets").json() == []


def test_manual_correction_preserves_prediction(client, test_db):
    conversation_id = start_conversation(client)
    add_message(client, conversation_id)
    response = client.post(
        f"/conversations/{conversation_id}/tickets",
        json=confirmation_body(get_draft(client, conversation_id)),
    )
    assert response.status_code == 201
    ticket_id = response.json()["id"]
    with test_db() as connection:
        connection.execute(
            "UPDATE users SET role='support' WHERE email='owner@example.test'"
        )

    response = client.patch(
        f"/tickets/{ticket_id}",
        json={
            "final_category": "Hardware",
            "status": "in_progress",
        },
    )

    assert response.status_code == 200
    assert response.json()["predicted_category"] == "Access"
    assert response.json()["final_category"] == "Hardware"

    active = client.get("/tickets", params={"status": "in_progress"})
    assert [ticket["id"] for ticket in active.json()] == [ticket_id]
    assert client.get("/tickets", params={"status": "open"}).json() == []


@pytest.mark.parametrize(
    "body",
    [{}, {"status": None}, {"status": "invalid"}, {"unexpected": "value"}],
)
def test_invalid_ticket_updates(client, body):
    response = client.patch(f"/tickets/{uuid4()}", json=body)
    assert response.status_code == 422


def test_unknown_resources(client, test_db):
    with test_db() as connection:
        connection.execute(
            "UPDATE users SET role='support' WHERE email='owner@example.test'"
        )
    missing_id = str(uuid4())

    assert client.get(f"/conversations/{missing_id}/messages").status_code == 404

    assert (
        client.post(
            f"/conversations/{missing_id}/messages",
            json={"content": "Nu mă pot conecta."},
        ).status_code
        == 404
    )

    assert (
        client.patch(
            f"/tickets/{missing_id}",
            json={"status": "resolved"},
        ).status_code
        == 404
    )


def test_empty_inputs(client):
    conversation_id = start_conversation(client)

    assert client.post("/tickets", json={"text": "   "}).status_code == 410

    assert (
        client.post(
            f"/conversations/{conversation_id}/messages",
            json={"content": "   "},
        ).status_code
        == 422
    )

    assert (
        client.post(f"/conversations/{conversation_id}/ticket-draft").status_code == 422
    )


def test_model_failure_does_not_save_partial_turn(client, monkeypatch):
    conversation_id = start_conversation(client)
    add_message(client, conversation_id)

    before = client.get(f"/conversations/{conversation_id}/messages").json()

    def unavailable_model(*args, **kwargs):
        raise HTTPException(status_code=502, detail="Model unavailable")

    monkeypatch.setattr(api, "generate_chat_reply", unavailable_model)

    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Problema a început azi."},
    )

    assert response.status_code == 502

    after = client.get(f"/conversations/{conversation_id}/messages").json()

    assert after == before
