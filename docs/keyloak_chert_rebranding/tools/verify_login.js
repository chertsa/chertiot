// CHERT Keycloak login — browser verification (headless Chrome via playwright-core; no browser
// download: uses the installed Google Chrome). Checks sign-in + forgot-password in EN and AR,
// desktop and phone, and (optionally) that the app hands its language to Keycloak.
//
//   npm i playwright-core@1
//   node verify_login.js --kc https://auth.example.com --realm myrealm --client portal \
//        --redirect https://example.com/auth/callback [--app https://example.com] [--lang-cookie lang] \
//        [--out ./shots]
//
// Exit code 0 only if every check passes. Prints a JSON report; writes screenshots to --out.
const fs = require("fs");
const { chromium } = require("playwright-core");

const arg = (k, d) => { const i = process.argv.indexOf("--" + k); return i > 0 ? process.argv[i + 1] : d; };
const KC = arg("kc"), REALM = arg("realm"), CLIENT = arg("client"), REDIRECT = arg("redirect");
const APP = arg("app"), LANG_COOKIE = arg("lang-cookie", "lang"), OUT = arg("out", "./chert-login-shots");
if (!KC || !REALM || !CLIENT || !REDIRECT) { console.error("usage: see header"); process.exit(2); }
fs.mkdirSync(OUT, { recursive: true });
const authUrl = (lang) => `${KC}/realms/${REALM}/protocol/openid-connect/auth?response_type=code&client_id=${encodeURIComponent(CLIENT)}` +
  `&redirect_uri=${encodeURIComponent(REDIRECT)}&scope=openid&ui_locales=${lang}`;

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const report = { checks: [], failures: [] };
  const ok = (name, cond, detail) => { (cond ? report.checks : report.failures).push(detail ? `${name}: ${detail}` : name); };
  const kcHost = new URL(KC).hostname;

  for (const [vw, tag] of [[1440, "desktop"], [390, "phone"]]) {
    for (const lang of ["en", "ar"]) {
      // browser language deliberately the opposite: ui_locales must win
      const ctx = await browser.newContext({ viewport: { width: vw, height: 900 }, locale: lang === "ar" ? "en-US" : "ar" });
      const p = await ctx.newPage();
      const bad = [];
      p.on("response", (r) => { if (r.status() >= 400) bad.push(`${r.status()} ${r.url()}`); });
      p.on("pageerror", (e) => bad.push("JS " + e.message));
      p.on("console", (m) => { if (m.type() === "error") bad.push("console " + m.text()); });
      p.on("request", (r) => { const u = new URL(r.url()); if (u.protocol.startsWith("http") && u.hostname !== kcHost) bad.push("EXTERNAL " + r.url()); });
      const id = `${tag}-${lang}`;

      await p.goto(authUrl(lang), { waitUntil: "networkidle" });
      const s = await p.evaluate(() => ({
        lang: document.documentElement.lang, dir: document.documentElement.getAttribute("dir"),
        panel: !!document.querySelector(".chert-auth__brand"), stack: !!document.querySelector(".chert-stack"),
        pill: document.querySelector(".chert-lang__pill")?.textContent.trim(), select: !!document.querySelector("#login-select-toggle"),
        css: [...document.querySelectorAll('link[rel=stylesheet]')].map((l) => l.getAttribute("href")).find((h) => /chert\.css/.test(h)) || "",
        icon: document.querySelector('link[rel="icon"]')?.getAttribute("href") || "",
        overflow: document.documentElement.scrollWidth - innerWidth,
      }));
      await p.screenshot({ path: `${OUT}/signin-${id}.png`, fullPage: true });
      ok(`${id} sign-in language`, s.lang === lang, `lang=${s.lang}`);
      ok(`${id} layout LTR`, s.dir === "ltr", `dir=${s.dir}`);
      ok(`${id} brand panel + stack`, s.panel && s.stack);
      ok(`${id} pill names other language`, s.pill === (lang === "ar" ? "English" : "العربية") && !s.select, `pill=${s.pill}`);
      ok(`${id} chert.css versioned`, /chert\.css\?v=[0-9a-f]{10}/.test(s.css), s.css);
      ok(`${id} CHERT favicon versioned`, /img\/favicon\.ico\?v=[0-9a-f]{10}/.test(s.icon), s.icon);
      ok(`${id} no horizontal overflow`, s.overflow <= 0, `overflow=${s.overflow}`);

      await p.click('a[href*="reset-credentials"]');
      await p.waitForLoadState("networkidle");
      const r = await p.evaluate(() => ({ lang: document.documentElement.lang, panel: !!document.querySelector(".chert-auth__brand"),
        pill: document.querySelector(".chert-lang__pill")?.textContent.trim() }));
      await p.screenshot({ path: `${OUT}/reset-${id}.png`, fullPage: true });
      ok(`${id} forgot-password language`, r.lang === lang && r.panel, `lang=${r.lang}`);
      ok(`${id} no 4xx / JS errors / external requests`, bad.length === 0, bad.join(" | "));
      await ctx.close();
    }
  }

  if (APP) {  // the app must hand its language to Keycloak (OIDC ui_locales)
    for (const lang of ["en", "ar"]) {
      const res = await fetch(`${APP.replace(/\/$/, "")}/login`, { redirect: "manual", headers: { cookie: `${LANG_COOKIE}=${lang}`, "accept-language": lang === "ar" ? "en" : "ar" } });
      const loc = res.headers.get("location") || "";
      ok(`app /login hands over ${lang}`, new URL(loc, APP).searchParams.get("ui_locales") === lang, `location ui_locales=${new URL(loc, APP).searchParams.get("ui_locales")}`);
    }
  }

  await browser.close();
  console.log(JSON.stringify(report, null, 1));
  process.exit(report.failures.length ? 1 : 0);
})().catch((e) => { console.error("FAILED:", e.message); process.exit(1); });
