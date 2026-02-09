---
title: Larger Results via External Storage with Pluggable Backends
authors:
  - "@vdemeester"
creation-date: 2026-02-04
last-updated: 2026-02-09
status: proposed
see-also:
  - TEP-0085
  - TEP-0086
  - TEP-0127
---

# TEP-0164: Larger Results via External Storage with Pluggable Backends

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [New Result Type: external](#new-result-type-external)
  - [Behavior When External Storage Is Not Configured](#behavior-when-external-storage-is-not-configured)
  - [Storage Backend Configuration](#storage-backend-configuration)
  - [Namespace-Level Configuration](#namespace-level-configuration)
  - [TaskRun Status with References](#taskrun-status-with-references)
  - [Transparent Resolution for Downstream Tasks](#transparent-resolution-for-downstream-tasks)
  - [Init Container Injection for Large Results](#init-container-injection-for-large-results)
  - [Pipeline-Level Result Declarations](#pipeline-level-result-declarations)
  - [Integration with External Tools and Services](#integration-with-external-tools-and-services)
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
  - [ConfigMaps per TaskRun](#configmaps-per-taskrun)
  - [Custom CRD for Results](#custom-crd-for-results)
  - [Workspaces Only](#workspaces-only)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes a new approach to handling large Task results by introducing
external storage backends with pluggable providers. Instead of storing large
result values directly in the TaskRun status (limited by Kubernetes CRD size
constraints), this proposal allows results to be stored in external storage
systems (S3, GCS, OCI registries, etc.) while only storing a reference in
the TaskRun status.

This approach provides:
- **No per-pod overhead**: Unlike TEP-0127's sidecar approach, no additional
  containers are injected into TaskRun pods
- **Truly unlimited result sizes**: Limited only by the external storage backend
- **Per-result opt-in**: Only results marked as `type: external` use external
  storage; existing behavior remains unchanged for inline results
- **Pluggable backends**: Operators can configure their preferred storage
  backend (S3, GCS, OCI registry, Azure Blob, PVC)
- **Transparent resolution**: Downstream tasks can reference external results
  using the same syntax as inline results

## Motivation

Tekton Results are currently severely constrained by Kubernetes limitations:

1. **Termination Message Limit**: Results are stored via container termination
   messages, limited to 4KB per container and 12KB total per Pod across all
   containers.

2. **Container Count Impact**: The more Steps in a Task, the smaller
   each result can be. For example, with 12 containers in a pod, each
   container gets only ~1KB for its termination message.

3. **CRD Size Limit**: Even with TEP-0127's sidecar logs approach, results
   ultimately end up in the TaskRun status, subject to the ~1.5MB CRD size
   limit.

These limitations significantly impact real-world use cases:

- **Tekton Chains**: Signing multiple container images produces large lists
  of digest-pinned image references that exceed result limits
- **SBOM Generation**: Software Bill of Materials documents are typically
  10KB-10MB in size
- **Build Manifests**: Multi-architecture build manifests listing all produced
  artifacts
- **JSON API Responses**: Tasks that fetch or transform JSON data between steps

### Goals

1. Enable Tasks to produce results of arbitrary size without impacting TaskRun
   pod overhead
2. Provide a pluggable storage backend system that operators can configure
3. Maintain backward compatibility with existing inline results
4. Allow per-result opt-in to external storage
5. Ensure transparent resolution so downstream tasks can consume external
   results without special handling
6. Support integrity verification via content digests

### Non-Goals

1. Replacing Tekton Results project - this TEP focuses on inter-task result
   passing, not long-term storage and querying
2. Automatic result streaming or real-time result access during Task execution
3. Providing a general-purpose artifact storage system (use Workspaces for that)
4. Solving the termination message limit for inline results (that remains at 4KB)

### Use Cases

**Use Case 1: Multi-Image Build Pipeline (Konflux)**

A Task builds multiple container images and needs to pass the list of all
image references (with digests) to a signing Task. With 20+ images, the
result easily exceeds 4KB.

```yaml
# build-images Task
results:
  - name: IMAGES
    type: external
    description: JSON array of built image references with digests

# sign-images Task
params:
  - name: images
    value: $(tasks.build-images.results.IMAGES)
```

**Use Case 2: SBOM Generation**

A Task generates an SBOM in SPDX or CycloneDX format that needs to be
passed to an attestation Task.

```yaml
results:
  - name: sbom
    type: external
    description: SPDX SBOM document
```

**Use Case 3: Test Results Processing**

A test Task produces detailed JUnit XML output that needs to be processed
by a reporting Task.

```yaml
results:
  - name: junit-report
    type: external
    description: JUnit XML test results
```

### Requirements

**Must Have:**

1. **Backward Compatibility**: Existing Tasks and Pipelines must continue to
   work without modification
2. **Opt-in**: External storage must be explicitly requested per-result
3. **Configurable**: Operators must be able to configure storage backends
   at the cluster level
4. **Secure**: Credentials for storage backends must be handled securely
5. **Verifiable**: Result integrity must be verifiable via content digests
6. **Clear failure modes**: When external storage is not configured but
   `type: external` is used, the failure must be immediate and obvious

**Nice to Have (can be deferred):**

7. **Garbage Collection**: External results should be cleanable when TaskRuns
   are deleted. For MVP, operators can rely on storage lifecycle policies.
8. **Namespace-level configuration**: Per-namespace storage backend overrides

## Proposal

Introduce a new result type `external` that stores result content in a
configured external storage backend and stores only a reference (with digest)
in the TaskRun status.

The key components are:

1. **New Result Type**: `type: external` in Task spec
2. **Storage Backend Configuration**: Cluster-level ConfigMap for default
   backend, with optional namespace-level overrides
3. **Reference Storage**: TaskRun status stores a reference object instead
   of the full value
4. **Transparent Resolution**: The entrypoint binary and controller handle
   fetching external results when needed by downstream tasks
5. **Pluggable Provider Interface**: Go interface that storage providers
   implement

### Notes and Caveats

- External storage requires additional infrastructure (S3 bucket, GCS bucket,
  or OCI registry)
- Network latency for fetching external results may impact Pipeline execution
  time
- Storage credentials must be available to:
  - TaskRun pods (for uploading results via entrypoint)
  - Tekton Pipelines controller (for resolving results in downstream tasks)
  - External tools/services that consume results (e.g., Tekton Chains for
    attestation, Tekton Results for long-term storage)
- Tasks declaring `type: external` results will fail validation on clusters
  without external storage configured

## Design Details

### New Result Type: external

Tasks can declare results with `type: external`:

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-images
spec:
  results:
    - name: digest
      type: string           # inline, current behavior (default)
      description: Primary image digest
    - name: IMAGES
      type: external         # NEW: stored externally
      description: JSON array of all built images with digests
    - name: sbom
      type: external
      description: SPDX SBOM document
      properties:
        maxSize: 10Mi        # optional: hint for storage allocation
  steps:
    - name: build
      image: builder:latest
      script: |
        # Small result - written to inline result path
        echo -n "sha256:abc123..." > $(results.digest.path)

        # Large results - written to external result path (same API)
        cat images.json > $(results.IMAGES.path)
        cat sbom.spdx.json > $(results.sbom.path)
```

The Task author experience is identical - results are written to the same
paths. The difference is in how the entrypoint handles them.

### Behavior When External Storage Is Not Configured

A key design question is: what happens when a Task declares `type: external`
for a result, but the cluster has no external storage backend configured?

**Proposed behavior:**

1. **Validation at admission time**: When a Task or TaskRun with `type: external`
   results is submitted and the feature flag `enable-external-results` is not
   enabled or no backend is configured, the controller should reject the
   resource with a clear error message:

   ```
   Error: Task "build-images" declares external result "IMAGES" but external
   result storage is not configured. Either configure a storage backend in
   config-result-storage ConfigMap or change the result type to "string".
   ```

2. **Feature flag gating**: The `type: external` result type is only valid when
   the `enable-external-results` feature flag is set to `"true"`. This ensures
   Tasks using external results are only accepted on clusters that support them.

3. **Graceful degradation option** (future consideration): An optional
   `fallback-to-inline: "true"` configuration could allow external results to
   fall back to inline storage if the content is small enough. This would be
   useful during migration periods.

This approach ensures that:
- Tasks are portable: they clearly declare their requirements
- Failures are fast and obvious: no silent data loss or truncation
- Operators have clear guidance on what configuration is needed

### Storage Backend Configuration

Cluster-level default configuration via ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-result-storage
  namespace: tekton-pipelines
data:
  # Enable external result storage (default: "false")
  enabled: "true"

  # Default backend type: s3, gcs, oci, azure, pvc
  backend: "s3"

  # S3 configuration
  s3.bucket: "tekton-results"
  s3.region: "us-east-1"
  s3.endpoint: ""                    # optional, for MinIO/other S3-compatible
  s3.pathStyle: "false"              # set to "true" for MinIO
  s3.credentialsSecret: "tekton-results-s3-creds"

  # Key pattern for storing results
  # Available variables: {{namespace}}, {{taskrun}}, {{result}}
  keyPattern: "{{namespace}}/{{taskrun}}/{{result}}"
```

Alternative backend configurations:

```yaml
# GCS configuration
data:
  backend: "gcs"
  gcs.bucket: "tekton-results"
  gcs.credentialsSecret: "tekton-results-gcs-creds"
  gcs.credentialsKey: "service-account.json"

# OCI Registry configuration
data:
  backend: "oci"
  oci.registry: "registry.example.com"
  oci.repository: "tekton/results"
  oci.credentialsSecret: "tekton-results-oci-creds"

# Azure Blob configuration
data:
  backend: "azure"
  azure.container: "tekton-results"
  azure.accountName: "tektonresults"
  azure.credentialsSecret: "tekton-results-azure-creds"
```

### Namespace-Level Configuration

In addition to cluster-level defaults, operators may want to configure
different storage backends per namespace. This is particularly useful in
multi-tenant environments where different teams have different storage
requirements or credentials.

Namespace-level configuration follows the patterns established in
[TEP-0085: Per-Namespace Controller Configuration](https://github.com/tektoncd/community/blob/main/teps/0085-per-namespace-controller-configuration.md).

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-result-storage
  namespace: team-a  # Namespace-specific override
  labels:
    tekton.dev/config-type: result-storage
data:
  backend: "oci"
  oci.registry: "team-a-registry.example.com"
  oci.repository: "tekton/results"
  oci.credentialsSecret: "team-a-registry-creds"
```

The controller resolves configuration in the following order:
1. Namespace-level ConfigMap (if exists)
2. Cluster-level ConfigMap in `tekton-pipelines` namespace
3. Built-in defaults (external results disabled)

### TaskRun Status with References

When a TaskRun completes with external results, the status contains references:

```yaml
apiVersion: tekton.dev/v1
kind: TaskRun
metadata:
  name: build-images-run-abc123
spec:
  taskRef:
    name: build-images
status:
  conditions:
    - type: Succeeded
      status: "True"
  results:
    # Inline result - stored directly
    - name: digest
      type: string
      value: "sha256:abc123def456..."

    # External result - reference only
    - name: IMAGES
      type: external
      ref:
        backend: s3
        bucket: tekton-results
        key: "default/build-images-run-abc123/IMAGES"
        digest: "sha256:789xyz..."
        size: 45678
        contentType: "application/json"

    # Another external result
    - name: sbom
      type: external
      ref:
        backend: s3
        bucket: tekton-results
        key: "default/build-images-run-abc123/sbom"
        digest: "sha256:def789..."
        size: 2457600
        contentType: "application/spdx+json"
```

### Transparent Resolution for Downstream Tasks

Downstream tasks reference external results using the standard syntax:

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
      params:
        - name: images
          # Same syntax - controller resolves external reference
          value: $(tasks.build.results.IMAGES)
      runAfter:
        - build

    - name: attest
      taskRef:
        name: create-attestation
      params:
        - name: sbom
          value: $(tasks.build.results.sbom)
      runAfter:
        - build
```

The PipelineRun controller:

1. Detects that `$(tasks.build.results.IMAGES)` references an external result
2. Injects an init container to fetch the content from storage
3. Substitutes the result reference with the file path where content is available

### Init Container Injection for External Results

All external results use an init container approach for downstream resolution.
This provides a consistent, simple model: `type: external` results are always
file-based, while `type: string` results remain inline.

**How it works:**

1. **Init container injection**: The controller injects an init container into
   downstream TaskRun pods that:
   - Fetches the external result content from storage
   - Writes it to a shared emptyDir volume at a well-known path
   - Verifies the content digest matches the reference

2. **File path substitution**: The controller substitutes result references
   with file paths:

   ```yaml
   # Original parameter reference
   value: $(tasks.build.results.sbom)

   # Becomes
   value: /tekton/results/external/build/sbom
   ```

3. **Well-known path structure**: External results are available at:
   ```
   /tekton/results/external/<task-name>/<result-name>
   ```

**Why always use init containers (no size threshold):**

- **Simplicity**: One code path instead of branching based on size
- **Consistency**: All external results behave the same way
- **No tuning**: No threshold to configure or optimize
- **Clear mental model**: `type: external` = file-based, `type: string` = inline
- **Future-proof**: Results can grow without changing behavior

If a result is small enough to be inline, it should use `type: string`.
Declaring `type: external` is an explicit signal that file-based handling
is appropriate.

### Pipeline-Level Result Declarations

Pipelines can declare results that reference Task results. When a Task result
is declared as `type: external`, the Pipeline result can also be declared as
external:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-and-sign
spec:
  results:
    - name: images
      type: external  # Pipeline result is also external
      value: $(tasks.build.results.IMAGES)
    - name: digest
      type: string    # Inline result from task
      value: $(tasks.build.results.digest)
  tasks:
    - name: build
      taskRef:
        name: build-images
```

**Behavior:**

- When a Pipeline result references an external Task result with
  `type: external`, the PipelineRun status stores the same reference
  (no re-upload needed).

- When a Pipeline result references an external Task result with
  `type: string` (inline), the controller fetches the external content
  and stores it inline in the PipelineRun status (subject to size limits).

- Attempting to declare a Pipeline result as `type: string` when referencing
  a very large external Task result will fail with a clear error message.

### Integration with External Tools and Services

External results must be accessible not only to the Tekton controller but
also to other tools and services in the Tekton ecosystem that consume
TaskRun results.

**Tekton Chains Integration:**

[Tekton Chains](https://github.com/tektoncd/chains) monitors TaskRun
completions and creates attestations based on results. For external results:

1. Chains must have access to the same storage credentials as the controller
2. Chains uses the `ResultRef` to fetch content for attestation
3. The digest in the reference can be included in the attestation without
   fetching the full content (for provenance)

**Credential Sharing:**

Storage credentials must be available to:
- TaskRun pods (for uploading results via entrypoint)
- Tekton Pipelines controller (for resolving results in downstream tasks)
- Tekton Chains controller (for creating attestations)
- Tekton Results (for long-term storage and querying)
- Any other tools that need to access result content

The recommended approach is to use a shared Secret that all components
can access, or workload identity (IRSA, GKE Workload Identity) where
credentials are derived from ServiceAccount annotations.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tekton-results-storage-creds
  namespace: tekton-pipelines
  annotations:
    # Used by controller, chains, and entrypoint
    tekton.dev/credential-scope: "result-storage"
type: Opaque
data:
  # Credentials shared across components
  access-key: ...
  secret-key: ...
```

### Storage Provider Interface

```go
package resultstorage

import (
    "context"
    "io"
)

// ResultRef contains the reference to an externally stored result
type ResultRef struct {
    Backend     string `json:"backend"`
    Bucket      string `json:"bucket,omitempty"`
    Key         string `json:"key"`
    Digest      string `json:"digest"`
    Size        int64  `json:"size"`
    ContentType string `json:"contentType,omitempty"`
}

// Provider defines the interface for result storage backends
type Provider interface {
    // Name returns the provider identifier (s3, gcs, oci, azure, pvc)
    Name() string

    // Store writes result content and returns a reference
    Store(ctx context.Context, key string, content io.Reader, opts StoreOptions) (*ResultRef, error)

    // Fetch retrieves result content by reference
    Fetch(ctx context.Context, ref *ResultRef) (io.ReadCloser, error)

    // Delete removes stored result (for garbage collection)
    Delete(ctx context.Context, ref *ResultRef) error

    // Exists checks if a result exists
    Exists(ctx context.Context, ref *ResultRef) (bool, error)
}

// StoreOptions contains options for storing a result
type StoreOptions struct {
    ContentType string
    Metadata    map[string]string
}

// ProviderConfig contains configuration for initializing a provider
type ProviderConfig struct {
    Backend     string
    Credentials CredentialsSource
    Options     map[string]string
}

// CredentialsSource defines where to get storage credentials
type CredentialsSource struct {
    SecretRef *SecretKeySelector
    // Future: ServiceAccount for workload identity
}
```

### Supported Backends

**Phase 1 (MVP):**
- S3 (via `gocloud.dev/blob/s3blob`)
- OCI Registry (via `oras.land/oras-go/v2`)
- PVC (local storage, no external infrastructure needed)

**Phase 2:**
- GCS (via `gocloud.dev/blob/gcsblob`)
- Azure Blob (via `gocloud.dev/blob/azureblob`)

**Phase 3:**
- Custom (webhook-based for extensibility)

### Garbage Collection

External results consume storage that should be cleaned up when no longer
needed. This section describes the garbage collection strategy.

**Note:** Garbage collection is considered a **nice-to-have for initial
implementation**. The MVP can rely on external storage lifecycle policies
(e.g., S3 bucket lifecycle rules) or manual cleanup. Automated garbage
collection can be added in a later phase.

**Proposed approaches (for future implementation):**

1. **Finalizer-based cleanup**: Add a finalizer to TaskRuns with external
   results. When the TaskRun is deleted, the controller deletes the
   associated external result objects before removing the finalizer.

   ```yaml
   metadata:
     finalizers:
       - results.tekton.dev/external-cleanup
   ```

2. **Background garbage collector**: A separate controller or CronJob that:
   - Lists all external result references in storage
   - Checks if the corresponding TaskRun still exists
   - Deletes orphaned results after a grace period

3. **TTL-based expiration**: Configure storage backend with automatic
   expiration (e.g., S3 lifecycle policies, OCI tag expiration). Results
   are automatically deleted after a configurable period.

4. **Integration with Tekton Results**: When Tekton Results is deployed,
   external result references can be migrated to Results storage before
   TaskRun deletion, preserving data for historical queries.

**Recommendation for MVP:** Document that operators should configure
storage lifecycle policies for automatic cleanup, and implement
finalizer-based cleanup in Phase 2 or 3.

## Design Evaluation

### Reusability

This proposal builds on existing patterns:
- URI scheme pattern from [tekton-caches](https://github.com/openshift-pipelines/tekton-caches)
- Storage abstraction from [go-cloud/blob](https://github.com/google/go-cloud)
- Artifact pattern from [Argo Workflows](https://argo-workflows.readthedocs.io/en/latest/walk-through/artifacts/)

The storage provider interface can be reused by other Tekton components
(e.g., Tekton Results project, Tekton Chains).

### Simplicity

**Current Experience (without feature):**
- Users hit 4KB/12KB limits unexpectedly
- Workarounds: use Workspaces (requires PVC), split results, compress data
- Sidecar logs approach adds overhead to every TaskRun

**With Feature:**
- Declare `type: external` on results that may be large
- Configure storage backend once at cluster level
- Same result writing API (`echo > $(results.name.path)`)
- Same result reference syntax (`$(tasks.x.results.y)`)

### Flexibility

- Pluggable backends allow operators to use existing infrastructure
- OCI registry backend works in environments with only registry access
- PVC backend (Phase 3) requires no external infrastructure
- Per-result opt-in means users control which results use external storage

### Conformance

- Extends existing Results API with new type
- Does not require understanding Kubernetes internals
- API changes are additive and backward compatible
- Results syntax remains consistent

### User Experience

**Task Authors:**
- Add `type: external` to large result declarations
- Same file-based result writing API

**Pipeline Authors:**
- No changes - same `$(tasks.x.results.y)` syntax

**Operators:**
- Configure `config-result-storage` ConfigMap once
- Manage storage backend credentials

### Performance

**Positive Impact:**
- No sidecar container overhead on every TaskRun
- Large results don't bloat etcd/API server

**Potential Impact:**
- Network latency when fetching external results for downstream tasks
- Storage backend availability affects Pipeline reliability

**Mitigations:**
- Content-addressable references enable caching
- Parallel fetching for multiple external results in a single init container
- Init container startup overhead is minimal compared to result fetch time

### Risks and Mitigations

| Risk                                    | Mitigation                                                         |
|-----------------------------------------|--------------------------------------------------------------------|
| Storage backend unavailable             | Graceful degradation with clear error messages; retry with backoff |
| Credential management complexity        | Support workload identity (IRSA, GKE WI); clear documentation      |
| Orphaned results after TaskRun deletion | Garbage collection via finalizers or async cleanup job             |
| Large result fetching latency           | Caching layer; parallel fetch; optional streaming                  |

### Drawbacks

1. **External Infrastructure Required**: Unlike sidecar logs, this requires
   additional infrastructure (S3 bucket, registry, etc.)

2. **Credential Management**: Storage credentials must be configured and
   maintained

3. **Network Dependency**: Result resolution depends on network access to
   storage backend

4. **Debugging Complexity**: Results are not directly visible in TaskRun status

## Alternatives

### TEP-0127: Sidecar Logs

**Approach**: Inject a sidecar container that monitors result files and emits
them via stdout; controller reads from pod logs.

**Why Not Chosen**:
- Creates sidecar on EVERY TaskRun (resource overhead)
- ~3 second startup time increase per TaskRun
- Cluster-wide only, no per-Task opt-in
- Results still end up in TaskRun status (~1.5MB CRD limit)
- Controller needs pod logs access (security concern)
- [Issue #8448](https://github.com/tektoncd/pipeline/issues/8448) requests selective enablement

### ConfigMaps per TaskRun

**Approach**: Create a ConfigMap for each TaskRun to store results, then
copy to TaskRun status.

**Why Not Chosen**:
- RBAC complexity (controller needs permission to create roles/bindings)
- Still limited to ~1.5MB per ConfigMap
- API server load (3+ requests per TaskRun)
- Cleanup complexity

### Custom CRD for Results

**Approach**: Store results in dedicated TaskRunResult CRD.

**Why Not Chosen**:
- Still subject to ~1.5MB CRD limit
- Introduces new resource type to manage
- Additional API server load

### Workspaces Only

**Approach**: Document that large data should use Workspaces, no changes needed.

**Why Not Chosen**:
- Requires separate storage infrastructure
- Changes how users think about results vs files
- Requires Task modifications to read from workspace paths
- Breaks task library patterns
- Incompatible with no-code/low-code abstractions

## Implementation Plan

### Phase 1: Core Infrastructure (Alpha)

1. Define `ResultRef` types in API
2. Implement `Provider` interface
3. Implement S3 provider using `gocloud.dev/blob`
4. Implement OCI provider using ORAS
5. Add `config-result-storage` ConfigMap handling
6. Modify entrypoint to upload external results
7. Feature flag: `enable-external-results: "true"`
8. Modify TaskRun reconciler to handle external result references
9. Init container injection for downstream result resolution
10. Implement result resolution for PipelineRun
11. Validation: reject `type: external` when storage not configured
12. E2E tests with S3 and OCI backends
13. Document storage lifecycle policies for cleanup (defer automated GC)

### Phase 2: Additional Backends and Features (Beta)

1. Implement GCS provider
2. Implement Azure Blob provider
3. Implement PVC provider
4. Namespace-level configuration overrides (per TEP-0085 patterns)
5. Garbage collection via finalizers
6. Pipeline-level external result declarations
7. Tekton Chains integration testing
8. Promote to beta

### Phase 3: Production Ready (Stable)

1. Caching layer for frequently accessed results
2. Metrics and observability
3. Integration with Tekton Results project
4. Background garbage collector for orphaned results
5. Promote to stable

### Test Plan

- Unit tests for each storage provider
- Integration tests with mock storage
- E2E tests with real storage backends (S3/MinIO, OCI registry)
- Performance benchmarks comparing inline vs external results
- Failure mode testing (storage unavailable, credentials expired, etc.)

### Infrastructure Needed

- CI/CD access to test storage backends (MinIO for S3, local registry for OCI)
- Documentation updates for configuration
- Example Tasks demonstrating external results

### Upgrade and Migration Strategy

- Feature is opt-in via result type declaration
- No migration needed for existing Tasks/Pipelines
- Feature flag allows gradual rollout
- Existing inline results continue to work unchanged

### Implementation Pull Requests

<!-- To be filled as implementation progresses -->

## References

- [TEP-0085: Per-Namespace Controller Configuration](https://github.com/tektoncd/community/blob/main/teps/0085-per-namespace-controller-configuration.md)
- [TEP-0086: Changing the Way Result Parameters are Stored](https://github.com/tektoncd/community/blob/main/teps/0086-changing-the-way-result-parameters-are-stored.md)
- [TEP-0127: Larger Results via Sidecar Logs](https://github.com/tektoncd/community/blob/main/teps/0127-larger-results-via-sidecar-logs.md)
- [Issue #4012: Changing the way Result Parameters are stored](https://github.com/tektoncd/pipeline/issues/4012)
- [Issue #4808: Results, TerminationMessage and Containers](https://github.com/tektoncd/pipeline/issues/4808)
- [Issue #8448: Enable larger results without a sidecar on every TaskRun](https://github.com/tektoncd/pipeline/issues/8448)
- [Argo Workflows Artifacts](https://argo-workflows.readthedocs.io/en/latest/walk-through/artifacts/)
- [tekton-caches: Pluggable storage backends](https://github.com/openshift-pipelines/tekton-caches)
- [go-cloud/blob: Multi-cloud storage abstraction](https://github.com/google/go-cloud/tree/master/blob)
- [ORAS: OCI Registry As Storage](https://oras.land/)
- [Tekton Results Project](https://github.com/tektoncd/results)
- [Tekton Chains](https://github.com/tektoncd/chains)
