FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production

COPY . .

RUN pip install --upgrade pip \
    && pip install -e . \
    && mkdir -p /app/logs /app/output/static /home/app \
    && DJANGO_SETTINGS_MODULE=config.settings.local DJANGO_SECRET_KEY="build-time-placeholder-not-used-in-production-x1y2z3" python manage.py collectstatic --noinput \
    && addgroup --system app \
    && adduser --system --ingroup app --home /home/app app \
    && chown -R app:app /app /home/app

USER app

CMD ["sh", "scripts/start-railway.sh"]
