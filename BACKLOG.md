# BACKLOG — out of current plan scope (D12)
- Portal as OIDC-aware "login as user" audit trail hardening (M3.3 detail).
- X.509 device auth over MQTTS (D8: layer4 passthrough switch).
- Keycloak: build an optimized image (kc.sh build) so `start --optimized` is used instead of auto-build on start.
- Portal: explicit CSRF tokens on state-changing forms (currently relying on SameSite=Lax session cookie).
- Portal: cache the student's TB JWT in the session instead of sysadmin impersonation on every request.
- Portal: e2e cleanup of portal_users rows for test accounts (TB tenants are cleaned; portal rows remain).

## M4.1 LoRaWAN — ChirpStack schema init (blocked, needs upstream-level fix)
The chirpstack/chirpstack:4.19.1 image applies **0 schema migrations** to a fresh PostgreSQL DB
(diesel tracker table created, but no `user`/device tables). Our config matches the upstream
chirpstack-docker example; the container starts, configures EU868, connects Postgres and serves
gRPC, but `run_pending_migrations` embeds/sees an empty set (completes in ~200 ms, no diesel output).
Diagnosed but not root-caused (candidate: image build feature flag). Impact: ChirpStack device
*registration* (the /lora "Register" button) can't persist a device yet. The rest of M4.1 is DONE
and verified: the lora-bridge forwards ChirpStack-format uplinks to the owning student's TB device
(bridge-path acceptance PASS on staging — a simulated uplink landed on the dashboard), portal
mapping, simulator, gateway docs, gRPC client. Next step when resumed: reproduce with a known-good
tag / minimal config in isolation, or raise upstream; then re-run the full register→uplink test.
