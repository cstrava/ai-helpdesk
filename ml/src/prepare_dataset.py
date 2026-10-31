import hashlib
import json
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ml/data/raw/it_service_tickets.csv"
OUTPUT_DIR = ROOT / "ml/data/processed"
REPORT_DIR = ROOT / "ml/reports"
SEED = 42


def main():
    raw = pd.read_csv(SOURCE)

    df = pd.DataFrame({
        "text": raw["Document"].fillna("").astype(str).str.strip(),
        "label": raw["Topic_group"].fillna("").astype(str).str.strip(),
    })

    df = df.loc[df["text"].ne("") & df["label"].ne("")].copy()

    # Folosit pentru deduplicare și verificarea separării.
    normalized = (
        df["text"]
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    df["text_id"] = normalized.map(
        lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest()
    )

    label_counts = df.groupby("text_id")["label"].nunique()
    conflicting_ids = label_counts[label_counts > 1].index
    df = df.loc[~df["text_id"].isin(conflicting_ids)]
    df = df.drop_duplicates(subset="text_id")

    train, remaining = train_test_split(
        df,
        test_size=0.20,
        random_state=SEED,
        stratify=df["label"],
    )

    validation, test = train_test_split(
        remaining,
        test_size=0.50,
        random_state=SEED,
        stratify=remaining["label"],
    )

    splits = {
        "train": train,
        "validation": validation,
        "test": test,
    }

    # Niciun text normalizat nu trebuie să apară în două partiții.
    ids = {
        name: set(frame["text_id"])
        for name, frame in splits.items()
    }

    for first, second in [
        ("train", "validation"),
        ("train", "test"),
        ("validation", "test"),
    ]:
        if ids[first] & ids[second]:
            raise ValueError(f"Data overlap: {first} and {second}")

    labels = sorted(df["label"].unique().tolist())

    for name, frame in splits.items():
        if set(frame["label"]) != set(labels):
            raise ValueError(f"Missing categories in {name}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "seed": SEED,
        "strategy": "stratified_random_80_10_10",
        "input_rows": len(raw),
        "retained_rows": len(df),
        "removed_rows": len(raw) - len(df),
        "exact_text_overlap": False,
        "near_duplicate_check_performed": False,
        "splits": {},
    }

    for name, frame in splits.items():
        path = OUTPUT_DIR / f"{name}.csv"
        frame.to_csv(path, index=False)

        report["splits"][name] = {
            "rows": len(frame),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "class_counts": {
                str(label): int(count)
                for label, count in frame["label"].value_counts().items()
            },
        }

    label_to_id = {label: index for index, label in enumerate(labels)}
    (OUTPUT_DIR / "label_mapping.json").write_text(
        json.dumps(label_to_id, indent=2) + "\n",
        encoding="utf-8",
    )

    output = json.dumps(report, indent=2)
    (REPORT_DIR / "data_split.json").write_text(
        output + "\n",
        encoding="utf-8",
    )
    print(output)


if __name__ == "__main__":
    main()