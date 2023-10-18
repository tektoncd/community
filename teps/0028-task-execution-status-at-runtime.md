---
title: task-exec-status-at-runtime
authors:
  - "@pritidesai"
creation-date: 2020-10-15
last-updated: 2021-06-03
status: implemented
---

# TEP-0028: Task Execution Status at Runtime

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

**Note** In this TEP, `dag` tasks refer to `pipelineTasks` under `tasks` section and `finally` tasks refer to `pipelineTasks` in `finally` section.

A `finally` task in a `pipeline` is executed just before exiting the `pipeline`. `Pipeline` executes `finally` tasks
after all `dag` tasks finish successfully or one of the `dag` task results in failure i.e `finally` tasks are always
executed in parallel irrespective of success or failure of a `dag` task. Such `finally` tasks are lacking access to the
execution status of the `dag` tasks at runtime to better design and process success scenarios v/s failure scenarios.

This proposal is enabling a `finally` task to access the execution status of `dag` tasks at runtime to better design
`pipeline` based on the status.

## Motivation

* A `pipeline` author wants to send notification to an external system based on the execution status of the `dag` tasks. 
* A `pipeline` author wants to rollback if the deployment fails in that environment/cluster/region/provider.

### Goals

The main goal of this proposal is to allow access to the execution status of a task within the `pipeline` at runtime.
And design this approach in the simplest possible way, without any extra processing. 

An additional but important goal of this proposal is identify the different execution states of a `pipelineTask` and
how each of those states derived based on `taskRun` and/or `pipelineRun` status.

### Non-Goals

* This proposal does not allow dag tasks to access status of other dag tasks.

* This proposal is not to expose the execution state of `finally` tasks since its not required.
 
* This proposal is not to expose the entire status of a `taskRun`/`pipelineRun` as metadata at runtime.

## Proposal

Introduce a new variable `$(tasks.<pipelineTask>.status)` which resolves to one of the execution states: `Succeeded`, `Failed`, and `None`

This variable is instantiated and available at the runtime. In the following example, `deployment` is a `dag` task and `rollback` is a `finally` task. The `finally` task, `rollback`, checks the execution status of `deployment` task using this variable and continues if `deployment` resulted in failure.

```yaml
    finally:
    - name: rollback
      params:
        - name: deployment-state
          value: "$(tasks.deployment.status)"
      taskSpec:
        params:
          - name: deployment-state
        steps:
          - image: ubuntu
            name: check-deployment
            script: |
              if [ $(params.deployment-state) == "Failed" ]
              then
                echo "Deployment has failed, it's time to rollback!"
              fi
```

| State       | Description                                                                                                                                                                                                                                                                                                                   |
|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Succeeded` | The `pipelineTask` was successful i.e. a respective pod was created and completed successfully. The `pipelineTask` had a `taskRun` with `Succeeded` `ConditionType` and  `True` `ConditionStatus`.                                                                                                                            |
| `Failed`    | The `pipelineTask` failed i.e. a respective pod was created but exited with error. The `pipelineTask` has a `taskRun` with `Succeeded` `ConditionType`,  `False` `ConditionStatus` and have exhausted all the retries.                                                                                                        |
| `None`      | no execution state available either (1) the `pipeline` stopped executing `dag` tasks before it could get to this task i.e. this task was not started/executed  or (2) the `pipelineTask` is `skipped` because of `when expression` or one of the parent tasks was `skipped`. It is part of `pipelineRun.Status.SkippedTasks`. |

### User Stories

A `pipeline` author can design a `finally` task which can send success notification or failure notification depending
on the execution status. 

## Test Plan

All necessary e2e and unit tests will be added.

## Drawbacks

* Missing access to the entire context of `pipelineRun` and/or `taskRun`.

## Alternatives

* If the states defined in this [Proposal](#proposal) are not clear, one alternative is to change these states and align them
to `pipelineRun` [execution status](https://github.com/tektoncd/pipeline/blob/main/docs/pipelineruns.md#monitoring-execution-status) (`Unknown`, `True`, `False`). Also change the proposed variable pattern to match these states.

* Another alternative is to add more states such as `Started`, `Running`, and `Cancelled` if the proposed states are
not sufficient for your use cases.

* We chose to name this variable `$(tasks.<pipelineTask>.status)`, an alternative (original proposal) had it named as
`$(context.pipelineRun.tasks.<pipelineTask>.status)`. Original proposal had it as context variable since this variable
does not have to be mapped to any `pipeline` param. Also, Tekton controller populates it with an appropriate value for the
`pipeline` author. But an alternative name was chosen for these reasons:
(1) The variable name in original proposal was too verbose with extra `context.pipelineRun` as a prefix.
(2) This name follows `JSONPath` syntax, representing `spec` as a root element with `$` and `.` operator as the child
element resulting into `spec.tasks.<pipelineTask>.status`.

## References (optional)

* https://github.com/tektoncd/pipeline/issues/1020
* https://github.com/tektoncd/pipeline/pull/3390
* https://docs.google.com/document/d/1eJBb2VHuSTbrIWfPE3TGdRRfdbJsRCOBIqfTwx9M3H8/edit#
