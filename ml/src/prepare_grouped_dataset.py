import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "ml/data/processed"
OUTPUT_DIR = DATA_DIR / "grouped"
REPORT_DIR = ROOT / "ml/reports"

THRESHOLD = 0.95
BATCH_SIZE = 128
SEED = 42


def main():
    frames = {
        name: pd.read_csv(DATA_DIR / f"{name}.csv")
        for name in ["train", "validation", "test"]
    }

    df = pd.concat(frames.values(), ignore_index=True)

    if df["text_id"].duplicated().any():
        raise ValueError("Duplicate text IDs found.")

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=2,
        max_features=100_000,
        sublinear_tf=True,
    )

    vectorizer.fit(frames["train"]["text"])
    matrix = vectorizer.transform(df["text"])

    parents = np.arange(len(df))
    sizes = np.ones(len(df), dtype=int)

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(first, second):
        first = find(first)
        second = find(second)

        if first == second:
            return

        if sizes[first] < sizes[second]:
            first, second = second, first

        parents[second] = first
        sizes[first] += sizes[second]

    search = NearestNeighbors(
        metric="cosine",
        algorithm="brute",
        n_jobs=1,
    )
    search.fit(matrix)

    edge_count = 0

    for start in range(0, len(df), BATCH_SIZE):
        stop = min(start + BATCH_SIZE, len(df))

        distances, neighbors = search.radius_neighbors(
            matrix[start:stop],
            radius=1 - THRESHOLD + 1e-12,
            return_distance=True,
        )

        for offset, (row_distances, row_neighbors) in enumerate(
            zip(distances, neighbors)
        ):
            first = start + offset

            for distance, second in zip(row_distances, row_neighbors):
                second = int(second)

                if second > first and 1 - distance >= THRESHOLD:
                    union(first, second)
                    edge_count += 1

        if start == 0 or stop % 4096 == 0 or stop == len(df):
            print(f"Checked {stop:,}/{len(df):,} tickets", flush=True)

    roots = np.array([find(index) for index in range(len(df))])
    df["group_id"] = pd.factorize(roots)[0]

    splitter = StratifiedGroupKFold(
        n_splits=10,
        shuffle=True,
        random_state=SEED,
    )

    fold_ids = np.full(len(df), -1, dtype=int)

    for fold, (_, held_out) in enumerate(
        splitter.split(
            np.zeros(len(df)),
            df["label"],
            groups=df["group_id"],
        )
    ):
        fold_ids[held_out] = fold

    df["split"] = np.where(
        fold_ids == 0,
        "test",
        np.where(fold_ids == 1, "validation", "train"),
    )

    if df.groupby("group_id")["split"].nunique().max() != 1:
        raise ValueError("A similarity group crosses split boundaries.")

    all_labels = set(df["label"])
    splits = {
        name: df.loc[df["split"].eq(name)].copy()
        for name in ["train", "validation", "test"]
    }

    for name, frame in splits.items():
        if set(frame["label"]) != all_labels:
            raise ValueError(f"Missing categories in {name}.")

    group_sizes = df.groupby("group_id").size()
    group_label_counts = df.groupby("group_id")["label"].nunique()

    report = {
        "seed": SEED,
        "similarity_threshold": THRESHOLD,
        "grouping": "connected_components_word_tfidf_cosine",
        "grouping_vocabulary_fit": "original_train",
        "split_method": "stratified_group_10_folds",
        "fold_assignment": {
            "test": [0],
            "validation": [1],
            "train": list(range(2, 10)),
        },
        "rows": len(df),
        "similarity_edges": edge_count,
        "groups": len(group_sizes),
        "groups_with_multiple_rows": int((group_sizes > 1).sum()),
        "rows_in_multirow_groups": int(
            group_sizes[group_sizes > 1].sum()
        ),
        "largest_group": int(group_sizes.max()),
        "groups_with_multiple_labels": int(
            (group_label_counts > 1).sum()
        ),
        "largest_10_groups": {
            str(group): int(size)
            for group, size in group_sizes.nlargest(10).items()
        },
        "cross_split_group_overlap": False,
        "splits": {},
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    for name, frame in splits.items():
        path = OUTPUT_DIR / f"{name}.csv"
        frame.drop(columns="split").to_csv(path, index=False)

        report["splits"][name] = {
            "rows": len(frame),
            "percentage": round(100 * len(frame) / len(df), 2),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "class_counts": {
                str(label): int(count)
                for label, count in frame["label"].value_counts().items()
            },
        }

    df[["text_id", "group_id", "split"]].to_csv(
        OUTPUT_DIR / "split_manifest.csv",
        index=False,
    )

    labels = sorted(all_labels)
    (OUTPUT_DIR / "label_mapping.json").write_text(
        json.dumps(
            {label: index for index, label in enumerate(labels)},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    output = json.dumps(report, indent=2)
    (REPORT_DIR / "grouped_data_split.json").write_text(
        output + "\n",
        encoding="utf-8",
    )
    print("\n" + output)


if __name__ == "__main__":
    main()