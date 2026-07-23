from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .policy import ASTRO_PROFILE, CLASSICAL_PROFILE


class Polarity(StrEnum):
    SUPPORTING = "supporting"
    CHALLENGING = "challenging"
    CONTEXTUAL = "contextual"


class Outlook(StrEnum):
    FAVOURABLE = "favourable"
    MIXED = "mixed"
    CHALLENGING = "challenging"
    INSUFFICIENT = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    domain: str
    statement: str
    polarity: Polarity
    weight: float
    source_rule_ids: tuple[str, ...]
    source_kind: str
    reason: str
    independence_key: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("evidence_id is required")
        if not self.domain.strip():
            raise ValueError("domain is required")
        if not self.statement.strip():
            raise ValueError("statement is required")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("weight must be between 0 and 1")
        if self.source_kind not in {"classical", "convention"}:
            raise ValueError("source_kind must be classical or convention")
        if self.source_kind == "classical" and not self.source_rule_ids:
            raise ValueError("classical evidence requires at least one source rule ID")
        if not self.independence_key.strip():
            object.__setattr__(self, "independence_key", self.evidence_id)


@dataclass(frozen=True, slots=True)
class PredictionRequest:
    period: str
    as_of: str
    evidence: tuple[Evidence, ...]
    calculation_profile: str = ASTRO_PROFILE
    classical_profile: str = CLASSICAL_PROFILE

    def __post_init__(self) -> None:
        if self.period not in {"daily", "weekly", "monthly", "natal"}:
            raise ValueError("unsupported prediction period")
        if self.calculation_profile != ASTRO_PROFILE:
            raise ValueError("unsupported astronomical calculation profile")
        if self.classical_profile != CLASSICAL_PROFILE:
            raise ValueError("unsupported classical profile")


@dataclass(frozen=True, slots=True)
class DomainResult:
    domain: str
    outlook: Outlook
    strength: str
    supporting_score: float
    challenging_score: float
    net_score: float
    statement: str
    advisory: str
    favourable_timing: str | None
    challenging_timing: str | None
    supporting_factors: tuple[Evidence, ...]
    challenging_factors: tuple[Evidence, ...]
    contextual_factors: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class PredictionResponse:
    engine_version: str
    calculation_profile: str
    classical_profile: str
    period: str
    as_of: str
    results: tuple[DomainResult, ...]
    disclaimer: str

    def as_dict(self) -> dict[str, Any]:
        def evidence_dict(item: Evidence) -> dict[str, Any]:
            return {
                "evidence_id": item.evidence_id,
                "domain": item.domain,
                "statement": item.statement,
                "polarity": item.polarity.value,
                "weight": item.weight,
                "source_rule_ids": list(item.source_rule_ids),
                "source_kind": item.source_kind,
                "reason": item.reason,
                "independence_key": item.independence_key,
            }

        return {
            "engine_version": self.engine_version,
            "calculation_profile": self.calculation_profile,
            "classical_profile": self.classical_profile,
            "period": self.period,
            "as_of": self.as_of,
            "results": [
                {
                    "domain": result.domain,
                    "outlook": result.outlook.value,
                    "strength": result.strength,
                    "supporting_score": result.supporting_score,
                    "challenging_score": result.challenging_score,
                    "net_score": result.net_score,
                    "statement": result.statement,
                    "advisory": result.advisory,
                    "favourable_timing": result.favourable_timing,
                    "challenging_timing": result.challenging_timing,
                    "supporting_factors": [
                        evidence_dict(item) for item in result.supporting_factors
                    ],
                    "challenging_factors": [
                        evidence_dict(item) for item in result.challenging_factors
                    ],
                    "contextual_factors": [
                        evidence_dict(item) for item in result.contextual_factors
                    ],
                }
                for result in self.results
            ],
            "disclaimer": self.disclaimer,
        }
