import copy
import json

import pytest
from pydantic import ValidationError

from src.gtm_audit.methodology_v3.config import Methodology, load_methodology

AXIS_IDS = ["usability", "navigation", "visual", "content", "accessibility", "performance", "trust"]


def _text(label):
    return {"en": f"{label} en", "fr": f"{label} fr"}


def _criterion(axis_id, slug="sample"):
    return {
        "id": f"{axis_id}.{slug}",
        "title": _text("title"),
        "description": _text("description"),
        "weight": "core",
        "standards": ["NNG:H1"],
        "targets": ["website", "webapp"],
        "page_types": ["any"],
        "evidence_type": "measured",
        "pass_guidance": _text("pass"),
        "fail_guidance": _text("fail"),
        "example_good": _text("good"),
        "example_rejected": _text("rejected"),
        "logical_defect_family": f"{axis_id}-{slug}",
    }


def _fixture():
    axes = []
    for index, axis_id in enumerate(AXIS_IDS):
        other = AXIS_IDS[(index + 1) % len(AXIS_IDS)]
        axes.append({
            "id": axis_id,
            "name": _text("name"),
            "core_question": _text("question"),
            "why_it_matters": _text("why"),
            "failure_modes": [_text("failure")],
            "out_of_scope": [{"topic": "elsewhere", "routes_to": other}],
            "criteria": [_criterion(axis_id)],
        })
    return {
        "version": 3,
        "axes": axes,
        "scoring": {
            "penalties": {"critical": 25, "high": 12, "medium": 5, "low": 1},
            "ai_confidence_gate": 0.8,
            "maturity_bands": [
                {"level": 5, "label": _text("Excellent"), "min_score": 90},
                {"level": 4, "label": _text("Good"), "min_score": 75},
                {"level": 3, "label": _text("Fair"), "min_score": 55},
                {"level": 2, "label": _text("Weak"), "min_score": 35},
                {"level": 1, "label": _text("Critical"), "min_score": 0},
            ],
        },
        "productTypeWeights": {"ecommerce": {"trust": 1.5, "usability": 1.2}},
    }


def _invalid(mutate):
    data = copy.deepcopy(_fixture())
    mutate(data)
    with pytest.raises(ValidationError):
        Methodology.model_validate(data)


def test_valid_fixture_loads_seven_axes_in_order():
    methodology = Methodology.model_validate(_fixture())
    assert [axis.id for axis in methodology.axes] == AXIS_IDS
    assert methodology.axis("trust").id == "trust"
    assert methodology.criterion("usability.sample").numeric_weight == 3
    assert methodology.product_type_weights["ecommerce"]["trust"] == 1.5


def test_unknown_criterion_is_none():
    assert Methodology.model_validate(_fixture()).criterion("nope") is None


def test_supporting_weight_is_one():
    data = _fixture()
    data["axes"][0]["criteria"][0]["weight"] = "supporting"
    assert Methodology.model_validate(data).criterion("usability.sample").numeric_weight == 1


def test_axis_order_must_match():
    _invalid(lambda d: d["axes"].reverse())


def test_missing_axis_is_rejected():
    _invalid(lambda d: d["axes"].pop())


def test_duplicate_criterion_id_is_rejected():
    _invalid(lambda d: d["axes"][0]["criteria"].append(copy.deepcopy(d["axes"][0]["criteria"][0])))


def test_criterion_id_must_carry_axis_prefix():
    def mutate(d):
        d["axes"][0]["criteria"][0]["id"] = "navigation.sample_x"
    _invalid(mutate)


def test_standards_must_be_non_empty():
    def mutate(d):
        d["axes"][0]["criteria"][0]["standards"] = []
    _invalid(mutate)


@pytest.mark.parametrize("standard", ["WCAG:1.4.3", "WCAG21:1.4.3","CWV:FID", "random", "WCAG22:1.4"])
def test_standards_must_match_known_patterns(standard):
    def mutate(d):
        d["axes"][0]["criteria"][0]["standards"] = [standard]
    _invalid(mutate)


@pytest.mark.parametrize("standard", ["WCAG22:1.4.3", "WCAG22:2.5.8", "NNG:H10", "CWV:INP", "GESTALT:proximity", "BAYMARD:checkout-forms", "ISO9241:110", "STANFORD:credibility"])
def test_known_standards_are_accepted(standard):
    data = _fixture()
    data["axes"][0]["criteria"][0]["standards"] = [standard]
    Methodology.model_validate(data)


def test_targets_must_be_non_empty():
    def mutate(d):
        d["axes"][0]["criteria"][0]["targets"] = []
    _invalid(mutate)


def test_out_of_scope_must_route_to_another_axis():
    def mutate(d):
        d["axes"][0]["out_of_scope"][0]["routes_to"] = "usability"
    _invalid(mutate)


def test_out_of_scope_must_route_to_known_axis():
    def mutate(d):
        d["axes"][0]["out_of_scope"][0]["routes_to"] = "task_execution"
    _invalid(mutate)


def test_penalties_need_exactly_four_severities():
    def mutate(d):
        d["scoring"]["penalties"].pop("low")
    _invalid(mutate)


def test_penalties_reject_extra_severity():
    def mutate(d):
        d["scoring"]["penalties"]["blocker"] = 40
    _invalid(mutate)


def test_maturity_bands_must_be_levels_five_to_one():
    def mutate(d):
        d["scoring"]["maturity_bands"].pop()
    _invalid(mutate)


def test_maturity_band_scores_must_descend():
    def mutate(d):
        d["scoring"]["maturity_bands"][1]["min_score"] = 95
    _invalid(mutate)


def test_product_type_weights_keys_must_be_axis_ids():
    def mutate(d):
        d["productTypeWeights"]["ecommerce"]["task_execution"] = 1.2
    _invalid(mutate)


def test_product_type_weights_must_be_positive():
    def mutate(d):
        d["productTypeWeights"]["ecommerce"]["trust"] = 0
    _invalid(mutate)


@pytest.mark.parametrize("path", [
    ("axes", 0, "name"),
    ("axes", 0, "failure_modes", 0),
    ("axes", 0, "criteria", 0, "example_rejected"),
    ("scoring", "maturity_bands", 0, "label"),
])
def test_french_text_must_be_non_empty(path):
    def mutate(d):
        node = d
        for key in path:
            node = node[key]
        node["fr"] = "  "
    _invalid(mutate)


def test_english_text_must_be_non_empty():
    def mutate(d):
        d["axes"][0]["criteria"][0]["title"]["en"] = ""
    _invalid(mutate)


def test_load_methodology_from_explicit_path(tmp_path):
    path = tmp_path / "methodology.json"
    path.write_text(json.dumps(_fixture()), encoding="utf-8")
    assert [axis.id for axis in load_methodology(path).axes] == AXIS_IDS


def test_load_methodology_reads_env_path(tmp_path, monkeypatch):
    data = _fixture()
    data["scoring"]["ai_confidence_gate"] = 0.9
    path = tmp_path / "methodology.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setenv("AUDIT_METHODOLOGY_V3_PATH", str(path))
    load_methodology.cache_clear()
    try:
        assert load_methodology().scoring.ai_confidence_gate == 0.9
    finally:
        monkeypatch.delenv("AUDIT_METHODOLOGY_V3_PATH")
        load_methodology.cache_clear()


def test_shared_config_is_valid():
    methodology = load_methodology()
    assert [axis.id for axis in methodology.axes] == AXIS_IDS
    assert all(axis.criteria for axis in methodology.axes)
