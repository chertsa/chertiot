# CHERT IoT — project memory
Read PLAN.md. Current: Phase 0 / M0.2. Last done: M0.1 (scaffold).
## Hard rules
- Decisions D1–D12 in PLAN.md are final.
- Brand: "CHERT IoT" display / `chertiot` code+domain.
- Portal→TB: REST only via tb_client.py. Idempotent provisioning, always.
- No secrets in git; .env only; .env.example current. Never invent creds — ask.
- Tests green before a milestone is done. make lint test must pass at session end.
- Staging before production, every time.
- Pin every image/dependency. Upgrades are deliberate milestones.
- TB API surprises → workaround in tb_client.py + note here + regression test.
## Commands
make dev | test | e2e | lint | staging-deploy | prod-deploy
## Environment
- Python via `uv` (portal/pyproject.toml + uv.lock). Python 3.12 pinned in portal/.python-version.
- Local dev: `make dev` (compose `core` profile). Needs `.env` (copy .env.example).
- Design tokens & logos: docs/branding/ (tokens/*.json, chert-tokens per CHERT-Design-System.md). Never hardcode a hex.
## Gotchas
- (none yet)
