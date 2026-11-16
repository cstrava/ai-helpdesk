"""Reproduce tracked v1/v2 and baseline evaluations without training or editing data."""

import hashlib
import json
from pathlib import Path

import joblib
import pandas as pd
import torch
import transformers
import sklearn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "ml/data/processed/grouped"
V2_DATA = ROOT / "ml/data/processed/v2"
PILOT = ROOT / "ml/evaluation/v2"
REPORTS = ROOT / "ml/reports"
SPLIT_REPORT = REPORTS / "grouped_data_split.json"
BASELINE_PATH = ROOT / "ml/models/grouped/baseline_svm.joblib"
MODEL_PATHS = {
    "v1": ROOT / "ml/models/xlm_roberta_helpdesk_v1/best_model",
    "v2": ROOT / "ml/models/xlm_roberta_helpdesk_v2/model",
}
OUTPUT = REPORTS / "reproducible_v1_v2_baseline.json"
BATCH_SIZE = 8
MAX_LENGTH = 256


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_identity(path: Path) -> dict:
    config_path = path / "config.json"
    weights = path / "model.safetensors"
    return {
        "local_id": path.relative_to(ROOT).as_posix(),
        "config_sha256": sha256(config_path),
        "weights_sha256": sha256(weights),
    }


def load_classifier(path: Path, device: torch.device):
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        path, local_files_only=True
    )
    model.to(device)
    model.eval()
    return tokenizer, model


def predict_transformer(
    tokenizer, model, texts: list[str], device, model_name: str
) -> list[str]:
    labels = model.config.id2label
    predictions = []
    with torch.inference_mode():
        for start in range(0, len(texts), BATCH_SIZE):
            batch = texts[start : start + BATCH_SIZE]
            inputs = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt",
            ).to(device)
            ids = model(**inputs).logits.argmax(dim=-1).tolist()
            predictions.extend(labels[index] for index in ids)
            if len(predictions) % 512 == 0 or len(predictions) == len(texts):
                print(
                    f"{model_name}: {len(predictions)}/{len(texts)}",
                    flush=True,
                )
    return predictions


def score(truth: list[str], predicted: list[str], labels: list[str]) -> dict:
    report = classification_report(
        truth,
        predicted,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    return {
        "rows": len(truth),
        "accuracy": float(accuracy_score(truth, predicted)),
        "macro_f1": float(
            f1_score(truth, predicted, labels=labels, average="macro", zero_division=0)
        ),
        "per_class": {
            label: {
                "precision": report[label]["precision"],
                "recall": report[label]["recall"],
                "f1": report[label]["f1-score"],
                "support": int(report[label]["support"]),
            }
            for label in labels
        },
        "confusion_matrix": {
            "labels": labels,
            "counts": confusion_matrix(truth, predicted, labels=labels).tolist(),
        },
    }


def predict_models(texts, device):
    predictions = {"baseline": joblib.load(BASELINE_PATH).predict(texts).tolist()}
    for name, path in MODEL_PATHS.items():
        tokenizer, model = load_classifier(path, device)
        print(f"Evaluating {name} on {len(texts)} records…", flush=True)
        predictions[name] = predict_transformer(
            tokenizer, model, texts, device, name
        )
        del model, tokenizer
        if device.type == "cuda":
            torch.cuda.empty_cache()
    return predictions


def main():
    split = json.loads(SPLIT_REPORT.read_text(encoding="utf-8"))
    if split.get("cross_split_group_overlap") is not False:
        raise ValueError("Manifestul nu confirmă izolarea grupurilor între splituri.")
    for part in ("train", "validation"):
        path = DATA / f"{part}.csv"
        expected = split["splits"][part]["sha256"]
        if sha256(path) != expected:
            raise ValueError(f"Hash-ul grouped {part}.csv nu corespunde manifestului.")

    train_pairs = pd.read_csv(PILOT / "train_pairs.csv")
    holdout_pairs = pd.read_csv(PILOT / "holdout_pairs.csv")
    if train_pairs["scenario_id"].duplicated().any():
        raise ValueError("train_pairs.csv trebuie să aibă un singur rând per scenariu.")
    if holdout_pairs["scenario_id"].duplicated().any():
        raise ValueError("holdout_pairs.csv trebuie să aibă un singur rând per scenariu.")
    overlap = set(train_pairs["scenario_id"]) & set(holdout_pairs["scenario_id"])
    if overlap:
        raise ValueError("Scenariile traduse se suprapun între train și holdout.")
    if holdout_pairs.groupby("scenario_id")["label"].nunique().max() != 1:
        raise ValueError("Etichetele traducerilor din holdout nu sunt consistente.")

    validation = pd.read_csv(DATA / "validation.csv")
    labels = sorted(split["splits"]["validation"]["class_counts"])
    pilot = holdout_pairs.melt(
        id_vars=["scenario_id", "label"],
        value_vars=["ro", "en"],
        var_name="language",
        value_name="text",
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(split["seed"])
    if device.type == "cuda":
        torch.cuda.manual_seed_all(split["seed"])
    if device.type == "cpu":
        torch.set_num_threads(2)

    validation_predictions = predict_models(validation["text"].tolist(), device)
    pilot_predictions = predict_models(pilot["text"].tolist(), device)

    validation_metrics = {
        model: score(validation["label"].tolist(), prediction, labels)
        for model, prediction in validation_predictions.items()
    }
    pilot_metrics = {}
    pilot["group_id"] = pilot["scenario_id"]
    for language, subset in pilot.groupby("language", sort=True):
        indices = subset.index
        pilot_metrics[language] = {
            model: score(
                subset["label"].tolist(),
                [prediction[index] for index in indices],
                labels,
            )
            for model, prediction in pilot_predictions.items()
        }

    report = {
        "schema_version": 1,
        "evaluation_config": {
            "grouped_split_seed": split["seed"],
            "grouping": split["grouping"],
            "similarity_threshold": split["similarity_threshold"],
            "split_method": split["split_method"],
            "scenario_grouping": "one holdout row contains both RO and EN translations; group_id is scenario_id",
            "translation_train_holdout_overlap": False,
            "grouped_split_cross_overlap": split["cross_split_group_overlap"],
            "batch_size": BATCH_SIZE,
            "max_length": MAX_LENGTH,
            "device": str(device),
            "torch_version": torch.__version__,
            "transformers_version": transformers.__version__,
            "scikit_learn_version": sklearn.__version__,
            "inference_only": True,
            "v2_training_configuration_available": False,
            "v2_training_configuration_note": "No versioned v2 trainer or complete training configuration was found; weights, model config, and available input data are hashed, but this does not reproduce v2 training.",
            "holdout_policy": "v2 is evaluated only on the paired bilingual pilot holdout, never on grouped_test",
            "validation_caveat": "The grouped English validation split was included as validation data in the v2 training archive; this score is not an independent holdout.",
        },
        "dataset_hashes": {
            "grouped_train": sha256(DATA / "train.csv"),
            "grouped_validation": sha256(DATA / "validation.csv"),
            "v2_training_pairs": sha256(PILOT / "train_pairs.csv"),
            "v2_holdout_pairs": sha256(PILOT / "holdout_pairs.csv"),
            "v2_mixed_training_data": sha256(V2_DATA / "train_mixed.csv"),
        },
        "models": {
            "baseline": {
                "local_id": "ml/models/grouped/baseline_svm.joblib",
                "artifact_sha256": sha256(BASELINE_PATH),
                "version": "tfidf_linear_svm_grouped_v1",
            },
            **{
                name: {**model_identity(path), "version": f"xlm_roberta_helpdesk_{name}"}
                for name, path in MODEL_PATHS.items()
            },
        },
        "grouped_english_validation": validation_metrics,
        "bilingual_pilot_holdout": {
            "scenario_count": int(holdout_pairs["scenario_id"].nunique()),
            "paired_text_count": len(pilot),
            "metrics_by_language": pilot_metrics,
        },
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    for model, result in validation_metrics.items():
        print(
            f"English validation {model}: accuracy={result['accuracy']:.4f} "
            f"macro-F1={result['macro_f1']:.4f}"
        )
    for language, results in pilot_metrics.items():
        for model, result in results.items():
            print(
                f"Pilot {language.upper()} {model}: accuracy={result['accuracy']:.4f} "
                f"macro-F1={result['macro_f1']:.4f}"
            )
    print(f"Raport scris în {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
