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
  breakpoint:
    onFailure: true
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
