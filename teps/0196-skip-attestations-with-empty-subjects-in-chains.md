---
status: proposed
title: Skip Attestations with Empty Subjects in Tekton Chains
creation-date: '2026-10-25'
last-updated: '2026-10-25'
authors:
  - '@infernus01'
collaborators: []
see-also:
  - TEP-0084
  - TEP-0109
---

# TEP-0196: Skip Attestations with Empty Subjects in Tekton Chains

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Why Subjects, Not Run Status](#why-subjects-not-run-status)
- [Design Details](#design-details)
  - [Where the Check Lives](#where-the-check-lives)
  - [New Annotation Value: skipped](#new-annotation-value-skipped)
  - [When a Run Has More Than One Signable Type](#when-a-run-has-more-than-one-signable-type)
  - [Deep Inspection](#deep-inspection)
  - [OCI Backend](#oci-backend)
- [Design Evaluation](#design-evaluation)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

Chains creates and signs [in-toto](https://github.com/in-toto/attestation/tree/main/spec/v1) attestations for every completed TaskRun and PipelineRun — even when the run produced no output artifacts, leaving the Statement's `subject` field nil.
The in-toto v1 spec [requires at least one subject](https://github.com/in-toto/attestation/blob/main/go/v1/statement.go)
(`ErrSubjectRequired`). Chains never calls `Validate()`, so these invalid attestations get signed, stored in all backends, and permanently uploaded to Rekor.

This TEP adds an empty-subject check after the in-toto Statement is built and before it is signed. If subjects are empty, skip the run and annotate it `chains.tekton.dev/signed=skipped`. The check is based on subjects, not run status — a failed run can still produce artifacts (image pushed before test step fails), and a successful run can have zero subjects (`git-clone`).

## Motivation

[Issue #484](https://github.com/tektoncd/chains/issues/484): Chains signs failed TaskRuns/PipelineRuns that produce no output artifacts and chains produces attestations with `subject: null`.

How this happens today:

1. Run completes. Reconciler starts signing.
2. The TaskRun/PipelineRun itself is always treated as something to attest — even when it produced no artifacts.
3. Subject extraction looks for type-hinted results (`*IMAGE_URL`/`*IMAGE_DIGEST`, `*ARTIFACT_URI`/`*ARTIFACT_DIGEST`, `*ARTIFACT_OUTPUTS`). Finds none. Returns nil.
4. Statement is created with `Subject: nil`.
5. Gets signed, stored in backends, uploaded to Rekor.

The in-toto spec's own `Validate()` would reject them — the [subject field's semantics are under active discussion](https://github.com/in-toto/attestation/issues/349) and the Go library already enforces `ErrSubjectRequired`. Only the OCI storage backend skips empty subjects today. The other backends store blindly.

Example — a clone → build → deploy pipeline:

| Task | Type-hinted results | Subjects | Result |
|---|---|---|---|
| `git-clone` | None | nil | Empty-subject attestation signed |
| `kaniko-build` | `IMAGE_URL`, `IMAGE_DIGEST` | 1 image | Valid attestation |
| `deploy` | None | nil | Empty-subject attestation signed |

All three get `signed=true` today. The `git-clone` and `deploy` attestations violate the spec.

### Goals

- Stop producing in-toto Statements with zero subjects.
- Stop uploading empty-subject attestations to Rekor.
- Make all storage backends behave consistently (not just OCI).
- Make skipped runs observable via annotation + logs.

### Non-Goals

- Changing how subjects are extracted (type-hinting is out of scope).
- Adding new predicate types for "audit" attestations.
- Changing Tekton Pipelines API.
- Fixing existing Rekor entries.

### Use Cases

1. **`git-clone` succeeds, no subjects.** Today: empty-subject attestation stored + uploaded. After: skipped, annotated `signed=skipped`.

2. **Build-and-push fails after pushing image.** Task has `IMAGE_URL` / `IMAGE_DIGEST` results but status is Failed. After: subjects found, so attestation is signed normally. (A status-based check would wrongly skip this.)

3. **PipelineRun with `onError: continue`, partial failures.** Three tasks produce images, two fail. After: PipelineRun attestation includes subjects from the three tasks.

4. **TaskRun times out, no results written.** Today: empty-subject attestation uploaded to Rekor. After: skipped.

### Requirements

1. Check happens after the in-toto Statement is built, before signing.
2. Covers all in-toto format versions Chains supports (v1, v2alpha3, v2alpha4).
3. Prevents signing, storage, and Rekor upload.
4. Skipped runs get `chains.tekton.dev/signed=skipped`, and are not signed again.

## Proposal

Add an empty-subject check in the signing path, after the Statement is built. When the in-toto Statement has no subjects:

1. Skip signing, storage, and Rekor upload.
2. Log at Info level.
3. Annotate the run `signed=skipped`.

Non-in-toto payloads (SimpleSigning) are unchanged.

### Why Subjects, Not Run Status

The initial approach was to check `IsSuccessful()` at the reconciler level.
This is wrong for two reasons:

- **False negative:** Failed run with artifacts. Build pushes image (`IMAGE_URL`/`IMAGE_DIGEST` populated), then test step fails. Image exists, should be attested. Status check would skip it.
- **False positive:** Successful run without artifacts. `git-clone` succeeds but has no `IMAGE_*` or `ARTIFACT_*` results. Status check would still create an empty-subject attestation.

The right question is "did the run produce subjects?", not "did the run succeed?".

## Design Details

### Where the Check Lives

One check, in the signing path, after the in-toto Statement is built and before sign / store / Rekor.

Not on the reconciler — that's the status-based approach we rejected.
Not per storage backend — that's why only OCI skips empty subjects today.

After the Statement is built, not before: subject extraction already lives in each format (type hints, structured results, deep inspection). The Statement is the one place that has the real subject list. Re-checking type-hints on the TaskRun would duplicate that and drift.

All in-toto formats Chains supports (v1, v2alpha3, v2alpha4) go through this path. SimpleSigning is not in-toto and is left alone.

### New Annotation Value: skipped

`chains.tekton.dev/signed` currently has two values: `"true"` and `"failed"`.
Add `"skipped"`.

| Value | Meaning |
|---|---|
| `"true"` | Signed and stored |
| `"failed"` | Signing attempted, errored |
| `"skipped"` | No subjects found, intentionally skipped |

`skipped` is a terminal state. The reconciler must treat it like `true` / `failed`: already handled, do not sign again. If it doesn't, skipped runs get reprocessed forever.

### When a Run Has More Than One Signable Type

A single run can produce more than one payload (TaskRun attestation and OCI image signatures, for example). The annotation is per-run, not per-payload.

| Any payload signed | Everything skipped | Error | Annotation |
|---|---|---|---|
| yes | — | no | `"true"` |
| no | yes | no | `"skipped"` |
| — | — | yes | `"failed"` (existing) |

`"true"` if anything was signed. `"skipped"` only if everything was skipped. Errors still win.

### Deep Inspection

With `enable-deep-inspection=false` (default): only PipelineRun-level results count as subjects. Child TaskRuns may have built images that were never promoted to Pipeline results — the PipelineRun attestation is empty and gets skipped. Child TaskRun attestations still fire. That's existing subject-extraction behavior, not a new gap.

With `enable-deep-inspection=true`: child TaskRun results are aggregated onto the PipelineRun. Subjects show up, attestation is signed.

### OCI Backend

OCI storage already refuses empty-subject Statements. Keep that. The new check also stops signing and Rekor; the OCI guard stays as backup if the central check ever regresses.

## Design Evaluation

- **Reusability:** Single check in the signing path covers all in-toto formats and backends.
- **Simplicity:** One subject check. No new config, no new CRDs.
- **Flexibility:** No new dependencies. No cross-project coupling.
- **Conformance:** No Tekton API changes.
- **Performance:** Empty-subject check is cheap. Skipped runs save signing + storage + upload work.
- **Risks:** (1) Runs unexpectedly skipped — mitigated by `Info` log + `skipped` annotation.
  (2) Systems expecting `signed=true` on all runs — those attestations were invalid anyway.
  (3) If `skipped` is not treated as already-handled, the reconciler loops forever.
- **Drawbacks:** (1) Runs that previously got `signed=true` now get `signed=skipped`. Monitoring rules may need updating.
  (2) No "audit attestation" for runs that produced nothing. Out of scope — in-toto spec requires subjects.

## Alternatives

1. **Check `IsSuccessful()` at reconciler level.** Rejected — wrong signal. Failed runs can have subjects, successful runs can have none. See [Why Subjects, Not Run Status](#why-subjects-not-run-status).

2. **ConfigMap opt-in/opt-out.** Rejected — producing invalid attestations shouldn't be configurable. The OCI backend already skips silently without config.

3. **Store locally but skip Rekor.** Rejected — locally stored attestation is still spec-non-compliant. Downstream consumers would still see it.

4. **Fix each storage backend individually.** Rejected — every backend to change instead of 1 central check. Signing + Rekor upload still happen. Future backends need to remember the guard.

5. **Call `Validate()` and use `ErrSubjectRequired` as skip signal.** Partially accepted — good idea but `Validate()` checks more than subjects (type URI, predicate, digests). Would conflate "no subjects" (expected skip) with "malformed statement" (unexpected error). Use targeted check, optionally add `Validate()` as general sanity check.

## Implementation Plan

Chains only. No Pipelines change.

1. Subject check in the signing path.
2. `skipped` as a terminal annotation value (write it, treat it as already reconciled).
3. Annotation rule above for mixed signables.
4. Docs: `signed=skipped` and the behavior change.

### Test Plan

**Unit tests:**

1. No type-hinted results → not signed, annotated `skipped`.
2. Has `IMAGE_URL`/`IMAGE_DIGEST` → signed normally.
3. Failed status, image results present → signed. (Proves we didn't key off status.)
4. Succeeded, no results → skipped.
5. Mixed signables: one skipped, one signed → annotation `true`.
6. Every in-toto format Chains supports, empty subjects → skipped.
7. `signed=skipped` is treated as already handled, not reprocessed.

**E2E tests:**

8. `git-clone` TaskRun → `skipped` annotation, no attestation.
9. Build-and-push TaskRun → attestation with image subject.

### Infrastructure Needed

None.

### Upgrade and Migration Strategy

Behavioral change, no API change. Runs with subjects are unaffected. Runs without subjects switch from `signed=true` (with invalid attestation) to `signed=skipped` (with no attestation). Operators should update monitoring rules that check annotation values.

### Implementation Pull Requests

<!--
To be filled after implementation.
-->

## References

- [Tekton Chains Issue #484](https://github.com/tektoncd/chains/issues/484)
- [in-toto Attestation Framework v1 — subject requirement](https://github.com/in-toto/attestation/blob/main/go/v1/statement.go)
- [in-toto/attestation#349 — subject field semantics discussion](https://github.com/in-toto/attestation/issues/349)
- [TEP-0084: End-to-End Provenance Collection](https://github.com/tektoncd/community/blob/main/teps/0084-endtoend-provenance-collection.md)
- [TEP-0109: Better Structured Provenance Retrieval](https://github.com/tektoncd/community/blob/main/teps/0109-better-structured-provenance-retrieval-in-tekton-chains.md)
