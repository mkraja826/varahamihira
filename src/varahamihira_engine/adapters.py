from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import Evidence, Polarity, PredictionRequest


def request_from_astro_bridge(payload: Mapping[str, Any]) -> PredictionRequest:
    """Parse the versioned Astro-to-Varahamihira bridge contract.

    This intentionally does not guess the shape of individual Astro endpoints.
    Astro must normalize its classical condition, aspect, strength, dasha, and
    transit results into the bridge evidence records before calling this engine.
    """

    bridge_version = payload.get("bridge_version")
    if bridge_version != "astro_varahamihira_evidence_v1":
        raise ValueError("unsupported Astro bridge version")

    raw_evidence = payload.get("evidence")
    if not isinstance(raw_evidence, list):
        raise ValueError("evidence must be a list")

    evidence: list[Evidence] = []
    for raw in raw_evidence:
        if not isinstance(raw, Mapping):
            raise ValueError("each evidence item must be an object")
        rule_ids = raw.get("source_rule_ids", [])
        if not isinstance(rule_ids, list) or not all(
            isinstance(item, str) for item in rule_ids
        ):
            raise ValueError("source_rule_ids must be a string list")
        evidence.append(
            Evidence(
                evidence_id=str(raw.get("evidence_id", "")),
                domain=str(raw.get("domain", "")),
                statement=str(raw.get("statement", "")),
                polarity=Polarity(str(raw.get("polarity", ""))),
                weight=float(raw.get("weight", 0.0)),
                source_rule_ids=tuple(rule_ids),
                source_kind=str(raw.get("source_kind", "")),
                reason=str(raw.get("reason", "")),
                independence_key=str(
                    raw.get("independence_key", raw.get("evidence_id", ""))
                ),
            )
        )

    return PredictionRequest(
        period=str(payload.get("period", "")),
        as_of=str(payload.get("as_of", "")),
        calculation_profile=str(payload.get("calculation_profile", "")),
        classical_profile=str(payload.get("classical_profile", "")),
        evidence=tuple(evidence),
    )
