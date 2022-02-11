---
status: proposed
title: Changing the way result parameters are stored
creation-date: '2021-09-27'
last-updated: '2021-09-27'
authors:
- '@tlawrie'
- '@imjasonh'
---

# TEP-0086: Changing the way result parameters are stored

<!--
**Note:** When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the SIG that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly.  The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved.  Any TEP
marked as a `proposed` is a working document and subject to change.  You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused.  If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP.  Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/NNNN-TEP-template/README.md).

-->

<!--
This is the title of your TEP.  Keep it short, simple, and descriptive.  A good
title can help communicate what the TEP is and should be considered as part of
any review.
-->

<!--
A table of contents is helpful for quickly jumping to sections of a TEP and for
highlighting any additional information provided beyond the standard TEP
template.

Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-request-s)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

To enhance the usage experience of a [Tasks Results](https://tekton.dev/docs/pipelines/tasks/#emitting-results) by end users, we want to change the way Results are stored to allow for greater storage capacity yet with the current ease of [reference](https://tekton.dev/docs/pipelines/variables/#variables-available-in-a-pipeline) and no specific additional dependencies such as a storage mechanism.

The current way that Results are reported via a containers `terminationMessage` imposes a limit of 4KB per step, and 12KB total per TaskRun.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

The ability to improve Task Result storage size as part of a TaskRun without needing to have access to additional storage. 

Additionally this will help projects that wrap/abstract Tekton where users understand how to reference Task Results between tasks and dont have the ability to adjust a Task to retrieve from a storage path. Part of the motivation for me putting this TEP together is around making that easier. With my [project](https://github.com/boomerang-io) end users run tasks without knowing YAML, they drag and drop tasks on a GUI.

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

* Allow larger storage than the current 4096 bytes of the Termination Message.
* Allow users to reference a Task Result in its current form `$(tasks.Task Name.results.Result Name)`
* Use existing objects (or standard ones incl CRDs) where the complexity _can_ be abstracted from a user.
* Allow flexibility in the design for additional plug and play storage mechanisms
* Ensure secure RBAC is in place.

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

* Not attempting to solve the storage of blobs or large format files such as JARs

### Use Cases (optional)

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

1. Provide Task authors and end users the ability to store larger Results, such as JSON payloads from a HTTP call, that they can inspect later or pass to other tasks without the need to understand storage mechanisms.

2. The Tekton operator / administrator not dependent on maintaining a storage solution and removing a complex barrier for some installations

3. Store a CloudEvent payload as a Result for subsequent tasks to reference and process.

4. _Potential_ Ability to use JSONPath on Results with JSON data to be able to reference specific elements in the contents.
  - Do we add this as part of the scope? Not only change the storage but update the access method to build on top of **TEP-0080: Support domain-scoped parameter/result names** to allow access to the contents of Results through JSONPath scoping?

5. For projects wrapping or extending Tekton, such as with [Boomerang Flow](https://useboomerang.io) the end users may not know about adjusting Tasks to work with Workspaces. In this instance, they drag and drop tasks on a no-code UI and can only pass parameters around. Additional other extensions may also not know or understand storage systems.

6. emit structured results, e.g. multiple built image results from a task (see https://github.com/tektoncd/pipeline/issues/4282 for a relevant release pipeline failure, and [TEP-0075](https://github.com/tektoncd/pipeline/issues/4282) and [TEP-0076](https://github.com/tektoncd/community/pull/477) for structured result support) <-- or this could just be part of item (1)

7. The ability to emit [SBOMs](https://en.wikipedia.org/wiki/Software_bill_of_materials) as results from Tasks and make them easily consumable by tools observing execution (e.g. Tekton Chains) without requiring those tools to mount and access volumes

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

This proposal provides options for handling a change to result parameter storage and potentially involves adjusting the `entrypoint` or additional sidecar to write to this storage implementation.

We need to consider both performance and security impacts of the changes and trade off with the amount of capacity we would gain from the option.

### Notes/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

* The storage of the result parameter may still be limited by a number of scenarios, including:
  - 1.5 MB CRD size
  - The total size of the PipelineRun _if_ it was to be patched back into an existing TaskRun object based on aggregate size of these objects.

* Eventually this may result in running into a limit with etcd, however not a problem for now. Can be solved via cleanups / offloading history.

* We want to try and minimize reimplementing access control in a webhook (in part because it means the webhook needs to know which task identities can update which task runs, which starts to get annoyingly stateful)

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

* Concern on using etcd as a database

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

* Users must be able to refer to these result parameters exactly as they currently do and still be able to reference in subsequent tasks (i.e. read access)

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable.  This may include API specs (though not always
required) or even code snippets.  If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->

**Solution TBD.** Primary approach for consideration is the *Result Sidecar* implementation for recording results coupled with the *Dedicated HTTP Service* (with a well defined interface that can be swapped out) which would abstract th ebackend. With this approach the default backend could be a ConfigMap (or CRD) since only the HTTP service would need the permissions required to make ConfigMap edits (vs a solution where we need to on the fly configure every service account associated with every taskrun to have this permission).

### Considerations

Overall by using a plug-and-play extensible design, the question of what the storage mechanism is becomes less of an implementation design choice. Instead the questions now become

1. What is the default storage mechanism shipped? We want to provide a mechanism that does not require storage or additional dependencies. Configmaps is the ideal choice here, even if it creates additional ServiceAccount changes as when it comes time to production, these can be tightened as well as an alternative Results backing mechansim chosen.

2. Are we wanting a centralized or distributed design? If we combine the Result Sidecar with the Dedicated HTTP Service we potentially get the best of both worlds. A centralized controller for security and extensibility. With a sidecar of reading and processing the results.

**Auth** 
If we do something with network calls (on or off cluster), look at service account (projected?) volume - k8s has built in oidc provider, can materialized short lived (e.g. 10 min max) oidc token on filesystem for a service account with a configurable audience

Even KIND has a built in OIDC provider, example: https://github.com/mattmoor/kind-oidc. OIDC is also how Tekton Results works.

**Encryption**
Further enhance with the encryption of the result upload

**Defined Interface**
Define standard proto or REST interface that storage systems would implement + authenticate with OIDC tokens, potential for controller to give explicit authorization for a task to fill out a particular result.

Once you have the proto, can implement in lots of different ways = an appealing for plugging in different storage mechanisms
- REST annoations + GRPC mix example: https://github.com/mattmoor/grpc-example.




### Open Design Questions

- Do we need the extra byRef boolean in the model? And should byRef become the default always.
- Should the sidecar be responsible for deciding whether the result should be reported by-value or by-reference? Or is that a controller-wide configuration? 
- Is passing by-value still useful for small pieces of data to be able to have them inlined in TaskRun/PipelineRun statuses?
- How should the sidecar report that results-writing or param-getting failed, and how should the TaskRun controller be notified so that the TaskRun can also be failed?

## Test Plan

<!--
**Note:** *Not required until targeted at a release.*

Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all of the test cases, just the general strategy.  Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

### SideCar Result References

Beyond size limits of specific TaskRuns’ results, the fundamental issue is that API objects in etcd are not suitable for storing as much data as users want to be able to report in results, and pass as parameters.

In addition to disaggregating TaskRun statuses into PipelineRun statuses (which we should do anyway before v1), we should introduce some way to pass one TaskRun’s output results into another TaskRun’s input parameters by reference, instead of only by value as they are today.

**Example:**

```yaml
tasks:
- name: first-task
  taskSpec: foo
  results:
  - name: out
    byRef: true # <-- *new field*
- name: second-task
  taskSpec: bar
  params:
  - name: in
    value: "$(tasks.first-task.results.out)"
```


**Implementation:**

Result references require some code to take the contents of `/tekton/results/out` in the container environment, copy them elsewhere, and mint a unique reference. It also requires some code to take that reference, locate the contents whever they are, and make them available to other TaskRuns at `/tekton/params/in`.

Both of these could be satisfied by the same component: a Tekton-internal sidecar, the *Result Collector Sidecar*. 

**Sidecar API:**

1. The controller is passed a flag, -sidecar-image=<image>
2. This image is added as a container in every TaskRun Pod, with each steps’ results emptyDir volume attached as read–only, and params emptyDir volumes attached as read-write.
3. Watch directory, and any time it sees a result file appear, it writes that content externally (GCS, datastore, cuneiform tablets, the moon)
it must be able to produce an opaque string that represents that result value, which it writes to TaskRun status
> TODO: Do we achieve this via terminationMessage? We can enforce that these opaque strings be small; otherwise, ConfigMap? – an example signed URL is 824 bytes, this limits to ~12 per TaskRun.
4. the TaskRun controller updates the status to include that opaque string
5. when the next TaskRun starts, for each passed-in param that’s passed by reference, the TaskRun controller passes opaque reference strings to the sidecar along with the associated param name. the sidecar dereferences the opaque strings and writes the real param value to the param value file mounted into steps.
6. the sidecar reports READY only after these steps are complete, allowing the first step to begin as normal.

```yaml 
apiVersion: tekton.dev/v1beta1
kind: TaskRun
...
status:
  taskResults:
  - name: out
    valueRef: <opaque-string>  # <-- *new field*
```

With this API in place, Tekton can provide an implementation that writes results to a ConfigMap, and other operators can implement their own that write results to cluster-local persistent volumes, external object storage, document store, relational database, etc.

Implementations should take care to ensure the integrity of result/param contents:

- ideally, content-addressed for tamper-evidence
- ideally, incremental for speed and cost efficiency
- ideally, with tight access controls to prevent tampering and leakage
for example, an implementation that stored contents in GCS could use signed URLs to only authorize one POST of object contents, only authorize GETs for only one hour, and delete the object contents entirely after one day.

### N Configmaps Per TaskRun with Patch Merges (c). 

  - As the TaskRun Pod proceeds, the injected entrypoint would write result data from `/tekton/results/foo` to the ConfigMap. After a TaskRun completes, the TaskRun controller would read the associated ConfigMap data and copy it into the TaskRun’s status. The ConfigMap is then deleted.
  - Create N ConfigMaps** for each of N results, and grant the workload access to write to these results using one of these focused Roles: 
    - https://github.com/tektoncd/pipeline/blob/9c61cdf6d4b7b5e26c787d62447c0eed1c92b68f/config/200-role.yaml#L100
    - The ConfigMaps**, the Role, and the RoleBinding could all be OwnerRef'd to the *Run, to deal with cleanup.
  - Concerns:
    - Results in the pipelines controller being given more power, i.e. to create and delete roles and rolebindings
    - Having to create a new ConfigMap**, Role and RoleBinding per TaskRun, when at the end of the day we don't actually care about updating that ConfigMap**, but the TaskRun's results.
    - Parallelism even with queued Patch Merges
    - Increased load on the API server, on the order of 3+ more API requests per TaskRun:
      - create the ConfigMap
      - update RBAC to the ConfigMap
      - (during TaskRun execution) N ConfigMap updates, where N is the number of steps that produce a result.
      - (after the TaskRun completes) delete the ConfigMap
    - 'scale fail' - The maximum size of a ConfigMap is ~1.5MB, if the data it reports is copied into the TaskRun status, and again into the aggregated PipelineRun status, the effective maximum result size is ~1.5MB per PipelineRun.

### CRD

  - Help reduce load in the presence of controllers that watch for ConfigMaps cluster-wide
  - Minimally limits the accidently chance of editing with `kubectl edit cm <results>`
  - Similar benefits to ConfigMap from a Role and Rolebinding perspective
  - Webhook to validate the write once immutability

### Dedicated HTTP Service

  - Potential Auth and HA problems
  - Could run as part of the controller
  - Could be a separate HTTP server(s) which write to TaskRuns (or even config maps); task pods connect to this server to submit results, this server records the results (means result size would be limited to what can be stored in the CRD but there probably needs to be an upper bound on result size anyway)

### Self-update / mutate the TaskRun via admission controller

  - With the various controls i.e. first write, subsequent read only
  - Potential issue with self updating its own Status

### Separate Database

  - Introducing an additional database requirement to Tekton to support the storage of information outside of etcd.

### No change. Use workspaces.

  - There is the alternative of storing result parameters as data in a workspace, however Workspaces
    - require there has to be a storage mechanism in the cluster that can be shared between Tasks. That can be complex, or have performance issues in itself if using an As A Service that orders the storage at spin-up time. Or forces Tasks to all run on the same node. etc. Storage is a big complex adoption hurdle.
    - changes the way end users refer to the result parameter or pass between containers
    - requires some tasks to be altered to retrieve data from the file system in a certain location. This makes it difficult to use a library of Tekton Tasks or an abstraction that doesn't provide access to where a parameter comes from.

### Repurpose Artifact Storage API

  - Already supported by Tekton Pipelines for `PipelineResources`
  - Supports buckets and temporary PVCs
  - Only requires a one-time configuration by operators
  - Transparently moves data between tasks in a pipeline
  - Currently tightly coupled with `OutputResources` and `InputResources` but this could evolve
  - [Docs on setting up storage](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#configuring-pipelineresource-storage)
  - [Interface](https://github.com/tektoncd/pipeline/blob/main/pkg/artifacts/artifacts_storage.go#L39-L47)

### Use stdout logs from a dedicated sidecar to return a json result object
  
  - The controller would wait for the sidecar to exit and then read the logs based on a particular query and append info to the TaskRun
  - Potential to use a CloudEvent object to wrap result object

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

Backwards compatability with the default option using ConfigMaps (or CRD) and the ability to resolve the value.

Potentially feature flag depending on the object used and security role changes.

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References (optional)

- [Original issue](https://github.com/tektoncd/pipeline/issues/4012)
- [HackMD Result Collector Sidecar Design](https://hackmd.io/a6Kl4oS0SaOyBqBPTirzaQ)
- [TEP-0086 Design Breakout Session Recording](https://drive.google.com/file/d/1lIqyy1RyZMYOrMCC2CLZD8eOf0NrVeDb/view?usp=sharing)
- [TEP-0086 Design Breakout Session Notes](https://hackmd.io/YU_g27vRS2S5DwfBXDGpYA?view)