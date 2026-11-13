import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
GROUPED = ROOT / "ml/data/processed/grouped"
V2 = ROOT / "ml/data/processed/v2"
SEED = 42


def main():
    split_report = json.loads(
        (ROOT / "ml/reports/grouped_data_split.json").read_text()
    )

    for split in ["train", "validation"]:
        path = GROUPED / f"{split}.csv"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != split_report["splits"][split]["sha256"]:
            raise ValueError(f"Fișierul {split}.csv diferă de cel folosit la v1.")

    original = pd.read_csv(GROUPED / "train.csv")
    bilingual = pd.read_csv(V2 / "bilingual_train.csv")

    replay = pd.concat(
        [
            group.sample(n=32, random_state=SEED)
            for _, group in original.groupby("label", sort=True)
        ],
        ignore_index=True,
    )

    replay = replay[["text_id", "text", "label"]].rename(
        columns={"text_id": "source_id"}
    )
    replay["source"] = "original_train"

    pilot = bilingual[["scenario_id", "language", "text", "label"]].copy()
    pilot["source_id"] = pilot["scenario_id"] + "_" + pilot["language"]
    pilot["source"] = "bilingual_" + pilot["language"]

    columns = ["source_id", "source", "text", "label"]
    mixed = pd.concat([replay[columns], pilot[columns]], ignore_index=True)
    mixed = mixed.sample(frac=1, random_state=SEED).reset_index(drop=True)

    label_mapping = json.loads((GROUPED / "label_mapping.json").read_text())
    if mixed["label"].value_counts().to_dict() != dict.fromkeys(label_mapping, 40):
        raise ValueError("Distribuția așteptată este de 40 de texte pe categorie.")

    train_path = V2 / "train_mixed.csv"
    mixed.to_csv(train_path, index=False)

    archive = V2 / "helpdesk_v2_training_data.zip"
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        bundle.write(train_path, "train_mixed.csv")
        bundle.write(GROUPED / "validation.csv", "validation.csv")
        bundle.write(GROUPED / "label_mapping.json", "label_mapping.json")

    print(mixed["source"].value_counts().to_string())
    print(f"Total train: {len(mixed)}")
    print(f"Arhivă: {archive}")


if __name__ == "__main__":
    main()