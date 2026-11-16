import json
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "ml/data/raw"
REPORT_DIR = ROOT / "ml/reports"

DATASET_ID = "Console-AI/IT-helpdesk-synthetic-tickets"


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    revision = HfApi().dataset_info(DATASET_ID).sha
    dataset = load_dataset(DATASET_ID, revision=revision, split="train")
    df = dataset.to_pandas()

    required = {"subject", "description", "category"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    df.to_csv(RAW_DIR / "console_ai_tickets.csv", index=False)

    text = (
        df["subject"].fillna("").astype(str)
        + " "
        + df["description"].fillna("").astype(str)
    )
    normalized = text.str.lower().str.replace(r"\s+", " ", regex=True).str.strip()

    report = {
        "dataset": DATASET_ID,
        "revision": revision,
        "status": "candidate_under_review",
        "synthetic": True,
        "rows": len(df),
        "columns": df.columns.tolist(),
        "missing_values": {
            column: int(count)
            for column, count in df.isna().sum().items()
        },
        "empty_texts": int(normalized.eq("").sum()),
        "duplicate_texts": int(normalized.duplicated().sum()),
        "category_counts": {
            str(category): int(count)
            for category, count in df["category"].value_counts(dropna=False).items()
        },
    }

    output = json.dumps(report, indent=2, ensure_ascii=False)
    (REPORT_DIR / "dataset_inspection.json").write_text(
        output + "\n", encoding="utf-8"
    )
    print(output)

    print("\n--- SAMPLE TICKETS ---")
    for _, row in df.sample(n=min(5, len(df)), random_state=42).iterrows():
        print(f"\nCategory: {row['category']}")
        print(f"Subject: {row['subject']}")
        print(f"Description: {str(row['description'])[:400]}")


if __name__ == "__main__":
    main()