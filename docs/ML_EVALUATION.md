# Classification model evaluation

## Scope and reproducibility

The application uses the local XLM-RoBERTa v2 classifier. The tracked results compare that artifact with v1 and a TF-IDF + Linear SVM baseline. Qwen generates conversation replies and ticket drafts; it is not evaluated by these classification metrics.

Model artifacts and datasets are local and are not committed. A fresh checkout alone cannot reproduce inference. With the required artifacts available, install the evaluation dependencies in a dedicated environment and run from the repository root:

```bash
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.11.0+cpu
python -m pip install -r ml/requirements.evaluation.txt
python ml/src/reproduce_evaluation.py
```

The script expects:

- `ml/models/grouped/baseline_svm.joblib`;
- v1 at `ml/models/xlm_roberta_helpdesk_v1/best_model/` and v2 at `ml/models/xlm_roberta_helpdesk_v2/model/`, including tokenizer files, configuration and `model.safetensors`;
- grouped `train.csv` and `validation.csv` under `ml/data/processed/grouped/`;
- `train_pairs.csv` and `holdout_pairs.csv` under `ml/evaluation/v2/`;
- `ml/data/processed/v2/train_mixed.csv`.

It checks grouped train/validation hashes against the tracked split manifest and rejects overlapping bilingual train/holdout scenario IDs. Each bilingual row contains both translations, keeping the RO/EN pair in the same scenario group. It runs inference without training or changing datasets, then overwrites [the evaluation report](../ml/reports/reproducible_v1_v2_baseline.json). The report contains no ticket texts: it records artifact/data hashes, library versions, split provenance, accuracy, macro-F1, per-class metrics and confusion matrices. The script selects CUDA when available and otherwise CPU; the tracked run used CPU.

The complete v2 trainer and training configuration are not versioned. Artifact hashes identify the evaluated weights and inputs, but do not make v2 training reproducible. Seed 42 identifies the grouped split and evaluation seed; it is not evidence of the v2 training seed.

## Models and datasets

| Item | Meaning |
|---|---|
| Baseline | TF-IDF + Linear SVM trained on the original English corpus using the grouped split |
| v1 | Earlier local XLM-RoBERTa classifier |
| v2 | Local bilingual adaptation used by the application |
| Grouped English validation | 4,784 rows from the English corpus, grouped by connected components of word TF-IDF cosine similarity at threshold 0.95 and split with seed 42 |
| Bilingual pilot holdout | 16 synthetic scenarios, each with paired Romanian and English text; reported separately by language |

The grouped English validation split was included as validation data in the archive prepared for v2. Its v2 score is a validation comparison, not an independent holdout result. The script does not evaluate v2 on `grouped/test.csv`.

The pilot is too small to estimate performance on real incidents. The 32 translated texts represent 16 paired scenarios, not 32 independent observations. Do not combine pilot scores with grouped-corpus scores.

## Recorded results

These values come from the tracked inference report; they were not rerun as part of the documentation revision.

| Dataset and language | Model | Accuracy | Macro-F1 |
|---|---|---:|---:|
| Grouped EN validation (n=4,784) | Baseline SVM | 0.8612 | 0.8560 |
| Grouped EN validation (n=4,784) | XLM-R v1 | 0.8798 | 0.8782 |
| Grouped EN validation (n=4,784) | XLM-R v2 | 0.8142 | 0.8024 |
| RO pilot (16 scenarios) | Baseline SVM | 0.1250 | 0.0333 |
| RO pilot (16 scenarios) | XLM-R v1 | 0.1875 | 0.0982 |
| RO pilot (16 scenarios) | XLM-R v2 | 0.5625 | 0.5292 |
| EN pilot (same 16 scenarios) | Baseline SVM | 0.3125 | 0.2579 |
| EN pilot (same 16 scenarios) | XLM-R v1 | 0.2500 | 0.2121 |
| EN pilot (same 16 scenarios) | XLM-R v2 | 0.6250 | 0.5750 |

On the pilot, v2 accuracy exceeds v1 by 37.5 percentage points in each language. On grouped English validation, v2 loses 6.56 percentage points of accuracy and 7.58 points of macro-F1 relative to v1. The improvement on a small synthetic pilot therefore comes with an observed English regression; it does not establish that v2 is generally better.

## Historical reports

- [Grouped test comparison](../ml/reports/grouped/test_comparison.json): baseline SVM versus XLM-R v1 on grouped English test data. It contains no v2 result.
- [Romanian v1 evaluation](../ml/reports/ro_evaluation_v1.json): a separate small manually authored Romanian set, distinct from the bilingual pilot and grouped validation.
- [Initial baseline validation](../ml/reports/baseline_validation.json): the earlier random split, distinct from the grouped baseline used above. See [dataset assessment](dataset_assessment.md).

Read every metric with its model version, split and data hash. Keep holdout examples fixed rather than editing them in response to errors. These metrics measure category agreement; they do not validate priority assignment, incident resolution or autonomous ticket handling.

## Limitations and next steps

The classifier truncates inputs to 256 tokens and returns a category without calibrated confidence or reliable out-of-domain detection. Dataset labels reflect the source taxonomy, whose routing rules are unknown. Support can correct categories and explicitly review labels for export, but an exported review is not automatically suitable training data.

A stronger evaluation needs a documented training configuration, an independent English holdout for v2, and a larger scenario-separated bilingual set with reviewed provenance and labels. Any real ticket data would also need appropriate permission and anonymization before reuse. No retraining or model replacement is performed by the application feedback workflow.
