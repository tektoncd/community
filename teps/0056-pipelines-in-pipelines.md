---
status: proposed
title: Pipelines in Pipelines
creation-date: '2021-03-08'
last-updated: '2022-05-03'
authors:
- '@jerop'
- '@abayer'
see-also:
- TEP-0044
- TEP-0050
- TEP-0059
- TEP-0084
- TEP-0090
- TEP-0100
---

# TEP-0056: Pipelines in Pipelines

<!-- toc -->
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Composability](#composability)
    - [Reusability](#reusability)
    - [Failure Strategies](#failure-strategies)
    - [Skipping Strategies](#skipping-strategies)
    - [Data Locality and Pod Overhead](#data-locality-and-pod-overhead)
    - [Software Supply Chain Security](#software-supply-chain-security)
    - [Fanning Out Pipelines](#fanning-out-pipelines)
  - [Requirements](#requirements)
  - [References](#references)
<!-- /toc -->

## Summary

Today, users can define and execute `Tasks` and `Custom Tasks` in `Pipelines`. In this TEP, we propose 
allowing users to define and execute `Pipelines` in `Pipelines`, alongside `Tasks` and `Custom Tasks`.

## Motivation

A `Pipeline` is a collection of `PipelineTasks` that are connected through resource dependencies (such as `Results`)
and ordering dependencies (via `runAfter`). A `Pipeline` is executed as a directed acyclic graph where each 
`PipelineTask` is a node, the ordering & resource dependencies define edges, and connected `PipelineTasks` make up 
`Branches`. A `Pipeline` is executed through a `PipelineRun` that creates a corresponding `TaskRun` for each 
`PipelineTask` in the `Pipeline`.

While the above workflow is simple, it presents the following challenges and limitations:
- [Composability](#composability)
- [Reusability](#reusability)
- [Failure Strategies](#failure-strategies)
- [Skipping Strategies](#skipping-strategies)
- [Data Locality and Pod Overhead](#data-locality-and-pod-overhead)
- [Software Supply Chain Security](#software-supply-chain-security)
- [Fanning Out Pipelines](#fanning-out-pipelines)

### Composability

Today, a subset of `Tasks` in a `Pipeline` cannot be grouped together as a unit of execution within the `Pipeline`.
Users need to define a set of `Tasks` as a complete unit of execution. The grouping of sets of `Tasks` as units of
execution would also improve visualization of `Pipelines`.

As a `Pipeline` author, I need to define a set of `Tasks` as a complete unit of execution within a `Pipeline`. For
example, I have 5 `Tasks` that apply templates including a `DeploymentConfig`. After the 5 `Tasks` are completed,
I have 3 other `Tasks` that add `ConfigMaps` and `Secrets` to the `DeploymentConfig`. I need to specify that the second
set of `Tasks` all need to wait for the first set of `Tasks` to complete execution. Today, I'd have to add each of the
5 `Task` names to the `runAfter` section of each of the 3 `Task` names - adding up to 15 items in `runAfter` that I
have to maintain.

```
                                   git-clone
                                       |
                                       v
                                     build
                                       |
                                       v
           ----------------------------------------------------------
           |              |            |             |              |
           v              v            v             v              v          
    apply-configmap   apply-pvc   apply-route   apply-service     apply-dc
    ----------------------------------------------------------------------
               |                   |                       |
               v                   v                       v   
          add-configmap    add-columna-service       add-kafka-config      
          ------------------------------------------------------------
                                   |                           
                                   v                           
                                deploy
```

Instead, I want to define and distribute `apply-config` set of 5 `Tasks` and `add-config` set of 3 `Tasks` so that I
can specify that the latter waits for the former to complete execution.

```                           
       git-clone
           |                           
           v                           
         build 
           |
           v 
      apply-config
           |                           
           v                           
       add-config 
           |
           v 
        deploy
```

For further information, read [Tekton Pipelines Issue #2134][issue-2134] and [Tekton Pipelines Issue #4067][issue-4067].

### Reusability

Today, a subset of `Tasks` in a `Pipeline` cannot be distributed as a unit of execution within `Pipelines`. As 
such, users have to specify those related `Tasks` separately and repeatedly across many `Pipelines`.

As a `Pipeline` author, I need to define a set of `Tasks` as a complete unit of execution that I can share across
`Pipelines`. I need to define a `Pipeline` with `set-status`, `unit-tests` and `set-status` `Tasks`, where the 
first `Task` sets the commit to pending and the last `Task` sets the commit to success or failure. I need to 
distribute this `Pipeline` so that it can be reused across multiple `Pipelines`.

For example, I can define and distribute `set-sta` set of `Tasks` and `testing` set of `Tasks`:

```
        git-clone                     
           |                           
           v
 run-unit-tests-with-status
           |                           
           v
       run-scans
```

Where `run-unit-tests-with-status` is made up of `set-status`, `unit-tests` and `set-status` set of `Tasks`:

```                           
        set-status
           |                           
           v                           
       unit-tests 
           |
           v 
        set-status
```

For further information, read [Tekton Pipelines Issue #2134][issue-2134] and [Tekton Pipelines Issue #4067][issue-4067].

### Failure Strategies

Today, when a `Task` in a `Branch` fails, it stops the execution of unrelated `Branches` and the `Pipeline` as a whole.
When `Tasks` are specified in independent `Branches`, there are no dependencies between them, so users may expect that
a failure in one `Branch` would not stop the execution of the other `Branch`.

Users need a way to prevent the failure of unrelated `Tasks` from affecting the execution of set of related `Tasks`
that should execute to completion once the first one has started.

As a `Pipeline` author, I need to decouple failures in unrelated sets of `Tasks`. For example, I can design a
`Pipeline` where `lint` might fail, but the `unit-tests`, `integration-tests` and `report-test-results` will 
continue executing so that I can get the test results without a rerun of the `Pipeline`.

```
          lint                     unit-tests
           |                           |
           v                           v
   report-linter-output        integration-tests 
                                       |
                                       v 
                              report-test-results
```

The above is possible because we don't interrupt execution upon first failure, instead we don't schedule anything 
new and wait for ongoing execution to complete.

For related work, read [TEP-0050][tep-0050].

### Skipping Strategies

Today, users guard the execution of a `PipelineTask` using `when` expressions. The declared `when` expression are 
evaluated before a `PipelineTask` is executed. If the `when` expressions evaluate to `"false"`, the `PipelineTask` 
is skipped and the dependent `PipelineTasks` continue execution. To guard a `PipelineTask` and its dependent
`PipelineTasks`, a user has to cascade the `when` expressions to the dependent `PipelineTasks` - this is verbose and 
error-prone as shown in the example below.

As a `Pipeline` author, I need to guard `manual-approval` and its dependent `Tasks` - `build-image`, `deploy-image` 
and `slack-msg` - in a `Pipeline` based on the git operation triggering the `Pipeline` being a merge action. Today, 
I'd have to cascade that `when` expression across the four `PipelineTasks`.
```
                                     tests
                                       |
                                       v
                                 manual-approval
                                 |            |
                                 v        (approver)
                            build-image       |
                                |             v
                                v          slack-msg
                            deploy-image
```

I need to combine those four `PipelineTasks` into one `Pipeline` - let's refer to this `Pipeline` as 
`approval-build-deploy-slack`:

```
                                 manual-approval
                                 |            |
                                 v        (approver)
                            build-image       |
                                |             v
                                v          slack-msg
                            deploy-image
```

Then, I can guard and execute the above `Pipeline` within the main `Pipeline`:

```
                                     tests
                                       |
                                       v
                          approval-build-deploy-slack
```

Users have been using the `Pipeline` in `Pipeline` `Custom Task` to guard a `PipelineTask` and its dependent 
`PipelineTasks`. For further information, read the [documentation][when] and [TEP-0059][tep-0059]. 

### Data Locality and Pod Overhead

In [TEP-0044][tep-0044], we are exploring supporting executing a `Pipeline` in a `Pod` to provide data locality and
reduce pod overhead. Users will need a way to group a set of `Tasks` in a `Pipeline` that should execute in a `Pod`.

As a `Pipeline` author, I need to define a subset of `Tasks` in a `Pipeline` that should execute in a `Pod`. For 
example, I need `fetch-source`, `unit-tests` and `upload-results` set of `Tasks` to execute in one `Pod` while 
`update-slack` to execute in its own `Pod`:

```
      fetch-source                     
           |                           
           v
       unit-tests
           |                           
           v
     upload-results
           |          
           v
     update-slack
```

I need to combine `fetch-source`, `unit-tests` and `upload-results` set of `Tasks` into one `Pipeline` - let's 
refer to this `Pipeline` as `fetch-test-upload`:

```
      fetch-source                     
           |                           
           v
       unit-tests
           |         
           v
     upload-results
```

Then, I can execute the above `Pipeline` in a `Pod` within the main `Pipeline`:

```
    fetch-test-upload               
           |                           
           v
     update-slack
```

### Software Supply Chain Security

In [TEP-0084][tep-0084], we are exploring generating `PipelineRun` level provenance in *Tekton Chains* to meet
[SLSA][slsa] L2 requirements and support secure software supply chain. Users will need to validate the provenance 
generated from a set of `Tasks` in a `Pipeline` before proceeding with execution.

As a `Pipeline` author, I need to define a subset of `Tasks` in a `Pipeline` whose provenance I need to validate 
before executing subsequent Tasks. For example, I need `fetch-source` and `build-image` end-to-end provenance validated 
before executing `deploy-image`:

```
      fetch-source                     
           |                           
           v
      build-image
           |                           
           v
     deploy-image
```

I need to combine `fetch-source` and `build-image` set of `Tasks` into one `Pipeline` - let's refer to this 
`Pipelines` as `fetch-source-build-image`: 

```
      fetch-source                     
           |                           
           v
      build-image
```
Then I can validate the end-to-end provenance generated from the above `Pipeline` before executing `deploy-image`:

```
fetch-source-build-image
           |                           
           v
     deploy-image
```

In addition, a user [described][slack] how `Pipelines` in `Pipelines` would allow them to define and distribute 
`Pipelines` to meet their security requirements, including separation of concerns between different roles:

> We want to use different Pipelines for building images and for scanning vulnerabilities because they are built by
different people: developers and security experts. Adding the Tasks to scan images in all Pipelines that build them is
less maintainable. Pipelines in Pipelines fits perfectly for this.

### Fanning Out Pipelines

In [TEP-0090][tep-0090], we proposed fanning out `PipelineTasks` with substitutions from combinations of `Parameters` 
in a `Matrix`. So far, it'd support fanning out `Tasks` into multiple `TaskRuns` and `Custom Tasks` into multiple 
`Runs`. Users need a way to fan out `Pipelines` into multiple `PipelineRuns` as well. 

As a `Pipeline` author, I have a `Pipeline` with several `Tasks` that validate a repository meets compliance and 
security requirements then sends out a notification with the outcomes to the security team. For example, the `Tasks` 
include `fetch-source`, [`scorecard`][scorecard], [`codeql`][codeql] and `notification`:

```
      fetch-source                     
           |                           
           v
       scorecards
           |                           
           v
        codeql
           |          
           v
      notification
```

The above `Pipeline` needs to be run on several repositories in my organization; I need to pass an array repository 
names as a `Parameter` to a `PipelineTask` that has the above `Pipeline` within a `Pipeline`.

In addition, a user [shared][matrix-uc] a related use case for supporting `Matrix` at the `Pipeline` level:

> There is a Pipeline which clones a node-based project and then we want to test that repo on different versions of 
nodejs, ie, node-12, node-14 and node-16.

## Requirements

1. Users should be able to define and distribute a set of `PipelineTasks` as a complete unit of execution. 
2. Users should be able decouple failures in unrelated sets of `PipelineTasks`.
3. Users should be able to pass inputs (such as `Parameters`) from the main-`Pipeline` to the sub-`Pipeline`.
4. Users should be able to access outputs (`Results`) from the sub-`Pipeline` in the main-`Pipeline`.
5. Users should be able to access sufficient information about the sub-`PipelineRun` from the status of the
main-`PipelineRun` to be able to fetch and access the sub-`PipelineRun`'s full status.
6. Users should be able to propagate actions from the main-`Pipeline` to the sub-`Pipeline`, such as deletion and
cancellation.

## References

- Issues
  - [Issue #2134: Support using a PipelineTask in the Pipeline CRD to run other Pipelines the same way we run a Task][issue-2134]
  - [Issue #4067: Add a gateway task or grouping for pipelines][issue-4067]
- Experiments
  - [Experimental Project Proposal][experiment-proposal]
  - [Pipelines in Pipelines Custom Task][pip]
- Proposals
  - [TEP-0044: Data Locality and Pod Overhead in Pipelines][tep-0044]
  - [TEP-0050: Ignore Task Failures][tep-0050]
  - [TEP-0059: Skipping Strategies][tep-0059]
  - [TEP-0084: End-to-End Provenance Collection][tep-0084]
  - [TEP-0090: Matrix][tep-0090]
  - [TEP-0100: Embedded TaskRuns and Runs Status in PipelineRuns][tep-0100]
  - [Original Proposal][doc]

[tep-0044]: 0044-data-locality-and-pod-overhead-in-pipelines.md
[tep-0050]: 0050-ignore-task-failures.md
[tep-0059]: 0059-skipping-strategies.md
[tep-0084]: 0084-endtoend-provenance-collection.md
[tep-0090]: 0090-matrix.md
[tep-0100]: 0100-embedded-taskruns-and-runs-status-in-pipelineruns.md
[pip]: https://github.com/tektoncd/experimental/tree/main/pipelines-in-pipelines
[doc]: https://docs.google.com/document/d/14Uf7XQEnkMFBpNYRZiwo4dwRfW6do--m3yPhXHx4ybk/edit
[experiment-proposal]: https://github.com/tektoncd/community/issues/330
[issue-4067]: https://github.com/tektoncd/pipeline/issues/4067
[issue-2134]: https://github.com/tektoncd/pipeline/issues/2134
[when]: https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guarding-a-task-and-its-dependent-tasks
[slack]: ../teps/images/0056-slack-thread.png
[slsa]: https://slsa.dev/
[scorecard]: https://github.com/ossf/scorecard
[codeql]: https://github.com/github/codeql
[matrix-uc]: https://github.com/tektoncd/community/pull/600#pullrequestreview-851817251
[status-test]: https://github.com/tektoncd/pipeline/issues/2134#issuecomment-631552148
