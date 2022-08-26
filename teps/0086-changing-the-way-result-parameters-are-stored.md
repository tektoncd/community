---
status: proposed
title: Changing the way result parameters are stored
creation-date: '2021-09-27'
last-updated: '2022-06-09'
authors:
- '@tlawrie'
- '@imjasonh'
- '@bobcatfish'
- '@pritidesai'
- '@tomcli'
- '@ScrapCodes'
---

# TEP-0086: Changing the way result parameters are stored

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
  - [Required](#required)
- [Alternatives](#alternatives)
  - [Result Sidecar - Upload results from sidecar](#result-sidecar---upload-results-from-sidecar)
    - [Option: Supporting multiple sidecars](#option-supporting-multiple-sidecars)
    - [Risks and Mitigations](#risks-and-mitigations)
    - [User Experience (optional)](#user-experience-optional)
    - [Performance (optional)](#performance-optional)
    - [Design Evaluation](#design-evaluation)
    - [Design Details](#design-details)
      - [Considerations](#considerations)
      - [Open Design Questions](#open-design-questions)
      - [Test Plan](#test-plan)
    - [Drawbacks](#drawbacks)
  - [Result References vs results in TaskRun](#result-references-vs-results-in-taskrun)
  - [N Configmaps Per TaskRun with Patch Merges (c).](#n-configmaps-per-taskrun-with-patch-merges-c)
  - [CRD](#crd)
    - [Notes/Caveats](#notescaveats)
  - [Dedicated HTTP Service](#dedicated-http-service)
  - [Self-update / mutate the TaskRun via admission controller](#self-update--mutate-the-taskrun-via-admission-controller)
  - [Separate Database](#separate-database)
  - [Store results on PVCs](#store-results-on-pvcs)
  - [No change. Use workspaces.](#no-change-use-workspaces)
  - [Repurpose Artifact Storage API](#repurpose-artifact-storage-api)
  - [Using logs emitted by the Task](#using-logs-emitted-by-the-task)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [Next steps to unblock](#next-steps-to-unblock)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

To enhance the usage experience of a [Tasks Results](https://tekton.dev/docs/pipelines/tasks/#emitting-results) by end users, we want to change the way Results are stored to allow for greater storage capacity yet with the current ease of [reference](https://tekton.dev/docs/pipelines/variables/#variables-available-in-a-pipeline) and no specific additional dependencies such as a storage mechanism.

The current way that Results are reported via a containers `terminationMessage` imposes a limit of 4 KB per step, and 12 KB total per TaskRun.

## Motivation

The ability to improve Task Result storage size as part of a TaskRun while allowing the Task to continue to use the
[`results`](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#emitting-results) feature and without needing
to use other mechanisms such as [workspaces](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-workspaces).

Additionally, this will help projects that wrap/abstract Tekton where users understand how to reference Task Results between tasks and don't have the ability to adjust a Task to retrieve from a storage path. Part of the motivation for me putting this TEP together is around making that easier. With my [project](https://github.com/boomerang-io) end users run tasks without knowing YAML, they drag and drop tasks on a GUI.

### Goals

* Allow larger storage than the current 4096 bytes of the Termination Message.
* Provide a mechanism to plug an external storage to store large results.

### Non-Goals

* Not attempting to solve the storage of blobs or large format files such as JARs

### Use Cases (optional)

1. Provide Task authors and end users the ability to store larger Results, such as JSON payloads from an HTTP call, that they can inspect later or pass to other tasks without the need to understand storage mechanisms.

2. The Tekton operator / administrator not dependent on maintaining a storage solution and removing a complex barrier for some installations

3. Store a CloudEvent payload as a Result for subsequent tasks to reference and process.

4. _Potential_ Ability to use JSONPath on Results with JSON data to be able to reference specific elements in the contents.
  - Do we add this as part of the scope? Not only change the storage but update the access method to build on top of **TEP-0080: Support domain-scoped parameter/result names** to allow access to the contents of Results through JSONPath scoping?

5. For projects wrapping or extending Tekton, such as with [Boomerang Flow](https://useboomerang.io) the end users may not know about adjusting Tasks to work with Workspaces. In this instance, they drag and drop tasks on a no-code UI and can only pass parameters around. Additional other extensions may also not know or understand storage systems.

6. emit structured results, e.g. multiple built image results from a task (see https://github.com/tektoncd/pipeline/issues/4282 for a relevant release pipeline failure, and [TEP-0075](https://github.com/tektoncd/pipeline/issues/4282) and [TEP-0076](https://github.com/tektoncd/community/pull/477) for structured result support) <-- or this could just be part of item (1)

7. The ability to emit [SBOMs](https://en.wikipedia.org/wiki/Software_bill_of_materials) as results from Tasks and make them easily consumable by tools observing execution (e.g. Tekton Chains) without requiring those tools to mount and access volumes

## Requirements


* Allow users to reference a Task Result in its current form `$(tasks.Task Name.results.Result Name)`
* Use existing objects (or standard ones incl CRDs) where the complexity _can_ be abstracted from a user.
* Allow flexibility in the design for additional plug and play storage mechanisms.
* Ensure secure RBAC is in place.
* The default mechanism for storing results out of the box should not require giving the Tekton Controller any ability
  to modify Roles or RoleBindings (i.e. it should not require that Tekton dynamically change the permissions of the
  ServiceAccount executing the Task that emits results).
* It must be clear from looking at a Task whether or not a Tekton installation can support the results storage
  requirements (i.e. we want to avoid having Tasks that require writing huge results and finding out at runtime that
  the backing storage used by a Tekton installation doesn't support it).
* Allow flexibility in the design such that the TaskRun status continue to be the source of truth for the contents of the result.
  This flexible design must benefit the use cases which must avoid results in the TaskRun status.
    * Some important notes/limitations with having results in the TaskRun:
      * This requirement can potentially introduce an upper bound on the result size that is limited by
        [the total allowed size of a CRD](https://github.com/kubernetes/kubernetes/issues/82292).
      * This may mean sensitive information can never be stored in a result (maybe that is a reasonable restriction).
      * This may also prevent encrypting results (unless they are encrypted within the TaskRun itself).
      * Define a clear upper limit on the expected maximum size of a result.
      * Support an environment where executing pods are not permitted to make network connections within the cluster.

## Alternatives

### Dedicated Storage API Service

In this approach, a dedicated Result Storage API is used to abstract away large
result storage and implementation.

```
┌───────────────────┐
│                   │     ┌─────────────────────────┐
│   Control Plane   │     │           Pod           │
│                   │     │                         │
│   ┌────────────┐  │     │ ┌──────────┐    ┌────┐  │
│   │ Controller ├──┼─────┼─►entrypoint├────►step│  │
│   └────────────┘  │     │ └─────┬────┘    └────┘  │
│                   │     │       │                 │
│                   │     │       │                 │
│   ┌───────────┐   │     │       │                 │
│   │Storage API◄───┼─────┼───────┘                 │
│   └─────┬─────┘   │     │                         │
│         │         │     └─────────────────────────┘
└─────────┼─────────┘
          │
          │
          │
  ┌───────▼───────┐
  │Storage Backend│
  └───────────────┘
```

This approach relies on the fact that the entrypoint wraps the running user
container. Today, Tekton utilizes this today to
[order user steps by reading/writing post files](https://github.com/tektoncd/pipeline/blob/main/cmd/entrypoint/README.md),
we could utilize this same process to perform other post-step actions on the
Pod - i.e. we could use this to perform result uploading with the existing user
Pod.

The Storage API should be a known address to the entrypoint (either a static
address or configured by the Tekton Pod controller). User pods should
authenticate to the Storage API using the OIDC credentials issued by the
Kubernetes cluster, likely via
[Service Account Token Projection](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/#service-account-token-volume-projection)
with a custom Tekton audience claim. If desired, Tekton service providers can
customize the token behavior by modifying the OIDC configuration options of the
Kubernetes API server
(https://kubernetes.io/docs/reference/access-authn-authz/authentication/#configuring-the-api-server).
For permission decoupling, we recommend that the Storage API is not ran as the
same identity/Pod as the Pipeline controller. There is no requirement that the
Storage API must be local to the cluster - it is the responsibility of the
Tekton service provider to ensure that the Storage API can accept Pod OIDC
credentials from the entrypoint (i.e. via OIDC federation or some other
mechanism). Tekton should build a cluster local open source implementation that
is vendor agnostic. TBD what the default open source storage backend will be
(e.g. Volumes, ConfigMaps, within the Tekton CRD itself, etc).

The Storage API spec should be agnostic to the underlying storage backend (e.g.
local storage, GCS, OCI, etc). By swapping out the implementation of the
Storage API binary, Tekton installations can modify the behavior of where Result
bytes are ultimately stored. It should be the responsibility of the Storage API
server to handle any authentication with storage backends - user containers
should **not** be given direct access to storage backend so that Result contents
cannot be modified by user code.

#### Risks and Mitigations

- The Storage API must be available for the user Task to successfully complete.
  Some providers may want to implement high availability and retry strategies
  within the entrypoint to mitigate this.

#### Design Evaluation

- Reusability
  - A backend agnostic Storage API means that it can be reused across different
    implementations. Since storage backend auth and configuration should be
    handled by the Storage API implementation, there isn't a high risk of
    storage backend specific fields bleeding into the API.
- Simplicity
  - Introduces more complexity to the user Pod lifecycle, but this is being done
    to enable larger results.
  - By reusing existing components we don't need to introduce additional compute
    overhead into user Pods.
- Flexibility
  - Tekton service providers can swap out the implementation for whatever they
    want so long as they can accept the Pod credentials. This lets them
    customize how and where Result is stored.
- Conformance
  - The Storage API should become a part of the conformance spec for
    implementations.

### Result Sidecar - Upload results from sidecar

In this solution we include a sidecar in all pods that back TaskRuns which waits for individual steps to write results
and then writes these results somewhere else, so they can be stored and made available.

**Sidecar API:**

1. The controller is passed a flag, -sidecar-image=<image>
2. This image is added as a container in every TaskRun Pod, with each steps’ results emptyDir volume attached as read–only, and params emptyDir volumes attached as read-write.
3. Watch directory, and any time it sees a result file appear, it writes that content externally (GCS, datastore, cuneiform tablets, the moon)
it must be able to produce an opaque string that represents that result value, which it writes to TaskRun status
> TODO: Do we achieve this via terminationMessage? We can enforce that these opaque strings be small; otherwise, ConfigMap? – an example signed URL is 824 bytes, this limits to ~12 per TaskRun.
4. The TaskRun controller updates the status to include that opaque string
5. When the next TaskRun starts, for each passed-in param that’s passed by reference, the TaskRun controller passes opaque reference strings to the sidecar along with the associated param name. the sidecar dereferences the opaque strings and writes the real param value to the param value file mounted into steps.
6. The sidecar reports READY only after these steps are complete, allowing the first step to begin as normal.

#### Option: Supporting multiple sidecars

With this API in place, Tekton can provide an implementation that writes results to a centralized HTTP service and other
operators can implement their own that write results to cluster-local persistent volumes, external object storage,
document store, relational database, etc.

Implementations should take care to ensure the integrity of result/param contents:

- ideally, content-addressed for tamper-evidence
- ideally, incremental for speed and cost efficiency
- ideally, with tight access controls to prevent tampering and leakage
  for example, an implementation that stored contents in GCS could use signed URLs to only authorize one POST of object contents, only authorize GETs for only one hour, and delete the object contents entirely after one day.

However, we are currently leaning toward using implementations of [the HTTP service](#dedicated-http-service) as the place
to plug in support for different backends instead.

This alternative provides options for handling a change to result parameter storage and potentially involves adjusting the
`entrypoint` or additional sidecar to write to this storage implementation.

We need to consider both performance and security impacts of the changes and trade off with the amount of capacity we would gain from the option.

#### Risks and Mitigations

* Concern on using kubernetes (backed by etcd) as a database
* Storing results outside a TaskRun means that all systems integrating with Tekton that want access to that
  result must now integrate with the results storage
    * Mitigation: if we define an interface for accessing results storage, this can at least be limited to integrating
      with this one interface
* Complexity of the solution (see [Design Evaluation](#design-evaluation) below).

#### User Experience (optional)

* Users must be able to refer to these result parameters exactly as they currently do and still be able to reference in subsequent tasks (i.e. read access)

#### Performance (optional)

* Speed:
    * Adding any additional communication required in order to write and read results will likely decrease performance
* Storage:
    * Supporting larger results may mean storing more results data

#### Design Evaluation

* Reusability
    * At authoring time, it must be possible to communicate to users if there are any special assumptions a Task is making
      about results it expects to be able to emit
* Simplicity
    * This makes our implementations more complex, and likley makes administration/operation more complex
    * More potential points of failure
* Flexibility
    * Can use your own backing storage (depending on [the requirement we use the TaskRun as the source of truth](#requirements))
* Conformance
    * Must be possible to use Tasks across Tekton installations - if a Task expects to be run in an installation that
      supports larger Task runs, this must be clear

#### Design Details

This approach for recording results coupled with the [*Dedicated HTTP Service*](#dedicated-http-service)
(with a well defined interface that can be swapped out) can help abstract the backend. With this approach the default
backend could be a ConfigMap (or CRD) - or we could even continue to use the TaskRun itself to store results - since
only the HTTP service would need the permissions required to make teh edits (vs a solution where we need to on the fly
configure every service account associated with every taskrun to have this permission).

##### Considerations

Overall by using a plug-and-play extensible design, the question of what the storage mechanism is becomes less of an implementation design choice. Instead, the questions now become

1. **What is the default storage mechanism shipped?** We want to provide a mechanism that does not require storage or additional dependencies. Configmaps is the ideal choice here, even if it creates additional ServiceAccount changes as when it comes time to production, these can be tightened as well as an alternative Results backing mechanism chosen.

2. **Are we wanting a centralized or distributed design?** If we combine the Result Sidecar with the Dedicated HTTP
   Service we potentially get the best of both worlds. A centralized service for security and extensibility. With a
   sidecar of reading and processing the results.

**Auth**
We could use built in k8s OIDC token support to materialize short lived tokens in the pod running the Task for
authentication with the centralized service. For example:

1. Sidecar reads result from disk
2. Sidecar in the pod gets an OIDC token from k8s
3. Sidecar uses OIDC token to authenticate with HTTP Result storage service
4. Sidecar uploads result
5. HTTP Result storage service records the result

**Encryption**
Communication between the pods and the HTTP Results storage service could be encrypted.

**Defined Interface**
The HTTP Results storage service would implement a standardized interface that could be implemented by anyone desiring
to use a different mechanism to store results. TBD: depends on whether or not we have a [requirement](#requirements)
that results are stored on the TaskRun itself

##### Open Design Questions

- How should the sidecar report that results-writing or param-getting failed, and how should the TaskRun controller be notified so that the TaskRun can also be failed?
- Do we need the extra byRef boolean in the model? And should byRef become the default always.
- Should the sidecar be responsible for deciding whether the result should be reported by-value or by-reference? Or is that a controller-wide configuration?
- Is passing by-value still useful for small pieces of data to be able to have them inlined in TaskRun/PipelineRun statuses?

##### Test Plan

* All end-to-end tests and examples that use results would be updated to setup and use the default result handling
  mechanism
* Any additional ways of backing results would need their own set of tests

#### Drawbacks

* Increased complexity within Tekton Pipelines execution
* Increased complexity for systems integrating with Tekton Pipelines

(See [Risks and mitigations](#risks-and-mitigations).)

### Result References vs results in TaskRun

Beyond size limits of specific TaskRuns’ results, the fundamental issue is that API objects in etcd are not suitable for
storing arbitrarily large data.

In this option we introduce a way to pass one TaskRun’s output results into another TaskRun’s input parameters by reference, instead of
only by value as they are today.
The result `type` could also be configured as `stringReference` or `arrayReference` explicitly to indicate that the output is storing to a remote stroage.
**Example:**

```yaml
tasks:
- name: first-task
  taskSpec: foo
    results:
    - name: out
      type: stringReference # <-- *new type*
- name: second-task
  taskSpec: bar
  params:
  - name: in
    value: "$(tasks.first-task.results.out)"
```
                                  
Alternatively, the remote storage flag can be specified as a new field. e.g.
                                  
```yaml
tasks:
- name: first-task
  taskSpec: foo
    results:
    - name: out
      type: string
      storage: reference  # <-- *new type*
- name: second-task
  taskSpec: bar
  params:
  - name: in
    value: "$(tasks.first-task.results.out)"
```

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
...
status:
  taskResults:
  - name: out
    valueRef: <opaque-string>  # <-- *new field*
```

**Implementation:**

Result references require some code to take the contents of `/tekton/results/out` in the container environment, copy
them elsewhere, and mint a unique reference. It also requires some code to take that reference, locate the contents
wherever they are, and make them available to other TaskRuns at `/tekton/params/in`.

Questions:
- Do we need the extra byRef boolean in the model? And should byRef become the default always.
- Should the sidecar be responsible for deciding whether the result should be reported by-value or by-reference? Or is that a controller-wide configuration?
- Is passing by-value still useful for small pieces of data to be able to have them inlined in TaskRun/PipelineRun statuses?

### N Configmaps Per TaskRun with Patch Merges (c). 

  - As the TaskRun Pod proceeds, the injected entrypoint would write result data from `/tekton/results/foo` to the ConfigMap. After a TaskRun completes, the TaskRun controller would read the associated ConfigMap data and copy it into the TaskRun’s status. The ConfigMap is then deleted.
  - **Create N ConfigMaps** for each of N results, and grant the workload access to write to these results using one of these focused Roles: 
    - https://github.com/tektoncd/pipeline/blob/9c61cdf6d4b7b5e26c787d62447c0eed1c92b68f/config/200-role.yaml#L100
    - The **ConfigMaps**, the Role, and the RoleBinding could all be OwnerRef'd to the **Run**, to deal with cleanup.
  - Concerns:
    - Results in the pipelines controller being given more power, i.e. to create and delete roles and rolebindings
    - Having to create a new **ConfigMap**, Role and RoleBinding per TaskRun, when at the end of the day we don't actually care about updating that **ConfigMap**, but the TaskRun's results.
    - Parallelism even with queued Patch Merges
    - Increased load on the API server, on the order of 3+ more API requests per TaskRun:
      - create the ConfigMap
      - update RBAC to the ConfigMap
      - (during TaskRun execution) N ConfigMap updates, where N is the number of steps that produce a result.
      - (after the TaskRun completes) delete the ConfigMap
    - 'scale fail' - The maximum size of a ConfigMap is ~1.5 MB, if the data it reports is copied into the TaskRun status, and again into the aggregated PipelineRun status, the effective maximum result size is ~1.5 MB per PipelineRun.
    

### CRD

  - Help reduce load in the presence of controllers that watch for ConfigMaps cluster-wide
  - Minimally limits the accidentally chance of editing with `kubectl edit cm <results>`
  - Similar benefits to ConfigMap from a Role and Rolebinding perspective
  - Webhook to validate the write once immutability

#### Notes/Caveats

* The storage of the result parameter may still be limited by a number of scenarios, including:
    - [1.5 MB CRD size](https://github.com/kubernetes/kubernetes/issues/82292)
    - The total size of the PipelineRun _if_ the TaskRun content is included, however
      [TEP-100 is removing this](https://github.com/tektoncd/community/blob/main/teps/0100-embedded-taskruns-and-runs-status-in-pipelineruns.md)
* Eventually this may result in running into a limit with etcd overall, however not a problem for now. Can be solved via cleanups / offloading history.
* We want to try and minimize reimplementing access control in a webhook (in part because it means the webhook needs to know which task identities can update which task runs, which starts to get annoyingly stateful)

### Self-update / mutate the TaskRun via admission controller

  - With the various controls i.e. first write, subsequent read only
  - Potential issue with self updating its own Status

### Separate Database

  - Introducing an additional database requirement to Tekton to support the storage of information outside of etcd.

### Store results on PVCs

  - Use PVCs to store results. The Tekton controller will auto provision the PVC and mount on the task if necessary.
    The result location will be a pvc/storage path in the pod spec. Then, configure Tekton entrypoint script to retrieve result
    file contents in the PVCs and replace the pvc/storage path with the new contents. This can avoid the 1.5 MB CRD size as the result contents are
    replaced during init-container, so it won't be part of the pod or taskrun spec. In the API Spec, we could let users to choose whether to opt-in this
    feature for each task to reduce the unnecessary overheads if not needed.
                                     
   #### API details:
   - In the Pipeline API field, introduce a new field `resultWorkspace` for passing all the `reference` type results. The new field consist the name of the workspace name for passing the big results and can extend in the future for more workspace configurations.
   
                                     
   ```yaml
   apiVersion: tekton.dev/v1beta1
   kind: Pipeline
   spec:
     resultWorkspace:
       name: shared-data
   ...
   ```
   - POC pull request: [TEP-0086 Large results using workspace POC](https://github.com/tektoncd/pipeline/pull/5337)

Pros:
- PVCs can leverage with CSI driver to store files in most storages.
- Able to avoid the 1.5 MB CRD size since the result contents are populated during the init-container.
- Users can opt-in only for the large result files to be stored in PVCs and keep the rest to use termination logs or any other solution that we make default in future. The sidecar driven approach can be made default if its implementable.

Cons:
- Any downsides of PVCs we've encountered in other places (e.g. [TEP-0044 data locality](https://github.com/tektoncd/community/blob/main/teps/0044-data-locality-and-pod-overhead-in-pipelines.md))
- Any consumer of the opted in remote results would need to mount the PVC

### No change. Use workspaces.

  - There is the alternative of storing result parameters as data in a workspace, however Workspaces
    - require there has to be a storage mechanism in the cluster that can be shared between Tasks. That can be complex, or have performance issues in itself if using an As A Service that orders the storage at spin-up time. Or forces Tasks to all run on the same node. etc. Storage is a big complex adoption hurdle.
    - changes the way end users refer to the result parameter or pass between containers
    - requires some tasks to be altered to retrieve data from the file system in a certain location. This makes it difficult to use a library of Tekton Tasks or an abstraction that doesn't provide access to where a parameter comes from.

### Repurpose Artifact Storage API

  - Already supported by Tekton Pipelines for `PipelineResources`
  - Support buckets and temporary PVCs
  - Only requires a one-time configuration by operators
  - Transparently moves data between tasks in a pipeline
  - Currently, tightly coupled with `OutputResources` and `InputResources` but this could evolve
  - [Docs on setting up storage](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#configuring-pipelineresource-storage)
  - [Interface](https://github.com/tektoncd/pipeline/blob/main/pkg/artifacts/artifacts_storage.go#L39-L47)

### Using logs emitted by the Task

  - We are also exploring using **stdout logs from a dedicated sidecar to return a json result object** as a simpler way 
to support larger TaskResults, but we need to explore this in a POC as we suspect we may not be able to rely on logs for this.
  - The controller would wait for the sidecar to exit and then read the logs based on a particular query and append info to the TaskRun
  - Potential to use a CloudEvent object to wrap result object

Cons:
- No guarantees on when logs will be available (would have to wait for this before considering a TaskRun complete)
- No guarantee you'll be able to access a log before it disappears (e.g. logs will not be available via the k8s API
  once a pod is deleted)
- The storage of the result parameter may still be limited by a number of scenarios, including:
    - [1.5 MB CRD size](https://github.com/kubernetes/kubernetes/issues/82292)
    - The total size of the PipelineRun _if_ the TaskRun content is included, however
      [TEP-100 is removing this](https://github.com/tektoncd/community/blob/main/teps/0100-embedded-taskruns-and-runs-status-in-pipelineruns.md)

### Using embedded storage client to store result files in remote storage

  - Use embedded storage client to store results. It needs an extra post-processing step since some storage client may have some dependency on the container
  settings. The result location will be a storage path in the pod spec. Then, inject a preproceesing step to retrieve result file contents using the storage
  client code and replace the storage path with the new contents.

Pros:
- Post-processing step can be pluggable to accommodate for any type of stroage.
- Able to avoid the 1.5 MB CRD size since the result contents are populated during the init-container.

Cons:
- Require two extra storage client code steps to store and retrieve result files.

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

Feature flag in the Tekton configmap to enable storing Tekton results in a remote storage. The way to opt-in this
function could be cluster-wise or on a per task basis.

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

- [TEP-0086 Large results using workspace POC](https://github.com/tektoncd/pipeline/pull/5337)

## Next steps to unblock

* [x] Determine if WIP [requirements](#requirements) should be included:(esp the requirement that results be stored
  on the TaskRun
  * Marked this as a requirement with flexible design based on the discussion in the API WG with @skaegi and [TEP-0089](0089-nonfalsifiable-provenance-support.md).
* [ ] Determine if we can agree to an upper limit on the size of a result.
* [ ] POC of a [logs based approach](#using-logs-emitted-by-the-task).


## References (optional)

- [Original issue](https://github.com/tektoncd/pipeline/issues/4012)
- [HackMD Result Collector Sidecar Design](https://hackmd.io/a6Kl4oS0SaOyBqBPTirzaQ)
- [TEP-0086 Design Breakout Session Recording](https://drive.google.com/file/d/1lIqyy1RyZMYOrMCC2CLZD8eOf0NrVeDb/view?usp=sharing)
- [TEP-0086 Design Breakout Session Notes](https://hackmd.io/YU_g27vRS2S5DwfBXDGpYA?view)
