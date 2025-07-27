lint:
	poetry run ruff check --fix && \
		poetry run ruff format

dry_lint:
	poetry run ruff check && \
		poetry run ruff format --check

run_db:
	docker run --rm --name postgres-container \
		-e POSTGRES_USER=root \
		-e POSTGRES_PASSWORD=root \
		-e POSTGRES_DB=postgres \
		-v ./.pgdata:/var/lib/postgresql/data \
		-p 5432:5432 -d postgres

migrate_db:
	docker cp ./scripts/ddl.sql postgres-container:/tmp/ddl.sql && \
		docker exec -it postgres-container psql -U root -d postgres -f /tmp/ddl.sql

drop_db:
	docker cp ./scripts/drop_ddl.sql postgres-container:/tmp/drop_ddl.sql && \
		docker exec -it postgres-container psql -U root -d postgres -f /tmp/drop_ddl.sql

stop_db:
	docker stop postgres-container

run:
	poetry run chainlit run clinical_trials_assistant/main.py

test:
	poetry run pytest
