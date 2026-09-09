"""Every method of the supported fldigi release must be reachable through a named
operation, and every operation's argument kind must agree with fldigi's own
signature. The catalog is the ``fldigi.list`` output shipped in
``src/fldigi_mcp/data/fldigi_methods.json`` (4.2.13, identical to 4.2.11).

If fldigi adds a method, regenerate the catalog (see CONTRIBUTING.md) and this
test names what still has to be wired.
"""

from __future__ import annotations

import json
from importlib import resources

import pytest

from fldigi_mcp import methods

CATALOG = json.loads(resources.files("fldigi_mcp").joinpath("data/fldigi_methods.json").read_text())
LIVE = {m["name"]: m for m in CATALOG["methods"]}

# fldigi signature letters -> the connector's kind for the argument part
_ARG_KIND = {
    "n": None,
    "i": "i",
    "d": "d",
    "b": "b",
    "s": "s",
    "A": "A",
    "6": "6",
    "ii": "ii",
    "si": "si",
}

# Where the live build disagrees with its own fldigi.list signature (field-verified
# on 4.2.13, 9 Sep 2026): method -> the argument kind that actually works.
SIGNATURE_OVERRIDES = {
    "main.get_tx_timing": "6",  # declared n:s; rejects str, accepts base64, returns a string
    "main.get_char_timing": "6",  # declared n:i; rejects int, accepts base64, returns a string
}


def _reachable() -> dict[str, str]:
    """method name -> how it is reached ("tool:operation" or "direct")."""
    out: dict[str, str] = {}
    for tool, opmap in methods.ALL_OPMAPS.items():
        for op, (method, _kind) in opmap.items():
            out.setdefault(method, f"{tool}:{op}")
    for f in methods.LOG_GET_FIELDS:
        out.setdefault(f"log.get_{f}", f"log:get {f}")
    for f in methods.LOG_SET_FIELDS:
        out.setdefault(f"log.set_{f}", f"log:set {f}")
    for m in methods.DIRECT_METHODS:
        out.setdefault(m, "direct")
    return out


def test_catalog_is_the_supported_release():
    assert CATALOG["fldigi_version"] == "4.2.13"
    assert len(LIVE) == 174


def test_every_catalog_method_is_reachable():
    reach = _reachable()
    missing = sorted(set(LIVE) - set(reach))
    assert not missing, f"catalog methods with no named operation: {missing}"


def test_no_operation_targets_an_unknown_method():
    reach = _reachable()
    unknown = sorted(set(reach) - set(LIVE))
    assert not unknown, f"operations that target methods fldigi 4.2.13 does not serve: {unknown}"


@pytest.mark.parametrize(
    "tool,op,method,kind",
    [(t, op, m, k) for t, om in methods.ALL_OPMAPS.items() for op, (m, k) in om.items()],
)
def test_operation_kind_matches_fldigi_signature(tool, op, method, kind):
    sig = LIVE[method]["signature"]
    args = sig.split(":", 1)[1]
    expected = SIGNATURE_OVERRIDES.get(method, _ARG_KIND.get(args, "?"))
    assert expected == kind, (
        f"{tool}:{op} -> {method} has kind {kind!r} but fldigi's signature is {sig!r}"
    )


def test_log_field_setters_and_getters_match_signatures():
    for f in methods.LOG_GET_FIELDS:
        assert LIVE[f"log.get_{f}"]["signature"] == "s:n"
    for f in methods.LOG_SET_FIELDS:
        assert LIVE[f"log.set_{f}"]["signature"] == "n:s"


def test_deprecated_methods_live_only_in_legacy():
    deprecated = {n for n, m in LIVE.items() if "DEPRECATED" in m["help"]}
    legacy = {m for (m, _k) in methods.LEGACY_OPS.values()}
    # main.get_frequency is deprecated but still the documented dial read; it stays in frequency
    assert deprecated - legacy - {"main.get_frequency"} == set()
    # main.flmsg_* are undocumented aliases of flmsg.* (same help text, older namespace)
    aliases = {
        "main.flmsg_online",
        "main.flmsg_available",
        "main.flmsg_transfer",
        "main.flmsg_squelch",
    }
    for m in legacy - aliases:
        assert "DEPRECATED" in LIVE[m]["help"], (
            f"{m} is in LEGACY_OPS but fldigi does not mark it deprecated"
        )
