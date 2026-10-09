# App integration: language handoff (required)

The theme alone makes the pages look right. These two app-side pieces make them **behave** like
chertiot.com: the sign-in pages open in the app's language, and switching language there switches
the app too.

## The contract (3 rules)

1. **Hand the language to Keycloak.** When the app starts sign-in (the OIDC authorization
   request), add **`ui_locales=<lang>`**, where `<lang>` is the app's current UI language (`en`/`ar`).
   - Do **not** use `kc_locale` on the auth URL: Keycloak 26 ignores it there.
   - `ui_locales` outranks Keycloak's own `KEYCLOAK_LOCALE` cookie (verified on 26.7.2).
2. **Expose a language switch with a safe `next`.** Provide `GET {langSwitchPath}`, e.g.
   `GET /lang/{code}?next=/login`:
   - set the app's language (cookie or session) to `code` (`en`/`ar`);
   - redirect to `next` **only if** it is a same-site relative path: it starts with `/`, does not
     start with `//`, and contains no `\`. Otherwise redirect to the Referer or `/`. This prevents
     open redirects.
   - Set `langSwitchPath` in `project.json` to that path with `{code}`, and set the client's
     **Base URL** in Keycloak (the pill links to `<Base URL><langSwitchPath>`).
3. **Never read Keycloak's `locale` back** (the user attribute or the `locale` token claim) to set
   the app language. Keycloak stores it only when the user switches on its page and never clears it,
   so it is often weeks stale. The app is the single source of truth.

No language endpoint yet? Set `"langSwitchPath": ""`. The pill then uses Keycloak's own switch
(Keycloak changes language; the app doesn't follow). Rule 1 still applies.

## Snippets

### FastAPI / Starlette + Authlib (the chertiot.com implementation)
```python
@router.get("/login")
async def login(request: Request):
    return await oauth.keycloak.authorize_redirect(
        request, f"{PUBLIC_URL}/auth/callback", ui_locales=locale_of(request)  # "en" | "ar"
    )

def _safe_next(value: str | None) -> str | None:
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value:
        return value
    return None

@router.get("/lang/{code}")
def set_language(code: str, request: Request, next: str | None = None):
    target = _safe_next(next) or request.headers.get("referer") or "/"
    resp = RedirectResponse(target, status_code=303)
    if code in ("en", "ar"):
        resp.set_cookie("lang", code, max_age=365 * 24 * 3600, samesite="lax")
    return resp
```

### Flask + Authlib
```python
@app.get("/login")
def login():
    return oauth.keycloak.authorize_redirect(url_for("callback", _external=True),
                                            ui_locales=current_lang())
```

### Django + mozilla-django-oidc
```python
# urls.py: point "oidc_authentication_init" at this view
from mozilla_django_oidc.views import OIDCAuthenticationRequestView
from django.utils.translation import get_language

class ChertAuthRequestView(OIDCAuthenticationRequestView):
    def get_extra_params(self, request):
        params = super().get_extra_params(request)
        params["ui_locales"] = (get_language() or "en")[:2]
        return params
```
Django's built-in `set_language` is POST-only; add a small GET view for the pill
(`/lang/<code>?next=/oidc/authenticate/`). It sets the language cookie
(`settings.LANGUAGE_COOKIE_NAME`) and validates `next` with
`url_has_allowed_host_and_scheme(next, allowed_hosts={request.get_host()})`.

### Node / Express + openid-client
```js
// v5:
const url = client.authorizationUrl({ scope: "openid email profile", state, nonce, ui_locales: req.cookies.lang || "en" });
// v6:
const url = client.buildAuthorizationUrl(config, { redirect_uri, scope: "openid email profile", state, ui_locales: lang });

app.get("/lang/:code", (req, res) => {
  const next = req.query.next;
  const safe = typeof next === "string" && next.startsWith("/") && !next.startsWith("//") && !next.includes("\\");
  if (["en", "ar"].includes(req.params.code)) res.cookie("lang", req.params.code, { maxAge: 31536000000, sameSite: "lax" });
  res.redirect(303, safe ? next : (req.get("referer") || "/"));
});
```

### Next.js + Auth.js (next-auth)
```ts
// client: pass authorization params per sign-in
signIn("keycloak", undefined, { ui_locales: locale });   // locale = "en" | "ar"
```
Add a route handler `app/lang/[code]/route.ts` that implements rule 2 and redirects to `next`
(e.g. a page that calls `signIn`).

### Single-page app + keycloak-js
```js
keycloak.login({ locale: currentLang });   // keycloak-js sends it as ui_locales
```

### Spring Security (OAuth2 client)
Wrap `DefaultOAuth2AuthorizationRequestResolver` and add the parameter:
```java
builder.additionalParameters(p -> p.put("ui_locales", LocaleContextHolder.getLocale().getLanguage()));
```

### Anything else
Append `&ui_locales=en` or `&ui_locales=ar` to the authorization URL your app builds.

## Check it
```bash
curl -s -o /dev/null -w '%{redirect_url}\n' -b 'lang=ar' https://app.example.com/login   # → ...&ui_locales=ar
curl -s -o /dev/null -w '%{redirect_url}\n' -b 'lang=en' https://app.example.com/login   # → ...&ui_locales=en
```
`tools/verify_login.js --app https://app.example.com --lang-cookie lang` runs the same check.
