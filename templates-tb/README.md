# templates-tb/
ThingsBoard entities the portal instantiates per student via REST (D5):
- `tenant-profile-student.json` — quotas/rate limits (D4). Applied by `ensure_student_profile` and made the default profile so Keycloak-auto-created tenants inherit it. Override a few via `TB_QUOTA_*` env.
- `starter-dashboard.json` — "My devices" dashboard copied into every student tenant (editable; "Reset starter dashboard" re-imports it). Alias resolves all devices in the tenant.
Rate-limit strings are `count:seconds[,count:seconds]` (e.g. `10:1,300:60` = 10/s and 300/min).
