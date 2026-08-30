SHELL := /bin/bash
COMPOSE := docker compose
UV := uv --directory portal

.PHONY: help dev down test e2e lint fmt bootstrap provision kc-export caddy-image check-profiles staging-deploy prod-deploy

help:
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

.env:
	@echo "ERROR: .env not found. Copy .env.example to .env and fill in values (see PLAN.md §5)."; exit 1

dev: .env ## Local core stack
	$(COMPOSE) --profile core up -d

down: ## Stop local stack
	$(COMPOSE) --profile core --profile flows --profile lab --profile lora down

test: ## Portal unit + integration tests (integration skips unless local TB is up)
	@if [ -f .env ]; then set -a && . ./.env && set +a; fi; TB_ADMIN_URL=http://127.0.0.1:18080 $(UV) run pytest tests/unit tests/integration

e2e: .env ## End-to-end provisioning tests against local stack
	$(UV) run pytest tests/e2e

lint: ## ruff + mypy + compose config validation
	$(UV) run ruff check .
	$(UV) run ruff format --check .
	$(UV) run mypy app
	$(MAKE) check-profiles

fmt: ## Auto-format
	$(UV) run ruff format . && $(UV) run ruff check --fix .

bootstrap: .env ## Idempotent: Keycloak realm/clients + TB OAuth2 client/domain (M0.3)
	set -a && . ./.env && set +a && KC_ADMIN_URL=http://127.0.0.1:18081 TB_ADMIN_URL=http://127.0.0.1:18080 \
	  $(UV) run python -m scripts.setup_keycloak && \
	  set -a && . ./.env && set +a && KC_ADMIN_URL=http://127.0.0.1:18081 TB_ADMIN_URL=http://127.0.0.1:18080 \
	  $(UV) run python -m scripts.setup_tb_oauth2

provision: .env ## Provision/repair a student tenant: make provision EMAIL=x@y
	set -a && . ./.env && set +a && TB_ADMIN_URL=http://127.0.0.1:18080 $(UV) run python -m scripts.provision_student $(EMAIL) $(ARGS)

kc-export: .env ## Export the Keycloak realm to keycloak/realm/ (secrets masked)
	set -a && . ./.env && set +a && KC_ADMIN_URL=http://127.0.0.1:18081 KC_EXPORT_DIR=$(CURDIR)/keycloak/realm \
	  $(UV) run python -m scripts.export_keycloak

caddy-image: ## Build Caddy + layer4 image for staging/prod (D8). Needs ~4 GB RAM.
	docker build --build-arg CADDY_VERSION=$$(grep ^CADDY_VERSION= .env.example | cut -d= -f2) \
	  --build-arg CADDY_L4_VERSION=$$(grep ^CADDY_L4_VERSION= .env.example | cut -d= -f2) \
	  -t chertiot/caddy:$$(grep ^CADDY_VERSION= .env.example | cut -d= -f2)-l4 deploy/caddy

check-profiles: ## Validate compose file for every profile
	@for p in core flows lab lora; do $(COMPOSE) -f docker-compose.yml --env-file .env.example --profile $$p config -q || exit 1; done

staging-deploy: ## Deploy to staging (M2.2)
	@echo "not implemented until M2.2"; exit 1

prod-deploy: ## Deploy to production (M2.3)
	@echo "not implemented until M2.3"; exit 1
