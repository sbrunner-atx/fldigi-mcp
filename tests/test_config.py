"""Claude Desktop passes a blank optional setting as the literal template string."""

from fldigi_mcp.config import Config


def test_unsubstituted_templates_are_unset(monkeypatch):
    monkeypatch.setenv("FLDIGI_HUNT_URL", "${user_config.hunt_url}")
    monkeypatch.setenv("FLDIGI_AUDIO_DEVICE", "iMic")
    monkeypatch.setenv("FLDIGI_CALLSIGN", "${user_config.callsign}")
    monkeypatch.setenv("FLDIGI_PORT", "${user_config.fldigi_port}")
    c = Config.from_env()
    assert c.hunt_url == ""
    assert c.audio_device == "iMic"
    assert c.callsign == "" and c.transmit_ready is False
    assert c.port == 7362
