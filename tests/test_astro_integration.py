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
                "grahas": [
                    {"graha": name, "d1_sign_index": index, "d1_house": index}
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
                    "saturn": 2.0,
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

    request = request_from_astro_analysis(
        period="daily",
        as_of="2026-07-23T12:00:00+05:30",
        weighted_career=weighted_career,
        weighted_dasha=weighted_dasha,
    )
    response = evaluate(request)
    by_domain = {result.domain: result for result in response.results}

    assert by_domain["career"].outlook is Outlook.CHALLENGING
    assert "negative" in by_domain["career"].statement
    assert by_domain["overall"].outlook is Outlook.MIXED
    assert len(by_domain["overall"].supporting_factors) == 1
    assert len(by_domain["overall"].challenging_factors) == 1
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
