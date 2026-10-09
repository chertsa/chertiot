# Prompt: apply the CHERT Keycloak sign-in design to this project

Copy everything below the line into Claude Code, opened in the target project's repository.

---

Apply the **CHERT universal Keycloak login design** to this project. The sign-in and
forgot-password pages (and every other Keycloak login page) must **look and behave exactly like the
reference**, https://auth.chertiot.com (CHERT IoT). **Only the text changes** for this project.

**Get the kit** (public repo, pinned tag):
```bash
git clone --depth 1 --branch keycloak-kit-1.0.0 https://github.com/chertsa/chertiot /tmp/chert-kit
cp -R /tmp/chert-kit/docs/keyloak_chert_rebranding ./docs/keyloak_chert_rebranding
```
Read `docs/keyloak_chert_rebranding/GUIDE.md` completely before changing anything. Also read
`integration/APP-INTEGRATION.md`, `integration/KEYCLOAK-SETUP.md`, and look at `screenshots/`.

### Steps

1. **Discover and report** before editing. Find:
   - the Keycloak version and how it runs (compose service, image, volumes, `start` vs `start-dev`);
   - the realm name and the app's OIDC client id;
   - the app's login route and how the app stores its UI language;
   - any existing Keycloak theme;
   - how the project deploys (staging and production).

   If Keycloak is not 26.x, follow GUIDE.md "Different Keycloak version?" (re-apply
   `upstream/CHERT-template.diff` onto your version's `keycloak.v2` template). Never copy the 26.7.2
   template blindly.
2. **Project text: the only design input.** Create `project.json` from `project.example.json`:
   - Draft `productName` (the word after "CHERT" in the logo), the English eyebrow, title,
     titleAccent, lead and 3 bullet points, plus 3 icons from the allowed list. Base them on this
     project's README and purpose, and follow the length rules in GUIDE.md §2.
   - Write the Arabic yourself in Modern Standard Arabic. Keep brand, product and technical terms
     in Latin script.
   - **Show the draft to the owner and get approval before continuing.**
   - Set `appClientId` to the app's client id, and `langSwitchPath` to the app's language-switch
     path (`""` if the app has no UI language yet).
3. **Install the theme:**
   - copy `theme/chert` into the project, e.g. `keycloak/themes/chert`;
   - run `python3 docs/keyloak_chert_rebranding/tools/apply_project.py project.json keycloak/themes/chert/login`;
   - confirm with `tools/version_assets.py … --check`.

   Do not edit `chert.css`, the layout, the artwork, fonts or colours. If something looks wrong,
   fix the cause (mount, realm settings, version), not the design.
4. **Mount** the theme directory into Keycloak (compose volume) and **restart Keycloak**.
5. **Realm and client:** add the settings from `integration/KEYCLOAK-SETUP.md` to the project's
   idempotent bootstrap (preferred), or run `tools/keycloak_setup.py` with `KC_ADMIN_PASSWORD` from
   the environment. Use `--email-as-username` only if users already sign in by email.
6. **App language handoff** (`integration/APP-INTEGRATION.md`):
   - send `ui_locales` (the app's current language) on the authorization request;
   - add the `GET {langSwitchPath}` endpoint with a safe relative `next`;
   - never read Keycloak's `locale` back;
   - add unit tests: `ui_locales` for both languages, and `next` accepts `/login` but rejects
     `https://…`, `//host` and `/\host`.
7. **CI guard:** copy `tools/test_keycloak_theme.py` into the test suite, with `CHERT_THEME_DIR`
   pointing at the theme's `login` folder.
8. **Verify on staging:**
   - `npm i playwright-core@1`, then
     `node docs/keyloak_chert_rebranding/tools/verify_login.js --kc <auth-url> --realm <realm> --client <client> --redirect <redirect-uri> --app <app-url> --out ./shots`
     must report **0 failures**;
   - compare `./shots` with `screenshots/reference-*`: identical apart from the text;
   - walk the journey once: app → العربية → Sign in (Arabic) → Forgot password (Arabic) →
     pill "English" (the app switches, back on sign-in in English) → sign in → app in the active language.
9. **Production only after the owner's explicit "go":**
   - take a backup or snapshot first;
   - deploy and restart Keycloak;
   - run `verify_login.js` against production (0 failures);
   - report the before/after screenshots.

### Rules
- Same design everywhere: change only `project.json`. No new colours, fonts, images or layout.
- Zero external runtime assets (fonts, icons and images ship inside the theme).
- Arabic is translation-only: the layout stays LTR.
- Cache-busting: every theme asset keeps its `?v=` content hash. Re-run `version_assets.py` after
  any change.
- Never print, log or commit secrets (admin passwords, client secrets, tokens). Use environment
  variables or mode-600 files.
- Keep pinned versions; do not upgrade Keycloak as part of this work.

**Done =** CI guard green; `verify_login.js` passes with 0 failures on staging and production;
screenshots match the reference except for the text; the owner has approved the text.
