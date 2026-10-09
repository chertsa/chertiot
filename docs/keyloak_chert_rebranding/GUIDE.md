# CHERT Keycloak login — universal rebranding guide

The reference build is **chertiot.com** (CHERT IoT, Keycloak 26.7.2, live since v2.0.1). Every CHERT
project that signs users in with Keycloak uses **this exact design**: same layout, graphics, colours,
typography, motion and behaviour. **Only the text changes** per project.

| Reference page | URL |
|---|---|
| Sign-in | `https://auth.chertiot.com/realms/chertiot/protocol/openid-connect/auth?client_id=portal&…&ui_locales=ar` |
| Forgot password | `https://auth.chertiot.com/realms/chertiot/login-actions/reset-credentials?client_id=portal&…` |

Reference screenshots: [`screenshots/`](screenshots/) (EN/AR, desktop/phone, sign-in and forgot password),
plus an example of another project (`example-chert-club-*`) built from this kit: same design, different text.

**Tested:**
- production chertiot.com passes all 38 checks of `tools/verify_login.js`;
- a clean Keycloak 26.7.2 running a different project from this kit passes 36 of 36.

---

## 1. What you get

- A complete Keycloak **login theme** (`theme/chert/`), a child of Keycloak's `keycloak.v2`:
  - **Brand panel** (left, dark): CHERT logo + product name, eyebrow, two-tone headline, lead
    sentence, three icon bullets, and an animated isometric "layer stack" with rising data packets.
  - **Form card** (right, cream): Keycloak's own PatternFly 5 form, restyled as a CHERT card.
  - **Language pill** naming the other language (English ↔ العربية) instead of Keycloak's dropdown.
  - **CHERT favicon** and apple-touch icon; self-hosted Inter and IBM Plex Sans Arabic fonts.
- It covers **every** login-theme page: sign-in, forgot password, update password, verify email,
  OTP, errors and info pages. They all render through `template.ftl`.
- **Tools:** `apply_project.py` (writes the text), `version_assets.py` (cache-busting),
  `test_keycloak_theme.py` (CI guard), `verify_login.js` (browser verification).

## 2. The only per-project input: `project.json`

Copy [`project.example.json`](project.example.json) (chertiot.com's values) and change the text:

| Field | Where it shows | Rules |
|---|---|---|
| `productName` | Logo: **CHERT** <span style="color:#FF8651">**{productName}**</span> | 1–2 words, Latin script (brand) |
| `en/ar.loginTitle` | Browser tab title | "Sign in to CHERT {product}" |
| `en/ar.eyebrow` | Small orange caps line above the headline | ≤ 5 words |
| `en/ar.title` | Headline, first part (cream) | ≤ 6 words, ends with "." |
| `en/ar.titleAccent` | Headline, second part (orange→tan gradient) | ≤ 8 words |
| `en/ar.lead` | Grey sentence under the headline | 1 sentence, ≤ 20 words |
| `en/ar.points[3]` | Three bullets with icons | ≤ 8 words each |
| `icons[3]` | Bullet icons | `lock wifi globe users shield chart book bolt layers grid cpu database calendar heart check` |
| `appClientId` | Your app's OIDC client id | Used by the language pill |
| `langSwitchPath` | Your app's language switch | `"/lang/{code}?next=/login"`, or `""` to use Keycloak's own switch |

Arabic is **Modern Standard Arabic**. Keep product names, protocols and acronyms in Latin
(CHERT, MQTT, Node-RED, Python…). `apply_project.py` automatically protects Latin hyphenated words
("Node-RED", "Wi-Fi") from breaking across lines in Arabic. Without that, the bidi order of the
sentence scrambles.

## 3. Design specification (do not change per project)

### 3.1 Colours: CHERT tokens (single source: the `:root` block of `chert.css`)

| Token | Value | Use |
|---|---|---|
| `--chert-orange` | `#FF8651` | Primary button, accent text, pill hover, focus ring |
| `--chert-orange-deep` | `#F26B33` | Button hover, links, gradient end |
| `--chert-tan` | `#D2B082` | Gradient middle, panel glow |
| `--chert-cream` | `#FFFAE4` | Page (form side) background |
| `--chert-ink` | `#1A1A18` | Text on light, button text (ink on orange = 7.3:1) |
| `--chert-surface` | `#FFFFFF` | Form card, inputs |
| `--chert-surface-alt` | `#FBF7EC` | Password-eye button |
| `--chert-border` / `-strong` | `#ECE0C2` / `#D9C9A4` | Card and input borders / pill border |
| `--chert-muted` | `#6B6B66` | Secondary text |
| `--chert-dark` / `-surface` / `-border` | `#151311` / `#1B1815` / `#26221D` | Brand panel |
| `--chert-dark-text` / `-muted` | `#F3EDE0` / `#A89E8D` | Brand panel text |
| `--chert-error/-success/-warning/-info` (+ `-tint`) | `#EF4444` `#10B981` `#F59E0B` `#3B82F6` | Alerts |

Rule: **never write a colour value outside that token block.** Tints use `color-mix(in srgb, var(--token) N%, transparent)`.

### 3.2 Layout

- **Desktop (≥ 960 px):** two columns, `5fr : 6fr`, full viewport height.
  - **Left, brand panel:** `--chert-dark` with two radial glows (orange top-right 26%, tan
    bottom-left 14%). Padding `clamp(28px, 5vw, 64px)`. Logo at the top, pitch centred vertically,
    layer stack at the bottom.
  - **Right, form side:** cream with a 22 px tan dot grid. Card centred, `width: min(100%, 500px)`,
    radius 24 px, 1 px border, padding `clamp(24px, 4vw, 40px)`, soft long shadow.
- **Phone (< 960 px):** stacked. The brand panel shrinks to logo + eyebrow + headline (26 px); lead,
  bullets and artwork are hidden. The card follows below. No horizontal scroll, ever.

### 3.3 Typography

- **Latin:** Inter (variable, self-hosted). **Arabic:** IBM Plex Sans Arabic 400/600/700 (self-hosted).
- Headline: `clamp(30px, 3.4vw, 46px)`, weight 800, letter-spacing −0.035em, line-height 1.06
  (Arabic: normal letter-spacing, line-height 1.3).
- Card title (`#kc-page-title`): `clamp(26px, 3vw, 32px)`, weight 800. Eyebrow: 12 px, 700,
  uppercase, letter-spacing 0.14em, orange, with a 24 × 2 px rule before it.
- Body 16 px; labels 14 px / 600; lead 18 px / line-height 1.6 in `--chert-dark-muted`.

### 3.4 Components

- **Primary button:** orange, ink text, 700, min-height 46 px, radius 8 px. Hover: orange-deep and
  lift 1 px. **Secondary** (e.g. "« Back to Login"): transparent with a 1.5 px ink outline.
- **Inputs:** white, 1 px `--chert-border`, radius 8 px, min-height 42 px. Focus: orange border plus
  a 3 px orange ring at 25%, with no second outline. Password eye: joined on the right,
  surface-alt background.
- **Language pill:** shows only the other language ("English" on Arabic pages, "العربية" on English
  pages). Pill radius 999 px, 1 px strong border, 600 / 14 px. Hover turns orange-deep.
- **Bullets:** 36 px rounded-square tile (radius 11 px), orange icon on orange 14% tint, 600 text.
- **Alerts:** radius 10 px, 4 px left edge in the semantic colour, tint background.
- **Links:** orange-deep, 600, no underline; underline on hover.

### 3.5 Graphics and motion

- **Layer stack:** four isometric plates (`rotateX(58deg) rotateZ(45deg)`), the top plate
  orange-tinted. They float ±7 px on a 6 s cycle with staggered delays. A vertical orange beam
  carries four glowing packets rising every 4 s. Geometry scales with `--u` (0.6 px in the panel).
- **Logo:** `img/logo.svg` (the CHERT arrowhead) at 30 px. **Favicon:** `img/favicon.ico`
  (multi-size 16–64, 12 KB); do not use the 378 KB SVG as a favicon.
- `prefers-reduced-motion: reduce` → no float and no packets (static artwork).

## 4. Behaviour rules (the details that make it "the same")

1. **Arabic is translation-only: the layout stays LTR.** Keycloak marks `ar` as RTL and emits
   `dir="rtl"`. The theme forces `direction: ltr` (CSS) and `dir="ltr"` (`js/ltr.js`), keeps text
   left-aligned, and gives each text block `unicode-bidi: plaintext`, so mixed Arabic + Latin reads
   in the right order without mirroring the page.
2. **The app's language decides the sign-in language.** The app must send OIDC **`ui_locales`**
   (`en`/`ar`) on its authorization request. On Keycloak 26 this outranks a stale
   `KEYCLOAK_LOCALE` cookie. **`kc_locale` on the auth URL is ignored**, so don't use it.
3. **The language pill switches through the app.** On sign-in and forgot-password pages for your
   app's client, the pill links to `{client Base URL}{langSwitchPath}`. The app sets its own
   language cookie and restarts sign-in in the new language, so app and Keycloak never disagree.
   On every other page (email action links, other clients) Keycloak's own switch is kept, so
   one-time action URLs survive.
4. **Never read Keycloak's stored `locale` attribute back into the app.** Keycloak stores it only
   when the user switches on its page, and never clears it. Reading it back applies stale choices
   from weeks ago (verified).
5. **Cache-busting is mandatory.** Keycloak serves theme files under
   `/resources/<keycloak-build>/…` with `max-age=30 days`, and that URL doesn't change when your
   theme does. Every asset carries `?v=<sha256[:10]>`. **Run `tools/version_assets.py` after any
   change**; the CI test enforces it.
6. **Light design only:** `darkMode=false` (otherwise Keycloak recolours the card with OS dark mode).
7. **Zero external requests:** fonts, icons and images are all inside the theme.

## 5. Install into a project

1. **Copy the theme:** `theme/chert` → your repo, e.g. `keycloak/themes/chert/`.
2. **Write the text:** `cp project.example.json project.json`, edit it, then
   `python3 tools/apply_project.py project.json keycloak/themes/chert/login`.
3. **Mount it into Keycloak** (Docker Compose):
   ```yaml
   keycloak:
     volumes:
       - ./keycloak/themes/chert:/opt/keycloak/themes/chert:ro
   ```
   A directory mount, not single files. Keycloak only scans themes at start-up, so **restart
   Keycloak after every theme change** (a production `start` caches templates).
4. **Configure the realm and client** with the idempotent tool (or the same settings in your
   own bootstrap):
   `KC_ADMIN_PASSWORD=… python3 tools/keycloak_setup.py --kc <url> --realm <realm> --client <app-client> --base-url <app-home> [--email-as-username]`
   - Login theme `chert`
   - Internationalization ON (`en` + `ar`, default `en`)
   - **Forgot password ON** (otherwise there is no reset link)
   - Remember me ON
   - the client's **Base URL**, which the pill needs
   - with `--email-as-username`, an "Email" field like the reference

   See [`integration/KEYCLOAK-SETUP.md`](integration/KEYCLOAK-SETUP.md).
5. **Wire your app:** send `ui_locales` and provide the language switch. See
   [`integration/APP-INTEGRATION.md`](integration/APP-INTEGRATION.md) (FastAPI/Authlib, Django,
   Flask, Node, Spring and plain URL examples).
6. **Add the CI guard:** copy `tools/test_keycloak_theme.py` into your tests (set `CHERT_THEME_DIR`).
7. **Verify in a real browser:** `tools/verify_login.js` (§6). Do staging first, then production.

### Different Keycloak version?

`template.ftl` is Keycloak 26.7.2's `keycloak.v2/login/template.ftl` with CHERT changes in the
`<body>` only (plus the `chertIcon` macro and the language block). The original is in
[`upstream/keycloak.v2-26.7.2-template.ftl`](upstream/), and the exact changes are in
[`upstream/CHERT-template.diff`](upstream/CHERT-template.diff). On another 26.x version, extract
*your* version's `template.ftl` from `lib/lib/main/org.keycloak.keycloak-themes-<ver>.jar` and
re-apply the diff hunks by hand. Never copy an older template over a newer Keycloak blindly.

## 6. Verification (must pass before you call it done)

```bash
npm i playwright-core@1      # uses the installed Google Chrome; no browser download
node tools/verify_login.js --kc https://auth.example.com --realm myrealm --client portal \
     --redirect https://example.com/auth/callback --app https://example.com --out ./shots
```

It checks EN and AR × desktop and phone, sign-in and forgot password:
- page language, `dir=ltr`, brand panel and stack, a pill naming the other language;
- versioned CSS and favicon;
- no 4xx responses, no JS/console errors, no external requests, no horizontal overflow;
- with `--app`, that the app's `/login` hands over `ui_locales` for each language.

Compare the screenshots with [`screenshots/`](screenshots/): they must look the same apart from
the text.

Manual journey (once): app → choose العربية → Sign in (Arabic) → Forgot password (Arabic) →
pill "English" (the app switches to English, back on sign-in in English) → back to Arabic →
sign in → the app opens in Arabic.

## 7. Pitfalls already paid for (chertiot.com history)

| Symptom | Cause | Fix built into this kit |
|---|---|---|
| New layout but old styling for weeks | 30-day cache on an unversioned CSS URL | `?v=` hashes + CI guard |
| Console 404 / MIME error on the login page | `styles=css/login.css` listed but missing | Only `css/chert.css` is listed |
| Keycloak logo in the tab | The theme had no favicon (fell back to the parent) | CHERT `favicon.ico`, versioned |
| Page flipped right-to-left in Arabic | Keycloak's `ar` = RTL | CSS + `ltr.js` force LTR |
| "Node-" … "RED" split, Arabic order scrambled | Line break at the hyphen | Automatic word joiner |
| Wrong language after sign-in | Reading Keycloak's stale `locale` attribute | Never read it; the app is the source of truth |
| Sign-in ignores the app language | `kc_locale` sent on the auth URL | Use OIDC `ui_locales` |
| Form card recoloured at night | `keycloak.v2` dark mode | `darkMode=false` |
| Theme change not visible | Keycloak not restarted / cached templates | Restart Keycloak after changes |
| Stock Keycloak page; log says "Failed to find LOGIN theme chert" | The mounted folder is empty in the container (Docker/Colima only shares your home folder) | Keep the theme inside a shared path; `docker exec … ls /opt/keycloak/themes/chert/login` |
| No "Forgot password?" link | `resetPasswordAllowed` off | `tools/keycloak_setup.py` turns it on |
| Form says "Username or email" and has no "Remember me" | Realm login settings differ from the reference | `--email-as-username` (only if users sign in by email); Remember me is set by default |
| `tools/version_assets.py` crashed on `${style}` | It tried to version Keycloak's own parent files | Fixed: only this theme's files are versioned |

## 8. Files

```
docs/keyloak_chert_rebranding/
├── README.md                     start here (3-step quick start)
├── GUIDE.md                      this guide
├── PROMPT.md                     copy-paste prompt for Claude Code in each project
├── project.example.json          per-project text (chertiot.com values)
├── theme/chert/login/            the theme (copy as-is)
│   ├── template.ftl              keycloak.v2 26.7.2 + CHERT body
│   ├── theme.properties          parent, assets (?v=), locales, darkMode, project keys
│   ├── messages/messages_{en,ar}.properties
│   └── resources/{css/chert.css, js/ltr.js, img/{logo.svg,favicon.ico,apple-touch-icon.png}, fonts/*.woff2}
├── tools/{apply_project.py, version_assets.py, keycloak_setup.py, test_keycloak_theme.py, verify_login.js}
├── integration/{APP-INTEGRATION.md, KEYCLOAK-SETUP.md}
├── upstream/{keycloak.v2-26.7.2-template.ftl, CHERT-template.diff}
└── screenshots/                  reference renders (EN/AR, desktop/phone)
```
