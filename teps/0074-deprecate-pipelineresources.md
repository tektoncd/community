---
status: implemented
title: Deprecate PipelineResources
creation-date: '2021-07-14'
last-updated: '2023-03-21'
authors:
- '@bobcatfish'
- '@lbernick'
---

# TEP-0074: Deprecate PipelineResources

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Features that will replace PipelineResources functionality](#features-that-will-replace-pipelineresources-functionality)
  - [Images used in PipelineResources](#images-used-in-pipelineresources)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience](#user-experience)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Keep PipelineResources](#keep-pipelineresources)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

This Proposal builds on the hard work of many people who have been tackling the problem over the past couple years,
including but not limited to:

* @sbws
* @vdemeester
* @dlorenc
* @pmorie

## Summary

This TEP proposes deprecating the CRD [PipelineResource](https://github.com/tektoncd/pipeline/blob/main/docs/resources.md)
in its current form, and addressing each problem PipelineResources were solving with specific features (see
[Design details](#design-details) for more depth on how the listed replacements address the feature):

| PipelineResources Feature                                | Replacement                                                                                                                                                                                                                                                                                   |
|----------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Augmenting Tasks with steps that execute on the same pod | [TEP-0044 Decoupling Task composition from scheduling](https://github.com/tektoncd/community/blob/main/teps/0044-decouple-task-composition-from-scheduling.md)                                                                                                                                |
| Automatic storage provisioning                           | [volumeClaimTemplates](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md#volumeclaimtemplate), [TEP-0044 Decoupling Task composition from scheduling](https://github.com/tektoncd/community/blob/main/teps/0044-decouple-task-composition-from-scheduling.md) + catalog tasks |
| PipelineResource specific credential handling            | [TEP-0044 Decoupling Task composition from scheduling](https://github.com/tektoncd/community/blob/main/teps/0044-decouple-task-composition-from-scheduling.md)                                                                                                                                |
| Expressing typed inputs and outputs                      | [TEP-0075 Dictionary/object params and results](https://github.com/tektoncd/community/pull/479)                                                                                                                                                                                               |
| Reusable parameter bundles                               | [TEP-0075 Dictionary/object params and results](https://github.com/tektoncd/community/pull/479)                                                                                                                                                                                               |
| Contract around files provided or expected on disk       | [TEP-0030 Workspace paths](https://github.com/tektoncd/community/blob/main/teps/0030-workspace-paths.md)                                                                                                                                                                                      |

This still leaves the door open for adding a similar abstraction, but in the meantime, we can remove this contentious
concept from our API and move forward toward our [v1 Pipelines release](https://github.com/tektoncd/pipeline/issues/3548).

## Motivation

When we [brought Tekton Pipelines to beta in Mar 2020](https://github.com/tektoncd/pipeline/releases/tag/v0.11.0), we
[decided not to make PipelineResources beta](https://github.com/tektoncd/pipeline/blob/e76d4132ab2ecfbedc45a964f08a01022e2d4c14/docs/resources.md#why-arent-pipelineresources-in-beta).

We decided this after the exploration of [a world without PipelineResources](https://docs.google.com/document/d/1u6qO7CPtDnTOZMYFQ5ARysSOy8lfFeVw83C_5BxAKsw/edit),
during which [we identified some missing features that PipelineResources gave us](https://docs.google.com/document/d/1u6qO7CPtDnTOZMYFQ5ARysSOy8lfFeVw83C_5BxAKsw/edit),
primarily around volume management and duplication.

We went to beta with [the workspaces feature](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md) to
improve dealing with volumes without needing PipelineResources. Since then, in addition to
the other features they provide (see [design details](#design-details) for a complete list), the main feature
PipelineResources provide is the ability to "extend" Tasks by allowing Task authors to define core functionality,
and augment it with git cloning, file uploading, etc. however with issue such as:

* They made Tasks less reusable:
  * Using a PipelineResource in a Task couples the Task to this PipelineResource. For
    example, using a `git` PipelineResource in a Task made it so that it would not be possible to use that Task with
    data that was obtained any other way (e.g. downloaded from a bucket, stored in a different version control system).
    * The [storage PipelineResoruce](https://github.com/tektoncd/pipeline/blob/e76d4132ab2ecfbedc45a964f08a01022e2d4c14/docs/resources.md#storage-resource)
      did a better job of this in that it allowed for multiple storage backends to be used.
  * Task authors had to anticipate what PipelineResources would be useful to be used with them; if you wanted to use
    a PipelineResource with a Task that the author didn't anticipate (e.g. adding a storage upload at the end of a Task)
    the Task would need to be modified
* Tekton Pipelines ships with only
  [6 PipelineResource types](https://github.com/tektoncd/pipeline/blob/e76d4132ab2ecfbedc45a964f08a01022e2d4c14/docs/resources.md#resource-types)
  and extending these requires making changes to Tekton Pipelines. We've had several proposal for how to work
  around this:
  * [Tekton Pipeline Resource Extensibility](https://docs.google.com/document/d/1rcMG1cIFhhixMSmrT734MBxvH3Ghre9-4S2wbzodPiU/edit)
  * [Specializing Tasks: Possible designs](https://docs.google.com/document/d/1p8zq_wkAcwr1l5BpNQDyNjgWngOtnEhCYEpcNKMHvG4/edit)
  * [PipelineResources 2 uber Design Doc](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit)
* It was very hard to describe concretely what the purpose of PipelineResources is (a strong hint that the abstraction
  is not right):
  * Four of the types interact with external systems (git, pull-request, gcs, gcs-build). 
  * Five of them write files to a Task's disk (git, pull-request, gcs, gcs-build, cluster). 
  * One tells the Pipelines controller to emit CloudEvents to a specific endpoint (cloudEvent).
  * One writes config to disk for a Task to use (cluster).
  * One writes a digest in one Task and then reads it back in another Task (image).
  * Perhaps the one thing you can say consistently about the PipelineResource CRD is that it can create side-effects
    for your Tasks.
* The line between the functionality provided by PipelineResources and Tasks is not clear (especially after the addition
  of [results](https://github.com/tektoncd/pipeline/blob/e76d4132ab2ecfbedc45a964f08a01022e2d4c14/docs/tasks.md#emitting-results)
  and [workspaces](https://github.com/tektoncd/pipeline/blob/e76d4132ab2ecfbedc45a964f08a01022e2d4c14/docs/tasks.md#specifying-workspaces),
  PipelineResources predate both of these features):
  * User-definable Steps? This is what Tasks provide.
  * User-definable params? Tasks already have these.
  * User-definable "resource results"? Tasks have Task Results.
  * Sharing data between Tasks using PVCs? workspaces provide this for Tasks.

So the choice is: do we fix PipelineResources such that the above issues are mitigated, or do we remove them completely?
This proposal suggests that we remove them completely. A similar concept could still be added in the future, but it
could be designed from the start to avoid the problems we've run into, and meanwhile we can go ahead with our v1 plans
without having to solve this abstraction first (also the fact that this hasn't been fixed yet is a possible indication
that maybe this concept, at least in its current form, isn't required).

### Goals

* Get ready for [the v1 Tekton Pipelines release](https://github.com/tektoncd/pipeline/issues/3548) by either deciding
  to bring PipelineResources to beta and then v1, or removing them
* Finally address PipelineResources which have been languishing at alpha since our
  [Tekton Pipelines beta release in Mar 2020](https://github.com/tektoncd/pipeline/releases/tag/v0.11.0) but are
  [still confusingly part of these beta APIs](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-resources)
  (that is, beta Tasks and Pipelines are still coupled to these alpha types) in their APIs.

### Non-Goals

* State absolutely that a similar concept is not useful and should not be explored in the future: similar ideas have
  been popping up in different places, for example:
  * The pipelines-as-code [Repository CRD](https://github.com/openshift-pipelines/pipelines-as-code#features)
  * Not explicitly mentioned in the proposal but the concept has been discussed in the context of the
    [Tekton workflows feature](https://github.com/tektoncd/community/issues/464)
  * [On twitter](https://twitter.com/bobcatwilson/status/1408064403585441804)

### Use Cases

* As a user of Tekton Pipelines v1, I want to be able to:
  * Understand clearly the stability level of the CRDs I'm using
  * Know which components I should depend on and are likely to continue to be supported in the future
    * I want this to be clear in the documentation, examples, and dogfooding done on the project itself
* As a maintainer of Tekton Pipelines, I want to know if I should continue to fix bugs with and add features to
  PipelineResources

## Requirements

* When we create v1 versions of Tasks, Pipelines, TaskRuns and PipelineRuns, all alpha features (note that
  PipelineResources are currently alpha but are not guarded by any flag) should be behind 
  [the alpha api flag](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#customizing-the-pipelines-controller-behavior)
* Our documentation and examples should clearly recommend best practices for how to use Tekton Pipelines components
* Our dogfooding should provide guidelines for how we recommend using Tekton

## Proposal

1. ~~Update dogfooding to use [the experimental Pipeline to TaskRun custom task](https://github.com/tektoncd/experimental/pull/770)
   in at least one Pipeline as a POC that combining Tasks is a viable way to extend Tasks instead of using PipelineResources~~
   - Dogfooding already [uses](https://github.com/tektoncd/plumbing/blob/f266eeeb78b5bd46010d6f29d623488bfb644251/tekton/mario-bot/mario-github-comment.yaml#L57)
   the Pipeline to TaskRun custom task, showing that this is a viable strategy.
   - We should update dogfooding to use the latest approach to running a Pipeline in a pod, the experimental
   [ColocatedPipelineRun custom Task](https://github.com/tektoncd/experimental/tree/main/pipeline-in-pod)
1. ~~Mark PipelineResources as deprecated in our Pipelines documentation; announce it officially in the next
   Pipelines release.~~
1. ~~Update tutorials, examples (except those used for testing), and dogfooding Pipelines to not use PipelineResources.~~
1. ~~Continue to support `PipelineResources` in the Pipelines `v1beta1` API for at least 9 months after announcing their deprecation,
   following our [stability policy](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md).~~ `PipelineResources`
   are going to be removed since it has been 9 months after the deprecation announcement.

### Features that will replace PipelineResources functionality

- [ ] Update dogfooding to use [the experimental ColocatedPipelineRun custom task](https://github.com/tektoncd/experimental/tree/main/pipeline-in-pod)
  - [x] Update uses of `PipelineResources` in plumbing to use `Pipelines` instead of `Tasks` with `PipelineResources`
    - Configuration in [ci-workspaces](https://github.com/tektoncd/plumbing/tree/main/tekton/ci-workspace/jobs) represents
      `Pipeline` and `Task` usage which is being updated to use `workspaces` and `when expressions` and to no longer use
      `PipelineResources`
  - [ ] Update some or all resulting `Pipelines` to run "in a pod" using [the experimental ColocatedPipelineRun custom task](https://github.com/tektoncd/experimental/tree/main/pipeline-in-pod)
- [ ] [TEP-0075 Object/Dictionary support](https://github.com/tektoncd/community/pull/479) is implemented and promoted to beta
- [ ] [TEP-0076 Array support](https://github.com/tektoncd/community/pull/479) is implemented and promoted to beta
- [ ] [TEP-0044 Data Locality and Pod Overhead in Pipelines](https://github.com/tektoncd/community/blob/main/teps/0044-data-locality-and-pod-overhead-in-pipelines.md)
  is implemented at alpha
  - [ ] If the solution to TEP-0044 requires [TEP-0056 Pipelines in Pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md),
  this should also be in beta
  
### Images used in PipelineResources

PipelineResources are executed inside TaskRuns by running images that are built and published as part of Tekton Pipelines
releases. These same images are also used by
[the equivalent catalog Tasks](https://github.com/tektoncd/pipeline/blob/main/docs/migrating-v1alpha1-to-v1beta1.md#replacing-pipelineresources-with-tasks).

These images are versioned alongside Tekton Pipelines, regardless of whether they change or not.

The images are:

* [git-init](https://github.com/tektoncd/pipeline/tree/main/cmd/git-init)
  * Used in the catalog Tasks "git-clone" and "git-batch-merge"
* [pullrequest-init](https://github.com/tektoncd/pipeline/tree/main/cmd/pullrequest-init)
  * Used in the "pull-request" catalog Task, intended as a replacement for the pullrequest PipelineResource
* [kubeconfigwriter](https://github.com/tektoncd/pipeline/tree/main/cmd/kubeconfigwriter)
  * Used in the "kubeconfig-creator" catalog Task, intended as a replacement for the cluster PipelineResource
* [imagedigestexporter](https://github.com/tektoncd/pipeline/tree/main/cmd/imagedigestexporter)
  * No longer used in any catalog Tasks

If we deprecate PipelineResources, it doesn't make sense to keep these in the Tekton Pipelines codebase.

As part of [TEP-0079](./0079-tekton-catalog-support-tiers.md), the "git-clone" and "git-batch-merge" Tasks (plus a few others)
will be moved to a verified catalog maintained by the Tekton org, and the community catalog will be archived.
Code for the "git-init" image will be moved into the tektoncd-catalog/git-clone repo.
The "kubconfig-creator" and "pull-request" catalog Tasks will be deprecated, unless there are volunteers to maintain them.

Code for the pullrequest-init, kubeconfigwriter, and imagedigestexporter images should be removed.

Possible alternatives:

* Create a new repo `tektoncd/images` and move the code for these images there, where they can be
  maintained and released separately from Tekton Pipelines
* Keep the images in Tekton Pipelines and keep versioning them the way we currently do
* One repo per image (e.g. tektoncd/git) ("images" is so vague it might be hard to draw the line around what images
  we accept into this repo and which we don't)


### Risks and Mitigations

* Risk: Folks depending on PipelineResources may not get the functionality they are looking for without them
  * Mitigation: In [design details](#design-details) we attempt to enumerate the functionality that folks may be
    missing without PipelineResources and provide alternatives.
* Risk: Some of the alternatives listed in [design details](#design-details) are simply proposals and haven't yet been
  accepted
  * Mitigation: We progress the most critical of these along before updating this TEP to implemented at a beta level
    of stability:
    1. Get to an acceptable degree of confidence in a Task composition (within a Pipeline but running on one pod) based
       approach as viable alternative for getting PipelineResource like composition:
      1. Update dogfooding to use [pipeline-to-taskrun experimental custom task](https://github.com/tektoncd/experimental/pull/770))
         to prove that a Pipeline based approach can be viable
      1. Block on [TEP-0056 Pipelines in Pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md)
         getting to implementable (which would be required for a pipeline based composition approach), being implemented,
         and getting to a beta level of stability
    1. Block on [TEP-0075 Object/Dictionary support](https://github.com/tektoncd/community/pull/479) getting to
       implementable (which is itself blocked on [TEP-0076 Array support](https://github.com/tektoncd/community/pull/479)),
       being implemented, and being promoted from an alpha feature to beta
    1. Assume it is okay to accept this TEP while these are still WIP:
      * [TEP-0030 Workspace Paths](https://github.com/tektoncd/community/blob/main/teps/0030-workspace-paths.md)): this
        functionality doesn't seem to be as important to any users as the rest of the PipelineResources features
* Risk: Migration to v1 will be harder for people who are using PipelineResources
  * Mitigation: We provide detailed examples of how to migrate from each type of PipelineResource to the equivalent
    Pipeline (e.g. like [the beta documentation we provided](https://github.com/tektoncd/pipeline/blob/main/docs/migrating-v1alpha1-to-v1beta1.md#replacing-pipelineresources-with-tasks)

### User Experience

* Pros:
  * Users can get PipelineResource style composition using their own Tasks (they don't have to wait for them to be
    added to Tekton Pipelines)
* Cons:
  * Might not be as obvious or easy how to use common CI/CD integrations such as git when looking at Tekton Pipelines docs
    (will need to be directed to the catalog and/or [tektoncd/images](#new-repo-tektoncdimages))
    * We can mitigate this by providing examples, walk-throughs and use cases in our docs that show how to use these
      common integrations
  * Won't be as clear to users or to external tools what artifacts are moving through Pipelines (at least until
    we build on [TEP-0075 Object/Dictionary support](https://github.com/tektoncd/community/pull/479) and define common
    interfaces with them)

## Design Details

This is a list of all the features we've identified that PipelineResources provide and how we can provide these features
without requiring PipelineResources:

* Feature: **Augmenting Tasks with steps that execute on the same pod**
  * *Description*: Wrapping a series of steps with actions that are performed before and/or after, which augment the main
    responsibility of the Task.
  * *Replacement*: [TEP-0044](https://github.com/tektoncd/community/blob/main/teps/0044-decouple-task-composition-from-scheduling.md)
    will provide the ability to combine Tasks and allow them to run within one pod (initially as we explore TEP-0044,
    this functionality will be provided by the [pipeline-to-taskrun experimental custom task](https://github.com/tektoncd/experimental/pull/770))
* Feature: **Automatic storage provisioning**
  * *Description* PipelineResources today silently create and destroy PVCs or upload to blob storage in order to share
    data amongst Tasks in a Pipeline.
  * *Replacement* Using
    [volumeClaimTemplates](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md#volumeclaimtemplate) with
    workspaces provides automatic PVC creation and destruction, with the added bonus of being obvious instead of hidden.
    Uploading and downloading from external blob storage could be accomplished with
    [TEP-0044](https://github.com/tektoncd/community/blob/main/teps/0044-decouple-task-composition-from-scheduling.md)
    and Tasks that know how to upload and download (e.g.
    [the aws cli Task](https://github.com/tektoncd/catalog/blob/main/task/aws-cli/0.2/README.md) can be used to upload
    to and download from S3).
* Feature: **PipelineResource specific credential handling**
  * *Description*: PipelineResources express their own credential requirements and handle them such for example that the
    author of a Task which uses a git PipelineResource doesn’t need to know about how to authenticate with git or add
    any additional requirements to the Task around the credentials.
  * *Replacement*: [TEP-0044](https://github.com/tektoncd/community/blob/main/teps/0044-decouple-task-composition-from-scheduling.md)
    will provide the ability to combine Tasks; the PipelineResource equivalent Task can do its own credential handling.
* Feature: **Expressing typed inputs and outputs**
  * *Description*: Using PipelineResources provided tools observing Pipeline execution (e.g.
    [Tekton Chains](https://github.com/tektoncd/chains/blob/main/docs/config.md#chains-type-hinting)) the ability to see
    when known types were used, e.g. [git repos](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md#git-resource)
    and [images](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md#image-resource)
  * *Replacement*: Supporting dicts ([TEP-0075](https://github.com/tektoncd/community/pull/479)) and eventually more
    complex params and results will allow us to use those to define known interfaces that will allow external tools to
    know what inputs and outputs a Task is using
* Feature: **Reusable parameter bundles**
  * *Description*: PipelineResources group and abstract common sets of parameters, for example when cloning from a git
    repo, you will usually need the same information such as url and commitish. Without some kind of bundling mechanism,
    not only do you need to redeclare this list every time you need to use them, but the declared lists can be
    inconsistent, for example to communicate with git you can easily need more than url and commitish, you also need
    proxy information, etc., which is why
    [the git-clone task has 15 parameters](https://github.com/tektoncd/catalog/blob/main/task/git-clone/0.4/README.md#parameters),
    but having to duplicate these params each time you use them has led to the
    [git-rebase lacking many of these params](https://github.com/tektoncd/catalog/blob/main/task/git-rebase/0.1/README.md#parameters)
  * *Replacement*: Supporting objects ([TEP-0075](https://github.com/tektoncd/community/pull/479)) and eventually more
    complex params and results will allow us to use those to define known interfaces, e.g. a dictionary of values you
    need when connecting to git. This will still be duplicated each time, but we might still be able to use this feature
    to help with that by declaring known types via json schema in the future.
* Feature: **Contract around files provided or expected on disk**
  * *Description*: Tasks that use PipelineResources give Task and Pipeline authors some assurances (though the details are
    hidden) that a PipelineResource will be writing to and reading from expected locations on disk. If you use variable
    interpolation in your Task to access the values provided by the PipelineResource, you can be assured that the
    PipelineResource will provide the files at that path.
  * *Replacement*: [TEP-0030 Workspace Paths](https://github.com/tektoncd/community/blob/main/teps/0030-workspace-paths.md))
    describes this problem; the community hasn't yet indicated this functionality is a priority, but if that changes
    we can explore workspace based solutions [such as this one](https://github.com/tektoncd/community/pull/285)
* Feature: **Encapsulating the above in one feature**
  * *Description*: The existing PipelineResource CRD enapsulates the above features into one type
  * *Replacement*: ??? For now, we don't replace this, but the door is open to add a new abstraction to the API later.
    Based on the PipelineResource experience, if we add something like this later on, we should add it in way that
    avoids coupling Task definitions to it (i.e. Tasks should be able to be written and combined with this abstraction
    without relying on details of it and/or limiting their reusability). OR you could argue that the replacment, the
    feature that encapsulates all of the above, is a Task.

## Design Evaluation

* **Reusability**:
  * Tasks will be more reusable when they are not coupled to PipelineResources; Tasks can be combined with different
    sources of data and destinations for data without the Tasks themselves having to be changed.
* **Simplicity**:
  * This proposal reduces the number of concepts a user needs to understand to use Tekton Pipelines; it replaces
    PipelineResources with Tasks
* **Flexibility**:
  * The functionality previously provided by PipelineResources can be infinitely extended by users: they can write
    their own Tasks instead of having to build PipelineResources
* **Conformance**:
  * This proposal will reduce the conformance API surface (i.e. PipelineResources will not be added to it)

## Drawbacks

As mentioned in [non-goals](#non-goals), there is appetite for an abstraction that does one or both of:

* Grouping features such as params, workspaces and results (though again, this sounds like what a Task does)
* Represents "artifacts" moving through the pipeline, especially in a way that external systems can observe
  and reason about (such as [Tekton chains](https://github.com/tektoncd/chains))

By removing this feature, we are removing an abstraction that at least has the elements of being a good solution for
these problems. The mitigation is that folks who are motivated can continue to explore adding a new abstraction which
does what Pipeline Resources does but better.

## Alternatives

### Keep PipelineResources

We could continue to support PipelineResources, and in the v1 release, we could keep them behind
[the alpha api flag](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#customizing-the-pipelines-controller-behavior).

Pros:
* People who like PipelineResources can keep using them

Cons:
* We continue maintaining PipelineResources and dealing with [the problems that motivated this proposal](#motivation)

Two ways we could potentially tackle the extensibilitiy problems in PipelineResources if we kept them as-is:

* [Create a controller based way of providing custom PipelineResources](https://docs.google.com/document/d/1rcMG1cIFhhixMSmrT734MBxvH3Ghre9-4S2wbzodPiU/edit#)
  (similar to [custom tasks](https://github.com/tektoncd/community/blob/main/teps/0002-custom-tasks.md))
* [Extend PipelineResources via `PipelineResourceType`](https://docs.google.com/document/d/1p8zq_wkAcwr1l5BpNQDyNjgWngOtnEhCYEpcNKMHvG4/edit#heading=h.es3nl28r2u1l):
  introduce a new CRD that can be used to define the structure of PipelineResources, ultimately referring to Tasks for
  the "input" and "output" behavior
* [PipelineResources 2 uber Design Doc](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit) which provides
  a `PipelineResourceType` as well as a `PipelineResourceInstance` which is very similar to today's `PipelineResource` CRD

## Upgrade & Migration Strategy

1. Announce [the deprecation](https://github.com/tektoncd/pipeline/blob/main/docs/deprecations.md)
1. Remove usages of PipelineResources in our tutorials and dogfooding.
1. When we create v1, do not include PipelineResources in any of the API surfaces
  1. Provide users with docs and examples showing how to migrate from PipelineResources
1. At least 9 months after announcing PipelineResources deprecation, we can completely delete PipelineResources from our codebase

_See details in [Proposal](#proposal)_

## Implementation Pull request(s)

- [Mark PipelineResources as deprecated](https://github.com/tektoncd/pipeline/pull/4376)
- [Removal of PipelineResources](https://github.com/tektoncd/pipeline/pulls?q=is%3Apr+author%3AJeromeJu+is%3Aclosed+tep074)

## References

* [PipelineResources: The Final Chapter?](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit)
* [A world without PipelineResources](https://docs.google.com/document/d/1u6qO7CPtDnTOZMYFQ5ARysSOy8lfFeVw83C_5BxAKsw/edit),
* [Why aren't PipelineResources beta](https://github.com/tektoncd/pipeline/blob/e76d4132ab2ecfbedc45a964f08a01022e2d4c14/docs/resources.md#why-arent-pipelineresources-in-beta).
* [Tekton Pipeline Resource Extensibility](https://docs.google.com/document/d/1rcMG1cIFhhixMSmrT734MBxvH3Ghre9-4S2wbzodPiU/edit)
* [PipelineResources 2 uber Design Doc](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit)
* [Specializing Tasks - Vision & Goals](https://docs.google.com/document/d/1G2QbpiMUHSs4LOqcNaIRswcdvoy8n7XuhTV8tXdcE7A/edit)
* [Specializing Tasks: Possible designs](https://docs.google.com/document/d/1p8zq_wkAcwr1l5BpNQDyNjgWngOtnEhCYEpcNKMHvG4/edit)
