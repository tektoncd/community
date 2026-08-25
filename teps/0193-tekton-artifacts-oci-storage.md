---
title: "Tekton Artifacts OCI Storage"
authors:
  - "@vdemeester"
  - "@savitaashture"
creation-date: 2026-08-19
last-updated: 2026-08-19
status: proposed
see-also:
  - TEP-0085
  - TEP-0147
  - TEP-0192
---

# TEP-0193: Tekton Artifacts OCI Storage

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Why OCI First](#why-oci-first)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Design Details](#design-details)
  - [OCI Provider Implementation](#oci-provider-implementation)
    - [Verification](#verification)
  - [Repository Configuration Hierarchy](#repository-configuration-hierarchy)
  - [ConfigMap Configuration](#configmap-configuration)
  - [Authentication](#authentication)
  - [OCI Artifact Format Specification](#oci-artifact-format-specification)
  - [Multi-File Artifacts](#multi-file-artifacts)
  - [OCI Referrers as Artifact Attachment Model](#oci-referrers-as-artifact-attachment-model)
  - [Same-Repository Constraint](#same-repository-constraint)
  - [PipelineRun Grouping via OCI Referrers](#pipelinerun-grouping-via-oci-referrers)
  - [Tagging Convention](#tagging-convention)
  - [Integration with Tekton Chains](#integration-with-tekton-chains)
  - [Integration with Tekton Results and UIs](#integration-with-tekton-results-and-uis)
  - [Garbage Collection](#garbage-collection)
  - [Konflux CI Compatibility](#konflux-ci-compatibility)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [S3 as Default Backend](#s3-as-default-backend)
  - [PVC as Default Backend](#pvc-as-default-backend)
  - [Custom CRD for Storage](#custom-crd-for-storage)
- [Implementation Plan](#implementation-plan)
  - [Phase 1 (Alpha)](#phase-1-alpha)
  - [Phase 2 (Beta)](#phase-2-beta)
  - [Phase 3 (Stable)](#phase-3-stable)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
- [Future Work](#future-work)
- [References](#references)
<!-- /toc -->

## Summary

This TEP defines the OCI registry implementation of the `Provider`
interface from [TEP-0192](0192-tekton-artifacts-api.md). OCI is the
default and first storage backend for Tekton's declarative artifact
system.

When a Task declares a `type: content` output artifact, the entrypoint
uploads it to an OCI registry as an OCI artifact manifest. When a
downstream Task declares a content input, an init container pulls the
artifact from the registry and verifies its digest. Output artifacts
marked with `subject: true` can have other artifacts attached as OCI
referrers, creating a supply chain graph visible via `cosign tree` or
`oras discover`.

## Motivation

### Why OCI First

OCI is the natural default backend for Tekton artifact storage:

1. **Already available**: Every Kubernetes cluster has access to an OCI
   registry for container images. No additional infrastructure required in
   many setups.

2. **Production proven**: [Konflux CI](https://github.com/konflux-ci) uses
   OCI registries for trusted artifacts in production
   ([ADR-0036](https://github.com/konflux-ci/architecture/blob/main/ADR/0036-trusted-artifacts.md)).

3. **Chains alignment**: Tekton Chains already stores attestations and
   signatures in OCI registries. Artifacts join the same graph.

4. **Content-addressable**: Native deduplication and caching. The same
   content pushed twice stores only one copy.

5. **Referrers API**: OCI 1.1 referrers enable natural artifact grouping
   — the same mechanism cosign signatures, SBOMs, and SLSA attestations
   use.

6. **Auth reuse**: ServiceAccount `imagePullSecrets` provide registry
   credentials with zero additional configuration.

7. **Cross-cluster**: Registries are network-accessible, enabling artifact
   sharing across clusters without shared PVCs.

### Goals

1. Implement the `Provider` interface from TEP-0192 for OCI registries.
2. Define the OCI artifact format (manifests, layers, annotations).
3. Define repository configuration at cluster, namespace, Pipeline, and
   PipelineRun levels.
4. Attach artifacts as OCI referrers to `subject: true` artifacts.
5. Reuse existing Kubernetes/Tekton auth mechanisms.
6. Align with Konflux CI's OCI artifact format for interoperability.

### Non-Goals

1. Implementing S3, GCS, PVC, or other backends (future TEPs).
2. Building a registry (operators choose their own).
3. Registry-level access control (delegated to registry and K8s RBAC).
4. Artifact content indexing or search (that's Tekton Results' domain).

## Design Details

### OCI Provider Implementation

The OCI provider implements the `Provider` interface using
[ORAS](https://oras.land/) (`oras.land/oras-go/v2`):

```go
package oci

import (
    "context"
    "io"

    v1 "github.com/tektoncd/pipeline/pkg/apis/pipeline/v1"
    "github.com/tektoncd/pipeline/pkg/artifactstorage"
)

type OCIProvider struct {
    repository string
    // ... registry client, auth config
}

func (p *OCIProvider) Name() string { return "oci" }

func (p *OCIProvider) Store(ctx context.Context, opts artifactstorage.StoreOptions, content io.Reader) (*v1.StorageRef, error) {
    // 1. Read content, compute SHA-256 digest
    // 2. Create OCI manifest with content as layer
    // 3. Push manifest to repository with tag from opts
    // 4. Return StorageRef with backend="oci", location, digest
}

func (p *OCIProvider) Fetch(ctx context.Context, ref *v1.StorageRef) (io.ReadCloser, error) {
    // 1. Parse location to get repository + reference
    // 2. Pull manifest by digest, extract content layer
    // 3. Return content reader
}

// ContentAddressed reports that OCI pulls are digest-pinned and therefore
// self-verifying, so core skips wrapping Fetch in a verifying reader.
func (p *OCIProvider) ContentAddressed() bool { return true }

func (p *OCIProvider) Delete(ctx context.Context, ref *v1.StorageRef) error {
    // Delete manifest by digest from repository
}

func (p *OCIProvider) Exists(ctx context.Context, ref *v1.StorageRef) (bool, error) {
    // HEAD request for manifest by digest
}
```

The OCI provider is compiled into the Tekton controller and the
entrypoint binary. No separate sidecar or service needed.

#### Verification

[TEP-0192](0192-tekton-artifacts-api.md) makes digest verification the
responsibility of Tekton core rather than of backend authors: core wraps
every `Fetch` in a digest-verifying read by default, so a provider cannot
accidentally omit the check.

OCI is the case where that wrapper is redundant. Content is pulled by digest
(`@sha256:...`), and an OCI pull that resolves has already verified the
content against that digest — verification is a property of the transport,
not a separate step. The provider therefore implements the optional
`ContentAddressedProvider` interface so that large artifacts are not hashed
twice.

This is specific to content-addressed transports. A hypothetical S3 or GCS
backend would not implement it: object keys can be chosen to embed the
digest, but `ETag` is an MD5 or a multipart-dependent value and cannot be
trusted as an integrity check, so core's verifying read would apply.

### Repository Configuration Hierarchy

The OCI repository where artifacts are stored is configured at four
levels. This is an **operational concern** (where to store), not a
Pipeline design concern (what to do).

**Resolution order (highest priority first):**

| Priority | Source | Use Case |
|----------|--------|----------|
| 1 | PipelineRun annotations | Caller-controlled, per-invocation |
| 2 | Pipeline annotations | Pipeline author default |
| 3 | Namespace ConfigMap | Team/project isolation (TEP-0085) |
| 4 | Cluster ConfigMap (`tekton-pipelines`) | Cluster default |

Each level inherits unset fields from the level below. For example, a
PipelineRun annotation can override just the repository while inheriting
inline threshold and tag pattern from the cluster ConfigMap.

**Level 1: Cluster-level ConfigMap (global default)**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-artifact-storage
  namespace: tekton-pipelines
data:
  enabled: "true"
  backend: "oci"
  inline-threshold: "1024"
  oci.repository: "registry.example.com/tekton/artifacts"
  oci.attachReferrers: "true"
  oci.tagPattern: "{{namespace}}.{{taskrun}}.{{artifact}}"
```

**Level 2: Namespace-level ConfigMap (per TEP-0085)**

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-artifact-storage
  namespace: team-a
  labels:
    tekton.dev/config-type: artifact-storage
data:
  oci.repository: "team-a-registry.example.com/artifacts"
  oci.credentialsSecret: "team-a-registry-creds"
```

**Level 3: Pipeline annotations**

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: release-pipeline
  annotations:
    tekton.dev/artifact-storage-oci-repository: "registry.example.com/release/artifacts"
```

**Level 4: PipelineRun annotations**

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  annotations:
    tekton.dev/artifact-storage-oci-repository: "my-registry.example.com/my-app/artifacts"
spec:
  serviceAccountName: my-sa  # SA imagePullSecrets used for OCI auth
  pipelineRef:
    name: release-pipeline
```

### ConfigMap Configuration

Full cluster-level ConfigMap reference:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-artifact-storage
  namespace: tekton-pipelines
data:
  # Enable content artifact storage (default: "false")
  enabled: "true"

  # Backend type (default: "oci")
  backend: "oci"

  # Artifacts smaller than this are stored inline in TaskRun status
  # regardless of backend (default: "1024" bytes)
  inline-threshold: "1024"

  # --- OCI-specific configuration ---

  # Default OCI repository for artifact staging (task-to-task passing).
  # Required when backend is "oci".
  oci.repository: "registry.example.com/tekton/artifacts"

  # Secret containing OCI registry credentials (kubernetes.io/dockerconfigjson).
  # If not set, ServiceAccount imagePullSecrets are used.
  # oci.credentialsSecret: "tekton-artifact-oci-creds"

  # Attach output artifacts as OCI referrers to subject artifacts.
  # Referrers are pushed to the subject's repository (same-repo constraint).
  # Default: "true"
  oci.attachReferrers: "true"

  # Tag pattern for artifact manifests in oci.repository.
  # Variables: {{namespace}}, {{pipelinerun}}, {{taskrun}}, {{artifact}}
  # Default: "{{namespace}}.{{taskrun}}.{{artifact}}"
  oci.tagPattern: "{{namespace}}.{{taskrun}}.{{artifact}}"

  # Create a root OCI Index per PipelineRun and attach all artifacts
  # as referrers to it. Useful when there is no subject artifact.
  # Default: "false"
  oci.groupByPipelineRun: "false"
```

### Authentication

The OCI provider reuses Kubernetes-native registry authentication:

1. **ServiceAccount imagePullSecrets (default)**: The TaskRun's
   ServiceAccount credentials are used for push/pull. No additional
   configuration needed if the SA already has access to the registry.

2. **Dedicated Secret**: `oci.credentialsSecret` points to a
   `kubernetes.io/dockerconfigjson` Secret for registries that need
   separate artifact credentials.

3. **Workload Identity**: On GKE (Workload Identity) and AWS (IRSA), the
   Pod's identity grants registry access automatically.

This means clusters that already pull images from a private registry can
store artifacts there with **zero additional credential configuration**.

The ServiceAccount bound to the PipelineRun/TaskRun must have push access
to the resolved repository. For referrer attachment (post-run), the SA
must also have push access to the subject artifact's repository.

### OCI Artifact Format Specification

Each content artifact is stored as an OCI manifest with a single content
layer, following the [OCI Image Manifest
Specification](https://github.com/opencontainers/image-spec/blob/main/manifest.md)
and [ORAS conventions](https://oras.land/).

**Single-file artifact manifest:**

```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "config": {
    "mediaType": "application/vnd.tekton.artifact.config.v1+json",
    "digest": "sha256:<config-digest>",
    "size": 233
  },
  "layers": [
    {
      "mediaType": "application/xml",
      "digest": "sha256:<content-digest>",
      "size": 45678,
      "annotations": {
        "org.opencontainers.image.title": "test-results"
      }
    }
  ],
  "annotations": {
    "dev.tekton.artifact/name": "test-results",
    "dev.tekton.artifact/taskrun": "run-tests-abc123",
    "dev.tekton.artifact/pipelinerun": "my-pipeline-run",
    "dev.tekton.artifact/namespace": "default",
    "dev.tekton.artifact/created": "2026-08-19T12:00:00Z"
  }
}
```

**Config blob** (artifact metadata, not container config):

```json
{
  "created": "2026-08-19T12:00:00Z",
  "artifact": {
    "name": "test-results",
    "taskrun": "run-tests-abc123",
    "pipelinerun": "my-pipeline-run",
    "namespace": "default",
    "contentType": "application/xml"
  }
}
```

**Media types:**

| Media Type | Usage |
|------------|-------|
| `application/vnd.tekton.artifact.config.v1+json` | Config blob |
| `application/octet-stream` | Default content layer (binary) |
| `application/json` | Content detected as JSON |
| `application/xml` | Content detected as XML |
| `application/spdx+json` | SPDX SBOMs (from `mediaType` declaration) |
| `application/vnd.cyclonedx+json` | CycloneDX SBOMs |
| `application/vnd.tekton.artifact.tar+gzip` | Multi-file archives |

The layer media type is determined by:
1. `mediaType` field on `ArtifactDeclaration` (if specified).
2. Content detection (inspect first bytes).
3. Fallback: `application/octet-stream`.

### Multi-File Artifacts

When a Step writes multiple files to `$(outputs.name.path)/`, the
entrypoint creates a tar+gzip archive before uploading:

```json
{
  "layers": [
    {
      "mediaType": "application/vnd.tekton.artifact.tar+gzip",
      "digest": "sha256:<tar-digest>",
      "size": 102400,
      "annotations": {
        "org.opencontainers.image.title": "test-results",
        "dev.tekton.artifact/archive": "tar+gzip"
      }
    }
  ]
}
```

The init container (fetch side) detects the `dev.tekton.artifact/archive`
annotation and extracts the tar to the input path, preserving directory
structure.

Single-file artifacts are stored as-is (no archiving overhead).

### OCI Referrers as Artifact Attachment Model

Output artifacts from a PipelineRun can be attached as **OCI referrers**
to the `subject: true` artifact using the OCI 1.1
[`subject` field](https://github.com/opencontainers/image-spec/blob/main/manifest.md).
This is the same mechanism used by cosign signatures, SBOM attachments,
and SLSA attestations.

**Example referrer tree** (validated in
[PoC on ghcr.io](https://github.com/vdemeester/tekton-experiments)):

```
$ cosign tree ghcr.io/vdemeester/tekton-experiments:latest
📦 Supply Chain Security Related artifacts for an image: ghcr.io/vdemeester/tekton-experiments:latest
├── 🔐 Attestations (Tekton Chains SLSA provenance)
├── 🔐 Signatures (Tekton Chains cosign)
├── 🔐 SBOMs (ko-generated SPDX)
├── 📦 images-manifest.json   (Tekton artifact referrer)
├── 📦 junit-results.xml      (Tekton artifact referrer)
└── 📦 coverage.out           (Tekton artifact referrer)
```

Each referrer manifest includes a `subject` descriptor:

```json
{
  "schemaVersion": 2,
  "mediaType": "application/vnd.oci.image.manifest.v1+json",
  "artifactType": "application/vnd.tekton.artifact.v1",
  "subject": {
    "mediaType": "application/vnd.oci.image.manifest.v1+json",
    "digest": "sha256:<subject-image-digest>",
    "size": 1234
  },
  "config": { ... },
  "layers": [ ... ],
  "annotations": {
    "dev.tekton.artifact/name": "test-results",
    "dev.tekton.artifact/pipelinerun": "my-pipeline-run"
  }
}
```

**What this enables:**

- **Discovery**: `oras discover <image>` or `cosign tree <image>` shows
  the full supply chain graph in one view.
- **Ecosystem native**: same API as cosign, Chains, and SBOM tooling.
- **Any OCI artifact as subject**: container images, binary tarballs, RPMs,
  Helm charts, ML models.
- **History**: referrers accumulate per image digest, filterable by
  `dev.tekton.artifact/pipelinerun` annotation.

Referrer attachment is enabled by default (`oci.attachReferrers: "true"`)
and happens **post-PipelineRun** as a non-blocking operation. If
attachment fails (missing credentials, registry doesn't support
referrers), the controller emits a warning condition — it does not fail
the PipelineRun.

### Same-Repository Constraint

The [OCI Distribution
Spec](https://github.com/opencontainers/distribution-spec/blob/main/spec.md#listing-referrers)
requires referrers in the **same repository** as their subject.

This means artifact staging (task-to-task transport) and referrer
attachment (supply chain graph) may target different repositories:

| Operation | When | Destination | Purpose |
|-----------|------|-------------|---------|
| Staging | During the run | `oci.repository` | Task-to-task content passing |
| Referrer attachment | After the run | Subject's repository | Supply chain graph |

**Example: image build pipeline**

```
# Staging repo (from config)
registry.example.com/tekton/artifacts ← task-to-task artifact content

# Subject repo (from the built image URI)
registry.example.com/myapp           ← referrers live here (same repo as image)
```

The controller handles this by:

1. **During the run**: uploading content artifacts to `oci.repository` for
   downstream Task consumption.
2. **After the PipelineRun**: for each output artifact, pushing a referrer
   manifest into the **subject's repository** with the artifact content
   cross-mounted (if registry supports it) or re-uploaded.

**Cross-registry considerations**: If the subject lives in a different
registry than `oci.repository`, the SA must have push credentials for both.
If cross-mount is not supported, the content is re-uploaded.

For pipelines **without** a `subject: true` artifact, referrers are
attached within `oci.repository` itself (no cross-repo needed).

### PipelineRun Grouping via OCI Referrers

For use cases requiring a single entry point per PipelineRun (or when
there is no `subject: true` artifact), the controller can create a root
OCI Index manifest and attach all artifacts as referrers:

```
PipelineRun root manifest (OCI Index)
├── refers-to → build/images artifact
├── refers-to → build/build-log artifact
├── refers-to → test/test-results artifact
└── refers-to → sign/signatures artifact
```

Enabled with `oci.groupByPipelineRun: "true"`. The root manifest is
created in:
- The subject artifact's repository (if `subject: true` exists).
- `oci.repository` (if no subject artifact).

This enables:
- **Single entry point**: list all artifacts via
  `GET /v2/<repo>/referrers/<root-digest>`.
- **Bulk cleanup**: delete root + referrers to remove all PipelineRun
  artifacts.

### Tagging Convention

Artifacts are pushed with tags following the `oci.tagPattern`:

```
registry.example.com/tekton/artifacts:<tag>
```

Default pattern: `{{namespace}}.{{taskrun}}.{{artifact}}`

Examples:
```
registry.example.com/tekton/artifacts:default.build-images-abc.images
registry.example.com/tekton/artifacts:default.build-images-abc.sbom
registry.example.com/tekton/artifacts:default.run-tests-def.test-results
```

Tags are mutable references for human convenience. The canonical reference
is always by digest (`@sha256:...`), recorded in `StorageRef.Digest` and
used for verification.

### Integration with Tekton Chains

Chains already stores attestations and signatures in OCI registries.
With this TEP:

- Tekton artifacts join the same referrer tree as Chains attestations
  and cosign signatures.
- `cosign tree <image>` shows everything: signatures, attestations, SBOMs,
  and build artifacts.
- Chains records only URI + digest for content artifacts (not full content),
  keeping attestations small.

The PoC at
[`vdemeester/tekton-experiments`](https://github.com/vdemeester/tekton-experiments)
demonstrates this end-to-end on ghcr.io.

### Integration with Tekton Results and UIs

**Tekton Results**: Can archive OCI artifact content by pulling from the
registry using `StorageRef`. Enables long-term retention independent of
registry lifecycle policies.

**UIs**: Can resolve `StorageRef` with `backend: "oci"` to fetch and
display artifact content on demand. `oras` CLI or any OCI client works.

```bash
# Fetch artifact content
oras pull registry.example.com/tekton/artifacts:default.build-abc.sbom

# List referrers for a build image
oras discover registry.example.com/myapp@sha256:abc123
```

### Garbage Collection

Artifact storage cleanup approaches (in order of implementation):

**Phase 1 (MVP): Registry lifecycle policies**

Document that operators should configure registry-native TTL policies:
- Harbor: tag retention policies
- GCR/GAR: cleanup policies
- ECR: lifecycle rules
- Quay: tag expiration

**Phase 2: Finalizer-based cleanup**

Add a finalizer to TaskRuns with OCI-stored artifacts:

```yaml
metadata:
  finalizers:
    - artifacts.tekton.dev/oci-cleanup
```

On TaskRun deletion, the controller deletes the artifact manifest from
the registry by digest.

**Phase 3: Background garbage collector**

A controller that periodically scans for orphaned artifact manifests
(referencing deleted TaskRuns) and removes them.

### Konflux CI Compatibility

[Konflux CI](https://github.com/konflux-ci)'s trusted artifacts
([ADR-0036](https://github.com/konflux-ci/architecture/blob/main/ADR/0036-trusted-artifacts.md))
use ORAS to push/pull content from OCI registries via
[`build-trusted-artifacts`](https://github.com/konflux-ci/build-trusted-artifacts).

The formats are compatible:
- Konflux pushes content as OCI artifact layers with digests.
- This TEP uses the same ORAS primitives with additional Tekton-specific
  annotations.
- Tasks using Konflux's existing `create-trusted-artifact` /
  `use-trusted-artifact` StepActions can coexist with Tekton-managed
  artifacts.

Over time, the declarative `spec.artifacts` API (TEP-0192) replaces the
need for explicit trusted-artifact StepActions — Tekton handles
upload/download/verify transparently. Because TEP-0192 lets a `StepAction`
declare its own `artifacts.outputs`, this can be an incremental migration
rather than a rewrite: an existing `create-trusted-artifact` StepAction can
declare the artifact it produces and let Tekton take over transport, without
Tasks that reference it changing shape.

## Design Evaluation

### Reusability

- Uses standard OCI APIs and ORAS libraries.
- OCI artifact format is consumable by any OCI-aware tool (`oras`, `crane`,
  `skopeo`, registry UIs).
- Referrer model is the same as cosign, Chains, and SBOM tooling.

### Simplicity

- **For operators**: one ConfigMap field (`oci.repository`) to configure.
  Auth reuses existing imagePullSecrets.
- **For Task authors**: no OCI awareness needed. Write to
  `$(outputs.name.path)`, Tekton handles the rest.
- **For consumers**: `oras pull` or `cosign tree` — standard tooling.

### Flexibility

- Four-level repository configuration covers single-tenant to multi-tenant.
- Referrer attachment is optional and non-blocking.
- PipelineRun grouping is optional.
- Any OCI-compliant registry works (Docker Distribution, Harbor, Zot,
  GCR, ECR, ACR, Quay, ghcr.io).

### Performance

- Content-addressable storage = native deduplication.
- OCI layer caching works with registry mirrors and pull-through caches.
- Parallel push/pull for multiple artifacts.
- Single-file artifacts skip tar overhead.

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Registry unavailable | Retry with backoff; clear error message; inline fallback for small content |
| Cross-registry referrer push fails | Warning condition, not failure; referrer attachment is post-run |
| Registry doesn't support referrers API | Fallback tag scheme (OCI 1.0 compat); warn in conditions |
| Large artifacts slow pipeline | Parallel upload/download; layer caching; size shown in status |
| Tag conflicts | Tags include namespace + TaskRun name; canonical ref is by digest |

### Drawbacks

1. **Registry infrastructure**: Requires an OCI registry. Mitigated by
   ubiquity (every K8s cluster has one) and future PVC backend for
   air-gapped environments.

2. **Registry capacity**: Large artifacts consume registry storage.
   Mitigated by content-addressable dedup, lifecycle policies, and GC.

3. **Network dependency**: Artifact fetch adds network latency between
   Tasks. Mitigated by caching, parallel fetch, and inline mode for
   small content.

## Alternatives

### S3 as Default Backend

**Why not**: Not universally available in Kubernetes clusters. Requires
provisioning a bucket and credentials. No referrers/supply-chain-graph
equivalent. Good as a Phase 2 backend.

### PVC as Default Backend

**Why not**: Requires ReadWriteMany for parallel Tasks (not universally
available). Limited to node/PVC capacity. No cross-cluster sharing. No
content addressing or dedup. Good as a Phase 2 backend for air-gapped
and development environments.

### Custom CRD for Storage

**Why not**: Adds API server load. Doesn't solve the storage problem —
content still needs to go somewhere. Over-engineering for what is
fundamentally a blob store operation.

## Implementation Plan

### Phase 1 (Alpha)

1. Implement `OCIProvider` using `oras.land/oras-go/v2`.
2. OCI artifact format: manifest, config blob, content layer, annotations.
3. Content-type detection and `mediaType` override.
4. Multi-file tar+gzip archiving.
5. SHA-256 digest computation and verification.
6. Auth via ServiceAccount imagePullSecrets.
7. `config-artifact-storage` ConfigMap handling (cluster + namespace).
8. Entrypoint integration: push content artifacts after step completion.
9. Init container (`cmd/artifactfetcher`, released with tektoncd/pipeline): pull + verify for content inputs.
10. E2E tests with Zot (lightweight OCI registry) in CI.
11. Documentation: registry requirements, configuration guide.

### Phase 2 (Beta)

1. Pipeline/PipelineRun annotation overrides for repository.
2. OCI referrer attachment (post-PipelineRun).
3. PipelineRun grouping via OCI Index.
4. `oci.credentialsSecret` support.
5. Cross-mount for referrer attachment.
6. Finalizer-based garbage collection.
7. Konflux CI interoperability validation.

### Phase 3 (Stable)

1. Background garbage collector.
2. Metrics: upload/download latency, storage usage, cache hit rate.
3. Registry mirror / pull-through cache documentation.
4. Promote to stable.

### Test Plan

- Unit tests: OCI manifest creation, digest computation, tag pattern
  rendering, config parsing, auth resolution.
- Integration tests: push/pull with mock registry, multi-file archive
  round-trip, referrer attachment, digest verification failure.
- E2E tests: full Pipeline with OCI backend (Zot in CI), cross-Task
  artifact passing, referrer tree validation, Chains coexistence.
- Compatibility tests: Konflux trusted-artifact format interop.
- Performance tests: upload/download latency benchmarks for various
  artifact sizes.

### Infrastructure Needed

- CI: lightweight OCI registry (Zot or distribution/registry).
- Optional: ghcr.io or quay.io for referrer API E2E (these support OCI 1.1).
- No new production infrastructure — operators bring their own registry.

## Future Work

- **S3 backend** (`gocloud.dev/blob/s3blob`): MinIO-compatible for
  on-premises. Implements same `Provider` interface.
- **GCS backend** (`gocloud.dev/blob/gcsblob`): Google Cloud native.
- **PVC backend**: No external infrastructure. Suitable for development
  and air-gapped clusters.
- **Azure Blob backend** (`gocloud.dev/blob/azureblob`).
- **OCI layer caching**: Integration with registry mirrors and
  pull-through caches for faster artifact fetch.
- **Content deduplication across PipelineRuns**: Same content → same
  digest → already in registry. Automatic with content-addressable storage.

## References

- [TEP-0192: Tekton Artifacts API](0192-tekton-artifacts-api.md)
- [TEP-0147: Tekton Artifacts Phase 1](0147-tekton-artifacts-phase1.md)
- [TEP-0085: Per-Namespace Controller Configuration](0085-per-namespace-controller-configuration.md)
- [Konflux CI Trusted Artifacts (ADR-0036)](https://github.com/konflux-ci/architecture/blob/main/ADR/0036-trusted-artifacts.md)
- [OCI Image Manifest Specification](https://github.com/opencontainers/image-spec/blob/main/manifest.md)
- [OCI Distribution Spec — Referrers](https://github.com/opencontainers/distribution-spec/blob/main/spec.md#listing-referrers)
- [ORAS: OCI Registry As Storage](https://oras.land/)
- [Proof of Concept: `vdemeester/tekton-experiments`](https://github.com/vdemeester/tekton-experiments)
- [Tekton Chains](https://github.com/tektoncd/chains)
