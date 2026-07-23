import pytest

from varahamihira_engine import Outlook, evaluate
from varahamihira_engine.astro_integration import request_from_astro_analysis


def test_real_astro_contract_maps_negative_and_positive_evidence_without_hiding_either() -> None:
    weighted_career = {
        "profile_id": "varahamihira_v1",
        "career": {
            "candidates": [
                {
                    "graha": "Saturn",
                    "rule_ids": ["VM-BJ-C10-VOCATION-JUPITER-SATURN-001"],
                }
            ]
        },
        "candidate_strengths": [
            {
                "graha": "Saturn",
                "repetition_count": 2,
                "strength": {
                    "available": True,
                    "total_score": -4.0,
                    "reason": "Synthetic debilitated fixture.",
                },
            }
        ],
    }
    weighted_dasha = {
        "profile_id": "varahamihira_v1",
        "weighted_strength": {
            "calculation_profile": "south_indian_drik_lahiri_jpl_de440s_v1",
            "raw_strength": {
                "cancellation_policy": {
                    "confirmed_rule_count": 0,
                    "cancellation_rules_enabled": False,
                    "supported_rule_ids": [],
                },
                "cancellations_applied": False,
                "grahas": [
                    {
                        "graha": name,
                        "d1_sign_index": index,
                        "d1_house": index,
                        "vargottama": name == "jupiter",
                        "cancellation": {
                            "status": (
                                "unsupported_by_profile"
                                if name == "saturn"
                                else "not_applicable"
                            ),
                            "applicable": name == "saturn",
                            "cancellation_applied": False,
                        },
                    }
                    for index, name in enumerate(
                        ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn"],
                        start=1,
                    )
                ]
            },
            "weighted_grahas": [
                {
                    "graha": name,
                    "total_score": score,
                    "cancellation_adjustment": 0.0,
                    "cancellation_applied": False,
                    "components": [
                        {
                            "classical_rule_ids": ["VM-BJ-C02-DIGNITY-001"],
                        }
                    ],
                }
                for name, score in {
                    "sun": 2.0,
                    "moon": 3.0,
                    "mars": -8.0,
                    "mercury": 1.0,
                    "jupiter": 4.0,
                    "venus": -4.0,
                    "saturn": -4.0,
                }.items()
            ],
        },
        "dasha": {
            "levels": [
                {
                    "level": "mahadasha",
                    "lord": "Saturn",
                    "supporting_evidence": [],
                    "challenging_evidence": [
                        {
                            "fact": "dignity",
                            "value": "debilitation",
                            "reason": "Synthetic adverse fixture.",
                            "rule_ids": ["VM-BJ-C02-DIGNITY-001"],
                        }
                    ],
                    "contextual_evidence": [
                        {
                            "fact": "owned_houses",
                            "value": "2,3",
                            "reason": "Synthetic house ownership fixture.",
                            "rule_ids": [],
                        }
                    ],
                },
                {
                    "level": "antardasha",
                    "lord": "Jupiter",
                    "supporting_evidence": [
                        {
                            "fact": "own_sign",
                            "value": "true",
                            "reason": "Synthetic supporting fixture.",
                            "rule_ids": ["VM-BJ-C02-DIGNITY-001"],
                        }
                    ],
                    "challenging_evidence": [],
                    "contextual_evidence": [],
                },
                {
                    "level": "pratyantardasha",
                    "lord": "Moon",
                    "supporting_evidence": [],
                    "challenging_evidence": [],
                    "contextual_evidence": [],
                },
                {
                    "level": "sookshma",
                    "lord": "Mercury",
                    "supporting_evidence": [],
                    "challenging_evidence": [],
                    "contextual_evidence": [],
                },
            ]
        },
    }
    transit_horizon = {
        "period": "daily",
        "sample_count": 4,
        "sampling_applied": True,
        "exact_ingress_egress_applied": False,
        "samples": [
            {
                "sample_index": sample_index,
                "factors": [
                    {
                        "body": name,
                        "house_from_natal_ascendant": house,
                        "normalized_balance": balance,
                        "polarity": (
                            "supporting"
                            if balance > 0
                            else "challenging"
                            if balance < 0
                            else "contextual"
                        ),
                        "rule_ids": [
                            "VM-BJ-C09-TRANSIT-BAV-BALANCE-001",
                            f"VM-BJ-C09-{name.upper()}-BAV-001",
                        ],
                    }
                    for name, house, balance in (
                        ("sun", 1, 0.0),
                        ("moon", 4, 0.25),
                        ("mars", 10, -0.5),
                        ("mercury", 5, 0.25),
                        ("jupiter", 9, 0.5),
                        ("venus", 7, -0.25),
                        ("saturn", 10, -0.5),
                    )
                ],
            }
            for sample_index in range(1, 5)
        ],
    }

    request = request_from_astro_analysis(
        period="daily",
        as_of="2026-07-23T12:00:00+05:30",
        weighted_career=weighted_career,
        weighted_dasha=weighted_dasha,
        transit_horizon=transit_horizon,
    )
    response = evaluate(request)
    by_domain = {result.domain: result for result in response.results}

    assert by_domain["career"].outlook is Outlook.CHALLENGING
    assert "negative" in by_domain["career"].statement
    assert by_domain["overall"].outlook is Outlook.MIXED
    assert by_domain["overall"].supporting_factors
    assert by_domain["overall"].challenging_factors
    assert set(by_domain) == {
        "career",
        "education_creativity",
        "family_home",
        "money_resources",
        "overall",
        "relationships_marriage",
        "spirituality",
        "travel_change",
        "wellbeing",
    }
    assert by_domain["money_resources"].outlook is Outlook.CHALLENGING
    assert by_domain["travel_change"].outlook is Outlook.CHALLENGING
    assert by_domain["family_home"].outlook is Outlook.FAVOURABLE
    assert by_domain["career"].timing_status == "evaluated"
    assert by_domain["career"].challenging_timing
    assert by_domain["wellbeing"].outlook is Outlook.CHALLENGING
    assert by_domain["spirituality"].outlook is Outlook.MIXED
    assert (
        sum(
            factor.independence_key
            == "natal-spirituality-jupiter-controlled-strength"
            for factor in (
                *by_domain["spirituality"].supporting_factors,
                *by_domain["spirituality"].challenging_factors,
            )
        )
        == 1
    )
    assert any(
        factor.evidence_id.startswith("natal-occupant-")
        for factor in by_domain["family_home"].supporting_factors
    )
    assert any(
        factor.evidence_id.startswith("natal-aspect-career-mars-8-to-10")
        for factor in by_domain["career"].challenging_factors
    )
    mars_aspect = next(
        factor
        for factor in by_domain["career"].challenging_factors
        if factor.evidence_id.startswith("natal-aspect-career-mars-8-to-10")
    )
    assert mars_aspect.weight == 0.2
    assert "VM-BJ-C02-SPECIAL-ASPECT-EVAL-001" in mars_aspect.source_rule_ids
    karaka_factors = [
        factor
        for result in by_domain.values()
        for factor in (
            *result.supporting_factors,
            *result.challenging_factors,
            *result.contextual_factors,
        )
        if factor.evidence_id.startswith("natal-karaka-")
    ]
    assert len(karaka_factors) == 1
    assert karaka_factors[0].domain == "career"
    assert "VM-BJ-C10-VOCATION-JUPITER-SATURN-001" in (
        karaka_factors[0].source_rule_ids
    )
    jupiter_confirmation = next(
        factor
        for factor in (
            *by_domain["spirituality"].supporting_factors,
            *by_domain["spirituality"].challenging_factors,
        )
        if factor.independence_key
        == "natal-spirituality-jupiter-controlled-strength"
    )
    assert "D9 confirmation" in jupiter_confirmation.reason
    assert "VM-BJ-C01-VARGOTTAMA-EVAL-001" in (
        jupiter_confirmation.source_rule_ids
    )
    d10_marker = next(
        factor
        for factor in by_domain["career"].contextual_factors
        if factor.evidence_id == "coverage-varga-d10-career"
    )
    assert d10_marker.weight == 0.0
    assert "unavailable" in d10_marker.statement
    saturn_boundary = next(
        factor
        for factor in by_domain["career"].challenging_factors
        if factor.independence_key == "natal-career-saturn-controlled-strength"
    )
    assert "Cancellation boundary" in saturn_boundary.reason
    assert "No cancellation or score adjustment was applied" in saturn_boundary.reason
    assert "VM-BJ-C02-CANCELLATION-SOURCE-BOUNDARY-001" in (
        saturn_boundary.source_rule_ids
    )
    transit_factor = next(
        factor
        for factor in by_domain["career"].challenging_factors
        if factor.evidence_id == "transit-daily-career-saturn-bav-balance"
    )
    assert transit_factor.weight == 0.15
    assert "VM-BJ-C09-TRANSIT-BAV-BALANCE-001" in transit_factor.source_rule_ids

    weighted_dasha["weighted_strength"]["weighted_grahas"][-1][
        "cancellation_adjustment"
    ] = 4.0
    with pytest.raises(
        ValueError,
        match="unsupported cancellation adjustment",
    ):
        request_from_astro_analysis(
            period="daily",
            as_of="2026-07-23T12:00:00+05:30",
            weighted_career=weighted_career,
            weighted_dasha=weighted_dasha,
            transit_horizon=transit_horizon,
        )
