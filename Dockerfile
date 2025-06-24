FROM python:3.12-slim
#sets hugging face cache directory
#prevents .pyc files from being created
#prevents python from buffering stdout/stderr
ENV HF_HOME=/opt/hf-cache \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

COPY ./backend-api ./backend-api
COPY ./LLM         ./LLM

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.main:app", "--app-dir", "backend-api", "--host", "0.0.0.0", "--port", "8080", "--log-level", "info"]

