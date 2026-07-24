from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

OUTLOOK_INDEX_VERSION = "outlook_index_v1"
OUTLOOK_INDEX_MINIMUM_COVERAGE = 0.50
OUTLOOK_INDEX_DISCLAIMER = (
    "This outlook index is an interpretive comparison aid, not a probability, "
    "diagnosis, guarantee, or objective measurement."
)


class OutlookDomain(StrEnum):
    LOVE = "love"
    FINANCE = "finance"
    WELLBEING = "wellbeing"
    PARTNERSHIP = "partnership"
    OPPORTUNITY = "opportunity"
    HAPPINESS = "happiness"
    OVERALL = "overall"


class OutlookBand(StrEnum):
    VERY_CHALLENGING = "very_challenging"
    CHALLENGING = "challenging"
    MIXED = "mixed"
    SUPPORTIVE = "supportive"
    VERY_SUPPORTIVE = "very_supportive"


class ConfidenceStatus(StrEnum):
    INSUFFICIENT = "insufficient"
    UNCALIBRATED_LOW = "uncalibrated_low"
    UNCALIBRATED_MODERATE = "uncalibrated_moderate"


class ConflictStatus(StrEnum):
    NONE = "none"
    INTERNAL_CONFLICT = "internal_conflict"
    CROSS_CHANNEL_CONFLICT = "cross_channel_conflict"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True, slots=True)
class OutlookIndex:
    domain: OutlookDomain
    score: int | None
    band: OutlookBand | None
    score_version: str
    confidence_status: ConfidenceStatus
    supporting_component: float
    challenging_component: float
    coverage: float
    conflict_status: ConflictStatus
    evidence_refs: tuple[str, ...]
    disclaimer: str = OUTLOOK_INDEX_DISCLAIMER

    def __post_init__(self) -> None:
        for field_name, value in (
            ("supporting_component", self.supporting_component),
            ("challenging_component", self.challenging_component),
            ("coverage", self.coverage),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be between 0 and 1")
        if (self.score is None) != (self.band is None):
            raise ValueError("score and band must either both be present or both be absent")
        if self.score is not None and not 0 <= self.score <= 100:
            raise ValueError("score must be between 0 and 100")
        if self.score is not None and not self.evidence_refs:
            raise ValueError("a scored outlook index requires evidence references")
        if self.score_version != OUTLOOK_INDEX_VERSION:
            raise ValueError("unsupported outlook index version")
        if not self.disclaimer.strip():
            raise ValueError("outlook index disclaimer is required")

    @property
    def abstained(self) -> bool:
        return self.score is None

    def as_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain.value,
            "score": self.score,
            "band": self.band.value if self.band is not None else None,
            "score_version": self.score_version,
            "confidence_status": self.confidence_status.value,
            "supporting_component": self.supporting_component,
            "challenging_component": self.challenging_component,
            "coverage": self.coverage,
            "conflict_status": self.conflict_status.value,
            "evidence_refs": list(self.evidence_refs),
            "disclaimer": self.disclaimer,
        }


def _band_for_score(score: int) -> OutlookBand:
    if score <= 19:
        return OutlookBand.VERY_CHALLENGING
    if score <= 39:
        return OutlookBand.CHALLENGING
    if score <= 59:
        return OutlookBand.MIXED
    if score <= 79:
        return OutlookBand.SUPPORTIVE
    return OutlookBand.VERY_SUPPORTIVE


def calculate_outlook_index(
    *,
    domain: OutlookDomain,
    supporting_component: float,
    challenging_component: float,
    coverage: float,
    confidence_status: ConfidenceStatus,
    conflict_status: ConflictStatus,
    evidence_refs: tuple[str, ...],
    minimum_coverage: float = OUTLOOK_INDEX_MINIMUM_COVERAGE,
) -> OutlookIndex:
    for field_name, value in (
        ("supporting_component", supporting_component),
        ("challenging_component", challenging_component),
        ("coverage", coverage),
        ("minimum_coverage", minimum_coverage),
    ):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field_name} must be between 0 and 1")

    should_abstain = (
        coverage < minimum_coverage
        or confidence_status is ConfidenceStatus.INSUFFICIENT
        or not evidence_refs
    )
    if should_abstain:
        return OutlookIndex(
            domain=domain,
            score=None,
            band=None,
            score_version=OUTLOOK_INDEX_VERSION,
            confidence_status=ConfidenceStatus.INSUFFICIENT,
            supporting_component=supporting_component,
            challenging_component=challenging_component,
            coverage=coverage,
            conflict_status=ConflictStatus.INSUFFICIENT,
            evidence_refs=evidence_refs,
        )

    net = max(-1.0, min(1.0, supporting_component - challenging_component))
    score = max(0, min(100, int(round(50.0 + (50.0 * net)))))
    return OutlookIndex(
        domain=domain,
        score=score,
        band=_band_for_score(score),
        score_version=OUTLOOK_INDEX_VERSION,
        confidence_status=confidence_status,
        supporting_component=supporting_component,
        challenging_component=challenging_component,
        coverage=coverage,
        conflict_status=conflict_status,
        evidence_refs=evidence_refs,
    )
