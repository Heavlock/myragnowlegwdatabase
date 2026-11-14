.DEFAULT_GOAL := help

PROFILE ?= postgres
LOG_TAIL ?= 100
FOLLOW ?= false
COMPOSE = docker compose --profile "$(PROFILE)"

ifeq ($(filter $(PROFILE),postgres qdrant),)
$(error PROFILE must be postgres or qdrant)
endif

.PHONY: hardware compute compute-test skills-test docs-check help model-check model-download build config up down status logs test smoke-test smoke-test-all migrate migration-generate migration-pull

help: ## Show available commands (default target)
	@awk 'BEGIN {FS = ":.*## "} /^[a-z-]+:.*## / {printf "%-22s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

hardware: ## Inspect CPU, RAM, GPU vendors/drivers and candidate inference backends
	python3 scripts/machine_info.py

compute: ## Persist CPU/GPU choice: make compute MODE=cpu or MODE=gpu
	python3 scripts/configure_compute.py --mode "$(MODE)"

compute-test: ## Verify CPU/CUDA embeddings and retrieval in disposable PostgreSQL stacks
	python3 -m unittest discover -s scripts -p test_compute_config.py
	python3 scripts/test_compute.py

model-check: ## Check the local GGUF file; never downloads it
	./scripts/check_embedding_model.sh

model-download: ## Download the pinned Qwen GGUF and verify its SHA-256
	./scripts/download_embedding_model.sh

build: ## Compile the Go packages without writing binaries into the repository
	go build ./...

config: ## Validate the selected Compose profile
	$(COMPOSE) config --quiet

up: model-check config ## Build and start a profile; wait for database/model health
	$(COMPOSE) up -d --build --wait

down: ## Stop both profiles; preserve database volumes
	docker compose --profile postgres --profile qdrant down

status: ## Show containers for the selected profile
	$(COMPOSE) ps

logs: ## Show recent logs; use FOLLOW=true to stream until Ctrl-C
	$(COMPOSE) logs --tail "$(LOG_TAIL)" --follow="$(FOLLOW)"

test: ## Run Go unit and real database integration tests (Docker required)
	go test ./...

smoke-test: model-check ## Test HTTP/MCP/UI and persistence in an isolated profile
	./scripts/docker_compose_smoke_test.sh "$(PROFILE)"

smoke-test-all: model-check ## Run isolated smoke tests for both database profiles
	$(MAKE) smoke-test PROFILE=postgres
	$(MAKE) smoke-test PROFILE=qdrant

migrate: ## Apply sql/project to PostgreSQL using pgCodeKeeper
	@test "$(PROFILE)" = postgres || { echo 'SQL migrations require PROFILE=postgres' >&2; exit 2; }
	./migration.sh

migration-generate: ## Generate a PostgreSQL schema diff without applying it
	@test "$(PROFILE)" = postgres || { echo 'SQL migrations require PROFILE=postgres' >&2; exit 2; }
	./migration_generate.sh

migration-pull: ## Replace the local schema project with the PostgreSQL schema
	@test "$(PROFILE)" = postgres || { echo 'SQL migrations require PROFILE=postgres' >&2; exit 2; }
	./migration_pull.sh

docs-check: ## Validate documentation links and shell examples
	python3 scripts/check_docs.py

skills-test: ## Verify save/update/search contracts in disposable database profiles
	python3 scripts/test_knowledge_contracts.py
