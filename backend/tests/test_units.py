"""Unit tests for pure functions in main.py — no HTTP layer."""
import copy
import re

import pytest

from main import vary_amounts, pick_by_filename, pick_by_carrier, build_contestation_email, _validated_route, _validated_period
from scenarios import SCENARIOS

_AMT_RE = re.compile(r"^\d[\d\s]*\s*(USD|EUR)$")


# ── vary_amounts ──────────────────────────────────────────────────────────────

def test_vary_amounts_returns_deep_copy():
    original = copy.deepcopy(SCENARIOS[0])
    result = vary_amounts(SCENARIOS[0])
    # Original must not be mutated
    assert SCENARIOS[0]["lines"][0]["amount"] == original["lines"][0]["amount"]


def test_vary_amounts_preserves_currency():
    result = vary_amounts(SCENARIOS[1])
    for line in result["lines"]:
        assert _AMT_RE.match(line["amount"]), f"Bad amount: {line['amount']!r}"


def test_vary_amounts_stays_within_5_percent():
    for scenario in SCENARIOS:
        varied = vary_amounts(scenario)
        for orig, var in zip(scenario["lines"], varied["lines"]):
            m_o = re.match(r"([\d\s]+)\s*(USD|EUR)", orig["amount"])
            m_v = re.match(r"([\d\s]+)\s*(USD|EUR)", var["amount"])
            if m_o and m_v:
                orig_n = int(m_o.group(1).replace(" ", ""))
                var_n  = int(m_v.group(1).replace(" ", ""))
                assert abs(var_n - orig_n) <= orig_n * 0.06, (
                    f"Variation exceeds 5%: {orig_n} → {var_n}"
                )


def test_vary_amounts_preserves_non_amount_fields():
    result = vary_amounts(SCENARIOS[2])
    for orig, var in zip(SCENARIOS[2]["lines"], result["lines"]):
        assert orig["code"]    == var["code"]
        assert orig["status"]  == var["status"]
        assert orig["verdict"] == var["verdict"]


# ── pick_by_filename ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("filename, expected_carrier", [
    ("facture_msc_surestaries.pdf",  "MSC"),
    ("MSC_invoice.PDF",              "MSC"),
    ("facture_hapag_anomalies.pdf",  "Hapag-Lloyd"),
    ("multi_charges.pdf",            "Hapag-Lloyd"),
    ("facture_maersk_normale.pdf",   "Maersk"),
    ("facture_cmacgm_baf.pdf",       "CMA CGM"),
    ("cmacgm_2026.pdf",              "CMA CGM"),
])
def test_pick_by_filename(filename, expected_carrier):
    scenario = pick_by_filename(filename)
    assert scenario["carrier"] == expected_carrier


def test_pick_by_filename_unknown_is_deterministic():
    s1 = pick_by_filename("unknown_invoice.pdf")
    s2 = pick_by_filename("unknown_invoice.pdf")
    assert s1["id"] == s2["id"]


def test_pick_by_filename_unknown_is_valid_scenario():
    s = pick_by_filename("random_file_xyz.pdf")
    assert s in SCENARIOS


# ── pick_by_carrier ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("carrier, expected_carrier", [
    ("MSC",                     "MSC"),
    ("Mediterranean Shipping",  "MSC"),
    ("Hapag-Lloyd",             "Hapag-Lloyd"),
    ("HAPAG LLOYD",             "Hapag-Lloyd"),
    ("Maersk Line",             "Maersk"),
    ("MAERSK",                  "Maersk"),
    ("CMA CGM",                 "CMA CGM"),
    ("CMA CGM S.A.",            "CMA CGM"),
])
def test_pick_by_carrier(carrier, expected_carrier):
    scenario = pick_by_carrier(carrier)
    assert scenario is not None
    assert scenario["carrier"] == expected_carrier


def test_pick_by_carrier_unknown_returns_none():
    assert pick_by_carrier("Evergreen") is None
    assert pick_by_carrier("COSCO") is None
    assert pick_by_carrier("") is None


# ── build_contestation_email ──────────────────────────────────────────────────

def _make_scenario(statuses):
    lines = [
        {"code": f"LINE{i}", "desc": "desc", "amount": "100 USD", "status": s, "verdict": f"verdict {i}"}
        for i, s in enumerate(statuses)
    ]
    return {
        "carrier": "TestCarrier",
        "route": "A → B",
        "period": "Q1 2026",
        "anomalies_count": sum(1 for s in statuses if s != "ok"),
        "lines": lines,
        "recoverable": "300 USD",
    }


def test_email_contains_carrier():
    email = build_contestation_email(_make_scenario(["ok", "err"]))
    assert "TestCarrier" in email


def test_email_contains_recoverable():
    email = build_contestation_email(_make_scenario(["ok", "err"]))
    assert "300 USD" in email


def test_email_only_lists_anomalous_lines():
    scenario = _make_scenario(["ok", "err", "warn"])
    email = build_contestation_email(scenario)
    assert "LINE1" in email
    assert "LINE2" in email
    assert "LINE0" not in email


def test_email_tone_demeure_when_errors():
    email = build_contestation_email(_make_scenario(["err"]))
    assert "mettons en demeure" in email
    assert "demandons" not in email


def test_email_tone_demandons_when_warnings_only():
    email = build_contestation_email(_make_scenario(["warn"]))
    assert "demandons" in email
    assert "mettons en demeure" not in email


def test_email_has_fmc_reference():
    email = build_contestation_email(_make_scenario(["err"]))
    assert "Federal Maritime Commission" in email or "FMC" in email


# ── _validated_route ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("route", [
    "Shanghai → Le Havre",
    "Ningbo → Marseille",
    "Busan → Hambourg → Le Havre",
])
def test_validated_route_accepts_valid(route):
    assert _validated_route(route) == route


@pytest.mark.parametrize("bad", [
    "Shanghai<script>alert(1)</script>",
    "DROP TABLE invoices",
    "",
    None,
    "NoArrow",
])
def test_validated_route_rejects_invalid(bad):
    assert _validated_route(bad) is None


# ── _validated_period ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("period", [
    "Q1 2026",
    "Q4 2025",
    "Janv. 2026",
    "Févr. 2026",
    "Mars 2026",
])
def test_validated_period_accepts_valid(period):
    assert _validated_period(period) == period


@pytest.mark.parametrize("bad", [
    "<script>",
    "'; DROP TABLE--",
    "",
    None,
    "random text with no date",
])
def test_validated_period_rejects_invalid(bad):
    assert _validated_period(bad) is None
