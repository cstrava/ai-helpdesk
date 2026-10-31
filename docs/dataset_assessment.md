# Initial Dataset Assessment

## Dataset

- Source: https://www.kaggle.com/datasets/adisongoh/it-service-ticket-classification-dataset
- License displayed by source: CC0: Public Domain
- Records: 47,837
- Categories: 8

## Automated checks

- No missing texts or labels.
- No exact duplicate texts after case and whitespace normalization.
- No identical normalized texts with conflicting labels.
- Near-duplicates have not been checked.

## Baseline

TF-IDF + Linear SVM, evaluated on the validation partition:

- Accuracy: 0.8622
- Macro-F1: 0.8615

These results measure agreement with the dataset labels, not verified
performance on natural user tickets or Romanian text.

## Manual review

Reviewed 10 training examples from each of three categories:
Administrative rights, Access, and Hardware.

Observed issues:

- Texts appear heavily preprocessed and sometimes lack essential context.
- Administrative rights contains installation and update requests without
  explicit references to elevated permissions.
- Access includes physical access cards, licenses, and administrative accounts.
- Hardware includes several application, reporting, and access issues.

The original routing rules are unknown. These observations indicate a
mismatch with our proposed application taxonomy, not proof that all
original labels are incorrect.

The small review sample does not establish a dataset-wide label error rate.

## Decision

Retain this dataset and baseline as an initial experiment.
Pause fine-tuning on these labels.

Evaluate alternative datasets with documented categories, natural ticket
text, clear provenance, and suitable usage terms before selecting the
application's final taxonomy.

Do not manually relabel validation or test examples based on model errors.