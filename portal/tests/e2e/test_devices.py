"""M1.2 acceptance: a student adds a second device from the portal, downloads the rendered
starter snippet, runs it (Raspberry Pi track, real Python) and sees telemetry on that device —
no ThingsBoard admin screens involved. Then rename, token revoke, delete."""

import os
import re
import subprocess
import sys
import tempfile
import time
import uuid

import paho.mqtt.client as mqtt

from app.tb_client import TbClient
from tests.e2e.conftest import make_client
from tests.e2e.test_signup_flow import follow, keycloak_login, mailpit_link

TB_ADMIN = os.environ.get("TB_ADMIN_URL", "http://127.0.0.1:18080")
PORTAL = os.environ.get("PORTAL_PUBLIC_URL", "http://localhost")


def _signup_and_login(s, email: str, password: str) -> None:  # type: ignore[no-untyped-def]
    r = s.post(
        f"{PORTAL}/signup",
        data={
            "email": email,
            "password": password,
            "password_confirm": password,
            "age_attested": "yes",
        },
    )
    assert r.status_code == 303
    link = mailpit_link(
        email, r"https?://auth\.localhost/realms/chertiot/login-actions/action-token[^\s\"<]+"
    )
    r = follow(s, s.get(link))
    if "Click here to proceed" in r.text:
        proceed = re.findall(r'href="(http[^"]*action-token[^"]*)"', r.text)[-1]
        r = follow(s, s.get(proceed.replace("&amp;", "&")))
    if "Back to Application" in r.text:
        back = re.findall(r'href="(http[^"]+/auth/verified[^"]*)"', r.text)[-1]
        follow(s, s.get(back.replace("&amp;", "&")))
    r = keycloak_login(s, f"{PORTAL}/login", email, password)
    assert r.status_code == 303 and r.headers["location"] == "/home"


def test_second_device_from_snippet_to_telemetry(kc_url: str, tb_url: str) -> None:
    sysadmin = TbClient(
        TB_ADMIN,
        username=os.environ["TB_SYSADMIN_EMAIL"],
        password=os.environ["TB_SYSADMIN_PASSWORD"],
    )
    email = f"e2e-dev-{uuid.uuid4().hex[:8]}@test.chertiot.local"
    password = "correct-horse-battery-staple"  # noqa: S105
    with make_client(follow_redirects=False) as s:
        _signup_and_login(s, email, password)

        # Add a second device.
        r = s.post(f"{PORTAL}/devices", data={"name": "kitchen-sensor"})
        assert r.status_code == 303 and r.headers["location"].startswith("/devices/"), r.text[:300]
        device_url = f"{PORTAL}{r.headers['location']}"
        r = s.get(device_url)
        assert r.status_code == 200 and "kitchen-sensor" in r.text
        token = re.search(r"data-device-token>([^<]+)<", r.text)
        assert token
        token = token.group(1)
        r = s.get(f"{PORTAL}/devices")
        assert (
            "kitchen-sensor" in r.text
            and "my-first-device" in r.text
            and "2 / 10" in r.text and "devices used" in r.text
        )

        # Download the Raspberry Pi snippet and run it for real against the local broker.
        r = s.get(f"{device_url}/snippet/rpi-python")
        assert r.status_code == 200 and token in r.text
        assert "{{ACCESS_TOKEN}}" not in r.text and "{{MQTT_HOST}}" not in r.text
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(r.text)
            script = f.name
        proc = subprocess.Popen(  # noqa: S603 — runs the snippet we just rendered, with our interpreter
            [sys.executable, "-u", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        time.sleep(8)
        proc.terminate()
        out = proc.communicate(timeout=10)[0].decode()
        assert "temperature" in out, out[-400:]

        # Telemetry landed on *that* device.
        tenant = sysadmin.find_tenant(email)
        assert tenant and tenant.id
        user = sysadmin.find_tenant_user(tenant.id.id, email)
        assert user and user.id
        student = sysadmin.impersonate(user.id.id)
        device = student.find_device("kitchen-sensor")
        assert device and device.id
        latest = {}
        for _ in range(20):
            latest = student.latest_timeseries(device.id.id, ["temperature"])
            if latest.get("temperature"):
                break
            time.sleep(0.5)
        assert latest.get("temperature"), "no telemetry from the snippet"

        # Rename → revoke (old token rejected) → delete.
        r = s.post(f"{device_url}/rename", data={"name": "balcony-sensor"})
        assert r.status_code == 303 and student.get_device(device.id.id).name == "balcony-sensor"
        r = s.post(f"{device_url}/revoke")
        assert r.status_code == 303
        new_token = student.get_device_credentials(device.id.id).credentials_id
        assert new_token != token
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        c.username_pw_set(token)
        rc = {"code": None}
        c.on_connect = lambda client, userdata, flags, reason, props=None: rc.__setitem__(
            "code", reason
        )
        c.connect(
            os.environ.get("MQTT_HOST", "127.0.0.1"), int(os.environ.get("MQTT_PORT", "1883"))
        )
        c.loop_start()
        time.sleep(2)
        c.loop_stop()
        assert rc["code"] is None or rc["code"].is_failure, f"old token still accepted: {rc}"
        r = s.post(f"{device_url}/delete")
        assert r.status_code == 303 and student.find_device("balcony-sensor") is None
        student.close()
        sysadmin.delete_tenant(tenant.id.id)
    sysadmin.close()
