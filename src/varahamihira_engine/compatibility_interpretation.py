from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .outlook_index import (
    ConfidenceStatus,
    ConflictStatus,
    OutlookDomain,
    OutlookIndex,
    calculate_outlook_index,
)

COMPATIBILITY_INTERPRETATION_VERSION = "compatibility_interpretation_v1"
SUPPORTED_COMPATIBILITY_FACTS_VERSION = "compatibility_facts_v2"
COMPATIBILITY_TOTAL_POINTS = 36
COMPATIBILITY_DISCLAIMER = (
    "This compatibility report is a traditional interpretive comparison aid. "
    "It is not a probability, guarantee, diagnosis, or decision about whether a "
    "relationship or marriage will succeed."
)


class CompatibilityComponent(StrEnum):
    VARNA = "varna"
    VASHYA = "vashya"
    TARA = "tara"
    YONI = "yoni"
    GRAHA_MAITRI = "graha_maitri"
    GANA = "gana"
    BHAKOOT = "bhakoot"
    NADI = "nadi"


COMPONENT_MAXIMUM_POINTS: dict[CompatibilityComponent, int] = {
    CompatibilityComponent.VARNA: 1,
    CompatibilityComponent.VASHYA: 2,
    CompatibilityComponent.TARA: 3,
    CompatibilityComponent.YONI: 4,
    CompatibilityComponent.GRAHA_MAITRI: 5,
    CompatibilityComponent.GANA: 6,
    CompatibilityComponent.BHAKOOT: 7,
    CompatibilityComponent.NADI: 8,
}


class ComponentEvaluationStatus(StrEnum):
    EVALUATED = "evaluated"
    ABSTAINED = "abstained"


class ComponentInterpretationBand(StrEnum):
    INSUFFICIENT = "insufficient"
    CHALLENGING = "challenging"
    MIXED = "mixed"
    SUPPORTIVE = "supportive"


class ManglikReferencePoint(StrEnum):
    LAGNA = "lagna"
    MOON = "moon"
    VENUS = "venus"


@dataclass(frozen=True, slots=True)
class CompatibilityComponentInput:
    component: CompatibilityComponent
    status: ComponentEvaluationStatus
    achieved_points: float | None
    maximum_points: int
    rule_ids: tuple[str, ...]
    calculation_notes: tuple[str, ...] = ()
    abstention_reason: str | None = None

    def __post_init__(self) -> None:
        expected_maximum = COMPONENT_MAXIMUM_POINTS[self.component]
        if self.maximum_points != expected_maximum:
            raise ValueError(
                f"{self.component.value} maximum_points must be {expected_maximum}"
            )
        if not self.rule_ids or any(not item.strip() for item in self.rule_ids):
            raise ValueError("compatibility components require non-blank rule IDs")
        if self.status is ComponentEvaluationStatus.EVALUATED:
            if self.achieved_points is None:
                raise ValueError("evaluated components require achieved_points")
            if not 0.0 <= self.achieved_points <= self.maximum_points:
                raise ValueError("achieved_points must be within the component maximum")
            if self.abstention_reason is not None:
                raise ValueError("evaluated components cannot include abstention_reason")
        else:
            if self.achieved_points is not None:
                raise ValueError("abstained components cannot include achieved_points")
            if self.abstention_reason is None or not self.abstention_reason.strip():
                raise ValueError("abstained components require an abstention_reason")


@dataclass(frozen=True, slots=True)
class ManglikFactorInput:
    reference_point: ManglikReferencePoint
    mars_house: int
    flagged: bool
    rule_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 1 <= self.mars_house <= 12:
            raise ValueError("mars_house must be between 1 and 12")
        if not self.rule_ids or any(not item.strip() for item in self.rule_ids):
            raise ValueError("Manglik factors require non-blank rule IDs")


@dataclass(frozen=True, slots=True)
class CompatibilityInterpretationRequest:
    facts_version: str
    components: tuple[CompatibilityComponentInput, ...]
    total_achieved_points: float
    evaluated_maximum_points: int
    complete_36_point_evaluation: bool
    subject_manglik_factors: tuple[ManglikFactorInput, ...]
    partner_manglik_factors: tuple[ManglikFactorInput, ...]

    def __post_init__(self) -> None:
        if self.facts_version != SUPPORTED_COMPATIBILITY_FACTS_VERSION:
            raise ValueError("unsupported compatibility facts version")
        component_names = tuple(item.component for item in self.components)
        if len(component_names) != len(CompatibilityComponent):
            raise ValueError("all eight compatibility components are required")
        if len(set(component_names)) != len(CompatibilityComponent):
            raise ValueError("compatibility components must appear exactly once")
        if set(component_names) != set(CompatibilityComponent):
            raise ValueError("compatibility component set is incomplete")

        evaluated = tuple(
            item
            for item in self.components
            if item.status is ComponentEvaluationStatus.EVALUATED
        )
        expected_total = sum(item.achieved_points or 0.0 for item in evaluated)
        if abs(expected_total - self.total_achieved_points) > 1e-6:
            raise ValueError("total_achieved_points does not match component facts")
        expected_maximum = sum(item.maximum_points for item in evaluated)
        if expected_maximum != self.evaluated_maximum_points:
            raise ValueError("evaluated_maximum_points does not match component facts")
        if not 0 <= self.evaluated_maximum_points <= COMPATIBILITY_TOTAL_POINTS:
            raise ValueError("evaluated_maximum_points must be between 0 and 36")
        if self.complete_36_point_evaluation is not (
            self.evaluated_maximum_points == COMPATIBILITY_TOTAL_POINTS
        ):
            raise ValueError("complete_36_point_evaluation does not match coverage")

        for label, factors in (
            ("subject", self.subject_manglik_factors),
            ("partner", self.partner_manglik_factors),
        ):
            references = tuple(item.reference_point for item in factors)
            if set(references) != set(ManglikReferencePoint) or len(references) != 3:
                raise ValueError(
                    f"{label} Manglik factors must include Lagna, Moon, and Venus once"
                )


@dataclass(frozen=True, slots=True)
class ComponentInterpretation:
    component: CompatibilityComponent
    status: ComponentEvaluationStatus
    achieved_points: float | None
    maximum_points: int
    ratio: float | None
    band: ComponentInterpretationBand
    headline: str
    explanation: str
    evidence_refs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "component": self.component.value,
            "status": self.status.value,
            "achieved_points": self.achieved_points,
            "maximum_points": self.maximum_points,
            "ratio": self.ratio,
            "band": self.band.value,
            "headline": self.headline,
            "explanation": self.explanation,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ManglikContext:
    subject_flagged_count: int
    partner_flagged_count: int
    comparison: str
    evidence_refs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_flagged_count": self.subject_flagged_count,
            "partner_flagged_count": self.partner_flagged_count,
            "comparison": self.comparison,
            "evidence_refs": list(self.evidence_refs),
            "disclaimer": (
                "Manglik placements are contextual factors, not automatic rejection rules."
            ),
        }


@dataclass(frozen=True, slots=True)
class CompatibilityInterpretationResponse:
    interpretation_version: str
    facts_version: str
    evaluated_maximum_points: int
    complete_36_point_evaluation: bool
    partnership_index: OutlookIndex
    components: tuple[ComponentInterpretation, ...]
    strengths: tuple[str, ...]
    cautions: tuple[str, ...]
    manglik_context: ManglikContext
    disclaimer: str = COMPATIBILITY_DISCLAIMER

    def as_dict(self) -> dict[str, Any]:
        return {
            "interpretation_version": self.interpretation_version,
            "facts_version": self.facts_version,
            "evaluated_maximum_points": self.evaluated_maximum_points,
            "complete_36_point_evaluation": self.complete_36_point_evaluation,
            "partnership_index": self.partnership_index.as_dict(),
            "components": [item.as_dict() for item in self.components],
            "strengths": list(self.strengths),
            "cautions": list(self.cautions),
            "manglik_context": self.manglik_context.as_dict(),
            "disclaimer": self.disclaimer,
        }


_COMPONENT_LABELS = {
    CompatibilityComponent.VARNA: "Traditional role alignment",
    CompatibilityComponent.VASHYA: "Mutual influence pattern",
    CompatibilityComponent.TARA: "Reciprocal Nakshatra support",
    CompatibilityComponent.YONI: "Instinctive interaction pattern",
    CompatibilityComponent.GRAHA_MAITRI: "Moon-sign-lord rapport",
    CompatibilityComponent.GANA: "Temperament pattern",
    CompatibilityComponent.BHAKOOT: "Moon-sign relationship pattern",
    CompatibilityComponent.NADI: "Traditional Nadi comparison",
}


def _interpret_component(item: CompatibilityComponentInput) -> ComponentInterpretation:
    label = _COMPONENT_LABELS[item.component]
    if item.status is ComponentEvaluationStatus.ABSTAINED:
        return ComponentInterpretation(
            component=item.component,
            status=item.status,
            achieved_points=None,
            maximum_points=item.maximum_points,
            ratio=None,
            band=ComponentInterpretationBand.INSUFFICIENT,
            headline=f"{label}: not evaluated",
            explanation=(
                f"This component was not scored because {item.abstention_reason}. "
                "No zero score was substituted."
            ),
            evidence_refs=item.rule_ids,
        )

    ratio = (item.achieved_points or 0.0) / item.maximum_points
    if ratio >= 0.75:
        band = ComponentInterpretationBand.SUPPORTIVE
        headline = f"{label}: supportive"
        explanation = (
            "This traditional component is comparatively supportive within the "
            "selected convention. Treat it as one part of the whole comparison."
        )
    elif ratio >= 0.40:
        band = ComponentInterpretationBand.MIXED
        headline = f"{label}: mixed"
        explanation = (
            "This traditional component contains both supportive and challenging "
            "signals. Clear communication and realistic expectations remain important."
        )
    else:
        band = ComponentInterpretationBand.CHALLENGING
        headline = f"{label}: requires attention"
        explanation = (
            "This traditional component is comparatively challenging in the selected "
            "table. It is a discussion point, not a prediction of relationship failure."
        )
    return ComponentInterpretation(
        component=item.component,
        status=item.status,
        achieved_points=item.achieved_points,
        maximum_points=item.maximum_points,
        ratio=round(ratio, 6),
        band=band,
        headline=headline,
        explanation=explanation,
        evidence_refs=item.rule_ids,
    )


def _manglik_context(request: CompatibilityInterpretationRequest) -> ManglikContext:
    subject_count = sum(item.flagged for item in request.subject_manglik_factors)
    partner_count = sum(item.flagged for item in request.partner_manglik_factors)
    if subject_count == partner_count:
        comparison = (
            "Both charts have the same number of flagged Mars reference-point placements. "
            "This is contextual information only; no cancellation is inferred."
        )
    else:
        comparison = (
            "The charts have different numbers of flagged Mars reference-point placements. "
            "This difference should not be used as an automatic acceptance or rejection rule."
        )
    evidence_refs = tuple(
        dict.fromkeys(
            rule_id
            for factor in (
                *request.subject_manglik_factors,
                *request.partner_manglik_factors,
            )
            for rule_id in factor.rule_ids
        )
    )
    return ManglikContext(
        subject_flagged_count=subject_count,
        partner_flagged_count=partner_count,
        comparison=comparison,
        evidence_refs=evidence_refs,
    )


def interpret_compatibility(
    request: CompatibilityInterpretationRequest,
) -> CompatibilityInterpretationResponse:
    component_results = tuple(_interpret_component(item) for item in request.components)
    evaluated_results = tuple(
        item
        for item in component_results
        if item.status is ComponentEvaluationStatus.EVALUATED
    )
    ratios = tuple(item.ratio or 0.0 for item in evaluated_results)
    conflict_status = ConflictStatus.NONE
    if ratios and max(ratios) >= 0.75 and min(ratios) < 0.40:
        conflict_status = ConflictStatus.INTERNAL_CONFLICT

    if request.evaluated_maximum_points:
        supporting = request.total_achieved_points / request.evaluated_maximum_points
    else:
        supporting = 0.0
    challenging = 1.0 - supporting if request.evaluated_maximum_points else 0.0
    coverage = request.evaluated_maximum_points / COMPATIBILITY_TOTAL_POINTS
    evidence_refs = tuple(
        dict.fromkeys(
            rule_id
            for component in request.components
            for rule_id in component.rule_ids
        )
    )
    partnership_index = calculate_outlook_index(
        domain=OutlookDomain.PARTNERSHIP,
        supporting_component=supporting,
        challenging_component=challenging,
        coverage=coverage,
        confidence_status=(
            ConfidenceStatus.UNCALIBRATED_MODERATE
            if request.complete_36_point_evaluation
            else ConfidenceStatus.UNCALIBRATED_LOW
        ),
        conflict_status=conflict_status,
        evidence_refs=evidence_refs,
    )

    supportive = sorted(
        (
            item
            for item in component_results
            if item.band is ComponentInterpretationBand.SUPPORTIVE
        ),
        key=lambda item: item.ratio or 0.0,
        reverse=True,
    )
    challenging_items = sorted(
        (
            item
            for item in component_results
            if item.band is ComponentInterpretationBand.CHALLENGING
        ),
        key=lambda item: item.ratio or 0.0,
    )
    strengths = tuple(item.headline for item in supportive[:3])
    cautions = tuple(item.headline for item in challenging_items[:3])
    if not request.complete_36_point_evaluation:
        cautions = (
            *cautions,
            "The comparison is partial because one or more directional components abstained.",
        )

    return CompatibilityInterpretationResponse(
        interpretation_version=COMPATIBILITY_INTERPRETATION_VERSION,
        facts_version=request.facts_version,
        evaluated_maximum_points=request.evaluated_maximum_points,
        complete_36_point_evaluation=request.complete_36_point_evaluation,
        partnership_index=partnership_index,
        components=component_results,
        strengths=strengths,
        cautions=cautions,
        manglik_context=_manglik_context(request),
    )
