# django/.Dockerfile
ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    bash \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=project.settings.production
# Default port; can be overridden by Compose via PORT=${DJANGO_PORT}
ENV PORT=8000

# Use $PORT so Traefik and Compose can control the binding
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
