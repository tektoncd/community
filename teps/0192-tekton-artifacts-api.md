---
title: "Tekton Artifacts API"
authors:
  - "@vdemeester"
  - "@savitaashture"
creation-date: 2026-08-19
last-updated: 2026-08-19
status: proposed
see-also:
  - TEP-0085
  - TEP-0139
  - TEP-0147
  - TEP-0193
---

# TEP-0192: Tekton Artifacts API

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Current Limitations](#current-limitations)
  - [Convergence Opportunity](#convergence-opportunity)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Two Artifact Types](#two-artifact-types)
    - [Default type and disabled storage](#default-type-and-disabled-storage)
  - [Replacing TEP-0147 Phase 1 API](#replacing-tep-0147-phase-1-api)
  - [Relationship to TEP-0147 and TEP-0139](#relationship-to-tep-0147-and-tep-0139)
- [Design Details](#design-details)
  - [Artifact Declaration in Task Spec](#artifact-declaration-in-task-spec)
  - [ArtifactDeclaration Type](#artifactdeclaration-type)
  - [StepAction Artifacts](#stepaction-artifacts)
    - [StepAction declares its outputs](#stepaction-declares-its-outputs)
    - [Task surfaces them explicitly](#task-surfaces-them-explicitly)
    - [Where each field is declared](#where-each-field-is-declared)
    - [Inputs are passed as params](#inputs-are-passed-as-params)
  - [Extending ArtifactValue for Status](#extending-artifactvalue-for-status)
    - [Inline threshold bounds](#inline-threshold-bounds)
  - [Variable Substitution](#variable-substitution)
  - [Entrypoint Behavior](#entrypoint-behavior)
  - [TaskRun Status](#taskrun-status)
  - [Pipeline-Level Artifact Bindings](#pipeline-level-artifact-bindings)
  - [Pipeline-Level Artifact Declarations](#pipeline-level-artifact-declarations)
  - [PipelineRun Artifact Inputs](#pipelinerun-artifact-inputs)
  - [Transparent Content Fetch and Verification](#transparent-content-fetch-and-verification)
  - [Storage Backend](#storage-backend)
  - [Integration with Tekton Chains](#integration-with-tekton-chains)
  - [Integration with Tekton Results and UIs](#integration-with-tekton-results-and-uis)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Keep the TEP-0147 Phase 1 Provenance JSON API](#keep-the-tep-0147-phase-1-provenance-json-api)
  - [TEP-0139 Injected Trusted Steps with PVC](#tep-0139-injected-trusted-steps-with-pvc)
  - [TEP-0127 Sidecar Logs](#tep-0127-sidecar-logs)
  - [Workspaces Only](#workspaces-only)
- [Implementation Plan](#implementation-plan)
  - [Phase 1 (Alpha)](#phase-1-alpha)
  - [Phase 2 (Beta)](#phase-2-beta)
  - [Phase 3 (Stable)](#phase-3-stable)
  - [Test Plan](#test-plan)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
- [References](#references)
<!-- /toc -->

## Summary

This TEP introduces a declarative Artifact API for Tekton Tasks and
Pipelines, replacing the manual provenance-JSON model from TEP-0147
Phase 1 (alpha, behind `enable-artifacts` feature flag).

Tasks declare `spec.artifacts.inputs` and `spec.artifacts.outputs` with
two types:

- **`type: content`** — the step writes data to a path; Tekton uploads,
  downloads, and verifies it transparently across Tasks.
- **`type: reference`** — the step already pushed content elsewhere (e.g.,
  `buildah push`); it writes a URI and digest so Tekton can record and
  propagate the reference.

Pipelines bind artifacts between Tasks with `from:` syntax, creating
implicit DAG edges. The controller injects init containers to fetch and
verify content artifacts before user steps execute.

This TEP also defines the `Provider` interface that storage backends
implement. The first (and default) implementation is the OCI registry
backend defined in [TEP-0193](0193-tekton-artifacts-oci-storage.md).

## Motivation

### Current Limitations

**TEP-0147 Phase 1 (alpha)** provides an artifact provenance mechanism
where Steps write raw JSON to `$(step.artifacts.path)`:

```yaml
# Current TEP-0147 Phase 1: manual JSON writing
steps:
  - name: build
    script: |
      cat > $(step.artifacts.path) << EOF
      {
        "outputs":[{
          "name":"image",
          "values":[{
            "uri":"pkg:docker/myapp@sha256:abc123",
            "digest":{"sha256":"abc123..."}
          }]
        }]
      }
      EOF
```

This has several problems:

1. **Error-prone**: Task authors hand-write JSON with specific schema.
   Typos, malformed JSON, and missing fields produce silent failures.

2. **No storage**: Tekton records artifact metadata but does not manage
   content. Steps handle their own upload/download.

3. **No trust chain**: Without Tekton-managed storage, there is no built-in
   verification that artifacts passed between Tasks are untampered.

4. **No declarative API**: Tasks don't declare what artifacts they consume
   or produce. There's no validation at admission time.

5. **Size limits**: Results stored via termination messages are limited to
   4KB per container, 12KB total per Pod. Even with TEP-0127's sidecar
   logs, results end up in the ~1.5MB CRD size limit.

6. **Type hinting for Chains**: Tekton Chains relies on result names like
   `IMAGE_URL` and `IMAGE_DIGEST` to identify SLSA subjects — a fragile
   convention.

7. **PVC Workspaces for inter-task data**: The dominant pattern for passing
   data between Tasks today is shared PVC Workspaces. This introduces
   significant operational and security problems:
   - **ReadWriteMany requirement**: Parallel Tasks need RWX PVCs, which
     are not universally available and often expensive.
   - **Race conditions**: Concurrent PipelineRuns sharing the same RWX
     workspace can tamper with each other's data — a known security
     concern (see [shared PVC vulnerability report](https://github.com/tektoncd/pipeline/issues/8448)).
   - **Lifecycle management**: PVCs must be provisioned, sized, and
     cleaned up. `volumeClaimTemplate` creates per-run PVCs but doesn't
     always clean them up.
   - **Affinity constraints**: Pod-to-PVC affinity (coschedule assistant)
     limits scheduling flexibility.
   - **No provenance**: Files on a PVC have no digest, no URI, no
     attestation trail — they're opaque blobs.

   Content artifacts (`type: content`) eliminate the need for shared PVC
   Workspaces in the most common patterns: clone→build, clone→test,
   build→sign. Analysis of the tekton-oracle cluster showed that **most
   PVC workspaces exist solely to pass data between Tasks** (source
   checkouts, build outputs, test results) — exactly what content
   artifacts handle with better security (digest verification), no
   infrastructure requirements (uses existing OCI registry), and full
   provenance tracking.

### Convergence Opportunity

Three related TEPs address overlapping concerns:

| TEP | Focus | Status | Provenance | Storage | Declarative API |
|-----|-------|--------|------------|---------|-----------------|
| [TEP-0147](0147-tekton-artifacts-phase1.md) | Artifact provenance | Implemented (alpha) | ✅ | ❌ | ❌ |
| [TEP-0139](0139-trusted-artifacts.md) | Trusted artifact sharing | Proposed | ✅ | ✅ (PVC) | ✅ |
| This TEP (0192) | Declarative Artifact API | Proposed | ✅ | ✅ (pluggable) | ✅ |

This TEP unifies them: **TEP-0147's provenance structure + TEP-0139's
declarative API + pluggable storage backends**.

### Goals

1. **Declarative Artifact API** — Tasks declare `spec.artifacts.inputs` and
   `spec.artifacts.outputs` with validation at admission time.
2. **Two artifact types** — `reference` (Tekton records metadata) and
   `content` (Tekton manages storage and transport).
3. **Self-describing Steps** — `StepAction`s declare the artifacts they
   produce, so reusable Steps participate in the Artifacts API rather than
   remaining on the `IMAGE_URL`/`IMAGE_DIGEST` type-hinting convention.
4. **Transparent transport** — for content artifacts, Tekton handles upload,
   download, and digest verification without user intervention.
5. **Pipeline-level binding** — Pipelines connect Tasks through artifact
   bindings with implicit DAG edges.
6. **SLSA subject declaration** — `subject: true` on artifact declarations
   replaces the `IMAGE_URL`/`IMAGE_DIGEST` type-hinting convention.
7. **Pluggable storage** — Define a `Provider` interface for storage
   backends (OCI, S3, GCS, PVC). The default OCI implementation is in
   [TEP-0193](0193-tekton-artifacts-oci-storage.md).
8. **Replace TEP-0147 Phase 1 API** — the manual `$(step.artifacts.path)`
   provenance-JSON model is deprecated and removed. This is acceptable
   because the feature is alpha, behind a feature flag.

### Non-Goals

1. Replacing Tekton Results project (long-term storage and querying).
2. Automatic artifact streaming during Task execution.
3. Defining specific storage backend implementations (see TEP-0193 for OCI).
4. Auto-provisioning storage infrastructure.
5. Changing how `spec.results` (inline string/object results) work — they
   remain as-is.
6. **Signature and policy verification.** Verification in this TEP is
   digest-only: it establishes that content is byte-identical to what the
   producing TaskRun recorded. Verifying *who* produced an artifact and
   whether it is authorised for use requires a trust root and key
   distribution, and remains the domain of Tekton Chains and admission-time
   policy engines.
7. **Per-Step input provenance.** Tekton records which Task consumed an
   artifact, not which Step within it. Steps in a Task share a pod and an
   `emptyDir` and are not mutually distrusting — the Task is the trust unit,
   so per-Step input attribution would add API surface without adding a
   guarantee.

### Use Cases

**Use Case 1: Multi-Image Build (reference artifact)**

A Task builds and pushes container images. It doesn't need Tekton to
transport the images — buildah already pushed them. It just needs to tell
Tekton what it built.

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-images
spec:
  params:
    - name: image
  artifacts:
    outputs:
      - name: image
        type: reference
        subject: true
  steps:
    - name: build
      image: quay.io/buildah/stable:latest
      script: |
        buildah build -t $(params.image) .
        buildah push $(params.image)
        # Record the reference — Tekton doesn't transport it, just records it
        DIGEST=$(buildah inspect --format '{{.Digest}}' $(params.image))
        echo "$(params.image)@${DIGEST}" > $(outputs.image.uri)
```

**Use Case 2: Test Results (content artifact)**

A Task produces JUnit XML that a downstream reporting Task needs to consume.
Tekton transports the content.

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: run-tests
spec:
  artifacts:
    outputs:
      - name: test-results
        type: content
        mediaType: application/xml
  steps:
    - name: test
      image: maven:latest
      script: |
        mvn test
        cp target/surefire-reports/*.xml $(outputs.test-results.path)/
```

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: report-results
spec:
  artifacts:
    inputs:
      - name: results
  steps:
    - name: report
      image: reporter:latest
      script: |
        # Content was fetched and verified by Tekton before this step runs
        process-junit $(inputs.results.path)/*.xml
```

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: test-and-report
spec:
  tasks:
    - name: test
      taskRef:
        name: run-tests
    - name: report
      taskRef:
        name: report-results
      artifacts:
        inputs:
          - name: results
            from: tasks.test.outputs.test-results
      # runAfter is implicit from the artifact dependency
```

**Use Case 3: SBOM Generation with Signing**

An SBOM (10KB–10MB) is produced by one Task and consumed by a signing Task.
The SBOM is content; the signed image is a reference.

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: generate-sbom
spec:
  params:
    - name: image
  artifacts:
    outputs:
      - name: sbom
        type: content
        mediaType: application/spdx+json
  steps:
    - name: generate
      image: syft:latest
      script: |
        syft scan $(params.image) -o spdx-json > $(outputs.sbom.path)
```

**Use Case 4: Source Passing Between Tasks**

A clone Task fetches source code and passes it to a build Task. The source
tarball is a content artifact — Tekton uploads it from the clone Task and
downloads it into the build Task.

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: git-clone
spec:
  params:
    - name: url
    - name: revision
  artifacts:
    outputs:
      - name: source
        type: content
  steps:
    - name: clone
      image: alpine/git:latest
      script: |
        git clone $(params.url) $(outputs.source.path)
        cd $(outputs.source.path) && git checkout $(params.revision)
```

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build
spec:
  artifacts:
    inputs:
      - name: source
    outputs:
      - name: image
        type: reference
        subject: true
  steps:
    - name: build-and-push
      image: quay.io/buildah/stable:latest
      script: |
        cd $(inputs.source.path)
        buildah build -t myimage .
        buildah push myimage
        echo "registry.example.com/myimage@sha256:..." > $(outputs.image.uri)
```

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: clone-build
spec:
  tasks:
    - name: clone
      taskRef:
        name: git-clone
      params:
        - name: url
          value: "https://github.com/example/app"
        - name: revision
          value: main
    - name: build
      taskRef:
        name: build
      artifacts:
        inputs:
          - name: source
            from: tasks.clone.outputs.source
```

This replaces the common pattern of Workspaces + PVC for source sharing
between Tasks, removing the need for ReadWriteMany PVCs.

**Use Case 5: Release Pipeline Without PVCs**

Release pipelines typically chain many Tasks (clone → build → sign →
publish → draft release) using a shared PVC workspace with subPaths.
With content artifacts, each Task declares its inputs and outputs
explicitly:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: release
spec:
  tasks:
    - name: clone
      taskRef:
        name: git-clone
      params:
        - name: url
          value: "https://github.com/tektoncd/pipeline"
    - name: build
      taskRef:
        name: build-release
      artifacts:
        inputs:
          - name: source
            from: tasks.clone.outputs.source
    - name: sign
      taskRef:
        name: sign-artifacts
      artifacts:
        inputs:
          - name: release-artifacts
            from: tasks.build.outputs.release-artifacts
          - name: image-ref
            from: tasks.build.outputs.image
    - name: publish
      taskRef:
        name: publish-release
      artifacts:
        inputs:
          - name: release-artifacts
            from: tasks.build.outputs.release-artifacts
          - name: signatures
            from: tasks.sign.outputs.signatures
```

No PVC, no affinity assistant, no ReadWriteMany, no cleanup. Each
artifact is content-addressed, digest-verified, and tracked in
provenance. The Pipeline is also more readable — data flow is explicit
in the artifact bindings rather than implicit in shared filesystem paths.

### Requirements

**Must Have:**

1. Tasks declare `spec.artifacts.inputs` and `spec.artifacts.outputs`.
2. Two types: `reference` and `content` (default: `content`).
3. `$(outputs.<name>.path)` for content artifacts, `$(outputs.<name>.uri)`
   for reference artifacts.
4. `$(inputs.<name>.path)` for consuming content artifacts.
5. Pipeline-level `artifacts.inputs[].from` binding with implicit DAG.
6. `subject: true` for SLSA attestation subject identification.
7. `Provider` interface for pluggable storage backends.
8. Init container injection for downloading content artifacts.
9. Digest verification on upload and download.
10. Feature-flag gated (`enable-artifacts` flag, already exists).

**Nice to Have (can be deferred):**

11. Pipeline-level artifact declarations (inputs/outputs on Pipeline spec).
12. PipelineRun-level artifact inputs.
13. Inline storage mode for small content artifacts.

## Proposal

### Two Artifact Types

The core insight is that artifacts in a CI/CD pipeline fall into two
categories:

**Reference artifacts (`type: reference`)**: The step already stored the
content somewhere (e.g., `buildah push` pushed an image to a registry).
Tekton only needs to **record** the URI and digest for provenance tracking
and downstream consumption. No upload or download happens.

**Content artifacts (`type: content`)**: The step produces data that needs
to be **transported** to downstream Tasks (e.g., test results, SBOMs,
source tarballs). The **entrypoint** uploads the content to a storage
backend after the step completes; an **init container** downloads and
verifies it before any step of a consuming Task runs.

The two actors are distinct and appear throughout this TEP: the entrypoint
is a **per-Step** actor (it wraps one step and handles that step's outputs),
while the fetching init container is a **per-Task** actor (it runs once,
before all steps, and satisfies the Task's declared inputs).

This distinction is explicit in the Task spec via the `type` field. When
omitted, `type` defaults to `content`.

#### Default type and disabled storage

`content` is the default type, but content storage is **disabled by
default** (see [Storage Backend](#storage-backend)). The minimal declaration
therefore selects the type that needs infrastructure the operator may not
have configured. Rather than making Task validity depend on cluster
configuration — which would make catalog Tasks non-portable — the behaviour
degrades:

- With content storage **disabled**, content artifacts are still digested
  and recorded in TaskRun status, but not uploaded. This is the same
  provenance-only degradation applied to unsurfaced artifacts (see
  [Entrypoint Behavior](#entrypoint-behavior)), and matches what TEP-0147
  Phase 1 provides today.
- A **Pipeline that binds** a content artifact (`from: tasks.x.outputs.y`)
  is rejected at admission when content storage is disabled, with an error
  naming the artifact and the ConfigMap setting to enable. Binding is the
  point at which transport is genuinely required, so that is where the
  failure belongs.

A Task is therefore always valid on its own, and the error surfaces where
the missing capability actually matters.

### Replacing TEP-0147 Phase 1 API

The current TEP-0147 Phase 1 API (`$(step.artifacts.path)` with manual
JSON writing) is **deprecated and removed** by this TEP.

**Justification**: The feature is alpha, behind the `enable-artifacts`
feature flag. Per the [API compatibility
policy](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md),
alpha features may introduce breaking changes.

**Migration path**:

| TEP-0147 Phase 1                                                                      | This TEP                                   |
|---------------------------------------------------------------------------------------|--------------------------------------------|
| `$(step.artifacts.path)` with JSON                                                    | `$(outputs.<name>.uri)` for references     |
| `$(artifacts.path)` with JSON                                                         | `$(outputs.<name>.path)` for content       |
| No `spec.artifacts` declaration                                                       | `spec.artifacts.outputs`, `spec.artifacts.inputs` declaration       |
| Manual JSON: `{"outputs":[{"name":"image","values":[{"uri":"...","digest":{...}}]}]}` | `echo "uri@digest" > $(outputs.image.uri)` |

The new API is simpler, validated at admission, and integrated with
Tekton's transport and provenance systems.

### Relationship to TEP-0147 and TEP-0139

| Aspect           | TEP-0147 Phase 1              | TEP-0139                       | This TEP (0192)                                |
|------------------|-------------------------------|--------------------------------|------------------------------------------------|
| Declarative API  | ❌                            | ✅ `spec.inputs/outputs`       | ✅ `spec.artifacts.inputs/outputs`             |
| Step API         | `$(step.artifacts.path)` JSON | Provenance files               | `$(outputs.name.path)` / `$(outputs.name.uri)` |
| Pipeline binding | `$(tasks.name.outputs.art)`   | `inputs: [{from: ...}]`        | `artifacts.inputs: [{from: ...}]`              |
| Storage          | ❌ User-managed               | PVC + injected Steps           | Pluggable backends via Provider                |
| Trust            | ❌                            | Injected verify Steps          | Init container digest verification             |
| Transport        | ❌                            | Injected upload/download Steps | Entrypoint + init container (transparent)      |

**What we adopt from TEP-0139:**
- Declarative API (`spec.artifacts.inputs/outputs`)
- Pipeline-level binding
- Chain of trust via digest verification

**Where we differ from TEP-0139:**
- Entrypoint + init container instead of 4 injected Steps (lower overhead)
- Pluggable backends instead of PVC-only
- Content stored as-is, not as tarballs on PVC

## Design Details

### Artifact Declaration in Task Spec

Tasks declare artifacts in `spec.artifacts`:

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-and-test
spec:
  artifacts:
    inputs:
      - name: source
        description: Source code to build
    outputs:
      - name: image
        description: Built container image reference
        type: reference
        subject: true
      - name: test-results
        description: JUnit test results
        type: content
        mediaType: application/xml
      - name: build-log
        description: Build summary
        type: content
  steps:
    - name: build
      image: builder:latest
      script: |
        cd $(inputs.source.path)
        make build
        make push IMAGE=registry.example.com/myapp:latest
        echo "registry.example.com/myapp@sha256:abc..." > $(outputs.image.uri)
    - name: test
      image: tester:latest
      script: |
        make test
        cp target/surefire-reports/*.xml $(outputs.test-results.path)/
        echo "Tests passed: 42/42" > $(outputs.build-log.path)
```

### ArtifactDeclaration Type

```go
// ArtifactDeclarations declares what artifacts a Task consumes and produces.
type ArtifactDeclarations struct {
    // Inputs declares artifacts that the Task expects to consume.
    // +listType=atomic
    Inputs []ArtifactDeclaration `json:"inputs,omitempty"`
    // Outputs declares artifacts that the Task produces.
    // +listType=atomic
    Outputs []ArtifactDeclaration `json:"outputs,omitempty"`
}

// ArtifactDeclaration describes a single artifact input or output.
type ArtifactDeclaration struct {
    // Name of the artifact (used in path substitution and pipeline bindings).
    Name string `json:"name"`
    // Description of the artifact.
    // +optional
    Description string `json:"description,omitempty"`
    // Type of the artifact: "reference" or "content".
    // - "reference": step already pushed content, writes URI+digest for Tekton to record.
    // - "content": step writes data to a path, Tekton handles upload/download/verify.
    // Default: "content".
    // +optional
    Type ArtifactType `json:"type,omitempty"`
    // MediaType hint for the artifact content (e.g., application/xml, application/spdx+json).
    // Used by storage backends for content-type metadata.
    // +optional
    MediaType string `json:"mediaType,omitempty"`
    // Subject marks this artifact as the primary build output — the SLSA
    // attestation subject. Chains uses this instead of the IMAGE_URL/IMAGE_DIGEST
    // type-hinting convention. Multiple artifacts can be subjects.
    // +optional
    Subject bool `json:"subject,omitempty"`
    // Value surfaces an artifact produced by a Step, using
    // $(steps.<step>.artifacts.<name>). Mirrors TaskResult.Value. When set,
    // Type and MediaType are inherited from the referenced step artifact.
    // +optional
    Value string `json:"value,omitempty"`
}

// ArtifactType distinguishes how Tekton handles the artifact.
type ArtifactType string

const (
    // ArtifactTypeContent means Tekton manages storage and transport.
    ArtifactTypeContent ArtifactType = "content"
    // ArtifactTypeReference means the step handles storage; Tekton records metadata.
    ArtifactTypeReference ArtifactType = "reference"
)
```

`TaskSpec` gains an `Artifacts` field:

```go
type TaskSpec struct {
    // ... existing fields ...

    // Artifacts declares the artifact inputs and outputs of this Task.
    // +optional
    Artifacts *ArtifactDeclarations `json:"artifacts,omitempty"`
}
```

### StepAction Artifacts

Steps are increasingly written as
[StepActions](https://tekton.dev/docs/pipelines/stepactions/) rather than
inline scripts. A StepAction that builds and pushes an image should be able
to describe that it produces an image reference, in the same way it already
describes its `params` and `results`. Without this, only Tasks with inline
`script:` steps could use the Artifacts API, and reusable Steps would stay
on the `IMAGE_URL`/`IMAGE_DIGEST` type-hinting convention this TEP sets out
to replace.

Artifact outputs therefore follow the model already established by
`results`: the StepAction declares them and writes to a **step-scoped**
path, and the Task **explicitly surfaces** the ones that form its contract.

#### StepAction declares its outputs

```yaml
apiVersion: tekton.dev/v1beta1
kind: StepAction
metadata:
  name: buildah
spec:
  params:
    - name: IMAGE
    - name: source-dir
      default: /workspace/source
  artifacts:
    outputs:
      - name: image
        type: reference
        description: The image built and pushed by this StepAction.
  script: |
    cd $(params.source-dir)
    buildah bud -t $(params.IMAGE) .
    buildah push $(params.IMAGE)
    echo "$(params.IMAGE)@$(buildah inspect --format '{{.FromImageDigest}}' $(params.IMAGE))" \
      > $(step.artifacts.outputs.image.uri)
```

`StepActionSpec` and `Step` both gain an `Artifacts` field carrying outputs
only:

```go
// StepArtifacts declares the artifacts a Step or StepAction produces.
type StepArtifacts struct {
    // Outputs declares artifacts produced by this Step or StepAction.
    // +listType=atomic
    Outputs []ArtifactDeclaration `json:"outputs,omitempty"`
}
```

`Step.artifacts` mirrors the existing `Step.results`, so an inline step can
declare step-scoped artifacts without referencing a StepAction.

#### Task surfaces them explicitly

```yaml
kind: Task
spec:
  artifacts:
    outputs:
      - name: image
        subject: true
        value: $(steps.build.artifacts.image)
  steps:
    - name: build
      ref:
        name: buildah
      params:
        - name: IMAGE
          value: registry.example.com/myapp:latest
```

As with results, surfacing is **explicit** — Tekton does not infer a Task's
artifacts from the StepActions it references. This keeps the Task's declared
contract readable on its own, and matches the existing behaviour for
`results`, where a Task must declare `results` and wire them from
`$(steps.<step>.results.<name>)`.

#### Where each field is declared

| Field | Declared on | Rationale |
|-------|-------------|-----------|
| `type` (`reference`/`content`) | StepAction | Intrinsic to what the Step does. `buildah` always pushes, so its output is always a `reference`; a Task cannot change that. |
| `mediaType` | StepAction, Task may override | Usually intrinsic, occasionally specialised by the Task. |
| `subject` | Task | A policy decision, not a property of the Step. A Task that builds a throwaway image with `buildah` must be able to declare it is *not* an attestation subject. |
| `description` | Either | Documentation at the level it applies to. |

A Task artifact declared **with** `value:` inherits `type` and `mediaType`
from the referenced step artifact, and may set `subject` and `description`.
A Task artifact declared **without** `value:` owns its declaration outright,
and steps write to the Task-scoped `$(outputs.<name>.path)`. Both forms are
supported, exactly as `$(results.<name>.path)` and
`$(step.results.<name>.path)` coexist today.

#### Inputs are passed as params

Artifact *inputs* are not declared on StepActions. A Task's content inputs
are fetched once by an init container before any Step runs (see [Transparent
Content Fetch and
Verification](#transparent-content-fetch-and-verification)), and a Step
consumes them by receiving the path as an ordinary param:

```yaml
steps:
  - name: build
    ref:
      name: buildah
    params:
      - name: source-dir
        value: $(inputs.source.path)
```

This mirrors how StepActions already receive workspace paths, since a
StepAction cannot resolve `$(workspaces.*)` either.

The asymmetry between inputs and outputs is deliberate, and follows the
actors involved:

- **Outputs need step scope** — the entrypoint is a per-Step actor and must
  know which artifacts to digest and upload for the Step it wraps.
- **Inputs do not** — the fetching init container is a per-Task actor, and
  per-Step input provenance is a [non-goal](#non-goals).

A step-level input declaration would therefore carry no provenance or
verification semantics beyond what the Task-level declaration already
provides. It is omitted rather than added as documentation-only API.

### Extending ArtifactValue for Status

The existing `ArtifactValue` type (used in TaskRun status) gains three
optional fields:

- **`ref`** — a backend-specific storage reference (backend name, location,
  digest, content type). Present only for content artifacts stored
  externally. Absent for reference artifacts and inline content.
- **`size`** — content size in bytes, letting consumers and UIs know the
  artifact size before fetching.
- **`inline`** — small content embedded directly in the status, avoiding
  external storage overhead. The entrypoint decides based on a configurable
  size threshold (default 1KB); see [Inline threshold
  bounds](#inline-threshold-bounds) for why that default is small and what
  caps it.

Users never write these fields — Tekton populates them automatically in
TaskRun status based on the artifact type and storage configuration.

#### Inline threshold bounds

Inline content travels to the controller in the step's **termination
message**, which is subject to the Kubernetes limits this TEP already cites
as a motivation: **4KB per container and 12KB per Pod**. The inline
threshold is therefore an optimisation bounded by a hard platform limit, not
a freely tunable size:

- The configured threshold is validated against a **2KB ceiling**, leaving
  headroom in the per-container budget for results and artifact metadata.
  A larger value is rejected when the ConfigMap is loaded.
- The 12KB per-Pod budget binds independently: several steps each emitting
  inline content can exhaust it even when no single step exceeds 2KB. The
  entrypoint tracks the remaining budget and **falls back to backend
  upload** when adding inline content would exceed it.
- Falling back is always safe, because inlining is a latency optimisation
  rather than part of the artifact's contract. Consumers read
  `$(inputs.<name>.path)` identically in both cases.

If content storage is disabled and an artifact exceeds the inline budget,
there is nowhere to fall back to; the step fails with an error naming the
artifact and its size.

### Variable Substitution

**Output variables (available in Steps):**

| Variable                 | Available for     | Resolves to                                                     |
|--------------------------|-------------------|-----------------------------------------------------------------|
| `$(outputs.<name>.path)` | `type: content`   | `/tekton/artifacts/outputs/<name>/`                             |
| `$(outputs.<name>.uri)`  | `type: reference` | `/tekton/artifacts/outputs/<name>.uri` (file to write URI into) |

For reference artifacts, the step writes the URI (including digest) to
`$(outputs.<name>.uri)`. The entrypoint parses it and populates the
`ArtifactValue` in the termination message.

For content artifacts, the step writes file(s) to `$(outputs.<name>.path)`.
The entrypoint uploads the content to the storage backend, computes the
digest, and populates the `ArtifactValue`.

**Step-scoped output variables (available inside a `StepAction` or a `Step`
that declares `artifacts.outputs`):**

| Variable                                | Available for     | Resolves to                                      |
|-----------------------------------------|-------------------|--------------------------------------------------|
| `$(step.artifacts.outputs.<name>.path)` | `type: content`   | `/tekton/artifacts/steps/<step>/outputs/<name>/` |
| `$(step.artifacts.outputs.<name>.uri)`  | `type: reference` | file to write the URI (including digest) into    |

These are the only artifact variables a referenced `StepAction` can use.
`$(outputs.*)` and `$(inputs.*)` are Task-scoped and do not resolve inside a
`StepAction`, just as `$(workspaces.*)` does not. This mirrors the existing
split between `$(results.<name>.path)` and `$(step.results.<name>.path)`.

**Task-level surfacing variables:**

| Variable                                  | Resolves to                                     |
|-------------------------------------------|-------------------------------------------------|
| `$(steps.<step>.artifacts.<name>)`        | The whole `ArtifactValue` produced by that Step |
| `$(steps.<step>.artifacts.<name>.uri)`    | URI of that artifact                            |
| `$(steps.<step>.artifacts.<name>.digest)` | Digest of that artifact                         |

Unlike `$(steps.<step>.results.<name>)`, which substitutes a string,
`$(steps.<step>.artifacts.<name>)` is a **structured** reference: it is
resolved by copying the whole `ArtifactValue` (uri, digest, mediaType, ref)
into the Task's artifact output, not by text substitution. The `.uri` and
`.digest` forms do substitute strings, and can be used in later Steps'
params.

**Input variables (available in Steps):**

| Variable                  | Resolves to                          |
|---------------------------|--------------------------------------|
| `$(inputs.<name>.path)`   | `/tekton/artifacts/inputs/<name>/`   |
| `$(inputs.<name>.uri)`    | URI string from upstream producer    |
| `$(inputs.<name>.digest)` | Digest string from upstream producer |

For content inputs, the init container fetches and verifies content before
steps run. For reference inputs, only URI and digest are available (no
content fetch).

**Pipeline-level variables:**

| Variable                                | Resolves to                           |
|-----------------------------------------|---------------------------------------|
| `$(tasks.<task>.outputs.<name>)`        | Serialized artifact JSON (for params) |
| `$(tasks.<task>.outputs.<name>.uri)`    | URI of the first artifact value       |
| `$(tasks.<task>.outputs.<name>.digest)` | Digest of the first artifact value    |

### Entrypoint Behavior

After a step completes, the entrypoint processes the output artifacts
declared for that step — both the step-scoped ones from its `StepAction` (or
`Step.artifacts`) and any Task-scoped ones written by an inline script.

For `type: content` outputs, it reads the content written to the artifact
path and computes a SHA-256 digest. For `type: reference` outputs, it reads
the URI from the artifact's `.uri` file.

**Reference artifacts MUST carry a digest.** If a step writes a URI with no
digest, the entrypoint fails the step. A Step that has just pushed content
always knows its digest, so this costs nothing — and it guarantees every
reference propagated through a Pipeline is digest-pinned. That guarantee is
what allows Tekton to forward references without re-verifying them, and what
makes `subject: true` meaningful for SLSA attestation: an attestation
subject without a digest asserts nothing.

**Only artifacts surfaced by the Task are uploaded.** Content is expensive to
store, and a step artifact that no Task output binds cannot be consumed
downstream:

| Type | Surfaced by the Task | Not surfaced |
|------|----------------------|--------------|
| `content` | digest computed **and content uploaded** to the storage backend (or inlined if below the threshold) | digest, size and `mediaType` recorded in TaskRun status; **no upload** |
| `reference` | `uri` and `digest` recorded | `uri` and `digest` recorded (identical — there is nothing to transport) |

The entrypoint must read the content to compute its digest in any case, so
recording provenance for unsurfaced artifacts is nearly free while skipping
the upload avoids spending bandwidth and storage on content nobody consumes.
Unsurfaced artifacts degrade to provenance-only records — precisely what
TEP-0147 Phase 1 provides today, so nothing is lost. This also lets a
StepAction declare artifacts before any Task surfaces them.

In all cases the artifact metadata (URI, digest, storage reference) is
included in the termination message for the controller to record in TaskRun
status.

If a declared output artifact has no content written, the entrypoint emits
a warning — the artifact is omitted from status, not a failure.

### TaskRun Status

TaskRun status includes artifact values with storage references:

```yaml
apiVersion: tekton.dev/v1
kind: TaskRun
metadata:
  name: build-run-abc123
status:
  conditions:
    - type: Succeeded
      status: "True"
  artifacts:
    outputs:
      - name: image
        subject: true
        values:
          - uri: "registry.example.com/myapp@sha256:abc123..."
            digest:
              sha256: "abc123..."
      - name: test-results
        values:
          - uri: "pkg:generic/test-results"
            digest:
              sha256: "def456..."
            ref:
              backend: oci
              location: "registry.example.com/tekton/artifacts:default-build-run-abc123-test-results"
              digest: "sha256:def456..."
              contentType: "application/xml"
            size: 45678
      - name: build-log
        values:
          - digest:
              sha256: "789abc..."
            inline: "Tests passed: 42/42"
```

Note:
- `image` (reference): only `uri` + `digest`, no `ref` (Tekton didn't
  store it)
- `test-results` (content, large): has `ref` pointing to storage backend
- `build-log` (content, small): has `inline` with embedded content

### Pipeline-Level Artifact Bindings

Pipelines connect Tasks through artifact bindings on `PipelineTask`:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-sign-attest
spec:
  tasks:
    - name: clone
      taskRef:
        name: git-clone
      params:
        - name: url
          value: "https://github.com/example/app"

    - name: build
      taskRef:
        name: build-images
      artifacts:
        inputs:
          - name: source
            from: tasks.clone.outputs.source

    - name: sign
      taskRef:
        name: sign-images
      artifacts:
        inputs:
          - name: image-ref
            from: tasks.build.outputs.image
      # runAfter is implicit — artifact dependency creates DAG edge

    - name: report
      taskRef:
        name: report-results
      artifacts:
        inputs:
          - name: results
            from: tasks.build.outputs.test-results
```

When an artifact binding is declared:

1. The PipelineRun controller creates an implicit `runAfter` DAG edge
   between producer and consumer.
2. For content artifacts: the controller passes the `StorageRef` to the
   consumer TaskRun, which injects an init container to fetch+verify.
3. For reference artifacts: the controller passes `Uri` + `Digest` to the
   consumer TaskRun, available via `$(inputs.<name>.uri)` and
   `$(inputs.<name>.digest)`.

### Pipeline-Level Artifact Declarations

Pipelines can declare their own artifact inputs and outputs, surfacing
Task-level artifacts at the Pipeline boundary:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-and-sign
spec:
  artifacts:
    inputs:
      - name: source
        description: Source code
    outputs:
      - name: image
        from: tasks.build.outputs.image
      - name: signatures
        from: tasks.sign.outputs.signatures
  tasks:
    - name: build
      taskRef:
        name: build-images
      artifacts:
        inputs:
          - name: source
            from: artifacts.inputs.source
    - name: sign
      taskRef:
        name: sign-images
      artifacts:
        inputs:
          - name: image-ref
            from: tasks.build.outputs.image
```

Pipeline-level outputs carry the same `ArtifactValue` references from
the producing Tasks (no re-upload). The PipelineRun status includes the
full artifact provenance chain.

### PipelineRun Artifact Inputs

PipelineRuns can provide artifact inputs when triggering a run:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: my-build-run
spec:
  pipelineRef:
    name: build-and-sign
  artifacts:
    inputs:
      - name: source
        values:
          - uri: "pkg:generic/source@abc123"
            digest:
              sha256: "abc123..."
            ref:
              backend: oci
              location: "registry.example.com/sources:abc123"
              digest: "sha256:abc123..."
```

### Transparent Content Fetch and Verification

When a Task has content artifact inputs (from Pipeline bindings or
PipelineRun inputs), the controller transparently fetches and verifies
the content before any user Steps execute. The fetch image is built and
released as part of tektoncd/pipeline, following the same pattern as the
entrypoint, nop, and workingdirinit images.

The fetch process:
- Retrieves content from the storage backend using the storage reference.
- Verifies the content digest matches — if verification fails, the
  TaskRun fails with a clear error.
- Makes content available at `$(inputs.<name>.path)` before Steps run.

Verification is **digest-only**: it establishes that the fetched bytes are
the bytes the producing TaskRun recorded. Signature and policy verification
are a [non-goal](#non-goals).

**Reference inputs are not verified.** There is no content to hash, and a
registry round-trip would prove only that the manifest still resolves, while
requiring registry credentials in the init container and introducing a
transient failure mode. Because every reference artifact is required to
carry a digest (see [Entrypoint Behavior](#entrypoint-behavior)), a consumer
that pulls the reference verifies it at the point of use — which is where
the integrity guarantee actually matters.

Key difference from TEP-0139: this uses init containers rather than
injected Steps, so the fetch/verify operations don't appear in the Step
list and don't consume Step-level resources.

### Storage Backend

Content artifacts require a storage backend for upload and download.
Backends implement a `Provider` contract:

```go
type Provider interface {
    Name() string
    Store(ctx context.Context, opts StoreOptions, content io.Reader) (*StorageRef, error)
    Fetch(ctx context.Context, ref *StorageRef) (io.ReadCloser, error)
    Delete(ctx context.Context, ref *StorageRef) error
    Exists(ctx context.Context, ref *StorageRef) (bool, error)
}

// ContentAddressedProvider is optional. Providers whose transport is
// inherently content-addressed implement it to skip redundant hashing.
type ContentAddressedProvider interface {
    Provider
    ContentAddressed() bool
}
```

**Verification is performed by Tekton, not by the provider.** Core wraps
every fetch in a digest-verifying read by default, so that a backend author
cannot accidentally omit a security-critical check. A provider whose
transport already guarantees integrity — such as the digest-pinned OCI pulls
of [TEP-0193](0193-tekton-artifacts-oci-storage.md) — may implement the
optional `ContentAddressedProvider` interface to avoid hashing content
twice. Defining that optional interface now means the capability can be
adopted later without a breaking change to `Provider`.

The first and default backend is the OCI registry, defined in
[TEP-0193](0193-tekton-artifacts-oci-storage.md). Additional backends
(S3, GCS, PVC) can be added later without API changes.

Storage is configured via a `config-artifact-storage` ConfigMap in the
`tekton-pipelines` namespace, with per-namespace overrides following
[TEP-0085](0085-per-namespace-controller-configuration.md). Key
backend-agnostic settings include whether content storage is enabled
(default: disabled) and the inline threshold below which small artifacts
are embedded directly in TaskRun status (default: 1KB, ceiling 2KB — see
[Inline threshold bounds](#inline-threshold-bounds)). Backend-specific
configuration (repository, credentials) is defined per backend TEP.

### Integration with Tekton Chains

**`subject: true` replaces type hinting:**

Today, Chains identifies SLSA subjects by scanning for result names matching
`IMAGE_URL` and `IMAGE_DIGEST`. This is fragile.

With this TEP, artifacts with `subject: true` are explicitly marked. Chains
reads the artifact declarations from TaskRun status:

```yaml
# TaskRun status
artifacts:
  outputs:
    - name: image
      subject: true    # ← Chains uses this
      values:
        - uri: "registry.example.com/myapp@sha256:abc123"
          digest:
            sha256: "abc123..."
```

Chains maps `subject: true` artifacts to SLSA `subject[]` and others to
`byProducts[]`.

**Reference-based attestations:**

For content artifacts with `StorageRef`, Chains records only the reference
(URI + digest) in the attestation, not the full content:

```json
{
  "subject": [{
    "name": "registry.example.com/myapp@sha256:abc123",
    "digest": {"sha256": "abc123..."}
  }],
  "predicate": {
    "buildType": "tekton.dev/v1",
    "byProducts": [{
      "name": "test-results",
      "digest": {"sha256": "def456..."},
      "annotations": {
        "tekton.dev/storage-ref": "oci://registry.example.com/tekton/artifacts:tag"
      }
    }]
  }
}
```

This keeps attestations small. Anyone with the digest can independently
fetch and verify content from the storage backend.

### Integration with Tekton Results and UIs

**Tekton Results:**
- Stores `ArtifactValue` (including `StorageRef`) as metadata.
- Enables querying by artifact digest for cross-pipeline correlation.

**UIs (Dashboard, third-party):**
- Display artifact metadata (URI, digest, size) from TaskRun status.
- For content viewing: resolve `StorageRef` and fetch on demand.
- `Inline` artifacts display directly without fetching.
- `Size` field enables showing content size without fetching.

## Design Evaluation

### Reusability

Extends TEP-0147's existing types rather than creating a parallel system.
The `Provider` interface can be reused by Chains and Results. Pipeline
binding syntax follows existing Tekton patterns.

Declaring artifact outputs on `StepAction` makes reusable Steps
self-describing: a catalog `buildah` StepAction states that it produces an
image reference, instead of relying on the `IMAGE_URL`/`IMAGE_DIGEST` result
naming convention that consumers must know out of band. Because surfacing is
explicit, the same StepAction can be used by a Task that declares its output
an attestation subject and by one that does not.

### Simplicity

**For Task authors**: declare artifacts, write to paths or URIs. No JSON
schemas, no manual provenance files.

**For Pipeline authors**: `from: tasks.x.outputs.y` — same pattern as
params, just for artifacts.

**For operators**: one ConfigMap to enable and configure storage.

### Flexibility

- Two artifact types cover all use cases (reference and content).
- Pluggable backends via `Provider` interface.
- Inline threshold is configurable.
- Per-namespace configuration via TEP-0085.

### Conformance

- Feature-flag gated for gradual adoption.
- `spec.results` continues to work unchanged.
- Variable substitution follows existing Tekton patterns.

### User Experience

**Before (TEP-0147 Phase 1):**
```yaml
steps:
  - script: |
      cat > $(step.artifacts.path) << EOF
      {"outputs":[{"name":"image","values":[{"uri":"...","digest":{"sha256":"..."}}]}]}
      EOF
```

**After (this TEP):**
```yaml
artifacts:
  outputs:
    - name: image
      type: reference
      subject: true
steps:
  - script: |
      echo "registry.example.com/myapp@sha256:abc..." > $(outputs.image.uri)
```

Simpler, validated, integrated.

### Performance

**Positive:**
- No sidecar overhead (unlike TEP-0127).
- Large artifacts don't bloat etcd/API server.
- Content-addressable storage enables caching.

**Trade-offs:**
- Network latency for content artifact fetch (init container).
- Init container startup (~1–2s).

**Mitigations:**
- Parallel fetch for multiple artifacts in a single init container.
- Inline mode for small artifacts avoids any latency.
- Backend-level caching (OCI layer cache, S3 cache).

### Risks and Mitigations

| Risk                                    | Mitigation                                                         |
|-----------------------------------------|--------------------------------------------------------------------|
| Storage backend unavailable             | Clear error; retry with backoff; inline fallback for small content |
| Credential complexity                   | Reuse existing imagePullSecrets; workload identity support         |
| Orphaned artifacts                      | Backend lifecycle policies (MVP); finalizer cleanup (future)       |
| Breaking TEP-0147 Phase 1 users         | Alpha feature, flag-gated; migration path documented               |
| Reference artifact URI format ambiguity | Validate and document expected formats                             |

### Drawbacks

1. **Infrastructure requirement**: Content artifacts need a storage backend.
   Mitigated by PVC backend (no external infra) and inline mode.

2. **Two writing mechanisms**: `$(outputs.name.path)` vs
   `$(outputs.name.uri)` depending on type. Mitigated by clear type
   declaration and validation errors if misused.

3. **Breaking alpha API**: TEP-0147 Phase 1 users must migrate. Mitigated
   by the feature being alpha with few known users.

## Alternatives

### Keep the TEP-0147 Phase 1 Provenance JSON API

**Approach**: Keep `$(step.artifacts.path)` alongside the new API.

**Why not**: Two APIs for the same thing increases confusion. The JSON API
is error-prone, has no validation, and the feature is alpha — the right
time to fix API mistakes. Coexistence means maintaining two code paths
indefinitely.

### TEP-0139 Injected Trusted Steps with PVC

**Approach**: Inject 4 Steps (digest, upload, download, verify) into Pods,
using a shared PVC.

**Why not as-is**:
- 4 injected Steps per Task = visible overhead and Step count inflation.
- PVC-only storage limits to node disk / PVC capacity.
- PVC requires ReadWriteMany for parallel Tasks.
- No cross-cluster artifact sharing.
- Tarball format is opaque.

We adopt TEP-0139's declarative API design but use entrypoint + init
container instead of injected Steps, and pluggable backends instead of
PVC-only.

### TEP-0127 Sidecar Logs

**Approach**: Sidecar container monitors result files, emits via stdout.

**Why not**:
- Sidecar on every TaskRun (resource overhead, ~3s startup).
- Results still end up in TaskRun status (~1.5MB CRD limit).
- No artifact provenance integration.

### Workspaces Only

**Approach**: Use Workspaces for all inter-task data.

**Why not**:
- No provenance or trust chain.
- Requires ReadWriteMany PVCs for parallel Tasks.
- No size tracking or digest verification.
- Race conditions when multiple PipelineRuns share an RWX workspace.
- PVC lifecycle management (provisioning, sizing, cleanup, affinity).
- Data flow is implicit (filesystem paths) rather than explicit (declared
  artifacts with names and types).
- Analysis of real-world Tekton deployments shows most PVC workspaces
  exist solely to pass data between Tasks — a pattern content artifacts
  handle better.

## Implementation Plan

### Phase 1 (Alpha)

1. Add `ArtifactDeclarations` to `TaskSpec` (partially landed: `c16050c1a0ab`).
2. Implement variable substitution for `$(outputs.<name>.path)`,
   `$(outputs.<name>.uri)`, `$(inputs.<name>.path)`.
3. Modify entrypoint for content artifact upload and reference artifact
   recording.
4. Implement init container injection for content artifact fetch+verify.
5. Implement `PipelineTask` artifact binding with implicit DAG edges
   (partially landed: `5f9fe0ecdf02`).
6. Implement `Provider` interface.
7. Integrate first backend (OCI, per TEP-0193).
8. Deprecate and remove `$(step.artifacts.path)` / `$(artifacts.path)`.
9. Update examples and documentation.
10. E2E tests.

### Phase 2 (Beta)

1. Pipeline-level artifact declarations.
2. PipelineRun artifact inputs.
3. Chains integration (`subject: true` → SLSA subject).
4. Additional backends.
5. Inline storage mode.

### Phase 3 (Stable)

1. Metrics and observability.
2. Results integration.
3. Promote to stable.

### Test Plan

- Unit tests: `ArtifactDeclaration` validation, variable substitution,
  entrypoint artifact handling, init container injection logic.
- Integration tests: artifact binding between Tasks, reference vs content
  type handling, inline threshold behavior.
- E2E tests: full Pipeline with content and reference artifacts, storage
  backend integration, digest verification.
- Backward compatibility: ensure `spec.results` continues working.
- Migration: verify removal of `$(step.artifacts.path)`.
- Performance benchmarks, comparing content artifacts against the shared
  PVC workspace pattern they are intended to replace:
  - End-to-end wall time for `clone → build` via a shared PVC workspace
    versus via a content artifact, at several source sizes.
  - Init container fetch overhead, to substantiate the ~1–2s figure quoted
    in [Performance](#performance), against the pod scheduling delay the
    affinity assistant introduces when a PVC is shared.
  - Upload cost in the entrypoint as a function of artifact size.
  - Inline mode versus backend upload for small artifacts.

### Upgrade and Migration Strategy

- Feature is opt-in via `enable-artifacts` feature flag (already exists).
- `spec.results` continues to work unchanged.
- TEP-0147 Phase 1 users migrate from `$(step.artifacts.path)` JSON to
  `spec.artifacts` declarations. Since the feature is alpha with few known
  users, this is acceptable.
- Gradual rollout: enable artifact storage per-namespace via TEP-0085
  before cluster-wide.

**Migrating an existing Task away from PVC workspaces**

Widely used Tasks such as `git-clone` write into a workspace today. Because
a `StepAction` receives filesystem paths as ordinary params (see [Inputs are
passed as params](#inputs-are-passed-as-params)), the same StepAction serves
both models unchanged — only the Task wrapper differs:

```yaml
# Workspace-based Task (today)
steps:
  - name: clone
    ref:
      name: git-clone
    params:
      - name: output-path
        value: $(workspaces.output.path)
```

```yaml
# Artifact-based Task (this TEP)
artifacts:
  outputs:
    - name: source
      type: content
steps:
  - name: clone
    ref:
      name: git-clone
    params:
      - name: output-path
        value: $(outputs.source.path)
```

So migration does not require forking or re-versioning the reusable unit,
and does not require a Task that supports both models through conditional
logic. Publishing an artifact-based Task variant alongside the existing
workspace-based one lets Pipelines migrate one Task at a time, and both
variants stay in sync because the StepAction they share carries the actual
behaviour.

## References

- [TEP-0147: Tekton Artifacts Phase 1](0147-tekton-artifacts-phase1.md)
- [TEP-0139: Trusted Artifacts](0139-trusted-artifacts.md)
- [TEP-0193: Tekton Artifacts OCI Storage](0193-tekton-artifacts-oci-storage.md)
- [TEP-0085: Per-Namespace Controller Configuration](0085-per-namespace-controller-configuration.md)
- [TEP-0127: Larger Results via Sidecar Logs](0127-larger-results-via-sidecar-logs.md)
- [API Compatibility Policy](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md)
- [Issue #4012: Changing the way Result Parameters are stored](https://github.com/tektoncd/pipeline/issues/4012)
- [Issue #4808: Results, TerminationMessage and Containers](https://github.com/tektoncd/pipeline/issues/4808)
- [Issue #6326: Artifact provenance feature request](https://github.com/tektoncd/pipeline/issues/6326)
- [Issue #8448: Enable larger results without a sidecar on every TaskRun](https://github.com/tektoncd/pipeline/issues/8448)
- [Konflux CI Trusted Artifacts (ADR-0036)](https://github.com/konflux-ci/architecture/blob/main/ADR/0036-trusted-artifacts.md)
- [SLSA Provenance Specification](https://slsa.dev/provenance)
- [Proof of Concept: `vdemeester/tekton-experiments`](https://github.com/vdemeester/tekton-experiments)
