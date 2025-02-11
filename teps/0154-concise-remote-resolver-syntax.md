---
status: implementable 
title: Concise Remote Resolver Syntax 
creation-date: '2024-03-12'
last-updated: '2024-03-21'
authors:
- '@chitrangpatel'
contributors:
- '@wlynch'
---

# TEP-0154: Concise Remote Resolver Syntax 

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Stage 1](#stage-1)
    - [Extending the `resolver` field](#extending-the-resolver-field)
    - [Resolver Reference](#resolver-reference)
    - [Built-in Resolvers](#built-in-resolvers)
      - [Git Resolver](#git-resolver)
      - [Bundle Resolver](#bundle-resolver)
      - [Http Resolver](#http-resolver)
      - [Hub Resolver](#hub-resolver)
      - [Cluster Resolver](#cluster-resolver)
    - [Custom Resolvers](#custom-resolvers)
  - [Stage 2](#stage-2)
    - [Prioritized Subscription to `scheme`s](#prioritized-subscription-to-schemes)
    - [Creating the resolution request](#creating-the-resolution-request) 
- [Design Details](#design-details)
  - [Updating the `name` field](#updating-the-name-field)
  - [ValidateName](#validatename)
  - [Resolving the schemes](#resolving-the-schemes)
- [Alternatives](#alternatives)
  - [Simultaneous request to all subscribed resolvers](#simultaneous-request-to-all-subscribed-resolvers)
  - [Using CRD to store prioritized sunscription configuration](#using-crd-to-store-prioritized-subscription-configuration)
<!-- /toc -->

## Summary

We want to provide users a concise remote-resolver syntax. Additionally, we also want to enable remote resolution such that users don't have to worry about which resolver they are using for generic url schemes like `https`.

## Motivation

The current remote resolution syntax is quite verbose. Previously there used to be a one-liner that users could provide to the resolver when referencing a `Task` or a `Pipeline`. Reducing the current syntax (which could get to multiple lines very easily) down to a one-liner would help reduce the already quite verbose Tekton Spec.

Users have to currently know exactly which resolver they are using and is supported on the cluster. When running the same workload on another cluster, if the same resolvers are not supported then their workflow (`PipelineRun/TaskRun`) is not runnable as is. If users only needed to provide the url of the remote resource and not have to worry about which resolver to choose to resolve the remote resolution request, then for most generic url schemes like `oci://`, `https://` etc. they would not need to provide the resolver name and therefore, would make the workflow generic.  

### Goals

* Provide a way to pass the one-liner resolver-reference to the resolvers.
* Provide guidelines on how resolvers can format the expected resolver-reference.
* Define the formats for the existing Tekton's resolvers.
* The resolvers should be able to subscribe to the schemes automatically. 

### Non-Goals

### Use Cases

* As a task/pipeline author, I would like to reduce the verbosity of the yaml.
* As a task/pipeline author, I just want to be able to provide the url to the remote resource instead of having to investigate each resolver and the exact params they need.

### Requirements

* The new resolver-reference should not be backwards incompatible. It should be an additive change.
* The new resolver-reference should be optional.
* The custom-resolver guides should be updated to include how users can use the new resolver-reference.

## Proposal

We split the design into two stages:
* [Stage 1](#stage-1): Scheme based concise resolver syntax
* [Stage 2](#stage-2): Scheme based subscription for Remote Resplution 

### Stage 1
This stage focuses on achieving the concise remote resolver syntax based on a url-format.

#### Extending the `resolver` field

Current Remote Resolution syntax looks like follows for fetching the resource from a remote location:

```yaml
taskRef:
  resolver: <resolver-name>
  params:
    - name: ...
      value: ...
    ...
``` 

For fetching the resource already applied to the cluster, we rely on the name field:
```yaml
taskRef:
  name: name-of-the-task
```

Currently, users can either use the `name` field or the combination of `resolver` and `params`. The two fields (`name` and `resolver`) cannot be used together as the admission controller will not allow it.
We propose changing this behavior such that they are both allowed. We propose updating the `name` field whose value can also be the [resolver-reference](resolver-reference). For example: 

```yaml
taskRef:
  name: <resolver-reference>
  resolver: <resolver-name>
```

In turn, the Tekton controller will pass the `name` to the `Remote Resolver` (identified by the `resolver` field ). The remote resolver will parse the `name` and extract the necessary information it needs to perform resolution. In [stage 2](#stage-2), Tekton will auto-detect which resolver to forward the request to so that users dont need to explicitly declare the name of the resolver on the cluster.
 
#### Resolver Reference

[Package-URL](https://github.com/package-url/purl-spec) is a format that we have begun to use in Tekton Artifacts. To enable a consistent concise format for across resolvers, we propose taking purl as an inspiration to define our format. The reason for not using purl directly is that it is too rigid for the different types of resolvers.

To provide a consistent format across resolvers, we suggest the following `remote-resolver` template: `<scheme>://<location>[@<version>][#<selector>][?<params>]`. This template is a "best practice" so that all resolvers follow a similar template. It will not be enforced by the Tekton Pipeline/Task controllers. In the template, `scheme` is required while `location`, `version`, `selector` and `params` are all optional and should be parsed by the `Remote Resolvers` according to their needs. Additionally, the value of the `name` must be `url encoded`.
In [stage 2](#stage-2), remote resolvers will subscribe to `scheme`s that they support and Tekton will auto-forward the resolution request to the subscribed resovers based on a configured priority. 

The `Remote Resolver` must define the format using the above `remote-resolver` template. The `Remote Resolver` is responsible for parsing the `name` and extracting the necessary information. The Tekton controller will only validate that the `name` starts with `<scheme>://`. If a `scheme` is found, it will match against the schemes that the resolvers accept. If provided `scheme` is not supported by any of the resolvers, then it will throw an error. If the `name` does not start with `<scheme>://`, the Tekton controller will then treat it as a local reference and not forward the request to the remote resolvers. Validation of the other optional fields must be conducted by the resolvers themselves. 

The `Remote Resolver` does not need to be able to parse all possible schemes. It can document the schemes it understands and what the underlying format it uses to understand the resolver reference. For instance, the git resolver might only understand schemes `https`, `git+https`, `git`, `scmType` have the underlying resolver reference format suited to it.

Examples:
```
https://github.com/tektoncd/test@main#task.yaml
git+https://github.com/tektoncd/test@main#task.yaml
git://github.com/tektoncd/test@main#task.yaml
github://tektoncd/test@main#task.yaml
oci://tektoncd/image:v1@sha256:...#task/foo?secret=my-secret
https://example.com/task.yaml
http://10.5.3.2:8080/task.yaml
artifact/tasks-catalog/tasks/task@v1.0 # e.g. for the hub resolver where there is no need for a scheme
```

Since depending on the `scheme`, the choice of `params` could be different, we choose to not allow the use of the `params` field if the `name` is being used. The `params` for a `scheme` can be passed in the `name` so there is no need to allow both. i.e. This is not allowed:
 
```yaml
taskRef:
  name: <scheme>://<location>[@<version>][#<selector>][?<params>] 
  resolver: <resolver-name>
  params: # Not allowed since params can be specified as part of the name.
    # resolver-params
    ...
```

#### Built-in Resolvers

Tekton provides the following built-in resolvers:
- [git](#git-resolver)
- [bundles](#bundle-resolver)
- [http](#http-resolver)
- [hub](#hub-resolver)
- [cluster](#cluster-resolver)

This section shows the proposed schemes and the formats based on the above [template](#resolver-reference) for each of the built-in resolvers.
 
##### Git Resolver
Based on `git` resolver's [params](https://tekton.dev/docs/pipelines/git-resolver/#parameters), we define the following `resolver-reference` formats:

If scheme is `git`, `git+https` or `https`,

```
<git/git+https/https>://<complete git repo>@<revision>#<pathInRepo>?token=<token>&tokenKey=<tokenKey>
```

Example:

```
https://github.com/tektoncd/catalog@sha256:053a6cb9f3711d4527dd0d37ac610e8727ec0288a898d5dfbd79b25bcaa29828#task/hello-world?token=git-token
git://github.com/tektoncd/catalog@sha256:053a6cb9f3711d4527dd0d37ac610e8727ec0288a898d5dfbd79b25bcaa29828#task/hello-world?token=git-token
git+https://github.com/tektoncd/catalog@sha256:053a6cb9f3711d4527dd0d37ac610e8727ec0288a898d5dfbd79b25bcaa29828#task/hello-world?token=git-token
```

Using the above example, a user can do the following when referencing the Task:
```yaml
taskRef:
  name: https://github.com/tektoncd/catalog@sha256:053a6cb9f3711d4527dd0d37ac610e8727ec0288a898d5dfbd79b25bcaa29828#task/hello-world?token=git-token
  resolver: git
```

Alternatively, if the `scheme` is the `scmType` then the format is:

```
<scmType>://<org>/<repo>@<revision>#<pathInRepo>?token=<token>&tokenKey=<tokenKey>
```

**Note**, there could be many possible `scmType`s, especially for enterprise users where they have a custom/unique `scmType`. This makes [stage 2](#stage-2) challenging in this scenario as all need to be registered as valid schemes. In this case, we suggest users choosing the specific `resolver` so that `Tekton` does not need to identify which resolver to forward the request to.  

Example:

```yaml
github.com://tektoncd/pipeline@v0.57.0#examples/taskruns/v1/hello.yaml
gitlab.com://foo/bar@sha256:053a6cb9f3711d4527dd0d37ac610e8727ec0288a898d5dfbd79b25bcaa29828#examples/taskruns/v1/hello.yaml
```


##### Bundle Resolver
Based on `bundle` resolver's [params](https://tekton.dev/docs/pipelines/bundle-resolver/#parameters), we define the following `resolver-reference` format: 

```
oci://<bundle-provider>/<bundle-namespace>/<bundle-name>@<bundle-version>?kind=<kind>&name=<name>&secret=<secret>
```

Example

```
oci://docker.io/ptasci67/example-oci@sha256:053a6cb9f3711d4527dd0d37ac610e8727ec0288a898d5dfbd79b25bcaa29828?kind=task&name=hello-world&secret=default
```

Using the above example, a user can do the following when referencing the Task:
```yaml
taskRef:
  resolver: bundles
  name: "oci://docker.io/ptasci67/example-oci@sha256:053a6cb9f3711d4527dd0d37ac610e8727ec0288a898d5dfbd79b25bcaa29828?kind=task&name=hello-world&secret=default"
```

Occasionally, users may want to fetch from a private registry (e.g. at `10.96.190.208:5000`).

```yaml
taskRef:
  resolver: bundles
  name: "oci://10.96.190.208:5000/ptasci67/example-oci@sha256:053a6cb9f3711d4527dd0d37ac610e8727ec0288a898d5dfbd79b25bcaa29828?kind=task&name=hello-world?secret=default"
```

##### Http Resolver
Based on `http` resolver's [params](https://tekton.dev/docs/pipelines/http-resolver/#parameters), we define the following `resolver-reference` format: 

```
<http-url>?http-username=<http-username>&http-password-secret=<http-password-secret>&http-password-secret-key=<http-password-secret-key>
```

Here, the url contains the `scheme` and `location`: `<scheme>://<locaiton>`:

Example:
```
http://example.com/foo/task.yaml
https://raw.githubusercontent.com/tektoncd-catalog/git-clone/main/task/git-clone/git-clone.yaml
```

Using the above example, a user can do the following when referencing the Task:
```yaml
taskRef:
  resolver: http
  name: "https://raw.githubusercontent.com/tektoncd-catalog/git-clone/main/task/git-clone/git-clone.yaml?http-username=git&http-password-secret=git-secret&http-password-secret-key=git-token"
```

##### Hub Resolver
Based on `hub` resolver's [params](https://tekton.dev/docs/pipelines/hub-resolver/#parameters), we define the following `resolver-reference` format: 

```
artifacthub://<catalog>/<kind>/<name>@<version>
tektonhub://<catalog>/<kind>/<name>@<version>
```
**Note** that we use a scheme called `artifacthub` or `tektonhub` which is only meaningful to the hub resolver.

Example:

```
artifacthub://tekton-catalog-tasks/task/git-clone@0.6
```

Using the above example, a user can do the following when referencing the Task:

```yaml
taskRef:
  resolver: hub
  name: "artifacthub://tekton-catalog-tasks/task/git-clone@0.6"
```

##### Cluster Resolver
Based on `cluster` resolver's [params](https://tekton.dev/docs/pipelines/cluster-resolver/#parameters), we define the following `resolver-reference` format: 

```
cluster://<namespace>/<kind>/<name>
```

**Note** that we use a scheme called `cluster` which is only meaningful to the cluster resolver.

Example:

```
cluster://default/task/git-clone
```

Using the above example, a user can do the following when referencing the Task:

```yaml
taskRef:
  resolver: "cluster"
  name: "cluster://default/task/git-clone" 
```

#### Custom Resolvers
When implementing a new custom resolver, just like users have the freedom to choose their parameters, they also have the freedom to define their `name` (or `url`) based on:

```
<scheme>://<location>[@<version>][#<selector>][?<params>]
```

The custom resolver must determine the schemes it wants to support and subscribe to (in case of stage 2). For each scheme, it must define the remainder of `location, version, selectors and params` as needed. An example `scheme` could be `<custom-resolver-name>`. A `location` may be made up of concrete units e.g. `location = <foo>/<bar>` (i.e. expect two parts) that are up to the discretion of the custom resolvers.

The custom resolver must validate the `name` which will be passed within the `Remote Resolution CRD's` spec. The `name` (or `url`) can then be parsed based on the format for that `scheme` and used to fetch the remote resource.

### Stage 2

In this stage, we enable the Tekton controller to be able to identify the resolvers on the clusters that have subscribed to the scheme of the incoming [resolver reference](#resolver-reference).

#### Prioritized Subscription to `scheme`s
This mapping of `scheme` to `resolver` could be easily maintained in a `configMap` (or a [CRD](#using-crd-to-store-prioritized-subscription-configuration)) for the cluster. For [built-in resolvers](#built-in-resolvers), Tekton installation will be pre-configured with the schemes and priorities so that the cluster operators do not need to worry about any interaction unless they want to update the priority or additional custom resolvers. The cluster operators will only be required to know the custom remote resolvers that are running on the cluster and the schemes they are subscribed to. They can modify the existing configuration to add the custom resolvers. This means that any resolver that is not a [built-in](#built-in-resolvers) resolver needs to be explicitly added to this configMap. The configMap must list out all the schemes supported by all the resolvers in order of priority.

Each remote resolver will subscribe to `scheme`s. e.g. the git resolver might subscribe to `scheme`s like `git+https`, `https` or a bundle resolver might subscribe to `scheme`s like `oci`. If a custom resolver can handle any scheme then we use `"*"` as the key to indicate that any scheme that is not specified in the configMap can be passed to that custom resolver. For the specifically listed schemes, this custom resolver also needs to be placed in the comma-separated priority sequence.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: remote-resolution-scheme-subscription
  namespace: tekton-pipelines
data:
  #<scheme>: "<resolvers subscribed to the scheme; comma separated in order of priority>"
  https: "git,http,my-custom-resolver"
  git+https: "git,my-custom-resolver"
  git: "git,my-custom-resolver"
  http: "http,my-custom-resolver"
  oci: "bundle,my-custom-resolver"
  artifacthub: "hub,my-custom-resolver"
  *: "my-custom-resolver"
```
Even though the reterival of the k-v pairs is not ordered, the comma-separated list gives the deterministic behaviour since that order will not change.

####  Creating the resolution request
The when the Tekton controller (`PipelineRun` or `TaskRun`) creates a resolution request, it will match the `scheme` to the prioritized resolvers and create a new resolution request for each resolver in order of the priority until the first one succeeds. If all of the resolvers subscribed to the scheme fail to resolve it then the Tekton controller will also fail the `TaskRun/PipelineRun`. If a `scheme` is not supported by any of the resolvers on the cluster then the Tekton controller will directly fail the `TaskRun/PipelineRun`.

In the scenario that the user provides both the `name` and the `resolver`, the user is specifying the exact resolver they wish to send the request to. Therefore, Tekton will not try to identify the resolvers that have subscribed to the scheme. Instead, it will forward the request to the specified resolver like it does today.

## Design Details
The feature will be gated behind a feature flag: `enable-concise-resolver-syntax`. The feature will be propagated through the lifecycle of `alpha --> beta --> stable` like we do with other features.

### Updating the `name` field
* Currently the value of the `name` field in a `taskRef/pipelineRef/ref` must be a sub-domain name. We will loosen this restricitons to also allow for a url-like name. For example:
```yaml
taskRef:
  name: https://github.com/tektoncd/pipeline@v0.56.3#examples/v1/taskruns/hello.yaml # will now be allowed.
```
 
* The string field `name` will also be added to the [ResolutionRequest CRD's spec](https://github.com/tektoncd/pipeline/blob/ab47f4ef789c36b157b4f2e734e3a0b5f49fb9ad/pkg/apis/resolution/v1beta1/resolution_request_types.go#L59-L67) which will contain the value (after variable replacement).
* The individual resolver is expected to [validate the `name`](#validatename), extract the necessary information and perform the resolution because the format and how the information is used is only known to the resolver itself. 

### ValidateName
We propose adding the `ValidateName` (just like `ValidateParams`) method to the Resolver interface. The resolver will be responsible for validating this `name`. The framework will call this method before calling the `Resolve` method. 

### Resolving the schemes

When the Tekton controller detects a resolver reference field in the `Pipeline/Task`, it will fetch the associated resolvers from the `remote-resolution-scheme-subscription` configMap. The value is a comma-separated string containing the resolver names. Stating from the first resolver (on the left), it will create a new resolution request to the first remote resolver. If the remote resolver fails to resolve the CRD, the Tekton Controller will send out a new resolution request to the next resolver. Since the name of the resolver can be found in the Resolution Request CRD, the Tekton controller knows which one failed so that it can try the next one on the comma-separated value. If all the resolvers fail, the Tekton controller will fail the `TaskRun/PipelineRun`. If the `scheme` is not found in the `remote-resolution-scheme-subscription` configMap then the Tekton Controller will fail the `TaskRun/PipelineRun`.

## Alternatives

### Simultaneous request to all subscribed resolvers

The Tekton controller could also simultaneously send out new requests to all the subscribed resolvers and then loop over the resolvers until the first one succeeds. However, this creates a non-deterministic behavior at runtime since we don't know the order in which the request was tried. While debugging, this could lead to poor UX.

### Using CRD to store prioritized subscription configuration

Instead of a `configMap`, we could store the configuration in a CRD since it allows us to store more complex structure over key-value pairs. 

```yaml
apiVersion: tekton.dev/v1alpha1
kind: RemoteResolutionSubscription
metadata:
  name: remote-reslution-subscription
  namespace: tekton-pipelines
spec:
  - schemes: # schemes for which the order of resolvers is the same
      - https
      - http
    resolvers: # prioritized order from top to bottom
      - http
      - git
      - my-custom-resolver
  - schemes:
      - git+https
      - git
    resolvers:
      - git
      - my-custom-resolver
  - schemes:
      - oci
    resolvers:
      - bundles
      - my-custom-resolver
  - schemes:
      - "*" # Any other scheme that is not specified in this list.
    resolvers:
      - my-custom-resolver
```
Allows easier grouping over schemes where the order of priority amongst the subscribed resolvers is the same. The CRD can stabilize over `v1alpha1 --> v1beta1 --> v1` as the feature matures.
