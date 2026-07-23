from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .models import Outlook, PredictionResponse

_OUTCOME_LABELS = {item.value for item in Outlook}


def canonical_digest(value: dict[str, Any]) -> str:
    """Return a stable SHA-256 digest suitable for pre-registering a case."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def blind_case(
    *,
    case_id: str,
    prediction: PredictionResponse,
    chart_fingerprint: str,
    registered_at: str | None = None,
) -> dict[str, Any]:
    """Freeze a prediction without exposing birth or identity data."""
    if not case_id.strip() or not chart_fingerprint.strip():
        raise ValueError("case_id and chart_fingerprint are required")
    payload = prediction.as_dict()
    case = {
        "case_id": case_id,
        "chart_fingerprint": hashlib.sha256(chart_fingerprint.encode()).hexdigest(),
        "registered_at": registered_at
        or datetime.now(UTC).replace(microsecond=0).isoformat(),
        "prediction": payload,
    }
    return {**case, "registration_digest": canonical_digest(case)}


@dataclass(frozen=True, slots=True)
class ValidationGate:
    name: str
    status: str
    completed: int
    required: int
    reason: str


def validation_gates(
    *,
    automated_checks_passed: bool,
    expert_reviews: Iterable[dict[str, Any]],
    outcomes: Iterable[dict[str, Any]],
    required_expert_reviews: int = 30,
    required_outcomes: int = 100,
) -> tuple[ValidationGate, ...]:
    reviews = tuple(expert_reviews)
    observed = tuple(outcomes)
    valid_reviews = sum(
        1
        for item in reviews
        if item.get("blind") is True
        and isinstance(item.get("accuracy_rating"), int)
        and 1 <= item["accuracy_rating"] <= 5
    )
    valid_outcomes = sum(
        1
        for item in observed
        if item.get("observed_outlook") in _OUTCOME_LABELS
        and item.get("prediction_digest")
    )
    return (
        ValidationGate(
            "automated_invariants",
            "passed" if automated_checks_passed else "pending",
            int(automated_checks_passed),
            1,
            "Determinism, policy, schema, and source-traceability checks.",
        ),
        ValidationGate(
            "blinded_expert_review",
            "passed" if valid_reviews >= required_expert_reviews else "pending",
            valid_reviews,
            required_expert_reviews,
            "Independent reviewers score frozen predictions without outcome access.",
        ),
        ValidationGate(
            "prospective_outcomes",
            "passed" if valid_outcomes >= required_outcomes else "pending",
            valid_outcomes,
            required_outcomes,
            "Outcomes are recorded only after the pre-registered forecast horizon.",
        ),
    )


def outcome_metrics(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Score categorical forecasts; abstentions remain visible and unscored."""
    rows = tuple(records)
    scored = [
        row
        for row in rows
        if row.get("predicted_outlook") in _OUTCOME_LABELS - {Outlook.INSUFFICIENT.value}
        and row.get("observed_outlook") in _OUTCOME_LABELS - {Outlook.INSUFFICIENT.value}
    ]
    correct = sum(row["predicted_outlook"] == row["observed_outlook"] for row in scored)
    confusion = Counter(
        (row["predicted_outlook"], row["observed_outlook"]) for row in scored
    )
    abstentions = sum(
        row.get("predicted_outlook") == Outlook.INSUFFICIENT.value for row in rows
    )
    return {
        "total_records": len(rows),
        "scored_records": len(scored),
        "abstentions": abstentions,
        "coverage": round(len(scored) / len(rows), 6) if rows else 0.0,
        "categorical_accuracy": round(correct / len(scored), 6) if scored else None,
        "confusion": {
            f"{predicted}->{observed}": count
            for (predicted, observed), count in sorted(confusion.items())
        },
        "calibration_status": (
            "prospective_measurement_available" if scored else "insufficient_outcomes"
        ),
    }
