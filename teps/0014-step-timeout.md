---
title: Step Timeout
authors:
  - "@Peaorl"
creation-date: 2020-09-10
last-updated: 2020-09-10
status: implementable
---

# TEP-0014: Step timeout

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Design Details](#design-details)
  - [Caveats](#caveats)
    - [Resolution of a <code>Step</code> Timeout](#resolution-of-a--timeout)
- [Test Plan](#test-plan)
- [References](#references)
<!-- /toc -->

## Summary

A `Step` could end up executing longer than expected. Currently, Tekton does
not provide a way of terminating an overdue `Step`. Therefore, this TEP proposes
a `Step` timeout feature.

Implementing this TEP, every `Step` can be annotated with a `timeout` field.
If during runtime the `Step` execution time exceeds this timeout, the `Step`
is terminated. Moreover, any subsequently scheduled `Steps` within the `Task`
are canceled.

In case a `Step` timeout occurred, the `TaskRun` status field displays an
accompanying error message.


## Motivation
A `Task` author may want to specify a timeout for numerous reason.
A few example use cases are listed below:

-  A `Task` author may expect a `Step` to only take a short period of time. For
example, a `Task` author may expect a `Step` responsible for performing setup
to only require a few seconds. If for some reason the `Step` execution time
is much longer, it may be favorable to *fail fast*. As such, a supposedly
trivial `Step` can't stall or delay a `TaskRun`. As a result, a `Task` author
is able to troubleshoot sooner. Furthermore, potentially costly cluster
resources are released quicker.

- A dependency-fetching `Step` may hang because an external registry is
slowed down. In this case it may be better to *fail fast* and retry instead
of waiting for the connection to time out.

- A team has reduced the compilation time of their codebase and would like to
ensure that new changes do not increase the compilation time substantially.
They enforce this by setting a timeout on the compilation `Step` in their build
`Task` and run this `Task` against all new PRs.

Direct motivation for this TEP stems from
[this](https://github.com/tektoncd/pipeline/issues/1690) user story.

### Goals

- Provide the ability to terminate an overdue `Step`
- Cancel `Steps` originally scheduled after a timeout terminated `Step`

### Non-Goals

- Provide the ability to terminate an overdue `Sidecar`

## Requirements

1. Possibility to have a `Step` terminated after exceeding a `Task` author
specified timeout
1. Tekton should provide a reasonable timeout resolution of about 1 second at
most<a name="req2"></a>
1. `Steps` scheduled after a timeout terminated `Step` shall be canceled

## Proposal

`Task` authors will be able to annotate a `Step` with a `timeout` field as
displayed in the following example:
```yaml
steps:
  - name: sleep-then-timeout
    image: ubuntu
    script: | 
      #!/usr/bin/env bash
      echo "I am supposed to sleep for 60 seconds!"
      sleep 60
    timeout: 5s
```
In this example, the `Step` prints a message and intends to *sleep* for 60 seconds.
However, since a five second timeout is specified, Tekton terminates the `Step` after five seconds.

Subsequently, Tekton populates the `status.conditions.message` field in the initiating
`TaskRun` with the following message:  

`sleep-then-timeout exited because the step exceeded the specified timeout limit;`

Additionally, if successive `Steps` were specified, Tekton cancels all these
successive `Steps` and indicate this with *exit code* 1 under
`status.steps.terminated.exitCode` of the `TaskRun`.

### Risks and Mitigations

The duration of a timeout is entirely up to the `Task` author. It is therefore
the `Task` author's responsibility to ensure a timeout provides a `Step`
enough time to properly execute. Performance variability amongst clusters may
require a suitable margin on a timeout.

## Design Details

The root of the design is centered around the preexisting Tekton entrypoint
binary. This binary overrides the original entrypoint of the *container*
associated with a `Step`. The Tekton entrypoint binary executes the command
or script specified by a `Step`.

The design presented here essentially wires a timeout annotation from a
`Step` through to the Tekton entrypoint binary. The Tekton entrypoint binary
is modified to ensure it adheres to the specified timeout. Therefore, a
`Step` is automatically terminated once the timeout is exceeded.
Subsequently, Tekton writes a
*PostFile* indicating the `Step` has been terminated, thereby cancelling any
successive `Steps`.

In order to populate the `TaskRun` status with a timeout message, the Tekton
entrypoint binary writes a timeout `Result` of the `InternalTektonResultType`
kind. Based on this `Result`, the `TaskRun` status is [populated](#Proposal)
while the `Result` is filtered out from `Task` author related results (like
`PipelineResourceResults`) based on its kind.

### Caveats

#### Resolution of a `Step` Timeout

The resolution at which a `Step` timeout can be specified is the same as the
resolution of the [Duration
type](https://golang.org/pkg/time/#ParseDuration). The smallest resolution
supported by the Duration type is a nanosecond. Nevertheless, the
[motivation](#motivation) of this TEP is not to provide nanosecond resolution.
Instead, the aim is to provide a timeout that would [reasonably](#req2) meet
the `Task` authors expectations. E.g., a `Task` author may expect a `Step` to
execute for five seconds at most and therefore specify a six second timeout.

Technically, a hard requirement on the resolution can not be set because 
performance variability between cluster setups may introduce discrepancies.
However, as a reference, our tests have shown a resolution accuracy of about
10 ms on GKE clusters. This means that for a `Step` that has a 5 second
execution time, specifying a 5010 ms timeout will not cause a
timeout. On the other hand, a timeout specified between 5 seconds and 5010 ms
may cause the `Step` to timeout. Tekton tries to minimize overhead and therefore we do
not expect huge discrepancies with other clusters.

## Test Plan

* A unit test verifies the Tekton entrypoint binary can be timed out
* An integration test verifies a `Step` can be timed out
* An integration test verifies a timeout with a wide margin of 1 second will
not cause a `Step` timeout
  - Concretely: This test will verify that a `Step` supposed to *sleep* for 1
  second will not timeout in case a 2 second `Step` timeout has been
  specified

## References

[Issue #1690](https://github.com/tektoncd/pipeline/issues/1690)  
[PR #3087](https://github.com/tektoncd/pipeline/pull/3087)
