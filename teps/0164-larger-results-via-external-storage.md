---
title: "Tekton Artifacts Phase 2: External Storage for Artifacts and Results"
authors:
  - "@vdemeester"
creation-date: 2026-02-04
last-updated: 2026-02-13
status: proposed
supersedes:
see-also:
  - TEP-0085
  - TEP-0086
  - TEP-0127
  - TEP-0139
  - TEP-0147
---

# TEP-0164: Tekton Artifacts Phase 2 — External Storage for Artifacts and Results

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Relationship to TEP-0147 and TEP-0139](#relationship-to-tep-0147-and-tep-0139)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [Extending ArtifactValue with Storage References](#extending-artifactvalue-with-storage-references)
  - [Artifact Declaration in Task Spec](#artifact-declaration-in-task-spec)
  - [Storage Modes](#storage-modes)
  - [Storage Backend Configuration](#storage-backend-configuration)
  - [Namespace-Level and Per-PipelineRun Configuration](#namespace-level-and-per-pipelinerun-configuration)
  - [TaskRun Status with Storage References](#taskrun-status-with-storage-references)
  - [Transparent Resolution for Downstream Tasks](#transparent-resolution-for-downstream-tasks)
  - [Init Container Injection for External Artifacts](#init-container-injection-for-external-artifacts)
  - [Pipeline-Level Artifact Declarations](#pipeline-level-artifact-declarations)
  - [OCI Artifact Grouping per PipelineRun](#oci-artifact-grouping-per-pipelinerun)
  - [Integration with Tekton Chains](#integration-with-tekton-chains)
  - [Integration with Tekton Results and UIs](#integration-with-tekton-results-and-uis)
  - [Storage Provider Interface](#storage-provider-interface)
  - [Supported Backends](#supported-backends)
  - [Garbage Collection](#garbage-collection)
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
  - [TEP-0127: Sidecar Logs](#tep-0127-sidecar-logs)
  - [TEP-0139: Injected Trusted Steps with PVC](#tep-0139-injected-trusted-steps-with-pvc)
  - [Standalone External Results (Original TEP-0164)](#standalone-external-results-original-tep-0164)
  - [ConfigMaps per TaskRun](#configmaps-per-taskrun)
  - [Workspaces Only](#workspaces-only)
- [Future Work: Convergence of Results, Params, and Artifacts](#future-work-convergence-of-results-params-and-artifacts)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP extends [TEP-0147 (Tekton Artifacts Phase
1)](https://github.com/tektoncd/community/blob/main/teps/0147-tekton-artifacts-phase1.md)
with external storage backends, unifying two related problems:

1. **Larger Results**: Overcoming the 4KB/12KB termination message limits and
   ~1.5MB CRD size constraints that prevent Tasks from producing results of
   meaningful size.

2. **Trusted Artifacts**: Establishing a chain of trust for data shared between
   Tasks, as proposed in [TEP-0139](https://github.com/tektoncd/community/blob/main/teps/0139-trusted-artifacts.md),
   by combining verified storage with artifact provenance metadata.

TEP-0147 Phase 1 (implemented, alpha) provides the artifact provenance
structure — `ArtifactValue` with `Uri` and `Digest` fields — and the
`$(step.artifacts.path)` API for reporting artifact metadata. However, it has
**no storage backend**: artifacts are referenced but not managed by Tekton.

This TEP adds the missing storage layer and the declarative Artifact API
proposed in TEP-0139. By extending `ArtifactValue` with a `StorageRef` and
introducing `spec.artifacts.inputs/outputs` on Tasks, we enable Tekton to
upload, download, verify, and manage artifact content through pluggable
backends (OCI registry, S3, GCS, PVC). This solves the results size problem,
the trusted artifacts problem, and the artifact declaration problem with a
single, unified design.

## Motivation

### Current Limitations

Tekton Results are severely constrained by Kubernetes limitations:

1. **Termination Message Limit**: Results stored via container termination
   messages are limited to 4KB per container and 12KB total per Pod.

2. **Container Count Impact**: More Steps in a Task means less space per
   result. With 12 containers, each gets only ~1KB.

3. **CRD Size Limit**: Even with TEP-0127's sidecar logs, results end up in
   TaskRun status, subject to the ~1.5MB CRD size limit.

4. **No Storage for Artifacts**: TEP-0147 provides provenance metadata
   (`Uri` + `Digest`) but no mechanism to actually store or retrieve artifact
   content. Steps must handle their own upload/download.

5. **No Trust Chain**: Without Tekton-managed storage, there is no built-in
   verification that artifacts passed between Tasks have not been tampered
   with (the problem TEP-0139 identifies).

### Convergence Opportunity

Three related TEPs address overlapping concerns:

| TEP | Focus | Status | Has Provenance | Has Storage |
|-----|-------|--------|----------------|-------------|
| [TEP-0147](https://github.com/tektoncd/community/blob/main/teps/0147-tekton-artifacts-phase1.md) | Artifact provenance metadata | Implemented (alpha) | ✅ Uri + Digest | ❌ |
| [TEP-0139](https://github.com/tektoncd/community/blob/main/teps/0139-trusted-artifacts.md) | Trusted artifact sharing | Proposed | ✅ (references 0147) | ✅ (conceptual) |
| TEP-0164 (this) | External storage + Artifact API | Proposed | ✅ (extends 0147) | ✅ (concrete) |

Rather than three separate systems, this TEP unifies them: **TEP-0147's
provenance structure + TEP-0139's Artifact API + external storage backends =
trusted artifacts with arbitrary size support and a declarative API**.

### Goals

1. **Extend TEP-0147** with pluggable storage backends for artifact content.
2. **Implement TEP-0139's Artifact API** — declarative `spec.artifacts.inputs`
   and `spec.artifacts.outputs` on Tasks, with Pipeline-level artifact binding.
3. Enable Tasks to produce and consume **artifacts of arbitrary size**.
4. Provide a **chain of trust** for artifacts shared between Tasks via
   digest verification on upload and download.
5. Maintain **backward compatibility** with existing inline results and
   TEP-0147 Phase 1 artifact reporting.
6. Support **transparent resolution** so downstream Tasks consume artifacts
   without special handling.
7. Align with **production patterns** from Konflux CI's OCI-based trusted
   artifacts.

### Non-Goals

1. Replacing Tekton Results project — this TEP focuses on inter-task artifact
   passing, not long-term storage and querying.
2. Automatic artifact streaming or real-time access during Task execution.
3. Solving the termination message limit for inline results (that remains
   at 4KB).
4. Auto-provisioning of artifact storage (e.g., automatic PVC creation) — operators
   configure storage backends explicitly.

### Use Cases

**Use Case 1: Multi-Image Build Pipeline (Konflux)**

A Task builds multiple container images and needs to pass the list of all
image references (with digests) to a signing Task. With 20+ images, the
artifact data easily exceeds 4KB.

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-images
spec:
  artifacts:
    outputs:
      - name: images
        description: Built image references with digests
        buildOutput: true
        storage: external
  steps:
    - name: build
      image: builder:latest
      script: |
        # Build images, write output to artifact path
        # Tekton handles upload, digest, and provenance automatically
        cat images.json > $(outputs.images.path)
```

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: sign-images
spec:
  artifacts:
    inputs:
      - name: images
        description: Image references to sign
  steps:
    - name: sign
      image: cosign:latest
      script: |
        # Content is fetched and verified by init container before this runs
        cat $(inputs.images.path) | jq -r '.[].uri' | while read ref; do
          cosign sign "$ref"
        done
```

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-and-sign
spec:
  tasks:
    - name: build
      taskRef:
        name: build-images
    - name: sign
      taskRef:
        name: sign-images
      artifacts:
        inputs:
          - name: images
            from: tasks.build.outputs.images
```

**Use Case 2: SBOM Generation with Signing**

An SBOM is a large document (10KB-10MB) that should be **stored externally
and referenced**, not passed inline as text. A downstream Task can then sign
or attest the SBOM using its digest — without Tekton duplicating the entire
document in the attestation.

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
        description: SPDX SBOM document
        storage: external
  steps:
    - name: generate
      image: syft:latest
      script: |
        syft scan $(params.image) -o spdx-json > $(outputs.sbom.path)
        # Tekton computes digest and uploads automatically
```

The signing Task receives the SBOM reference (URI + digest) via the artifact
binding and can verify integrity before signing. Chains records only the
digest in the attestation, not the full SBOM content.

**Use Case 3: ML Model Passing (Kubeflow Pipelines)**

Kubeflow Pipelines on Tekton (kfp-tekton) needs to pass large ML artifacts
(datasets, models, metrics) between pipeline steps. Currently constrained
by the 4KB result limit, requiring workarounds with Workspaces and PVCs.

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: train-model
spec:
  artifacts:
    inputs:
      - name: dataset
        description: Training dataset
    outputs:
      - name: model
        description: Trained model weights
        storage: external
      - name: metrics
        description: Training metrics (small)
        storage: inline
  steps:
    - name: train
      image: tensorflow:latest
      script: |
        python train.py \
          --data $(inputs.dataset.path) \
          --output $(outputs.model.path)
        # Write small metrics inline
        echo '{"accuracy": 0.95, "loss": 0.05}' > $(outputs.metrics.path)
```

**Use Case 4: Test Results Processing**

A test Task produces detailed JUnit XML output (potentially large) that
needs to be processed by a reporting Task.

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: run-tests
spec:
  artifacts:
    outputs:
      - name: test-results
        description: JUnit XML test results
        storage: external
  steps:
    - name: test
      image: maven:latest
      script: |
        mvn test
        cp target/surefire-reports/*.xml $(outputs.test-results.path)/
```

### Requirements

**Must Have:**

1. **Backward Compatibility**: Existing Tasks, Pipelines, and TEP-0147
   Phase 1 artifact reporting must continue to work unchanged.
2. **Extends TEP-0147**: Builds on the existing `ArtifactValue` structure
   rather than introducing a parallel system.
3. **Declarative Artifact API**: Tasks declare `spec.artifacts.inputs` and
   `spec.artifacts.outputs` with `$(inputs.name.path)` / `$(outputs.name.path)`
   variables (adopting TEP-0139's design).
4. **Pluggable Backends**: Operators configure their preferred storage
   (OCI registry, S3, GCS, PVC).
5. **Digest Verification**: Content integrity verified on both upload and
   download (chain of trust).
6. **Transparent Resolution**: Downstream Tasks consume artifacts via
   declarative bindings or variable substitution.
7. **Reference-Based**: Only references (URI + digest) stored in TaskRun
   status; actual content lives in external storage.

**Nice to Have (can be deferred):**

7. **Garbage Collection**: Automated cleanup of external artifacts.
8. **OCI Artifact Grouping**: Group artifacts per PipelineRun using OCI
   referrers.
9. **Caching**: OCI layer caching for frequently accessed artifacts.

## Proposal

Extend TEP-0147's `ArtifactValue` type with a storage reference and adopt
TEP-0139's declarative Artifact API, enabling Tekton to manage artifact
content in external storage while providing a first-class API for declaring,
producing, and consuming artifacts.

The key insight is that TEP-0147 already provides the right data structure
for artifact provenance (`Uri` + `Digest`), and TEP-0139 already designed
the right user-facing API (`spec.artifacts.inputs/outputs`). What's missing
is:

1. A **storage backend** that Tekton manages (upload/download/verify)
2. A **reference** from `ArtifactValue` to the stored content
3. **Metadata** about the stored content (size, content type)
4. An option for **inline** small content (avoiding external storage overhead
   for small artifacts)
5. A **declarative API** for Tasks to declare input/output artifacts upfront

### Relationship to TEP-0147 and TEP-0139

This TEP is explicitly designed as **TEP-0147 Phase 2** and a concrete
implementation of **TEP-0139's goals**:

| Aspect | TEP-0147 Phase 1 | TEP-0139 (proposed) | This TEP (Phase 2) |
|--------|-------------------|---------------------|---------------------|
| Artifact provenance | ✅ `{Uri, Digest}` | ✅ `{uri, digest}` | ✅ Extended with `{Ref, Size, Inline}` |
| Declarative API | ❌ | ✅ `spec.inputs/outputs` | ✅ `spec.artifacts.inputs/outputs` |
| Step API | ✅ `$(step.artifacts.path)` | ✅ (provenance files) | ✅ Same + `$(outputs.name.path)` |
| Task-level artifacts | ✅ `$(artifacts.path)` | ✅ | ✅ Same API |
| Pipeline binding | ✅ `$(tasks.name.outputs.art)` | ✅ `inputs: [{value: $(tasks...)}]` | ✅ Both syntaxes |
| Storage management | ❌ User-managed | ✅ PVC + injected Steps | ✅ Pluggable backends (OCI/S3/GCS/PVC) |
| Trust mechanism | ❌ | ✅ Injected digest/upload/download/verify Steps | ✅ Entrypoint + init container (transparent) |
| Size limits | ❌ Termination msg | ❌ PVC/node disk | ✅ Unlimited (backend-dependent) |

**What we adopt from TEP-0139:**

1. **Declarative Artifact API** — Tasks declare `spec.artifacts.inputs` and
   `spec.artifacts.outputs` upfront, with `$(inputs.name.path)` and
   `$(outputs.name.path)` variables for Steps to read/write artifact content.
2. **Pipeline-level artifact binding** — Pipelines connect Tasks by piping
   outputs to inputs: `inputs: [{name: bar, from: tasks.producer.outputs.foo}]`.
3. **Chain of trust** — digest verification on both upload and download,
   ensuring artifacts have not been tampered with between Tasks.
4. **Provenance integration** — artifact metadata flows into TaskRun status
   and Tekton Chains attestations.

**Where we differ from TEP-0139:**

1. **No injected Steps** — TEP-0139 injects 4 Steps (digest, upload, download,
   verify) into the Pod. This adds visible overhead and complexity. Instead,
   we handle storage operations transparently in the entrypoint binary (upload)
   and init container (download + verify).
2. **External storage, not just PVC** — TEP-0139 focuses on PVC-based sharing
   with a single Workspace. We support pluggable backends (OCI, S3, GCS, PVC),
   which removes the PVC/node disk size limitation and enables cross-cluster
   artifact sharing.
3. **No Artifact Workspace auto-provisioning** — TEP-0139 proposes automatic
   PVC provisioning for artifact sharing. We require operators to configure
   storage backends explicitly, which is simpler and more predictable.
4. **Content format** — TEP-0139 stores artifacts as tarballs (`<digest>.tgz`)
   on PVC. We store content as-is in external storage (OCI layers, S3 objects),
   which is more natural for each backend.

### Notes and Caveats

- External storage requires additional infrastructure (OCI registry, S3
  bucket, etc.)
- Network latency for fetching artifacts may impact Pipeline execution time
- Storage credentials must be available to TaskRun pods and the controller
- Tasks using external storage will fail on clusters without it configured
- Two artifact authoring APIs coexist:
  - **Declarative** (`spec.artifacts` + `$(outputs.name.path)`): recommended,
    Tekton manages everything
  - **Provenance-only** (`$(step.artifacts.path)` JSON): TEP-0147 Phase 1
    backward compatibility, Steps manage their own storage
- The declarative API mirrors TEP-0139's design but uses different storage
  mechanisms (external backends instead of injected Steps + PVC)

## Design Details

### Extending ArtifactValue with Storage References

The core API change extends TEP-0147's `ArtifactValue` type:

```go
// ArtifactValue represents a specific value or data element within an Artifact.
// Extended from TEP-0147 Phase 1 with storage reference support.
type ArtifactValue struct {
    // Existing TEP-0147 fields
    Digest map[Algorithm]string `json:"digest,omitempty"`
    Uri    string               `json:"uri,omitempty"`

    // NEW: External storage reference
    Ref    *StorageRef          `json:"ref,omitempty"`

    // NEW: Content size in bytes
    Size   int64                `json:"size,omitempty"`

    // NEW: Small content inline (avoids external storage for small artifacts)
    Inline string               `json:"inline,omitempty"`
}

// StorageRef identifies content in an external storage backend.
type StorageRef struct {
    // Backend type: oci, s3, gcs, azure, pvc
    Backend string `json:"backend"`

    // Backend-specific location
    // OCI: "registry.example.com/tekton/artifacts:tag"
    // S3:  "bucket/key"
    // PVC: "pvc-name/path"
    Location string `json:"location"`

    // Content digest for integrity verification (redundant with ArtifactValue.Digest
    // but included for self-contained reference resolution)
    Digest string `json:"digest"`

    // Content type hint (e.g., "application/json", "application/spdx+json")
    ContentType string `json:"contentType,omitempty"`
}
```

**Design rationale:**

- `Ref` is a pointer (optional) — `ArtifactValue` without a `Ref` behaves
  exactly as in TEP-0147 Phase 1.
- `Size` enables consumers to know artifact size before fetching.
- `Inline` allows small content to be embedded directly, avoiding external
  storage overhead. This replaces the need for `type: string` results when
  content is small but should still participate in the artifact provenance
  system.
- The `Digest` in both `ArtifactValue` and `StorageRef` enables verification
  at both the provenance and storage levels.

### Artifact Declaration in Task Spec

This TEP introduces a declarative Artifact API on Tasks, adopting the design
from TEP-0139. Tasks can declare input and output artifacts upfront, similar
to how they declare parameters and results today.

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-images
spec:
  artifacts:
    inputs:
      - name: source
        description: Source code to build
    outputs:
      - name: images
        description: Built container image references
        buildOutput: true    # Chains treats as SLSA subject (not byProduct)
        storage: external    # hint: use external storage
      - name: build-log
        description: Build summary log
        storage: inline      # hint: keep inline (small)
  steps:
    - name: build
      image: builder:latest
      env:
        - name: SOURCE_PATH
          value: $(inputs.source.path)    # resolves to /tekton/artifacts/inputs/source/
      script: |
        # Read input artifacts
        ls ${SOURCE_PATH}

        # Produce output artifacts by writing to the output path
        cat images.json > $(outputs.images.path)
        echo "Build completed: 2 images" > $(outputs.build-log.path)
```

**Variables available to Steps:**

| Variable | Resolves to | Description |
|----------|-------------|-------------|
| `$(inputs.<name>.path)` | `/tekton/artifacts/inputs/<name>/` | Directory for input artifact content |
| `$(inputs.<name>.uri)` | URI string | Artifact URI from upstream producer |
| `$(inputs.<name>.digest)` | Digest string | Artifact digest from upstream producer |
| `$(outputs.<name>.path)` | `/tekton/artifacts/outputs/<name>/` | Directory for output artifact content |

When a Step writes content to `$(outputs.<name>.path)`, the entrypoint
binary handles the rest:
1. Computes the content digest
2. Uploads to external storage (if configured and content exceeds threshold)
3. Generates provenance metadata (`uri`, `digest`) for the TaskRun status

This is a higher-level API than TEP-0147 Phase 1's `$(step.artifacts.path)`
where Steps had to write provenance JSON manually. Both APIs coexist:

- **Declarative API** (`spec.artifacts` + `$(outputs.name.path)`): Tekton
  manages storage, digest, and provenance automatically. Recommended for new
  Tasks.
- **Provenance-only API** (`$(step.artifacts.path)` JSON): Steps handle their
  own storage and write provenance metadata manually. Preserved for backward
  compatibility with TEP-0147 Phase 1 Tasks.

**The `storage` field** is a hint, not a hard requirement. The entrypoint
binary decides based on content size and cluster configuration:

| `storage` hint | Content ≤ threshold | Content > threshold |
|----------------|---------------------|---------------------|
| `inline` | Stored inline | Error (content too large) |
| `external` | Stored externally | Stored externally |
| (not set) | Stored inline | Stored externally if configured, error if not |

**Backward compatibility:** Existing TEP-0147 Phase 1 Tasks (without
`spec.artifacts`) continue to work unchanged. The entrypoint only uses
the new storage path when `spec.artifacts` is declared.

### Storage Modes

Artifacts can be stored in three modes:

1. **Inline**: Content embedded in `ArtifactValue.Inline` field (current
   behavior, small artifacts). Subject to termination message limits.

2. **External**: Content uploaded to configured storage backend. Only
   `StorageRef` stored in TaskRun status.

3. **Reference-only**: No content managed by Tekton — only `Uri` + `Digest`
   recorded (pure TEP-0147 Phase 1 behavior). Used when Steps handle their
   own storage.

The entrypoint determines the mode based on:
1. Task spec `storage` hint (if declared)
2. Content size vs inline threshold (configurable, default 1KB)
3. Whether external storage is configured on the cluster

### Storage Backend Configuration

Cluster-level configuration via ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-artifact-storage
  namespace: tekton-pipelines
data:
  # Enable external artifact storage (default: "false")
  enabled: "true"

  # Default backend type: oci, s3, gcs, azure, pvc
  backend: "oci"

  # Inline threshold: artifacts smaller than this are stored inline
  # regardless of storage hint (default: "1024" bytes)
  inline-threshold: "1024"

  # OCI Registry configuration
  oci.repository: "registry.example.com/tekton/artifacts"
  oci.credentialsSecret: "tekton-artifact-oci-creds"

  # Tag pattern for storing artifacts
  # Available variables: {{namespace}}, {{pipelinerun}}, {{taskrun}}, {{artifact}}
  oci.tagPattern: "{{namespace}}-{{taskrun}}-{{artifact}}"
```

Alternative backend configurations:

```yaml
# S3 configuration
data:
  backend: "s3"
  s3.bucket: "tekton-artifacts"
  s3.region: "us-east-1"
  s3.endpoint: ""                    # optional, for MinIO/S3-compatible
  s3.pathStyle: "false"              # "true" for MinIO
  s3.credentialsSecret: "tekton-artifact-s3-creds"
  # Key pattern
  s3.keyPattern: "{{namespace}}/{{taskrun}}/{{artifact}}"

# GCS configuration
data:
  backend: "gcs"
  gcs.bucket: "tekton-artifacts"
  gcs.credentialsSecret: "tekton-artifact-gcs-creds"

# PVC configuration (no external infrastructure needed)
data:
  backend: "pvc"
  pvc.claimName: "tekton-artifacts"
  pvc.basePath: "/artifacts"
```

### Namespace-Level and Per-PipelineRun Configuration

**Namespace-level** configuration overrides follow [TEP-0085](https://github.com/tektoncd/community/blob/main/teps/0085-per-namespace-controller-configuration.md):

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-artifact-storage
  namespace: team-a
  labels:
    tekton.dev/config-type: artifact-storage
data:
  backend: "oci"
  oci.repository: "team-a-registry.example.com/artifacts"
  oci.credentialsSecret: "team-a-registry-creds"
```

**Per-PipelineRun** configuration via annotations, allowing credentials to be
derived from the ServiceAccount bound to the PipelineRun:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: my-pipeline-run
  annotations:
    tekton.dev/artifact-storage-backend: "oci"
    tekton.dev/artifact-storage-oci-repository: "my-registry.example.com/artifacts"
spec:
  serviceAccountName: my-sa  # SA credentials used for OCI auth
  pipelineRef:
    name: build-and-sign
```

Resolution order:
1. PipelineRun annotations (if set)
2. Namespace-level ConfigMap (if exists)
3. Cluster-level ConfigMap in `tekton-pipelines` namespace
4. Built-in defaults (external storage disabled)

### TaskRun Status with Storage References

When a TaskRun completes with externally stored artifacts, the status
contains extended `ArtifactValue` entries with storage references:

```yaml
apiVersion: tekton.dev/v1
kind: TaskRun
metadata:
  name: build-images-run-abc123
status:
  conditions:
    - type: Succeeded
      status: "True"
  # Existing inline results (unchanged)
  results:
    - name: commit
      type: string
      value: "abc123def"
  # Artifact provenance with storage references
  steps:
    - container: step-build
      outputs:
        - name: images
          buildOutput: true
          values:
            - uri: "pkg:docker/myapp@sha256:abc123"
              digest:
                sha256: "abc123..."
              ref:
                backend: oci
                location: "registry.example.com/tekton/artifacts:default-build-images-run-abc123-images"
                digest: "sha256:abc123..."
                contentType: "application/json"
              size: 45678
            - uri: "pkg:docker/myapp@sha256:def456"
              digest:
                sha256: "def456..."
        - name: build-log
          values:
            - uri: "pkg:generic/build-log"
              digest:
                sha256: "789xyz..."
              inline: "Build completed: 2 images, 0 errors"  # Small, stored inline
```

Note how:
- Artifacts with `ref` have their content in external storage
- Artifacts with `inline` have small content embedded directly
- Artifacts with neither (just `uri` + `digest`) are pure provenance
  references (TEP-0147 Phase 1 behavior)
- The existing `results` field continues to work for traditional inline
  results

### Transparent Resolution for Downstream Tasks

Downstream Tasks consume artifacts through two complementary mechanisms:

**1. Declarative Artifact Binding (recommended)**

When both producer and consumer Tasks declare `spec.artifacts`, the Pipeline
connects them directly through artifact bindings:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-sign-attest
spec:
  tasks:
    - name: build
      taskRef:
        name: build-images

    - name: sign
      taskRef:
        name: sign-images
      artifacts:
        inputs:
          - name: images
            from: tasks.build.outputs.images
      # runAfter is implicit — artifact dependency creates DAG edge

    - name: attest
      taskRef:
        name: create-attestation
      artifacts:
        inputs:
          - name: sbom
            from: tasks.build.outputs.sbom
```

When an artifact binding is declared, the PipelineRun controller:

1. Creates a DAG edge (implicit `runAfter`) between producer and consumer
2. Injects an init container to fetch the content from storage
3. Verifies the content digest matches the reference
4. Mounts content at `$(inputs.<name>.path)` before user Steps execute

**2. Variable Substitution (TEP-0147 Phase 1 compatible)**

For Tasks that don't use the declarative API (or for passing artifact
metadata as parameters), the existing variable substitution syntax works:

```yaml
    - name: notify
      taskRef:
        name: send-notification
      params:
        - name: images-digest
          # TEP-0147 syntax — resolves to provenance metadata (JSON string)
          value: $(tasks.build.outputs.images)
```

This resolves to the serialized JSON `values` array, as in TEP-0147 Phase 1.
It passes provenance metadata (URI + digest), not the full content. Tasks
using this pattern must handle content fetching themselves.

### Init Container Injection for External Artifacts

When a downstream Task needs artifact content from external storage, the
controller injects an init container that:

1. Fetches artifact content from the storage backend
2. Verifies content digest matches the `StorageRef.Digest`
3. Writes content to a shared emptyDir volume at a well-known path
4. Reports verification status

```yaml
# Injected by controller (not written by users)
initContainers:
  - name: tekton-artifact-fetch
    image: gcr.io/tekton-releases/artifact-fetcher:latest
    args:
      - --artifacts=build/images:oci://registry.example.com/tekton/artifacts:tag
      - --verify-digest=sha256:abc123...
      - --output-dir=/tekton/artifacts/external
    volumeMounts:
      - name: tekton-artifacts
        mountPath: /tekton/artifacts/external
```

Content is available to Steps at the paths resolved by `$(inputs.<name>.path)`:
```
/tekton/artifacts/inputs/<artifact-name>/          # for declarative API
/tekton/artifacts/inputs/<artifact-name>/provenance.json  # provenance metadata
```

This parallels the trust model from TEP-0139: the init container acts as
the "download + verify" trusted step, ensuring content integrity before any
user Steps execute. The key difference from TEP-0139 is that these are init
containers (not injected Steps), so they don't appear in the Step list and
don't consume Step-level resources.

### Pipeline-Level Artifact Declarations

Pipelines can declare their own inputs and outputs, enabling artifact
passing across Pipeline boundaries and surfacing Task artifacts at the
Pipeline level:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-and-sign
spec:
  # Pipeline-level artifact declarations
  artifacts:
    inputs:
      - name: source
        description: Source code (passed from an outer Pipeline or PipelineRun)
    outputs:
      - name: images
        from: tasks.build.outputs.images
      - name: signatures
        from: tasks.sign.outputs.signatures
  tasks:
    - name: build
      taskRef:
        name: build-images
      artifacts:
        inputs:
          - name: source
            from: artifacts.inputs.source  # from Pipeline-level input
    - name: sign
      taskRef:
        name: sign-images
      artifacts:
        inputs:
          - name: images
            from: tasks.build.outputs.images
```

**PipelineRun artifact inputs** can be provided when triggering a run:

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

When the referenced Task artifacts have storage references, the Pipeline
output artifacts carry the same references (no re-upload). The PipelineRun
status includes the full artifact provenance chain.

### OCI Artifact Grouping per PipelineRun

When using an OCI registry backend, individual artifacts from a PipelineRun
can be difficult to browse. This section describes an optional grouping
strategy using OCI referrers (subject/refers-to relationships).

**Proposed structure:**

```
PipelineRun reference artifact (index)
├── TaskRun "build" reference artifact
│   ├── artifact: images (content layer)
│   └── artifact: build-log (content layer)
├── TaskRun "sign" reference artifact
│   └── artifact: signatures (content layer)
└── TaskRun "attest" reference artifact
    └── artifact: attestation (content layer)
```

The PipelineRun controller creates a root OCI artifact on PipelineRun
initialization. Each TaskRun's artifacts are attached as referring artifacts.
This enables:

- **Browsability**: Users can discover all artifacts from a PipelineRun
  starting from a single reference
- **Cache-friendliness**: Content-addressable layers enable OCI cache hits
- **Cleanup**: Deleting the root artifact cascades to all related artifacts

This feature is **optional** and only active when using the OCI backend with
`oci.groupByPipelineRun: "true"` in the configuration.

### Integration with Tekton Chains

Tekton Chains monitors TaskRun completions and creates SLSA provenance
attestations. The storage reference design directly addresses a critical
concern: **provenance explosion**.

**Problem**: If Chains records full artifact content in attestations (as it
currently does for results), large artifacts would cause:
- Massive attestation documents
- Rekor storage issues (as seen with SBOMs)
- Duplication: same content in one Task's output and another's input

**Solution with storage references:**

Chains can include only the **reference** (URI + digest) in the attestation,
not the full content:

```json
{
  "subject": [
    {
      "name": "pkg:docker/myapp@sha256:abc123",
      "digest": {"sha256": "abc123..."},
      "annotations": {
        "tekton.dev/storage-ref": "oci://registry.example.com/tekton/artifacts:tag"
      }
    }
  ]
}
```

This keeps attestations small and verifiable. Anyone with the digest can
fetch and verify the full content from external storage independently.

**Chains integration requirements:**
1. Chains must recognize `StorageRef` in artifact values
2. Chains records `Uri` + `Digest` (already does this for TEP-0147 artifacts)
3. Chains does NOT fetch and inline full content for externally stored artifacts
4. Chains MAY include `StorageRef.Location` as an annotation for discoverability

### Integration with Tekton Results and UIs

**Tekton Results** (long-term storage and querying):
- Results API stores `StorageRef` as metadata
- Optionally fetches and archives artifact content for long-term retention
- Query by artifact digest enables cross-pipeline correlation

**Downstream UIs** (Dashboard, third-party):
- UIs display artifact metadata from TaskRun status (URI, digest, size)
- For full content viewing, UIs resolve the `StorageRef` and fetch on demand
- Inline artifacts display directly (no fetch needed)
- The `size` field enables UIs to show content size without fetching

**Archivista and other storage backends:**
- Chains integration with [Archivista](https://github.com/tektoncd/chains/pull/1316)
  works as before — it stores the attestation, which now contains references
  rather than full content
- No-op for Archivista: it depends on Chains's provenance, not on raw content

### Storage Provider Interface

```go
package artifactstorage

import (
    "context"
    "io"

    v1 "github.com/tektoncd/pipeline/pkg/apis/pipeline/v1"
)

// Provider defines the interface for artifact storage backends.
type Provider interface {
    // Name returns the provider identifier (oci, s3, gcs, azure, pvc).
    Name() string

    // Store uploads artifact content and returns a storage reference.
    // The provider computes the digest during upload and returns it
    // in the StorageRef.
    Store(ctx context.Context, opts StoreOptions, content io.Reader) (*v1.StorageRef, error)

    // Fetch retrieves artifact content by storage reference.
    // Returns an error if the content digest does not match.
    Fetch(ctx context.Context, ref *v1.StorageRef) (io.ReadCloser, error)

    // Delete removes stored artifact content.
    Delete(ctx context.Context, ref *v1.StorageRef) error

    // Exists checks if artifact content exists.
    Exists(ctx context.Context, ref *v1.StorageRef) (bool, error)
}

// StoreOptions contains metadata for storing an artifact.
type StoreOptions struct {
    // Namespace of the TaskRun
    Namespace string
    // TaskRun name
    TaskRun string
    // PipelineRun name (if part of a pipeline)
    PipelineRun string
    // Artifact name
    ArtifactName string
    // Content type hint
    ContentType string
    // Additional metadata
    Labels map[string]string
}

// ProviderConfig contains configuration for initializing a provider.
type ProviderConfig struct {
    Backend     string
    Options     map[string]string
    Credentials CredentialsSource
}

// CredentialsSource defines where to get storage credentials.
type CredentialsSource struct {
    // SecretRef references a Kubernetes Secret
    SecretRef *SecretKeySelector
    // ServiceAccountName for workload identity (IRSA, GKE WI)
    ServiceAccountName string
}

// SecretKeySelector identifies a Secret and key
type SecretKeySelector struct {
    Name string
    Key  string
}
```

### Supported Backends

**Phase 1 (Alpha):**
- **OCI Registry** (via `oras.land/oras-go/v2`) — primary backend, compatible
  with Konflux CI's OCI-based trusted artifacts pattern
- **S3** (via `gocloud.dev/blob/s3blob`) — compatible with MinIO for
  on-premises deployments
- **PVC** — no external infrastructure needed, suitable for single-cluster
  development

**Phase 2 (Beta):**
- **GCS** (via `gocloud.dev/blob/gcsblob`)
- **Azure Blob** (via `gocloud.dev/blob/azureblob`)

**OCI Backend Details:**

The OCI backend is the recommended default, as it aligns with:
- Konflux CI's production trusted artifacts ([ADR-0036](https://github.com/konflux-ci/architecture/blob/main/ADR/0036-trusted-artifacts.md))
  using `create-trusted-artifact` / `use-trusted-artifact` steps
- Tekton Chains' existing OCI storage for attestations
- Container image registries already present in Kubernetes clusters

Artifacts are stored as OCI artifacts with:
- Content as a single layer (content-addressable by digest)
- Artifact metadata as annotations
- Tags following the configured `tagPattern`

### Garbage Collection

External artifacts consume storage that should be cleaned up. Approaches
(in order of implementation priority):

1. **Storage lifecycle policies** (MVP): Document that operators should
   configure backend-native TTL policies (S3 lifecycle rules, OCI tag
   expiration, etc.)

2. **Finalizer-based cleanup** (Phase 2): Add a finalizer to TaskRuns with
   external artifacts. On deletion, the controller removes associated
   artifacts from external storage.

   ```yaml
   metadata:
     finalizers:
       - artifacts.tekton.dev/external-cleanup
   ```

3. **Integration with Tekton Results** (Phase 3): When Tekton Results is
   deployed, artifact references can be preserved in Results storage before
   TaskRun deletion, maintaining queryability without retaining all content.

## Design Evaluation

### Reusability

This proposal extends TEP-0147 Phase 1 (implemented, alpha) rather than
creating a new system. The artifact provenance structure, API paths, and
variable substitution syntax are all reused directly. The storage provider
interface can be reused by Tekton Chains and Tekton Results.

The OCI backend aligns with Konflux CI's production pattern, enabling
compatibility with existing `create-trusted-artifact` / `use-trusted-artifact`
StepActions.

### Simplicity

**For Task authors**: No change to the artifact reporting API. Steps still
write to `$(step.artifacts.path)` in the same JSON format. If external
storage is configured, the entrypoint handles upload transparently.

**For Pipeline authors**: No change to variable substitution syntax. Artifacts
from upstream Tasks are consumed via `$(tasks.name.outputs.artifact)` as
before.

**For operators**: Single ConfigMap (`config-artifact-storage`) to configure
the storage backend. Familiar pattern from Tekton Chains configuration.

### Flexibility

- Pluggable backends allow operators to use existing infrastructure
- Three storage modes (inline, external, reference-only) cover all use cases
- Per-namespace and per-PipelineRun configuration enables multi-tenant setups
- OCI artifact grouping is optional for teams that want browsability

### Conformance

- Extends existing TEP-0147 API with backward-compatible additions
- Variable substitution syntax unchanged
- Results API unchanged (artifacts and results are separate concerns)
- Feature flag gated for gradual adoption

### User Experience

**What changes:**
- Operators configure `config-artifact-storage` (one-time setup)
- Task authors declare `spec.artifacts.inputs/outputs` and use
  `$(inputs.name.path)` / `$(outputs.name.path)` variables
- Pipeline authors connect Tasks with `artifacts.inputs[].from`

**What stays the same:**
- `$(step.artifacts.path)` API (TEP-0147 Phase 1 backward compat)
- `$(tasks.name.outputs.artifact)` syntax (provenance metadata)
- Artifact JSON format (`inputs`/`outputs` with `uri`/`digest`)
- TaskRun status structure (extended, not replaced)

**Progressive adoption path:**
1. **Today**: Tasks use `$(step.artifacts.path)` to write provenance JSON
   manually (TEP-0147 Phase 1)
2. **With this TEP**: Tasks can declare `spec.artifacts` and write content
   to `$(outputs.name.path)` — Tekton handles storage, digest, provenance
3. **Migration**: Existing Tasks continue to work; new Tasks use the
   declarative API for a simpler, safer experience

### Performance

**Positive:**
- No sidecar container overhead (unlike TEP-0127)
- Large artifacts don't bloat etcd/API server
- OCI content-addressable storage enables caching

**Potential:**
- Network latency when fetching artifacts for downstream Tasks
- Init container startup time (~1-2s)

**Mitigations:**
- Parallel fetching for multiple artifacts in a single init container
- OCI layer caching when clusters have caching proxies configured
- Inline mode for small artifacts avoids any latency

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Storage backend unavailable | Clear error messages; retry with backoff; inline fallback for small content |
| Credential management complexity | Support workload identity (IRSA, GKE WI); per-SA configuration |
| Orphaned artifacts | Storage lifecycle policies (MVP); finalizer cleanup (Phase 2) |
| Provenance explosion in Chains | Reference-based design: Chains records URI + digest, not content |
| Breaking TEP-0147 Phase 1 | All additions are optional fields; existing behavior unchanged |

### Drawbacks

1. **Infrastructure requirement**: External storage requires additional
   infrastructure (OCI registry, S3 bucket, etc.) — mitigated by PVC
   backend for development.

2. **Credential management**: Storage credentials must be configured —
   mitigated by workload identity support and per-SA configuration.

3. **Debugging complexity**: Artifact content not directly visible in
   TaskRun status — mitigated by inline mode for small artifacts, and
   `size` + `digest` metadata in status for troubleshooting.

## Alternatives

### TEP-0127: Sidecar Logs

**Approach**: Inject a sidecar container that monitors result files and emits
them via stdout; controller reads from pod logs.

**Why not chosen**:
- Sidecar on EVERY TaskRun (resource overhead)
- ~3 second startup time increase per TaskRun
- Results still end up in TaskRun status (~1.5MB CRD limit)
- No artifact provenance integration
- [Issue #8448](https://github.com/tektoncd/pipeline/issues/8448) requests
  selective enablement

### TEP-0139: Injected Trusted Steps with PVC

**Approach**: Inject 4 Steps (digest, upload, download, verify) into TaskRun
Pods, using a shared PVC Workspace for artifact storage.

**Why not chosen as-is**:
- Injected Steps are visible overhead (4 extra containers per Task)
- PVC-only storage limits artifact size to node disk / PVC capacity
- PVC requires ReadWriteMany for parallel Tasks (not universally available)
- No cross-cluster artifact sharing
- Artifact Workspace auto-provisioning adds controller complexity
- Tarball format (`<digest>.tgz`) is opaque in OCI registries

**What we adopt from TEP-0139**:
- Declarative Artifact API (`spec.artifacts.inputs/outputs`)
- Pipeline-level artifact binding
- Chain of trust via digest verification
- Artifact provenance in TaskRun status

**Where we differ**:
- Entrypoint + init container instead of injected Steps (transparent)
- External storage backends (OCI, S3, GCS) instead of PVC-only
- Content stored as-is, not as tarballs

### Standalone External Results (Original TEP-0164)

**Approach**: Introduce `type: external` as a new Result type, separate from
TEP-0147 artifacts.

**Why not chosen**:
- Creates a parallel system alongside TEP-0147 artifacts
- No artifact provenance integration (URI, digest)
- Doesn't address TEP-0139 trusted artifacts convergence
- Risk of duplicating content in Chains attestations (provenance explosion)
- @arewm's review correctly identified the need for reference-based design
  and TEP-0139 convergence

### ConfigMaps per TaskRun

**Approach**: Create a ConfigMap for each TaskRun to store results.

**Why not chosen**:
- Still limited to ~1.5MB per ConfigMap
- RBAC complexity
- API server load

### Workspaces Only

**Approach**: Document that large data should use Workspaces.

**Why not chosen**:
- Changes how users think about results vs files
- Requires Task modifications
- No provenance/trust chain
- Incompatible with no-code/low-code abstractions

## Future Work: Convergence of Results, Params, and Artifacts

This TEP introduces `spec.artifacts.inputs/outputs` alongside the existing
`spec.params` and `spec.results` fields. While this is the right incremental
step (params and results are stable/GA, artifacts are alpha), the long-term
direction is convergence into a unified inputs/outputs model.

### Mid-term: Results as Syntactic Sugar for Inline Artifacts

Results are fundamentally artifacts with `storage: inline` and no provenance
tracking. Once the artifact system matures to beta/stable, results could be
compiled down to inline artifacts internally:

```yaml
# These would become equivalent:
results:
  - name: digest
    type: string

artifacts:
  outputs:
    - name: digest
      storage: inline
```

This would:
- Unify the status format in TaskRun (one field instead of `results` +
  `artifacts`)
- Unify the resolution path in the controller
- Allow `$(tasks.x.results.y)` and `$(tasks.x.outputs.y)` to resolve
  identically
- Remove the results size limit naturally (inline threshold configurable,
  external storage for overflow)

The `spec.results` field would remain for backward compatibility and
ergonomics — most Tasks produce small metadata values where the full
artifact declaration is unnecessary overhead.

### Long-term: Unified Inputs and Outputs (API v2)

The natural end state is that Tasks declare **inputs** and **outputs**,
with the `type` field distinguishing values from artifacts:

```yaml
apiVersion: tekton.dev/v2  # future
kind: Task
metadata:
  name: build
spec:
  inputs:
    # Values (today's params)
    - name: repo-url
      type: string
    # Content with provenance (today's artifact inputs)
    - name: source
      type: artifact

  outputs:
    # Small values (today's results)
    - name: commit
      type: string
    # Content with provenance (today's artifact outputs)
    - name: images
      type: artifact
      buildOutput: true
      storage: external
```

Pipelines would connect them uniformly:

```yaml
tasks:
  - name: build
    taskRef: build
    inputs:
      - name: repo-url
        value: "https://github.com/..."
      - name: source
        from: tasks.clone.outputs.source
  - name: sign
    inputs:
      - name: images
        from: tasks.build.outputs.images
```

This convergence path is:

| Current | Mid-term | Long-term (v2) |
|---------|----------|----------------|
| `spec.params` | Unchanged | → `spec.inputs` (type: string/array/object) |
| `spec.results` | Sugar for inline artifacts | → `spec.outputs` (type: string/array/object) |
| `spec.artifacts.inputs` | Unchanged | → `spec.inputs` (type: artifact) |
| `spec.artifacts.outputs` | Unchanged | → `spec.outputs` (type: artifact) |
| `$(params.x)` | Unchanged | → `$(inputs.x)` or `$(inputs.x.value)` |
| `$(results.x.path)` | Unchanged | → `$(outputs.x.path)` |
| `$(tasks.x.results.y)` | Also `$(tasks.x.outputs.y)` | → `$(tasks.x.outputs.y)` |
| `$(step.artifacts.path)` | Backward compat | Deprecated |

This TEP does not propose these changes — they require a broader API
versioning discussion with the Tekton community. However, the design
choices in this TEP (declarative inputs/outputs, path-based variables,
storage modes) are intentionally aligned with this convergence direction
to avoid future breaking changes.

## Implementation Plan

### Phase 1: Core Infrastructure (Alpha)

1. **Declarative Artifact API**: Add `spec.artifacts.inputs/outputs` to
   Task spec with validation
2. **Artifact path variables**: Implement `$(inputs.name.path)`,
   `$(outputs.name.path)`, `$(inputs.name.uri)`, `$(inputs.name.digest)`
3. Extend `ArtifactValue` and `Artifact` types with `StorageRef`, `Size`,
   `Inline` fields
4. Define `Provider` interface
5. Implement OCI provider using ORAS (Konflux-compatible)
6. Implement S3 provider using `gocloud.dev/blob`
7. Implement PVC provider
8. Add `config-artifact-storage` ConfigMap handling
9. Modify entrypoint to upload artifacts from `$(outputs.name.path)` with
   automatic digest computation
10. Init container injection for downloading artifacts to
    `$(inputs.name.path)` with digest verification
11. Feature flag: `enable-artifact-storage: "true"` (extends existing
    `enable-artifacts`)
12. E2E tests with OCI and S3 backends
13. Document storage lifecycle policies for cleanup

### Phase 2: Extended Features (Beta)

1. **Pipeline-level artifact binding**: `artifacts.inputs[].from` syntax
   with implicit DAG edges
2. **Pipeline-level artifact declarations**: Pipeline `spec.artifacts`
   inputs/outputs
3. GCS and Azure Blob providers
4. Namespace-level configuration overrides
5. Per-PipelineRun configuration via annotations
6. OCI artifact grouping per PipelineRun
7. Garbage collection via finalizers
8. Tekton Chains integration (reference-based attestations)
9. Promote to beta

### Phase 3: Production Ready (Stable)

1. Caching layer for OCI artifacts
2. Metrics and observability (upload/download latency, storage usage)
3. Integration with Tekton Results project
4. Background garbage collector for orphaned artifacts
5. Promote to stable

### Test Plan

- Unit tests for `spec.artifacts` validation and variable substitution
- Unit tests for each storage provider
- Unit tests for `ArtifactValue` extension backward compatibility
- Integration tests for declarative artifact binding between Tasks
- Integration tests with mock storage
- E2E tests with real backends (OCI registry via `zot`, S3 via MinIO)
- E2E tests verifying digest verification catches tampering
- E2E tests for Pipeline-level artifact passing
- Performance benchmarks for upload/download latency
- Backward compatibility tests with TEP-0147 Phase 1 artifacts

### Infrastructure Needed

- CI/CD access to OCI registry (e.g., `zot` or local distribution registry)
- CI/CD access to S3-compatible storage (MinIO)
- Documentation updates for configuration

### Upgrade and Migration Strategy

- Feature is opt-in via ConfigMap configuration and feature flag
- No migration needed for existing Tasks/Pipelines
- Existing TEP-0147 Phase 1 artifacts continue to work unchanged
- Feature flag allows gradual rollout
- Inline results continue to work as before

### Implementation Pull Requests

<!-- To be filled as implementation progresses -->

## References

- [TEP-0147: Tekton Artifacts Phase 1](https://github.com/tektoncd/community/blob/main/teps/0147-tekton-artifacts-phase1.md) — Foundation this TEP extends
- [TEP-0139: Trusted Artifacts](https://github.com/tektoncd/community/blob/main/teps/0139-trusted-artifacts.md) — Trust chain requirements this TEP implements
- [TEP-0085: Per-Namespace Controller Configuration](https://github.com/tektoncd/community/blob/main/teps/0085-per-namespace-controller-configuration.md)
- [TEP-0127: Larger Results via Sidecar Logs](https://github.com/tektoncd/community/blob/main/teps/0127-larger-results-via-sidecar-logs.md) — Alternative approach
- [Konflux CI Trusted Artifacts (ADR-0036)](https://github.com/konflux-ci/architecture/blob/main/ADR/0036-trusted-artifacts.md) — Production OCI-based pattern
- [Issue #4012: Changing the way Result Parameters are stored](https://github.com/tektoncd/pipeline/issues/4012)
- [Issue #4808: Results, TerminationMessage and Containers](https://github.com/tektoncd/pipeline/issues/4808)
- [Issue #6326: Artifact provenance feature request](https://github.com/tektoncd/pipeline/issues/6326)
- [Issue #8448: Enable larger results without a sidecar on every TaskRun](https://github.com/tektoncd/pipeline/issues/8448)
- [Argo Workflows Artifacts](https://argo-workflows.readthedocs.io/en/latest/walk-through/artifacts/)
- [ORAS: OCI Registry As Storage](https://oras.land/)
- [go-cloud/blob: Multi-cloud storage abstraction](https://github.com/google/go-cloud/tree/master/blob)
- [Tekton Results Project](https://github.com/tektoncd/results)
- [Tekton Chains](https://github.com/tektoncd/chains)
