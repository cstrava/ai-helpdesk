import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

import psycopg
import torch
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator
from psycopg.rows import dict_row
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "ml/models/xlm_roberta_helpdesk_v2/model"
MODEL_VERSION = "xlm_roberta_helpdesk_v2"

load_dotenv(ROOT / ".env")


class TicketInput(BaseModel):
    text: Annotated[str, StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=12_000,
    )]


class Prediction(BaseModel):
    category: str
    model_version: str


class TicketResponse(BaseModel):
    id: UUID
    text: str
    predicted_category: str
    final_category: str
    model_version: str
    status: Literal["open", "in_progress", "resolved"]
    created_at: datetime

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

TicketStatus = Literal["open", "in_progress", "resolved"]


class TicketUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    final_category: Category | None = None
    status: TicketStatus | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("Trimite cel puțin un câmp de actualizat.")

        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"Câmpul {field} nu poate fi null.")

        return self

def connect_db():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        dbname=os.getenv("POSTGRES_DB", "ai_helpdesk"),
        user=os.getenv("POSTGRES_USER", "helpdesk"),
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
        row_factory=dict_row,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("POSTGRES_PASSWORD"):
        raise RuntimeError("POSTGRES_PASSWORD lipsește din configurație.")

    with connect_db() as connection:
        connection.execute("SELECT 1")

    app.state.tokenizer = AutoTokenizer.from_pretrained(
        MODEL_DIR,
        local_files_only=True,
    )
    app.state.model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR,
        local_files_only=True,
    )
    app.state.model.eval()
    yield


app = FastAPI(title="AI Helpdesk", lifespan=lifespan)


def classify(text: str, request: Request) -> Prediction:
    model = request.app.state.model
    inputs = request.app.state.tokenizer(
        text,
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )

    with torch.inference_mode():
        label_id = model(**inputs).logits.argmax(dim=-1).item()

    return Prediction(
        category=model.config.id2label[label_id],
        model_version=MODEL_VERSION,
    )


@app.post("/predict", response_model=Prediction)
def predict(ticket: TicketInput, request: Request) -> Prediction:
    return classify(ticket.text, request)


@app.post("/tickets", response_model=TicketResponse, status_code=201)
def create_ticket(ticket: TicketInput, request: Request) -> TicketResponse:
    prediction = classify(ticket.text, request)

    try:
        with connect_db() as connection:
            row = connection.execute(
                """
                INSERT INTO tickets (
                    text,
                    predicted_category,
                    final_category,
                    model_version
                )
                VALUES (%s, %s, %s, %s)
                RETURNING
                    id,
                    text,
                    predicted_category,
                    final_category,
                    model_version,
                    status,
                    created_at
                """,
                (
                    ticket.text,
                    prediction.category,
                    prediction.category,
                    prediction.model_version,
                ),
            ).fetchone()

            response = TicketResponse.model_validate(row)

    except psycopg.OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail="Baza de date este momentan indisponibilă.",
        ) from exc

    return response

@app.get("/tickets", response_model=list[TicketResponse])
def list_tickets(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: TicketStatus | None = None,
) -> list[TicketResponse]:
    try:
        with connect_db() as connection:
            rows = connection.execute(
                """
                SELECT
                    id,
                    text,
                    predicted_category,
                    final_category,
                    model_version,
                    status,
                    created_at
                FROM tickets
                WHERE (%s::text IS NULL OR status = %s)
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                (status, status, limit, offset),
            ).fetchall()

    except psycopg.OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail="Baza de date este momentan indisponibilă.",
        ) from exc

    return [TicketResponse.model_validate(row) for row in rows]


@app.patch("/tickets/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: UUID,
    update: TicketUpdate,
) -> TicketResponse:
    try:
        with connect_db() as connection:
            row = connection.execute(
                """
                UPDATE tickets
                SET
                    final_category = COALESCE(%s, final_category),
                    status = COALESCE(%s, status)
                WHERE id = %s
                RETURNING
                    id,
                    text,
                    predicted_category,
                    final_category,
                    model_version,
                    status,
                    created_at
                """,
                (
                    update.final_category,
                    update.status,
                    ticket_id,
                ),
            ).fetchone()

            if row is None:
                raise HTTPException(
                    status_code=404,
                    detail="Tichetul nu există.",
                )

            response = TicketResponse.model_validate(row)

    except psycopg.OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail="Baza de date este momentan indisponibilă.",
        ) from exc

    return response