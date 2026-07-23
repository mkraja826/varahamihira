import pytest

from varahamihira_engine import Evidence, Outlook, Polarity, PredictionRequest, evaluate


def evidence(
    evidence_id: str,
    polarity: Polarity,
    weight: float,
    *,
    domain: str = "career",
    source_kind: str = "classical",
    independence_key: str = "",
) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        domain=domain,
        statement=f"Synthetic test evidence {evidence_id}",
        polarity=polarity,
        weight=weight,
        source_rule_ids=("TEST-NOT-A-CLASSICAL-CITATION",) if source_kind == "classical" else (),
        source_kind=source_kind,
        reason="Synthetic fixture; not a Brihat Jataka attribution.",
        independence_key=independence_key,
    )


def request(*items: Evidence) -> PredictionRequest:
    return PredictionRequest(
        period="daily",
        as_of="2026-07-23T00:00:00+05:30",
        evidence=items,
    )


def test_negative_evidence_is_reported_directly_without_sugar_coating() -> None:
    result = evaluate(
        request(
            evidence("negative-1", Polarity.CHALLENGING, 0.8),
            evidence("positive-1", Polarity.SUPPORTING, 0.2),
        )
    ).results[0]

    assert result.outlook is Outlook.CHALLENGING
    assert result.net_score == -0.3
    assert "negative" in result.statement
    assert result.challenging_factors[0].evidence_id == "negative-1"
    assert result.timing_status == "unavailable"
    assert result.favourable_timing is None
    assert result.challenging_timing is None
    assert result.channel_scores["natal"]["coefficient"] == 0.5
    assert result.conflict_status == "none"
    assert result.confidence_status == "uncalibrated_low"


def test_timing_language_requires_explicit_timing_evidence() -> None:
    result = evaluate(
        PredictionRequest(
            period="daily",
            as_of="2026-07-23T00:00:00+05:30",
            evidence=(evidence("negative-1", Polarity.CHALLENGING, 0.8),),
            timing_evidence_available=True,
        )
    ).results[0]

    assert result.timing_status == "evaluated"
    assert result.challenging_timing


def test_natal_result_never_claims_a_dated_timing_window() -> None:
    result = evaluate(
        PredictionRequest(
            period="natal",
            as_of="2026-07-23T00:00:00+05:30",
            evidence=(evidence("positive-1", Polarity.SUPPORTING, 0.8),),
            timing_evidence_available=True,
        )
    ).results[0]

    assert result.timing_status == "not_applicable"
    assert result.favourable_timing is None
    assert result.challenging_timing is None


def test_close_conflict_is_mixed_and_preserves_both_sides() -> None:
    result = evaluate(
        request(
            evidence("negative-1", Polarity.CHALLENGING, 0.6),
            evidence("positive-1", Polarity.SUPPORTING, 0.5),
        )
    ).results[0]

    assert result.outlook is Outlook.MIXED
    assert len(result.supporting_factors) == 1
    assert len(result.challenging_factors) == 1


def test_context_is_not_silently_scored() -> None:
    result = evaluate(
        request(evidence("context-1", Polarity.CONTEXTUAL, 1.0, source_kind="convention"))
    ).results[0]

    assert result.outlook is Outlook.INSUFFICIENT
    assert result.net_score == 0.0
    assert len(result.contextual_factors) == 1


def test_classical_evidence_requires_source_rule_id() -> None:
    with pytest.raises(ValueError, match="source rule"):
        Evidence(
            evidence_id="missing-source",
            domain="career",
            statement="Invalid fixture",
            polarity=Polarity.SUPPORTING,
            weight=0.5,
            source_rule_ids=(),
            source_kind="classical",
            reason="Missing citation.",
        )


def test_blocked_consumer_domain_is_rejected() -> None:
    with pytest.raises(ValueError, match="blocked"):
        evaluate(
            request(
                evidence(
                    "blocked-1",
                    Polarity.CHALLENGING,
                    0.8,
                    domain="exact_death",
                )
            )
        )


def test_duplicate_underlying_fact_is_counted_once_and_retains_trace() -> None:
    result = evaluate(
        request(
            evidence(
                "lord-channel",
                Polarity.SUPPORTING,
                0.6,
                independence_key="natal-career-saturn-strength",
            ),
            evidence(
                "occupant-channel",
                Polarity.SUPPORTING,
                0.4,
                independence_key="natal-career-saturn-strength",
            ),
        )
    ).results[0]

    assert result.supporting_score == 0.3
    assert len(result.supporting_factors) == 1
    assert "occupant-channel" in result.supporting_factors[0].reason


def test_duplicate_underlying_fact_with_conflicting_polarity_fails_closed() -> None:
    with pytest.raises(ValueError, match="conflicting polarity"):
        evaluate(
            request(
                evidence(
                    "positive",
                    Polarity.SUPPORTING,
                    0.6,
                    independence_key="same-fact",
                ),
                evidence(
                    "negative",
                    Polarity.CHALLENGING,
                    0.4,
                    independence_key="same-fact",
                ),
            )
        )


def test_channels_are_capped_and_conflict_is_machine_visible() -> None:
    result = evaluate(
        PredictionRequest(
            period="daily",
            as_of="2026-07-23T00:00:00+05:30",
            evidence=(
                evidence(
                    "natal-1",
                    Polarity.SUPPORTING,
                    1.0,
                    independence_key="natal-career-sun-controlled-strength",
                ),
                evidence(
                    "natal-2",
                    Polarity.SUPPORTING,
                    1.0,
                    independence_key="natal-career-moon-controlled-strength",
                ),
                evidence(
                    "dasha-1",
                    Polarity.CHALLENGING,
                    1.0,
                    independence_key="dasha-current-career",
                ),
                evidence(
                    "transit-1",
                    Polarity.CHALLENGING,
                    1.0,
                    independence_key="transit-daily-career-saturn",
                ),
            ),
            timing_evidence_available=True,
        )
    ).results[0]

    assert result.supporting_score == 0.5
    assert result.challenging_score == 0.5
    assert result.outlook is Outlook.MIXED
    assert result.conflict_status == "cross_channel_conflict"
    assert result.confidence_status == "uncalibrated_low"
    assert result.channel_scores["natal"]["raw_supporting"] == 2.0
    assert result.channel_scores["natal"]["balanced_supporting"] == 0.5
