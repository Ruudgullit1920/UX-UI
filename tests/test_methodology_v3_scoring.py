import pytest

from src.gtm_audit.methodology_v3.config import load_methodology
from src.gtm_audit.methodology_v3.eligibility import is_score_eligible, normalize_confidence
from src.gtm_audit.methodology_v3.severity import Severity, escalate

GATE = 0.8


@pytest.fixture(scope="module")
def methodology():
    return load_methodology()


@pytest.mark.parametrize("severity, on_key_task, expected, escalated", [
    (Severity.CRITICAL, False, Severity.CRITICAL, False),
    (Severity.HIGH, False, Severity.HIGH, False),
    (Severity.MEDIUM, False, Severity.MEDIUM, False),
    (Severity.LOW, False, Severity.LOW, False),
    (Severity.CRITICAL, True, Severity.CRITICAL, False),
    (Severity.HIGH, True, Severity.CRITICAL, True),
    (Severity.MEDIUM, True, Severity.HIGH, True),
    (Severity.LOW, True, Severity.MEDIUM, True),
])
def test_escalation_table(severity, on_key_task, expected, escalated):
    assert escalate(severity, on_key_task) == (expected, escalated)


def test_severity_rank_orders_critical_first():
    assert [s.rank for s in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW)] == [0, 1, 2, 3]
    assert Severity("high") is Severity.HIGH


@pytest.mark.parametrize("value, expected", [
    ("0.85", 0.85),
    (85, 0.85),
    (None, 0.0),
    ("abc", 0.0),
    (1.4, 0.014),  # only values > 1 are read as percentages
    (1, 1.0),
    (0.8, 0.8),
    (-0.2, 0.0),
    (250, 1.0),
    (True, 0.0),
])
def test_normalize_confidence(value, expected):
    assert normalize_confidence(value) == pytest.approx(expected)


def test_measured_rows_are_always_eligible(methodology):
    criterion = methodology.criterion("accessibility.text_contrast")
    assert is_score_eligible({}, criterion, GATE) is True


@pytest.mark.parametrize("row, expected", [
    ({"confidence": 0.8, "elementIds": ["e4"]}, True),
    ({"confidence": 0.79, "elementIds": ["e4"]}, False),
    ({"confidence": 0.9}, False),
    ({"confidence": 0.9, "elementIds": []}, False),
    ({"confidence": 0.9, "screenshotRegion": {"x": 0, "y": 0, "width": 10, "height": 10}}, True),
    ({"confidence": "85", "elementIds": ["e4"]}, True),
])
def test_ai_assessed_eligibility(methodology, row, expected):
    criterion = methodology.criterion("usability.primary_action_clear")
    assert is_score_eligible(row, criterion, GATE) is expected


@pytest.mark.parametrize("row, expected", [
    ({}, False),
    ({"reviewStatus": "pending"}, False),
    ({"reviewStatus": "confirmed"}, True),
])
def test_manual_only_needs_confirmation(methodology, row, expected):
    criterion = methodology.criterion("usability.destructive_action_safeguard")
    assert is_score_eligible(row, criterion, GATE) is expected
