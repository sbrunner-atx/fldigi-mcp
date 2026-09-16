"""The browser tool targets methods that only a patched fldigi serves; they must stay
out of the stock coverage map and be well formed."""

from __future__ import annotations

import json
from importlib import resources

from fldigi_mcp import methods
from fldigi_mcp.methods import VALID_KINDS

CATALOG = json.loads(resources.files("fldigi_mcp").joinpath("data/fldigi_methods.json").read_text())
STOCK = {m["name"] for m in CATALOG["methods"]}


def test_browser_ops_are_patch_only():
    for _op, (method, kind) in methods.BROWSER_OPS.items():
        assert method.startswith("browser.")
        assert method not in STOCK, f"{method} is stock now: move it into ALL_OPMAPS"
        assert kind in VALID_KINDS


def test_patched_maps_are_not_in_the_stock_map():
    assert "browser" in methods.PATCHED_OPMAPS
    assert "browser" not in methods.ALL_OPMAPS


def test_patch_file_ships():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    patch = root / "patches" / "fldigi-4.2.13-browser-xmlrpc.patch"
    assert patch.is_file()
    text = patch.read_text()
    for name in ("browser.get_channels", "browser.clear", "api_text"):
        assert name in text
