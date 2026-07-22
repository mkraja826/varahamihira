import pytest

from varahamihira_engine import Evidence, Outlook, Polarity, PredictionRequest, evaluate


def evidence(
    evidence_id: str,
    polarity: Polarity,
    weight: float,
    *,
    domain: str = "career",
    source_kind: str = "classical",
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
    assert result.net_score == -0.6
    assert "negative" in result.statement
    assert result.challenging_factors[0].evidence_id == "negative-1"


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
