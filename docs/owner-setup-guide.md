# Owner setup guide — everything needed to put chertiot.com live

**Updated 2026-08-31.** Progress:

- [x] 1. GitHub repository — **done**: <https://github.com/chertsa/chertiot> (private). One follow-up decision: §1a below.
- [x] 2. Servers — **Hetzner pair bootstrapped** (hardening, firewall, Docker, swap). One decision + one resize: §2a below.
- [~] 3. DNS — nameservers live at DigitalOcean; `@`/`www`/`stage` exist. Needs the records in §3a (5 min, depends on §2a).
- [x] 4. SMTP — **done and verified**: `mail.chert.sa:587` answers with a valid certificate and SPF already authorizes it. I put the credentials into the servers' `.env` at deploy time (never into git). Since the password was pasted into chat, rotate it after launch when convenient.

---

## 1a. DECISION: GitHub Actions won't run — pick one (1 minute)

CI fails instantly with *"Actions budget is preventing further use"*: the account has no Actions budget for **private** repos.

**Option A — make the repo public (recommended; PLAN.md declares the project "fully open-source"; history verified clean of secrets).** Reply **`make it public`** and I run it. Actions minutes and GHCR become free and unlimited.

**Option B — keep it private and pay for minutes.** GitHub → your avatar → **Settings → Billing and plans → Budgets and alerts → New budget** → product **Actions** → set e.g. $10/month → save. CI starts on the next push; no reply needed, I'll see it.

## 2a. DECISION: which servers serve (and one resize)

Facts: my deploy key works on the **Hetzner** pair only; DNS currently points at the **DigitalOcean** droplets; every box is ≤4 GB while PLAN.md (D9, success criterion 5) requires **8 GB minimum for production**.

**Option A — consolidate on Hetzner (recommended: access already works, ~⅕ the price).**
1. Rescale production: Hetzner Console → project chertiot → server **chertiot-prod** → **Rescale** → *CPU/RAM only* → **CX32** (4 vCPU / 8 GB, ≈€8/mo) → confirm (~2 min downtime). Keep "CPU/RAM only" so you can downscale later.
2. Do §3a below (point DNS at Hetzner).
3. Destroy both DigitalOcean droplets when the switch is verified (saves $48/mo): DO console → droplet → **Destroy**.
- chertiot-staging (CX22, 4 GB) stays as-is — fine for staging.

**Option B — serve from DigitalOcean instead.**
1. Resize production: DO console → chertiotserver → **Resize → CPU and RAM only → s-4vcpu-8gb** ($48/mo).
2. The staging droplet (2 GB) is too small even for staging — resize to s-2vcpu-4gb.
3. Add my key to both: DO console → droplet → **Access → Launch Droplet Console** → log in → run:
   `mkdir -p ~/.ssh && echo '<the ssh-ed25519 line from §2.2>' >> ~/.ssh/authorized_keys`
4. Tell me when done; DNS already points here.

## 3a. DNS records (5 min, in the DigitalOcean panel you already use)

DO console → **Networking → Domains → chertiot.com**. For **Option A** set every record to the Hetzner IPs; for Option B keep the existing ones. Create what's missing (TTL 3600):

| Type | Hostname | Value (Option A) |
|---|---|---|
| A | `@` | 2.29.18.157 *(exists: change from 137.184.102.135)* |
| A | `www` | 2.29.18.157 *(change)* |
| A | `app` | 2.29.18.157 *(create)* |
| A | `auth` | 2.29.18.157 *(create)* |
| A | `status` | 2.29.18.157 *(create)* |
| A | `stage` | 2.29.25.134 *(exists: change from 137.184.53.196)* |
| A | `app.stage` | 2.29.25.134 *(create)* |
| A | `auth.stage` | 2.29.25.134 *(create)* |
| A | `status.stage` | 2.29.25.134 *(create)* |

I verify with `dig` and need no message from you.

## What I do the moment each lands
- §1a → CI green → tag v0.9.0 → branded ThingsBoard + Caddy images published.
- §3a (staging rows) → deploy staging on chertiot-staging → Let's Encrypt certs → full e2e over the internet.
- §2a resize + §3a (prod rows) → production deploy → backups + restore drill → Gate 2 → v1.0.0.

---

The original click-by-click sections follow for reference.

---

## 1. GitHub repository (CI, image builds, Gate 1 tag)

You are already logged into the GitHub CLI on this machine as **chertsa** with permission to create repositories.

**Option A — say the word (recommended).** Reply `create the repo` and I run:

~~~
gh repo create chertsa/chertiot --private --source . --push
~~~

That creates the private repo, pushes all 13 commits, and CI starts automatically (lint+tests, full-stack e2e, isolation; nightly flood; image builds on demand). Nothing else for you to do.

**Option B — do it yourself in the browser.**

1. Open <https://github.com/new>.
2. Owner: **chertsa** · Repository name: **chertiot** · visibility: **Private**.
3. Do NOT tick "Add a README" (the repo must stay empty).
4. Click **Create repository**, then send me the URL it shows (e.g. `https://github.com/chertsa/chertiot.git`). I push and verify CI.

**After this step:** CI runs the whole test suite on clean machines; when green I tag **v0.9.0** (Gate 1) and trigger the branded ThingsBoard + Caddy image builds to GHCR.

---

## 2. Servers — production and staging VPS

The plan (D9) calls for production **8 vCPU / 16 GB** plus a small staging box. Hetzner is the reference choice (any provider with Ubuntu 24.04 works — Contabo, DigitalOcean, OVH; keep the same sizes).

### 2.1 Create the account & project
1. Sign up at <https://accounts.hetzner.com> (needs a card or PayPal; identity check can take a few hours on new accounts).
2. Open **Hetzner Cloud Console** <https://console.hetzner.cloud> → **+ New project** → name it `chertiot`.

### 2.2 Add my deploy key (before creating servers)
1. In the project: **Security → SSH keys → Add SSH key**.
2. Name: `chertiot-deploy`. Paste exactly this public key (already generated on this machine; the private half never leaves it):

~~~
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINnOD4jh2yoB/IboBmLbG1eR46hfLdC54TR+R/zsCpkN chertiot-deploy
~~~

3. Also add **your own** SSH key the same way (Mac: `cat ~/.ssh/id_ed25519.pub`, create one with `ssh-keygen -t ed25519` if missing) — so you always have access independent of me.

### 2.3 Create the two servers
For each: **Servers → Add server**.

| Setting | Production | Staging |
|---|---|---|
| Location | Falkenstein or Helsinki (pick one, use it for both) | same |
| Image | **Ubuntu 24.04** | Ubuntu 24.04 |
| Type | **Shared vCPU x86 → CX42** (8 vCPU / 16 GB, ≈€17/mo) | **CX32** (4 vCPU / 8 GB, ≈€8/mo) |
| Networking | IPv4 + IPv6 on | same |
| SSH keys | tick **chertiot-deploy** and your key | same |
| Name | `chertiot-prod` | `chertiot-staging` |

(Prices are approximate — take whatever the console shows.)

### 2.4 Hand back
Send me the two IPv4 addresses shown on the server list, e.g.:

~~~
prod: 65.x.x.x
staging: 91.x.x.x
~~~

**After this step:** I run `deploy/scripts/bootstrap.sh` on both (hardening, firewall 22/80/443/8883, fail2ban, Docker), deploy the stack to staging first, run the full e2e suite against it over the real internet, then production, then the backup restore drill.

---

## 3. DNS — chertiot.com

Right now the domain answers with **no nameservers at all**, so nothing can resolve. Two sub-cases:

### 3.0 If the domain is not actually registered yet
Register `chertiot.com` at any registrar (Namecheap, Cloudflare Registrar, Porkbun; ≈US$10/yr), then continue below.

### 3.1 Put DNS on Cloudflare (free, reference choice)
1. Create a free account at <https://dash.cloudflare.com/sign-up>.
2. **Add a domain** → enter `chertiot.com` → choose the **Free** plan.
3. Cloudflare shows two nameservers (like `ada.ns.cloudflare.com` / `bob.ns.cloudflare.com`).
4. Log into your **registrar** (where the domain was bought) → find **Nameservers** for chertiot.com → replace whatever is there with those two → save. Propagation: minutes to a few hours.

### 3.2 Create the records (Cloudflare → chertiot.com → DNS → Records)
Add each with **Add record**. **Set "Proxy status" to "DNS only" (grey cloud) on every record** — Caddy does our TLS, and MQTT (8883) cannot pass through Cloudflare's proxy.

| Type | Name | Content | Proxy |
|---|---|---|---|
| A | `@` | *prod IP* | DNS only |
| A | `app` | *prod IP* | DNS only |
| A | `auth` | *prod IP* | DNS only |
| A | `status` | *prod IP* | DNS only |
| A | `staging` | *staging IP* | DNS only |
| A | `app.staging` | *staging IP* | DNS only |
| A | `auth.staging` | *staging IP* | DNS only |
| A | `status.staging` | *staging IP* | DNS only |

(`lab` and `flows` come with Phase 3 — I'll ask again then. Step 4 adds two more records here for email.)

### 3.3 Hand back
Nothing — I verify with `dig` and continue as soon as the records resolve.

---

## 4. SMTP — verification emails

Any SMTP works. Reference choice: **Brevo** (free 300 emails/day, no card):

1. Sign up at <https://www.brevo.com> and confirm your account email.
2. Top-right profile menu → **SMTP & API → SMTP** tab → **Generate a new SMTP key**. Note the 4 values shown: server (`smtp-relay.brevo.com`), port (`587`), login (your Brevo account email), and the generated SMTP key (password).
3. **Senders & domains → Domains → Add a domain** → `chertiot.com` → Brevo shows 2–3 DNS records (DKIM TXT, a Brevo code TXT, and asks for SPF). Add them in Cloudflare exactly as shown (DNS only), plus if no SPF exists yet:
   - TXT · Name `@` · Content `v=spf1 include:sendinblue.com ~all` *(use the exact value Brevo displays)*
   - TXT · Name `_dmarc` · Content `v=DMARC1; p=none; rua=mailto:khalid@alholan.com`
4. Back in Brevo click **Verify & authenticate** until the domain shows green.
5. **Senders → Add a sender**: `no-reply@chertiot.com`.

### Hand back
Fill these four lines (send them to me, or paste into `.env` on the servers later — I'll place them):

~~~
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=<your Brevo login email>
SMTP_PASSWORD=<the generated SMTP key>
~~~

**After this step:** Keycloak sends real verification mail; I run one real signup end-to-end on staging before Gate 2.

---

## What happens after all four (my side, no input needed)

1. CI green → tag **v0.9.0** (Gate 1) → branded ThingsBoard + Caddy images published.
2. Staging: bootstrap → deploy → Let's Encrypt certs → full e2e + isolation + flood over the internet → real ESP32 checklist.
3. Production: same deploy → backups live (nightly, alerted) → **restore drill onto staging, timed** (<1 h target).
4. Gate 2 checklist from PLAN.md (status page, privacy page, docs verified by an outside human) → **v1.0.0 — public launch**.
