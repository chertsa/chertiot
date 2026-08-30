from app.config import Settings
from app.snippets import TRACKS, placeholders, render


def settings() -> Settings:
    return Settings(
        portal_secret_key="t",
        portal_database_url="sqlite://",
        domain="chertiot.com",
        mqtt_host="chertiot.com",
        mqtt_port=8883,
        tb_public_url="https://app.chertiot.com",
    )


def test_every_track_renders_with_values_and_no_placeholders_left() -> None:
    for key in TRACKS:
        out = render(key, "kitchen-sensor", "TOKEN123", settings())
        for name in placeholders("d", "t", settings()):
            assert "{{" + name + "}}" not in out, (key, name)
        assert "TOKEN123" in out and "kitchen-sensor" in out
        assert "chertiot.com" in out


def test_mqtt_tracks_use_tls_port_and_browser_uses_http() -> None:
    assert "8883" in render("esp32-arduino", "d", "t", settings())
    assert "https://app.chertiot.com/api/v1/t/telemetry" in render(
        "browser-js", "d", "t", settings()
    )
