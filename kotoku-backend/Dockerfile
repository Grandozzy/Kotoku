FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . .

RUN pip install --upgrade pip && pip install -e .[dev]

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
