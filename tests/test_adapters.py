from varahamihira_engine.adapters import request_from_astro_bridge
from varahamihira_engine.models import Polarity


def test_astro_bridge_contract_is_parsed_without_endpoint_shape_guessing() -> None:
    request = request_from_astro_bridge(
        {
            "bridge_version": "astro_varahamihira_evidence_v1",
            "period": "weekly",
            "as_of": "2026-07-23T00:00:00+05:30",
            "calculation_profile": "south_indian_drik_lahiri_jpl_de440s_v1",
            "classical_profile": "varahamihira_v1",
            "evidence": [
                {
                    "evidence_id": "fixture-1",
                    "domain": "career",
                    "statement": "Synthetic bridge evidence",
                    "polarity": "challenging",
                    "weight": 0.75,
                    "source_rule_ids": ["TEST-NOT-A-CLASSICAL-CITATION"],
                    "source_kind": "classical",
                    "reason": "Synthetic fixture.",
                }
            ],
        }
    )

    assert request.period == "weekly"
    assert request.evidence[0].polarity is Polarity.CHALLENGING
