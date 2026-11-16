import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "ml/evaluation/v2"
OUTPUT = ROOT / "ml/data/processed/v2"
GROUPED = ROOT / "ml/data/processed/grouped"


def main():
    labels = set(json.loads((GROUPED / "label_mapping.json").read_text()))
    seen_ids = set()
    seen_texts = set()
    train_rows = []
    summary = {}

    for name, expected_per_class in [("train_pairs", 4), ("holdout_pairs", 2)]:
        path = SOURCE / f"{name}.csv"
        frame = pd.read_csv(path, keep_default_na=False)
        if frame["label"].value_counts().to_dict() != dict.fromkeys(labels, expected_per_class):
            raise ValueError(f"Distribuție incorectă în {name}")

        for row in frame.itertuples(index=False):
            if not row.scenario_id or row.scenario_id in seen_ids:
                raise ValueError(f"ID lipsă sau repetat: {row.scenario_id}")
            seen_ids.add(row.scenario_id)
            for lang in ["ro", "en"]:
                text = getattr(row, lang).strip()
                key = " ".join(text.casefold().split())
                if not key or key in seen_texts:
                    raise ValueError(f"Text gol sau repetat: {row.scenario_id}")
                seen_texts.add(key)
                if name == "train_pairs":
                    train_rows.append((row.scenario_id, lang, text, row.label))

        summary[name] = {
            "scenarios": len(frame),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    OUTPUT.mkdir(parents=True, exist_ok=True)
    train = pd.DataFrame(train_rows, columns=["scenario_id", "language", "text", "label"])
    train.to_csv(OUTPUT / "bilingual_train.csv", index=False)
    print(json.dumps(summary, indent=2))
    print(f"Train bilingv: {len(train)} texte")


if __name__ == "__main__":
    main()
