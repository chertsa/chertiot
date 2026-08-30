SHELL := /bin/bash
COMPOSE := docker compose
UV := uv --directory portal

.PHONY: help dev down test e2e lint fmt check-profiles staging-deploy prod-deploy

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

.env:
	@echo "ERROR: .env not found. Copy .env.example to .env and fill in values (see PLAN.md §5)."; exit 1

dev: .env ## Local core stack
	$(COMPOSE) --profile core up -d

down: ## Stop local stack
	$(COMPOSE) --profile core --profile flows --profile lab --profile lora down

test: ## Portal unit + integration tests
	$(UV) run pytest tests/unit tests/integration

e2e: .env ## End-to-end provisioning tests against local stack
	$(UV) run pytest tests/e2e

lint: ## ruff + mypy + compose config validation
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy app
	$(MAKE) check-profiles

fmt: ## Auto-format
	$(UV) run ruff format . && $(UV) run ruff check --fix .

check-profiles: ## Validate compose file for every profile
	@for p in core flows lab lora; do $(COMPOSE) --env-file .env.example --profile $$p config -q || exit 1; done

staging-deploy: ## Deploy to staging (M2.2)
	@echo "not implemented until M2.2"; exit 1

prod-deploy: ## Deploy to production (M2.3)
	@echo "not implemented until M2.3"; exit 1
