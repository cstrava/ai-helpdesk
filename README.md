cat > README.md <<'EOF'
# AI Help Desk

A bilingual IT support application for managing and automatically
classifying support tickets in Romanian and English.

## Project status

Initial setup. Model training and application development are planned.

## Goals

- Compare a TF-IDF + SVM baseline with a fine-tuned multilingual model.
- Evaluate classification performance separately for Romanian and English.
- Run model inference locally.
- Manage ticket status and collect corrections to model predictions.
- Record the model version used for each prediction.
- Deliver a tested application with Docker, CI, and local Kubernetes deployment.

## Planned stack

- Frontend: React
- Backend: Python, FastAPI
- Database: PostgreSQL
- Machine learning: scikit-learn, PyTorch, Hugging Face
- Delivery: Docker Compose, GitHub Actions, Kubernetes

## Repository structure

- backend/ — API and application logic
- frontend/ — user interface
- ml/ — data preparation, training, and evaluation
- infra/ — deployment configuration
- docs/ — architecture and project documentation

## Development principles

Dataset selection includes license and label-quality checks.
Training, validation, and test data remain separate.
Reported metrics must come from reproducible experiments.
Secrets, datasets, and trained model files are excluded from Git.
EOF

touch backend/app/.gitkeep frontend/.gitkeep
touch ml/notebooks/.gitkeep ml/src/.gitkeep ml/reports/.gitkeep
touch infra/k8s/.gitkeep docs/.gitkeep .github/workflows/.gitkeep
