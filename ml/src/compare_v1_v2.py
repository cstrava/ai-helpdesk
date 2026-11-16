from pathlib import Path

import pandas as pd
import torch
from sklearn.metrics import f1_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "ml/models"
pairs = pd.read_csv(ROOT / "ml/evaluation/v2/holdout_pairs.csv")

results = pairs.melt(
    id_vars=["scenario_id", "label"],
    value_vars=["ro", "en"],
    var_name="language",
    value_name="text",
)

paths = {
    "v1": MODELS / "xlm_roberta_helpdesk_v1/best_model",
    "v2": MODELS / "xlm_roberta_helpdesk_v2/model",
}

for name, path in paths.items():
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(
        path, local_files_only=True
    )
    model.eval()
    predictions = []

    with torch.inference_mode():
        for start in range(0, len(results), 8):
            batch = results["text"].iloc[start:start + 8].tolist()
            inputs = tokenizer(
                batch, padding=True, truncation=True,
                max_length=256, return_tensors="pt",
            )
            ids = model(**inputs).logits.argmax(dim=-1).tolist()
            predictions.extend(model.config.id2label[i] for i in ids)

    results[name] = predictions
    del model

for language, group in results.groupby("language", sort=False):
    for name in paths:
        correct = group[name].eq(group["label"]).sum()
        score = f1_score(group["label"], group[name], average="macro", zero_division=0)
        print(f"{language.upper()} {name}: {correct}/{len(group)} | macro-F1={score:.4f}")

output = ROOT / "ml/reports/v1_v2_bilingual_holdout.csv"
output.parent.mkdir(parents=True, exist_ok=True)
results.to_csv(output, index=False)