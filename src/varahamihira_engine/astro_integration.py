from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .models import Evidence, Polarity, PredictionRequest
from .policy import ASTRO_PROFILE, CLASSICAL_PROFILE

_LEVEL_WEIGHTS = {
    "mahadasha": 0.40,
    "antardasha": 0.30,
    "pratyantardasha": 0.20,
    "sookshma": 0.10,
}


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _sequence(value: Any, field: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value


def _strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, str) and item.strip())


def _score_weight(score: float) -> float:
    return round(min(1.0, max(0.1, abs(score) / 8.0)), 6)


def _career_evidence(weighted_career: Mapping[str, Any]) -> list[Evidence]:
    career = _mapping(weighted_career.get("career"), "weighted_career.career")
    raw_candidates = _sequence(career.get("candidates"), "career.candidates")
    rules_by_graha: dict[str, tuple[str, ...]] = {}
    for raw in raw_candidates:
        candidate = _mapping(raw, "career candidate")
        rules_by_graha[str(candidate.get("graha", ""))] = _strings(candidate.get("rule_ids"))

    evidence: list[Evidence] = []
    summaries = _sequence(
        weighted_career.get("candidate_strengths"),
        "weighted_career.candidate_strengths",
    )
    for index, raw in enumerate(summaries):
        summary = _mapping(raw, "career candidate strength")
        graha = str(summary.get("graha", "")).strip()
        repetition = int(summary.get("repetition_count", 0))
        strength = _mapping(summary.get("strength"), "candidate strength snapshot")
        available = bool(strength.get("available"))
        score_value = strength.get("total_score")
        if not graha or repetition < 1 or not available or score_value is None:
            continue
        score = float(score_value)
        if score == 0.0:
            polarity = Polarity.CONTEXTUAL
            weight = 0.0
        else:
            polarity = Polarity.SUPPORTING if score > 0 else Polarity.CHALLENGING
            weight = _score_weight(score)
        rule_ids = rules_by_graha.get(graha, ())
        evidence.append(
            Evidence(
                evidence_id=f"career-candidate-{index + 1}-{graha.lower()}",
                domain="career",
                statement=(
                    f"{graha} appears in {repetition} Karmājīva channel"
                    f"{'s' if repetition != 1 else ''} with controlled strength {score:.2f}."
                ),
                polarity=polarity,
                weight=weight,
                source_rule_ids=rule_ids,
                source_kind="convention",
                reason=str(strength.get("reason", "")).strip()
                or "Controlled career-indicator strength summary.",
            )
        )
    return evidence


def _dasha_evidence(weighted_dasha: Mapping[str, Any]) -> list[Evidence]:
    dasha = _mapping(weighted_dasha.get("dasha"), "weighted_dasha.dasha")
    levels = _sequence(dasha.get("levels"), "dasha.levels")
    evidence: list[Evidence] = []
    for level_index, raw in enumerate(levels):
        level = _mapping(raw, "dasha level")
        level_name = str(level.get("level", "")).strip()
        lord = str(level.get("lord", "")).strip()
        level_weight = _LEVEL_WEIGHTS.get(level_name)
        if level_weight is None or not lord:
            continue
        for category, polarity in (
            ("supporting_evidence", Polarity.SUPPORTING),
            ("challenging_evidence", Polarity.CHALLENGING),
            ("contextual_evidence", Polarity.CONTEXTUAL),
        ):
            facts = _sequence(level.get(category, []), f"{level_name}.{category}")
            for fact_index, raw_fact in enumerate(facts):
                fact = _mapping(raw_fact, "dasha evidence")
                fact_name = str(fact.get("fact", "")).strip()
                value = str(fact.get("value", "")).strip()
                reason = str(fact.get("reason", "")).strip()
                rule_ids = _strings(fact.get("rule_ids"))
                evidence.append(
                    Evidence(
                        evidence_id=(
                            f"dasha-{level_index + 1}-{category}-{fact_index + 1}"
                        ),
                        domain="overall",
                        statement=(
                            f"{level_name} lord {lord}: {fact_name}"
                            + (f" ({value})" if value else "")
                        ),
                        polarity=polarity,
                        weight=level_weight if polarity is not Polarity.CONTEXTUAL else 0.0,
                        source_rule_ids=rule_ids,
                        source_kind="classical" if rule_ids else "convention",
                        reason=reason or "Active-daśā evidence supplied by Astro.",
                    )
                )
    return evidence


def request_from_astro_analysis(
    *,
    period: str,
    as_of: str,
    weighted_career: Mapping[str, Any],
    weighted_dasha: Mapping[str, Any],
) -> PredictionRequest:
    """Compose real Astro career and active-daśā evidence for deterministic evaluation."""

    career_profile = str(weighted_career.get("profile_id", ""))
    dasha_profile = str(weighted_dasha.get("profile_id", ""))
    if career_profile != CLASSICAL_PROFILE or dasha_profile != CLASSICAL_PROFILE:
        raise ValueError("Astro classical profile mismatch")

    calculation_profile = str(
        _mapping(weighted_dasha.get("weighted_strength"), "weighted_dasha.weighted_strength").get(
            "calculation_profile",
            "",
        )
    )
    if calculation_profile != ASTRO_PROFILE:
        raise ValueError("Astro calculation profile mismatch")

    evidence = _career_evidence(weighted_career) + _dasha_evidence(weighted_dasha)
    if not evidence:
        raise ValueError("Astro analysis produced no evaluable evidence")

    return PredictionRequest(
        period=period,
        as_of=as_of,
        calculation_profile=calculation_profile,
        classical_profile=CLASSICAL_PROFILE,
        evidence=tuple(evidence),
    )
