# Production image for Johanna's site.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# Dependencies first, so rebuilds are fast when only code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Everything that changes at runtime lives in /data (a Docker volume):
# the database, uploaded images and the private downloads.
RUN useradd --create-home wagtail \
 && mkdir -p /data /backups \
 && chown -R wagtail:wagtail /app /data /backups
USER wagtail

# Collect CSS/JS/fonts into /app/static (served by WhiteNoise).
RUN SECRET_KEY=build-only ALLOWED_HOSTS=localhost python manage.py collectstatic --noinput

VOLUME ["/data"]
EXPOSE 8000

# Migrate on start, then serve. Two workers is plenty for a small portfolio site.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 60 --access-logfile -"]
