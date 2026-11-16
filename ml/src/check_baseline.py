from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "ml/data/processed"
MODEL_PATH = ROOT / "ml/models/baseline_svm.joblib"
MATRIX_PATH = ROOT / "ml/reports/baseline_confusion_matrix.csv"


def show_confusions():
    matrix = pd.read_csv(MATRIX_PATH, index_col=0)

    confusions = []
    for actual in matrix.index:
        for predicted in matrix.columns:
            count = int(matrix.loc[actual, predicted])
            if actual != predicted and count > 0:
                confusions.append((count, actual, predicted))

    confusions.sort(reverse=True)

    print("\n--- TOP 10 CONFUSIONS ---")
    print("Actual category -> Predicted category: number of errors")

    for count, actual, predicted in confusions[:10]:
        print(f"{actual} -> {predicted}: {count}")

    print("\n--- ERROR RATE BY CATEGORY ---")
    rates = []

    for category in matrix.index:
        total = int(matrix.loc[category].sum())
        correct = int(matrix.loc[category, category])
        rate = (total - correct) / total if total else 0
        rates.append((rate, category))

    for rate, category in sorted(rates, reverse=True):
        print(f"{category}: {rate:.1%}")


def show_error_examples():
    errors = pd.read_csv(DATA_DIR / "baseline_validation_errors.csv")

    print("\n--- VALIDATION ERROR EXAMPLES ---")

    for category, group in errors.groupby("label", sort=True):
        row = group.sample(n=1, random_state=42).iloc[0]

        print(f"\nActual: {category}")
        print(f"Predicted: {row['prediction']}")
        print(f"Text: {row['text'][:600]}")


def interactive_predictions():
    model = joblib.load(MODEL_PATH)

    print("\n--- TRY YOUR OWN TICKETS ---")
    print("Write an English ticket, then press Enter.")
    print("Type /exit to stop.")
    print("SVM scores are decision scores, NOT probabilities.")

    while True:
        try:
            text = input("\nTicket: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped.")
            break

        if text.lower() == "/exit":
            break

        if not text:
            continue

        features = model.named_steps["tfidf"].transform([text])

        if features.nnz == 0:
            print("No known vocabulary found. Prediction would be unreliable.")
            continue

        scores = model.decision_function([text])[0]
        classes = model.named_steps["classifier"].classes_
        ranked = sorted(
            zip(classes, scores),
            key=lambda item: item[1],
            reverse=True,
        )

        print(f"Predicted category: {ranked[0][0]}")
        print("Top 3 decision scores:")

        for category, score in ranked[:3]:
            print(f"  {category}: {score:.3f}")


def main():
    show_confusions()
    show_error_examples()
    interactive_predictions()


if __name__ == "__main__":
    main()