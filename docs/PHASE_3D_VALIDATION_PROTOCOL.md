# Phase 3D validation protocol

Phase 3D does not treat deterministic output as proof of predictive accuracy.
Production promotion requires three separate gates:

1. **Automated invariants** — deterministic output, policy boundaries, schema
   compatibility, source traceability, duplicate-evidence controls, conflict
   handling, and abstention tests must pass.
2. **Blinded expert review** — at least 30 frozen cases must be independently
   reviewed without outcome access. Reviewers score source fidelity, reasoning
   coherence, directness, and whether the conclusion follows from the disclosed
   evidence.
3. **Prospective outcomes** — at least 100 pre-registered domain forecasts must
   reach their horizon before outcomes are recorded. Accuracy, coverage,
   abstention, and the complete confusion matrix are reported; unfavourable
   results are not removed.

`blind_case` hashes the chart fingerprint and records a digest over the complete
prediction before review or outcome collection. This proves which forecast was
fixed in advance. It is not an anonymity guarantee if callers put identifying
data inside free-text prediction fields, so integrations must exclude such data.

The engine exposes `confidence_status` as `uncalibrated_*` until prospective
measurement supports a versioned calibration model. Internal weights must never
be described as probabilities. A Phase 3D release remains blocked while either
human gate is pending.

The repository CI result for the exact release commit is also a required
automated gate; passing tests from an earlier commit cannot promote a build.
