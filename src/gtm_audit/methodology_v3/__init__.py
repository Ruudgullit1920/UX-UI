"""UX/UI audit methodology v3: config, severity, eligibility, scoring."""
from .config import (
    AXIS_IDS,
    Axis,
    Criterion,
    LocalizedText,
    MaturityBand,
    Methodology,
    OutOfScope,
    ScoringConfig,
    load_methodology,
)

__all__ = [
    "AXIS_IDS",
    "Axis",
    "Criterion",
    "LocalizedText",
    "MaturityBand",
    "Methodology",
    "OutOfScope",
    "ScoringConfig",
    "load_methodology",
]
