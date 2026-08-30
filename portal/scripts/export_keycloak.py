"""Export the CHERT IoT realm (clients included, secrets masked by Keycloak) to keycloak/realm/."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from setup_keycloak import REALM, admin_client


def main() -> int:
    c = admin_client()
    params = {"exportClients": "true", "exportGroupsAndRoles": "true"}
    r = c.post(f"/{REALM}/partial-export", params=params)
    r.raise_for_status()
    out = Path(os.environ.get("KC_EXPORT_DIR", "keycloak/realm")) / f"{REALM}-realm.json"
    out.write_text(json.dumps(r.json(), indent=2, sort_keys=True) + "\n")
    print(f"exported to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
