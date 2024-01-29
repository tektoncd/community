---
status: proposed
title: Error Attribution via Conditions Status
creation-date: '2024-01-26'
last-updated: '2024-01-26'
authors:
- '@JeromeJu'
collaborators: []
---

# TEP-0151: Error Attribution via Conditions Status

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Use Cases](#use-cases)
  - [Goals](#goals)
  - [Non-Goals/Future Work](#non-goalsfuture-work)
  - [Requirements](#requirements)
- [References](#references)
<!-- /toc -->

## Summary
This TEP proposes to enhance error attribution by expanding our existing Condition Status ([PipelineRun.Status.Conditions](https://github.com/tektoncd/pipeline/blob/dbd2c67a22738130854bd029cb36b3432cef4338/pkg/apis/pipeline/v1/pipelinerun_types.go#L317)) and introducing more indicative [ConditionType](https://pkg.go.dev/knative.dev/pkg/apis#ConditionType)s that helps unmix the existing Condition Reasons.

## Motivation
Stemming from the [user request](https://github.com/tektoncd/pipeline/issues/6859#issuecomment-1817166207), our existing error attribution for Tekton Pipeline conflates user versus system and Pipeline internal errors. Downstream users would like to have more parsable Run failure `Condition.Reason` with the `Status.Conditions`.

By examining the [existing discrepancies](https://github.com/tektoncd/pipeline/issues/7434) in `Condition.Reason` for `PipelineRun.Status.Conditions` and the [needs to surface TerminationReason](https://github.com/tektoncd/pipeline/issues/7223) for Containers in TaskRun pods, we have identified the conflated runtime validation failure reasons and unclear failure messages being conveyed, which made it hard for users to differentiate or use machine to parse them. However, it is not feasible to make enhancement to the existing combination of `Status.Condition` with the existing ConditionType since [these changes are considered as backwards-incompatible](https://github.com/tektoncd/pipeline/issues/7539#issuecomment-1881246799) without a major version bump to `v2alpha1`.

### Goals
- Allow **v1** PipelineRuns and TaskRun failures to be more easily attributed for the failure errors by adding new `ConditionType` and breaking up the existing conflated failure `Condition.Status.Reason`. 
- Provide downstream users, including cluster operators and end Pipeline users, with enough information so that they can blame either the user for the configuration error, or system error or its vendor service error.
- Circumvent the existing limitation of incompatibility changes made to the error reasons: error reasons and pod termination reasons are conflated and needs identifications but they are backwards incompatbile changes that can only be made with a major version bump to `v2alpha1`.

### Non-goals/Future Work
- Predefine the schema for `v2alpha1` PipelineRun and TaskRun Status.


### Use cases
**Cluster Operators**
- As a cluster operator whose service consumes `PipelineRun.Status.Conditions[*]` and `PipelineRunReason`, I want to have more granular status outputs with clear failure reasons so that I can provide more insights for users. For example, I want to be able to know from the Run Status about whether the error should be attributed to the user, system or the service provided.

**End Users**
- As a user who configures Pipeline to run CI/CD jobs, I want each `PipelineRun`/`TaskRun` failure reason to be parsable, meaning that they are clearly separated, meaningful and deterministic for debugging.

**Tekton Pipeline and Task Author**
- As a Pipeline author, I want to easily identify and fix **configuration errors** in my pipelines and tasks, with informative Conditions, error reason and messages to guide me.

### Requirements
- The changes to `PipelineRun.Status.Conditions` will be made in a backwards compatible way:
  - It will not alter the output and the sequence of the existing "Succeeded" `ConditionType` including the Reason and Status of the Condition
  - Existing PipelineRun and TaskRun reasons will remain, supplemented by more granular reasons that are broken down from the [existing ones](https://github.com/tektoncd/pipeline/issues/7501).
- The additional `ConditionType` and `Condition.Reason` comply to [kubernetes Condition status conventions](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#typical-status-properties).
- The `ConditionType` and `Condition.Reason` added are insightful and could help identify more failure scenarios for debugging.

## References
- https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#typical-status-properties
- https://github.com/tektoncd/pipeline/issues/6859
- https://github.com/tektoncd/pipeline/issues/7434
- https://github.com/tektoncd/pipeline/issues/7501