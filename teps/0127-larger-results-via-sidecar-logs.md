---
status: implementable
title: Larger Results via Sidecar Logs
creation-date: '2022-11-30'
last-updated: '2022-12-01'
authors:
- '@chitrangpatel'
- '@jerop'
see-also:
- TEP-0086
---

# TEP-0127: Larger Results via Sidecar Logs

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Feature Gate](#feature-gate)
  - [Logs Access](#logs-access)
  - [Size Limit](#size-limit)
  - [PipelineRun Status](#pipelinerun-status)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Interoperability](#interoperability)
  - [Simplicity](#simplicity)
  - [Performance](#performance)
  - [Security](#security)
- [Experiment Questions](#experiment-questions)
- [References](#references)
<!-- /toc -->

This TEP builds on the hard work of many people who have been tackling the problem over the past couple years,
including but not limited to:
- '@abayer'
- '@afrittoli'
- '@bobcatfish'
- '@dibyom'
- '@imjasonh'
- '@pritidesai'
- '@ScrapCodes'
- '@skaegi'
- '@tlawrie'
- '@tomcli'
- '@vdemeester'
- '@wlynch'

## Summary

Today, `Results` have a size limit of 4KB per `Step` and 12KB per `TaskRun` in the best case - see [issue][4012]. 

The goal of [TEP-0086][tep-0086] is to support larger `Results` beyond the current size limits. TEP-0086 has many
alternatives but no proposal. This TEP proposes experimenting with one of the alternatives - `Sidecar` logs. This
allows us to support larger `Results` which are stored within `TaskRun` CRDs.

## Motivation

`Results` are too small - see [issue][4012]. The current implementation of `Results` involves parsing from disk and
storing as part of the `Termination Message` which has a limit of 4KB per `Container` and 12KB per `Pod`. As such,
the size limit of `Results` is 12KB per `TaskRun` and 4KB per `Step` at best.

To make matters worse, the limit is divided equally among all `Containers` in a `Pod` - see [issue][4808]. The more
the `Steps` in a `Task`, the less the size limit for `Results`. For example, if there are 12 `Steps` then each has
1KB in `Termination Message` storage to produce `Results`.

[TEP-0086][tep-0086] aims to support larger `Results`. It has many [alternatives][tep-0086-alts] but no proposal
because there's no obvious "best" solution that would meet all the requirements.

This TEP proposes experimenting with `Sidecar` logs to support larger `Results` that are stored within `TaskRun` CRDs.
This allows us to provide an immediate solution to the urgent needs of users, while not blocking pursuit of the other
alternatives.

In addition, the [documented guidance][docs] is that `Results` are used for outputs less than 1KB while `Workspaces`
are used for larger data. Supporting larger `Results` up to the CRD limit allows users to reuse `Tasks` in more
scenarios without having to change the specification to use `Workspaces` upon hitting the current low size limit of
4KB per `TaskRun`.

> As a general rule-of-thumb, if a `Result` needs to be larger than a kilobyte, you should likely use a `Workspace`
to store and pass it between `Tasks` within a `Pipeline`.

### Goals

The main goal of this TEP is to support larger `Results` via `Sidecar` logs. The `Results` are stored in the `TaskRun`,
therefore they are limited by the size limit of a `TaskRun` CRD - 1.5MB. 

### Non-Goals

The following are out of scope for this TEP:

1. Solving use cases that requires really large `Results` beyond the size limit of a CRD - 1.5MB.

2. Addressing other [alternatives][tep-0086-alts] for larger `Results` that are listed in [TEP-0086][tep-0086].
   However, this approach should co-exist with the other alternatives when they are implemented as experiments as well.

### Use Cases

1. Support signing `Results` using SPIRE for non-falsifiable provenance that's required for [SLSA L3][L3]. As described
   in [TEP-0089][tep-0089], the signatures and certificates used to verify `Results` are stored alongside the `Results`
   in the `Termination Message`. This exacerbates the size limit issues for `Results`. The size of the certificate is
   800 bytes and the size of signatures is approximately 100 bytes per `Result`.
   
   > For now, signatures of the `Results` will be contained within the `Termination Message` of the `Pod`, alongside
     any additional material required to perform verification. One consideration of this is the size of the additional
     fields required. The size of the certificate needed for verification is about 800 bytes, and the size of the
     signatures is about 100 bytes * (number of `Results` + 1). The current `Termination Message` size is 4K, but there
     is TEP-0086 looking at supporting larger results.

2. Support emitting structured `Results`. For example, store the images produced by `ko` and all their copies to the
   various regional registries in a `TaskRun`. The release `Pipeline` has this use case, and it ran into the current
   size limit of 4096 bytes. As described in the [issue][4282], the images produced were 4572 bytes which didn't fit
   into `Results`. For further details about structured `Results`, see [TEP-0075][tep-0075] and [TEP-0076][tep-0076].

## Proposal

To support larger `Results`, we propose using stdout logs from a dedicated `Sidecar` to return a json `Result` object.
The `Pipeline` controller would wait for the `Sidecar` to exit and then read the logs based on a particular query and
append `Results` to the `TaskRun`.

The dedicated `Sidecar` will be injected alongside other `Steps`. The `Sidecar` will watch the `Results` paths of the
`Steps`. This `Sidecar` will output the name of the `Result` and its contents to stdout in a parsable pattern. The
`TaskRun` controller will access the stdout logs of the `Sidecar` then extract the `Results` and its contents.

After the `Steps` have terminated, the `TaskRun` controller will write the `Results` from the logs of the `Sidecar`
instead of using the `Termination Message`, hence bypassing the 4KB limit. This approach keeps the rest of the existing
functionality the same and does not require any external storage mechanism.

For further details, see the [demonstration][demo] of the [implementation][poc].

This proposal provides an opportunity to experiment with this solution to provide `Results` within the CRDs as we
continue to explore other alternatives, including those that involve external storage.

### Feature Gate

This feature will be gated using a `results-from` feature flag. This feature flag defaults to `"termination-message"`
for backwards compatibility - `Results` will continue to pass through `Termination Message`. 

Users can set the `results-from` feature flag to `"sidecar-logs"` to enable the larger `Results` through `Sidecar` logs:
```shell
kubectl patch cm feature-flags -n tekton-pipelines -p '{"data":{"results-from":"sidecar-logs"}}'
```

Other alternatives can use the `results-from` feature flag to introduce other approaches. For now, the field will only
accept `"termination-message"` or `"sidecar-logs"`. 

### Logs Access

This feature requires that the `Pipeline` controller has access to `Pod` logs. 

Users have to grant `get` access to all `pods/log` to the `Pipeline` controller:
```shell
kubectl apply -f config/enable-log-access-to-controller/
```

### Size Limit

The size limit per `Result` can be configured using the `max-result-size` feature flag, which takes the integer value
of the bytes.

The `max-result-size` feature flag defaults to 4096 bytes. This ensures that we support existing `Tasks` with only one
`Result` that uses up the whole size limit of the `Termination Message`.

If users want to set the size limit per `Result` to be something other than 4096 bytes, they can set `max-result-size`
by setting `max-result-size: <VALUE-IN-BYTES>`. The value set here cannot exceed the CRD size limit of 1.5MB; if it
does, the controller logs an error and uses the default value.

```shell
kubectl patch cm feature-flags -n tekton-pipelines -p '{"data":{"max-result-size":"<VALUE-IN-BYTES>"}}'
```

Even though the size limit per `Result` is configurable, the size of `Results` is limited by CRD size limit of 1.5MB.
If the size of `Results` exceeds this limit, then the `TaskRun` will fail with a message indicating the size limit has
been exceeded.

### PipelineRun Status

In [TEP-0100][tep-0100], we proposed changes to `PipelineRun` status to reduce the amount of information stored about
the status of `TaskRuns` and `Runs`. Now, the `PipelineRun` status is set up to handle larger `Results` in `TaskRuns`
without storage issues.

For `ChildReferences` to be populated, the `embedded-status` must be set to `"minimal"`. We recommend that the minimal
embedded status - `ChildReferences` - is enabled while migration is ongoing until it becomes the only supported status.
This will ensure that larger `Results` from its `TaskRuns` will not bloat the `PipelineRun` CRD.

## Design Details

The `Sidecar` will run a binary that:
- receives argument for `Results`' paths and names which are identified from `taskSpec.results` field - this allows the
  `Sidecar` to know the `Results` it needs to read.
- has `/tekton/run` volume mounted as [read-only][4227] where status of each `Step` is written.
- periodically checks for `Step` status in the path `/tekton/run`.
- when all `Steps` have completed, it immediately parses all the `Results` in paths and prints them to stdout in a
  parsable pattern.

For further details, see the [demonstration][demo] of the [implementation][poc].

## Design Evaluation

### Reusability

This proposal does not introduce any API changes to specification `Results`. The changes are in implementation details
of `Results`. The existing `Tasks` will continue to function as they are, only that they can support larger `Results`.

Even more, supporting larger `Results` upto the CRD limit allows users to reuse `Tasks` in more scenarios without
having to change the specification to use `Workspaces` upon hitting the current low size limit of 4KB per `TaskRun`.
This allows users to control execution, as needed by their context, without having to modify `Tasks` and `Pipelines`.

### Interoperability

Users may write `Tasks` that assume larger `Results` support. These `Tasks` would only work on *Tekton Pipelines*
installations that are configured to support it. This is a risk to `Task` interoperability which is mitigated by:
1. Hard limit on the size of `Results` which is the CRD size limit - 1.5MB.
2. Plan to support larger `Results` in the long run regardless of the implementation details.

### Simplicity

This proposal provides a simple solution that solves most use cases:
- Users don't need additional infrastructure, such as server or object storage, to support larger `Results`.
- Existing `Tasks` will continue to function as they do now, while supporting larger `Results`, without any API changes.

### Performance

Performance benchmarking with 20-30 `PipelineRuns`, each with 3 `TaskRuns` each with two `Steps`:
- Average `Pipeline` controller's CPU difference during `PipelineRun` execution: 1%
- Average `Pipeline` controller's Memory usage difference during `PipelineRun` execution: 0.2%
- Average `Pod` startup time (time to get to running state) difference: 3s per `TaskRun`

In the experiment, we will continue to measure the startup overhead and explore ways to improve it.

For further details, see the [performance metrics][performance].

### Security

This approach requires that the `Pipeline` controller has access to `Pod` logs. The `Pipeline` controller already has
extensive permissions in the cluster, such as read access to `Secrets`. Expanding the access even further is a concern
for some users, but is also acceptable for some users given the advantages. We will document the extended permissions
so that users can make the right choice for their own use cases and requirements.

There will be a validation check to ensure that users cannot inject their own `Sidecar` overtop of the one specified by
Tekton.

## Experiment Questions

These are some questions we plan to answer in the experiment:

- What impact does this change have on the startup and execution time of `TaskRuns` and `PipelineRuns`? Can we
  improve the performance impact? 

- How reliable is using `Sidecar` logs to process `Results`?

- How many users adopt this solution? How many are satisfied with it given the advantages and disadvantages? 
  We will conduct a user survey soon after the feature has been released.

## References

- Implementation:
  - [Implementation Pull Request][poc]
  - [Demonstration by Chitrang][demo]
- Tekton Enhancement Proposals:
  - [TEP-0075: Object Parameters and Results][tep-0075]
  - [TEP-0076: Array Results][tep-0076]
  - [TEP-0086: Larger Results][tep-0086]
  - [TEP-0089: Non-Falsifiable Provenance][tep-0089]
  - [TEP-0100: PipelineRun Status][tep-0100]
- Issues:
  - [Changing the way Results are stored][4012]
  - [Results, TerminationMessage and Containers][4808]
  - [Publish task fails, IMAGES result too large][4282]
- Prior Work:
  - [TEP-0086: Using logs emitted by the Task][tep-0086-logs]
  - [TEP-0086: Larger Results via Sidecar Logs][745]
  - [TEP-0086 Working Group Meeting Notes][notes]
  - [Tekton Data Interface - Problem Space][data-interface]

[docs]: https://tekton.dev/docs/pipelines/tasks/#emitting-results
[4012]: https://github.com/tektoncd/pipeline/issues/4012
[4808]: https://github.com/tektoncd/pipeline/issues/4808
[4282]: https://github.com/tektoncd/pipeline/issues/4282
[4227]: https://github.com/tektoncd/pipeline/issues/4227
[745]: https://github.com/tektoncd/community/pull/745
[L3]: https://slsa.dev/spec/v0.1/levels
[crd-size]: https://github.com/kubernetes/kubernetes/issues/82292
[demo]: https://drive.google.com/file/d/1NrWudE_XBqweomiY24DP2Txnl1yN0yD9/view
[poc]: https://github.com/tektoncd/pipeline/pull/5695
[performance]: https://github.com/tektoncd/community/pull/745#issuecomment-1206668381
[tep-0075]: ./0075-object-param-and-result-types.md
[tep-0076]: ./0076-array-result-types.md
[tep-0086]: ./0086-changing-the-way-result-parameters-are-stored.md
[tep-0086-alts]: ./0086-changing-the-way-result-parameters-are-stored.md#alternatives
[tep-0086-logs]: ./0086-changing-the-way-result-parameters-are-stored.md#using-logs-emitted-by-the-task
[tep-0089]: ./0089-nonfalsifiable-provenance-support.md
[tep-0100]: ./0100-embedded-taskruns-and-runs-status-in-pipelineruns.md
[notes]: https://docs.google.com/document/d/1z2ME1o_XHvqv6cVEeElljvqVqHV8-XwtXdTkNklFU_8/edit?usp=sharing
[data-interface]: https://docs.google.com/document/d/1XbeI-_4bFaBize3adQmSL6Czo8MXVvoYn6dJgFZJ_So/edit?usp=sharing
