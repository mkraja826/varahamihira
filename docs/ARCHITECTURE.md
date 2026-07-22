# Architecture

## System ownership

### Astro repository

Astro remains the sole calculation authority for:

- Skyfield/JPL DE440s positions;
- Lahiri sidereal conversion;
- D1 and D9;
- Panchanga;
- Vimshottari timing;
- Varahamihira conditions, aspects, relationships, Ashtakavarga, strength,
  career, and source-linked evidence.

The Varahamihira package must not recalculate planetary positions.

### Varahamihira repository

This repository owns:

- the normalized Astro evidence bridge;
- direct favourable, mixed, challenging, or insufficient conclusions;
- transparent convention weights;
- conflict preservation;
- consumer-safety exclusions;
- the mandatory astrology disclaimer;
- a versioned output contract for Horos.

A numeric weight is an engine convention. It must never be attributed to a
Brihat Jataka verse.

### Horos repository

Horos owns authentication, profiles, entitlement, caching, localization, and
mobile presentation. Horos must display the engine's conclusion, evidence,
limitations, and disclaimer without changing a negative result into positive
copy.

## Flow

```text
Horos birth profile and requested period
        -> Astro calculation and classical evidence endpoints
        -> astro_varahamihira_evidence_v1 bridge
        -> Varahamihira deterministic evaluation
        -> horos_brihat_jataka_v1 response
        -> Horos English/Hindi/Telugu renderer
```

## Source policy

The pinned classical source remains N. Chidambaram Aiyar's 1905 public-domain
edition of Brihat Jataka, archive identifier `brihatjataka00varaiala`.
Verse numbers may only be registered after reconciliation with the approved
edition. Synthetic tests must be visibly labelled and may not resemble a
classical citation.

## No-sugar-coating rule

If challenging evidence dominates the configured threshold, the output must say
the result is negative. It may provide calm practical guidance, but guidance
cannot rewrite, hide, or exaggerate the finding.

## Phase boundaries

Phase 1 implements the bridge, evidence model, deterministic conflict resolver,
disclaimer, blocked domains, and contract tests. It does not yet claim complete
prediction coverage.

Phase 2 adds reviewed domain rules and an Astro bridge endpoint.

Phase 3 integrates the versioned response into Horos and replaces static
editorial readings only after validation.
