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
# Run migrations, collect static assets into STATIC_ROOT, ensure a superuser (if env vars provided), then start Gunicorn.
CMD ["sh", "-lc", "python manage.py makemigrations && python manage.py migrate --noinput && python manage.py collectstatic --noinput && python -m project.create_superuser || true && gunicorn project.wsgi:application --bind 0.0.0.0:${PORT} --workers 3 --access-logfile - --error-logfile -"]
