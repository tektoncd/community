---
title: taskrun-breakpoint-on-failure
authors:
  - "@waveywaves"
creation-date: 2021-01-15
last-updated: 2021-03-21
status: proposed
---

# TEP-0042: TaskRun Breakpoint on Failure of Step 

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Controlling Step Lifecycle](#controlling-step-lifecycle)
    - [Failure of a Step](#failure-of-a-step)
    - [Halting a Step on failure](#halting-your-step-on-failure)
    - [Exiting breakpoint](#exiting-breakpoint)
  - [Debug Environment Additions](#debug-environment-additions)
    - [Mounts](#mounts)
    - [Debug Scripts](#debug-scripts)
  - [User Stories](#user-stories)
    - [CLI Integration](#cli-integration)
      - [Environment Access](#environment-access)
- [Alternative](#alternatives)
<!-- /toc -->

## Summary

Debugging TaskRuns can be tiresome. Re-running Tasks to figure out which part of a particular step is to blame would tax productivity.
By enabling breakpoint on failure for a TaskRun we should be able to halt a TaskRun at the failing step and get access to the
step environment to analyze cause of the failure. Unlike legacy systems, this allows the user to debug TaskRuns while the TaskRun 
is still running, hence improving developer productivity and Pipeline debuggability.

## Motivation

Lack of live debugging for Pipelines.

### Goals

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  generateName: quarante-deux
spec:
  debug:
    breakpoint: ["onFailure"]
```

When the "breakpoint on failure" spec is mentioned in a particular TaskRun

- pause TaskRun on failure of a step
- failed step should not exit
- user should be able to get remote shell access to the step container to analyze and debug

### Non-Goals

The scope of this TEP does not exceed any other kind of breakpointing or debugging apart from breakpointing on failure and failure itself.

### Use Cases (optional)

This enhancement can allow a more interactive way of working with TaskRuns. CLI or IDE extensions could allow users to run a 
Task with breakpoint-on-failure and while the logs are being streamed, the user can be dropped to a shell in the breakpoint
failed step and allow the user to debug as they develop.

## Requirements

* To enable breakpoint on failure of a step, it would be necessary to update the Entrypoint to support lifecycle
changes when breakpoint on failure has been enabled.

* The step environment would have to have scripts which the user can use to clear the breakpoint or
mark the step as a success or a failure.

## Proposal

TaskRuns will add a new spec called `breakpoint` under which `onFailure` can be set to true to enable breakpointing
on failure.

### Controlling step lifecycle

#### Failure of a Step

The entrypoint binary is used to manage the lifecycle of a step. Steps are aligned beforehand by the TaskRun controller
allowing each step to run in a particular order. This is done using `-wait_file` and the `-post_file` flags. The former 
let's the entrypoint binary know that it has to wait on creation of a particular file before starting execution of the step.
And the latter provides information on the step number and signal the next step on completion of the step.

On success of a step, the `-post-file` is written as is, signalling the next step which would have the same argument given
for `-wait_file` to resume the entrypoint process and move ahead with the step. 

On failure of a step, the `-post_file` is written with appending `.err` to it denoting that the previous step has failed with
and error. The subsequent steps are skipped in this case as well, marking the TaskRun as a failure.

#### Halting a Step on failure

The failed step writes `<step-no>.err` to `/tekton/tools` and stops running completely. To be able to debug a step we would
need it to continue running (not exit), not skip the next steps and signal health of the step. By disabling step skipping, 
stopping write of the `<step-no>.err` file and waiting on a signal by the user to disable the halt, we would be simulating a 
"breakpoint".

In this breakpoint, which is essentially a limbo state the TaskRun finds itself in, the user can interact with the step 
environment using a CLI or an IDE. 

#### Exiting breakpoint

To exit a step which has been paused upon failure, the step would wait on a file similar to `<step-no>.breakpointexit` which 
would unpause and exit the step container. eg: Step 0 fails and is paused. Writing `0.breakpointexit` in `/tekton/tools`
would unpause and exit the step container.

### Debug Environment Additions 

#### Mounts

`/tekton/debug/scripts` : Contains scripts which the user can run to mark the step as a success, failure or exit the breakpoint.
Shared between all the containers.

`/tekton/debug/info/<n>` : Contains information about the step. Single EmptyDir shared between all step containers, but renamed 
to reflect step number. eg: Step 0 will have `/tekton/debug/info/0`, Step 1 will have `/tekton/debug/info/1` etc.

#### Debug Scripts

`/tekton/debug/scripts/debug-continue` : Mark the step as completed with success by writing to `/tekton/tools`. eg: User wants to mark
failed step 0 as a success. Running this script would create `/tekton/tools/0`.

`/tekton/debug/scripts/debug-continue-failure` : Mark the step as completed with failure by writing to `/tekton/tools`. eg: User wants to mark
failed step 0 as a success. Running this script would create `/tekton/tools/0.err`.

`/tekton/debug/scripts/debug-breakpointexit` : Mark the step as completed with failure by writing to `/tekton/tools`. eg: User wants to exit
breakpoint for failed step 0. Running this script would create `/tekton/tools/0` and `/tekton/tools/0.breakpointexit`.

### User Stories

#### CLI integration
The scenario below provides details on what the user should do to debug their failed task.

##### Environment access
1. Get Failed TaskRun name.
2. Provide as an argument to the cli to start the taskrun in debug mode. To get
   ```
   tkn taskrun debug failed-taskrun-1234 --on-failure --console-access
   ```
   In the above example we are recreating the TaskRun with the following patch.
   ```yaml
   metadata:
     name: failed-taskrun-1234-debug
   spec:
    debug: 
      breakpoint: ["onFailure"]
   ```
3. Once the TaskRun is created and a step fails, the TaskRun Pod will be in the Running state. Till that time the CLI will wait 
   for the TaskRun to stop executing (due to failure) and go into the limbo state which would be leveraged for debugging.
   The CLI will open a shell to the step container which would be a reimplementation of `kubectl exec -it`.



## Alternatives

1. *"Breakpoint" as a map in the debugSpec.*

    ```yaml
    debug:
      breakpoint: 
        onFailure: true
        beforeStep: []
        afterStep: []
    ```
    The above shows what it could look like if the user could provide more points where they can halt the TaskRun i.e. before and after certain steps. 

2. *"Breakpoint on failure" as a map.*

    Based on 1. we can say that there might come a time, if rerunning steps does become a reality (which is highly likely), the user would like to debug before the failure takes place by enabling, something like beforeFailure which would rerun the step and halt it before execution.

    ```yaml
    debug:
      breakpoint: 
        onFailure: 
          before: true
          after: true
        beforeStep: []
        afterStep: []
    ```

3. *Enums rock*

    Using a list instead of a map allow us to maintain the breakpoint locations in the Tekton API and not on the client side.

    - Add a breakpoint before and after the failure.

      ```yaml
      debug:
        breakpoint: ["beforeFailure", "onFailure"]
      ```

    - Create a breakpoint before and after execution of certain steps.
      The user provides the breakpoint location for before or after the step they want to debug; 
      followed by the name or the index number of the step itself. (Ordinal or Nominal step reference)

      ```yaml
      debug:
        breakpoint: ["before-push-to-registry", "after-3"]
      ```