.PHONY: install bootstrap dev migrate makemigrations test lint format worker beat shell clean-pyc

install:
	pip install -e .[dev]

bootstrap:
	./scripts/bootstrap.sh

dev:
	./scripts/run_dev.sh

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

shell:
	python manage.py shell

test:
	pytest

lint:
	ruff check .

format:
	ruff check . --fix

worker:
	celery -A config worker -l info

beat:
	celery -A config beat -l info

clean-pyc:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
