---
title: task-results-in-final-tasks
authors:
  - "@pritidesai"
  - "@bobcatfish"
creation-date: 2020-07-16
last-updated: 2020-07-16
status: proposed
---

# TEP-NNNN: Task Results in Final Tasks

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
- [Design Details](#design-details)
- [Advantages](#advantages)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
<!-- /toc -->

## Summary

A `Task` in a `Pipeline` can emit `Results` which can be consumed by any other `Tasks` within the same
`Pipeline`. `Result` of a `Task` in a `Pipeline` is received through the input parameter using variable
substitution such as `$(tasks.<pipeline-task-name>.results.<result-name>)`.

Today, final `Tasks` can not receive `Results` of any other `Tasks` in a `Pipeline`. This feature is
limited to non-finally `Tasks` of a `Pipeline`.

This proposal is enabling final `Tasks` to receive `Results` of any `Tasks` within the same `Pipeline`.

## Motivation

A `Pipeline` author wants to clean up resources that is done by the final `Tasks` in the `Pipeline`.
The resources are acquired by the setup `Task` which has the names of resources. The clean up `Tasks`
must clean up only those resources.

Also, cleanup must be done only if the setup was successful but regardless of the failure of the rest of
the `Tasks` in the `Pipeline`.

```none
setup
  |
  | e.g. Project Name
  v
cleanup
```

### Goals

One goal of this proposal is to allow final `Tasks` to receive `Results` from non-finally `Tasks`.

Second goal of this proposal is to determine what happens to the final `Task` when referenced
task results are not initialized because either dependent task failed or dependent task skipped
due to its own condition or if its parent was skipped.

### Non-Goals

This proposal is not enabling final `Task` to receive `Results` from other final `Tasks`.

This proposal is also not enabling final `Tasks` to produce `Task` `Results`.

## Proposal

Allow a finally `Task` to get a value from a non-finally `Task` via a `Task` `Result`.
If the `Task` producing the value fails, the finally `Task` that requires that value will be marked as failed.
That final `Task` will be `attempted` i.e. evaluated by the `Pipeline Controller` for execution,
but the validation will fail before the `TaskRun` is created since the required `Result` is not available.
However if the `Task` being attempted has a default value for that parameter, it can still run,
using the default when result is not available.

### User Stories

A `Pipeline` author can send the name of the project to finally task after non-finally task creates/acquires
resources for that project. The finally `Task` can then clean up those project resources regardless of the
failure of the rest of the `Tasks` in the Pipeline.

## Design Details

`Tasks` can produce one or more execution `Results` under `/tekton/results/` by specifying `results`
in the `Task` specification:

```yaml
spec:
  results:
    - name: leased-resource
      description: The name of the leased resource
  steps:
```

This task produces a result file at `/tekton/results/leased-resource`.

Any other `Pipeline` `Tasks` can use these `Results` as parameter values through variable substitution:

```yaml
spec:
  tasks:
    - name: boskos-release
      params:
        - name: leased-resource
          value: $(tasks.boskos-acquire.results.leased-resource)
```

No need to specify explicit runAfter here, `Tekton` infers the execution order by setting `boskos-acquire`
as a dependency so that the task emitting the referenced results executes before the task that consumes them.

Similar to non-final tasks, final task use `Results` through variable substitution:

```yaml
spec:
 tasks:
   - name: boskos-acquire
     taskRef:
       name: boskos-acquire
   - name: do-stuff-with-resource
     taskRef:
       name: do-stuff-with-resource
     params:
       - name: resource-name
         value:  $(tasks.boskos-acquire.results.leased-resource)
 finally:
   - name: boskos-release
     taskRef:
       name: boskos-release
     params:
       - name: leased-resource
         value:  $(tasks.boskos-acquire.results.leased-resource)
```

**Note:** Today final tasks are executed all in parallel and can not depend on any other `Task` in the `Pipeline`.
With adding support for `Task` `Results`, we are introducing dependencies to finally `Tasks` but that
does not change scheduling of finally tasks. All final tasks will still be executed in parallel after
all non-final tasks finishes.

**Q. What happens to `Pipeline` when the dependent task `boskos-acquire` either failed or not executed and
the task result `leased-resource` is not initialized?**

**A.** The finally `Task` `boskos-release` is attempted but declared failure since the task result
`leased-resource` is not initialized. Pipeline controller logs the reason of this failure as invalid result
reference `InvalidTaskResultReference`. `Pipeline` continues executing rest of the final tasks and exits with failure.

**Q. What happens when the dependent `Task` succeeds but the `Task` `Result` is empty?**

**A.** It could be possible that the task author intentionally chooses to leave the `Task` `Result` empty
(creating an empty file at `/tekton/results/`). `Pipeline` leaves that param value empty and executes
the final task. Empty `Task` `Result` is considered a valid value and results in successful variable
substitution. The error handling of such empty `Task` `Result` is left to the final `Task` author.

**Q. Can a final `Task` produce `Task` `Results`?**

**A.** Nope, this proposal does not enable final tasks to produce `Task` `Results`.


**Q. Explain the overall workflow.**

**A.**

```
                   ------------------------------------------
                  |             Param Validation              |
                  | (required params provided and their types)|
                   ------------------------------------------
                                    |
                                    V
                   -------------------------------------------
                  | Retrieve Execution Queue (All Final Tasks)|
                   -------------------------------------------
                                    |
                                    V
                -------------------------------------------------
               | Validate and Apply Results from Dependent Tasks |
                -------------------------------------------------
                                    | (if the validation fails, declare that task failure but
                                    | continue executing rest of the final tasks)
                                    V
                    ------------------------------------
                   | Execute the Task and Create TaskRun |
                    ------------------------------------
```

## Advantages

* No API changes.

* Finally contract does not break and all final tasks are attempted.

* Consistent across non-final and final tasks.

* Finally tasks do not need to explicitly check if the Task they depend on ran or not

* This proposal is extensible with future param validation by reading default from `Task` specification, for example,
if `boskos-acquire` fails, `boskos-release` will still be executed with the default value `best-default-ever` for
`leased-resource` param.

```yaml
# Pipeline
spec:
  params:
    - name: owner-name
      default: "the-best-owner"
  tasks:
   - name: boskos-acquire
     taskRef:
       name: boskos-acquire
     params:
       - name: owner-name
         value: $(params.owner-name)
   - name: do-stuff-with-resource
     taskRef:
       name: do-stuff-with-resource
     params:
       - name: resource-name
         value:  $(tasks.boskos-acquire.results.leased-resource)
 finally:
   - name: boskos-release
     taskRef:
       name: boskos-release
     params:
       - name: leased-resource
         value:  $(tasks.boskos-acquire.results.leased-resource)
---

# Task
name: boskos-release
spec:
  params:
    - name: resource-name
      default: "best-default-ever"
```

> `PipelineRun` reads parameter defaults from `Pipeline` specification but in case of
parameters associated with `Task` `Results`, the default values will be used from the `Task` since
`Pipeline` has no direct mapping between `Pipeline` parameter and `Task` parameter.

## Test Plan

* e2e and unit tests

## Drawbacks

* One could argue that this proposal breaks the finally contract, no longer means "finally tasks always run",
it now means "finally tasks always run unless they depend on something and that fails". But `PipelineRun`
does attempt such finally task which we explicitly fail with the validation failure so it is considered
`ran` by the `PipelineRun` Controller.

## Alternatives

1. Allow dependency to specify explicit default under `results`

```yaml

results:
  - name: leased-resource
    description: The name of the leased resource
    default: "best-default-ever"
```

**Pros/Cons:**

* The default value will likely be invalid; a Task consuming this value as a param would have to understand
what an invalid value looks like and prepare for that case.

* Same default applies to all consumers of that result.

* Inconsistent when the same task is invoked as non-final and final task. This default only applies to
final `TaskRuns` and non-final `Tasks` are not allowed to have this kind of default.

2. Allow `Tasks` to express validation on params; use this to identify when a default has been supplied

In this option, we allow `Tasks` to specify default values for results. However we also let Tasks specify
validation on their params, and finally Tasks can use this to verify they got value arguments and so
should run. Use a syntax similar to the schema syntax proposed in #1393 to express validation.

3. Allow default for Task Result in PipelineTask

PipelineTask release-env can specify default to a task result proj-name of referenced task.
In absence of any default, task result is considered as required and the final task results in a
validation failure if proj-name is not initialized.

```yaml
   kind: Pipeline
   spec:
    finally:
     - name: release-env
        taskRef:
          Name: boskos-release
        params:
          - name: proj-name
            value: $(tasks.get-env.results.project)
            default: best-default-ever
```

4. Allow finally tasks to depend on other Tasks; do not run if they fail




