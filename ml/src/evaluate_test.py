import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
import torch
from sklearn.metrics import accuracy_score, classification_report, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
TEST_PATH = ROOT / "ml/data/processed/grouped/test.csv"
SPLIT_REPORT = ROOT / "ml/reports/grouped_data_split.json"
SVM_PATH = ROOT / "ml/models/grouped/baseline_svm.joblib"
XLM_PATH = ROOT / "ml/models/xlm_roberta_helpdesk_v1/best_model"
OUTPUT = ROOT / "ml/reports/grouped/test_comparison.json"


def predict_xlm(texts):
    tokenizer = AutoTokenizer.from_pretrained(XLM_PATH, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        XLM_PATH, local_files_only=True
    )
    model.eval()

    predictions = []
    batch_size = 8

    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            inputs = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            )
            ids = model(**inputs).logits.argmax(dim=-1).tolist()
            predictions.extend(model.config.id2label[i] for i in ids)

            if len(predictions) % 400 == 0 or len(predictions) == len(texts):
                print(f"XLM-RoBERTa: {len(predictions)}/{len(texts)}", flush=True)

    return predictions


def main():
    expected = json.loads(SPLIT_REPORT.read_text())["splits"]["test"]
    checksum = hashlib.sha256(TEST_PATH.read_bytes()).hexdigest()
    if checksum != expected["sha256"]:
        raise ValueError("Checksum diferit pentru test.csv")

    test = pd.read_csv(TEST_PATH)
    texts = test["text"].tolist()
    truth = test["label"].tolist()
    labels = sorted(expected["class_counts"])

    svm = joblib.load(SVM_PATH)
    predictions = {
        "svm": svm.predict(texts),
        "xlm_roberta": predict_xlm(texts),
    }

    report = {"split": "grouped_test", "rows": len(test), "sha256": checksum}

    for name, predicted in predictions.items():
        accuracy = accuracy_score(truth, predicted)
        macro_f1 = f1_score(
            truth, predicted, labels=labels, average="macro", zero_division=0
        )
        report[name] = {
            "accuracy": accuracy,
            "macro_f1": macro_f1,
            "per_class": classification_report(
                truth, predicted, labels=labels, output_dict=True, zero_division=0
            ),
        }
        print(f"{name}: accuracy={accuracy:.4f} | macro-F1={macro_f1:.4f}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Raport salvat: {OUTPUT}")


if __name__ == "__main__":
    main()