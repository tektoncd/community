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
- [Future work](#future-work)
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
- Ability to partially run a Pipeline, without editing its definition or without
  an existing `PipelineRun`.
- An end user may not have to figure out the execution DAG, to be able to resume
  or retry.

## Proposal

### Requesting API Changes
1. Add `pipelineRunRef` under `PipelineRun.spec`. It has following fields: 
   - `pipelineRunRef.name` which is the name of previously run `PipelineRun`.
   - `pipelineRunRef.enableTasks` accepts an array of task names under it.
2. Add `disableTasks` under `PipelineRun.spec`, which accepts an array
    of task name.
   - `name`: Name of the task to be disabled.

Q. Why do we need `pipelineRunRef` when we have `disableTasks`? 

`disableTasks` can be used to explicitly disable tasks that a user 
do not wish to run. On the other hand, in `pipelineRunRef` tekton controller
automatically figures out the tasks failed and unfinished, because it knows the
DAG. For the end user, it can be difficult to figure out the DAG and prepare
the accurate execution plan for the next pipeline run.

Both, `pipelineRunRef` and `disableTasks` are optional fields. See examples
1 and 2 below.

### Semantics of execution.

- `pipelineRunRef` : pipelineRunRef references a previous pipelineRun and by default
    selects all the failed and unfinished tasks eligible for retrying/resuming.
    It references results of completed tasks from previous run.

- `pipelineRunRef.enableTasks`: If a task was successful in previous run, but
    it is required by the current run, this section can be used to explicitly
    enable it. For example, a task may perform some initialization for the
    other tasks in `PipelineRun`.

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
  - Previous Run stats from `prev-pipeline-run` :
    - Successful Tasks: A 
    - Failed Tasks: F, B
    - Not yet started tasks: D, E, G, C
  - Current Run: `new-pipeline-run`
      - Disabled task: B, G
      - To be executed: F, D, C

Since task B is disabled, task E will also be disabled as it depends on B.

We have disabled G, but F is still retried in the current Run i.e. `new-pipeline-run`

#### Examples

1. Resuming a failed Pipeline.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: new-pipeline-run
spec:
  # pipelineRunRef references a previous pipelineRun and by default selects
  # all the "failed" and "unfinished" tasks eligible for retrying/resuming.
  # It references results of completed tasks from previous run.
  pipelineRunRef:
    name: prev-pipeline-run
    # Enable tasks section can be used to enable those tasks which were
    # successful in previous run. e.g. an init task.
    enableTasks:
      - name: A
  # One of the failed task is disabled by disableTasks section.
  disableTasks:
    - name: B
    - name: G
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

Above example will run tasks: A, F, D, C

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
    - name: B
    # the task `B` is disabled for the current execution and everything
    # that depends on it.
    - name: G
```

Above example will run tasks: A, F, D, C

### Notes/Caveats (optional)

Q. Can we provide an option to disable a task but not all the that depend on it?

e.g. disable task with a flag e.g. `cascade: false` or `disableDependents: false`.
Also provide an option for hard-conding the results.
My preference is this can be work for future TEP.

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

## Future Work

1. **Provide an option to disable a task but not all the that depend on it.**
    
    ```yaml
    spec:
      pipelineRef:
        name: a-pipeline
      disableTasks:
        - name: B
          disableDependents: false
          results:
            - name: result-A
              value: result-value
        - name: G
    ```

    Above example will run tasks: A, E, F, D, C.
    Note: E is executed, because `disableDependents: false` and results are provided.
    
    Use cases include:
    1. A user can override the results being referenced from previous Run, by using
       this section.
    2. Suppose a failed task is permanently failing, and one would like to disable
       that task but not its dependents, then the user can hard code the results and 
       execute the dependents.
       

2. **Option to include all tasks from previous pipelineRun**
    ```yaml
    spec:
      pipelineRunRef:
        name: prev-pipeline-run
        include: All # one of: All|failed|none
      # One of the failed task is disabled by disableTasks section.
      disableTasks:
        - name: B
        - name: G
    ```
    Above example will run tasks: A, F, D, C.
    By default, only failed and unifinished tasks are included from previous 
    `PipelineRun`. With this option, a user will be able to include either
   everything or nothing as well. These are merely convenience options. The
   same can be achieved by a combination of `disableTasks` and `enableTasks`.
   
    Use cases:
    1. _A convenience option_, if there are large no. of tasks in the previous
        `PipelineRun` and only a few of them have to be explicitly disabled.
       Then, one can `include: All` and disable specific ones.
       
       Without this option, a user will have to list out all the tasks that
       should be disabled in the `disableTasks` section.


## Alternatives

1. **Using a boolean in the Task definition**
   Specify a boolean in the  Pipeline level within the definition of the Task to be disabled.
    ```yaml
    apiVersion: tekton.dev/v1beta1
    kind: Pipeline
    metadata:
      name: example-pipeline
    spec:
      tasks:
        - name: task-one
          taskRef:
            - name: task-one
              disable: true
        - name: task-two
          taskRef:
            - name: task-two
    ```

This alternative does not meet the requirement, without editing pipeline definition.

2. **Using an always-false When expression.**
   Disable a Task using an always-false When expression.
    ```yaml
    apiVersion: tekton.dev/v1beta1
    kind: Pipeline
    metadata:
      name: example-pipeline
    spec:
        tasks:
        - name: task-one
          when:
          - input: "false"
            operator: in
            values: ["true"]
          taskRef: 
            - name: task-one
        - name: task-two
          taskRef:
            - name: task-two
    ```

This alternative does not meet the requirement, without editing pipeline definition.

3. **SkipTasks**
    These PipelineTasks would be skipped, and their subsequent tasks would be skipped as well. 
    ```yaml
    apiVersion: tekton.dev/v1beta1
    kind: PipelineRun
    metadata:
      name: example-pipeline-run
    spec:
        pipelineRef:
          name: example-pipeline
        skipTasks:
          - name: fetch-the-recipe
          - name: print-the-recipe 
    ```

4. **Using skip tasks with output resources**
   Allow users to specify a list of PipelineTasks to be skipped when defining a
   PipelineRun, and include resource overrides to handle dependent Tasks. Some
   subsequent Tasks may be dependent on the disabled Tasks, that is, they expect
   some resources from the disabled Tasks. The user can optionally make those
   resources available by providing access to the workspaces and expected
   results in the `disabledTasks` definition as such:
   
    ```yaml
    apiVersion: tekton.dev/v1beta1
    kind: PipelineRun
    metadata:
        name: example-pipeline-run
    spec:
        pipelineRef:
            name: example-pipeline
        workspaces:
            - name: shared-data
        persistentVolumeClaim:
            claimName: shared-task-storage
        disabledTasks:
            - name: fetch-the-recipe
              outputs:
              workspaces:
                - name: filedrop
                  workspace: shared-data
                  results:
                - name: status
                  value: $(foo.status.results)
            - name: print-the-recipe
              workspaces:
              results:
    ```
   
5. **Resume from Tasks in a previous PipelineRun**
   We can implement some way to allow a PipelineRun to pick up from a previous
   PipelineRun, and resume from specific Tasks. Similar to Jenkins’ restart from
   stage.
   
    ```yaml
    apiVersion: tekton.dev/v1beta1
    kind: PipelineRun
    metadata:
      name: example-pipeline-run
    spec:
      pipelineRef:
        name: example-pipeline
        fromPreviousRun: foo
        resumeFrom: [print-the-recipe]
    ```
   
    One of the challenge here is, a user has to figure out a DAG. As point
    of resume can be plural.
   
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
