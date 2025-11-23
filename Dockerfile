# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install PostgreSQL client libraries
RUN apt-get update && apt-get install -y \
    libpq-dev gcc && \
    apt-get clean

# Create non-root user
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/usr/sbin/nologin" \
    --uid "${UID}" \
    appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create logs folder
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host=0.0.0.0", "--port=8000"]
