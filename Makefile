lint:
	poetry run ruff check --fix && \
		poetry run ruff format

dry_lint:
	poetry run ruff check && \
		poetry run ruff format --check

run:
	poetry run chainlit run clinical_trials_assistant/main.py

preview:
	poetry run uvicorn clinical_trials_assistant.main:app --host 0.0.0.0 --port 80

test:
	poetry run pytest
