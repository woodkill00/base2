# api/.Dockerfile
ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for runtime and ensure /app is writable
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

RUN mkdir -p /app/api

COPY requirements.txt ./api/requirements.txt
ENV PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN pip install --user --no-cache-dir -r api/requirements.txt

COPY . ./api

ENV PORT=8000
ENV PYTHONPATH=/app
# Use shell form to expand $PORT at runtime
CMD ["sh", "-lc", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
