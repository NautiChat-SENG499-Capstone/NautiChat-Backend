# Dockerfile for backend and llm

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./backend-api ./backend-api

CMD ["uvicorn", "backend-api.src.main:app", "--host", "0.0.0.0", "--port", "8000"]

