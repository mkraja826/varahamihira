from varahamihira_engine.models import (
    DomainResult,
    Outlook,
    PredictionResponse,
)
from varahamihira_engine.validation import (
    blind_case,
    canonical_digest,
    outcome_metrics,
    validation_gates,
)


def _prediction() -> PredictionResponse:
    return PredictionResponse(
        engine_version="test",
        calculation_profile="south_indian_drik_lahiri_jpl_de440s_v1",
        classical_profile="varahamihira_brihat_jataka_v1",
        period="daily",
        as_of="2026-07-23T12:00:00+05:30",
        results=(
            DomainResult(
                domain="career",
                outlook=Outlook.CHALLENGING,
                strength="moderate",
                supporting_score=0.1,
                challenging_score=0.5,
                net_score=-0.4,
                channel_scores={},
                conflict_status="none",
                confidence_status="uncalibrated_moderate",
                statement="The career indication is negative.",
                advisory="Reduce avoidable professional risk.",
                timing_status="evaluated",
                favourable_timing=None,
                challenging_timing="The evaluated horizon is challenging.",
                supporting_factors=(),
                challenging_factors=(),
                contextual_factors=(),
            ),
        ),
        disclaimer="Astrology is interpretive guidance, not a guarantee.",
    )


def test_blind_case_is_stable_and_contains_no_raw_chart_identifier() -> None:
    case = blind_case(
        case_id="case-001",
        prediction=_prediction(),
        chart_fingerprint="private chart identifier",
        registered_at="2026-07-23T12:00:00+00:00",
    )

    assert case["chart_fingerprint"] != "private chart identifier"
    assert len(case["chart_fingerprint"]) == 64
    digest_payload = {key: value for key, value in case.items() if key != "registration_digest"}
    assert case["registration_digest"] == canonical_digest(digest_payload)


def test_external_gates_remain_pending_until_real_records_exist() -> None:
    gates = validation_gates(
        automated_checks_passed=True,
        expert_reviews=[],
        outcomes=[],
    )

    assert [gate.status for gate in gates] == ["passed", "pending", "pending"]


def test_outcome_metrics_preserve_abstention_and_confusion() -> None:
    metrics = outcome_metrics(
        [
            {"predicted_outlook": "challenging", "observed_outlook": "challenging"},
            {"predicted_outlook": "favourable", "observed_outlook": "mixed"},
            {
                "predicted_outlook": "insufficient_evidence",
                "observed_outlook": "challenging",
            },
        ]
    )

    assert metrics["scored_records"] == 2
    assert metrics["abstentions"] == 1
    assert metrics["categorical_accuracy"] == 0.5
    assert metrics["confusion"]["favourable->mixed"] == 1
