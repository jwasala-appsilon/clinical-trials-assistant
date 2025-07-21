lint:
	poetry run ruff check --fix && \
		poetry run ruff format

dry_lint:
	poetry run ruff check && \
		poetry run ruff format --check

run:
	poetry run streamlit run clinical_trials_assistant/main.py

test:
	poetry run pytest
