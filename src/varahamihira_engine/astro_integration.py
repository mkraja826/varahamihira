from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import replace
from typing import Any

from .models import Evidence, Polarity, PredictionRequest
from .policy import ASTRO_PROFILE, CLASSICAL_PROFILE

_LEVEL_WEIGHTS = {
    "mahadasha": 0.40,
    "antardasha": 0.30,
    "pratyantardasha": 0.20,
    "sookshma": 0.10,
}

_LIFE_DOMAINS = {
    "career": frozenset({10}),
    "money_resources": frozenset({2, 11}),
    "relationships_marriage": frozenset({7}),
    "family_home": frozenset({4}),
    "education_creativity": frozenset({5}),
    "wellbeing": frozenset({1, 6}),
    "travel_change": frozenset({3, 9, 12}),
    "spirituality": frozenset({9, 12}),
}

_SIGN_RULERS = {
    1: "mars",
    2: "venus",
    3: "mercury",
    4: "moon",
    5: "sun",
    6: "mercury",
    7: "venus",
    8: "mars",
    9: "jupiter",
    10: "saturn",
    11: "saturn",
    12: "jupiter",
}

_CLASSICAL_GRAHAS = frozenset(
    {"sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"}
)
_GENERAL_ASPECTS = (
    (3, 0.25, "quarter"),
    (4, 0.75, "three-quarters"),
    (5, 0.50, "half"),
    (7, 1.00, "full"),
    (8, 0.75, "three-quarters"),
    (9, 0.50, "half"),
    (10, 0.25, "quarter"),
)
_SPECIAL_FULL_ASPECTS = {
    "mars": frozenset({4, 8}),
    "jupiter": frozenset({5, 9}),
    "saturn": frozenset({3, 10}),
}
_GENERAL_ASPECT_RULE_ID = "VM-BJ-C02-ASPECT-STRENGTH-EVAL-001"
_SPECIAL_ASPECT_RULE_ID = "VM-BJ-C02-SPECIAL-ASPECT-EVAL-001"
_VARGOTTAMA_RULE_ID = "VM-BJ-C01-VARGOTTAMA-EVAL-001"
_NATAL_LORD_CHANNEL_FACTOR = 0.60
_NATAL_OCCUPANT_CHANNEL_FACTOR = 0.40
_NATAL_ASPECT_CHANNEL_FACTOR = 0.20


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


def _ascendant_sign(raw_grahas: Sequence[Any]) -> int:
    inferred: set[int] = set()
    for raw in raw_grahas:
        graha = _mapping(raw, "raw strength graha")
        sign = int(graha.get("d1_sign_index", 0))
        house = int(graha.get("d1_house", 0))
        if 1 <= sign <= 12 and 1 <= house <= 12:
            inferred.add(((sign - house) % 12) + 1)
    if len(inferred) != 1:
        raise ValueError("Astro strength facts do not imply one ascendant sign")
    return inferred.pop()


def _component_rule_ids(weighted: Mapping[str, Any]) -> tuple[str, ...]:
    result: set[str] = set()
    for raw in _sequence(weighted.get("components", []), "weighted graha components"):
        component = _mapping(raw, "weighted graha component")
        result.update(_strings(component.get("classical_rule_ids")))
    return tuple(sorted(result))


def _natal_domain_evidence(weighted_dasha: Mapping[str, Any]) -> list[Evidence]:
    strength = _mapping(weighted_dasha.get("weighted_strength"), "weighted_dasha.weighted_strength")
    raw_strength = _mapping(strength.get("raw_strength"), "weighted_strength.raw_strength")
    raw_grahas = _sequence(raw_strength.get("grahas"), "raw_strength.grahas")
    ascendant = _ascendant_sign(raw_grahas)
    weighted_grahas = {
        str(item.get("graha", "")).strip().lower(): item
        for raw in _sequence(strength.get("weighted_grahas"), "weighted_strength.weighted_grahas")
        if (item := _mapping(raw, "weighted graha"))
    }

    evidence: list[Evidence] = []
    for domain, houses in _LIFE_DOMAINS.items():
        houses_by_lord: dict[str, list[int]] = {}
        for house in sorted(houses):
            sign = ((ascendant + house - 2) % 12) + 1
            houses_by_lord.setdefault(_SIGN_RULERS[sign], []).append(house)
        for lord, ruled_houses in sorted(houses_by_lord.items()):
            weighted = weighted_grahas.get(lord)
            if weighted is None:
                continue
            score = float(weighted.get("total_score", 0.0))
            polarity = (
                Polarity.SUPPORTING
                if score > 0
                else Polarity.CHALLENGING
                if score < 0
                else Polarity.CONTEXTUAL
            )
            weight = (
                round(_score_weight(score) * _NATAL_LORD_CHANNEL_FACTOR, 6)
                if polarity is not Polarity.CONTEXTUAL
                else 0.0
            )
            houses_text = ",".join(str(house) for house in ruled_houses)
            evidence.append(
                Evidence(
                    evidence_id=f"natal-house-lord-{domain}-{lord}",
                    domain=domain,
                    statement=(
                        f"{lord.title()}, lord of relevant house(s) {houses_text}, has "
                        f"controlled natal strength {score:.2f}."
                    ),
                    polarity=polarity,
                    weight=weight,
                    source_rule_ids=_component_rule_ids(weighted),
                    source_kind="convention",
                    reason=(
                        "Natal house-lord channel. Direction follows the transparent strength "
                        "score; weight = normalized absolute score × "
                        f"{_NATAL_LORD_CHANNEL_FACTOR:.2f}. "
                        "This is an API synthesis convention, not a classical textual formula."
                    ),
                    independence_key=f"natal-{domain}-{lord}-controlled-strength",
                )
            )
    return evidence


def _natal_occupant_evidence(weighted_dasha: Mapping[str, Any]) -> list[Evidence]:
    strength = _mapping(
        weighted_dasha.get("weighted_strength"),
        "weighted_dasha.weighted_strength",
    )
    raw_strength = _mapping(strength.get("raw_strength"), "weighted_strength.raw_strength")
    raw_grahas = _sequence(raw_strength.get("grahas"), "raw_strength.grahas")
    weighted_grahas = {
        str(item.get("graha", "")).strip().lower(): item
        for raw in _sequence(
            strength.get("weighted_grahas"),
            "weighted_strength.weighted_grahas",
        )
        if (item := _mapping(raw, "weighted graha"))
    }

    evidence: list[Evidence] = []
    seen: set[tuple[str, str, int]] = set()
    for raw in raw_grahas:
        graha = _mapping(raw, "raw strength graha")
        name = str(graha.get("graha", "")).strip().lower()
        house = int(graha.get("d1_house", 0))
        weighted = weighted_grahas.get(name)
        if not name or not 1 <= house <= 12 or weighted is None:
            continue
        for domain, houses in _LIFE_DOMAINS.items():
            identity = (domain, name, house)
            if house not in houses or identity in seen:
                continue
            seen.add(identity)
            score = float(weighted.get("total_score", 0.0))
            polarity = (
                Polarity.SUPPORTING
                if score > 0
                else Polarity.CHALLENGING
                if score < 0
                else Polarity.CONTEXTUAL
            )
            weight = (
                round(_score_weight(score) * _NATAL_OCCUPANT_CHANNEL_FACTOR, 6)
                if polarity is not Polarity.CONTEXTUAL
                else 0.0
            )
            evidence.append(
                Evidence(
                    evidence_id=f"natal-occupant-{domain}-{house}-{name}",
                    domain=domain,
                    statement=(
                        f"{name.title()} occupies relevant house {house} with controlled "
                        f"natal strength {score:.2f}."
                    ),
                    polarity=polarity,
                    weight=weight,
                    source_rule_ids=_component_rule_ids(weighted),
                    source_kind="convention",
                    reason=(
                        "Natal whole-sign occupant channel. Direction follows the transparent "
                        "strength score; weight = normalized absolute score × "
                        f"{_NATAL_OCCUPANT_CHANNEL_FACTOR:.2f}. This is an API synthesis "
                        "convention, not a classical textual formula."
                    ),
                    independence_key=f"natal-{domain}-{name}-controlled-strength",
                )
            )
    return evidence


def _natal_aspect_evidence(weighted_dasha: Mapping[str, Any]) -> list[Evidence]:
    strength = _mapping(
        weighted_dasha.get("weighted_strength"),
        "weighted_dasha.weighted_strength",
    )
    raw_strength = _mapping(strength.get("raw_strength"), "weighted_strength.raw_strength")
    raw_grahas = _sequence(raw_strength.get("grahas"), "raw_strength.grahas")
    ascendant = _ascendant_sign(raw_grahas)
    weighted_grahas = {
        str(item.get("graha", "")).strip().lower(): item
        for raw in _sequence(
            strength.get("weighted_grahas"),
            "weighted_strength.weighted_grahas",
        )
        if (item := _mapping(raw, "weighted graha"))
    }

    evidence: list[Evidence] = []
    seen: set[tuple[str, str, int, int]] = set()
    for raw in raw_grahas:
        graha = _mapping(raw, "raw strength graha")
        name = str(graha.get("graha", "")).strip().lower()
        source_sign = int(graha.get("d1_sign_index", 0))
        weighted = weighted_grahas.get(name)
        if (
            name not in _CLASSICAL_GRAHAS
            or not 1 <= source_sign <= 12
            or weighted is None
        ):
            continue
        score = float(weighted.get("total_score", 0.0))
        polarity = (
            Polarity.SUPPORTING
            if score > 0
            else Polarity.CHALLENGING
            if score < 0
            else Polarity.CONTEXTUAL
        )
        for relative_house, general_fraction, general_label in _GENERAL_ASPECTS:
            special = relative_house in _SPECIAL_FULL_ASPECTS.get(name, ())
            fraction = 1.0 if special else general_fraction
            label = "full" if special else general_label
            target_sign = ((source_sign + relative_house - 2) % 12) + 1
            target_house = ((target_sign - ascendant) % 12) + 1
            for domain, relevant_houses in _LIFE_DOMAINS.items():
                identity = (domain, name, relative_house, target_house)
                if target_house not in relevant_houses or identity in seen:
                    continue
                seen.add(identity)
                weight = (
                    round(
                        _score_weight(score)
                        * fraction
                        * _NATAL_ASPECT_CHANNEL_FACTOR,
                        6,
                    )
                    if polarity is not Polarity.CONTEXTUAL
                    else 0.0
                )
                rule_ids = {_GENERAL_ASPECT_RULE_ID, *_component_rule_ids(weighted)}
                if special:
                    rule_ids.add(_SPECIAL_ASPECT_RULE_ID)
                evidence.append(
                    Evidence(
                        evidence_id=(
                            f"natal-aspect-{domain}-{name}-"
                            f"{relative_house}-to-{target_house}"
                        ),
                        domain=domain,
                        statement=(
                            f"{name.title()} casts a {label} classical aspect to relevant "
                            f"house {target_house} with controlled natal strength {score:.2f}."
                        ),
                        polarity=polarity,
                        weight=weight,
                        source_rule_ids=tuple(sorted(rule_ids)),
                        source_kind="convention",
                        reason=(
                            "Aspect geometry and fractional strength follow Brihat Jataka "
                            "2.13. Direction follows the source Graha's controlled strength; "
                            "weight = normalized absolute score × aspect fraction × "
                            f"{_NATAL_ASPECT_CHANNEL_FACTOR:.2f}. The final directional "
                            "weight is an API synthesis convention, not a classical formula."
                        ),
                        independence_key=f"natal-{domain}-{name}-controlled-strength",
                    )
                )
    return evidence


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
                evidence_id=(
                    f"natal-karaka-career-karmājīva-"
                    f"{index + 1}-{graha.lower()}"
                ),
                domain="career",
                statement=(
                    f"{graha} is a declared Chapter 10 Karmājīva indicator in "
                    f"{repetition} independent reference channel"
                    f"{'s' if repetition != 1 else ''} with controlled strength {score:.2f}."
                ),
                polarity=polarity,
                weight=weight,
                source_rule_ids=rule_ids,
                source_kind="convention",
                reason=(
                    (
                        str(strength.get("reason", "")).strip()
                        or "Controlled career-indicator strength summary."
                    )
                    + " Karmājīva derivation is classical; converting controlled strength "
                    "to directional evidence is an API convention."
                ),
                independence_key=(
                    f"natal-career-{graha.lower()}-controlled-strength"
                ),
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
        contextual_facts = _sequence(
            level.get("contextual_evidence", []), f"{level_name}.contextual_evidence"
        )
        owned_houses: set[int] = set()
        for raw_context in contextual_facts:
            context = _mapping(raw_context, "dasha contextual evidence")
            if str(context.get("fact", "")).strip() == "owned_houses":
                for item in str(context.get("value", "")).split(","):
                    with suppress(ValueError):
                        owned_houses.add(int(item.strip()))
        relevant_domains = {
            domain for domain, houses in _LIFE_DOMAINS.items() if houses & owned_houses
        }
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
                base = Evidence(
                    evidence_id=(f"dasha-{level_index + 1}-{category}-{fact_index + 1}"),
                    domain="overall",
                    statement=(
                        f"{level_name} lord {lord}: {fact_name}" + (f" ({value})" if value else "")
                    ),
                    polarity=polarity,
                    weight=level_weight if polarity is not Polarity.CONTEXTUAL else 0.0,
                    source_rule_ids=rule_ids,
                    source_kind="classical" if rule_ids else "convention",
                    reason=reason or "Active-daśā evidence supplied by Astro.",
                    independence_key=(
                        f"dasha-{level_index + 1}-{level_name}-{lord}-"
                        f"{fact_name}-{value or 'none'}-overall"
                    ),
                )
                evidence.append(base)
                for domain in sorted(relevant_domains):
                    relevant_houses = ",".join(
                        str(h) for h in sorted(owned_houses & _LIFE_DOMAINS[domain])
                    )
                    evidence.append(
                        Evidence(
                            evidence_id=f"{base.evidence_id}-{domain}",
                            domain=domain,
                            statement=base.statement,
                            polarity=base.polarity,
                            weight=base.weight,
                            source_rule_ids=base.source_rule_ids,
                            source_kind=base.source_kind,
                            reason=(
                                f"{base.reason} Applied to {domain.replace('_', ' ')} because "
                                f"the active {level_name} lord owns relevant house(s): "
                                f"{relevant_houses}."
                            ),
                            independence_key=(
                                f"dasha-{level_index + 1}-{level_name}-{lord}-"
                                f"{fact_name}-{value or 'none'}-{domain}"
                            ),
                        )
                    )
    return evidence


def _apply_d9_confirmation(
    evidence: list[Evidence],
    weighted_dasha: Mapping[str, Any],
) -> list[Evidence]:
    strength = _mapping(
        weighted_dasha.get("weighted_strength"),
        "weighted_dasha.weighted_strength",
    )
    raw_strength = _mapping(strength.get("raw_strength"), "weighted_strength.raw_strength")
    raw_grahas = _sequence(raw_strength.get("grahas"), "raw_strength.grahas")
    confirmed = {
        str(item.get("graha", "")).strip().lower()
        for raw in raw_grahas
        if (item := _mapping(raw, "raw strength graha"))
        and bool(item.get("vargottama"))
    }
    if not confirmed:
        return evidence

    result: list[Evidence] = []
    for item in evidence:
        graha = next(
            (
                name
                for name in confirmed
                if item.independence_key.endswith(
                    f"-{name}-controlled-strength"
                )
            ),
            None,
        )
        if graha is None:
            result.append(item)
            continue
        result.append(
            replace(
                item,
                source_rule_ids=tuple(
                    sorted({*item.source_rule_ids, _VARGOTTAMA_RULE_ID})
                ),
                reason=(
                    f"{item.reason} D9 confirmation: {graha.title()} is Vargottama "
                    "(the same Rashi in D1 and D9). This confirms the existing trace "
                    "without adding a second directional weight."
                ),
            )
        )
    return result


def _coverage_evidence() -> list[Evidence]:
    evidence = [
        Evidence(
            evidence_id=f"coverage-{domain}",
            domain=domain,
            statement=(
                f"{domain.replace('_', ' ').title()} is evaluated only from traceable "
                "active-daśā, natal lord, occupant, aspect, and explicitly declared "
                "significator evidence currently available."
            ),
            polarity=Polarity.CONTEXTUAL,
            weight=0.0,
            source_rule_ids=(),
            source_kind="convention",
            reason="Coverage marker; it does not create a favourable or negative score.",
            independence_key=f"coverage-{domain}",
        )
        for domain in ("overall", *_LIFE_DOMAINS)
    ]
    evidence.append(
        Evidence(
            evidence_id="coverage-varga-d10-career",
            domain="career",
            statement=(
                "D10 career confirmation is unavailable and is not used in this result."
            ),
            polarity=Polarity.CONTEXTUAL,
            weight=0.0,
            source_rule_ids=(),
            source_kind="convention",
            reason=(
                "Astro does not currently expose a versioned, boundary-tested D10 "
                "calculation contract. The engine abstains instead of deriving one."
            ),
            independence_key="coverage-varga-d10-career",
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

    evidence = (
        _coverage_evidence()
        + _natal_domain_evidence(weighted_dasha)
        + _natal_occupant_evidence(weighted_dasha)
        + _natal_aspect_evidence(weighted_dasha)
        + _career_evidence(weighted_career)
        + _dasha_evidence(weighted_dasha)
    )
    evidence = _apply_d9_confirmation(evidence, weighted_dasha)
    if not evidence:
        raise ValueError("Astro analysis produced no evaluable evidence")

    return PredictionRequest(
        period=period,
        as_of=as_of,
        calculation_profile=calculation_profile,
        classical_profile=CLASSICAL_PROFILE,
        evidence=tuple(evidence),
    )
