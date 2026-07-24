import pytest

from varahamihira_engine.compatibility_interpretation import (
    COMPATIBILITY_DISCLAIMER,
    COMPATIBILITY_INTERPRETATION_VERSION,
    CompatibilityComponent,
    CompatibilityComponentInput,
    CompatibilityInterpretationRequest,
    ComponentEvaluationStatus,
    ComponentInterpretationBand,
    ManglikFactorInput,
    ManglikReferencePoint,
    interpret_compatibility,
)
from varahamihira_engine.outlook_index import (
    ConfidenceStatus,
    ConflictStatus,
    OutlookDomain,
)

MAXIMUMS = {
    CompatibilityComponent.VARNA: 1,
    CompatibilityComponent.VASHYA: 2,
    CompatibilityComponent.TARA: 3,
    CompatibilityComponent.YONI: 4,
    CompatibilityComponent.GRAHA_MAITRI: 5,
    CompatibilityComponent.GANA: 6,
    CompatibilityComponent.BHAKOOT: 7,
    CompatibilityComponent.NADI: 8,
}


def component(
    name: CompatibilityComponent,
    achieved: float | None,
    *,
    abstained: bool = False,
) -> CompatibilityComponentInput:
    return CompatibilityComponentInput(
        component=name,
        status=(
            ComponentEvaluationStatus.ABSTAINED
            if abstained
            else ComponentEvaluationStatus.EVALUATED
        ),
        achieved_points=None if abstained else achieved,
        maximum_points=MAXIMUMS[name],
        rule_ids=(f"TEST-{name.value.upper()}",),
        abstention_reason="Traditional roles were absent." if abstained else None,
    )


def manglik(
    reference: ManglikReferencePoint,
    *,
    flagged: bool,
) -> ManglikFactorInput:
    return ManglikFactorInput(
        reference_point=reference,
        mars_house=7 if flagged else 3,
        flagged=flagged,
        rule_ids=("TEST-MANGLIK",),
    )


def manglik_set(*flags: bool) -> tuple[ManglikFactorInput, ...]:
    return tuple(
        manglik(reference, flagged=flag)
        for reference, flag in zip(ManglikReferencePoint, flags, strict=True)
    )


def full_request() -> CompatibilityInterpretationRequest:
    components = (
        component(CompatibilityComponent.VARNA, 1),
        component(CompatibilityComponent.VASHYA, 2),
        component(CompatibilityComponent.TARA, 3),
        component(CompatibilityComponent.YONI, 4),
        component(CompatibilityComponent.GRAHA_MAITRI, 4),
        component(CompatibilityComponent.GANA, 1),
        component(CompatibilityComponent.BHAKOOT, 7),
        component(CompatibilityComponent.NADI, 0),
    )
    return CompatibilityInterpretationRequest(
        facts_version="compatibility_facts_v2",
        components=components,
        total_achieved_points=sum(item.achieved_points or 0 for item in components),
        evaluated_maximum_points=36,
        complete_36_point_evaluation=True,
        subject_manglik_factors=manglik_set(True, False, True),
        partner_manglik_factors=manglik_set(False, False, True),
    )


def partial_request() -> CompatibilityInterpretationRequest:
    directional = {
        CompatibilityComponent.VARNA,
        CompatibilityComponent.VASHYA,
        CompatibilityComponent.GANA,
    }
    components = tuple(
        component(
            name,
            MAXIMUMS[name] * 0.5,
            abstained=name in directional,
        )
        for name in CompatibilityComponent
    )
    return CompatibilityInterpretationRequest(
        facts_version="compatibility_facts_v2",
        components=components,
        total_achieved_points=sum(item.achieved_points or 0 for item in components),
        evaluated_maximum_points=27,
        complete_36_point_evaluation=False,
        subject_manglik_factors=manglik_set(False, False, False),
        partner_manglik_factors=manglik_set(False, False, False),
    )


def test_full_interpretation_preserves_component_conflict_and_evidence() -> None:
    response = interpret_compatibility(full_request())

    assert response.interpretation_version == COMPATIBILITY_INTERPRETATION_VERSION
    assert response.complete_36_point_evaluation
    assert response.partnership_index.domain is OutlookDomain.PARTNERSHIP
    assert (
        response.partnership_index.confidence_status
        is ConfidenceStatus.UNCALIBRATED_MODERATE
    )
    assert response.partnership_index.conflict_status is ConflictStatus.INTERNAL_CONFLICT
    assert response.partnership_index.score is not None
    assert len(response.components) == 8
    assert response.components[0].evidence_refs == ("TEST-VARNA",)
    assert any("supportive" in item.lower() for item in response.strengths)
    assert any("requires attention" in item.lower() for item in response.cautions)


def test_partial_interpretation_reports_abstention_and_low_confidence() -> None:
    response = interpret_compatibility(partial_request())

    assert response.evaluated_maximum_points == 27
    assert not response.complete_36_point_evaluation
    assert response.partnership_index.coverage == 0.75
    assert (
        response.partnership_index.confidence_status
        is ConfidenceStatus.UNCALIBRATED_LOW
    )
    abstained = [
        item
        for item in response.components
        if item.status is ComponentEvaluationStatus.ABSTAINED
    ]
    assert len(abstained) == 3
    assert all(item.band is ComponentInterpretationBand.INSUFFICIENT for item in abstained)
    assert all(item.achieved_points is None for item in abstained)
    assert any("partial" in item.lower() for item in response.cautions)


def test_manglik_context_is_comparison_only_not_rejection() -> None:
    response = interpret_compatibility(full_request())

    assert response.manglik_context.subject_flagged_count == 2
    assert response.manglik_context.partner_flagged_count == 1
    assert "automatic acceptance or rejection" in response.manglik_context.comparison
    serialized = response.as_dict()
    disclaimer = serialized["manglik_context"]["disclaimer"]
    assert "not automatic rejection rules" in disclaimer


def test_serialized_contract_is_explicitly_non_deterministic() -> None:
    payload = interpret_compatibility(full_request()).as_dict()

    assert payload["disclaimer"] == COMPATIBILITY_DISCLAIMER
    assert "not a probability" in payload["disclaimer"]
    assert "relationship or marriage will succeed" in payload["disclaimer"]
    assert payload["partnership_index"]["disclaimer"]
    assert len(payload["components"]) == 8


def test_request_rejects_false_totals_and_incomplete_component_sets() -> None:
    valid = full_request()

    with pytest.raises(ValueError, match="total_achieved_points"):
        CompatibilityInterpretationRequest(
            facts_version=valid.facts_version,
            components=valid.components,
            total_achieved_points=valid.total_achieved_points + 1,
            evaluated_maximum_points=valid.evaluated_maximum_points,
            complete_36_point_evaluation=True,
            subject_manglik_factors=valid.subject_manglik_factors,
            partner_manglik_factors=valid.partner_manglik_factors,
        )

    with pytest.raises(ValueError, match="all eight"):
        CompatibilityInterpretationRequest(
            facts_version=valid.facts_version,
            components=valid.components[:-1],
            total_achieved_points=valid.total_achieved_points,
            evaluated_maximum_points=valid.evaluated_maximum_points,
            complete_36_point_evaluation=True,
            subject_manglik_factors=valid.subject_manglik_factors,
            partner_manglik_factors=valid.partner_manglik_factors,
        )


def test_component_input_never_treats_abstention_as_zero() -> None:
    with pytest.raises(ValueError, match="cannot include achieved_points"):
        CompatibilityComponentInput(
            component=CompatibilityComponent.GANA,
            status=ComponentEvaluationStatus.ABSTAINED,
            achieved_points=0,
            maximum_points=6,
            rule_ids=("TEST-GANA",),
            abstention_reason="Roles absent.",
        )
