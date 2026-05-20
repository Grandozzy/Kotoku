FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=config.settings.production

COPY . .

RUN pip install --upgrade pip && pip install -e . && mkdir -p /app/logs

CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
