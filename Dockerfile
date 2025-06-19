# ───── Dockerfile (backend) ───────────────────────────────────────────
FROM python:3.12-slim AS base

ENV HF_HOME=/opt/hf-cache \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential git-lfs && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=1000 -r requirements.txt

RUN --mount=type=cache,target=${HF_HOME} \          
    huggingface-cli download jinaai/jina-embeddings-v3 \
         --revision main \
         --repo-type model \
         --local-dir ${HF_HOME}/jina-embeddings-v3 \
         --resume-download --quiet \
 && huggingface-cli download jinaai/xlm-roberta-flash-implementation \
         --revision 3830381a980542ad592bcf3cc6c8d8cda25947fb \
         --repo-type model \
         --local-dir ${HF_HOME}/xlm-roberta-flash-implementation \
         --resume-download --quiet

COPY ./backend-api ./backend-api
COPY ./LLM         ./LLM
ENV PYTHONPATH=/app
EXPOSE 8080
CMD ["uvicorn", "src.main:app", "--app-dir", "backend-api", "--host", "0.0.0.0", "--port", "8080", "--log-level", "debug"]
