from src.gtm_audit.common import AXIS_DEFINITIONS
from src.gtm_audit.generate_gtm_audit import axe_scoring_rows, axis_rows
from src.gtm_audit.scoring import score_axis


def test_measured_axe_violation_is_an_accessibility_score_input():
    results = {
        "pages": [
            {
                "name": "Protected route",
                "finalUrl": "https://example.test/consultant",
                "screenshotPath": "evidence.png",
                "axe": {
                    "status": "completed",
                    "measurement": "measured",
                    "pageId": "page-1",
                    "toolVersion": "4.11.1",
                    "raw": {
                        "violations": [
                            {
                                "id": "color-contrast",
                                "impact": "serious",
                                "help": "Elements must meet minimum color contrast ratio thresholds",
                                "nodes": [{"target": [".sidebar"], "failureSummary": "Insufficient contrast"}],
                            }
                        ],
                        "incomplete": [],
                    },
                },
            }
        ]
    }

    rows = axe_scoring_rows(results)
    accessibility = next(axis for axis in AXIS_DEFINITIONS if axis["id"] == "trust_accessibility")
    score = score_axis(axis_rows(rows, accessibility))

    assert len(rows) == 1
    assert rows[0]["ruleId"] == "axe:color-contrast"
    assert score.scored is True
    assert score.score == 0.0
