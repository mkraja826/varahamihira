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

## Natal occupant channel

Each classical Graha occupying a relevant whole-sign house creates an occupant trace. Its
direction uses the same controlled strength score and its maximum channel weight is:

`min(1, max(0.1, abs(score) / 8)) * 0.40`

The occupant and house-lord traces use the same independence key when they rely on the same
planet-strength fact for the same domain. The engine keeps the strongest trace, records the
corroborating evidence identifier, and does not add both weights. Conflicting polarities under
one independence key are rejected as a modelling error.

## Natal aspect channel

The seven classical Grahas use the Bṛhat Jātaka 2.13 whole-sign table:

| Relative house | General fraction |
| ---: | ---: |
| 3, 10 | 1/4 |
| 5, 9 | 1/2 |
| 4, 8 | 3/4 |
| 7 | Full |

Mars receives full 4th/8th aspects, Jupiter full 5th/9th aspects, and Saturn full
3rd/10th aspects. Rahu and Ketu are excluded from this seven-Graha pass.

An aspect reaching a relevant domain house uses:

`min(1, max(0.1, abs(score) / 8)) * aspect_fraction * 0.20`

Aspect geometry is classical; converting the source Graha's controlled strength into a
directional domain weight is an API convention. House-lord, occupant, and aspect traces share
the same independence key when they use the same source planet-strength fact for one domain.
The strongest trace is scored once and all corroborating evidence identifiers remain visible.

## Declared significator channel

The `varahamihira_v1` source registry currently supports one domain significator system:
Chapter 10 Karmājīva for `career`. It derives indicators independently from Lagna, Moon, and
Sun reference channels and preserves repetition without collapsing those derivations.

The engine converts each declared Karmājīva indicator's controlled strength into career
evidence. Because the numeric conversion is not a textual formula, the result remains labeled
`convention` while preserving the Chapter 10 rule identifiers. It shares the career
planet-strength independence key with lord, occupant, and aspect channels, so the same Graha
strength is scored once.

No generic kāraka mappings are enabled for money, marriage, family, education, wellbeing,
travel, or spirituality. Adding mappings from another text or tradition requires a separate
versioned classical profile; they must not be silently mixed into `varahamihira_v1`.

## Varga confirmation boundary

D9 is used only through the existing, boundary-tested Vargottama fact: a classical Graha
occupies the same Rashi in D1 and D9. When present, the engine attaches
`VM-BJ-C01-VARGOTTAMA-EVAL-001` to every existing domain trace using that Graha's controlled
strength. D9 confirmation does not create a new directional weight because Vargottama already
contributes to the controlled strength score.

Astro does not currently expose a versioned D10 calculation contract. Career results therefore
carry a zero-weight contextual abstention marker stating that D10 confirmation was not used.
No D10 sign, lord, dignity, house, or career conclusion may be inferred until Astro adds:

- an immutable D10 mapping profile;
- exact 3-degree boundary policy and boundary tests;
- calculation regression fixtures;
- external validation evidence;
- a source-traceable interpretation contract.

## Cancellation and modification boundary

The prediction engine consumes Astro's machine-readable cancellation policy and requires
`varahamihira_v1` to report zero confirmed rules, cancellation disabled, and zero applied
adjustment. A debilitated Graha marked `unsupported_by_profile` remains negative according
to its controlled strength; its existing domain trace receives
`VM-BJ-C02-CANCELLATION-SOURCE-BOUNDARY-001` and a statement that no cancellation was applied.
This annotation is non-additive.

The adapter fails closed if Astro reports an enabled cancellation rule, a non-zero
cancellation adjustment, or an applied per-Graha cancellation. Nīcabhaṅga conventions from
later or different texts are not imported into the Bṛhat Jātaka profile. Enabling any such
rule requires a separate versioned source profile, verse-level provenance, geometry tests,
duplicate-evidence rules, reference fixtures, and external review.

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
