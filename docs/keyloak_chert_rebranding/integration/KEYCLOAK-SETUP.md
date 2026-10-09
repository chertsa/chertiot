# Keycloak setup for the CHERT login theme

Tested on **Keycloak 26.7.2** (`quay.io/keycloak/keycloak:26.7.2`; CHERT mirrors it as
`ghcr.io/chertsa/chertiot-keycloak:26.7.2`). Any 26.x works; see GUIDE.md "Different Keycloak version?".

## 1. Mount the theme

```yaml
# docker-compose.yml
keycloak:
  image: quay.io/keycloak/keycloak:26.7.2          # or your pinned mirror
  command: start                                  # production; start-dev for local
  volumes:
    - ./keycloak/themes/chert:/opt/keycloak/themes/chert:ro   # directory mount
```

- **Restart Keycloak after every theme change.** Themes are discovered at start-up, and the
  production `start` caches templates.
  - In development you can disable caching: `KC_SPI_THEME_CACHE_THEMES=false` and
    `KC_SPI_THEME_CACHE_TEMPLATES=false`.
- **Docker Desktop / Colima file sharing:** the host folder must be inside a shared path (usually
  your home directory).
  - Symptom of a non-shared path: the mounted folder is **empty** inside the container, and the
    log says `Failed to find LOGIN theme chert, using built-in themes`.
  - Check with `docker exec <kc> ls /opt/keycloak/themes/chert/login`.
- No `kc.sh build` is needed for themes in `/opt/keycloak/themes`.

## 2. Configure the realm and your app's client: run the tool

```bash
KC_ADMIN_PASSWORD='…' python3 tools/keycloak_setup.py \
    --kc https://auth.example.com --realm myrealm --client portal --base-url https://example.com/ \
    [--email-as-username]
```
The tool is idempotent and uses only the standard library. It sets:

| Setting | Value | Why |
|---|---|---|
| Realm → Themes → Login theme | `chert` | Uses this theme |
| Realm → Localization | Internationalization ON; `en`, `ar`; default `en` | Bilingual pages |
| Realm → Login → Forgot password | ON (`resetPasswordAllowed`) | The reset link exists |
| Realm → Login → Remember me | ON | Same form as the reference |
| Client → Base URL | your app home, e.g. `https://example.com/` | The language pill links to `<Base URL><langSwitchPath>` |
| *(opt-in)* Email as username | `registrationEmailAsUsername`, `loginWithEmailAllowed` | Shows "Email" instead of "Username or email" |

Only use `--email-as-username` if your users sign in with their email. It changes how usernames work.

Prefer adding these settings to the project's own idempotent bootstrap. The tool is the reference
implementation (chertiot.com does the same in `portal/scripts/setup_keycloak.py`).

## 3. Security headers

Keycloak's default response headers (`frame-ancestors 'self'`, `object-src 'none'`) work as-is.
The theme uses inline `style="--i:…"` attributes for the layer-stack animation. If your realm sets a
stricter `Content-Security-Policy` with a `style-src` directive, it must allow
`'unsafe-inline'` for style attributes, or the artwork will not animate.
