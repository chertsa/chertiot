import importlib

from scripts import lora_bridge


def test_telemetry_from_decoded_object() -> None:
    payload = {"object": {"temperature": 21.5, "battery": 95, "note": "ok", "nested": {"x": 1}}}
    t = lora_bridge._telemetry_from_uplink(payload)
    assert t == {"temperature": 21.5, "battery": 95, "note": "ok"}  # scalar-only, nested dropped


def test_telemetry_from_raw_and_rxinfo() -> None:
    payload = {"data": "AQI=", "fPort": 2, "rxInfo": [{"rssi": -92, "snr": 7.5}]}
    t = lora_bridge._telemetry_from_uplink(payload)
    assert t["fPort"] == 2 and t["raw_hex"] == "0102" and t["rssi"] == -92 and t["snr"] == 7.5


def test_forward_ignores_unmapped_deveui(monkeypatch) -> None:  # noqa: ANN001
    calls = []
    monkeypatch.setattr(lora_bridge, "sysadmin_client", lambda: calls.append("tb"))

    class FakeSession:
        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *a):  # noqa: ANN002, ANN204
            return False

        def get(self, model, key):  # noqa: ANN001, ANN202
            return None

    monkeypatch.setattr(lora_bridge, "session_factory", lambda: (lambda: FakeSession()))
    lora_bridge._forward("deadbeef00000000", {"temperature": 1})
    assert calls == []  # never reached TB for an unmapped DevEUI


def test_new_ids_shapes() -> None:
    cs = importlib.import_module("app.chirpstack")
    assert len(cs.new_dev_eui()) == 16 and len(cs.new_app_key()) == 32
    assert all(ch in "0123456789abcdef" for ch in cs.new_dev_eui())
