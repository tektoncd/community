---
status: proposed
title: Platform Context Variables
creation-date: '2023-08-21'
last-updated: '2023-08-21'
authors:
- '@lbernick'
collaborators: []
---

# TEP-0141: Platform Context Variables

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Use Cases](#use-cases)
  - [Goals](#goals)
  - [Non-Goals/Future Work](#non-goalsfuture-work)
  - [Requirements](#requirements)
  - [Existing Workarounds](#existing-workarounds)
    - [Substitute directly in PipelineRun spec](#substitute-directly-in-pipelinerun-spec)
    - [Build a higher-level API](#build-a-higher-level-api)
    - [Inject Environment Variables](#inject-environment-variables)
    - [Create a ConfigMap per PipelineRun](#create-a-configmap-per-pipelinerun)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [TaskRun and PipelineRun syntax](#taskrun-and-pipelinerun-syntax)
  - [Parameter substitution](#parameter-substitution)
  - [Provenance generation](#provenance-generation)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes support for allowing platforms that build on top of Tekton to specify default, platform-specific variables that can be easily passed into Tasks and Pipelines, such as data from the event that triggered it.

## Motivation

### Use Cases

- Allow PipelineRuns to easily reference data related to the event(s) that triggered them. For example, a CI Pipeline might include a finally Task that posts status back to the pull request/merge request that triggered it, and needs to reference the pull request event when posting the status update.
  - A similar feature in Github Actions is the ["github" context](https://docs.github.com/en/actions/learn-github-actions/contexts#github-context).
  - This is also similar to the [variable substitution feature in Pipelines as Code](https://pipelinesascode.com/docs/guide/authoringprs/), which allows the user to specify variables like `{{event_type}}` in their PipelineRun.

- Allow PipelineRuns to reference their unique IDs on the platforms they run on.

- A vendor would like to provide default configuration shared between a PipelineRun and the platform's SCMs or image registries, and allow it to be easily referenced in the PipelineRun.

### Goals

- Allow platform builders to provide arbitrary context variables that can be referenced in PipelineRuns and TaskRuns

### Non-Goals/Future Work

- Support variable replacement of sensitive/secret data
- Support different configuration of platform-supported variables per namespace; this is better suited to address in [TEP-0085: Per-Namespace Controller Configuration](./0085-per-namespace-controller-configuration.md) and can be added later
- Support easily injecting an entire event body as a parameter to a TaskRun or PipelineRun. While this may be desirable, this would require implementing support for nested arrays and objects within object parameters.
- Define "reserved" context variables that different platforms can provide their own implementation for.

### Requirements

- Chains must be able to identify which context variables are supplied by the vendor.
  - When generating [provenance](https://slsa.dev/spec/v1.0/provenance), Chains identifies the TaskRun/PipelineRun spec as an "external parameter" (supplied by the user rather than the build system). This design should provide a mechanism for Chains to identify system-provided parameters so they can be output correctly in the "internal parameters" of the provenance's BuildType.  

- Task/Pipeline authors and users can't add, modify, or remove platform context variables. Doing so could result in falsifiable provenance, where a user could make a variable appear to be injected by the platform when in reality it was not.

### Existing Workarounds

Consider the following Pipeline, which uses catalog Tasks to clone a repo, build an image using Kaniko, and push the image to a remote repository:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: clone-kaniko-build-push
spec:
  workspaces:
  - name: source-code
  params:
  - name: image
  - name: repo-url
  tasks:
  - name: fetch-source
    taskRef:
      resolver: hub
      params:
      - name: name
        value: git-clone
      - name: version
        value: "0.7"
    workspaces:
    - name: output
      workspace: source-code
    params:
    - name: url
      value: $(params.repo-url)
  - name: build
    taskRef:
      resolver: hub
      params:
      - name: name
        value: kaniko
      - name: version
        value: "0.6"
    params:
    - name: image
      value: $(params.image)
    workspaces:
    - name: source-code
    runAfter:
    - fetch-source
```

The platform builder may want to provide default variable substitutions for these parameters, or parts of these parameters. For example, the platform could provide a variable substitution for the URL of a repo where an event triggering a run of this Pipeline occurred, which could be used to substitute the full "repo_url" param. The platform could also provide the location of the image/artifact registry where the built image should be pushed, which could be used to substitute part of the "image" param.

This section discusses several ways the platform builder could provide these parameter substitutions.

#### Substitute directly in PipelineRun spec

The platform could directly substitute any variables defined in the PipelineRun spec before submitting the PipelineRun to their Tekton implementation. For example, let's say the user defines the following PipelineRun:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: clone-kaniko-build-push-run
spec:
  pipelineRef:
    name: clone-kaniko-build-push
  params:
  - name: repo-url
    value: $REPO_URL
  - name: image
    value: $IMAGE_REGISTRY/myapp
  workspaces:
  - name: source-code
    ...
```

The platform builder could substitute `$REPO_URL` and `$IMAGE_REGISTRY` with the appropriate values before creating the PipelineRun.
However, this would involve mutating user-provided PipelineRun specs, and would likely not be considered Tekton conformant, as PipelineRuns don't support the syntax `$REPO_URL` and `$IMAGE_REGISTRY`. It would also cause confusion if PipelineRuns did start supporting this syntax in the future.

#### Build a higher-level API

To avoid mutating user-specified PipelineRun specs, platforms could build higher-level APIs that reference PipelineRuns, and allow variable substitutions within these APIs. This is the approach taken by Triggers. For example, TriggerTemplates support the following syntax:

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: clone-build-template
spec:
  params:
  - name: repo-url
  - name: image-registry
  resourcetemplates:
  - apiVersion: tekton.dev/v1
    kind: PipelineRun
    metadata:
      generateName: clone-build-run-
    spec:
      pipelineRef:
        name: clone-kaniko-build-push
      params:
      - name: repo-url
        value: $(tt.params.repo-url)
      - name: image-registry
        value: $(tt.params.image-registry)/myapp
```

This approach adds verbosity for PipelineRun authors, and doesn't allow provenance generators to distinguish between parameters provided by the PipelineRun author from parameters provided by the platform.

#### Inject Environment Variables

The platform builder could also inject environment variables into TaskRun pods; for example, by using a mutating admission webhook for pods. This works well for users who define their own Tasks, for example:

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: kaniko-build
spec:
  workspaces:
  - name: source-code
  params:
  - name: image-name
  results:
  - name: digest
  steps:
  - name: build-and-push
    image: "gcr.io/kaniko-project/executor:v1.5.1"
    args: [
      "--dockerfile=$(workspaces.source-code.path)/Dockerfile",
      "--context=dir://$(workspaces.source-code.path)",
      "--destination=$IMAGE_REGISTRY/$(params.image-name)",
      "--digest-file=$(results.digest.path)",
    ]
```
(Note the destination `$IMAGE_REGISTRY/$(params.image-name)`.)

However, this approach doesn't work for providing parameter values to existing Tasks that expect them, since environment variables can't be substituted inside Tekton parameters. In addition, environment variables can be used only in script, args, and command, but can't be used in other places where params can be substituted, such as the name of the image run by a Step. Lastly, using environment variables instead of parameters makes Tasks less reusable, since they can only run on platforms which provide these environment variables, as noted in [this comment](https://github.com/tektoncd/pipeline/issues/1294#issue-491170402) and [this comment](https://github.com/tektoncd/pipeline/issues/1294#issuecomment-683348479).

#### Create a ConfigMap per PipelineRun

This workaround is described in [triggers#1574](https://github.com/tektoncd/triggers/issues/1574) and [pipeline#1294](https://github.com/tektoncd/pipeline/issues/1294#issuecomment-531321704). With this workaround, the provider creates a ConfigMap for each PipelineRun, and mounts the ConfigMap as a PipelineRun workspace.

The downside of this approach is that Tasks can't easily reference the values of these variables; instead, they must read the values from workspaces. In addition, this does not address the problem of accurate provenance generation, and the ConfigMap must be deleted when the PipelineRun is deleted (or completed).

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation. The "Design Details" section below is for the real
nitty-gritty.
-->

### Notes and Caveats

<!--
(optional)

Go in to as much detail as necessary here.
- What are the caveats to the proposal?
- What are some important details that didn't come across above?
- What are the core concepts and how do they relate?
-->


## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable. This may include API specs (though not always
required) or even code snippets. If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->


## Design Evaluation
<!--
How does this proposal affect the api conventions, reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

### Reusability

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#reusability

- Are there existing features related to the proposed features? Were the existing features reused?
- Is the problem being solved an authoring-time or runtime-concern? Is the proposed feature at the appropriate level
authoring or runtime?
-->

### Simplicity

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#simplicity

- How does this proposal affect the user experience?
- What’s the current user experience without the feature and how challenging is it?
- What will be the user experience with the feature? How would it have changed?
- Does this proposal contain the bare minimum change needed to solve for the use cases?
- Are there any implicit behaviors in the proposal? Would users expect these implicit behaviors or would they be
surprising? Are there security implications for these implicit behaviors?
-->

### Flexibility

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#flexibility

- Are there dependencies that need to be pulled in for this proposal to work? What support or maintenance would be
required for these dependencies?
- Are we coupling two or more Tekton projects in this proposal (e.g. coupling Pipelines to Chains)?
- Are we coupling Tekton and other projects (e.g. Knative, Sigstore) in this proposal?
- What is the impact of the coupling to operators e.g. maintenance & end-to-end testing?
- Are there opinionated choices being made in this proposal? If so, are they necessary and can users extend it with
their own choices?
-->

### Conformance

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#conformance

- Does this proposal require the user to understand how the Tekton API is implemented?
- Does this proposal introduce additional Kubernetes concepts into the API? If so, is this necessary?
- If the API is changing as a result of this proposal, what updates are needed to the
[API spec](https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md)?
-->

### User Experience

<!--
(optional)

Consideration about the user experience. Depending on the area of change,
users may be Task and Pipeline editors, they may trigger TaskRuns and
PipelineRuns or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

### Performance

<!--
(optional)

Consider which use cases are impacted by this change and what are their
performance requirements.
- What impact does this change have on the start-up time and execution time
of TaskRuns and PipelineRuns?
- What impact does it have on the resource footprint of Tekton controllers
as well as TaskRuns and PipelineRuns?
-->

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate? Think broadly.
For example, consider both security and how this will impact the larger
Tekton ecosystem. Consider including folks that also work outside the WGs
or subproject.
- How will security be reviewed and by whom?
- How will UX be reviewed and by whom?
-->

### Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

<!--
What other approaches did you consider and why did you rule them out? These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->


## Implementation Plan

<!--
What are the implementation phases or milestones? Taking an incremental approach
makes it easier to review and merge the implementation pull request.
-->


### Test Plan

<!--
Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all the test cases, just the general strategy. Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

### Infrastructure Needed

<!--
(optional)

Use this section if you need things from the project or working group.
Examples include a new subproject, repos requested, GitHub details.
Listing these here allows a working group to get the process for these
resources started right away.
-->

### Upgrade and Migration Strategy

<!--
(optional)

Use this section to detail whether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

### Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

- [Better support for CI systems that provide many env vars](https://github.com/tektoncd/pipeline/issues/1294)
- [Provide a mechanism to more easily access the "event" in a workspace in pipelines](https://github.com/tektoncd/triggers/issues/1574)
