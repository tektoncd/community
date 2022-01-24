---
status: proposed
title: Embedded TaskRuns and Runs Status in PipelineRuns
creation-date: '2022-01-24'
last-updated: '2022-01-29'
authors:
- '@lbernick'
- '@jerop'
see-also:
- TEP-0021
- TEP-0056
- TEP-0090
---

# TEP-0100: Embedded TaskRuns and Runs Status in PipelineRuns

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [1. Performance Degradation](#1-performance-degradation)
  - [2. Memory Bloat](#2-memory-bloat)
  - [3. Lack of Extensibility](#3-lack-of-extensibility)
- [Goals](#goals)
- [Non-Goals](#non-goals)
- [Background](#background)
  - [PipelineRun Status](#pipelinerun-status)
  - [Owner References and Labels](#owner-references-and-labels)
  - [Tekton Results API](#tekton-results-api)
- [Open Questions](#open-questions)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes changes to `PipelineRun` Status to reduce the amount of information stored
about the status of `TaskRuns` and `Runs` to improve performance, reduce memory bloat and 
improve extensibility.

## Motivation

Today, we embed the status of each `TaskRun` and `Run` into the `PipelineRun` status.
This causes several issues: performance degradation, memory bloat, and lack of extensibility.

### 1. Performance Degradation 
    
Every time the status of `TaskRuns` and `Runs` change, the status of the parent `PipelineRun`
is updated as well. For example, the status of a `PipelineRun` is updated upon completion of
each `Step`, even if the `TaskRun` or `Run` has not completed. This causes extra requests to
etcd and extra load on the Dashboard, which reacts to CRD status updates. 
Read more in the [related issue][issue-3140].

### 2. Memory Bloat

Embedded statuses increase the size of the serialized `PipelineRuns`.
As shared in [API WG on 10/01/2022][api-wg], the embedded statuses is costly for users:
> "embedding status more than doubles the storage and has direct consequences on what 
> customers end up paying"

Read more in the [related issue][issue-3140].

### 3. Lack of Extensibility

The above problems will be exacerbated when we support features that execute multiple 
`TaskRuns` and `Runs` from one `PipelineTask`. For example:
* [**`Matrix`**][tep-0090]: fan out a given `PipelineTask` into multiple `TaskRuns` or `Runs`.
  Fanned out `TaskRuns` and `Runs` can even be created dynamically by consuming `Results` from
  previous `TaskRuns` and `Runs`.
* [**`Pipelines` in `Pipelines`**][tep-0056]: pass in `Pipelines` to `PipelineTasks` to run
  them similarly to `Tasks`.

## Goals

* Improve performance by reducing updates to `PipelineRun` status from `TaskRuns` and `Runs`.
* Improve memory usage by reducing the amount of storage `PipelineRun` status uses for `TaskRuns` and `Runs`.
* Improve extensibility by setting up `PipelineRun` status to better support upcoming features in Tekton Pipelines.

## Non-Goals

* Improve other aspects of `PipelineRun` status other than the embedding of `TaskRuns` and `Runs`.
* Make any changes to `PipelineRun` spec.

## Background

### PipelineRun Status

The `PipelineRunStatus` contains the status (`ConditionSucceeded`) of the `PipelineRun` and other
details including the complete status of its `TaskRuns` and `Runs`. This TEP aims to optimize the
`TaskRuns` and `Runs` fields only in the `PipelineRunStatus`. The other fields, such as the resolved
`PipelineSpec`, are out of scope and will not be changed.

[PipelineRunStatus][pipelinerunstatus]:
```go
type PipelineRunStatus struct {
	duckv1beta1.Status `json:",inline"`
	PipelineRunStatusFields `json:",inline"`
}
```

[PipelineRunStatusFields][pipelinerunstatusfields]:
```go
type PipelineRunStatusFields struct {
	StartTime *metav1.Time `json:"startTime,omitempty"`
	CompletionTime *metav1.Time `json:"completionTime,omitempty"`
	TaskRuns map[string]*PipelineRunTaskRunStatus `json:"taskRuns,omitempty"`
	Runs map[string]*PipelineRunRunStatus `json:"runs,omitempty"`
	PipelineResults []PipelineRunResult `json:"pipelineResults,omitempty"`
	PipelineSpec *PipelineSpec `json:"pipelineSpec,omitempty"`
	SkippedTasks []SkippedTask `json:"skippedTasks,omitempty"`
}
```

### Owner References and Labels

`TaskRuns` and `Runs` have owner references to `PipelineRuns`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  ...
  name: myTaskRun
  ownerReferences:
  - apiVersion: tekton.dev/v1beta1
    blockOwnerDeletion: true
    controller: true
    kind: PipelineRun
    name: myPipelineRun
  ...
```

`TaskRuns` and `Runs` also have labels for the source `PipelineRuns`: 
`tekton.dev/pipelineRun: <PipelineRunName>`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  labels:
    app.kubernetes.io/managed-by: tekton-pipelines
    tekton.dev/memberOf: tasks
    tekton.dev/pipeline: myPipeline
    tekton.dev/pipelineRun: myPipelineRun
    tekton.dev/pipelineTask: myPipelineTask
    tekton.dev/task: myTask
  name: myTaskRun
  ...
```

Users and tools can rely on these owner references and labels to connect
`TaskRuns` and `Runs` to the `PipelineRuns` that created them.

### Tekton Results API

[Tekton Results][results-api] bundles related `PipelineRuns`, `TaskRuns` and `Runs`
into a single unit (called `Result`).

For example, a `PipelineRun` with two `TaskRuns` would have one `Result` with
three `Records`:

```
                               myPipelineRun [Result]
                                         |
                                         v
          --------------------------------------------------------------
          |                              |                             |
          v                              v                             v   
 myPipelineRun [Record]           myTaskRun1 [Record]           myTaskRun2 [Record]
```

In addition to grouping related resources, Tekton Results provides long term storage
of `PipelineRuns`, `TaskRuns` and `Runs` away from the runtime storage in etcd.
Read more in [TEP-0021][tep-0021].

## Open Questions

* [Qn #1][qn-1]: What fields will no longer be available? What do we lose from the optimizations?
  We will discuss this in the proposal.
* [Qn #2][qn-1]: What does an example status look like?
  We will provide examples in the proposal.

## References

* Issues:
  * [PipelineRun and TaskRun Status][issue-3792]
  * [PipelineRun Status bloat and excessive updates][issue-3140]
* TEPs:
  * [TEP-0021: Results API][tep-0021]
  * [TEP-0056: Pipelines in Pipelines][tep-0056]
  * [TEP-0090: Matrix][tep-0090]
* [Tekton Results][results-api]

[tep-0056]: https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md
[tep-0090]: https://github.com/tektoncd/community/blob/main/teps/0090-matrix.md
[tep-0021]: https://github.com/tektoncd/community/blob/main/teps/0021-results-api.md
[issue-3140]: https://github.com/tektoncd/pipeline/issues/3140
[issue-3792]: https://github.com/tektoncd/pipeline/issues/3792
[api-wg]: https://docs.google.com/document/d/17PodAxG8hV351fBhSu7Y_OIPhGTVgj6OJ2lPphYYRpU/edit#heading=h.esbaqjpyouim
[pipelinerunstatus]: https://github.com/tektoncd/pipeline/blob/411d033c5e4bf3409f01b175531cbc1a0a75fadb/pkg/apis/pipeline/v1beta1/pipelinerun_types.go#L290-L296
[pipelinerunstatusfields]: https://github.com/tektoncd/pipeline/blob/411d033c5e4bf3409f01b175531cbc1a0a75fadb/pkg/apis/pipeline/v1beta1/pipelinerun_types.go#L393-L423
[results-api]: https://github.com/tektoncd/results
[qn-1]: https://github.com/tektoncd/community/pull/606#discussion_r792860152
