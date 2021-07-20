dev:
	poetry install
	poetry run pre-commit install

check:
	isort -c live_translation/
	isort -c scripts/
	isort -c tests/
	black --check live_translation/
	black --check scripts/
	black --check tests/
	flake8 live_translation/
	flake8 scripts/
	flake8 tests/

.PHONY: dev check
