# Varahamihira Engine

A deterministic, source-traceable interpretation engine derived from Varāhamihira's *Bṛhat Jātaka* for integration with the Horos and Astro projects.

The engine is being built with strict separation between:

1. astronomical facts supplied by the Skyfield/JPL Astro service;
2. classical rules tied to an approved edition, chapter, and verse;
3. deterministic conflict resolution;
4. consumer wording that cannot change the underlying result.

No rule may be attributed to *Bṛhat Jātaka* until its source reference has been reviewed. No AI-generated or invented verse is accepted as classical evidence.

## Validation boundaries

Textual source review in this repository means that a classical rule is traceable to the pinned edition and has passed editorial review. It does **not** independently validate planetary positions, charts, Panchanga, or other astronomical calculations.

The Astro repository owns astronomical regression baselines and the external-validation evidence manifest. Internal JPL baselines protect against calculation drift but are not independent evidence. Horos and this engine must not claim external-software verification until Astro records two distinct approved external sources for every frozen validation case.

Astrology is not scientifically established as a reliable predictor of future events. Engine output is intended for cultural, spiritual, and reflective use and is not professional medical, legal, mental-health, or financial advice.
