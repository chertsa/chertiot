"""Student threshold alerts (M3.4): rendered as a rule chain in the student's OWN tenant.

The chain replicates the root chain's storage spine (type switch → save timeseries/attributes),
then per rule: a TBEL filter on device+key+threshold → create alarm (always) and optionally
email (TB system SMTP) or webhook. It becomes the tenant's default-device-profile rule chain, so
every device message flows through it — students keep full edit rights over it (their tenant)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.tb_client import TbClient

if TYPE_CHECKING:
    from app.models import AlertRule

CHAIN_NAME = "chertiot-alerts"
OPS = {">": ">", "<": "<", ">=": ">=", "<=": "<=", "==": "=="}


def _node(node_type: str, name: str, config: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "type": node_type,
        "name": name,
        "configuration": config,
        "configurationVersion": 0,
        "debugSettings": None,
        "singletonMode": False,
        "additionalInfo": {"layoutX": 200 + 180 * (index % 4), "layoutY": 100 + 120 * (index // 4)},
    }


def _filter_script(rule: AlertRule) -> str:
    op = OPS.get(rule.op, ">")
    return (
        f"return metadata.deviceName == '{rule.device_name}' "
        f"&& msg.{rule.key} != null && msg.{rule.key} {op} {rule.threshold};"
    )


def build_metadata(rule_chain_id: str, rules: list[AlertRule]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    connections: list[dict[str, Any]] = []
    nodes.append(
        _node(
            "org.thingsboard.rule.engine.filter.TbMsgTypeSwitchNode",
            "Message Type Switch",
            {"version": 0},
            0,
        )
    )
    nodes.append(
        _node(
            "org.thingsboard.rule.engine.telemetry.TbMsgTimeseriesNode",
            "Save Timeseries",
            {"defaultTTL": 0},
            1,
        )
    )
    nodes.append(
        _node(
            "org.thingsboard.rule.engine.telemetry.TbMsgAttributesNode",
            "Save Client Attributes",
            {"scope": "CLIENT_SCOPE"},
            2,
        )
    )
    connections.append({"fromIndex": 0, "toIndex": 1, "type": "Post telemetry"})
    connections.append({"fromIndex": 0, "toIndex": 2, "type": "Post attributes"})

    for rule in rules:
        f_idx = len(nodes)
        nodes.append(
            _node(
                "org.thingsboard.rule.engine.filter.TbJsFilterNode",
                f"if {rule.device_name}.{rule.key} {rule.op} {rule.threshold}",
                {"scriptLang": "TBEL", "tbelScript": _filter_script(rule), "jsScript": ""},
                f_idx,
            )
        )
        connections.append({"fromIndex": 1, "toIndex": f_idx, "type": "Success"})
        a_idx = len(nodes)
        nodes.append(
            _node(
                "org.thingsboard.rule.engine.action.TbCreateAlarmNode",
                f"alarm {rule.key} {rule.op} {rule.threshold}",
                {
                    "alarmType": f"chertiot:{rule.key} {rule.op} {rule.threshold}",
                    "severity": "WARNING",
                    "propagate": False,
                    "useMessageAlarmData": False,
                    "overwriteAlarmDetails": False,
                    "dynamicSeverity": False,
                    "scriptLang": "TBEL",
                    "alarmDetailsBuildTbel": "return {};",
                    "alarmDetailsBuildJs": "",
                },
                a_idx,
            )
        )
        connections.append({"fromIndex": f_idx, "toIndex": a_idx, "type": "True"})
        if rule.action == "email" and rule.target:
            m_idx = len(nodes)
            nodes.append(
                _node(
                    "org.thingsboard.rule.engine.mail.TbMsgToEmailNode",
                    f"compose mail {rule.key}",
                    {
                        "fromTemplate": "no-reply@chertiot.com",
                        "toTemplate": rule.target,
                        "ccTemplate": None,
                        "bccTemplate": None,
                        "subjectTemplate": (
                            f"CHERT IoT alert: {rule.device_name} "
                            f"{rule.key} {rule.op} {rule.threshold}"
                        ),
                        "bodyTemplate": "Device ${deviceName}: "
                        + rule.key
                        + " = $["
                        + rule.key
                        + "]",
                        "isHtmlTemplate": "false",
                        "mailBodyType": "false",
                    },
                    m_idx,
                )
            )
            s_idx = len(nodes)
            nodes.append(
                _node(
                    "org.thingsboard.rule.engine.mail.TbSendEmailNode",
                    "send mail",
                    {"useSystemSmtpSettings": True},
                    s_idx,
                )
            )
            connections.append({"fromIndex": a_idx, "toIndex": m_idx, "type": "Created"})
            connections.append({"fromIndex": m_idx, "toIndex": s_idx, "type": "Success"})
        elif rule.action == "webhook" and rule.target:
            w_idx = len(nodes)
            nodes.append(
                _node(
                    "org.thingsboard.rule.engine.rest.TbRestApiCallNode",
                    f"webhook {rule.key}",
                    {
                        "restEndpointUrlPattern": rule.target,
                        "requestMethod": "POST",
                        "headers": {"Content-Type": "application/json"},
                        "useSimpleClientHttpFactory": False,
                        "readTimeoutMs": 10000,
                        "maxParallelRequestsCount": 5,
                        "parseToPlainText": False,
                        "enableProxy": False,
                        "ignoreRequestBody": False,
                        "credentials": {"type": "anonymous"},
                    },
                    w_idx,
                )
            )
            connections.append({"fromIndex": a_idx, "toIndex": w_idx, "type": "Created"})

    return {
        "ruleChainId": {"entityType": "RULE_CHAIN", "id": rule_chain_id},
        "firstNodeIndex": 0,
        "nodes": nodes,
        "connections": connections or None,
        "ruleChainConnections": None,
    }


def apply_rules(student: TbClient, rules: list[AlertRule]) -> str:
    """Create/update the student's alert chain and make it the default device profile's chain."""
    chain = student.find_rule_chain(CHAIN_NAME)
    if chain is None:
        chain = student.save_rule_chain({"name": CHAIN_NAME, "type": "CORE", "debugMode": False})
    chain_id = chain["id"]["id"]
    student.save_rule_chain_metadata(build_metadata(chain_id, rules))
    profile_info = student.get_default_device_profile()
    profile = student.get_device_profile(profile_info["id"]["id"])
    if (profile.get("defaultRuleChainId") or {}).get("id") != chain_id:
        profile["defaultRuleChainId"] = {"entityType": "RULE_CHAIN", "id": chain_id}
        student.save_device_profile(profile)
    return str(chain_id)
