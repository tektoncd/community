---
status: proposed
title: Pipeline-level Service
creation-date: '2023-01-24'
last-updated: '2023-02-21'
authors:
- '@lbernick'
collaborators: []
---

# TEP-0130: Pipeline-level Service

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Use Cases](#use-cases)
    - [Docker builds](#docker-builds)
    - [Other uses for this feature](#other-uses-for-this-feature)
  - [Goals](#goals)
  - [Requirements](#requirements)
  - [Related features in other CI/CD systems](#related-features-in-other-cicd-systems)
- [User Experience](#user-experience)
- [Proposal](#proposal)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Security](#security)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Do nothing](#do-nothing)
  - [Improve our documentation](#improve-our-documentation)
  - [Catalog Tasks for docker daemon](#catalog-tasks-for-docker-daemon)
  - [Pipeline-level Sidecar](#pipeline-level-sidecar)
    - [Open questions](#open-questions)
    - [Notes: Reusable sidecars](#notes-reusable-sidecars)
  - [First-class docker support](#first-class-docker-support)
  - [Docker daemon Custom Task](#docker-daemon-custom-task)
  - [Allow Pipeline Tasks to be run as daemons](#allow-pipeline-tasks-to-be-run-as-daemons)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes support for managing services with the same lifespan as a PipelineRun.
The primary use case for this feature is a Pipeline-level Docker daemon,
since it will allow users to create more customized Docker build Pipelines.

## Motivation

It's challenging to write a Tekton Pipeline that depends on an external service without exposing the service to multiple PipelineRuns. 
Task sidecars meet needs such as integration testing, but sometimes a service needs to be shared between multiple Tasks in a PipelineRun.
Right now, the best way for users to create a Pipeline-level service is to have one Task that spins up the service and a Finally Task that
tears it down, but this is non-trivial to write and leads to poor separation of concerns, with infrastructure
details built directly into build Pipelines. (For example, a developer writing a PipelineRun to build their
service might also need to concern themselves with how the service is created and torn down.)

### Use Cases

#### Docker builds

The docker-build catalog Task only allows building a single image and pushing it to a registry.
The following use cases are not addressed:
- Building multiple images concurrently with the same daemon to save resources and share cached base layers
  - For example, fanning out image build Tasks for the same repository via a Matrix
- Introducing additional steps, such as testing, in between a build and a push
  - A user may also want to guard guard execution of the push based on the results of those tasks
  - A user may also want to use the built image in these subsequent tasks without having to first push to and pull from a registry;
  for example, if using `docker exec` or `docker-compose`

Allowing multiple Tasks in a PipelineRun to use the same docker daemon allows PipelineRuns with
docker builds to take advantage of Pipeline features (e.g. using matrix to build multiple images,
executing a push conditionally on previous steps) while still having access to the same local
cache of built images and avoid having to push to a registry in between.

#### Other uses for this feature

A few other uses for Pipeline-level services have been proposed, but Docker builds are the highest priority use case identified so far.

- **Integration tests**: This feature may also be useful for integration tests that use a service to communicate with a test database.
However, integration tests are likely limited to a single Task; i.e. it's unlikely that a user would want multiple integration testing Tasks
to share the same test database. A test database Pipeline-level sidecar service could be limited to one Task (or a subset of Tasks) using
[Pipelines in Pipelines](./0056-pipelines-in-pipelines.md), or this use case could be met by allowing Pipelines or TaskRuns
to specify Task-level sidecars, as proposed in
[TEP-0126: Allow Task sidecars to be specified in PipelineRun](https://github.com/tektoncd/community/pull/877).

- **Heartbeats**: The [original feature request](https://github.com/tektoncd/pipeline/issues/2973) for Pipeline-level sidecar services was within a Pipeline
that uses Boskos resources. The first Task acquires the resources and creates a pod to send heartbeats to Boskos;
intermediate Tasks use the Boskos resources, and a Finally Task would release the lease on the resources and clean up the pod sending heartbeats.
One user [suggested](https://github.com/tektoncd/pipeline/issues/2973#issuecomment-672152635) that Boskos usage should be restricted to a subset of Tasks,
which could be done with Pipelines in Pipelines.

### Goals

- Users can easily create services per-PipelineRun that last for the lifespan of the PipelineRun
and can be easily referenced in the Pipeline.

### Requirements

- A Docker image built during a Pipeline can be used in a subsequent Task without first pushing it to an image registry
- Support [SLSA L3 build isolation requirements](https://slsa.dev/spec/v0.1/requirements#isolated)
("it MUST NOT be possible for a build to persist or influence the build environment for a subsequent build").
  - See ["Security"](#security) for more information.

### Related features in other CI/CD systems

A few other CI/CD systems have sidecar-like features.

The closest feature to Pipeline-level sidecar services is the Argo Workflows [daemon containers](https://argoproj.github.io/argo-workflows/walk-through/daemon-containers/) feature.
Daemon containers share the same lifespan as a Template, which can be analogous to a Task or a Pipeline. (Argo Workflows also has a [sidecar feature](https://argoproj.github.io/argo-workflows/walk-through/sidecars/) similar to Tekton's Task sidecars.)

Other CI/CD systems have features that are more analogous to Task sidecars in Tekton, and designed with integration tests in mind:
* GitHub Actions [service containers](https://docs.github.com/en/actions/using-containerized-services/about-service-containers)
  * Note: since GitHub Actions runs jobs on separate VMs, users don't have the option to create services
    accessible for a full Workflow run (a PipelineRun analogue).
* GitLab [services](https://docs.gitlab.com/ee/ci/services/)

Both [GitLab](https://docs.gitlab.com/ee/ci/docker/using_docker_build.html#use-the-docker-executor-with-docker-in-docker)
and [CircleCI](https://circleci.com/docs/executor-intro/#docker) provide Docker "executors" with built-in daemons that can be used for running Docker builds.

## User Experience

To create a Pipeline-level Docker daemon using existing features, users would have to use a first Task that creates a service and a deployment,
and a finally Task that tears it down. (These Tasks can be added to the catalog).

This Task would have to use a service account with permissions to create and delete services and deployments,
and mount a Workspace with k8s credentials.

The Task would also need to include a script to create the service and deployment, wait for it to start up,
and produce the service address as a result. (It probably shouldn't hard-code the service address,
because it would prevent multiple instances of the PipelineRun from running in the same namespace at the same time,
but it could create a service with a name prefixed by the TaskRun name.)

Here's what the same Pipeline would look like with existing features:

```yaml
kind: Pipeline
metadata:
  name: ci-with-docker-build
spec:
  params:
  - name: image
  - name: namespace
    value: $(context.pipelineRun.namespace)
  workspaces:
  - name: source
  - name: docker-tls-certs
  - name: kubeconfig-certs
  - name: sidecar-service-yaml
  results:
  - name: image-digest
    value: $(tasks.docker-build.results.IMAGE_DIGEST)
  tasks:
  - name: git-clone
    ...
  - name: startup-docker-daemon
    workspaces:
    - name: kubeconfig
    - name: docker-tls-certs
    - name: sidecar-service-yaml
    params:
    - name: namespace
    results:
    - name: daemon-host
    taskSpec:
      steps:
      - image: index.docker.io/aipipeline/kubeclient
        script: |
          KUBECONFIG=$(workspaces.kubeconfig.path)
          kubectl create -f $(workspaces.sidecar-service-yaml.path) -n $(params.namespace)
          kubectl wait deployment docker-daemon --for condition=Available -n $(params.namespace)
  - name: docker-build
    ...
    # Same spec as in the above example
    runAfter: ["git-clone", "startup-docker-daemon"]
  - name: pytest
    ...
    # Same spec as in the above example
  - name: docker-push
    ...
    # Same spec as in the above example
  finally:
  - name: teardown-docker-daemon
    ...
    # Similar to the "startup-docker-daemon" task
---
kind: PipelineRun
spec:
  pipelineRef:
    name: ci-with-docker-build
  workspaces:
  - name: kubeconfig-certs
    secret:
      secretName: kubeconfig
  - name: source
    ...
  - name: docker-tls-certs
    ...
  taskRunSpecs:
  # Use a service account with permissions to create and delete deployments and services
  - pipelineTaskName: startup-docker-daemon
    serviceAccountName: kube-creator
  - pipelineTaskName: teardown-docker-daemon
    serviceAccountName: kube-creator
```

Contents of the sidecar service yaml mounted onto the Task:

```yaml
apiVersion: v1
kind: Deployment
metadata:
  name: docker-daemon
  labels:
    app: docker
spec:
  template:
    spec:
      containers:
      - name: docker-daemon
        image: docker:dind
        securityContext:
          privileged: true
        ports:
        - containerPort: 2376
        startupProbe:
          tcpSocket:
            port: 2376
        volumeMounts:
        - name: docker-tls-certs
          mountPath: /certs/client
      volumes:
      - name: docker-tls-certs
        persistentVolumeClaim:
          claimName: docker-tls-certs
---
apiVersion: v1
kind: Service
metadata:
  name: docker-daemon-service
spec:
  selector:
    app.kubernetes.io/name: docker
  ports:
    - protocol: TCP
      port: 80
      targetPort: 9376
```

The Task creating a Docker daemon is simplified here in order to be shown as an example.
(There are a few problems with it: the same deployment and service will be used for each instance of the PipelineRun, and multiple instances can interfere with each other;
the deployment name and its volume mounts are hard-coded into the Task spec but the yaml is passed in via a workspace.)

A better approach might be to use a Task similar to the Catalog Task
[kubectl-deploy-pod](https://github.com/tektoncd/catalog/blob/5f6fc936854fa05ac710be12ecb8b43c8f37f742/task/kubectl-deploy-pod/0.1/kubectl-deploy-pod.yaml),
and modify it to create a service and a deployment (or use it twice, once for the service and once for the deployment), or to write custom code and build it into
a Task used specifically for creating a Docker daemon.

Here's what a docker build Task would look like if it used an external service as a daemon.
(This example is based on the [docker-build catalog task](https://github.com/tektoncd/catalog/blob/81bf7dc5610d5fa17281940a72a6377604105cea/task/docker-build/0.1/docker-build.yaml))

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: docker-build
spec:
  params:
  - name: image
    description: Reference of the image docker will produce.
  - name: docker_host  # This is new
    description: The address of the docker daemon to use.
  - name: builder_image
    description: The location of the docker builder image.
    default: docker.io/library/docker:stable@sha256:18ff92d3d31725b53fa6633d60bed323effb6d5d4588be7b547078d384e0d4bf #tag: stable
  - name: dockerfile
    description: Path to the Dockerfile to build.
    default: ./Dockerfile
  - name: context
    description: Path to the directory to use as context.
    default: .
  workspaces:
  - name: source
  - name: docker-tls-certs  # This is new
    optional: true
  results:
  - name: IMAGE_DIGEST
    description: Digest of the image just built.
  steps:
  - name: docker-build
    image: $(params.builder_image)
    env:
    # Connect to the sidecar over TCP, with TLS.
    - name: DOCKER_HOST
      value: $(params.docker_host)
    - name: DOCKER_TLS_VERIFY
      value: '1'
    - name: DOCKER_CERT_PATH
      value: /certs/client
    workingDir: $(workspaces.source.path)
    script: |
      docker build \
        --no-cache \
        -f $(params.dockerfile) -t $(params.image) $(params.context)
    workspaces:
      - name: docker-tls-certs
        mountPath: /certs/client
```

## Proposal

TODO. Most promising options are Catalog Tasks, Pipeline-level sidecars, and Custom Task.

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

### Security

TODO: Determine what implications, if any, this proposal has for provenance

SLSA L3 build isolation states that "it MUST NOT be possible for a build to persist or influence
the build environment for a subsequent build". This likely means that if we build first-class support
for a Pipeline-level service, the service should be accessible to only the PipelineRun that created it.

If we choose an alternative like improving our documentation, we can show ways of writing Docker build Pipelines
that build fresh each time using `--no-cache` and `--pull` (for example).

### Drawbacks

- May want to discourage people from using Docker daemons, due to security concerns related to privileged builds

## Alternatives

### Do nothing

Since pushing to image registries is relatively cheap, it's possible that users' Docker build needs already
well served by Task-level sidecars, and no new features are needed.
We can do user research to determine how much people would benefit from reduced resource usage and a different
UX when using Pipeline-level services.

### Improve our documentation

Instead of building new features, we could improve our documentation to help users better understand how to build a separate service into their PipelineRun.
See [user experience](#user-experience) for an example of what this would look like.

### Catalog Tasks for docker daemon

We could add Tasks to the verified catalog (or to a community catalog) for spinning up and tearing down a deployment with a service.
This would prevent users from having to write their own daemon creation/teardown tasks, but they would still have to provide their kube credentials
and use a service account with rolebindings that allow it to create services and deployments.
See [user experience](#user-experience) for an example of what this would look like.

Pros:
- Reuses existing features
- Container configuration is not copy-pasted between Tasks

Cons:
- Worse separation of concerns, since the person responsible for writing a build Pipeline has to worry
about specifying kube credentials and service account in their Pipeline
- If user misconfigures their Pipeline (e.g. passing wrong params into cleanup Task), the cleanup Task
may fail to run, wasting resources on the cluster
- Couples two Catalog Tasks together

### Pipeline-level Sidecar

Add support for Sidecars with the same lifespan as PipelineRuns, for example:

```yaml
kind: Pipeline
spec:
  params:
  - name: image
  - name: docker-host
    default: $(sidecars.docker-daemon.host):2376
  workspaces:
  - name: source
  - name: docker-tls-certs
  results:
  - name: image-digest
    value: $(tasks.docker-build.results.IMAGE_DIGEST)
  tasks:
  - name: git-clone
    ...
  - name: docker-build
    params:
    - name: image
    - name: docker-host
    workspaces:
    - name: source
    taskSpec:
      workingDir: $(workspaces.source.path)
      steps:
      - image: docker.io/library/docker
        script: docker build -f ./Dockerfile -t $(params.image)
        env:
        - name: DOCKER_HOST
          value: $(params.docker-host)
      results:
      - name: IMAGE_DIGEST
    runAfter: ["git-clone"]
  # This task uses the built image without first pushing it to a registry
  - name: pytest
    params:
    - name: docker-host
    - name: image
    taskSpec:
      workingDir: $(workspaces.source.path)
      steps:
      - image: docker.io/library/docker
        script: docker exec $(params.image) python -m pytest
        env:
        - name: DOCKER_HOST
          value: $(params.docker-host)
    runAfter: ["docker-build"]
  # This task pushes the image to the registry only if tests passed
  - name: docker-push
    when:
    - input: "$(tasks.pytest.status)"
      operator: in
      values: ["Succeeded"]
    params:
    - name: image
    - name: docker-host
    taskSpec:
      steps:
      - image: docker.io/library/docker
        script: docker push $(params.image)
        env:
        - name: DOCKER_HOST
          value: $(params.docker-host)
    runAfter: ["pytest"]
  sidecars:
  - name: docker-daemon
    image: docker:dind
    securityContext:
      privileged: true
    ports:
    - 2376
    startupProbe:
      tcpSocket:
        port: 2376
    workspaces:
    - name: docker-tls-certs   
```

The sidecar would likely be implemented as a deployment with one pod plus a service.
If the sidecar has readiness or startup probes, the PipelineRun would wait for them to succeed before starting the Pipeline Tasks.
We could use a [NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
to prevent other PipelineRuns from being able to use the sidecar.

Pros:
- Good separation of concerns: App developer creating build Pipeline doesn't have to worry about using the correct service accounts
or kube credentials
- Arguably better UX than using separate setup and teardown Tasks. Don't have to worry about resource leakage if teardown Task
fails due to a misconfigured PipelineRun.

Cons:
- Sidecar configurations will likely be copy-pasted between Pipelines.
  - This could be made more reusable or shareable in the future with features like reusable Sidecars,
    but this work would be out of scope for an initial version.
- If docker TLS certs are used, they must now be bound in a persistent volume claim to share
between multiple Tasks, rather than an emptyDir volume to share between multiple steps.
This is a pretty heavyweight option for a relatively small amount of data.
However, this is more an artifact of the limited options Pipelines currently has for sharing
data between Tasks, which should be treated as a separate problem.

#### Open questions

- Should Pipeline-level sidecars terminate before or after Finally Tasks?
- If a user specifies multiple sidecars, should they run in one pod or separate pods?
  - If the latter, do we want to provide a way to have multiple sidecar containers in one pod?

#### Notes: Reusable sidecars

A few sidecar configurations, such as docker daemons and database containers, likely make up the majority of use cases.
It's reasonable to ask whether we'd want to introduce a concept of a reusable sidecar.
For example, we could include a docker daemon sidecar in the catalog,
and allow Pipelines to contain inline sidecar specifications or references to sidecars
(stored on the hub, on the cluster, in git, etc, just like Tasks).

However, the lifespan of a reusable sidecar wouldn't be tied to the lifespan of a PipelineRun,
and managing it would expand the scope of responsibility of the PipelineRun controller.
This alternative would only be scoped to sidecars defined inline in a Pipeline.

### First-class Docker support

We could build in first class support for Docker, for example, a user could specify that they'd like their Pipeline to have a Docker daemon provided.
This solution is not proposed because it is too opinionated to align with our design principle on "flexibility".
There are multiple ways of building images (e.g. kaniko, Docker, buildkit) and no reason that Tekton should prefer one over the others.
Pipeline-level services can be used in much more flexible ways.

### Docker daemon Custom Task

We could create a Docker daemon custom task, for example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
spec:
  workspaces:
  - name: source
  - name: docker-tls-certs
  tasks:
  - name: git-clone
    ...
  - name: startup-docker-daemon
    taskRef:
      apiVersion: tekton.dev/v1beta1
      kind: docker
    workspaces:
    - name: docker-tls-certs
  - name: docker-build
    runAfter: ["startup-docker-daemon"]
    params:
    - name: docker-host
      value: $(tasks.startup-docker-daemon.results.host)
    ...
    # Same spec as in the above example
  - name: pytest
    ...
    # Same spec as in the above example
  - name: docker-push
    ...
    # Same spec as in the above example
```

The Docker daemon custom task would be responsible for creating a service and deployment. Once the deployment is ready,
the CustomRun would have "ConditionSucceeded" set to "true", and subsequent tasks would start.
The custom task controller would also observe PipelineRuns, and delete any deployments and services associated with completed PipelineRuns.

We could add support to the Catalog for custom tasks, and put the docker custom task into the Catalog.
Work required to support custom tasks in the Catalog is tracked in https://github.com/tektoncd/catalog/issues/1147.

Pros:
- Compared to using regular Tasks, only one additional Task is needed (instead of setup and teardown)
- Service account that can create deployments and services is only needed by the custom task controller instead of by each build Pipeline.
The service account and rolebindings can be set up by the cluster operator when the custom task controller is installed, instead of app developers
needing to understand why and how to use it in their Pipelines.
- Do not need to copy/paste docker daemon container yaml into multiple Pipelines

### Allow Pipeline Tasks to be run as daemons

This option is most similar to the Argo Workflows [daemon containers](https://argoproj.github.io/argo-workflows/walk-through/daemon-containers/)
feature. For example:

```yaml
kind: Task
metadata:
  name: docker-daemon
spec:
  params:
  - name: port
  workspaces:
  - name: docker-tls-certs
  steps:
  - name: sleep-forever
    image: busybox
    script: sleep inf
  sidecars:
  - image: docker:dind
    securityContext:
      privileged: true
    ports:
    - 2376
    startupProbe:  # Only sidecars (not steps) can have startup and readiness probes as of v1
      tcpSocket:
        port: $(params.port)
---
kind: Pipeline
spec:
  params:
  - name: image
  - name: docker-host
    value: $(tasks.docker-daemon.host):2376
  workspaces:
  - name: source
  - name: docker-tls-certs
  results:
  - name: image-digest
    value: $(tasks.docker-build.results.IMAGE_DIGEST)
  tasks:
  - name: docker-daemon
    mode: "daemon"  # This would be the new field; syntax TBD
    params:
    - name: port
      value: 2376
    workspaces:
    - name: docker-tls-certs
    taskRef:
      name: docker-daemon
  - name: git-clone
    ...
  - name: docker-build
    ...
  - name: pytest
    ...
  - name: docker-push
    ...
```

There are two ways this could work.

Strategy 1:

The docker-daemon Task contains a docker sidecar and a step that runs forever (as shown in the example).
The PipelineRun controller waits for the sidecar's readiness probe to succeed before starting other Tasks.
At the end, the PipelineRun controller cancels the TaskRun, causing deletion of the TaskRun pod,
and marks the PipelineRun as successful.

strategy 2:

The docker-daemon Task contains a docker sidecar and a step that exits once the sidecar is ready.
We would have to create some way of signaling the TaskRun controller to not mark the pod as completed,
so the TaskRun continues running. Once the TaskRun is marked as successful, the PipelineRun controller
would start any other Pipeline Tasks. At the end, the PipelineRun controller would delete the sidecar TaskRun.

Pros:
- No need to copy/paste sidecar configuration
- No need to configure a service account and kube config -> better separation of concerns between
app developers and cluster operators

Cons:
- Poor separation of concerns between the PipelineRun and TaskRun controllers.
We could do things like adding a "Ready" status to TaskRuns, having a TaskRun finish without
tearing down the sidecars, or having the PipelineRun controller observe a pod's readiness probe,
none of which make sense in the context of a regular Task.

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

- [[FR] Pipeline-level sidecars](https://github.com/tektoncd/pipeline/issues/5112)
- [Pipeline level sidecar](https://github.com/tektoncd/pipeline/issues/2973)
