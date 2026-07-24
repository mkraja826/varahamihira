from varahamihira_engine import (
    LIFE_PROFILE_FACTS_VERSION,
    PERIOD_ANALYSIS_FACTS_VERSION,
    LifeProfileInterpretationRequest,
    MonthAnalysisInput,
    MonthInterpretationRequest,
    YearInterpretationRequest,
    analysis_snapshot_from_prediction,
    interpret_life_profile,
    interpret_month_analysis,
    interpret_year_analysis,
)


def _prediction(as_of: str) -> dict:
    def evidence(eid: str, domain: str, polarity: str, weight: float) -> dict:
        return {
            "evidence_id": eid,
            "domain": domain,
            "statement": f"{domain} {polarity} evidence",
            "polarity": polarity,
            "weight": weight,
            "source_rule_ids": ["BJ.TEST.1"],
            "source_kind": "classical",
            "reason": "Frozen test evidence.",
        }

    domains = [
        "overall",
        "career",
        "money_resources",
        "relationships_marriage",
        "family_home",
        "education_creativity",
        "wellbeing",
        "travel_change",
        "spirituality",
    ]
    return {
        "engine_version": "horos_brihat_jataka_v2",
        "calculation_profile": "south_indian_drik_lahiri_jpl_de440s_v1",
        "classical_profile": "varahamihira_v1",
        "period": "monthly",
        "as_of": as_of,
        "results": [
            {
                "domain": domain,
                "outlook": "mixed",
                "strength": "moderate",
                "supporting_score": 0.7,
                "challenging_score": 0.3,
                "net_score": 0.4,
                "statement": "Mixed source-traceable factors.",
                "advisory": "Use balanced judgment.",
                "favourable_timing": None,
                "challenging_timing": None,
                "supporting_factors": [evidence(f"{domain}-s", domain, "supporting", 0.7)],
                "challenging_factors": [evidence(f"{domain}-c", domain, "challenging", 0.3)],
                "contextual_factors": [evidence(f"{domain}-x", domain, "contextual", 0.0)],
            }
            for domain in domains
        ],
        "disclaimer": "Traditional interpretation only.",
    }


def _month(year: int, month: int) -> MonthAnalysisInput:
    sample = f"{year:04d}-{month:02d}-15T12:00:00+05:30"
    return MonthAnalysisInput(
        year=year,
        month=month,
        sample_local_datetime=sample,
        snapshot=analysis_snapshot_from_prediction(_prediction(sample)),
        sampling_method="civil_month_midpoint_local_noon_v1",
        exact_boundary_calculation_applied=False,
        channels_available=("natal", "dasha"),
        channels_unavailable=("transit", "panchanga"),
    )


def test_life_profile_has_all_sections_and_safe_indices() -> None:
    snapshot = analysis_snapshot_from_prediction(_prediction("2026-07-15T12:00:00+05:30"))
    response = interpret_life_profile(
        LifeProfileInterpretationRequest(
            facts_version=LIFE_PROFILE_FACTS_VERSION,
            snapshot=snapshot,
        )
    ).as_dict()

    assert response["interpretation_version"] == "life_profile_interpretation_v1"
    assert len(response["sections"]) == 10
    assert all("guarantee" not in section["narrative"].lower() for section in response["sections"])
    indexed = [section["outlook_index"] for section in response["sections"] if section["outlook_index"]]
    assert len(indexed) == 7
    assert all(item["confidence_status"].startswith("uncalibrated_") for item in indexed)


def test_month_and_year_analysis_preserve_sampling_limits() -> None:
    month = interpret_month_analysis(
        MonthInterpretationRequest(
            facts_version=PERIOD_ANALYSIS_FACTS_VERSION,
            month=_month(2028, 2),
        )
    ).as_dict()

    assert month["month"] == 2
    assert month["exact_boundary_calculation_applied"] is False
    assert month["channels_unavailable"] == ["transit", "panchanga"]
    assert len(month["indices"]) == 7

    year = interpret_year_analysis(
        YearInterpretationRequest(
            facts_version=PERIOD_ANALYSIS_FACTS_VERSION,
            year=2028,
            months=tuple(_month(2028, item) for item in range(1, 13)),
        )
    ).as_dict()

    assert len(year["months"]) == 12
    assert len(year["overview_indices"]) == 7
    assert len(year["strongest_months"]) == 3
    assert len(year["challenging_months"]) == 3
