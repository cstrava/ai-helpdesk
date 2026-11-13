"""Explicit category review and minimal support-only training export."""

import csv
import hashlib
from io import StringIO
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .auth import current_user

Category = Literal[
    "Access",
    "Administrative rights",
    "HR Support",
    "Hardware",
    "Internal Project",
    "Miscellaneous",
    "Purchase",
    "Storage",
]


class CategoryReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verified_category: Category
    request_id: UUID
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


def require_support(user):
    if user["role"] != "support":
        raise HTTPException(403, "Operație rezervată suportului.")


def install_ml_feedback(app: FastAPI):
    from . import main
    from .collaboration import ticket_row

    @app.post("/tickets/{ticket_id}/category-review")
    def review_category(
        ticket_id: UUID,
        body: CategoryReview,
        user=Depends(current_user),
    ):
        require_support(user)
        with main.connect_db() as db:
            ticket = ticket_row(db, ticket_id, user, lock=True)
            source_text = f"{ticket['title'] or ''}\n{ticket['text']}"
            digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
            previous = db.execute(
                """SELECT id,ticket_id,reviewer_id,request_id,verified_category,
                   model_version,text_sha256,reason,reviewed_at,invalidated_at
                   FROM ticket_category_reviews
                   WHERE ticket_id=%s AND reviewer_id=%s AND request_id=%s""",
                (ticket_id, user["id"], body.request_id),
            ).fetchone()
            if previous:
                if (
                    previous["verified_category"] != body.verified_category
                    or previous["reason"] != (body.reason or None)
                ):
                    raise HTTPException(
                        409, "request_id a fost folosit pentru o altă revizuire."
                    )
                return previous

            db.execute(
                """UPDATE ticket_category_reviews SET invalidated_at=clock_timestamp()
                   WHERE ticket_id=%s AND invalidated_at IS NULL""",
                (ticket_id,),
            )
            return db.execute(
                """INSERT INTO ticket_category_reviews(
                     ticket_id,reviewer_id,request_id,verified_category,
                     model_version,text_sha256,reason
                   ) VALUES (%s,%s,%s,%s,%s,%s,%s)
                   RETURNING id,ticket_id,reviewer_id,request_id,verified_category,
                     model_version,text_sha256,reason,reviewed_at,invalidated_at""",
                (
                    ticket_id,
                    user["id"],
                    body.request_id,
                    body.verified_category,
                    ticket["model_version"],
                    digest,
                    body.reason or None,
                ),
            ).fetchone()

    @app.get("/tickets/{ticket_id}/category-review")
    def current_category_review(ticket_id: UUID, user=Depends(current_user)):
        require_support(user)
        with main.connect_db() as db:
            ticket_row(db, ticket_id, user)
            review = db.execute(
                """SELECT id,ticket_id,reviewer_id,verified_category,model_version,
                   text_sha256,reason,reviewed_at,invalidated_at
                   FROM ticket_category_reviews
                   WHERE ticket_id=%s AND invalidated_at IS NULL
                   ORDER BY reviewed_at DESC,id DESC LIMIT 1""",
                (ticket_id,),
            ).fetchone()
            return {"review": review}

    @app.get("/support/category-review-export")
    def export_reviewed_categories(
        limit: Annotated[int, Query(ge=1, le=10000)] = 5000,
        user=Depends(current_user),
    ):
        require_support(user)
        with main.connect_db() as db:
            rows = db.execute(
                """SELECT
                     r.ticket_id,
                     coalesce(t.title,'') || E'\\n' || t.text AS text,
                     r.verified_category AS label,
                     r.text_sha256,
                     r.model_version,
                     r.reviewer_id,
                     r.reviewed_at
                   FROM ticket_category_reviews r
                   JOIN tickets t ON t.id=r.ticket_id
                   WHERE r.invalidated_at IS NULL
                   ORDER BY r.reviewed_at,r.id
                   LIMIT %s""",
                (limit,),
            ).fetchall()

        output = StringIO(newline="")
        fields = (
            "ticket_id",
            "text",
            "label",
            "text_sha256",
            "model_version",
            "reviewer_id",
            "reviewed_at",
        )
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            exported_text = row["text"]
            if exported_text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
                exported_text = "'" + exported_text
            writer.writerow(
                {
                    **row,
                    "text": exported_text,
                    "reviewed_at": row["reviewed_at"].isoformat(),
                }
            )
        return Response(
            output.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="ai-helpdesk-reviewed-examples.csv"'
            },
        )
