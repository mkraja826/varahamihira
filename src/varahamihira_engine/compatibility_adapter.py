from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .compatibility_interpretation import (
    CompatibilityComponent,
    CompatibilityComponentInput,
    CompatibilityInterpretationRequest,
    ComponentEvaluationStatus,
    ManglikFactorInput,
    ManglikReferencePoint,
)

_ASTRO_FACTS_KEYS = {
    "request_id",
    "facts_version",
    "calculation_profile",
    "compatibility_profile",
    "subject_fingerprint",
    "partner_fingerprint",
    "pair_fingerprint",
    "subject",
    "partner",
    "ashtakoota_components",
    "total_achieved_points",
    "evaluated_maximum_points",
    "total_maximum_points",
    "complete_36_point_evaluation",
    "subject_manglik_factors",
    "partner_manglik_factors",
    "rule_ids",
    "metadata",
    "caveats",
}
_NATAL_KEYS = {
    "chart_fingerprint",
    "ascendant_sign_index",
    "moon_sign_index",
    "moon_degree_in_sign",
    "moon_nakshatra_index",
    "moon_nakshatra",
    "moon_pada",
    "planet_sign_indices",
}
_COMPONENT_KEYS = {
    "component",
    "status",
    "achieved_points",
    "maximum_points",
    "rule_ids",
    "source_kind",
    "abstention_reason",
    "calculation_notes",
}
_MANGLIK_KEYS = {
    "reference_point",
    "mars_house",
    "flagged",
    "rule_ids",
    "notes",
}
_METADATA_KEYS = {
    "engine",
    "engine_version",
    "astronomical_provider",
    "provider_version",
    "ephemeris_model",
    "swiss_ephemeris_version",
    "zodiac",
    "ayanamsha",
    "node_type",
    "house_system",
    "ephemeris_sources",
}
_EXPECTED_CALCULATION_PROFILE = "south_indian_drik_lahiri_jpl_de440s_v1"
_EXPECTED_COMPATIBILITY_PROFILE = "ashtakoota_v2"
_HEX_DIGITS = frozenset("0123456789abcdef")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{path} keys must be strings")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise ValueError(f"{path} is missing fields: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"{path} contains unknown fields: {', '.join(unknown)}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path} must be a non-blank string")
    return value


def _optional_string(value: Any, path: str) -> str | None:
    if value is None:
        return None
    return _string(value, path)


def _literal(value: Any, expected: str, path: str) -> str:
    actual = _string(value, path)
    if actual != expected:
        raise ValueError(f"{path} must be {expected}")
    return actual


def _fingerprint(value: Any, path: str) -> str:
    fingerprint = _string(value, path)
    if len(fingerprint) != 64 or any(item not in _HEX_DIGITS for item in fingerprint):
        raise ValueError(f"{path} must be a 64-character lowercase SHA-256 value")
    return fingerprint


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{path} must be a boolean")
    return value


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{path} must be an integer")
    return value


def _number(value: Any, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{path} must be a number")
    return float(value)


def _number_or_none(value: Any, path: str) -> float | None:
    if value is None:
        return None
    return _number(value, path)


def _string_tuple(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    return tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(value))


def _object_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    return value


def _validate_planet_signs(value: Any, path: str) -> None:
    signs = _mapping(value, path)
    if len(signs) < 7:
        raise ValueError(f"{path} must contain at least seven planets")
    for name, sign_index in signs.items():
        _string(name, f"{path}.planet")
        sign = _integer(sign_index, f"{path}.{name}")
        if not 1 <= sign <= 12:
            raise ValueError(f"{path}.{name} must be between 1 and 12")


def _validate_natal(value: Any, path: str, expected_fingerprint: str) -> None:
    natal = _mapping(value, path)
    _exact_keys(natal, _NATAL_KEYS, path)
    chart_fingerprint = _fingerprint(natal["chart_fingerprint"], f"{path}.chart_fingerprint")
    if chart_fingerprint != expected_fingerprint:
        raise ValueError(f"{path}.chart_fingerprint does not match the envelope")

    for field in ("ascendant_sign_index", "moon_sign_index"):
        sign = _integer(natal[field], f"{path}.{field}")
        if not 1 <= sign <= 12:
            raise ValueError(f"{path}.{field} must be between 1 and 12")
    degree = _number(natal["moon_degree_in_sign"], f"{path}.moon_degree_in_sign")
    if not 0.0 <= degree < 30.0:
        raise ValueError(f"{path}.moon_degree_in_sign must be between 0 and 30")
    nakshatra = _integer(
        natal["moon_nakshatra_index"],
        f"{path}.moon_nakshatra_index",
    )
    if not 1 <= nakshatra <= 27:
        raise ValueError(f"{path}.moon_nakshatra_index must be between 1 and 27")
    _string(natal["moon_nakshatra"], f"{path}.moon_nakshatra")
    pada = _integer(natal["moon_pada"], f"{path}.moon_pada")
    if not 1 <= pada <= 4:
        raise ValueError(f"{path}.moon_pada must be between 1 and 4")
    _validate_planet_signs(natal["planet_sign_indices"], f"{path}.planet_sign_indices")


def _validate_metadata(value: Any) -> None:
    metadata = _mapping(value, "metadata")
    _exact_keys(metadata, _METADATA_KEYS, "metadata")
    for field in (
        "engine",
        "engine_version",
        "astronomical_provider",
        "zodiac",
        "ayanamsha",
        "node_type",
        "house_system",
    ):
        _string(metadata[field], f"metadata.{field}")
    for field in ("provider_version", "ephemeris_model", "swiss_ephemeris_version"):
        _optional_string(metadata[field], f"metadata.{field}")
    _string_tuple(metadata["ephemeris_sources"], "metadata.ephemeris_sources")


def _component_input(value: Any, index: int) -> CompatibilityComponentInput:
    path = f"ashtakoota_components[{index}]"
    item = _mapping(value, path)
    _exact_keys(item, _COMPONENT_KEYS, path)
    try:
        component = CompatibilityComponent(_string(item["component"], f"{path}.component"))
        status = ComponentEvaluationStatus(_string(item["status"], f"{path}.status"))
    except ValueError as exc:
        raise ValueError(f"{path} contains an unsupported enum value") from exc

    abstention_reason = item["abstention_reason"]
    if abstention_reason is not None:
        abstention_reason = _string(abstention_reason, f"{path}.abstention_reason")
    source_kind = _string(item["source_kind"], f"{path}.source_kind")
    if source_kind not in {"classical", "convention"}:
        raise ValueError(f"{path}.source_kind is unsupported")
    return CompatibilityComponentInput(
        component=component,
        status=status,
        achieved_points=_number_or_none(
            item["achieved_points"],
            f"{path}.achieved_points",
        ),
        maximum_points=_integer(item["maximum_points"], f"{path}.maximum_points"),
        rule_ids=_string_tuple(item["rule_ids"], f"{path}.rule_ids"),
        calculation_notes=_string_tuple(
            item["calculation_notes"],
            f"{path}.calculation_notes",
        ),
        abstention_reason=abstention_reason,
    )


def _manglik_input(value: Any, path: str) -> ManglikFactorInput:
    item = _mapping(value, path)
    _exact_keys(item, _MANGLIK_KEYS, path)
    try:
        reference_point = ManglikReferencePoint(
            _string(item["reference_point"], f"{path}.reference_point")
        )
    except ValueError as exc:
        raise ValueError(f"{path}.reference_point is unsupported") from exc
    _string_tuple(item["notes"], f"{path}.notes")
    return ManglikFactorInput(
        reference_point=reference_point,
        mars_house=_integer(item["mars_house"], f"{path}.mars_house"),
        flagged=_boolean(item["flagged"], f"{path}.flagged"),
        rule_ids=_string_tuple(item["rule_ids"], f"{path}.rule_ids"),
    )


def _validate_envelope(facts: Mapping[str, Any]) -> None:
    _string(facts["request_id"], "request_id")
    _literal(
        facts["calculation_profile"],
        _EXPECTED_CALCULATION_PROFILE,
        "calculation_profile",
    )
    _literal(
        facts["compatibility_profile"],
        _EXPECTED_COMPATIBILITY_PROFILE,
        "compatibility_profile",
    )
    subject_fingerprint = _fingerprint(
        facts["subject_fingerprint"],
        "subject_fingerprint",
    )
    partner_fingerprint = _fingerprint(
        facts["partner_fingerprint"],
        "partner_fingerprint",
    )
    _fingerprint(facts["pair_fingerprint"], "pair_fingerprint")
    _validate_natal(facts["subject"], "subject", subject_fingerprint)
    _validate_natal(facts["partner"], "partner", partner_fingerprint)
    if _integer(facts["total_maximum_points"], "total_maximum_points") != 36:
        raise ValueError("total_maximum_points must be 36")
    if not _string_tuple(facts["rule_ids"], "rule_ids"):
        raise ValueError("rule_ids must not be empty")
    _string_tuple(facts["caveats"], "caveats")
    _validate_metadata(facts["metadata"])


def compatibility_request_from_astro_facts(
    payload: Mapping[str, Any],
) -> CompatibilityInterpretationRequest:
    """Convert one strict Astro `compatibility_facts_v2` response into engine input."""

    facts = _mapping(payload, "payload")
    _exact_keys(facts, _ASTRO_FACTS_KEYS, "payload")
    _validate_envelope(facts)
    components = tuple(
        _component_input(item, index)
        for index, item in enumerate(
            _object_list(facts["ashtakoota_components"], "ashtakoota_components")
        )
    )
    subject_manglik = tuple(
        _manglik_input(item, f"subject_manglik_factors[{index}]")
        for index, item in enumerate(
            _object_list(facts["subject_manglik_factors"], "subject_manglik_factors")
        )
    )
    partner_manglik = tuple(
        _manglik_input(item, f"partner_manglik_factors[{index}]")
        for index, item in enumerate(
            _object_list(facts["partner_manglik_factors"], "partner_manglik_factors")
        )
    )
    return CompatibilityInterpretationRequest(
        facts_version=_string(facts["facts_version"], "facts_version"),
        components=components,
        total_achieved_points=_number(
            facts["total_achieved_points"],
            "total_achieved_points",
        ),
        evaluated_maximum_points=_integer(
            facts["evaluated_maximum_points"],
            "evaluated_maximum_points",
        ),
        complete_36_point_evaluation=_boolean(
            facts["complete_36_point_evaluation"],
            "complete_36_point_evaluation",
        ),
        subject_manglik_factors=subject_manglik,
        partner_manglik_factors=partner_manglik,
    )
