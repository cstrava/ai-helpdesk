import json
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "ml/data/processed"
MODEL_DIR = ROOT / "ml/models"
REPORT_DIR = ROOT / "ml/reports"


def main():
    train = pd.read_csv(DATA_DIR / "train.csv")
    validation = pd.read_csv(DATA_DIR / "validation.csv")

    labels = sorted(train["label"].unique().tolist())

    # Reper simplu: prezice mereu categoria majoritară.
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit([[0]] * len(train), train["label"])
    dummy_predictions = dummy.predict([[0]] * len(validation))

    # Pipeline-ul învață vocabularul exclusiv din datele de train.
    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.98,
                max_features=100_000,
                sublinear_tf=True,
            ),
        ),
        (
            "classifier",
            LinearSVC(
                C=1.0,
                class_weight="balanced",
                random_state=42,
                max_iter=5000,
            ),
        ),
    ])

    print(f"Training on {len(train):,} tickets...", flush=True)
    started = time.perf_counter()
    model.fit(train["text"], train["label"])
    training_seconds = time.perf_counter() - started

    predictions = model.predict(validation["text"])

    report = {
        "model": "tfidf_linear_svm_v1",
        "evaluation_split": "validation",
        "train_rows": len(train),
        "validation_rows": len(validation),
        "training_seconds": round(training_seconds, 2),
        "vocabulary_size": len(
            model.named_steps["tfidf"].vocabulary_
        ),
        "parameters": {
            "ngram_range": [1, 2],
            "min_df": 2,
            "max_df": 0.98,
            "max_features": 100_000,
            "sublinear_tf": True,
            "C": 1.0,
            "class_weight": "balanced",
            "random_state": 42,
        },
        "majority_baseline": {
            "accuracy": accuracy_score(
                validation["label"], dummy_predictions
            ),
            "macro_f1": f1_score(
                validation["label"],
                dummy_predictions,
                average="macro",
                zero_division=0,
            ),
        },
        "svm": {
            "accuracy": accuracy_score(
                validation["label"], predictions
            ),
            "macro_f1": f1_score(
                validation["label"],
                predictions,
                average="macro",
                zero_division=0,
            ),
            "per_class": classification_report(
                validation["label"],
                predictions,
                labels=labels,
                output_dict=True,
                zero_division=0,
            ),
        },
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Salvăm împreună vectorizatorul și clasificatorul.
    joblib.dump(model, MODEL_DIR / "baseline_svm.joblib")

    (REPORT_DIR / "baseline_validation.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    matrix = confusion_matrix(
        validation["label"], predictions, labels=labels
    )
    pd.DataFrame(
        matrix,
        index=pd.Index(labels, name="actual"),
        columns=pd.Index(labels, name="predicted"),
    ).to_csv(REPORT_DIR / "baseline_confusion_matrix.csv")

    # Textele rămân în folderul de date, exclus din Git.
    errors = validation[["text_id", "text", "label"]].copy()
    errors["prediction"] = predictions
    errors = errors.loc[errors["label"] != errors["prediction"]]
    errors.to_csv(
        DATA_DIR / "baseline_validation_errors.csv",
        index=False,
    )

    print(f"\nTraining time: {training_seconds:.1f} seconds")
    print(f"Vocabulary: {report['vocabulary_size']:,} features")

    print("\nMAJORITY BASELINE")
    print(f"Accuracy: {report['majority_baseline']['accuracy']:.4f}")
    print(f"Macro-F1: {report['majority_baseline']['macro_f1']:.4f}")

    print("\nTF-IDF + LINEAR SVM")
    print(f"Accuracy: {report['svm']['accuracy']:.4f}")
    print(f"Macro-F1: {report['svm']['macro_f1']:.4f}")

    print("\nPER-CLASS RESULTS")
    print(classification_report(
        validation["label"],
        predictions,
        labels=labels,
        digits=4,
        zero_division=0,
    ))

    print(f"Validation errors: {len(errors)}")
    print(f"Model saved to: {MODEL_DIR / 'baseline_svm.joblib'}")


if __name__ == "__main__":
    main()