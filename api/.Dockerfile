# api/.Dockerfile
ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for runtime and ensure /app is writable
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

RUN mkdir -p /app/api

COPY --chown=appuser:appuser requirements.txt ./api/requirements.txt
ENV PATH="/home/appuser/.local/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN pip install --user --no-cache-dir -r api/requirements.txt

COPY --chown=appuser:appuser . ./api

RUN sed -i 's/\r$//' /app/api/entrypoint.sh && chmod +x /app/api/entrypoint.sh

ENV PORT=8000
ENV PYTHONPATH=/app
CMD ["/app/api/entrypoint.sh"]
