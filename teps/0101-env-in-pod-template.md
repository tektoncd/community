---
status: implementable
title: Env in POD template
creation-date: '2022-03-17'
last-updated: '2022-12-02'
authors:
- '@rafalbigaj'
- '@tomcli'
- '@piyush-garg'
---

# TEP-0101: Env in POD template

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
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
    - [PipelineRun and TaskRun API Changes](#pipelinerun-and-taskrun-api-changes)
    - [Global Default Environment Variables](#global-default-environment-variables)
    - [Precedence Order](#precedence-order)
    - [Forbidden Environment Variables](#forbidden-environment-variables)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

<!--
This section is incredibly important for producing high quality user-focused
documentation such as release notes or a development roadmap.  It should be
possible to collect this information before implementation begins in order to
avoid requiring implementors to split their attention between writing release
notes and implementing the feature itself.

A good summary is probably at least a paragraph in length.

Both in this section and below, follow the guidelines of the [documentation
style guide]. In particular, wrap lines to a reasonable length, to make it
easier for reviewers to cite specific portions, and to minimize diff churn on
updates.

[documentation style guide]: https://github.com/kubernetes/community/blob/master/contributors/guide/style-guide.md
-->

Providing the users a functionality for specifying additional environment variables or overwriting existing environment 
variables defined in `Steps` and `StepTemplate` of `Task` at runtime through `TaskRun` and `PipelineRun`. In order to 
achieve that, a [Pod template](https://github.com/tektoncd/pipeline/blob/main/docs/podtemplates.md) should support 
configuration of environment variables, which are combined with those defined in `steps` and `stepTemplate`, and then 
passed to all step containers. This let the user specify common variables to the global level as well as overwrite 
defaults specified on the particular step level.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

One of the most important motivators for this feature is the ability to eliminate redundant code from
the `PipelineRun` as well as `TaskRun` specification. On average this can reduce 3-5 lines of yaml per
each environment variable per each task in the pipeline.
In case of complex pipelines, which consist of dozen or even hundreds of tasks, any kind of repetition
significantly impacts the final size of `PipelineRun` and leads to resource exhaustion on the
Kubernetes ETCD limitation. 

Besides, users quite frequently are willing to overwrite environment variable values
specified in a `stepTemplate` in the single place when running pipelines.
That helps to optionally pass settings, without a need to define additional pipeline parameters.

Also, users can specify the global environment variables which needs to be added for every `TaskRun` or
`PipelineRun`, then users don't need to specify them in all `Tasks` and changing the values of those environment 
variables will also be not cumbersome as they can change it at single place in global default and can also overwrite
for particular run.

Having an `env` field in the pod template allows to:

- specify global level defaults, what is important to reduce the size of `TaskRun` and `PipelineRun`
- override defaults from `stepTemplate` at `TaskRun` and `PipelineRun` level

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

1. The main goal of this proposal is to enable support for specification of environment variables at the time of 
   execution.(`TaskRun` and `PipelineRun`)

2. Environment variables defined in the Pod template at `TaskRun` and `PipelineRun` level
   take precedence over the ones defined in `steps` and `stepTemplate`.
   
3. Allow cluster admin to define a list of default environment variables which gets added to all the `TaskRun` and 
   `PipelineRun` in [config-defaults.yaml](https://github.com/tektoncd/pipeline/blob/76e40b5a7b11262bfaa96ae31f28db2009002115/config/config-defaults.yaml#L57)

4. Allow cluster admin to define a list of cluster-wide forbidden environment variables by providing a field in 
   `config-defaults` so that users won't overwrite important environment variables configured by admin.

5. Define the order of precedence for the multiple locations where environment variables can be defined.

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

1. Namespace specific environment variables are not proposed. 

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

1. In the first case, common environment variables can be defined in a single place on a `PipelineRun` level or 
   `TaskRun` level. Values can be specified as literals or through Kubernetes references.
   Variables defined on a `PipelineRun` or `TaskRun` level are then available in all steps.
   That allows to simplify the Tekton run resource configuration and significantly reduce the size of
   `PipelineRun` and `TaskRun` resource, by excluding the common environment variables like static global settings, 
   common values coming from metadata etc

2. Secondly, environment variables defined in steps can be easily overwritten by the ones from `PipelineRun` and `TaskRun`.
   With that, common settings like API keys, connection details etc can be optionally overwritten in a single place.
  
3. For Cloud Providers, it's very common to inject user credentials using Kubernetes API `valueFrom` to avoid credentials
   being exposed to the PodSpec. Since each cloud provider has different credential format, able to assign environment 
   variables at the `PipelineRun` and `TaskRun` can reuse the same task with different Cloud Provider credentials.
   Kubernetes API `valueFrom` can also refer to values in the pod labels/annotations for specific Kubernetes cluster
   information such as namespace, application labels, and service annotations.
   
4. Allow users to reuse stock Tekton catalogs on different cloud environment by setting up a cloud specific global container
   spec.

5. User should be able to configure environment variable which needs to be provided to all workloads like for proxy 
   settings, Users need to set environment variables like `HTTP_PROXY`, `HTTPS_PROXY` and `NO_PROXY` on all steps/containers.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

1. Need to define a spec field to provide environment variables at `PipelineRun` and `TaskRun` level.
2. Need to provide a way to define a list of global environment variables.
3. Need to provide a way to define a list of cluster-wide forbidden environment variables. When users define environment variables in the Taskrun and Pipelinerun spec, check the list of forbidden
   environment variables and throw out a validation error if any of the environment variables is forbidden.
4. Since there are many places like listed below where user can define the environment variables, there needs to be a precedence order for different places. 
   - Global Level Forbidden Environment Variables
   - Global Level Default Environment Variables in Tekton Default Pod Template
   - PipelineRun Level Environment Variables in PipelineRun Pod Template
   - TaskRun Level Environment Variables in TaskRun Pod Template
   - Task Level Environment Variables in Task Step Template
   - Step Level Environment Variables in Step Container Spec

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

1. Environment variables can be defined in a single place on a `PipelineRun` and `TaskRun` level.
Values can be specified as literals or through references, e.g.:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: mypipelinerun
spec:
  podTemplate:
    env:
    - name: TOKEN_PATH
      value: /opt/user-token
    - name: TKN_PIPELINE_RUN
      valueFrom:
        fieldRef:
          fieldPath: metadata.labels['tekton.dev/pipelineRun']
```

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: mytaskrun
  namespace: default
spec:
  taskRef:
    name: mytask
  podTemplate:
    env:
    - name: TOKEN_PATH
      value: /opt/user-token
    - name: TKN_TASKRUN_RUN
      valueFrom:
        fieldRef:
          fieldPath: metadata.labels['tekton.dev/taskRun']
```

2. Environment variables defined in steps can be easily overwritten by the ones from a `TaskRun`, e.g.:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: mytask
  namespace: default
spec:
  steps:
    - name: echo-msg
      image: ubuntu
      command: ["bash", "-c"]
      args: ["echo $MSG"]
      envs:
      - name: "MSG"
        value: "Default message"
---
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: mytaskrun
  namespace: default
spec:
  taskRef:
    name: mytask
  podTemplate:
    envs:
      - name: "MSG"
        value: "Overwritten message"
```

3. Environment variables defined in steps can be easily overwritten by the ones from a `PipelineRun`, e.g.:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: mytask
  namespace: default
spec:
  steps:
    - name: echo-msg
      image: ubuntu
      command: ["bash", "-c"]
      args: ["echo $MSG $SECRET_PASSWORD $NAMESPACE"]
      envs:
      - name: "MSG"
        value: "Default message"
      - name: "SECRET_PASSWORD"
        value: "Default secret password"
      - name: "NAMESPACE"
        value: "tekton-pipelines"
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: one-task-pipeline-run
  namespace: default
spec:
  pipelineSpec:
    tasks:
      - name: mytaskrun
        taskRef:
          name: mytask
  podTemplate:
    envs:
      - name: "MSG"
        value: "Overwritten message"
```

4. Promote reusable tasks, users needs not to define different tasks just for the change of env value.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: mytask
  namespace: default
spec:
  steps:
    - name: echo-msg
      image: ubuntu
      command: ["bash", "-c"]
      args: ["echo $MSG $SECRET_PASSWORD $NAMESPACE"]
      envs:
        - name: "MSG"
          value: "Default message"
        - name: "SECRET_PASSWORD"
          value: "Default secret password"
        - name: "NAMESPACE"
          value: "tekton-pipelines"
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: three-task-pipeline-run
  namespace: default
spec:
  pipelineSpec:
    tasks:
      - name: mytaskrun
        taskRef:
          name: mytask
      - name: mytaskrun2
        taskRef:
          name: mytask
        runAfter:
          - mytaskrun
      - name: mytaskrun3
        taskRef:
          name: mytask
        runAfter:
          - mytaskrun2
  podTemplate:
    envs:
      - name: "MSG"
        valueFrom:
          fieldRef:
            fieldPath: metadata.labels['messages']
      - name: "SECRET_PASSWORD"
        valueFrom:
          secretKeyRef:
            name: mysecret
            key: password
            optional: false
      - name: "NAMESPACE"
        valueFrom:
          fieldRef:
            fieldPath: metadata.namespace
```

Without the ENV in podTemplate, every new `PipelineRun` above will need to create a new `Task` resource using 
stepTemplate to run the same examples if there is some change in env value. e.g.:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: mytask
  namespace: default
spec:
  stepTemplate:
    envs:
    - name: "MSG"
      value: "Overwritten message"
  steps:
    - name: echo-msg
      image: ubuntu
      command: ["bash", "-c"]
      args: ["echo $MSG $SECRET_PASSWORD $NAMESPACE"]
      envs:
      - name: "MSG"
        value: "Default message"
      - name: "SECRET_PASSWORD"
        value: "Default secret password"
      - name: "NAMESPACE"
        value: "tekton-pipelines"
---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: mytask2
  namespace: default
spec:
  stepTemplate:
    envs:
      - name: "MSG"
        valueFrom:
          fieldRef:
            fieldPath: metadata.labels['messages']
      - name: "SECRET_PASSWORD"
        valueFrom:
          secretKeyRef:
            name: mysecret
            key: password
            optional: false
      - name: "NAMESPACE"
        valueFrom:
          fieldRef:
            fieldPath: metadata.namespace
  steps:
    - name: echo-msg
      image: ubuntu
      command: ["bash", "-c"]
      args: ["echo $MSG $SECRET_PASSWORD $NAMESPACE"]
      envs:
      - name: "MSG"
        value: "Default message"
      - name: "SECRET_PASSWORD"
        value: "Default secret password"
      - name: "NAMESPACE"
        value: "tekton-pipelines"
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: one-task-pipeline-run
  namespace: default
spec:
  pipelineSpec:
    tasks:
      - name: mytaskrun
        taskRef:
          name: mytask
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: three-task-pipeline-run
  namespace: default
spec:
  pipelineSpec:
    tasks:
      - name: mytaskrun
        taskRef:
          name: mytask2
      - name: mytaskrun2
        taskRef:
          name: mytask2
        runAfter:
          - mytaskrun
      - name: mytaskrun3
        taskRef:
          name: mytask2
        runAfter:
          - mytaskrun2
```

5. Another use case is where admin can define a list of immutable environment variables in the cluster-wide configmap.
   Then, user will get error if these envs get defined in podtemplate of `PipelineRun` or `TaskRun`. List of forbidden 
   environment variables are located at the "config-defaults" configmap at the Tekton controller namespace.

Tekton configmap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-defaults
  namespace: tekton-pipelines
  labels:
    app.kubernetes.io/instance: default
    app.kubernetes.io/part-of: tekton-pipelines
data:
  pod-template-rules:
    forbidden-env-variables:
    - "HTTP_PROXY"
```

Tekton pipelinerun
```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: mytask
  namespace: default
spec:
  steps:
    - name: echo-msg
      image: ubuntu
      command: ["bash", "-c"]
      args: ["echo $HTTP_PROXY"]
---
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: mytaskrun
  namespace: default
spec:
  taskRef:
    name: mytask
  podTemplate:
    envs:
      - name: "HTTP_PROXY"
        value: "8080"
```

The above pipeline will return "HTTP_PROXY" is not a valid environment variable to define in the podTemplate.

6. User can also define a list of envs as part of global default pod template. All the tasks will have those envs set on steps.

Tekton configmap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-defaults
  namespace: tekton-pipelines
  labels:
    app.kubernetes.io/instance: default
    app.kubernetes.io/part-of: tekton-pipelines
data:
  default-pod-template:
    envs:
    - name: "MSG"
      value: "Default message"
```

Tekton pipelinerun
```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: mytask
  namespace: default
spec:
  steps:
    - name: echo-msg
      image: ubuntu
      command: ["bash", "-c"]
      args: ["echo $MSG"]
---
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: mytaskrun
  namespace: default
spec:
  taskRef:
    name: mytask
```
The default "MSG" environment variable will be available in step since it's set as part of the global default pod template.

### Notes/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

1. Forbidden Environment Variables are for pod template of `TaskRun` and `PipelineRun`, are they also valid for global 
   default pod Template? How will it be avoided then? How user will get the error for that?

2. If forbidden environment variables are specified, should they be avoided at Task's `stepTemplate` field or Step's 
   `Env` field too ?

3. Will there be option to pass different values of the same env, for different task in a pipeline? There can be a 
   case that the same env requires different value in different tasks of a pipeline, and if we put it at pipelineRun  
   spec level, then we are overwriting in all tasks.

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

In case of some environment variables are not allowed to change, it can have
a feature flag to opt-in with this new feature. Similar to the alpha API feature flag,
we can let the validation webhook fail with an error message when the feature flag is
disabled. The default behavior can change after 9 months of the Tekton release cycles.

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

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

Bring the task `stepTemplate` spec to the taskRuns and pipelineRuns. Similar to `stepTemplate`, 
pipelineRun `podTemplate` can overwrite the taskRun and taskRun `podTemplate` can overwrite `stepTemplate`.

#### PipelineRun and TaskRun API Changes

In the `podTemplate` struct, add the env variable field like:

```go
type Template struct {
	...
	
	// List of environment variables that can be provided to the containers belonging to the pod.
	// +optional
	Envs []corev1.EnvVar `json:"envs,omitempty" patchStrategy:"merge,retainKeys" patchMergeKey:"name" protobuf:"bytes,1,rep,name=envs"`
	
	...
}
```

`PipelineRun` spec already have `podTemplate` field, so new `Envs` field will be available here

```go
type PipelineRunSpec struct {
	....
	// PodTemplate holds pod specific configuration
	PodTemplate *PodTemplate `json:"podTemplate,omitempty"`
    ....
}
```

Also, `TaskRun` spec have `podTemplate` field, so `Envs` will be available here

```go
type TaskRunSpec struct {
	...
	
	// PodTemplate holds pod specific configuration
	PodTemplate *PodTemplate `json:"podTemplate,omitempty"`
	
	...
}
```

#### Global Default Environment Variables

Global level default can be provided at the `config-default` configmap under the `default-pod-template` field and the 
same `podTemplate` field is getting used to read the default values.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-defaults
  namespace: tekton-pipelines
data:
  default-pod-template:
    envs:
    - 
    -
    -
    ...
```

#### Precedence Order

We need to have the controller logic to act based on the envs available at different places. Controller should read all
and merge them till last stage which is converting them to container. The order of Precedence will look like this with 
first being the higher.

    a. Environment Variables in PipelineRun Pod Template or TaskRun Pod Template (Same priority as both are different places)
    c. Global Level Default Environment Variables in Tekton Default Pod Template
    d. Task Level Environment Variables in Task Step Template
    e. Step Level Environment Variables in Step Container Spec

If some default is configured and user is providing as the time of `PipelineRun` and `TaskRun`, then it should overwrite 
the default provided at global level.

#### Forbidden Environment Variables

There should be way to define the forbidden environment variables, which should not be overwritten by `PipelineRun` or 
`TaskRun`. If done so, webhook will throw an error that these are forbidden envs.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-defaults
  namespace: tekton-pipelines
  labels:
    app.kubernetes.io/instance: default
    app.kubernetes.io/part-of: tekton-pipelines
data:
  pod-template-rules:
    forbidden-env-variables : 
    - "HTTP_PROXY"
```

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
How does this proposal affect the api conventions, reusability, simplicity, flexibility
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

Define with a Top-level environment variable field. This new top-level field will be under the pipelinerun/taskrun spec 
level. Since the requirements also need to support Kubernetes value references such as secret, configmap, and Kubernetes 
downstream API, the type for this new spec will be an array of Kubernetes container V1 environment variable types.

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: mytaskrun
  namespace: default
spec:
  taskRef:
    name: mytask
  envs:
    - name: "HTTP_PROXY"
      value: "8080"
```

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: one-task-pipeline-run
  namespace: default
spec:
  pipelineSpec:
    tasks:
      - name: mytaskrun
        taskRef:
          name: mytask
  envs:
    - name: "MSG"
      value: "Overwritten message"

```

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail whether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

No impact on existing features. No breaking APIs. But if users configures global default environment variable, then 
task env may get overridden and env have different values.

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

Previously open: https://github.com/tektoncd/pipeline/pull/3566

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

Previously open

1. https://github.com/tektoncd/pipeline/issues/1606
2. https://github.com/tektoncd/pipeline/issues/3090
