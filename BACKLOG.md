# BACKLOG — out of current plan scope (D12)
- Portal as OIDC-aware "login as user" audit trail hardening (M3.3 detail).
- X.509 device auth over MQTTS (D8: layer4 passthrough switch).
- Keycloak: build an optimized image (kc.sh build) so `start --optimized` is used instead of auto-build on start.
- Portal: explicit CSRF tokens on state-changing forms (currently relying on SameSite=Lax session cookie).
- Portal: cache the student's TB JWT in the session instead of sysadmin impersonation on every request.
- Portal: e2e cleanup of portal_users rows for test accounts (TB tenants are cleaned; portal rows remain).

