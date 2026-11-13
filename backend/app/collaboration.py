"""Ticket collaboration with row locks, optimistic updates and idempotent messages."""

from typing import Annotated, Literal
from uuid import UUID, uuid4
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from .auth import current_user

Content = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class Reply(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: Content
    visibility: Literal["public", "internal"] = "public"
    request_id: UUID


class Assignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignee_id: UUID | None
    expected_version: Annotated[int, Field(strict=True, ge=0)]


class Version(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: Annotated[int, Field(strict=True, ge=0)]


class Reopen(Version):
    reason: Content
    request_id: UUID


def ticket_row(db, ticket_id, user, lock=False):
    row = db.execute(
        "SELECT tickets.*, (SELECT email FROM users WHERE users.id=tickets.assignee_id) AS assignee_email FROM tickets WHERE id=%s AND (%s='support' OR owner_id=%s)"
        + (" FOR UPDATE" if lock else ""),
        (ticket_id, user["role"], user["id"]),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Tichetul nu există.")
    return row


def require_support(user):
    if user["role"] != "support":
        raise HTTPException(403, "Operație rezervată suportului.")


def check_version(row, expected):
    if row["version"] != expected:
        raise HTTPException(
            409, "Tichetul s-a schimbat. Reîncarcă detaliile înainte de salvare."
        )


def event(db, ticket_id, user, field, old, new):
    if old != new:
        db.execute(
            "INSERT INTO ticket_events(ticket_id,actor_id,field,old_value,new_value) VALUES (%s,%s,%s,%s,%s)",
            (
                ticket_id,
                user["id"],
                field,
                str(old) if old is not None else "unassigned",
                str(new) if new is not None else "unassigned",
            ),
        )


def message_result(db, message_id):
    return db.execute(
        "SELECT m.id,m.ticket_id,m.content,m.visibility,m.kind,m.request_id,m.created_at,u.email AS author,u.role AS author_role FROM ticket_messages m JOIN users u ON u.id=m.author_id WHERE m.id=%s",
        (message_id,),
    ).fetchone()


def existing_message(db, ticket_id, user, request_id, content, visibility, kind):
    row = db.execute(
        "SELECT * FROM ticket_messages WHERE ticket_id=%s AND author_id=%s AND request_id=%s",
        (ticket_id, user["id"], request_id),
    ).fetchone()
    if row and (row["content"], row["visibility"], row["kind"]) != (
        content,
        visibility,
        kind,
    ):
        raise HTTPException(
            409, "Identificatorul cererii a fost deja folosit pentru alt mesaj."
        )
    return row


def insert_message(db, ticket_id, user, content, visibility, kind, request_id):
    return db.execute(
        "INSERT INTO ticket_messages(ticket_id,author_id,content,visibility,kind,request_id) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (ticket_id, user["id"], content, visibility, kind, request_id),
    ).fetchone()["id"]


def notify(db, recipient_id, ticket_id, kind, source_key):
    if recipient_id is not None:
        db.execute(
            "INSERT INTO notifications(recipient_id,ticket_id,kind,source_key) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (recipient_id, ticket_id, kind, source_key),
        )


def response_recipients(db, ticket, user):
    recipients = {ticket["owner_id"], ticket["assignee_id"]} - {user["id"], None}
    if ticket["assignee_id"] is None and user["role"] != "support":
        recipients.update(
            row["id"]
            for row in db.execute("SELECT id FROM users WHERE role='support'").fetchall()
        )
        recipients.discard(user["id"])
    return recipients


def update_ticket(db, ticket_id, update, user):
    require_support(user)
    row = ticket_row(db, ticket_id, user, True)
    if (
        update.resolution_message is not None or update.request_id is not None
    ) and update.status != "resolved":
        raise HTTPException(
            422, "Mesajul de rezolvare este permis numai pentru resolved."
        )
    if update.expected_version is not None:
        check_version(row, update.expected_version)
    if (
        update.priority is not None
        and update.priority != row["priority"]
        and update.expected_version is None
    ):
        raise HTTPException(422, "Schimbarea priorității cere expected_version.")
    if update.status is not None and update.status != row["status"]:
        if update.expected_version is None:
            raise HTTPException(422, "Schimbarea statusului cere expected_version.")
        if row["status"] == "resolved":
            raise HTTPException(
                409, "Redeschiderea cere un motiv și operația dedicată."
            )
        if update.status == "resolved":
            if not update.resolution_message or not update.request_id:
                raise HTTPException(
                    422, "Rezolvarea cere mesaj de rezolvare și request_id."
                )
            existing = existing_message(
                db,
                ticket_id,
                user,
                update.request_id,
                update.resolution_message,
                "public",
                "resolution",
            )
            if existing:
                raise HTTPException(
                    409,
                    "Această cerere de rezolvare a fost deja procesată. Reîncarcă tichetul.",
                )
            insert_message(
                db,
                ticket_id,
                user,
                update.resolution_message,
                "public",
                "resolution",
                update.request_id,
            )
    elif update.resolution_message is not None or update.request_id is not None:
        raise HTTPException(
            422, "Mesajul de rezolvare este permis numai la tranziția în resolved."
        )
    changed = False
    for field in ("final_category", "status", "priority"):
        value = getattr(update, field)
        if value is not None and row[field] != value:
            event(db, ticket_id, user, field, row[field], value)
            changed = True
    if changed:
        db.execute(
            "UPDATE tickets SET final_category=coalesce(%s,final_category),status=coalesce(%s,status),priority=coalesce(%s,priority),version=version+1,updated_at=now(),first_resolved_at=CASE WHEN %s='resolved' THEN coalesce(first_resolved_at,now()) ELSE first_resolved_at END WHERE id=%s",
            (
                update.final_category,
                update.status,
                update.priority,
                update.status,
                ticket_id,
            ),
        )
        if update.status is not None and update.status != row["status"]:
            notify(
                db,
                row["owner_id"],
                ticket_id,
                "status",
                update.request_id or uuid4(),
            )
        if update.status == "resolved" and update.request_id:
            notify(db, row["owner_id"], ticket_id, "reply", update.request_id)
    return ticket_row(db, ticket_id, user)


def install_collaboration(app):
    from . import main

    @app.get("/support/agents")
    def agents(user=Depends(current_user)):
        require_support(user)
        with main.connect_db() as db:
            return db.execute(
                "SELECT id,email FROM users WHERE role='support' ORDER BY email,id"
            ).fetchall()

    @app.get("/tickets/{ticket_id}/messages")
    def messages(
        ticket_id: UUID,
        user=Depends(current_user),
        after_id: UUID | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ):
        with main.connect_db() as db:
            ticket_row(db, ticket_id, user)
            cursor = None
            if after_id is not None:
                cursor = db.execute(
                    "SELECT created_at,id FROM ticket_messages WHERE id=%s AND ticket_id=%s AND (%s='support' OR visibility='public')",
                    (after_id, ticket_id, user["role"]),
                ).fetchone()
                if cursor is None:
                    raise HTTPException(404, "Cursorul nu există.")
            return db.execute(
                "SELECT m.id,m.ticket_id,m.content,m.visibility,m.kind,m.request_id,m.created_at,u.email AS author,u.role AS author_role FROM ticket_messages m JOIN users u ON u.id=m.author_id WHERE m.ticket_id=%s AND (%s::timestamptz IS NULL OR (m.created_at,m.id)>(%s,%s)) AND (%s='support' OR m.visibility='public') ORDER BY m.created_at,m.id LIMIT %s",
                (
                    ticket_id,
                    cursor["created_at"] if cursor else None,
                    cursor["created_at"] if cursor else None,
                    cursor["id"] if cursor else None,
                    user["role"],
                    limit,
                ),
            ).fetchall()

    @app.post("/tickets/{ticket_id}/messages", status_code=201)
    def reply(ticket_id: UUID, body: Reply, user=Depends(current_user)):
        if body.visibility == "internal":
            require_support(user)
        with main.connect_db() as db:
            ticket = ticket_row(db, ticket_id, user, True)
            previous = existing_message(
                db,
                ticket_id,
                user,
                body.request_id,
                body.content,
                body.visibility,
                "reply",
            )
            mid = (
                previous["id"]
                if previous
                else insert_message(
                    db,
                    ticket_id,
                    user,
                    body.content,
                    body.visibility,
                    "reply",
                    body.request_id,
                )
            )
            if body.visibility == "public" and previous is None:
                for recipient in response_recipients(db, ticket, user):
                    notify(db, recipient, ticket_id, "reply", body.request_id)
            # Ordinary replies never change status, assignment or the public audit.
            return message_result(db, mid)

    def assign(db, ticket_id, body, user, claim=False):
        require_support(user)
        row = ticket_row(db, ticket_id, user, True)
        check_version(row, body.expected_version)
        target = user["id"] if claim else body.assignee_id
        if claim and row["assignee_id"] is not None:
            raise HTTPException(
                409, "Tichetul a fost deja preluat. Reîncarcă detaliile."
            )
        if (
            target is not None
            and not db.execute(
                "SELECT id FROM users WHERE id=%s AND role='support'", (target,)
            ).fetchone()
        ):
            raise HTTPException(
                422, "Responsabilul trebuie să fie un cont support valid."
            )
        if row["assignee_id"] != target:
            event(db, ticket_id, user, "assignee_id", row["assignee_id"], target)
            db.execute(
                "UPDATE tickets SET assignee_id=%s,version=version+1,updated_at=now() WHERE id=%s",
                (target, ticket_id),
            )
            for recipient in {row["owner_id"], target} - {user["id"], None}:
                notify(db, recipient, ticket_id, "assignment", uuid4())
        return main.TicketResponse.model_validate(ticket_row(db, ticket_id, user))

    @app.put("/tickets/{ticket_id}/assignment", response_model=main.TicketResponse)
    def assignment(ticket_id: UUID, body: Assignment, user=Depends(current_user)):
        with main.connect_db() as db:
            return assign(db, ticket_id, body, user)

    @app.post("/tickets/{ticket_id}/claim", response_model=main.TicketResponse)
    def claim(ticket_id: UUID, body: Version, user=Depends(current_user)):
        with main.connect_db() as db:
            return assign(db, ticket_id, body, user, True)

    @app.post("/tickets/{ticket_id}/reopen", response_model=main.TicketResponse)
    def reopen(ticket_id: UUID, body: Reopen, user=Depends(current_user)):
        with main.connect_db() as db:
            row = ticket_row(db, ticket_id, user, True)
            previous = existing_message(
                db, ticket_id, user, body.request_id, body.reason, "public", "reopen"
            )
            if previous:
                return main.TicketResponse.model_validate(row)
            check_version(row, body.expected_version)
            if row["status"] != "resolved":
                raise HTTPException(409, "Numai un tichet resolved poate fi redeschis.")
            insert_message(
                db, ticket_id, user, body.reason, "public", "reopen", body.request_id
            )
            event(db, ticket_id, user, "status", "resolved", "open")
            db.execute(
                "UPDATE tickets SET status='open',version=version+1,updated_at=now() WHERE id=%s",
                (ticket_id,),
            )
            for recipient in response_recipients(db, row, user):
                notify(db, recipient, ticket_id, "reply", body.request_id)
                notify(db, recipient, ticket_id, "status", body.request_id)
            return main.TicketResponse.model_validate(ticket_row(db, ticket_id, user))

    @app.get("/notifications")
    def notifications(
        user=Depends(current_user),
        limit: Annotated[int, Query(ge=1, le=50)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ):
        with main.connect_db() as db:
            return db.execute(
                """SELECT n.id,n.ticket_id,n.kind,n.created_at,n.read_at,t.title
                FROM notifications n JOIN tickets t ON t.id=n.ticket_id
                WHERE n.recipient_id=%s AND (%s='support' OR t.owner_id=%s)
                ORDER BY n.created_at DESC,n.id DESC LIMIT %s OFFSET %s""",
                (user["id"], user["role"], user["id"], limit, offset),
            ).fetchall()

    @app.get("/notifications/unread-count")
    def unread_count(user=Depends(current_user)):
        with main.connect_db() as db:
            return db.execute(
                """SELECT count(*) AS count FROM notifications n
                JOIN tickets t ON t.id=n.ticket_id
                WHERE n.recipient_id=%s AND n.read_at IS NULL
                  AND (%s='support' OR t.owner_id=%s)""",
                (user["id"], user["role"], user["id"]),
            ).fetchone()

    @app.patch("/notifications/{notification_id}/read")
    def mark_notification_read(notification_id: UUID, user=Depends(current_user)):
        with main.connect_db() as db:
            row = db.execute(
                """UPDATE notifications n SET read_at=coalesce(read_at,now())
                FROM tickets t WHERE n.id=%s AND n.recipient_id=%s
                  AND t.id=n.ticket_id AND (%s='support' OR t.owner_id=%s)
                RETURNING n.id,n.ticket_id,n.kind,n.created_at,n.read_at,t.title""",
                (notification_id, user["id"], user["role"], user["id"]),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Notificarea nu există.")
            return row

    @app.get("/support/dashboard")
    def support_dashboard(
        days: Annotated[int, Query(ge=1, le=365)] = 30,
        user=Depends(current_user),
    ):
        require_support(user)
        with main.connect_db() as db:
            period = "created_at >= now() - (%s * interval '1 day') AND created_at <= now()"
            counts = db.execute(
                f"SELECT status,count(*) AS count FROM tickets WHERE {period} GROUP BY status",
                (days,),
            ).fetchall()
            unassigned = db.execute(
                f"SELECT count(*) AS count FROM tickets WHERE assignee_id IS NULL AND {period}",
                (days,),
            ).fetchone()["count"]
            categories = db.execute(
                f"SELECT final_category AS category,count(*) AS count FROM tickets WHERE {period} GROUP BY final_category ORDER BY final_category",
                (days,),
            ).fetchall()
            priorities = db.execute(
                f"SELECT priority,count(*) AS count FROM tickets WHERE {period} GROUP BY priority ORDER BY priority",
                (days,),
            ).fetchall()
            metrics = db.execute(
                """WITH scoped AS (
                    SELECT t.id,t.created_at,t.first_resolved_at FROM tickets t
                    WHERE t.created_at >= now() - (%s * interval '1 day')
                      AND t.created_at <= now()
                ), first_reply AS (
                    SELECT m.ticket_id,min(m.created_at) AS at
                    FROM ticket_messages m JOIN users u ON u.id=m.author_id
                    WHERE m.visibility='public' AND m.kind IN ('reply','resolution')
                      AND u.role='support' GROUP BY m.ticket_id
                )
                SELECT
                    avg(extract(epoch FROM (r.at-s.created_at)))
                      FILTER (WHERE r.at IS NOT NULL) AS avg_first_reply_seconds,
                    count(*) FILTER (WHERE r.at IS NULL)
                      AS without_public_support_reply,
                    avg(extract(epoch FROM (s.first_resolved_at-s.created_at)))
                      FILTER (WHERE s.first_resolved_at IS NOT NULL)
                      AS avg_first_resolution_seconds,
                    count(*) FILTER (WHERE s.first_resolved_at IS NULL)
                      AS without_first_resolution_event
                FROM scoped s LEFT JOIN first_reply r ON r.ticket_id=s.id""",
                (days,),
            ).fetchone()
        return {
            "days": days,
            "status_counts": counts,
            "unassigned_count": unassigned,
            "category_counts": categories,
            "priority_counts": priorities,
            **metrics,
        }
