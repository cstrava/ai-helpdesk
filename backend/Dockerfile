FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HUB_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

COPY backend/requirements.runtime.txt backend/requirements.lock.txt /tmp/

RUN python -m pip install --no-cache-dir \
        torch==2.11.0+cpu \
        --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir \
        -r /tmp/requirements.runtime.txt \
        -c /tmp/requirements.lock.txt

RUN useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser backend/app /app/backend/app

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]