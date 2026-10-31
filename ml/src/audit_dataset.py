import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "ml/data/raw/it_service_tickets.csv"
REPORT_DIR = ROOT / "ml/reports"


def main():
    df = pd.read_csv(DATA_PATH)

    required = {"Document", "Topic_group"}
    if not required.issubset(df.columns):
        raise ValueError(f"Expected columns: {sorted(required)}")

    # Normalizare pentru comparații; păstrăm textele originale.
    text = (
        df["Document"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    label = df["Topic_group"].fillna("").astype(str).str.strip()

    valid = text.ne("") & label.ne("")
    audit = pd.DataFrame({
        "text": text[valid],
        "label": label[valid],
    })

    labels_per_text = audit.groupby("text")["label"].nunique()
    conflicting_texts = labels_per_text[labels_per_text > 1].index
    conflicts = audit["text"].isin(conflicting_texts)

    # Câte exemple ar rămâne dacă eliminăm conflictele
    # și păstrăm un singur exemplar pentru fiecare text?
    candidates = audit.loc[~conflicts].drop_duplicates(subset="text")

    report = {
        "source": (
            "https://www.kaggle.com/datasets/adisongoh/"
            "it-service-ticket-classification-dataset"
        ),
        "license_as_displayed_on_source": "CC0: Public Domain",
        "file_sha256": hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
        "total_rows": len(df),
        "empty_text_rows": int(text.eq("").sum()),
        "empty_label_rows": int(label.eq("").sum()),
        "valid_rows": len(audit),
        "duplicate_text_rows_beyond_first": int(
            audit["text"].duplicated().sum()
        ),
        "texts_with_conflicting_labels": len(conflicting_texts),
        "rows_with_conflicting_labels": int(conflicts.sum()),
        "candidate_rows_after_exact_dedup_and_conflict_removal": len(candidates),
        "candidate_class_counts": {
            str(category): int(count)
            for category, count in candidates["label"].value_counts().items()
        },
        "limitations": [
            "Only exact duplicates after case and whitespace normalization checked.",
            "Near-duplicates and template similarities are not checked.",
            "Candidate filtering is diagnostic; the source CSV is unchanged.",
        ],
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output = json.dumps(report, indent=2, ensure_ascii=False)
    (REPORT_DIR / "it_service_audit.json").write_text(
        output + "\n", encoding="utf-8"
    )
    print(output)

    if len(conflicting_texts):
        print("\n--- CONFLICT EXAMPLES ---")
        for value in conflicting_texts[:5]:
            categories = sorted(
                audit.loc[audit["text"].eq(value), "label"].unique().tolist()
            )
            print(f"\nLabels: {categories}")
            print(f"Text: {value[:350]}")


if __name__ == "__main__":
    main()