# Phase 3 natal-domain method

Phase 3 separates lifetime chart capacity, period activation, and short-term timing.
This document specifies the first natal channel; it does not claim that the channel is a
complete prediction model.

## Source boundary

House ownership and planetary-condition facts remain pinned to the repository's
`varahamihira_v1` classical profile and its public-domain *Brihat Jataka* reference.
The conversion of those facts into a numeric domain score is an API convention, not a
classical textual formula.

## Domain houses

| Domain | Relevant whole-sign houses |
| --- | --- |
| career | 10 |
| money_resources | 2, 11 |
| relationships_marriage | 7 |
| family_home | 4 |
| education_creativity | 5 |
| wellbeing | 1, 6 |
| travel_change | 3, 9, 12 |
| spirituality | 9, 12 |

Wellbeing is non-diagnostic. The blocked consumer domains in `policy.py` remain blocked.

## Natal house-lord channel

1. Infer the whole-sign ascendant independently from every classical Graha's D1 sign and
   house. Reject the payload unless all Grahas imply the same ascendant.
2. Resolve the classical seven-Graha ruler of every relevant house.
3. Look up that lord's controlled strength score.
4. Count a lord once per domain even when it rules two relevant houses.
5. Preserve all contributing classical rule identifiers, but label the evidence source as
   `convention` because the numeric synthesis is not a verse.
6. Convert strength to evidence weight using:

   `min(1, max(0.1, abs(score) / 8)) * 0.60`

The remaining 0.40 of the future natal-domain budget is reserved for independently sourced
occupant, aspect, significator, varga, and cancellation channels. They must not be enabled
until their formulas and duplicate-evidence rules are specified and tested.

## Abstention and conflict

- Zero score is contextual and creates no direction.
- Supporting and challenging channels are both retained.
- Conflicts are resolved by the engine's declared threshold; no factor is silently removed.
- Coverage markers never affect scores.
- Daśā and transit evidence remain separate from natal evidence.

## Phase 3D validation requirements

Before production release, this method requires synthetic polarity tests, reference-chart
fixtures, duplicate-channel tests, output calibration tests, blinded expert review, and a
prospective outcome protocol. Automated tests cannot substitute for the last two gates.
