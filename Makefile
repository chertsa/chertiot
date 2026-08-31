SHELL := /bin/bash
COMPOSE := docker compose
UV := uv --directory portal

.PHONY: help dev down test e2e platform-test flood-test wait-healthy lint fmt bootstrap provision migrate class-code kc-export caddy-image check-profiles staging-deploy prod-deploy

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

e2e: .env ## End-to-end tests against the local stack (signup, SSO, devices)
	@set -a && . ./.env && set +a; $(UV) run pytest tests/e2e

platform-test: .env ## Tenancy isolation tests against the local stack
	@set -a && . ./.env && set +a; TB_ADMIN_URL=http://127.0.0.1:18080 $(UV) run pytest $(CURDIR)/tests-platform -q

flood-test: .env ## Flood / rate-limit test (~1 min, nightly)
	@set -a && . ./.env && set +a; TB_ADMIN_URL=http://127.0.0.1:18080 $(UV) run pytest $(CURDIR)/tests-platform -q -m flood -s

wait-healthy: ## Block until TB, Keycloak and portal report healthy
	@for i in $$(seq 1 60); do S=$$(docker compose --profile core ps --format '{{.Service}} {{.Status}}'); echo "$$S" | grep -q '^tb .*(healthy)' && echo "$$S" | grep -q '^keycloak .*(healthy)' && echo "$$S" | grep -q '^portal .*(healthy)' && exit 0; sleep 10; done; docker compose --profile core ps; exit 1

lint: ## ruff + mypy + compose config validation
	$(UV) run ruff check . $(CURDIR)/tests-platform
	$(UV) run ruff format --check . $(CURDIR)/tests-platform
	$(UV) run mypy app
	$(MAKE) check-profiles

fmt: ## Auto-format
	$(UV) run ruff format . $(CURDIR)/tests-platform && $(UV) run ruff check --fix . $(CURDIR)/tests-platform

bootstrap: .env ## Idempotent: Keycloak realm/clients + TB OAuth2 client/domain (M0.3)
	set -a && . ./.env && set +a && KC_ADMIN_URL=http://127.0.0.1:18081 TB_ADMIN_URL=http://127.0.0.1:18080 \
	  $(UV) run python -m scripts.setup_keycloak && \
	  set -a && . ./.env && set +a && KC_ADMIN_URL=http://127.0.0.1:18081 TB_ADMIN_URL=http://127.0.0.1:18080 \
	  $(UV) run python -m scripts.setup_tb_oauth2

provision: .env ## Provision/repair a student tenant: make provision EMAIL=x@y
	set -a && . ./.env && set +a && TB_ADMIN_URL=http://127.0.0.1:18080 $(UV) run python -m scripts.provision_student $(EMAIL) $(ARGS)

migrate: .env ## Apply portal DB migrations against the local stack
	set -a && . ./.env && set +a && PORTAL_DATABASE_URL=$$(echo $$PORTAL_DATABASE_URL | sed 's|@postgres:|@127.0.0.1:|') $(UV) run alembic upgrade head

class-code: .env ## Create a class code: make class-code CODE=X COHORT=Y INSTRUCTOR=Z
	set -a && . ./.env && set +a && PORTAL_DATABASE_URL=$$(echo $$PORTAL_DATABASE_URL | sed 's|@postgres:|@127.0.0.1:|') $(UV) run python -m scripts.class_code create $(CODE) --cohort $(COHORT) --instructor $(INSTRUCTOR)

kc-export: .env ## Export the Keycloak realm to keycloak/realm/ (secrets masked)
	set -a && . ./.env && set +a && KC_ADMIN_URL=http://127.0.0.1:18081 KC_EXPORT_DIR=$(CURDIR)/keycloak/realm \
	  $(UV) run python -m scripts.export_keycloak

caddy-image: ## Build Caddy + layer4 image for staging/prod (D8). Needs ~4 GB RAM.
	docker build --build-arg CADDY_VERSION=$$(grep ^CADDY_VERSION= .env.example | cut -d= -f2) \
	  --build-arg CADDY_L4_VERSION=$$(grep ^CADDY_L4_VERSION= .env.example | cut -d= -f2) \
	  -t chertiot/caddy:$$(grep ^CADDY_VERSION= .env.example | cut -d= -f2)-l4 deploy/caddy

check-profiles: ## Validate compose file for every profile
	@for p in core flows lab lora; do $(COMPOSE) -f docker-compose.yml --env-file .env.example --profile $$p config -q || exit 1; done

staging-deploy: ## Deploy/upgrade staging (M2.2)
	deploy/scripts/deploy.sh 2.29.25.134 stage.chertiot.com

prod-deploy: ## Deploy/upgrade production (M2.3)
	deploy/scripts/deploy.sh 2.29.18.157 chertiot.com
