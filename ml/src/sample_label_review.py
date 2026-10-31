from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "ml/data/processed/train.csv"
OUTPUT_PATH = ROOT / "ml/data/processed/label_review.csv"


def main():
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"Review file already exists: {OUTPUT_PATH}"
        )

    df = pd.read_csv(INPUT_PATH)

    samples = [
        group.sample(n=min(10, len(group)), random_state=42)
        for _, group in df.groupby("label", sort=True)
    ]

    review = pd.concat(samples, ignore_index=True)
    review = review.rename(columns={"label": "original_label"})
    review["review_status"] = ""
    review["suggested_label"] = ""
    review["notes"] = ""

    review.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(review)} tickets to: {OUTPUT_PATH}")
    print("\n--- ADMINISTRATIVE RIGHTS REVIEW ---")

    selected = review[
        review["original_label"] == "Administrative rights"
    ]

    for number, row in enumerate(selected.itertuples(index=False), start=1):
        print(f"\n[{number}] ID: {row.text_id}")
        print(row.text)
        print("-" * 70)


if __name__ == "__main__":
    main()