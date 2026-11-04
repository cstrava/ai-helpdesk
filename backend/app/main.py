from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

import torch
from fastapi import FastAPI, Request
from pydantic import BaseModel, StringConstraints
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "ml/models/xlm_roberta_helpdesk_v2/model"
MODEL_VERSION = "xlm_roberta_helpdesk_v2"


class TicketInput(BaseModel):
    text: Annotated[str, StringConstraints(
        strip_whitespace=True, min_length=1, max_length=12_000
    )]


class Prediction(BaseModel):
    category: str
    model_version: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tokenizer = AutoTokenizer.from_pretrained(
        MODEL_DIR, local_files_only=True
    )
    app.state.model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_DIR, local_files_only=True
    )
    app.state.model.eval()
    yield


app = FastAPI(title="AI Helpdesk", lifespan=lifespan)


@app.post("/predict", response_model=Prediction)
def predict(ticket: TicketInput, request: Request) -> Prediction:
    model = request.app.state.model
    inputs = request.app.state.tokenizer(
        ticket.text,
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