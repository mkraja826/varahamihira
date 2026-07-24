import pytest

from varahamihira_engine import (
    calculate_outlook_index,
    ConfidenceStatus,
    ConflictStatus,
    OUTLOOK_INDEX_DISCLAIMER,
    OUTLOOK_INDEX_VERSION,
    OutlookBand,
    OutlookDomain,
)


def build_index(
    supporting: float,
    challenging: float,
    *,
    coverage: float = 1.0,
    confidence: ConfidenceStatus = ConfidenceStatus.UNCALIBRATED_MODERATE,
    conflict: ConflictStatus = ConflictStatus.NONE,
    evidence_refs: tuple[str, ...] = ("TEST-EVIDENCE-1",),
):
    return calculate_outlook_index(
        domain=OutlookDomain.LOVE,
        supporting_component=supporting,
        challenging_component=challenging,
        coverage=coverage,
        confidence_status=confidence,
        conflict_status=conflict,
        evidence_refs=evidence_refs,
    )


@pytest.mark.parametrize(
    ("supporting", "challenging", "expected_score", "expected_band"),
    [
        (0.00, 1.00, 0, OutlookBand.VERY_CHALLENGING),
        (0.00, 0.62, 19, OutlookBand.VERY_CHALLENGING),
        (0.00, 0.60, 20, OutlookBand.CHALLENGING),
        (0.00, 0.22, 39, OutlookBand.CHALLENGING),
        (0.00, 0.20, 40, OutlookBand.MIXED),
        (0.18, 0.00, 59, OutlookBand.MIXED),
        (0.20, 0.00, 60, OutlookBand.SUPPORTIVE),
        (0.58, 0.00, 79, OutlookBand.SUPPORTIVE),
        (0.60, 0.00, 80, OutlookBand.VERY_SUPPORTIVE),
        (1.00, 0.00, 100, OutlookBand.VERY_SUPPORTIVE),
    ],
)
def test_score_band_boundaries(
    supporting: float,
    challenging: float,
    expected_score: int,
    expected_band: OutlookBand,
) -> None:
    result = build_index(supporting, challenging)

    assert result.score == expected_score
    assert result.band is expected_band
    assert not result.abstained


def test_equal_support_and_challenge_is_neutral() -> None:
    result = build_index(0.70, 0.70, conflict=ConflictStatus.INTERNAL_CONFLICT)

    assert result.score == 50
    assert result.band is OutlookBand.MIXED
    assert result.conflict_status is ConflictStatus.INTERNAL_CONFLICT


def test_score_is_monotonic_as_support_increases() -> None:
    scores = [build_index(value, 0.20).score for value in (0.0, 0.2, 0.4, 0.6, 0.8)]

    assert scores == sorted(scores)


@pytest.mark.parametrize(
    ("coverage", "confidence", "evidence_refs"),
    [
        (0.49, ConfidenceStatus.UNCALIBRATED_MODERATE, ("TEST-EVIDENCE-1",)),
        (1.00, ConfidenceStatus.INSUFFICIENT, ("TEST-EVIDENCE-1",)),
        (1.00, ConfidenceStatus.UNCALIBRATED_LOW, ()),
    ],
)
def test_insufficient_inputs_abstain(
    coverage: float,
    confidence: ConfidenceStatus,
    evidence_refs: tuple[str, ...],
) -> None:
    result = build_index(
        0.80,
        0.10,
        coverage=coverage,
        confidence=confidence,
        evidence_refs=evidence_refs,
    )

    assert result.score is None
    assert result.band is None
    assert result.abstained
    assert result.confidence_status is ConfidenceStatus.INSUFFICIENT
    assert result.conflict_status is ConflictStatus.INSUFFICIENT


def test_conflict_is_reported_without_secretly_changing_the_score() -> None:
    clear = build_index(0.70, 0.20, conflict=ConflictStatus.NONE)
    conflicted = build_index(
        0.70,
        0.20,
        conflict=ConflictStatus.CROSS_CHANNEL_CONFLICT,
    )

    assert clear.score == conflicted.score
    assert conflicted.conflict_status is ConflictStatus.CROSS_CHANNEL_CONFLICT


def test_serialized_contract_is_versioned_and_explicitly_non_probabilistic() -> None:
    payload = build_index(0.70, 0.20).as_dict()

    assert payload["domain"] == "love"
    assert payload["score"] == 75
    assert payload["band"] == "supportive"
    assert payload["score_version"] == OUTLOOK_INDEX_VERSION
    assert payload["evidence_refs"] == ["TEST-EVIDENCE-1"]
    assert payload["disclaimer"] == OUTLOOK_INDEX_DISCLAIMER
    assert "not a probability" in payload["disclaimer"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("supporting_component", -0.01),
        ("challenging_component", 1.01),
        ("coverage", -0.01),
        ("minimum_coverage", 1.01),
    ],
)
def test_components_must_remain_bounded(field: str, value: float) -> None:
    arguments = {
        "domain": OutlookDomain.FINANCE,
        "supporting_component": 0.50,
        "challenging_component": 0.20,
        "coverage": 1.00,
        "confidence_status": ConfidenceStatus.UNCALIBRATED_LOW,
        "conflict_status": ConflictStatus.NONE,
        "evidence_refs": ("TEST-EVIDENCE-1",),
        "minimum_coverage": 0.50,
    }
    arguments[field] = value

    with pytest.raises(ValueError, match=field):
        calculate_outlook_index(**arguments)
