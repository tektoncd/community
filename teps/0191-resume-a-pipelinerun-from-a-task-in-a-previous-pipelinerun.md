---
status: proposed
title: Resume a PipelineRun from a Task in a Previous PipelineRun
creation-date: '2026-07-16'
last-updated: '2026-07-16'
authors:
- '@chmouel'
collaborators: []
see-also:
- TEP-0015
- TEP-0033
- TEP-0097
- TEP-0121
- TEP-0123
---

# TEP-0191: Resume a PipelineRun from a Task in a Previous PipelineRun

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Example](#example)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Security](#security)
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

This TEP proposes a way to create a new `PipelineRun` that resumes execution
from a task in an earlier `PipelineRun`. Tasks that completed before the chosen
restart point are not run again. Their recorded outcomes and results are made
available to the new run so that Tekton can schedule downstream tasks using the
existing pipeline graph and result references.

The earlier `PipelineRun` remains unchanged and continues to represent its
original execution attempt. The resumed `PipelineRun` is a separate resource
with its own status and a visible link to the run from which it resumed.

## Motivation

A failed `PipelineRun` can only be recovered by creating another run. The new
run starts from the roots of the pipeline graph, even when most tasks already
completed successfully.

Repeating successful work is costly for long pipelines. Early tasks may build
large images, run long test suites, provision infrastructure, or wait for human
approval. Some tasks also have external side effects, such as creating tickets
or sending notifications, which makes blind re-execution unsafe.

Retries and breakpoints apply only to active runs, while a pending
`PipelineRun` can only be held before it starts. External orchestration remains
an option, but it must reproduce Tekton's dependency, result, and skipping
rules.

[TEP-0077](https://github.com/tektoncd/community/pull/484) previously combined
partial execution and resume. This TEP revisits only recovery from a recorded
run.

### Goals

- Allow a user or platform to create a new `PipelineRun` that resumes from one
  or more tasks in a previous `PipelineRun`.
- Inherit eligible upstream task outcomes and results without creating new
  runtime objects, while preserving graph dependencies.
- Record the relationship between the source and resumed runs, and distinguish
  inherited task state from work executed by the resumed run.
- Introduce the capability as an alpha feature without changing the behavior
  of existing `PipelineRuns`.

### Non-Goals

- Mutating or restarting a terminal `PipelineRun` in place.
- Pausing a running task or replacing retry behavior within an active run.
- Providing general-purpose partial execution for arbitrary subsets of a
  pipeline unrelated to a previous run.
- Restoring workspace data or reconstructing external side effects.

### Use Cases

1. A release pipeline builds and signs an image, deploys it, and then runs
   acceptance tests. The acceptance tests fail because an external service is
   unavailable. After the service recovers, the release manager creates a new
   run that starts from the acceptance-test task without rebuilding or signing
   the image.

2. A delivery pipeline includes a human approval task before deployment. A
   later verification task fails. The operator resumes from the failed task
   without requesting the same approval again.

These use cases assume that downstream tasks can recover their inputs from
task results or durable external storage. Resume does not restore data that
existed only in a workspace used by the source run.

### Requirements

1. A resumed execution must create a new `PipelineRun`; the source run remains
   immutable and must have reached an unsuccessful terminal state.
2. The request must identify a same-namespace source `PipelineRun` and the task
   or tasks that form the new execution frontier.
3. Tekton must verify pipeline compatibility and inherit only completed
   predecessors and results needed by the resumed graph. Inherited tasks must
   not create new `TaskRuns` or `CustomRuns`.
4. Tekton must reject unknown tasks, dependency gaps, unavailable results, and
   incompatible pipeline definitions before scheduling resumed work.
5. Status and provenance must identify the source run and distinguish inherited
   tasks from tasks executed by the resumed run. Callers must be authorized to
   read the source run.
6. The feature must be alpha-gated, leave ordinary `PipelineRuns` unchanged,
   and must not imply that workspace contents or external state are restored.

## Proposal

A resumed `PipelineRun` refers to an earlier `PipelineRun` and identifies one
or more tasks from which execution should continue. The exact API shape will be
defined while this TEP moves toward `implementable`, but it must represent two
concepts:

- the source run whose completed work may be inherited;
- the execution frontier containing the tasks that should run again.

### Example

The following YAML illustrates one possible API shape. The field names are not
final and will be defined before this TEP moves to `implementable`.

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: release-resume-1
spec:
  pipelineRef:
    name: release
  resume:
    sourceRun: release-1
    restartTasks:
      - acceptance-test
```

In this example, `release-1` completed the `build`, `sign`, and `deploy` tasks
before `acceptance-test` failed. The new run inherits the completed task
outcomes and their required results from `release-1`. It executes
`acceptance-test` and any downstream tasks without creating new runtime objects
for `build`, `sign`, or `deploy`.

The resumed run does not restore workspace contents from `release-1`. If
`acceptance-test` needs an artifact produced by `build`, that artifact must be
available through durable external storage and referenced by an inherited
result.

Tekton compares both pipeline graphs, treats eligible predecessors as complete,
and makes their recorded results available to downstream tasks. It rejects
missing dependencies, unavailable results, unknown tasks, and incompatible
pipeline definitions.

The new run records its source and distinguishes inherited tasks from executed
tasks for clients and provenance consumers. The feature remains behind
`enable-api-fields: "alpha"` while these semantics are evaluated.

### Notes and Caveats

Pipeline graphs are not always linear. A restart point may have several
predecessors or may run beside an independent branch. The design must define a
consistent execution frontier and may need to accept several restart tasks.
Required source status must still exist when the resumed run is created.

## Design Details

The design should remain centered on the relationship between two
`PipelineRuns`, rather than allowing callers to assert arbitrary completed
tasks and result values.

Before this TEP becomes `implementable`, the design must settle:

- how pipeline compatibility is established, likely through an immutable
  resolved specification or digest;
- whether all inputs must match the source run or which inputs may change
  safely;
- how branches, skipped tasks, `finally` tasks, matrix tasks, and custom tasks
  participate in the execution frontier;
- how long inherited results must remain available;
- how status and provenance represent inherited work.

The alpha implementation may reject graph shapes whose inherited execution
cannot be represented without ambiguous behavior.

## Design Evaluation

### Reusability

Resume is a runtime concern. Pipeline authors should not have to add
`when` expressions or maintain a second pipeline in anticipation of failure.
The proposal reuses the existing graph and result model.

### Simplicity

The user selects a source run and restart point. Tekton validates the graph and
inherits eligible predecessors. The scope excludes a general task-selection
language.

### Flexibility

Full reruns, retries, phased pipelines, and higher-level workflow systems remain
valid. The resume API must not depend on a specific CLI or dashboard.

### Conformance

The `PipelineRun` API specification must document the feature. Resume remains
optional while it is alpha and does not expose pod or controller internals.

### User Experience

Clients should preview inherited and restarted tasks before submission, report
specific validation errors, and distinguish inherited work after submission.

### Performance

Resume avoids repeated work. Its additional graph validation should be bounded
by pipeline size and must not affect ordinary `PipelineRuns`.

### Risks and Mitigations

- Invalid or missing source state could start downstream tasks with incorrect
  inputs. Validation must reject the request before scheduling.
- Source history may be pruned. Tekton must report unavailable required data
  clearly.
- The feature increases core controller complexity. Alpha scope should remain
  narrow and reject unsupported graph shapes.

### Security

A caller must not gain access to results by referencing a source run that the
caller cannot read. Cross-namespace resume is out of scope, and the resumed run
must pass the same admission and policy checks as an ordinary `PipelineRun`.
Inherited results remain untrusted input like any other task result.

Chains and other provenance producers must not represent inherited tasks as
work executed by the resumed run. Provenance for the resumed run must identify
the source run and distinguish inherited outcomes from new execution so that
SLSA and policy consumers can evaluate the linked evidence.

### Drawbacks

This feature adds API, reconciliation, validation, and status concepts for a
recovery pattern that higher-level workflow systems can implement by creating
new pipelines. It cannot make every pipeline resumable because workspace data
and external side effects may not be reproducible.

## Alternatives

1. Rerun the complete pipeline. This requires no API changes, but repeats
   successful work and may repeat non-idempotent side effects.

2. Continue the terminal `PipelineRun` in place. This obscures the boundary
   between execution attempts and complicates reconciliation, audit, timeout,
   and completion semantics.

3. Split the pipeline into phases and use an external orchestrator. This works
   today and remains appropriate when phase boundaries are part of the
   workflow. It requires the orchestrator to manage dependencies and transfer
   state between runs.

4. Let callers declare completed tasks and provide result values directly.
   This is flexible but weakens provenance because the values are assertions,
   not outputs tied to a recorded execution.

## Implementation Plan

Implementation will define the alpha API and validation rules, add controller
and status support for inherited tasks, and document the user workflow. CLI and
dashboard support can follow the API. Beta behavior will be based on alpha
feedback.

### Test Plan

Unit and reconciler tests will cover graph validation, inherited results,
missing history, and status. End-to-end tests will verify that resumed runs
execute only the requested frontier and downstream tasks.

### Infrastructure Needed

No new project infrastructure is required.

### Upgrade and Migration Strategy

The feature is additive and disabled unless alpha API fields are enabled.
Existing `Pipelines` and `PipelineRuns` require no migration.

### Implementation Pull Requests

None yet.

## References

- [TEP-0015: Support Pending PipelineRuns](./0015-pending-pipeline.md)
- [TEP-0033: Tekton Feature Gates](./0033-tekton-feature-gates.md)
- [TEP-0097: Breakpoints for TaskRuns and PipelineRuns](./0097-breakpoints-for-taskruns-and-pipelineruns.md)
- [TEP-0121: Refine Retries for TaskRuns and CustomRuns](./0121-refine-retries-for-taskruns-and-customruns.md)
- [TEP-0123: Specifying on-demand-retry in a PipelineTask](./0123-specifying-on-demand-retry-in-pipelinetask.md)
- [Pipeline issue #50: Design: Partial Pipeline execution](https://github.com/tektoncd/pipeline/issues/50)
- [Community PR #484: TEP-0077: Partial pipeline execute](https://github.com/tektoncd/community/pull/484)
- [Pipeline issue #5348: Pause, resume, or retry after retry exhaustion](https://github.com/tektoncd/pipeline/issues/5348)
- [Jenkins: Restarting a Jenkins Pipeline](https://www.jenkins.io/doc/book/pipeline/running-pipelines/#restart-from-a-stage)
