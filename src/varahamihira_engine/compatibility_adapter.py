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


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{path} must be a boolean")
    return value


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{path} must be an integer")
    return value


def _number_or_none(value: Any, path: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{path} must be a number or null")
    return float(value)


def _string_tuple(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    return tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(value))


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
    _string(item["source_kind"], f"{path}.source_kind")
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


def _object_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{path} must be a list")
    return value


def compatibility_request_from_astro_facts(
    payload: Mapping[str, Any],
) -> CompatibilityInterpretationRequest:
    """Convert one strict Astro `compatibility_facts_v2` response into engine input."""

    facts = _mapping(payload, "payload")
    _exact_keys(facts, _ASTRO_FACTS_KEYS, "payload")
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
        total_achieved_points=(
            _number_or_none(facts["total_achieved_points"], "total_achieved_points")
            or 0.0
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
