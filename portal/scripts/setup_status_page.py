"""Configure Uptime Kuma via the maintained uptime-kuma-api client: admin (fresh setup), a monitor
for every public service, and a published public status page. Idempotent.

    KUMA_URL=http://uptime-kuma:3001 KUMA_PASSWORD=... DOMAIN=chertiot.com \
        uv run python -m scripts.setup_status_page
"""

from __future__ import annotations

import os
import sys

from uptime_kuma_api import MonitorType, UptimeKumaApi

KUMA = os.environ.get("KUMA_URL", "http://uptime-kuma:3001")
USER = os.environ.get("KUMA_ADMIN", "chertiotadmin")
PASSWORD = os.environ["KUMA_PASSWORD"]
DOMAIN = os.environ["DOMAIN"]
SLUG = "chert-iot"

MONITORS = [
    ("Portal", f"https://{DOMAIN}/healthz"),
    ("Dashboards (ThingsBoard)", f"https://app.{DOMAIN}/login"),
    ("Sign-in (Keycloak)", f"https://auth.{DOMAIN}/realms/chertiot"),
    ("Docs", f"https://{DOMAIN}/docs/"),
    ("Notebooks (JupyterHub)", f"https://lab.{DOMAIN}/hub/login"),
    ("Flows (Node-RED)", f"https://flows.{DOMAIN}"),
]


def main() -> int:
    api = UptimeKumaApi(KUMA, timeout=30)
    try:
        if api.need_setup():
            api.setup(USER, PASSWORD)
            print("kuma: admin created")
        api.login(USER, PASSWORD)
        print("kuma: logged in")

        have = {m["name"]: m["id"] for m in api.get_monitors()}
        ids: list[int] = []
        for name, url in MONITORS:
            if name in have:
                ids.append(have[name])
                continue
            res = api.add_monitor(
                type=MonitorType.HTTP,
                name=name,
                url=url,
                interval=60,
                retryInterval=60,
                maxretries=2,
                accepted_statuscodes=["200-399"],
            )
            ids.append(res["monitorID"])
            print(f"kuma: monitor '{name}'")

        pages = {p["slug"] for p in api.get_status_pages()}
        if SLUG not in pages:
            api.add_status_page(SLUG, "CHERT IoT status")
            print("kuma: status page created")
        api.save_status_page(
            SLUG,
            title="CHERT IoT status",
            description="Live availability of the CHERT IoT platform.",
            publicGroupList=[{"name": "Platform", "monitorList": [{"id": i} for i in ids]}],
        )
        print(f"kuma: status page published with {len(ids)} monitors")
        return 0
    finally:
        api.disconnect()


if __name__ == "__main__":
    sys.exit(main())
