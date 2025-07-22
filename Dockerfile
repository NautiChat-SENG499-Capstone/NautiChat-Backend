FROM python:3.12-slim
#sets hugging face cache directory
#prevents .pyc files from being created
#prevents python from buffering stdout/stderr
ENV HF_HOME=/opt/hf-cache \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libomp-dev \
    python3-dev \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

COPY ./backend-api ./backend-api
COPY ./LLM         ./LLM

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.main:app", "--app-dir", "backend-api", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]

