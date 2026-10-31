import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "ml/data/processed"
REPORT_DIR = ROOT / "ml/reports"
BATCH_SIZE = 128
THRESHOLD = 0.95


def nearest_matches(search, matrix):
    scores = []
    indices = []

    for start in range(0, matrix.shape[0], BATCH_SIZE):
        batch = matrix[start:start + BATCH_SIZE]
        distances, neighbors = search.kneighbors(batch)
        scores.extend(np.clip(1 - distances[:, 0], 0, 1).tolist())
        indices.extend(neighbors[:, 0].tolist())

    return np.asarray(scores), np.asarray(indices)


def main():
    frames = {
        name: pd.read_csv(DATA_DIR / f"{name}.csv")
        for name in ["train", "validation", "test"]
    }

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        min_df=2,
        max_features=100_000,
        sublinear_tf=True,
    )

    matrices = {
        "train": vectorizer.fit_transform(frames["train"]["text"])
    }

    for name in ["validation", "test"]:
        matrices[name] = vectorizer.transform(frames[name]["text"])

    report = {
        "method": "nearest_neighbor_word_tfidf_cosine",
        "vocabulary_fit_split": "train",
        "review_threshold": THRESHOLD,
        "comparisons": {},
    }

    validation_matches = None

    for reference, query in [
        ("train", "validation"),
        ("train", "test"),
        ("validation", "test"),
    ]:
        print(f"Checking {query} against {reference}...", flush=True)

        search = NearestNeighbors(
            n_neighbors=1,
            metric="cosine",
            algorithm="brute",
            n_jobs=1,
        )
        search.fit(matrices[reference])

        scores, indices = nearest_matches(search, matrices[query])

        summary = {
            "query_rows": len(scores),
            "zero_vector_rows": int(
                (matrices[query].getnnz(axis=1) == 0).sum()
            ),
            "maximum_similarity": float(scores.max()),
            "rows_at_or_above": {
                str(threshold): int((scores >= threshold).sum())
                for threshold in [0.90, 0.95, 0.99]
            },
        }

        report["comparisons"][f"{query}_against_{reference}"] = summary

        if reference == "train" and query == "validation":
            validation_matches = (scores, indices)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output = json.dumps(report, indent=2)
    (REPORT_DIR / "near_duplicate_audit.json").write_text(
        output + "\n",
        encoding="utf-8",
    )
    print("\n" + output)

    scores, indices = validation_matches
    candidates = np.flatnonzero(scores >= THRESHOLD)
    candidates = candidates[np.argsort(-scores[candidates])]

    pairs = []
    for index in candidates:
        train_row = frames["train"].iloc[int(indices[index])]
        validation_row = frames["validation"].iloc[int(index)]

        pairs.append({
            "similarity": float(scores[index]),
            "train_id": train_row["text_id"],
            "validation_id": validation_row["text_id"],
            "train_text": train_row["text"],
            "validation_text": validation_row["text"],
        })

    pd.DataFrame(
        pairs,
        columns=[
            "similarity",
            "train_id",
            "validation_id",
            "train_text",
            "validation_text",
        ],
    ).to_csv(DATA_DIR / "near_duplicate_review.csv", index=False)

    print("\n--- TOP VALIDATION CANDIDATES ---")
    for pair in pairs[:5]:
        print(f"\nSimilarity: {pair['similarity']:.4f}")
        print("TRAIN:", pair["train_text"][:500])
        print("VALIDATION:", pair["validation_text"][:500])

    if not pairs:
        print("No pairs reached the review threshold.")


if __name__ == "__main__":
    main()