---
status: proposed
title: Move Image Entrypoint Lookup to the TaskRun Pod
creation-date: '2021-01-11'
last-updated: '2021-03-11'
authors:
- '@yaoxiaoqi'
---

# TEP-0041: Move Image Entrypoint Lookup to the TaskRun Pod

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Add Flags to EntryPoint Binary](#add-flags-to-entrypoint-binary)
  - [Resolve Image in EntryPoint Binary](#resolve-image-in-entrypoint-binary)
  - [Notes/Caveats](#notescaveats)
    - [Entrypoint Cache](#entrypoint-cache)
    - [Error Reporting Delay](#error-reporting-delay)
    - [Inconsistency](#inconsistency)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes to move the image entrypoint lookup to entrypoint binary that
runs in the TaskRun pod.

## Motivation

Currently, Tekton controller pod has access to all service accounts and will do
entry point lookup using `go-containerregistry` for the images that don't have
any command specified. This potentially might cause permission denied error when
user tries to pull an image from a private registry without providing the
`ImagePullSecret`. The authentication method will fall back to perform the OIDC
based auth under this circumstance. It supposed to use the service account that
user provides to run the target TaskRun pod to authenticate. However, the
request comes from Tekton pipelines controller pod. So it uses the wrong service
account `tekton-pipelines-controllers` to perform the OIDC auth which will fail
since users don't even know that they need to give authorization to this
service account.

To solve this confusing problem, this TEP proposes to move the image entrypoint
lookup to TaskRun pod. By doing this, we can use the service account that user
provided for the TaskRun to query the entrypoint of the image, which solves the
auth problem naturally. Moreover, it makes the architecture of Tekton pipeline
more clear.

### Goals

- Move the image entry point lookup logic to the entry point binary on the TaskRun pod

### Non-Goals

- Implement a kubernetes api to query the metadata of an image using kubelet
- Provide an authn.Keychain that can behave as using the service account on the
  target pod to do OICD auth

### Use Cases

TaskRun users encounter permission denied error if they don't specify command in
their container specs and want to rely on OIDC auth in the meantime. The error
happens when TaskRun controller pod tries to pull the private images from
registry and can't find any `ImagePullSecret` for the registry. Once they
specify command for the private images, the private images can be pulled
successfully. This problem can be solved by implementing this TEP.

## Proposal

This TEP proposes to move the image entry point lookup logic to the entry point
binary on the TaskRun pod. The related logic is going to be implemented in the
particular TaskRun pod instead of Tekton controller pod. This makes things more
reasonable and more clear. And the time window between fetching image and pod
scheduling is also smaller than before.

Even though we are already in the image we want to query the entrypoint from
after the architecture changing, the image metadata still needs to be fetched
from `go-containerregistry`. The ideal solution should be fetching image config
from the `kubelet` or underlying runtime straightly. However, the `kubelet` API
that is capable to do this does not exist for now.

### Add Flags to EntryPoint Binary

The entrypoint binary should resolve the image entrypoint or command when the
step container didn't specify a command. In order to find the image, three
paramters could be passed to the binary - `image`, `taskrun_namespace`, and
`taskrun_service_account`. `image` is used to reference the image.
`taskrun_namespace` and `taskrun_service_account` are used to retrieve the
authentication to pull the image.

```go
image = flag.String("image", "", "If specified, pull image and query image entrypoint")
taskrunNamespace = flag.String("taskrun_namespace", "", "If image specified, use this namespace to pull image")
taskrunServiceAccount = flag.String("taskrun_service_account", "", "If image specified, use this service account to pull image")
```

The parameter `entrypoint` must be empty when `image` is specified. The command
to be run will look like this when step command isn't specified:

```script
/tekton/tools/entrypoint -wait_file '/tekton/downward/ready' -wait_file_content\
-post_file '/tekton/tools/0' -termination_path '/tekton/termination'\
-image '<image_path>' -taskrun_namespace 'default' -taskrun_service_account 'default'
```

### Resolve Image in EntryPoint Binary

We will resolve entrypoint in the binary if `image` is specified. The steps list
below:

1. set up `kubeClient`
1. get the keychains using `kubeClient`
1. parse the image reference by the image name and pull the image from remote
   `containerregistry` using the keychains
1. extract the entrypoint from the image config, if entrypoint is not
   specified, use the command instead
1. add the entrypoint to `Entrypoint` struct and run the entrypoint
   binary as usual

### Notes/Caveats

#### Entrypoint Cache

(<em>If you have better ideas about cache, please feel free to complement</em>)

Tekton controller maintains an `entrypointCache` when resolving the entrypoint.
If the image can be found in the cache, there is no need to resolve it from the
registry again. Besides `entrypointCache`, it also maintains `localCache` for
single TaskRun, which means if multiple steps in one single TaskRun use the same
image, it can be fetched from the `localCache` directly. This mechanism can
reduce the startup latency time effectively.

But it could be hard to maintain a image cache after moving the entrypoint
lookup logic, because we resolve the entrypoint in different images. Some
techniques like inter-pod communication or permanently storage must be involved
to do this. Anyway, with or without cache, the cost of time will definitely be
higher than before.

#### Error Reporting Delay

If there was any failure in entry point fetching we would only find out when the
whole TaskRun pod is scheduled and started running as oppose to today that
Tekton Controller will find out about that and return error right away. But it
might be more reasonable because we fetch the image when the pod is scheduled.

#### Inconsistency

We need to check if command is specified before resolve the entrypoint. If we
gather the config from registry, there would be some inconsistency issue between
the image that the kubelet runs and the image that is fetched from
`containerregistry`. If the `imagePullPolicy` isn't set to `Always`, the image
that `kubelet` runs could be weeks old. If the entrypoint can get this
information from `kubelet` and the underlying local container runtime, there's
no opportunity for the inconsistency. But it might not be a good secure
unprivileged way to query the underlying runtime for the image's command. The
corresponding `kubelet` API does not exist either.

## References

[Github issue](https://github.com/tektoncd/pipeline/issues/3626)

[Related User case](https://github.com/tektoncd/pipeline/issues/2316)
