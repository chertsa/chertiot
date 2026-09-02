from app.alerts import CHAIN_NAME, apply_rules, build_metadata
from app.models import AlertRule


def _rule(**kw):  # noqa: ANN003, ANN202
    base = {
        "user_id": "u",
        "device_name": "dev-1",
        "key": "temperature",
        "op": ">",
        "threshold": 30.0,
        "action": "alarm",
        "target": None,
    }
    base.update(kw)
    return AlertRule(**base)


def test_metadata_spine_and_rule_nodes() -> None:
    md = build_metadata(
        "rc-1",
        [
            _rule(),
            _rule(action="email", target="a@b.c"),
            _rule(action="webhook", target="https://h.example/x"),
        ],
    )
    types = [n["type"].rsplit(".", 1)[-1] for n in md["nodes"]]
    assert types[:3] == ["TbMsgTypeSwitchNode", "TbMsgTimeseriesNode", "TbMsgAttributesNode"]
    assert md["firstNodeIndex"] == 0
    assert types.count("TbJsFilterNode") == 3 and types.count("TbCreateAlarmNode") == 3
    assert types.count("TbSendEmailNode") == 1 and types.count("TbRestApiCallNode") == 1
    # storage spine wired from the type switch
    assert {"fromIndex": 0, "toIndex": 1, "type": "Post telemetry"} in md["connections"]
    # filters hang off successful save so alerts never precede persistence
    assert any(c["fromIndex"] == 1 and c["type"] == "Success" for c in md["connections"])
    script = md["nodes"][3]["configuration"]["tbelScript"]
    assert "dev-1" in script and "temperature" in script and "> 30.0" in script


def test_apply_rules_creates_chain_and_wires_profile() -> None:
    calls: list[str] = []

    class FakeTB:
        def find_rule_chain(self, name: str):  # noqa: ANN202
            assert name == CHAIN_NAME
            return None

        def save_rule_chain(self, rc):  # noqa: ANN001, ANN202
            calls.append("create")
            return {"id": {"id": "rc-9"}}

        def save_rule_chain_metadata(self, md):  # noqa: ANN001, ANN202
            calls.append("metadata")
            assert md["ruleChainId"]["id"] == "rc-9"
            return md

        def get_default_device_profile(self):  # noqa: ANN202
            return {"id": {"id": "dp-1"}}

        def get_device_profile(self, pid: str):  # noqa: ANN202
            return {"id": {"id": pid}, "name": "default"}

        def save_device_profile(self, p):  # noqa: ANN001, ANN202
            calls.append("profile:" + p["defaultRuleChainId"]["id"])
            return p

    chain_id = apply_rules(FakeTB(), [_rule()])  # type: ignore[arg-type]
    assert chain_id == "rc-9" and calls == ["create", "metadata", "profile:rc-9"]
