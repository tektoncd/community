---
status: proposed
title: Aggregate Status of DAG Tasks
creation-date: '2021-03-04'
last-updated: '2021-03-25'
authors:
- '@pritidesai'
---

# TEP-0049: Aggregate Status of DAG Tasks

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
- [Test Plan](#test-plan)
- [References](#references)
<!-- /toc -->

## Summary

**Note** In this TEP, `dag` task refers to `pipelineTask` in the `tasks` section and `finally` task refers to
`pipelineTask` in the `finally` section.

A `finally` task in a `pipeline` has access to the execution status of any `dag` task through a context variable
`$(tasks.<pipelineTask>.status)`. [TEP-0028: Task Execution Status at Runtime](0028-task-execution-status-at-runtime.md)
implemented this context variable which is instantiated and available at the runtime. This context variable is set
to `Succeeded`, `Failed`, or `None` depending on the execution status of that task and generally consumed in
`when` expressions:

```yaml
    finally:
      - name: notify-build-failure # notify build failure only when golang-build task fails
        when:
          - input: $(tasks.golang-build.status)
            operator: in
            values: ["Failed"]
        taskRef:
          name: send-to-slack-channel
```


This works great for a pipeline where a `finally` task depends on the execution status of an individual `dag` task.
We often run into the use cases where a `finally` task needs to be executed if any one of the `dag` tasks fail.
This use case can also be accomplished by explicitly spelling out each `dag` task in the comparison:

```yaml
finally:
      - name: notify-any-failure # executed only when any dag task fail
        when:
          - input: "Failed"
            operator: in
            values: [$(tasks.unit-tests.status), $(tasks.golang-build.status), $(tasks.deploy.status)]
```

But, this solution does not scale well with a larger pipeline with 50 to 60 `dag` tasks. It explodes the `when`
expressions with the entire list of `dag` tasks. Also, every time a pipeline is updated to add/delete a `dag` task,
the pipeline author has to remember to update `when` expressions in the `finally` task as well.

These concerns can be addressed by introducing a context variable with an aggregate status of all the `dag` tasks,
`$(tasks.status)`.


## Motivation

* A `pipeline` author wants to perform some operation or execute a `finally` task as part of the same `pipeline` if one
  of the `dag` tasks fail.

### Goals

* The main goal of this proposal is to allow access to aggregate status of all `dag` tasks within the `pipeline`
  in `finally` at runtime. An additional goal of this proposal is to align the aggregate status to `pipelineRun` status.

### Non-Goals

* This proposal does not allow `dag` tasks to access aggregate status of the `dag` tasks.

* This proposal is not to expose the entire status of a `taskRun`/`pipelineRun` as metadata at runtime.

### Use Cases

* As a `pipeline` author, I would like to design a `finally` task to send failure notification to slack if any `dag`
  task fail.
  
## Proposal

Introduce a new variable `$(tasks.status)` which resolves to one of the execution states: `Succeeded`, `Failed`,
and `Completed`.

This variable is instantiated and available at the runtime. In the following example, the `pipeline` has ten `dag` tasks
and a `finally` task to send failure notifications. The `finally` task, `notify-any-failure`, checks the aggregate
execution status of `dag` tasks using this variable and continues if it is set to `Failed`.

```yaml
finally:
      - name: notify-any-failure # executed only when one of the dag tasks fail
        when:
          - input: $(tasks.status)
            operator: in
            values: ["Failed"]
```

| State | Description |
| ----- | ----------- |
| `Succeeded` | All `dag` tasks have succeeded. |
| `Failed` | Any one of the `dag` task failed. |
| `Completed` | All `dag` tasks completed successfully including one or more skipped tasks. |
| `None` | No aggregate execution status available (i.e. none of the above) because some of the tasks are still pending or running or cancelled or timed out. |

`$(tasks.status)` is not accessible in any `dag` task but only accessible in a `finally` task. The `pipeline` creation
will fail with the validation error if `$(tasks.status)` is used in any `dag` task.

## Test Plan

All necessary e2e, unit tests, and example will be added.

## References

* [TEP-0028: Task Execution Status at Runtime](0028-task-execution-status-at-runtime.md)
* [tektoncd/pipeline PR #3390 - Access execution status of any task in finally](https://github.com/tektoncd/pipeline/pull/3390) 
* [tektoncd/pipeline Issue #3806 - Be able to use pipeline execution status in pipeline finally](https://github.com/tektoncd/pipeline/issues/3806)
* [tektoncd/pipeline Issue #1020 - The finally task C wants to perform a different logic if either task A or task B fails.](https://github.com/tektoncd/pipeline/issues/1020#issuecomment-747156100)
* [tektoncd/pipeline PR #3738 - Overall status of tasks in When Expressions](https://github.com/tektoncd/pipeline/pull/3738#discussion_r568618980)
* [Monitoring Execution Status](https://github.com/tektoncd/pipeline/blob/master/docs/pipelineruns.md#monitoring-execution-status)
* [tektoncd/pipeline Implementation PR #3817](https://github.com/tektoncd/pipeline/pull/3817)
