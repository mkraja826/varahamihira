from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from .models import (
    DomainResult,
    Evidence,
    Outlook,
    Polarity,
    PredictionRequest,
    PredictionResponse,
)
from .policy import ASTROLOGY_DISCLAIMER, BLOCKED_DOMAINS, ENGINE_VERSION

_DIRECTION_THRESHOLD = 0.25


def _deduplicate_evidence(evidence: tuple[Evidence, ...]) -> tuple[Evidence, ...]:
    """Count one directional contribution per underlying fact within a domain."""

    grouped: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence:
        grouped[item.independence_key].append(item)

    result: list[Evidence] = []
    for independence_key in sorted(grouped):
        candidates = grouped[independence_key]
        polarities = {item.polarity for item in candidates}
        if len(polarities) != 1:
            raise ValueError(
                "conflicting polarity for independent evidence key: "
                f"{independence_key}"
            )
        winner = min(candidates, key=lambda item: (-item.weight, item.evidence_id))
        if len(candidates) > 1:
            corroborating_ids = ", ".join(
                item.evidence_id
                for item in sorted(candidates, key=lambda item: item.evidence_id)
                if item.evidence_id != winner.evidence_id
            )
            rule_ids = tuple(
                sorted(
                    {
                        rule_id
                        for item in candidates
                        for rule_id in item.source_rule_ids
                    }
                )
            )
            winner = replace(
                winner,
                source_rule_ids=rule_ids,
                reason=(
                    f"{winner.reason} Corroborating record(s) {corroborating_ids} share "
                    "the same underlying fact and were retained in the trace without "
                    "adding their weight."
                ),
            )
        result.append(winner)
    return tuple(result)


def _strength(supporting: float, challenging: float, net: float) -> str:
    directional_total = supporting + challenging
    magnitude = abs(net)
    if directional_total >= 1.5 and magnitude >= 0.75:
        return "strong"
    if directional_total >= 0.75 and magnitude >= 0.35:
        return "moderate"
    return "weak"


def _outlook(supporting: float, challenging: float) -> Outlook:
    if supporting == 0.0 and challenging == 0.0:
        return Outlook.INSUFFICIENT
    net = supporting - challenging
    if net >= _DIRECTION_THRESHOLD:
        return Outlook.FAVOURABLE
    if net <= -_DIRECTION_THRESHOLD:
        return Outlook.CHALLENGING
    return Outlook.MIXED


def _statement(domain: str, outlook: Outlook, strength: str) -> str:
    readable = domain.replace("_", " ")
    if outlook is Outlook.FAVOURABLE:
        return f"The evaluated indications for {readable} are favourable ({strength})."
    if outlook is Outlook.CHALLENGING:
        return f"The evaluated indications for {readable} are negative ({strength})."
    if outlook is Outlook.MIXED:
        return (
            f"The evaluated indications for {readable} are mixed; neither side "
            f"clearly dominates ({strength})."
        )
    return f"There is insufficient directional evidence for {readable}."


def _timing(period: str, outlook: Outlook) -> tuple[str, str | None, str | None]:
    window = {"daily": "day", "weekly": "week", "monthly": "month", "natal": "natal period"}[period]
    if outlook is Outlook.FAVOURABLE:
        return (
            "Use the comparatively supportive window for measured action; "
            "confirm important decisions with real-world facts.",
            f"The evaluated {window} is comparatively supportive; this is not a "
            "guaranteed outcome or an exact clock-time election.",
            None,
        )
    if outlook is Outlook.CHALLENGING:
        return (
            "Proceed cautiously, reduce avoidable exposure, and delay "
            "non-essential commitments when practical.",
            None,
            f"The evaluated {window} carries comparatively challenging indications; "
            "this does not guarantee harm.",
        )
    if outlook is Outlook.MIXED:
        return (
            "Act selectively: use the supporting factors and actively mitigate "
            "the stated challenges.",
            f"Parts of the evaluated {window} are supportive, but no exact "
            "clock-time window has been validated.",
            f"Parts of the evaluated {window} require caution; the evidence "
            "does not identify an exact clock time.",
        )
    return (
        "No directional advisory is justified from the available evidence.",
        None,
        None,
    )


def _evaluate_domain(period: str, domain: str, evidence: tuple[Evidence, ...]) -> DomainResult:
    evidence = _deduplicate_evidence(evidence)
    supporting = tuple(item for item in evidence if item.polarity is Polarity.SUPPORTING)
    challenging = tuple(item for item in evidence if item.polarity is Polarity.CHALLENGING)
    contextual = tuple(item for item in evidence if item.polarity is Polarity.CONTEXTUAL)

    supporting_score = round(sum(item.weight for item in supporting), 6)
    challenging_score = round(sum(item.weight for item in challenging), 6)
    net_score = round(supporting_score - challenging_score, 6)
    outlook = _outlook(supporting_score, challenging_score)
    strength = _strength(supporting_score, challenging_score, net_score)
    advisory, favourable_timing, challenging_timing = _timing(period, outlook)

    return DomainResult(
        domain=domain,
        outlook=outlook,
        strength=strength,
        supporting_score=supporting_score,
        challenging_score=challenging_score,
        net_score=net_score,
        statement=_statement(domain, outlook, strength),
        advisory=advisory,
        favourable_timing=favourable_timing,
        challenging_timing=challenging_timing,
        supporting_factors=supporting,
        challenging_factors=challenging,
        contextual_factors=contextual,
    )


def evaluate(request: PredictionRequest) -> PredictionResponse:
    grouped: dict[str, list[Evidence]] = defaultdict(list)
    for item in request.evidence:
        if item.domain in BLOCKED_DOMAINS:
            raise ValueError(f"consumer prediction domain is blocked: {item.domain}")
        grouped[item.domain].append(item)

    results = tuple(
        _evaluate_domain(request.period, domain, tuple(grouped[domain]))
        for domain in sorted(grouped)
    )
    return PredictionResponse(
        engine_version=ENGINE_VERSION,
        calculation_profile=request.calculation_profile,
        classical_profile=request.classical_profile,
        period=request.period,
        as_of=request.as_of,
        results=results,
        disclaimer=ASTROLOGY_DISCLAIMER,
    )
