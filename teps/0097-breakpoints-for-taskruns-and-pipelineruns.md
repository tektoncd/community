---
title: breakpoints-for-taskruns-and-pipelineruns
authors:
  - "@waveywaves"
creation-date: 2022-07-12
last-updated: 2022-07-12
status: implementable 
see-also:
  - TEP-0042
---

# TEP-0097: Breakpoints for TaskRuns and PipelineRuns

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [TaskRun Proposal](#taskrun-proposal)
  - [Breakpoint before/after a step](#breakpoint-beforeafter-a-step)
  - [Breakpoint on failure of a step (already implemented; will be moved to <code>breakpoints.onFailure</code> spec)](#breakpoint-on-failure-of-a-step-already-implemented-will-be-moved-to-breakpointsonfailure-spec)
    - [Controlling step lifecycle](#controlling-step-lifecycle)
      - [Failure of a Step](#failure-of-a-step)
      - [Halting a Step on failure](#halting-a-step-on-failure)
      - [Exiting breakpoint](#exiting-breakpoint)
  - [TaskRun Timeout Implications](#taskrun-timeout-implications)
  - [Debug Environment Additions](#debug-environment-additions)
    - [Mounts](#mounts)
    - [Debug Scripts](#debug-scripts)
- [PipelineRun Proposal](#pipelinerun-proposal)
  - [Breakpoint before or after a TaskRun](#breakpoint-before-or-after-a-taskrun)
    - [before TaskRun](#before-taskrun)
    - [after TaskRun](#after-taskrun)
    - [Dependent and Independent TaskRuns](#dependent-and-independent-taskruns)
  - [Breakpoint on failure of a TaskRun](#breakpoint-on-failure-of-a-taskrun)
  - [PipelineRun Timeout Implications](#pipelinerun-timeout-implications)
- [User Stories](#user-stories)
  - [CLI integration](#cli-integration)
    - [Environment access](#environment-access)
- [Alternatives](#alternatives)
<!-- /toc -->
## Summary

The previous TEP on debug, TEP-0042 focuses on breakpoint on failure in a TaskRun. This proposal expands on that groundwork to 
outline what breakpointing at specific steps looks like. The same theories have been used to also outline what breakpointing at
particular steps, and on failure in PipelineRuns looks like.

## Motivation

Lack of live debugging for Pipelines.

### Goals

Have an interface to debug TaskRuns and PipelineRuns at any stage of the Run in Tekton.

### Use Cases (optional)

This enhancement can allow a more interactive way of working with TaskRuns and PipelineRun. CLI or IDE extensions could allow users to run a 
Task, Pipeline with breakpoint-on-failure and manual breakpoints and while the logs are being streamed, the user can be dropped to a shell in the breakpoint
failed step and allow the user to debug as they develop.

## Requirements

* To enable breakpoint on failure, before or after a Step in a TaskRun.

* To enable breakpoint on failure, before or after a TaskRun in a PipelineRun.

## TaskRun Proposal

### Breakpoint before/after a step
The `breakpoint` spec would contain the `beforeSteps` and `afterSteps` specs which are arrays containing names of steps
which the user plans on debugging.

```yaml
  debug:
    breakpoints:
      onFailure: "enabled"
      beforeSteps: ["test-js"]
      afterSteps: ["push-to-registry"]
      
```

### Breakpoint on failure of a step (already implemented; will be moved to `breakpoints.onFailure` spec)
The `breakpoints` spec would contain `onFailure` spec which can be set to true to enable breakpoint-ing on failure.

When the "breakpoint on failure" spec is mentioned in a particular TaskRun

- pause TaskRun on failure of a step
- failed step should not exit
- user should be able to get remote shell access to the step container to analyze and debug

#### Controlling step lifecycle

##### Failure of a Step

The entrypoint binary is used to manage the lifecycle of a step. Steps are aligned beforehand by the TaskRun controller
allowing each step to run in a particular order. This is done using `-wait_file` and the `-post_file` flags. The former 
let's the entrypoint binary know that it has to wait on creation of a particular file before starting execution of the step.
And the latter provides information on the step number and signal the next step on completion of the step.

On success of a step, the `-post-file` is written as is, signalling the next step which would have the same argument given
for `-wait_file` to resume the entrypoint process and move ahead with the step. 

On failure of a step, the `-post_file` is written with appending `.err` to it denoting that the previous step has failed with
and error. The subsequent steps are skipped in this case as well, marking the TaskRun as a failure.

##### Halting a Step on failure

The failed step writes `out.err` to `/tekton/run/<step-no.>` and stops running completely. To be able to debug a step we would
need it to continue running (not exit), not skip the next steps and signal health of the step. By disabling step skipping, 
stopping write of the `out.err` file and waiting on a signal by the user to disable the halt, we would be simulating a 
"breakpoint".

In this breakpoint, which is essentially a limbo state the TaskRun finds itself in, the user can interact with the step 
environment using a CLI or an IDE. 

##### Exiting breakpoint

To exit a step which has been paused upon failure, the step would wait on a file similar to `<step-no>.breakpointexit` which 
would unpause and exit the step container. eg: Step 0 fails and is paused. Writing `out.breakpointexit` in `/tekton/run/0/`
would unpause and exit the step container.

### TaskRun Timeout Implications

In the process of debugging a TaskRun, there shouldn't be any interruption. To ensure this timeout will be set to max timeout
(no timeout) on the TaskRun. Alternatively, the timeout (in minutes) for debug can be specified as follows :-

```yaml
  debug:
    timeout: "120"
    breakpoints:
      onFailure: "enabled"
      beforeSteps: ["test-js"]
      afterSteps: ["push-to-registry"]
      
```

### Debug Environment Additions

#### Mounts

`/tekton/debug/scripts` : Contains scripts which the user can run to mark the step as a success, failure or exit the breakpoint.
Shared between all the containers.

`/tekton/debug/info/<n>` : Contains information about the step. Single EmptyDir shared between all step containers, but renamed 
to reflect step number. eg: Step 0 will have `/tekton/debug/info/0`, Step 1 will have `/tekton/debug/info/1` etc.

#### Debug Scripts

`/tekton/debug/scripts/debug-continue` : Mark the step as completed with success by writing to `/tekton/run/<step-no.>/`. eg: User wants to mark
failed step 0 as a success. Running this script would create `/tekton/run/0/out`.

`/tekton/debug/scripts/debug-continue-failure` : Mark the step as completed with failure by writing to `/tekton/run/<step-no.>/`. eg: User wants to mark
failed step 0 as a success. Running this script would create `/tekton/run/0/out.err`.

`/tekton/debug/scripts/debug-breakpointexit` : Mark the step as completed with failure by writing to `/tekton/run/<step-no.>/`. eg: User wants to exit
breakpoint for failed step 0. Running this script would create `/tekton/run/0/out` and `/tekton/run/0/out.breakpointexit`.

## PipelineRun Proposal

Breakpoints would be enabled on PipelineRuns in a way that the logic of putting the breakpoints in place will be in the 
hands of the TaskRun controller and the step entrypoint.

Using the below spec we will look at how this will work with the following example.
    
```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: quarante-deux-deux
spec:
  debug:
    breakpoints:
        onFailure: "enabled"
        beforeTasks: ["task-build-archive"]
        afterTasks: ["deploy-frontend"]
```

### Breakpoint before or after a TaskRun

Upon providing a before/after breakpoint for a particular Task in a PipelineRun, the TaskRun will inherit breakpoints as
follows. 

#### before TaskRun

Adding the name of the Task to `beforeTasks` spec will add a breakpoint before the first step of the TaskRun of the
Task mentioned in the spec.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: quarante-deux-deux
spec:
  debug:
    breakpoints:
      beforeTasks: ["task-build-archive"]
```

#### after TaskRun

Adding the name of the Task to `afterTasks` spec will add a breakpoint after the last step of the TaskRun of the 
Task mentioned in the spec.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: quarante-deux-deux
spec:
  debug:
    breakpoints:
      afterTasks: ["deploy-frontend"]
```

#### Dependent and Independent TaskRuns

Since a pipeline may be running several tasks in parallel, in case of breakpoints, multiple ones could be hit in parallel, the user will have the opportunity of interacting with all the tasks under debug. Tasks that do not depend on any task being debugged will continue to run and be scheduled normally.

### Breakpoint on failure of a TaskRun

When we provide `onFailure` as `enabled` in the `breakpoint` spec of the PipelineRun, this will be applied to all the children TaskRun under
this PipelineRun and hence `onFailure` will be present in the breakpoints of all the children TaskRuns.

> Note: we typically avoid boolean fields due to [k8s api guidelines](https://github.com/kubernetes/community/blob/17a75cb315905854699d1a37c06dd1a5421b8577/contributors/devel/sig-architecture/api-conventions.md?plain=1#L589-L592) 
> that state "Think twice about bool fields. Many ideas start as boolean but eventually trend towards a small set of mutually exclusive options."
> so we use a string filed with value `enabled` to enable the onFailure breakpoint.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: quarante-deux-deux
spec:
  debug:
    breakpoints:
      onFailure: "enabled"
```

### PipelineRun Timeout Implications

In the process of debugging a PipelineRun, there shouldn't be any interruption. To ensure this timeout will be set to max timeout
(no timeout) on the PipelineRun. Alternatively, the timeout (in minutes) for debug can be specified as follows :-

```yaml
  debug:
    timeout: "120"
    breakpoints:
      onFailure: "enabled"
      beforeTasks: ["task-build-archive"]
      afterTasks: ["deploy-frontend"]
      
```

## User Stories

### CLI integration
The scenario below provides details on what the user should do to debug their failed task.

#### Environment access
1. Get Failed TaskRun name.
2. Provide as an argument to the cli to start the TaskRun in debug mode. To get
   ```
   tkn taskrun debug failed-taskrun-1234 --on-failure --console-access
   ```
   In the above example we are recreating the TaskRun with the following patch.
   ```yaml
   metadata:
     name: failed-taskrun-1234-debug
   spec:
    debug: 
      breakpoint: 
        onFailure: "enabled"
   ```
3. Once the TaskRun is created and a step fails, the TaskRun Pod will be in the Running state. Till that time the CLI will wait 
   for the TaskRun to stop executing (due to failure) and go into the limbo state which would be leveraged for debugging.
   The CLI will open a shell to the step container which would be a reimplementation of `kubectl exec -it`.

## Alternatives

1. *"Breakpoints" as a map in the debugSpec.* (Used right now)

    ```yaml
    debug:
      breakpoints: 
        onFailure: "enabled"
        beforeSteps: []
        afterSteps: []
    ```
    The above shows what it could look like if the user could provide more points where they can halt the TaskRun i.e. before and after certain steps. 

    _Pros_: 
    - Breakpoints can be cleanly segregated between onFailure beforeSteps and afterSteps.
    - In case new onFailure options come, they can be added via strings. 
    _Cons_:
    - Parsing using string matching for the onFailure options need to added to the controller.

2. *"Breakpoint on failure" as a map.*

    Based on 1. we can say that there might come a time, if rerunning steps does become a reality (which is highly likely), the user would like to debug before the failure takes place by enabling, something like beforeFailure which would rerun the step and halt it before execution.

    ```yaml
    debug:
      breakpoint: 
        onFailure: 
          before: true
          after: true
        beforeSteps: []
        afterSteps: []
    ```

    _Cons_:
    - In case new onFailure options come, new API changes need to be introduced. 

3. *Enums rock* (Not applicable anymore)

    Using a list instead of a map allow us to maintain the breakpoint locations in the Tekton API and not on the client side.

    - Add a breakpoint before and after the failure.

      ```yaml
      debug:
        breakpoints: ["beforeFailure", "onFailure"]
      ```

    - Create a breakpoint before and after execution of certain steps.
      The user provides the breakpoint location for before or after the step they want to debug; 
      followed by the name or the index number of the step itself. (Ordinal or Nominal step reference)

      ```yaml
      debug:
        breakpoints: ["before-push-to-registry", "after-3"]
      ```

    _Cons_:
    - The different kinds of breakpoints are not segregated properly and need to remember the format while writing the breakpoints instead of remembering just the name of the step/taskrun. 