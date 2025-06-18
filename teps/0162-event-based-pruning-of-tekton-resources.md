---
status: proposed
title: event based pruning of tekton resources
creation-date: '2025-06-18'
last-updated: '2025-06-18'
authors:
- '@@anithapriyanatarajan'
collaborators:
- '@@jkandasa'
- '@@pramodbindal'
---

# TEP-0162: event based pruning of tekton resources
---


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
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
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

This proposal introduces a new `event-driven pruning controller` for Tekton that automatically cleans up completed `PipelineRun` and `TaskRun` resources. The controller monitors completed PipelineRuns and TaskRuns(including both successful and failed ones) and deletes them based on pruning configurations defined by the user.

It supports cleanup based on:

- **Time-to-live (TTL)**: How long to keep a resource after it finishes in seconds

- **History limits**: How many successful and failed runs to keep

The pruning behavior can be configured at different levels, following a clear priority order listed below from lowest to highest:

- **Cluster level** – Default settings for the entire cluster

- **Namespace level** – Overrides for specific namespaces

- **Resource group level** – Based on labels & annotations

The controller reads and applies pruning configurations from `ConfigMaps`, giving users a simple and consistent way to manage cleanup settings.

## Motivation

Current pruning mechanisms in Tekton are distributed across multiple components, each with its own limitations. Here's a summary of the existing options:

- **Operator-based pruner**:
A CronJob-based solution that runs in the `tekton-pipelines` namespace. It periodically launches a pod that uses the `tkn` CLI to delete `PipelineRun` and `TaskRun` resources across all namespaces.
If users want namespace-specific pruning policies, they must add annotations to the namespace, which results in additional CronJobs being created per namespace.

- **Tekton Results**:
Performs cleanup after exporting data by using finalizers, but it does not support time-based TTL or history limit based granular retention policies.

These approaches are fragmented, difficult to customize, and do not offer fine-grained control. Introducing a unified pruning controller brings all pruning logic into a single, consistent component—making it easier for users and administrators to manage resource cleanup.

### Goals

Implement an **event-based pruning mechanism** for `PipelineRun` and `TaskRun`.

Support:

- Time-based pruning using `ttlSecondsAfterFinished`

- History-based pruning using `successfulHistoryLimit`, `failedHistoryLimit`, or a combined `historyLimit`

Allow hierarchical configuration:

- Global defaults

- Namespace-level overrides

- Resource-group level matching via labels,annotations

Deliver declarative pruning configuration options through `ConfigMaps`.


### Non-Goals

- Removing finalizers set by other controllers (e.g., Tekton Results). The pruning controller will set the deletion time stamp as per settings on identfieid resources but it will not attempt to remove finalizers that prevent the PipelineRun or TaskRun from deletion.

- Pruning of unrelated custom resources.The scope is limited strictly to PipelineRun and TaskRun resources.

### Use Cases

If the proposed event-driven Pruner Controller is implemented, different user groups will benefit in the following ways:

1. **Cluster Administrators**

- **Centralized management**: Can define cluster-wide retention policies using a ConfigMap in the tekton-pipelines namespace.

- **Reduced operational burden**: Automatic pruning reduces etcd pressure and avoids resource clutter that could affect API performance.

2. **Namespace Owners / Platform Engineers**

- **Per-namespace control**: Define custom TTLs and history limits specific to their team’s workloads without needing elevated permissions.

3. **Pipeline Authors / Task Authors**

- **Faster iteration**: Reduced clutter in the Tekton dashboard or CLI improves usability and discoverability of recent runs.

- **Cleaner environments**: Eliminates noise from outdated runs, making it easier to debug and observe current pipeline behavior.

### Requirements

1. The pruner must operate efficiently and scale well in large Tekton clusters.

2. Resource cleanup must only occur after a PipelineRun or TaskRun is fully completed (either succeeded or failed).

3. The controller must not remove resources with active finalizers from other systems (e.g., Results).

4. The configuration system must support a hierarchical priority:

- Cluster level (lowest priority – default fallback)
- Namespace level
- Resource group level (labels/annotations/names)
- Individual resource level (highest priority)

If multiple levels define overlapping rules, the highest-priority match wins.

5. Users can enforce a specific configuration level using the `enforcedConfigLevel` flag to prevent lower-priority overrides.

6. Invalid or malformed configuration keys/values must be validated and either rejected or ignored with proper logging.

7. TaskRuns created as part of a PipelineRun should follow the PipelineRun’s pruning policy unless configured otherwise.

8. Changes to configuration (e.g., updated ConfigMaps) should apply without restarting the controller.

## Proposal

The proposal introduces a standalone Pruner Controller that automatically deletes completed `PipelineRun` and `TaskRun` resources based on cleanup settings defined in a ConfigMap named `tekton-pruner-default-spec`. 

The ConfigMap to handle clusterwide pruning behaviour will be managed in the `tekton-pipelines` namespace. By default config includes minimal configuration as per spec [here](https://raw.githubusercontent.com/openshift-pipelines/tektoncd-pruner/refs/heads/main/config/600-tekton-pruner-default-spec.yaml). 

This can be modified as required. Here's a basic example:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tekton-pruner-default-spec
  namespace: tekton-pipelines
data:
  global-config: |
    enforcedConfigLevel: global
    ttlSecondsAfterFinished: 300    # 5 minutes
    successfulHistoryLimit: 3       # Keep last 3 successful runs
    failedHistoryLimit: 3           # Keep last 3 failed runs
    historyLimit: 5                 # When successfulHistoryLimit and failedHistoryLimit are not set
```
The controller continuously watches of completed `PipelineRun` or `TaskRun` events and triggers deletion of the same based on the settings defined in the configMap.

### Notes and Caveats

1. The initial implementation supports cluster-wide defaults and namespace-specific overrides, using a ConfigMap located in the tekton-pipelines namespace.

1. A validation mechanism to ensure only valid configuration keys and values are accepted in the ConfigMap is under development.

1. Fine-grained pruning policies based on resource groups (using labels, annotations, or resource names) are also planned for a future release.

## Design Details

[Tekton Pruner Overview](https://github.com/openshift-pipelines/tektoncd-pruner?tab=readme-ov-file#tekton-pruner)

## Design Evaluation
TO BE UPDATED

### Reusability

### Simplicity

### Flexibility

### Conformance

### User Experience

### Performance

### Risks and Mitigations

### Drawbacks

## Alternatives
TO BE UPDATED

## Implementation Plan
TO BE UPDATED

### Test Plan

### Infrastructure Needed

### Upgrade and Migration Strategy

### Implementation Pull Requests

## References

- [Operator based pruner](https://tekton.dev/docs/operator/tektonconfig/#pruner)
- [Introduce runHistoryLimit](https://github.com/tektoncd/pipeline/issues/2332)
- [Experimental Cleanup implementation](https://github.com/tektoncd/experimental/tree/main/pipeline/cleanup)

