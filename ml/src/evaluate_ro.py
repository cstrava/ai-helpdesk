import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score

from evaluate_test import predict_xlm

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ml/evaluation/ro_tickets_v1.csv"
MAPPING = ROOT / "ml/data/processed/grouped/label_mapping.json"
OUTPUT = ROOT / "ml/reports/ro_evaluation_v1.json"


def main():
    tickets = pd.read_csv(SOURCE)
    labels = list(json.loads(MAPPING.read_text(encoding="utf-8")))

    if tickets[["id", "text", "label"]].isna().any().any():
        raise ValueError("Există câmpuri goale în fișierul de evaluare.")
    if not tickets["id"].is_unique or not tickets["text"].is_unique:
        raise ValueError("Există ID-uri sau texte duplicate.")
    if tickets["label"].value_counts().to_dict() != dict.fromkeys(labels, 3):
        raise ValueError("Setul trebuie să conțină câte 3 tichete pentru fiecare clasă.")

    truth = tickets["label"].tolist()
    predictions = predict_xlm(tickets["text"].tolist())
    tickets["prediction"] = predictions

    correct = tickets["label"].eq(tickets["prediction"])
    report = {
        "dataset": "ro_tickets_v1",
        "description": "Small manually authored Romanian evaluation set",
        "model": "xlm_roberta_helpdesk_v1",
        "correct": int(correct.sum()),
        "total": len(tickets),
        "accuracy": accuracy_score(truth, predictions),
        "macro_f1": f1_score(
            truth, predictions, labels=labels, average="macro", zero_division=0
        ),
        "per_class": classification_report(
            truth, predictions, labels=labels, output_dict=True, zero_division=0
        ),
        "predictions": tickets.to_dict(orient="records"),
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Corecte: {report['correct']}/{report['total']}")
    print(f"Accuracy: {report['accuracy']:.4f}")
    print(f"Macro-F1: {report['macro_f1']:.4f}")

    for row in tickets.loc[~correct].itertuples(index=False):
        print(f"\n{row.id}: {row.label} -> {row.prediction}")
        print(row.text)


if __name__ == "__main__":
    main()