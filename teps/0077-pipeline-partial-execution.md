---
status: proposed
title: Pipeline partial execution
creation-date: '2021-07-21'
last-updated: '2021-07-21'
authors:
- '@jerop'
- '@bobcatfish'
- '@Tomcli'
- '@ScrapCodes'
---

# TEP-0077: Pipeline partial execution

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
    - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
    - [Notes/Caveats (optional)](#notescaveats-optional)
    - [Risks and Mitigations](#risks-and-mitigations)
    - [User Experience (optional)](#user-experience-optional)
    - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-request-s)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

Add an ability for `PipelineRun` to have disabled tasks i.e. a `PipelineRun`
can execute a `Pipeline` partially. 

Allow `PipelineRun` to be created from previous `PipelineRun`.

So, a `PipelineRun` can be partially run or cancelled at run time, and
resumed at a later point with the help of work proposed in this TEP.

Together these will bring in the ability to resume/retry a failed `PipelineRun`

## Motivation

1. A very long Pipeline may fail due to a transient failure, and the user may
   want to only rerun the `Tasks` that failed. This is the most significant
   motivation, as we use tekton as a backend for running our machine learning
   pipelines at Kubeflow.
2. It is not enough to `retry` a `PipelineTask` n times, as the failures can
   be due to e.g. service outage. A manual resume/ retry may be helpful.
3. Iterate quickly, by disabling tasks that take longer time. This can be done
   at run time, i.e. without editing pipeline definition.

### Goals

- Partially execute a `Pipeline`, by disabling tasks.
- Resume a failed or cancelled `PipelineRun` from previous `PipelineRun`.
- Discuss how the results/workspaces of disabled tasks can be referenced or
  populated from previous `PipelineRun`.

### Non-Goals

- TBD.

### Use Cases (optional)

1. *Optimal use of resources*: `tektoncd` as a backend for ML. 
   A machine learning pipeline may consist of tasks moving large amount of
   data and then training ml models, all of it can be very resource consuming
   and inability to retry would require a user to start the entire pipeline
   over. A manual retry, with the ability to specify what tasks should
   be skipped, may be helpful.
2. Partial execution of pipeline. This is useful for reusing an existing
   pipeline i.e. a user can disable certain task from an existing pipeline
   and in this way run it without creating a new pipeline.
3. Partial execution is also helpful for testing, i.e. skipping some tasks
   and developing and testing iteratively and quickly.
4. Pause and resume, i.e. one could manually cancel a running `PipelineRun`
   and resume at later point.

## Requirements
- Create a new `PipelineRun` to resume or retry a completed `PipelineRun`.

## Proposal

#### Requesting API Changes
1. Add `resumeFrom` under `PipelineRun.spec`. It has following fields: 
   - `resumeFrom.name` which is the name of previously run `PipelineRun`.
   - `resumeFrom.enableTasks` accepts an array of task names under it.
2. Add `disableTasks` under `PipelineRun.spec`, which accepts an array
    of task name and their result definitions.
   - `name`: Name of the task to be disabled.
        - `results`: Pre-populate results for the disabled task.

Q. Why do we need `resumeFrom` when we have `disableTasks`? 

`disableTasks` can be used to explicitly disable tasks that a user 
do not wish to run and `resumeFrom` tekton controller automatically
figures out the tasks failed and unfinished, because it knows the
DAG. For the end user, it can be difficult to figure out the DAG and
prepare the accurate execution plan for the next pipeline run.

Both, `resumeFrom` and `disableTasks` are optional fields. See examples
1 and 2 below.

#### Semantics of execution.

- `resumeFrom` : resumeFrom references a previous pipelineRun and by default
selects all the failed and unfinished tasks eligible for retrying/resuming.
It references results of completed tasks from previous run, unless
overridden by `disableTasks` section.

- `resumeFrom.enableTasks`: If a task was successful in previous run, but
it is required by the current run, this section can be used to explicitly
enable it.

**Case: disabled task exists somewhere in the middle of DAG execution.**

Consider the case of following failed `PipelineRun`.
```
F   A     D
| \ |     |
v   v     v 
G   B --> E
    |
    v
    C
```

1. 
  - Previous Run stats:
    - Successful Tasks: A 
    - Failed Tasks: F, B
    - Not yet started tasks: D, E, G, C
  - Current Run:
      - Disabled task: B
      - To be executed: F, D, E, G, C

Since task B is disabled, task E will use its pre-set result.
Even if we disable G, F is still retried in the current Run.

#### Examples

1. Resuming a failed Pipeline.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: new-pipeline-run
spec:
  # resumeFrom references a previous pipelineRun and by default selects
  # all the failed and unfinished tasks eligible for retrying/resuming.
  # It references results of completed tasks from previous run, unless
  # overridden by disableTasks section.
  resumeFrom:
    name: prev-pipeline-run
    # Enable tasks section can be used to enable those tasks which were
    # successful in previous run. e.g. an init task.
    enableTasks:
      - name: init-task-name
  # One of the failed task is disabled by disableTasks section, for some
  # reason we want it skipped and the expected results has been hard coded.
  disableTasks:
    - name: task-name
      # option to pre-populate the values of disabled task's results.
      results: 
        - name: result1-name
          value: some-val
        - name: result2-name
          value: some-val2
  serviceAccountName: 'default'
  # Some tasks needs cleaning of workspaces, this can be done here.
  # e.g. one could override a workspace by specifying the name.
  workspaces:
  - name: some-data
    persistentVolumeClaim:
      claimName: some-storage
  resources:
  - name: repo
    resourceRef:
      name: some-ref
```

2. Partial execution of a pipeline.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: new-pipeline-run
spec:
  pipelineRef:
    name: a-pipeline
  disableTasks:
    - name: task-name
      # optionally pre-populate the values of disabled task's results.
      results: 
        - name: result1-name
          value: some-val
        - name: result2-name
          value: some-val2
    - name: task-name-other
      results:
        - name: result1-name
          value: some-val
        - name: result2-name
          value: some-val2
```

### Notes/Caveats (optional)

Q. Can we provide an option to disable a task and all the that depend on it?

e.g. disable task with a flag e.g. `cascade: true` or `disableDependents: true`.


### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable.  This may include API specs (though not always
required) or even code snippets.  If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->

## Test Plan

<!--
**Note:** *Not required until targeted at a release.*

Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all of the test cases, just the general strategy.  Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References (optional)

1. [Google Doc: Disabling a Task in a Pipeline](https://docs.google.com/document/d/1rleshixafJy4n1CwFlfbAJuZjBL1PQSm3b0Q9s1B_T8/edit#heading=h.jz9jia3av6h1)
2. [TEP-0065](https://github.com/tektoncd/community/pull/422)
