---
status: proposed
title: Tekton Kueue Integration
creation-date: '2026-01-28'
last-updated: '2026-01-28'
authors:
- '@gbenhaim'
collaborators: []
see-also:
- TEP-0132
---

# TEP-0164: Tekton Kueue Integration

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
  - [Architecture Overview](#architecture-overview)
  - [Key Components](#key-components)
  - [Configuration](#configuration)
  - [CEL Expressions](#cel-expressions)
  - [MultiKueue Support](#multikueue-support)
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
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes the adoption of [tekton-kueue](https://github.com/konflux-ci/tekton-kueue) into the Tekton community. tekton-kueue is a controller that integrates Tekton with [Kueue](https://kueue.sigs.k8s.io/), enabling Kueue to manage the scheduling and queueing of Tekton PipelineRuns.

This project directly addresses the requirements for PipelineRuns outlined in [TEP-0132: Queueing Concurrent Runs](./0132-queueing-concurrent-runs.md) by providing:

- Concurrency control for PipelineRuns through Kueue's quota management
- Resource-aware scheduling using Kueue's ResourceFlavors and ClusterQueues
- Support for "fire and forget" execution patterns where many PipelineRuns can be created without overwhelming the cluster
- Integration with MultiKueue for multi-cluster workload distribution

tekton-kueue leverages Kueue, a Kubernetes-native job queueing system that is part of the Kubernetes SIG Scheduling ecosystem, providing a robust and well-maintained foundation for workload management.

## Motivation

[TEP-0132: Queueing Concurrent Runs](./0132-queueing-concurrent-runs.md) identified a significant gap in Tekton's capabilities: the lack of native support for controlling the number of PipelineRuns and TaskRuns that can run concurrently. This limitation leads to several problems:

1. **Cluster overload**: Running many PipelineRuns in parallel can overwhelm cluster resources, potentially making the cluster unresponsive
2. **No "fire and forget" capability**: Users cannot create many PipelineRuns knowing they will be queued and executed in a controlled manner
3. **Resource contention**: Without proper queueing, PipelineRuns compete for resources unpredictably
4. **Rate limiting concerns**: PipelineRuns communicating with rate-limited external services may exceed quotas

tekton-kueue addresses these challenges by integrating Tekton with Kueue, a project specifically designed for Kubernetes-native job queueing and quota management. Rather than implementing queueing logic from scratch within Tekton, this approach leverages an established, well-maintained project that the broader Kubernetes community uses for similar workload management needs.

### Goals

1. **Adopt tekton-kueue** as a Tekton community project to provide queueing capabilities for PipelineRuns
2. **Enable Kueue-based scheduling** of Tekton PipelineRuns through a dedicated controller and admission webhook
3. **Support resource quota management** allowing cluster administrators to control concurrent PipelineRun execution
4. **Provide flexible queuing configuration** through CEL expressions for dynamic mutation of PipelineRuns
5. **Support multi-cluster scenarios** through integration with MultiKueue

### Non-Goals

1. **Queueing at the TaskRun level**: The initial scope focuses on PipelineRun queueing only
2. **Priority and preemption of queued runs**: While Kueue supports priority, advanced preemption strategies are not in scope for initial adoption
4. **Modifying Tekton Pipelines core**: tekton-kueue operates as a separate controller without requiring changes to tekton/pipeline

### Use Cases

The following use cases are addressed by tekton-kueue, directly mapping to those identified in TEP-0132:

1. **Controlling load on a cluster**
   - A cluster operator wants to limit the total number of PipelineRuns that can execute concurrently across all namespaces
   - Multiple teams share a cluster and need fair resource allocation through quota management

2. **Fire and forget execution**
   - A CI system creates hundreds of PipelineRuns in response to webhook events; these should be queued and executed as resources become available
   - Developers can submit many builds knowing they will be processed in order without overwhelming the cluster

3. **Rate-limited external services**
   - PipelineRuns that communicate with rate-limited APIs (e.g., package registries for SBOM generation) need throttling to avoid exceeding quotas
   - Integration tests that interact with shared external services require controlled concurrency

4. **Resource-constrained environments**
   - Teams with limited compute resources (e.g., specialized hardware, test devices) need to queue PipelineRuns for those resources
   - Cloud cost optimization by limiting concurrent resource-intensive workloads

5. **Multi-cluster workload distribution**
   - Organizations with multiple Kubernetes clusters want to distribute PipelineRuns across clusters based on capacity and locality

### Requirements

1. **Kubernetes-native**: The solution must work with standard Kubernetes primitives and be deployable via standard methods (kubectl, kustomize)
2. **Non-invasive**: Must not require modifications to existing PipelineRun definitions or the Tekton Pipelines controller
3. **Observable**: Must expose metrics for monitoring queueing behavior and performance
4. **Configurable**: Must support both cluster-wide defaults and namespace-specific overrides
5. **Extensible**: Must allow custom logic through CEL expressions for dynamic configuration

## Proposal

We propose adopting tekton-kueue as a Tekton community project. The project provides a controller and admission webhook that integrates Tekton PipelineRuns with Kueue's workload management system.

The core workflow is:

1. When a PipelineRun is created, the admission webhook intercepts it and:
   - Adds a label associating the PipelineRun with a Kueue LocalQueue
   - Sets the PipelineRun status to `Pending` to prevent immediate execution
   - Applies any configured mutations (annotations, labels, priority) via CEL expressions
   - Creates resource request annotations based on configuration

2. The tekton-kueue controller:
   - Creates a Kueue Workload resource for each pending PipelineRun
   - Monitors the Workload's admission status
   - When Kueue admits the Workload, updates the PipelineRun to allow execution
   - Handles PipelineRun completion by updating the corresponding Workload

3. Kueue manages the actual queueing and quota enforcement:
   - Maintains ClusterQueues with resource quotas
   - Admits Workloads based on available capacity
   - Handles fair queueing across namespaces via LocalQueues

### Notes and Caveats

1. **Kueue Dependency**: tekton-kueue requires Kueue to be installed on the cluster. Kueue is a mature CNCF project with an active community.

2. **External Framework Registration**: Kueue must be configured to recognize `pipelineruns.tekton.dev` as an external framework.

3. **Current Maturity**: tekton-kueue is currently used in production by Konflux CI. The project has:
   - Unit tests covering core functionality
   - End-to-end tests validating integration with Kueue
   - Active maintenance and issue tracking

4. **Version Compatibility**: Currently supports Kueue v0.14.x and Tekton Pipelines v1.6.x

## Design Details

### Architecture Overview

tekton-kueue consists of three main components:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                        │
│                                                                  │
│  ┌──────────────┐    ┌───────────────────┐    ┌──────────────┐ │
│  │  PipelineRun │───▶│ Admission Webhook │───▶│  PipelineRun │ │
│  │   (created)  │    │  (mutates PLR)    │    │  (pending)   │ │
│  └──────────────┘    └───────────────────┘    └──────┬───────┘ │
│                                                       │         │
│                      ┌────────────────────────────────┘         │
│                      ▼                                          │
│  ┌──────────────────────────────────┐                          │
│  │      tekton-kueue Controller      │                          │
│  │  - Creates Workload for each PLR │                          │
│  │  - Monitors Workload admission   │                          │
│  │  - Updates PLR when admitted     │                          │
│  └──────────────┬───────────────────┘                          │
│                 │                                               │
│                 ▼                                               │
│  ┌──────────────────────────────────┐                          │
│  │           Kueue                   │                          │
│  │  - ClusterQueue (quotas)         │                          │
│  │  - LocalQueue (namespace binding)│                          │
│  │  - Workload (admission tracking) │                          │
│  └──────────────────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

**Admission Webhook**
- Intercepts PipelineRun creation requests
- Adds `kueue.x-k8s.io/queue-name` label to associate with a LocalQueue
- Sets PipelineRun to pending state (`spec.status: PipelineRunPending`)
- Applies CEL-based mutations for annotations, labels, and priority
- Creates resource request annotations

**Controller**
- Watches PipelineRuns with the Kueue queue label
- Creates corresponding Kueue Workload resources
- Monitors Workload admission status
- Updates PipelineRun status when admitted by Kueue
- Cleans up Workloads when PipelineRuns complete

**ConfigMap-based Configuration**
- Global settings via `tekton-kueue-config` ConfigMap
- CEL expressions for dynamic mutation logic
- Support for MultiKueue mode

### Configuration

Configuration is managed through a ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tekton-kueue-config
  namespace: tekton-kueue-system
data:
  config.yaml: |
    queueName: "pipelines-queue"
    multiKueueOverride: false
    cel:
      expressions:
        - 'annotation("tekton.dev/mutated-by", "tekton-kueue")'
        - 'label("environment", "production")'
        - 'priority("high")'
        - 'resource("compute-intensive", 2)'
```

**Resource Requests**

By default, tekton-kueue adds a `tekton.dev/pipelineruns` resource with value 1 to each Workload. This enables controlling concurrent PipelineRun count. Additional resources can be specified via:

- Annotations on PipelineRuns (`kueue.konflux-ci.dev/requests-cpu`, etc.)
- CEL expressions using the `resource()` function

### CEL Expressions

tekton-kueue supports CEL (Common Expression Language) for dynamic PipelineRun mutation:

**Available Variables:**
- `pipelineRun`: The complete PipelineRun object
- `plrNamespace`: Shorthand for the PipelineRun namespace
- `pacEventType`: Pipelines as Code event type label value
- `pacTestEventType`: Integration test event type label value

**Available Functions:**
- `annotation(key, value)`: Set an annotation
- `label(key, value)`: Set a label
- `priority(value)`: Set Kueue priority class
- `resource(key, value)`: Add a resource request (values are summed for duplicates)

**Example:**

```yaml
cel:
  expressions:
    # Conditional priority based on namespace
    - 'priority(plrNamespace == "production" ? "high" : "low")'

    # Dynamic resource allocation
    - 'resource("gpu", plrNamespace == "ml-training" ? 4 : 1)'

    # Multiple mutations in one expression
    - |
      [
        annotation("tekton.dev/queue-time", "2026-01-01T00:00:00Z"),
        label("team", "platform"),
        priority("medium")
      ]
```

### MultiKueue Support

For multi-cluster deployments, tekton-kueue supports MultiKueue:

```yaml
data:
  config.yaml: |
    multiKueueOverride: true
```

When enabled, the webhook sets `spec.managedBy` to `kueue.x-k8s.io/multikueue`, allowing MultiKueue to distribute PipelineRuns across worker clusters.

## Design Evaluation

### Reusability

- **Leverages existing ecosystem**: Uses Kueue, a well-established Kubernetes project, rather than building queueing from scratch
- **Non-invasive design**: Existing Tasks and Pipelines work without modification
- **Catalog compatibility**: PipelineRuns using Catalog tasks work seamlessly with queueing

### Simplicity

- **Single responsibility**: tekton-kueue focuses solely on the integration between Tekton and Kueue
- **Minimal configuration**: Works with sensible defaults; advanced configuration is optional
- **Standard Kubernetes patterns**: Uses admission webhooks and controllers, familiar patterns for Kubernetes operators

### Flexibility

- **CEL expressions**: Powerful customization without requiring code changes
- **Configurable at multiple levels**: Global defaults, namespace overrides, per-PipelineRun annotations
- **Extensible resource model**: Custom resource types can be defined for any use case
- **MultiKueue support**: Scales to multi-cluster scenarios

### Conformance

- **No API changes to Tekton**: Works with existing PipelineRun API
- **Platform agnostic queueing logic**: Kueue handles the queueing, which could theoretically work with other Tekton implementations
- **Standard Kubernetes primitives**: Uses labels, annotations, and ConfigMaps for configuration

### User Experience

**Before tekton-kueue:**
- Creating many PipelineRuns risks overwhelming the cluster
- No visibility into queued vs running PipelineRuns
- Manual rate limiting required

**After tekton-kueue:**
- PipelineRuns are automatically queued and admitted based on available capacity
- Kueue provides visibility via Workload resources and ClusterQueue status
- Fire-and-forget execution model works naturally

**CLI Integration:**
The `tekton-kueue mutate` subcommand allows testing CEL expressions locally before deployment:

```sh
tekton-kueue mutate --pipelinerun-file pr.yaml --config-dir config/
```

### Performance

- **Minimal overhead**: Admission webhook adds milliseconds to PipelineRun creation
- **Efficient reconciliation**: Controller uses informers and work queues following controller-runtime best practices
- **Kueue scalability**: Kueue is designed for large-scale workload management

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Kueue dependency creates coupling | Kueue is a widely adopted project with long-term support; the integration is loosely coupled via Workload resources |
| Admission webhook becomes bottleneck | Webhook is stateless and horizontally scalable |
| Configuration errors cause PipelineRuns to hang | Comprehensive validation of CEL expressions; metrics for monitoring |
| Kueue version compatibility | Clear documentation of supported versions; testing across Kueue releases |

### Drawbacks

1. **Additional component to deploy and maintain**: Organizations must manage tekton-kueue alongside Tekton and Kueue
2. **Learning curve**: Operators need to understand Kueue concepts (ClusterQueue, LocalQueue, ResourceFlavor)
3. **Kueue dependency**: Requires Kueue to be installed and properly configured

## Alternatives

1. **Native Tekton queueing**: Implement queueing directly in the Tekton Pipelines controller
   - Rejected because: Significant complexity addition to core; Kueue already solves this well

2. **Kubernetes Resource Quotas**: Use standard ResourceQuota for limiting PipelineRuns
   - Rejected because: Quotas don't provide queueing; excess PipelineRuns are rejected, not queued

3. **Custom admission controller without Kueue**: Build a standalone queueing system
   - Rejected because: Reinventing existing functionality; maintenance burden

4. **External orchestration**: Use an external system (e.g., Argo Events, Temporal) for queueing
   - Rejected because: Additional complexity; tight coupling to external systems

## Implementation Plan

tekton-kueue is already implemented and used in production. The adoption plan focuses on:

1. **Phase 1: Community Review and Adoption**
   - Present project at Tekton working group meetings
   - This TEP review and approval
   - Transfer repository to tektoncd organization

2. **Phase 2: Infrastructure Setup**
   - Set up CI/CD in tektoncd/plumbing
   - Configure release automation
   - Set up documentation on tekton.dev

3. **Phase 3: Documentation and Outreach**
   - Create user guides and tutorials
   - Add examples to tektoncd/catalog
   - Blog post announcing availability

### Test Plan

The project currently has:

- **Unit tests**: Coverage of core controller and webhook logic
- **End-to-end tests**: Validation of PipelineRun queueing with Kueue
- **Integration tests**: Testing CEL expression evaluation and mutation

Post-adoption, we will:
- Integrate with Tekton's test infrastructure
- Add conformance tests for Kueue version compatibility
- Expand e2e coverage for edge cases

### Infrastructure Needed

1. **Repository**: `tektoncd/tekton-kueue` (transferred from `konflux-ci/tekton-kueue`)
2. **CI/CD**: Prow jobs in tektoncd/plumbing for testing and releases
3. **Container Registry**: Images published to gcr.io/tekton-releases
4. **Documentation**: Section on tekton.dev for tekton-kueue

### Upgrade and Migration Strategy

For existing tekton-kueue users:

1. **Image migration**: Update deployments to use tektoncd images
2. **No API changes**: Configuration format remains compatible
3. **Gradual rollout**: Can run alongside existing deployment during migration

### Implementation Pull Requests

The implementation already exists at:
- https://github.com/konflux-ci/tekton-kueue

Post-adoption PRs will be tracked in the new tektoncd repository.

## References

**Related TEPs:**
- [TEP-0132: Queueing Concurrent Runs](./0132-queueing-concurrent-runs.md)
- [TEP-0120: Canceling Concurrent PipelineRuns](./0120-canceling-concurrent-pipelineruns.md)
- [TEP-0092: Scheduling Timeout](./0092-scheduling-timeout.md)

**External Documentation:**
- [Kueue Documentation](https://kueue.sigs.k8s.io/docs/)
- [tekton-kueue Repository](https://github.com/konflux-ci/tekton-kueue)
- [Kueue External Frameworks](https://kueue.sigs.k8s.io/docs/concepts/workload/)

**Feature Requests (from TEP-0132):**
- [Concurrency limiter controller](https://github.com/tektoncd/experimental/issues/699)
- [Tekton Queue. Concurrency](https://github.com/tektoncd/pipeline/issues/5835)
- [Ability to throttle concurrent TaskRuns](https://github.com/tektoncd/pipeline/issues/4903)
- [Controlling max parallel jobs per Pipeline](https://github.com/tektoncd/pipeline/issues/2591)
- [Provide a Pipeline concurrency limit](https://github.com/tektoncd/pipeline/issues/1305)

**Similar Features in Other Systems:**
- [GitHub Actions concurrency controls](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency)
- [GitLab Runner concurrency](https://docs.gitlab.com/runner/configuration/advanced-configuration.html#the-global-section)
- [Pipelines as Code concurrency limit](https://pipelinesascode.com/docs/guide/repositorycrd/#concurrency)
