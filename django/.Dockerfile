# django/.Dockerfile
ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION}

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DJANGO_SETTINGS_MODULE=project.settings.production
# Default port; can be overridden by Compose via PORT=${DJANGO_PORT}
ENV PORT=8000

# Use $PORT so Traefik and Compose can control the binding
CMD ["sh", "-lc", "gunicorn project.wsgi:application --bind 0.0.0.0:${PORT} --workers 3"]
