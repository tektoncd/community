---
status: proposed
title: Add optional PVCs autoremoval in workspaces coschedule mode
creation-date: '2025-05-26'
last-updated: '2025-05-26'
authors:
- '@fambelic'
collaborators: []
---

# TEP-0161: Add an Optional Flag for Enabling Pvcs Autoremoval Behavior

- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Drawbacks](#drawbacks)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
- [References](#references)


## Summary
This is a very small TEP aimed at extending existing functionality. The general concept has already been discussed in prior resources:
- [TEP-0135: Coscheduling PipelineRun Pods](https://github.com/tektoncd/community/blob/main/teps/0135-coscheduling-pipelinerun-pods.md)
- [Discussion](https://github.com/tektoncd/pipeline/pull/6741#issuecomment-1610123340)

In [PR #6940](https://github.com/tektoncd/pipeline/pull/6940), two new feature flags (`pipelineruns` and `isolated-pipelineruns`) related to the `AffinityAssistant` were added to modify node scheduling behavior and enable automatic deletion of workspace `PVCs` when PipelineRuns complete.
This TEP proposes adding the same PVC auto-removal behavior through an optional flag when `coschedule` mode is set to `workspaces`.
This maintains backward compatibility while providing users with the option to enable automated cleanup of PVCs associated with PipelineRuns in workspaces mode.
## Motivation
Automatic PVC removal can help reduce cluster storage consumption and improve resource management.
By enabling this behavior in `workspaces` coschedule mode, users can benefit from auto-cleanup even when pods are scheduled based on shared workspaces. Letting the controller handle PVC cleanup upon PipelineRun completion reduces storage waste and improves the user experience when inspecting Kubernetes objects, as it avoids cluttering the namespace with useless PVCs.

### Goals
- Allow users to enable PVC auto-removal when using `workspaces` coschedule mode.
### Non-Goals
- Unless explicitly overridden, it does not alter the default behavior of `workspaces` coschedule mode, where PVCs are retained after PipelineRun completion.
- It does not change how PVCs are created or the ownership model, where PipelineRuns are the owners of PVCs created via the `Affinity Assistant`.
## Proposal
This TEP proposes a new optional boolean flag called `enable-pvc-auto-removal` within feature-flags ConfigMap that can be set to true when the auto-removal behavior wants to be enabled when the coschedule mode is set to `workspaces`. 
Here's an example of the proposed feature:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: feature-flags
  namespace: tekton-pipelines
  labels:
    app.kubernetes.io/instance: default
    app.kubernetes.io/part-of: tekton-pipelines
data:
  coschedule: "workspaces"
  enable-pvc-auto-removal: "true"
  .....
```
This flag is only evaluated when coschedule is set to `workspaces`. If set to "`true`, the controller removes PVCs associated with completed PipelineRuns. If omitted or set to `false`, the default behavior is preserved and PVCs remain.
## Design Details

The new flag is a boolean with the following behavior:
 - `true`: PVCs are automatically deleted once their associated PipelineRuns complete, using the same logic already implemented for other coschedule modes.
 - `false`(default): PVCs persist alongside completed PipelineRuns.
### Reusability
The proposed change would reuse the PVC cleanup logic already in place for the other modes. This minimizes implementation effort and ensures consistency across modes.
### Drawbacks
- While it does not cause functional issues, enabling this flag introduces a small inconsistency: PVCs are still owned by PipelineRuns, but are deleted automatically.
## Implementation Plan

1. Add the `enable-pvc-auto-removal` flag to the `FeatureFlags` struct.
2. Modify the Affinity Assistant logic to check on the new flag in `workspaces` mode.
3. Ensure backward compatibility by defaulting the flag to false.

### Test Plan

- Add unit tests for the new flag behavior.
- If necessary, add integration and/or e2e tests verifying PVC removal in workspaces mode when the flag is enabled.

## References
- [TEP](https://github.com/tektoncd/community/blob/main/teps/0135-coscheduling-pipelinerun-pods.md)
- [Discussion](https://github.com/tektoncd/pipeline/pull/6741#issuecomment-1610123340)
- [Commit](https://github.com/tektoncd/pipeline/commit/84b8621df194177fe26f53d8b330387295517484)
