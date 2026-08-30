# chertBI Visual Identity Map

Derived 2026-07-11 from branding/chert-colors.jpg and branding/chert_logo.png
(pixel-sampled via Pillow; correct here if official brand hex codes differ).

## Color Tokenss

| Token | Hex | Source | Usage in chertBI |
|---|---|---|---|
| chert-coral (primary) | #FF8651 | brand board, top block | Primary actions, links, active states, accents |
| chert-cream | #FFFAE4 | brand board, bottom-left block | Light surfaces / marketing backgrounds |
| chert-tan | #D2B082 | brand board, bottom-right block | Secondary surfaces, subtle highlights |
| chert-ink | #141414 | brand board typography (measured #010101) | Text, dark UI elements |
| chert-taupe | #5E5044 | dominant logo tone | Logo artwork, muted borders/dividers |

## Name Usage

- Product name: **chertBI** (lowercase "chert", capital "BI") — replaces all user-facing upstream naming.
- Company/brand: **chert**.
- Domains: chertbi.com (marketing), app.chertbi.com (application).

## Logo Placements (application)

| Surface | Asset | Mechanism |
|---|---|---|
| Navbar logo | chert arrowhead (chert_logo.png, 197×300) | `APP_ICON` + `LOGO_RIGHT_TEXT="chertBI"` |
| Browser favicon | same artwork | `FAVICONS` |
| Login page | APP_NAME + logo | `APP_NAME="chertBI"` (drives login heading + page titles) |
| Logo click target | / (home) | `LOGO_TARGET_PATH` |

## Application Theme Mapping

- Primary color → chert-coral #FF8651 (legacy `THEME_OVERRIDES` + antd `colorPrimary` token for Superset 5.x).
- Text → chert-ink; keep default neutral grays for data surfaces (charts must stay readable — do not tint chart palettes with brand colors wholesale).

## Constraints

- Upstream engine name must not appear on public-facing surfaces (marketing site, login page title/heading, navbar).
- Internal license/about notices remain intact (Apache 2.0 compliance).
