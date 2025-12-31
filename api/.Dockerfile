# api/.Dockerfile
ARG PYTHON_VERSION=3.12-slim-bookworm
FROM python:${PYTHON_VERSION}

WORKDIR /app

# Keep base OS packages updated and minimize image size
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
       bash build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for runtime and ensure /app is writable
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

RUN mkdir -p /app/api

# Upgrade pip to address known advisories
RUN python -m pip install --user --upgrade pip

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
