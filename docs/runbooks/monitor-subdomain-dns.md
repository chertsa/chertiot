# Owner action — add DNS for `monitor.stage.chertiot.com`

To rebrand the platform-Grafana URL from `grafana.stage.chertiot.com` to
`monitor.stage.chertiot.com`, one DNS record is required first. There is **no wildcard**
for `*.stage.chertiot.com` (each sub-domain has its own record), so this must be added
explicitly. Everything else (Caddy routing, TLS cert, Grafana root URL, Keycloak OAuth
redirect, portal links) is code/config I will apply once the name resolves.

## Add this record (at your DNS provider for `chertiot.com`)

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `monitor.stage` | `161.35.119.46` | 300 (or default) |

That points `monitor.stage.chertiot.com` at the staging droplet — the same IP that
`grafana.stage.chertiot.com` already uses.

> For the production/`main` droplet later, the equivalent record is
> `monitor` → `134.122.31.32` (add only when you want it there too).

## Verify it resolves

```
dig +short monitor.stage.chertiot.com     # should print 161.35.119.46
```

## Then tell me, and I will (one deploy):

1. Add the `monitor.{$DOMAIN}` vhost in `deploy/caddy/Caddyfile.prod` (Caddy fetches the
   Let's Encrypt cert on first hit) and make `grafana.{$DOMAIN}` **redirect** to it so old
   links keep working.
2. Set Grafana `GF_SERVER_ROOT_URL` to `https://monitor.{$DOMAIN}`.
3. Update the Keycloak `grafana` OAuth client redirect URI / web origin to `monitor.`.
4. Point the portal "Platform Grafana" card (and the Explore-stack link) at
   `https://monitor.{$DOMAIN}/d/chert-device-traffic?...&kiosk`.
5. Force-recreate Caddy (single-file Caddyfile inode) and verify SSO + the kiosk dashboard
   on the new host end-to-end.

No data or dashboards change — this is a hostname move only.
