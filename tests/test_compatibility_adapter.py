import copy

import pytest

from varahamihira_engine.compatibility_adapter import (
    compatibility_request_from_astro_facts,
)
from varahamihira_engine.compatibility_interpretation import (
    ComponentEvaluationStatus,
    interpret_compatibility,
)

_COMPONENTS = (
    ("varna", 1),
    ("vashya", 2),
    ("tara", 3),
    ("yoni", 4),
    ("graha_maitri", 5),
    ("gana", 6),
    ("bhakoot", 7),
    ("nadi", 8),
)


def natal(fingerprint: str) -> dict[str, object]:
    return {
        "chart_fingerprint": fingerprint,
        "ascendant_sign_index": 1,
        "moon_sign_index": 2,
        "moon_degree_in_sign": 10.5,
        "moon_nakshatra_index": 3,
        "moon_nakshatra": "Krittika",
        "moon_pada": 2,
        "planet_sign_indices": {
            "sun": 1,
            "moon": 2,
            "mars": 3,
            "mercury": 4,
            "jupiter": 5,
            "venus": 6,
            "saturn": 7,
        },
    }


def component(name: str, maximum: int) -> dict[str, object]:
    return {
        "component": name,
        "status": "evaluated",
        "achieved_points": maximum / 2,
        "maximum_points": maximum,
        "rule_ids": [f"ASTRO-{name.upper()}"],
        "source_kind": "convention",
        "abstention_reason": None,
        "calculation_notes": ["Frozen test convention."],
    }


def manglik(reference_point: str, flagged: bool) -> dict[str, object]:
    return {
        "reference_point": reference_point,
        "mars_house": 7 if flagged else 3,
        "flagged": flagged,
        "rule_ids": ["ASTRO-MANGLIK"],
        "notes": ["Context only."],
    }


def payload() -> dict[str, object]:
    subject_fingerprint = "a" * 64
    partner_fingerprint = "b" * 64
    components = [component(name, maximum) for name, maximum in _COMPONENTS]
    return {
        "request_id": "compat_test",
        "facts_version": "compatibility_facts_v2",
        "calculation_profile": "south_indian_drik_lahiri_jpl_de440s_v1",
        "compatibility_profile": "ashtakoota_v2",
        "subject_fingerprint": subject_fingerprint,
        "partner_fingerprint": partner_fingerprint,
        "pair_fingerprint": "c" * 64,
        "subject": natal(subject_fingerprint),
        "partner": natal(partner_fingerprint),
        "ashtakoota_components": components,
        "total_achieved_points": sum(
            float(item["achieved_points"] or 0) for item in components
        ),
        "evaluated_maximum_points": 36,
        "total_maximum_points": 36,
        "complete_36_point_evaluation": True,
        "subject_manglik_factors": [
            manglik("lagna", True),
            manglik("moon", False),
            manglik("venus", True),
        ],
        "partner_manglik_factors": [
            manglik("lagna", False),
            manglik("moon", False),
            manglik("venus", True),
        ],
        "rule_ids": ["ASTRO-COMPATIBILITY-ASSEMBLER"],
        "metadata": {
            "engine": "jyothisyam-api",
            "engine_version": "test",
            "astronomical_provider": "skyfield_jpl",
            "provider_version": "1.54",
            "ephemeris_model": "de440s",
            "swiss_ephemeris_version": None,
            "zodiac": "sidereal",
            "ayanamsha": "lahiri",
            "node_type": "true_osculating",
            "house_system": "whole_sign",
            "ephemeris_sources": ["jpl_de440s"],
        },
        "caveats": ["Traditional calculation facts only."],
    }


def test_adapter_converts_complete_astro_payload_and_interprets_it() -> None:
    request = compatibility_request_from_astro_facts(payload())
    response = interpret_compatibility(request)

    assert request.facts_version == "compatibility_facts_v2"
    assert request.evaluated_maximum_points == 36
    assert request.complete_36_point_evaluation
    assert all(
        item.status is ComponentEvaluationStatus.EVALUATED
        for item in request.components
    )
    assert response.partnership_index.score is not None
    assert len(response.components) == 8


def test_adapter_rejects_unknown_and_missing_top_level_fields() -> None:
    unknown = payload()
    unknown["unexpected"] = True
    with pytest.raises(ValueError, match="unknown fields: unexpected"):
        compatibility_request_from_astro_facts(unknown)

    missing = payload()
    del missing["facts_version"]
    with pytest.raises(ValueError, match="missing fields: facts_version"):
        compatibility_request_from_astro_facts(missing)


def test_adapter_rejects_profile_and_fingerprint_drift() -> None:
    wrong_profile = payload()
    wrong_profile["calculation_profile"] = "tropical"
    with pytest.raises(ValueError, match="calculation_profile must be"):
        compatibility_request_from_astro_facts(wrong_profile)

    mismatch = payload()
    mismatch["subject"]["chart_fingerprint"] = "d" * 64
    with pytest.raises(ValueError, match="does not match the envelope"):
        compatibility_request_from_astro_facts(mismatch)


def test_adapter_rejects_loose_component_and_manglik_types() -> None:
    bad_status = payload()
    bad_status["ashtakoota_components"][0]["status"] = "unknown"
    with pytest.raises(ValueError, match="unsupported enum value"):
        compatibility_request_from_astro_facts(bad_status)

    bad_boolean = payload()
    bad_boolean["subject_manglik_factors"][0]["flagged"] = 1
    with pytest.raises(ValueError, match="must be a boolean"):
        compatibility_request_from_astro_facts(bad_boolean)

    bad_source = payload()
    bad_source["ashtakoota_components"][0]["source_kind"] = "editorial"
    with pytest.raises(ValueError, match="source_kind is unsupported"):
        compatibility_request_from_astro_facts(bad_source)


def test_adapter_preserves_abstention_instead_of_converting_it_to_zero() -> None:
    partial = copy.deepcopy(payload())
    directional = {"varna", "vashya", "gana"}
    for item in partial["ashtakoota_components"]:
        if item["component"] in directional:
            item["status"] = "abstained"
            item["achieved_points"] = None
            item["abstention_reason"] = "Traditional roles were absent."
    partial["total_achieved_points"] = sum(
        float(item["achieved_points"] or 0)
        for item in partial["ashtakoota_components"]
    )
    partial["evaluated_maximum_points"] = 27
    partial["complete_36_point_evaluation"] = False

    request = compatibility_request_from_astro_facts(partial)

    abstained = [
        item
        for item in request.components
        if item.status is ComponentEvaluationStatus.ABSTAINED
    ]
    assert len(abstained) == 3
    assert all(item.achieved_points is None for item in abstained)


def test_adapter_rejects_malformed_provenance_and_total_maximum() -> None:
    bad_metadata = payload()
    bad_metadata["metadata"]["unknown"] = "value"
    with pytest.raises(ValueError, match="metadata contains unknown fields"):
        compatibility_request_from_astro_facts(bad_metadata)

    bad_maximum = payload()
    bad_maximum["total_maximum_points"] = 35
    with pytest.raises(ValueError, match="must be 36"):
        compatibility_request_from_astro_facts(bad_maximum)
