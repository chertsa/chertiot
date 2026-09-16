# CHERT IoT — Student User Guide

Welcome to **[chertiot.com](https://chertiot.com)** — your own Internet-of-Things lab. In about ten
minutes you'll create an account, connect a device (a real ESP32/Raspberry Pi, or just your browser),
and watch your data appear live on a dashboard. This guide walks you through everything.

> Tip: you can switch the whole site to **العربية** with the language toggle in the top bar. Docs
> are also available in Arabic at `/docs/ar/`.

---

## 1. Create your account
1. Go to **<https://chertiot.com/signup>**.
2. Enter your **email** and a **password**, confirm you meet the **age** requirement, and — if your
   teacher gave you a **class code** — type it in (this puts you in their class). No code? Leave it blank.
3. Check your email and click the **verification link**.
4. Come back and **Sign in**. That's it — your personal lab is created automatically: your own space
   in ThingsBoard with a starter device and a dashboard.

**One login for everything.** The same sign-in works for the dashboard, the flow editor and the
notebooks — you'll never type a second password.

---

## 2. Add a device and get your code
1. On your home page, open **My devices** (or **Open my dashboard** to jump straight to charts).
2. You already have a **starter device**. To add more, click **Add device** and name it (up to 10).
3. Open the device to see its **Connection details**:
   - **MQTT host:** `chertiot.com` · **Port:** `8883` (secure/TLS)
   - **Access token** — this is your device's username (keep it secret)
   - **Topic:** `v1/devices/me/telemetry`
4. Scroll to **Starter code** and download the file for your board — your token and the broker
   address are already filled in.

**Four ways to send data:**
| You have… | Use |
|---|---|
| An **ESP32** | ESP32 — Arduino (`chertiot_starter.ino`) or MicroPython |
| A **Raspberry Pi** | Raspberry Pi — Python |
| **No hardware** | Browser (JavaScript) — send test data from a web page |

Add your Wi-Fi details to the downloaded file, flash it to your board, and power it on.

---

## 3. Watch your data live
1. Click **Open my dashboard**. You'll land in your dashboard (no second login).
2. Your **Temperature** and **Humidity** charts update within seconds as your device publishes.
3. The **Latest telemetry** table shows the newest values; the **Devices** panel shows what's online.

Made a mess of the dashboard? Click **Reset starter dashboard** to bring back the clean version —
your devices and data are untouched.

**Lost or leaked your token?** Open the device and click **Issue new token** — the old one stops
working immediately.

---

## 4. Build logic without code — Flows
1. Open **Flows** (`/flows`) and click **Start my Node-RED**. Your private editor (**CHERT Node**)
   starts in a few seconds.
2. Click **Open the editor**. Drag nodes onto the canvas, wire them together, and **Deploy**.
3. Your ThingsBoard connection is already provided as `TB_MQTT_HOST`, `TB_MQTT_PORT` and
   `TB_ACCESS_TOKEN`, so you can react to your device data, trigger actions, or call other services —
   no programming required.

Your editor is **yours alone** — no one else can open it. It pauses after 30 minutes idle and resumes
when you come back.

---

## 5. Analyse with Python — Lab
1. Open **<https://lab.chertiot.com>** and sign in (same account).
2. Start your server and open an example notebook.
3. Use the built-in **`chertiot.py`** helper to pull **your** telemetry into pandas and plot it with
   matplotlib. You can only see your own data.

---

## 6. Get notified — Alerts
1. Open **Alerts** (`/alerts`) → **New alert**.
2. Pick a device, a **telemetry key** (e.g. `temperature`), a condition (e.g. `>`) and a **threshold**.
3. Choose an action: a dashboard **alarm**, an **email**, or a **webhook**.
4. When a reading crosses your threshold, the alarm fires. You can also **export** your telemetry as
   CSV or JSON for a time range.

---

## 7. Go long-range — LoRaWAN (optional)
1. Open **LoRaWAN** (`/lora`) → **Register a LoRa device**. You'll get **OTAA credentials**
   (DevEUI + AppKey).
2. Point your LoRaWAN gateway (Semtech UDP packet forwarder) at **`chertiot.com:1700/udp`**, EU868 —
   full steps are in the [gateway guide](https://chertiot.com/docs/guides/lorawan/).
3. Uplinks from your LoRa device appear on the **same dashboard** as your Wi-Fi devices.

---

## 8. Good to know
- **Limits:** up to 10 devices; about 10 messages/second per device; telemetry is kept for 90 days.
  These keep the shared lab fair — if you flood, your device is throttled, but no one else is affected.
- **Security:** connect only over `8883` (TLS). Treat your access token like a password.
- **Privacy:** we store your email, your devices' telemetry (90 days) and an audit log (30 days) —
  nothing else. See the [Privacy](https://chertiot.com/docs/policies/privacy/) and
  [Fair use](https://chertiot.com/docs/policies/fair-use/) pages.
- **Language:** toggle **English / العربية** anytime; the site fully supports right-to-left Arabic.
- **Status:** check **<https://status.chertiot.com>** if something looks down.
- **Sign out:** use **Sign out** to end your session completely.

---

## 9. Quick troubleshooting
| Problem | Try this |
|---|---|
| No data on the dashboard | Confirm the device is powered and on Wi-Fi; check the token and that the port is **8883**; the topic must be `v1/devices/me/telemetry`. |
| "User account is not active" on the ThingsBoard page | Don't type a password there — click **"Sign in with CHERT IoT"** (you log in through your CHERT account). |
| Can't add another device | You've hit the 10-device limit — delete one you don't need. |
| Flow editor says "reconnecting" | Give it a moment after **Start**; reopen the editor. |
| Forgot your password | Use **"Forgot your password?"** on the sign-in page. |

---

**Start here → <https://chertiot.com/signup>** and read the full docs at
**<https://chertiot.com/docs/>**. Happy building! 🛰️
