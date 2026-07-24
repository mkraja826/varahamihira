from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from statistics import mean
from typing import Any, Iterable

from .models import Polarity
from .outlook_index import (
    ConfidenceStatus,
    ConflictStatus,
    OutlookDomain,
    OutlookIndex,
    calculate_outlook_index,
)

LIFE_PROFILE_FACTS_VERSION = "life_profile_facts_v1"
LIFE_PROFILE_INTERPRETATION_VERSION = "life_profile_interpretation_v1"
PERIOD_ANALYSIS_FACTS_VERSION = "period_analysis_facts_v1"
PERIOD_ANALYSIS_INTERPRETATION_VERSION = "period_analysis_interpretation_v1"

LIFE_PROFILE_DISCLAIMER = (
    "This life profile is a source-traceable traditional interpretation. It describes "
    "tendencies and themes, not fixed traits, probabilities, diagnoses, guarantees, or "
    "instructions to make major life decisions."
)
PERIOD_ANALYSIS_DISCLAIMER = (
    "This period analysis is an interpretive comparison of sampled astrological evidence. "
    "It is not a probability or a guarantee of events, dates, health, relationships, or money."
)


class LifeProfileSectionName(StrEnum):
    CHARACTER = "character_temperament"
    STRENGTHS_GROWTH = "strengths_growth"
    RELATIONSHIP_STYLE = "relationship_style"
    FINANCE_STYLE = "finance_style"
    CAREER_STYLE = "career_style"
    WELLBEING = "wellbeing"
    PARTNERSHIP = "partnership"
    OPPORTUNITY = "opportunity"
    HAPPINESS = "happiness"
    OVERALL = "overall"


@dataclass(frozen=True, slots=True)
class AnalysisEvidence:
    evidence_id: str
    domain: str
    statement: str
    polarity: Polarity
    weight: float
    source_rule_ids: tuple[str, ...]
    source_kind: str
    reason: str

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.domain.strip() or not self.statement.strip():
            raise ValueError("analysis evidence requires non-blank identifiers and text")
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("analysis evidence weight must be between 0 and 1")
        if self.source_kind not in {"classical", "convention"}:
            raise ValueError("analysis evidence source_kind must be classical or convention")
        if self.source_kind == "classical" and not self.source_rule_ids:
            raise ValueError("classical analysis evidence requires rule IDs")

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "domain": self.domain,
            "statement": self.statement,
            "polarity": self.polarity.value,
            "weight": self.weight,
            "source_rule_ids": list(self.source_rule_ids),
            "source_kind": self.source_kind,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class AnalysisDomainSnapshot:
    domain: str
    supporting: tuple[AnalysisEvidence, ...]
    challenging: tuple[AnalysisEvidence, ...]
    contextual: tuple[AnalysisEvidence, ...]
    coverage: float

    def __post_init__(self) -> None:
        if not self.domain.strip():
            raise ValueError("analysis domain is required")
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError("analysis domain coverage must be between 0 and 1")
        for item in self.supporting:
            if item.polarity is not Polarity.SUPPORTING:
                raise ValueError("supporting evidence has the wrong polarity")
        for item in self.challenging:
            if item.polarity is not Polarity.CHALLENGING:
                raise ValueError("challenging evidence has the wrong polarity")
        for item in self.contextual:
            if item.polarity is not Polarity.CONTEXTUAL:
                raise ValueError("contextual evidence has the wrong polarity")


@dataclass(frozen=True, slots=True)
class AnalysisSnapshot:
    as_of: str
    domains: tuple[AnalysisDomainSnapshot, ...]

    def __post_init__(self) -> None:
        if not self.as_of.strip():
            raise ValueError("analysis snapshot as_of is required")
        names = tuple(item.domain for item in self.domains)
        if not names or len(set(names)) != len(names):
            raise ValueError("analysis snapshot domains must be non-empty and unique")

    def by_name(self) -> dict[str, AnalysisDomainSnapshot]:
        return {item.domain: item for item in self.domains}


@dataclass(frozen=True, slots=True)
class LifeProfileInterpretationRequest:
    facts_version: str
    snapshot: AnalysisSnapshot

    def __post_init__(self) -> None:
        if self.facts_version != LIFE_PROFILE_FACTS_VERSION:
            raise ValueError("unsupported life-profile facts version")


@dataclass(frozen=True, slots=True)
class MonthAnalysisInput:
    year: int
    month: int
    sample_local_datetime: str
    snapshot: AnalysisSnapshot
    sampling_method: str
    exact_boundary_calculation_applied: bool
    channels_available: tuple[str, ...]
    channels_unavailable: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 1900 <= self.year <= 2200:
            raise ValueError("analysis year must be between 1900 and 2200")
        if not 1 <= self.month <= 12:
            raise ValueError("analysis month must be between 1 and 12")
        if not self.sample_local_datetime.strip() or not self.sampling_method.strip():
            raise ValueError("month analysis sampling metadata is required")
        if self.exact_boundary_calculation_applied:
            raise ValueError("period_analysis_v1 does not support exact boundary claims")
        if not self.channels_available:
            raise ValueError("at least one analysis channel must be available")


@dataclass(frozen=True, slots=True)
class MonthInterpretationRequest:
    facts_version: str
    month: MonthAnalysisInput

    def __post_init__(self) -> None:
        if self.facts_version != PERIOD_ANALYSIS_FACTS_VERSION:
            raise ValueError("unsupported month-analysis facts version")


@dataclass(frozen=True, slots=True)
class YearInterpretationRequest:
    facts_version: str
    year: int
    months: tuple[MonthAnalysisInput, ...]

    def __post_init__(self) -> None:
        if self.facts_version != PERIOD_ANALYSIS_FACTS_VERSION:
            raise ValueError("unsupported year-analysis facts version")
        if not 1900 <= self.year <= 2200:
            raise ValueError("analysis year must be between 1900 and 2200")
        if len(self.months) != 12:
            raise ValueError("year analysis requires twelve months")
        if tuple(item.month for item in self.months) != tuple(range(1, 13)):
            raise ValueError("year analysis months must be ordered January through December")
        if any(item.year != self.year for item in self.months):
            raise ValueError("year analysis month year mismatch")


@dataclass(frozen=True, slots=True)
class InterpretedSection:
    section: str
    headline: str
    narrative: str
    guidance: str
    confidence_status: ConfidenceStatus
    conflict_status: ConflictStatus
    supporting_evidence: tuple[AnalysisEvidence, ...]
    challenging_evidence: tuple[AnalysisEvidence, ...]
    contextual_evidence: tuple[AnalysisEvidence, ...]
    outlook_index: OutlookIndex | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "headline": self.headline,
            "narrative": self.narrative,
            "guidance": self.guidance,
            "confidence_status": self.confidence_status.value,
            "conflict_status": self.conflict_status.value,
            "supporting_evidence": [item.as_dict() for item in self.supporting_evidence],
            "challenging_evidence": [item.as_dict() for item in self.challenging_evidence],
            "contextual_evidence": [item.as_dict() for item in self.contextual_evidence],
            "outlook_index": self.outlook_index.as_dict() if self.outlook_index else None,
        }


@dataclass(frozen=True, slots=True)
class LifeProfileInterpretationResponse:
    interpretation_version: str
    facts_version: str
    as_of: str
    sections: tuple[InterpretedSection, ...]
    disclaimer: str = LIFE_PROFILE_DISCLAIMER

    def as_dict(self) -> dict[str, Any]:
        return {
            "interpretation_version": self.interpretation_version,
            "facts_version": self.facts_version,
            "as_of": self.as_of,
            "sections": [item.as_dict() for item in self.sections],
            "disclaimer": self.disclaimer,
        }


@dataclass(frozen=True, slots=True)
class MonthInterpretationResponse:
    interpretation_version: str
    facts_version: str
    year: int
    month: int
    sample_local_datetime: str
    sampling_method: str
    exact_boundary_calculation_applied: bool
    channels_available: tuple[str, ...]
    channels_unavailable: tuple[str, ...]
    indices: tuple[OutlookIndex, ...]
    sections: tuple[InterpretedSection, ...]
    disclaimer: str = PERIOD_ANALYSIS_DISCLAIMER

    def as_dict(self) -> dict[str, Any]:
        return {
            "interpretation_version": self.interpretation_version,
            "facts_version": self.facts_version,
            "year": self.year,
            "month": self.month,
            "sample_local_datetime": self.sample_local_datetime,
            "sampling_method": self.sampling_method,
            "exact_boundary_calculation_applied": self.exact_boundary_calculation_applied,
            "channels_available": list(self.channels_available),
            "channels_unavailable": list(self.channels_unavailable),
            "indices": [item.as_dict() for item in self.indices],
            "sections": [item.as_dict() for item in self.sections],
            "disclaimer": self.disclaimer,
        }


@dataclass(frozen=True, slots=True)
class YearInterpretationResponse:
    interpretation_version: str
    facts_version: str
    year: int
    overview_indices: tuple[OutlookIndex, ...]
    months: tuple[MonthInterpretationResponse, ...]
    strongest_months: tuple[int, ...]
    challenging_months: tuple[int, ...]
    disclaimer: str = PERIOD_ANALYSIS_DISCLAIMER

    def as_dict(self) -> dict[str, Any]:
        return {
            "interpretation_version": self.interpretation_version,
            "facts_version": self.facts_version,
            "year": self.year,
            "overview_indices": [item.as_dict() for item in self.overview_indices],
            "months": [item.as_dict() for item in self.months],
            "strongest_months": list(self.strongest_months),
            "challenging_months": list(self.challenging_months),
            "disclaimer": self.disclaimer,
        }


_SECTION_SOURCES: dict[LifeProfileSectionName, tuple[str, ...]] = {
    LifeProfileSectionName.CHARACTER: ("overall", "family_home", "education_creativity"),
    LifeProfileSectionName.STRENGTHS_GROWTH: ("overall", "career", "education_creativity"),
    LifeProfileSectionName.RELATIONSHIP_STYLE: ("relationships_marriage", "family_home"),
    LifeProfileSectionName.FINANCE_STYLE: ("money_resources",),
    LifeProfileSectionName.CAREER_STYLE: ("career",),
    LifeProfileSectionName.WELLBEING: ("wellbeing",),
    LifeProfileSectionName.PARTNERSHIP: ("relationships_marriage",),
    LifeProfileSectionName.OPPORTUNITY: ("career", "travel_change", "education_creativity"),
    LifeProfileSectionName.HAPPINESS: ("family_home", "spirituality"),
    LifeProfileSectionName.OVERALL: (
        "overall",
        "career",
        "money_resources",
        "relationships_marriage",
        "family_home",
        "education_creativity",
        "wellbeing",
        "travel_change",
        "spirituality",
    ),
}
_SECTION_INDEX_DOMAIN: dict[LifeProfileSectionName, OutlookDomain] = {
    LifeProfileSectionName.RELATIONSHIP_STYLE: OutlookDomain.LOVE,
    LifeProfileSectionName.FINANCE_STYLE: OutlookDomain.FINANCE,
    LifeProfileSectionName.WELLBEING: OutlookDomain.WELLBEING,
    LifeProfileSectionName.PARTNERSHIP: OutlookDomain.PARTNERSHIP,
    LifeProfileSectionName.OPPORTUNITY: OutlookDomain.OPPORTUNITY,
    LifeProfileSectionName.HAPPINESS: OutlookDomain.HAPPINESS,
    LifeProfileSectionName.OVERALL: OutlookDomain.OVERALL,
}
_PERIOD_SOURCES: dict[OutlookDomain, tuple[str, ...]] = {
    OutlookDomain.LOVE: ("relationships_marriage",),
    OutlookDomain.FINANCE: ("money_resources",),
    OutlookDomain.WELLBEING: ("wellbeing",),
    OutlookDomain.PARTNERSHIP: ("relationships_marriage",),
    OutlookDomain.OPPORTUNITY: ("career", "travel_change", "education_creativity"),
    OutlookDomain.HAPPINESS: ("family_home", "spirituality"),
    OutlookDomain.OVERALL: (
        "overall",
        "career",
        "money_resources",
        "relationships_marriage",
        "family_home",
        "education_creativity",
        "wellbeing",
        "travel_change",
        "spirituality",
    ),
}


def _dedupe(items: Iterable[AnalysisEvidence]) -> tuple[AnalysisEvidence, ...]:
    seen: set[str] = set()
    result: list[AnalysisEvidence] = []
    for item in items:
        if item.evidence_id not in seen:
            seen.add(item.evidence_id)
            result.append(item)
    return tuple(result)


def _collect(snapshot: AnalysisSnapshot, sources: tuple[str, ...]) -> tuple[
    tuple[AnalysisEvidence, ...],
    tuple[AnalysisEvidence, ...],
    tuple[AnalysisEvidence, ...],
    float,
]:
    by_name = snapshot.by_name()
    available = [by_name[name] for name in sources if name in by_name]
    if not available:
        return (), (), (), 0.0
    supporting = _dedupe(item for domain in available for item in domain.supporting)
    challenging = _dedupe(item for domain in available for item in domain.challenging)
    contextual = _dedupe(item for domain in available for item in domain.contextual)
    coverage = round(
        min(1.0, (len(available) / len(sources)) * mean(item.coverage for item in available)),
        6,
    )
    return supporting, challenging, contextual, coverage


def _component(items: tuple[AnalysisEvidence, ...]) -> float:
    if not items:
        return 0.0
    return round(min(1.0, sum(item.weight for item in items) / max(1.0, len(items))), 6)


def _confidence(coverage: float, evidence_count: int) -> ConfidenceStatus:
    if coverage < 0.50 or evidence_count == 0:
        return ConfidenceStatus.INSUFFICIENT
    if coverage >= 0.75 and evidence_count >= 3:
        return ConfidenceStatus.UNCALIBRATED_MODERATE
    return ConfidenceStatus.UNCALIBRATED_LOW


def _conflict(
    supporting: tuple[AnalysisEvidence, ...],
    challenging: tuple[AnalysisEvidence, ...],
    confidence: ConfidenceStatus,
) -> ConflictStatus:
    if confidence is ConfidenceStatus.INSUFFICIENT:
        return ConflictStatus.INSUFFICIENT
    if supporting and challenging:
        return ConflictStatus.INTERNAL_CONFLICT
    return ConflictStatus.NONE


def _section_copy(section: str, index: OutlookIndex | None, conflict: ConflictStatus) -> tuple[str, str, str]:
    label = section.replace("_", " ").title()
    if index is None or index.score is None:
        return (
            f"{label}: limited evidence",
            "The currently available source-traceable channels are not sufficient for a numeric comparison.",
            "Use this section as context only and avoid fixed conclusions.",
        )
    band = index.band.value.replace("_", " ") if index.band else "mixed"
    conflict_copy = (
        " Supporting and challenging factors are both present."
        if conflict is not ConflictStatus.NONE
        else ""
    )
    return (
        f"{label}: {band}",
        f"The available evidence produces a {band} interpretive pattern.{conflict_copy}",
        "Treat the result as a reflection prompt; compare it with lived experience and current circumstances.",
    )


def _interpret_section(
    snapshot: AnalysisSnapshot,
    *,
    section: str,
    sources: tuple[str, ...],
    index_domain: OutlookDomain | None,
) -> InterpretedSection:
    supporting, challenging, contextual, coverage = _collect(snapshot, sources)
    confidence = _confidence(coverage, len(supporting) + len(challenging))
    conflict = _conflict(supporting, challenging, confidence)
    index = None
    if index_domain is not None:
        index = calculate_outlook_index(
            domain=index_domain,
            supporting_component=_component(supporting),
            challenging_component=_component(challenging),
            coverage=coverage,
            confidence_status=confidence,
            conflict_status=conflict,
            evidence_refs=tuple(item.evidence_id for item in (*supporting, *challenging)),
        )
    headline, narrative, guidance = _section_copy(section, index, conflict)
    return InterpretedSection(
        section=section,
        headline=headline,
        narrative=narrative,
        guidance=guidance,
        confidence_status=confidence,
        conflict_status=conflict,
        supporting_evidence=supporting,
        challenging_evidence=challenging,
        contextual_evidence=contextual,
        outlook_index=index,
    )


def interpret_life_profile(
    request: LifeProfileInterpretationRequest,
) -> LifeProfileInterpretationResponse:
    sections = tuple(
        _interpret_section(
            request.snapshot,
            section=section.value,
            sources=_SECTION_SOURCES[section],
            index_domain=_SECTION_INDEX_DOMAIN.get(section),
        )
        for section in LifeProfileSectionName
    )
    return LifeProfileInterpretationResponse(
        interpretation_version=LIFE_PROFILE_INTERPRETATION_VERSION,
        facts_version=request.facts_version,
        as_of=request.snapshot.as_of,
        sections=sections,
    )


def interpret_month_analysis(
    request: MonthInterpretationRequest,
) -> MonthInterpretationResponse:
    sections = tuple(
        _interpret_section(
            request.month.snapshot,
            section=domain.value,
            sources=sources,
            index_domain=domain,
        )
        for domain, sources in _PERIOD_SOURCES.items()
    )
    return MonthInterpretationResponse(
        interpretation_version=PERIOD_ANALYSIS_INTERPRETATION_VERSION,
        facts_version=request.facts_version,
        year=request.month.year,
        month=request.month.month,
        sample_local_datetime=request.month.sample_local_datetime,
        sampling_method=request.month.sampling_method,
        exact_boundary_calculation_applied=request.month.exact_boundary_calculation_applied,
        channels_available=request.month.channels_available,
        channels_unavailable=request.month.channels_unavailable,
        indices=tuple(item.outlook_index for item in sections if item.outlook_index is not None),
        sections=sections,
    )


def _overview_index(
    domain: OutlookDomain,
    months: tuple[MonthInterpretationResponse, ...],
) -> OutlookIndex:
    indices = [next(item for item in month.indices if item.domain is domain) for month in months]
    scored = [item for item in indices if item.score is not None]
    coverage = round(mean(item.coverage for item in indices), 6)
    confidence = (
        ConfidenceStatus.UNCALIBRATED_MODERATE
        if len(scored) == 12 and coverage >= 0.75
        else ConfidenceStatus.UNCALIBRATED_LOW
        if len(scored) >= 6
        else ConfidenceStatus.INSUFFICIENT
    )
    conflict = (
        ConflictStatus.CROSS_CHANNEL_CONFLICT
        if any(item.conflict_status is not ConflictStatus.NONE for item in scored)
        else ConflictStatus.NONE
    )
    refs = tuple(dict.fromkeys(ref for item in scored for ref in item.evidence_refs))
    return calculate_outlook_index(
        domain=domain,
        supporting_component=round(mean(item.supporting_component for item in indices), 6),
        challenging_component=round(mean(item.challenging_component for item in indices), 6),
        coverage=coverage,
        confidence_status=confidence,
        conflict_status=conflict,
        evidence_refs=refs,
    )


def interpret_year_analysis(
    request: YearInterpretationRequest,
) -> YearInterpretationResponse:
    months = tuple(
        interpret_month_analysis(
            MonthInterpretationRequest(
                facts_version=request.facts_version,
                month=month,
            )
        )
        for month in request.months
    )
    overview = tuple(_overview_index(domain, months) for domain in _PERIOD_SOURCES)
    overall_scores = [
        (month.month, next(item.score for item in month.indices if item.domain is OutlookDomain.OVERALL))
        for month in months
    ]
    scored = [(month, score) for month, score in overall_scores if score is not None]
    strongest = tuple(month for month, _ in sorted(scored, key=lambda item: (-item[1], item[0]))[:3])
    challenging = tuple(month for month, _ in sorted(scored, key=lambda item: (item[1], item[0]))[:3])
    return YearInterpretationResponse(
        interpretation_version=PERIOD_ANALYSIS_INTERPRETATION_VERSION,
        facts_version=request.facts_version,
        year=request.year,
        overview_indices=overview,
        months=months,
        strongest_months=strongest,
        challenging_months=challenging,
    )


def analysis_snapshot_from_prediction(payload: dict[str, Any]) -> AnalysisSnapshot:
    expected = {
        "engine_version",
        "calculation_profile",
        "classical_profile",
        "period",
        "as_of",
        "results",
        "disclaimer",
    }
    if set(payload) != expected:
        raise ValueError("prediction payload fields do not match the analysis adapter contract")
    raw_results = payload.get("results")
    if not isinstance(raw_results, list) or not raw_results:
        raise ValueError("prediction payload requires non-empty results")
    domains: list[AnalysisDomainSnapshot] = []
    for raw in raw_results:
        if not isinstance(raw, dict):
            raise ValueError("prediction result must be an object")
        domain = str(raw.get("domain", "")).strip()
        supporting = _parse_evidence(raw.get("supporting_factors"), Polarity.SUPPORTING)
        challenging = _parse_evidence(raw.get("challenging_factors"), Polarity.CHALLENGING)
        contextual = _parse_evidence(raw.get("contextual_factors"), Polarity.CONTEXTUAL)
        total = len(supporting) + len(challenging) + len(contextual)
        domains.append(
            AnalysisDomainSnapshot(
                domain=domain,
                supporting=supporting,
                challenging=challenging,
                contextual=contextual,
                coverage=1.0 if total else 0.0,
            )
        )
    return AnalysisSnapshot(as_of=str(payload.get("as_of", "")), domains=tuple(domains))


def _parse_evidence(value: Any, expected_polarity: Polarity) -> tuple[AnalysisEvidence, ...]:
    if not isinstance(value, list):
        raise ValueError("prediction evidence groups must be lists")
    parsed: list[AnalysisEvidence] = []
    for raw in value:
        if not isinstance(raw, dict):
            raise ValueError("prediction evidence must be an object")
        polarity = Polarity(str(raw.get("polarity", "")))
        if polarity is not expected_polarity:
            raise ValueError("prediction evidence polarity mismatch")
        rule_ids = raw.get("source_rule_ids")
        if not isinstance(rule_ids, list) or any(not isinstance(item, str) for item in rule_ids):
            raise ValueError("prediction evidence rule IDs must be strings")
        parsed.append(
            AnalysisEvidence(
                evidence_id=str(raw.get("evidence_id", "")),
                domain=str(raw.get("domain", "")),
                statement=str(raw.get("statement", "")),
                polarity=polarity,
                weight=float(raw.get("weight", 0.0)),
                source_rule_ids=tuple(rule_ids),
                source_kind=str(raw.get("source_kind", "")),
                reason=str(raw.get("reason", "")),
            )
        )
    return tuple(parsed)
