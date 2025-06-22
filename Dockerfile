# ───── Dockerfile (backend) ───────────────────────────────────────────
FROM python:3.12-slim AS base

ENV HF_HOME=/opt/hf-cache \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

<<<<<<< HEAD
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git-lfs \
        curl \
        gcc \
        g++ \
        libomp-dev \
        python3-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

=======
>>>>>>> origin/main
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

# Copy application code first
COPY ./backend-api ./backend-api
COPY ./LLM         ./LLM

<<<<<<< HEAD
ENV PYTHONPATH=/app
EXPOSE 8080

# Add health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "src.main:app", "--app-dir", "backend-api", "--host", "0.0.0.0", "--port", "8080", "--log-level", "debug"]

=======
CMD ["uvicorn", "src.main:app", "--app-dir", "backend-api", "--host", "0.0.0.0", "--port", "8080"]
>>>>>>> origin/main
