import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

from evaluate_test import predict_xlm

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "ml/reports"

english = {
    "ro01": "I changed my phone and the authentication codes still go to the old one. How can I get back into the portal?",
    "ro02": "My account was locked after several attempts. Could you unlock it?",
    "ro03": "I forgot my intranet password and the reset link has expired.",
    "ro04": "I can log into my laptop, but installing the driver asks for an administrator password. I need approval to install it.",
    "ro05": "I need to restart a service on the test server. Could you grant me temporary sudo privileges?",
    "ro06": "I can access the application as a regular user and need to manage my colleagues' roles. Who can grant me that permission?",
    "ro07": "I changed my address and would like it updated in my personnel file.",
    "ro08": "Two approved vacation days are missing from my timesheet. Can you help correct it?",
    "ro09": "A colleague's contract ends on Friday. Where do I send the departure form?",
    "ro10": "My laptop shuts down as soon as I unplug the charger, even though the battery shows 80%.",
    "ro11": "The Enter key on my office keyboard is physically stuck.",
    "ro12": "My monitor flickers even with a different cable. Can you check the equipment?",
    "ro13": "We need a code for the new phase of the internal Atlas project. Could you add it to the project record?",
    "ro14": "The internal Orion project plan still lists the previous person in charge. Please update the owner of the testing phase.",
    "ro15": "An extension was approved for the internal Delta project. Please update the end date in the project register.",
    "ro16": "The internal phone directory lists the old extension for reception. Where should I send the correction?",
    "ro17": "The cafeteria menu link on the intranet opens last week's schedule.",
    "ro18": "The recurring invitation for the general meeting lists two different rooms. Could you correct the location?",
    "ro19": "My manager approved two new monitors. Where do I submit the purchase request?",
    "ro20": "Please tell me the status of the order for the docking station requested last week.",
    "ro21": "We have the supplier's quote for ten headsets. Can you help us place the order?",
    "ro22": "Our team's shared folder has reached its storage limit. We need another 50 GB.",
    "ro23": "I accidentally deleted a directory on the shared drive. Can it be restored from last night's backup?",
    "ro24": "The archive volume has no room left for log files. Can you increase its capacity?",
}

report = json.loads((REPORT_DIR / "ro_evaluation_v1.json").read_text())
pairs = pd.DataFrame(report["predictions"]).rename(columns={"prediction": "pred_ro"})

if not pairs["id"].is_unique or set(pairs["id"]) != set(english):
    raise ValueError("ID-urile traducerilor nu corespund raportului RO.")

pairs["text_en"] = pairs["id"].map(english)
pairs["pred_en"] = predict_xlm(pairs["text_en"].tolist())

for lang in ["ro", "en"]:
    predicted = pairs[f"pred_{lang}"]
    accuracy = accuracy_score(pairs["label"], predicted)
    macro_f1 = f1_score(pairs["label"], predicted, average="macro", zero_division=0)
    print(f"{lang.upper()}: accuracy={accuracy:.4f} | macro-F1={macro_f1:.4f}")

ro_ok = pairs["pred_ro"].eq(pairs["label"])
en_ok = pairs["pred_en"].eq(pairs["label"])

print("Corecte în ambele:", int((ro_ok & en_ok).sum()))
print("Corecte doar în EN:", int((~ro_ok & en_ok).sum()))
print("Corecte doar în RO:", int((ro_ok & ~en_ok).sum()))
print("Greșite în ambele:", int((~ro_ok & ~en_ok).sum()))

pairs.to_csv(REPORT_DIR / "ro_en_paired_v1.csv", index=False)