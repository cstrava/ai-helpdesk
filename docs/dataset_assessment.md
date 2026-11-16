# Dataset assessment

## Source and initial checks

The initial corpus is the [IT Service Ticket Classification Dataset](https://www.kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset). The tracked [source audit](../ml/reports/it_service_audit.json) records 47,837 rows across eight categories and the source's displayed license, CC0: Public Domain. This is recorded provenance, not a new license review.

The audit found no empty texts or labels, no duplicate texts after case and whitespace normalization, and no identical normalized texts with conflicting labels. Those checks do not rule out near-duplicates or labeling errors. The audit retained the source CSV unchanged.

## Historical baseline and leakage checks

The first TF-IDF + Linear SVM baseline used a stratified random 80/10/10 split with seed 42. On its 4,784-row validation partition, [the report](../ml/reports/baseline_validation.json) records accuracy 0.8622 and macro-F1 0.8615. These are historical random-split results, distinct from the grouped baseline in the [current model comparison](ML_EVALUATION.md).

A subsequent [nearest-neighbor audit](../ml/reports/near_duplicate_audit.json) found 138 validation rows with word TF-IDF cosine similarity of at least 0.95 to training rows, and 116 test rows at that threshold against training. Similarity indicates possible template leakage; it does not by itself prove identical incidents.

The later [grouped split](../ml/reports/grouped_data_split.json) keeps connected components at similarity threshold 0.95 together, using stratified group folds with seed 42. It records 46,848 groups and no cross-split group overlap. This reduces leakage under that similarity rule; it does not establish that all semantically related tickets are isolated.

## Recorded manual review

The initial review sampled ten training examples from each of Administrative rights, Access and Hardware. It recorded these observations:

- Texts appeared heavily preprocessed and sometimes lacked essential context.
- Administrative rights included installation and update requests without explicit references to elevated permissions.
- Access included physical access cards, licenses and administrative accounts.
- Hardware included some application, reporting and access issues.

The original routing rules are unknown. These observations suggest a mismatch with the proposed application taxonomy, rather than proving that the original labels are wrong. The small review does not establish a dataset-wide label error rate.

## Interpretation and subsequent work

The initial assessment recommended retaining the dataset as an experiment and pausing fine-tuning while reviewing alternatives. That was a historical recommendation: the repository now includes evaluation artifacts for XLM-R v1 and a local bilingual v2 adaptation. Their results and reproducibility limits are documented in [ML evaluation](ML_EVALUATION.md).

Dataset scores measure agreement with source labels, not verified performance on natural user tickets or Romanian text. Future dataset selection should review category definitions, text quality, provenance and usage terms. Validation and test labels should not be changed merely because a model predicts something different.
