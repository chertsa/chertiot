# thingsboard-brand/

Source-built ThingsBoard CE with the CHERT IoT brand applied as a **patch series** (D2/D7). Nothing here edits a running container; the output is an image that replaces `thingsboard/tb-node` in `docker-compose.yml` (`TB_IMAGE` in `.env`).

## What is branded
| Surface | Patch / asset |
|---|---|
| Logos (login page, header) | `assets/logo_title_white.svg`, `assets/logo_white.svg` (derived from `docs/branding/logo-master.svg`) |
| Favicon | `assets/favicon.ico` (from `docs/branding/logo-512.png`) |
| Page title, login logo link, "ThingsBoard IoT Hub" home title, share text | `patches/0001-ui-titles-and-links.patch` |
| Primary/secondary palette (`ui-ngx/src/scss/constants.scss`) | `patches/0002-ui-palette.patch` — CHERT ink/taupe as the *primary* (orange stays fill-only per the design system) |
| Login page "powered by ThingsBoard" line | `patches/0003-ui-login-powered-by.patch` |
| Email templates (activation, reset, …) | `patches/0004-email-templates.patch` |

Apache-2.0 attribution stays: About/licence notices are untouched and every branded surface says "powered by ThingsBoard".

## Build
```
./build.sh              # clone v$TB_VERSION → patches → Dockerized Maven build → chertiot/tb:<ver>-b<N>
./build.sh --skip-clone # reuse upstream/ (e.g. while iterating on patches)
```
Needs Docker with ≥8 GB RAM and ~10 GB disk; ~20–60 min. `BUILD_NUMBER` bumps `-bN` when patches change for the same upstream tag.

## Upgrade drill (every upstream bump, M2.1 acceptance)
1. `TB_VERSION=<new> ./build.sh` — patches are applied with `git apply --check` first; a rejected hunk stops the build.
2. Fix the rejected patch against the new sources (`cd upstream && git apply --reject ../patches/000N-*.patch`, edit, `git diff > ../patches/000N-*.patch`).
3. Run the smoke test: `./smoke.sh chertiot/tb:<new>-b1` (branded strings present, stock strings absent).
4. Bump `TB_VERSION` in `.env.example`, run the full local stack + e2e, commit as its own PR.
