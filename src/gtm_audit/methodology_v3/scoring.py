"""Methodology v3 axis scoring: dedupe, penalties, maturity caps, coverage."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .config import Axis, Criterion, LocalizedText, MaturityBand, ScoringConfig
from .eligibility import is_score_eligible
from .severity import Severity, escalate

# Worst first: a key keeps its worst outcome.
_OUTCOME_RANK = {"fail": 0, "warning": 1, "unknown": 2, "pass": 3}


@dataclass(frozen=True)
class Coverage:
    evaluated: int
    applicable: int
    not_applicable_for_target: tuple[str, ...]
    not_evaluated: tuple[str, ...]


@dataclass(frozen=True)
class AxisScore:
    axis_id: str
    score: float
    maturity: int
    maturity_label: LocalizedText
    coverage: Coverage
    worst_severity: Severity | None
    scored_defects: int
    observations: tuple[dict, ...]
    escalations: tuple[str, ...]


def dedupe_key(row: dict, criterion: Criterion) -> str:
    """One logical defect = family + page + elements (spec §6.2).

    Rows with neither a page nor elements fall back to their findingId, so
    distinct defects never collapse into one.
    """
    page = str(row.get("pageId") or "")
    elements = ",".join(sorted(str(item) for item in row.get("elementIds") or ()))
    if not page and not elements:
        finding = row.get("findingId")
        return f"{criterion.logical_defect_family}|finding:{finding if finding else id(row)}"
    return f"{criterion.logical_defect_family}|{page}|{elements}"


def _severity(value: object) -> Severity:
    try:
        return Severity(str(value).strip().lower())
    except ValueError:
        return Severity.MEDIUM


def _outcome(row: dict) -> str:
    value = str(row.get("outcome") or "unknown").lower()
    return value if value in _OUTCOME_RANK else "unknown"


def maturity_for(score: float, worst: Severity | None, bands: Sequence[MaturityBand]) -> int:
    level = next((band.level for band in bands if score >= band.min_score), bands[-1].level)
    if worst is Severity.CRITICAL:
        level = min(level, 2)
    elif worst is Severity.HIGH:
        level = min(level, 4)
    return level


def _label(level: int, bands: Sequence[MaturityBand]) -> LocalizedText:
    return next(band.label for band in bands if band.level == level)


def score_axis_v3(rows: Iterable[dict], axis: Axis, target: str, scoring: ScoringConfig) -> AxisScore | None:
    applicable = {c.id: c for c in axis.criteria if target in c.targets}
    if not applicable:
        return None
    not_applicable = tuple(c.id for c in axis.criteria if c.id not in applicable)

    observations: list[dict] = []
    criterion_outcomes: dict[str, str] = {}
    defects: dict[str, tuple[Severity, str | None]] = {}  # key -> (severity after escalation, escalated finding)
    for row in rows:
        criterion = applicable.get(str(row.get("criterionId") or ""))
        if criterion is None:
            continue  # unknown, other axis, or not applicable to this target
        outcome = _outcome(row)
        if not is_score_eligible(row, criterion, scoring.ai_confidence_gate):
            if outcome != "pass":
                observations.append(row)
            continue
        current = criterion_outcomes.get(criterion.id)
        if current is None or _OUTCOME_RANK[outcome] < _OUTCOME_RANK[current]:
            criterion_outcomes[criterion.id] = outcome
        if outcome != "fail":
            continue
        severity, escalated = escalate(_severity(row.get("severity")), bool(row.get("onKeyTask")))
        key = dedupe_key(row, criterion)
        kept = defects.get(key)
        if kept is None or severity.rank < kept[0].rank:
            defects[key] = (severity, str(row.get("findingId") or criterion.id) if escalated else None)

    evaluated = [cid for cid, outcome in criterion_outcomes.items() if outcome in ("pass", "fail")]
    total_weight = sum(applicable[cid].numeric_weight for cid in evaluated)
    passed_weight = sum(applicable[cid].numeric_weight for cid in evaluated if criterion_outcomes[cid] == "pass")
    base = 100.0 * passed_weight / total_weight if total_weight else 0.0
    penalty = sum(scoring.penalties[severity.value] for severity, _ in defects.values())
    score = min(max(base - penalty, 0.0), 100.0)

    worst = min((severity for severity, _ in defects.values()), key=lambda s: s.rank, default=None)
    bands = scoring.maturity_bands
    maturity = maturity_for(score, worst, bands)
    return AxisScore(
        axis_id=axis.id,
        score=score,
        maturity=maturity,
        maturity_label=_label(maturity, bands),
        coverage=Coverage(
            evaluated=len(evaluated),
            applicable=len(applicable),
            not_applicable_for_target=not_applicable,
            not_evaluated=tuple(cid for cid in applicable if cid not in evaluated),
        ),
        worst_severity=worst,
        scored_defects=len(defects),
        observations=tuple(observations),
        escalations=tuple(finding for _, finding in defects.values() if finding),
    )
