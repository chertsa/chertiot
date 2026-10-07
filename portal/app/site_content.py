"""Marketing-site content: the IoT project lifecycle and the layered CHERT architecture.

One source of truth for the landing page — the template renders it server-side (so the page reads
fully without JS) and the same structure is embedded as JSON for static/site.js, which draws the
data-flow connectors, animates the journeys and drives the lifecycle wheel. Every string goes
through the request-scoped gettext `_` so the page follows the visitor's language.

Component ids are referenced by LIFECYCLE[*].components, EDGES and JOURNEYS[*].steps; the unit test
tests/unit/test_site_content.py keeps those references consistent.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

Gettext = Callable[[str], str]


def layers(_: Gettext) -> list[dict[str, Any]]:
    """IoT reference layers, top (devices) to bottom (applications), plus two cross-cutting
    rails."""
    return [
        {
            "id": "devices",
            "kind": "band",
            "n": "01",
            "title": _("Devices & sensing"),
            "desc": _("Sensors and microcontrollers that measure the physical world."),
            "nodes": [
                ("esp32", "cpu", "ESP32", _("Wi-Fi microcontroller")),
                ("rpi", "server", "Raspberry Pi", _("Linux single-board computer")),
                ("browser", "monitor", _("Browser device"), _("No hardware needed")),
                ("lorasensor", "radio", _("LoRa sensors"), _("Long-range, low-power")),
            ],
        },
        {
            "id": "connect",
            "kind": "band",
            "n": "02",
            "title": _("Connectivity & edge"),
            "desc": _("Secure transport from the field into the platform."),
            "nodes": [
                ("caddy", "shield", "Caddy", _("TLS edge · MQTTS :8883")),
                ("loragw", "wifi", _("LoRa gateway"), _("Your radio gateway")),
                ("gwbridge", "link", _("Gateway Bridge"), _("ChirpStack UDP → MQTT")),
                ("mosquitto", "message", "Mosquitto", _("Internal LoRa broker")),
                ("chirpstack", "radio", "ChirpStack", _("LoRaWAN network server")),
                ("lorabridge", "bolt", "lora-bridge", _("LoRa uplinks → ThingsBoard")),
            ],
        },
        {
            "id": "platform",
            "kind": "band",
            "n": "03",
            "title": _("Platform & data"),
            "desc": _("Device registry, rule engine, alarms and durable storage."),
            "nodes": [
                ("thingsboard", "layers", "ThingsBoard", _("Devices · rules · alarms")),
                ("postgres", "database", "PostgreSQL", _("Telemetry & state")),
                ("redis", "bolt", "Redis", _("LoRaWAN session cache")),
            ],
        },
        {
            "id": "apps",
            "kind": "band",
            "n": "04",
            "title": _("Applications & insight"),
            "desc": _("Where people see, automate and analyse their data."),
            "nodes": [
                ("portal", "grid", _("CHERT portal"), _("Projects · devices · monitoring")),
                ("dashboards", "chart", _("Dashboards"), _("Live widgets & reports")),
                ("nodered", "sitemap", "Node-RED", _("No-code automation")),
                ("jupyter", "flask", "JupyterLab", _("Python notebooks")),
                ("docs", "book", _("Docs"), _("Guides & firmware")),
            ],
        },
        {
            "id": "security",
            "kind": "rail",
            "n": "S",
            "title": _("Security & identity"),
            "desc": _("One identity, isolated projects."),
            "nodes": [
                ("keycloak", "key", "Keycloak", _("Single sign-on")),
                ("isolation", "lock", _("Project isolation"), _("One tenant per project")),
                ("sandbox", "box", _("Per-user sandbox"), _("Capped containers")),
            ],
        },
        {
            "id": "ops",
            "kind": "rail",
            "n": "O",
            "title": _("Operations & observability"),
            "desc": _("Keeping the platform healthy."),
            "nodes": [
                ("prometheus", "activity", "Prometheus", _("Metrics collection")),
                ("grafana", "gauge", "Grafana", _("Platform monitor")),
                ("alertmanager", "bell", "Alertmanager", _("Operator alerts")),
                ("kuma", "pulse", "Uptime Kuma", _("Public status page")),
            ],
        },
    ]


def node_details(_: Gettext) -> dict[str, str]:
    """Longer explanation per component, shown in the diagram's detail panel."""
    return {
        "esp32": _(
            "The classic IoT board. CHERT generates ready-to-flash starter firmware with your "
            "device's access token and the broker address already filled in."
        ),
        "rpi": _(
            "A full Linux computer at the edge. Starter Python code publishes readings over MQTT "
            "or HTTP — ideal for gateways, cameras and heavier sensors."
        ),
        "browser": _(
            "No hardware yet? A browser page acts as a virtual device and sends real telemetry, "
            "so you can build dashboards and rules on day one."
        ),
        "lorasensor": _(
            "Battery-powered sensors that reach kilometres over LoRaWAN, for agriculture, "
            "metering and environmental monitoring."
        ),
        "caddy": _(
            "The single front door. It serves every site over HTTPS with automatic certificates "
            "and terminates MQTTS on port 8883 before handing messages to ThingsBoard."
        ),
        "loragw": _(
            "A LoRaWAN gateway receives radio uplinks from nearby sensors and forwards them over "
            "the internet to the platform."
        ),
        "gwbridge": _(
            "ChirpStack Gateway Bridge converts the gateway's packet-forwarder protocol into MQTT "
            "messages the network server understands."
        ),
        "mosquitto": _(
            "An internal MQTT broker that carries LoRaWAN traffic between the gateway bridge, "
            "ChirpStack and lora-bridge. It is never exposed to the internet."
        ),
        "chirpstack": _(
            "The LoRaWAN network server: device activation, de-duplication, decryption and "
            "decoding of uplink payloads."
        ),
        "lorabridge": _(
            "A small CHERT service that subscribes to ChirpStack's decoded uplinks and delivers "
            "them to the right device in the right project on ThingsBoard."
        ),
        "thingsboard": _(
            "The IoT core. Each CHERT project is its own ThingsBoard tenant with its own devices, "
            "rule chains, alarms and dashboards — nothing is shared between projects."
        ),
        "postgres": _(
            "Every reading, attribute, alarm and project record is stored durably in PostgreSQL "
            "on your own server."
        ),
        "redis": _("Fast in-memory state that ChirpStack uses for LoRaWAN device sessions."),
        "portal": _(
            "Your home base: create projects, invite your team, register devices, copy starter "
            "code, watch live monitoring and print lifecycle reports."
        ),
        "dashboards": _(
            "Every project starts with a ready dashboard. Add charts, gauges, maps and tables "
            "that update in real time as readings arrive."
        ),
        "nodered": _(
            "A personal Node-RED editor per project, already connected to ThingsBoard. Wire "
            "devices to logic, notifications and webhooks without writing code."
        ),
        "jupyter": _(
            "A JupyterLab server per project with pandas and matplotlib, scoped to your own "
            "telemetry — for cleaning, analysing and modelling your data."
        ),
        "docs": _(
            "Step-by-step guides in English and Arabic, from flashing your first board to "
            "building rule chains and notebooks."
        ),
        "keycloak": _(
            "One CHERT account signs you in to the portal, ThingsBoard, Node-RED and JupyterLab. "
            "Email verification and sessions are handled centrally."
        ),
        "isolation": _(
            "A project is an isolated tenant. Members see only the projects they belong to, and "
            "destructive actions stay with the owner."
        ),
        "sandbox": _(
            "Node-RED and notebook servers run as separate containers per user, with capped CPU "
            "and memory so one experiment can't affect anyone else."
        ),
        "prometheus": _(
            "Scrapes health metrics from every server, container and database on the platform."
        ),
        "grafana": _(
            "The platform monitor for instructors and administrators: device traffic, resource "
            "use and service health at a glance."
        ),
        "alertmanager": _(
            "Routes operator alerts when something on the platform needs attention — before "
            "users notice."
        ),
        "kuma": _("A public status page with live up/down checks for every public service."),
    }


def lifecycle(_: Gettext) -> list[dict[str, Any]]:
    """The IoT project lifecycle: nine stages that loop (operate → plan the next iteration)."""
    stages = [
        (
            "clipboard",
            _("Plan"),
            _("Define the goal and the team"),
            _(
                "Decide what to measure and why. Create a project in CHERT, invite members and "
                "agree who owns it."
            ),
            ["portal", "keycloak", "isolation"],
        ),
        (
            "rocket",
            _("Provision"),
            _("Get an isolated workspace"),
            _(
                "Creating a project provisions its own ThingsBoard tenant, a starter dashboard "
                "and a secure place for its data — in seconds."
            ),
            ["portal", "thingsboard", "postgres", "isolation"],
        ),
        (
            "cpu",
            _("Build devices"),
            _("Wire sensors and flash firmware"),
            _(
                "Register each device to get its access token, then flash ready-made starter "
                "code onto an ESP32, a Raspberry Pi or a browser device."
            ),
            ["portal", "esp32", "rpi", "browser", "lorasensor", "docs"],
        ),
        (
            "wifi",
            _("Connect"),
            _("Transmit securely"),
            _(
                "Devices publish over MQTTS, HTTPS or LoRaWAN. Traffic is encrypted end to end "
                "and authenticated per device."
            ),
            ["caddy", "loragw", "gwbridge", "mosquitto", "chirpstack", "lorabridge"],
        ),
        (
            "database",
            _("Ingest & store"),
            _("Process every reading"),
            _(
                "The rule engine validates, enriches and routes each message, then stores it as "
                "time-series data you can query later."
            ),
            ["thingsboard", "postgres", "redis"],
        ),
        (
            "chart",
            _("Visualise"),
            _("See what is happening"),
            _(
                "Live dashboards, per-device monitoring with last-seen status, and 24-hour "
                "trends in the portal."
            ),
            ["dashboards", "portal", "thingsboard"],
        ),
        (
            "bell",
            _("Automate & alert"),
            _("React automatically"),
            _(
                "Set thresholds that raise alarms, then send emails, call webhooks or trigger "
                "actions with Node-RED flows."
            ),
            ["thingsboard", "nodered", "sandbox"],
        ),
        (
            "flask",
            _("Analyse"),
            _("Turn data into insight"),
            _(
                "Pull your history into a JupyterLab notebook, clean it with pandas, chart it "
                "with matplotlib and share findings."
            ),
            ["jupyter", "sandbox", "thingsboard"],
        ),
        (
            "refresh",
            _("Operate & evolve"),
            _("Keep it running, then improve"),
            _(
                "Watch platform health, rotate device tokens, print lifecycle reports and feed "
                "what you learned into the next iteration."
            ),
            ["prometheus", "grafana", "alertmanager", "kuma", "portal"],
        ),
    ]
    out = []
    count = len(stages)
    for i, (icon, title, tagline, desc, comps) in enumerate(stages):
        # Position on the lifecycle wheel (percent of the square), starting at 12 o'clock.
        angle = -math.pi / 2 + i * 2 * math.pi / count
        out.append(
            {
                "n": i + 1,
                "icon": icon,
                "title": title,
                "tagline": tagline,
                "desc": desc,
                "components": comps,
                "x": round(50 + 42 * math.cos(angle), 2),
                "y": round(50 + 42 * math.sin(angle), 2),
            }
        )
    return out


# Data-flow connectors drawn between diagram nodes (source → target).
EDGES: list[tuple[str, str]] = [
    ("esp32", "caddy"),
    ("rpi", "caddy"),
    ("browser", "caddy"),
    ("lorasensor", "loragw"),
    ("loragw", "gwbridge"),
    ("gwbridge", "mosquitto"),
    ("mosquitto", "chirpstack"),
    ("chirpstack", "lorabridge"),
    ("chirpstack", "redis"),
    ("lorabridge", "thingsboard"),
    ("caddy", "thingsboard"),
    ("thingsboard", "postgres"),
    ("thingsboard", "dashboards"),
    ("thingsboard", "portal"),
    ("thingsboard", "nodered"),
    ("thingsboard", "jupyter"),
    ("keycloak", "portal"),
    ("keycloak", "thingsboard"),
    ("sandbox", "nodered"),
    ("sandbox", "jupyter"),
    ("prometheus", "grafana"),
    ("prometheus", "alertmanager"),
]


def journeys(_: Gettext) -> list[dict[str, Any]]:
    """Animated walk-throughs: each step lights a component and explains what happens there."""
    return [
        {
            "id": "reading",
            "label": _("Follow a reading"),
            "steps": [
                ("esp32", _("An ESP32 reads its temperature sensor and publishes JSON over MQTT.")),
                ("caddy", _("Caddy accepts the encrypted MQTTS connection on port 8883.")),
                (
                    "thingsboard",
                    _("ThingsBoard checks the device token and runs your project's rule chain."),
                ),
                ("postgres", _("The reading is stored as time-series in PostgreSQL.")),
                ("dashboards", _("Your dashboard widgets update within a second.")),
                ("portal", _("The portal's Monitoring view shows last-seen and 24-hour trends.")),
                ("nodered", _("A Node-RED flow reacts — for example, sending a notification.")),
                ("jupyter", _("Later, a notebook loads the history into pandas for analysis.")),
            ],
        },
        {
            "id": "lora",
            "label": _("LoRaWAN uplink"),
            "steps": [
                ("lorasensor", _("A battery sensor wakes up and transmits a LoRa radio packet.")),
                ("loragw", _("Your gateway receives it, kilometres away, and forwards it.")),
                ("gwbridge", _("The Gateway Bridge turns the packet into an MQTT message.")),
                ("mosquitto", _("The internal Mosquitto broker carries it inside the platform.")),
                ("chirpstack", _("ChirpStack de-duplicates, decrypts and decodes the payload.")),
                (
                    "lorabridge",
                    _("lora-bridge delivers it to the matching device in your project."),
                ),
                ("thingsboard", _("ThingsBoard treats it like any other reading.")),
                ("dashboards", _("It appears on the same dashboard as your Wi-Fi devices.")),
            ],
        },
        {
            "id": "signin",
            "label": _("Single sign-on"),
            "steps": [
                ("portal", _("You open CHERT and choose Sign in.")),
                ("keycloak", _("Keycloak verifies your identity once, for every tool.")),
                ("isolation", _("The portal checks which projects you belong to and your role.")),
                ("thingsboard", _("ThingsBoard opens with a session limited to that project.")),
                ("sandbox", _("Your own Node-RED and notebook containers start on demand.")),
                ("jupyter", _("JupyterLab opens through the same identity — no extra password.")),
            ],
        },
        {
            "id": "ops",
            "label": _("Platform health"),
            "steps": [
                (
                    "prometheus",
                    _("Prometheus scrapes metrics from every service every few seconds."),
                ),
                ("grafana", _("Grafana turns them into the live platform monitor.")),
                ("alertmanager", _("If a threshold is crossed, Alertmanager notifies operators.")),
                ("kuma", _("The public status page shows everyone what is up.")),
            ],
        },
    ]


def site_content(_: Gettext) -> dict[str, Any]:
    """Everything the landing page needs, in the visitor's language."""
    lyr = layers(_)
    details = node_details(_)
    stages = lifecycle(_)
    titles = {nid: name for layer in lyr for (nid, _icon, name, _role) in layer["nodes"]}
    layer_of = {nid: layer["title"] for layer in lyr for (nid, *_rest) in layer["nodes"]}
    roles = {nid: role for layer in lyr for (nid, _icon, _name, role) in layer["nodes"]}
    stages_of: dict[str, list[int]] = {nid: [] for nid in titles}
    for st in stages:
        for nid in st["components"]:
            stages_of[nid].append(st["n"])
    jrn = journeys(_)
    payload = {
        "nodes": {
            nid: {
                "name": titles[nid],
                "role": roles[nid],
                "layer": layer_of[nid],
                "detail": details[nid],
                "stages": stages_of[nid],
            }
            for nid in titles
        },
        "edges": EDGES,
        "journeys": {
            j["id"]: [{"node": nid, "text": text} for nid, text in j["steps"]] for j in jrn
        },
        "stageTitles": {st["n"]: st["title"] for st in stages},
    }
    return {
        "layers": lyr,
        "lifecycle": stages,
        "journeys": jrn,
        "payload": payload,
        "component_count": len(titles),
    }
