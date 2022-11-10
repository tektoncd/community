---
status: proposed
title: Add credential filter to entrypoint logger
creation-date: '2022-10-27'
last-updated: '2022-10-27'
authors:
- '@useurmind'
---

# TEP-0125: Add credential filter to entrypoint logger

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Future Work](#futurework)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

Currently tekton pipeline steps are printing out any secrets in plaintext. This 
can be intended output from shell scripts but also accidental output from e.g. 
the `set -x` shell command.

Both is a security issue as logs are often propagated to log aggregators from a 
central daemon. This can leak secrets.

Therefore the tekton entrypoint which is running all pipeline step commands should
filter secrets automatically where possible. 

## Motivation

Automatically avoid leaking secret values/credentials into the output logs of
tekton pipelines.

### Goals

Secrets are filtered correctly from the output log in a way that the developer 
of the pipeline does not need to configure this.

Especially output from the `set -x` command should also be filtered correctly.

### Non-Goals

We only target secret values that tekton can automatically redact. We do not want 
to redact secrets that are dynamically retrieved during the pipeline run and can
not be known at the start of the pipeline.

We also dont want to redact pipeline parameters containing secret values as part 
of this TEP.

### Use Cases

When a pipeline is created by the pipeline developer he does not need to configure
anything. Secrets and credentials used in the pipeline and exposed by logging in the
pipeline step are automacially redacted from the final log output stream of the tekton
entrypoint. Also secrets printed via the `set -x` command are redacted from the final
log output stream.

### Requirements

We do not want to give the entrypoint running in the pipeline step more/any permissions 
on the API server. 
It should not call the API server to get secret values for example.

Operators should be able to enable/disable this behaviour via a feature flag in case any
problems arise from this filtering mechanism.

## Proposal

The tekton controller looks for secret refs in volumes and env and also for CSI volumes 
referencing secrets in the definition of the pipeline pod. It saves the information in 
form of the names of environment variables and paths to files with secrets. The pod can
then read those values and redact them.

This design does not transmit actual secrets and the pod does not need access to the API 
sever to retrieve them. It tells the pipeline pod only the places where it can find secrets
attached to it. And those are the secrets that will be redacted. Because only those can be
used in the corresponding pipeline step.

The credential filter will redact values contained in those secrets from the output log stream
and replace them with `[REDACTED:<secret-name>]`. Secret name is either the name of the 
environment variable or the file path where the secret is stored in the pod.

### Notes and Caveats

Secrets can come from different sources than the one implemented in this filter.

Therefore it is important to be very specific about what is being filtered.


## Design Details

While creating the pods for the pipeline, the controller will try to detect all secrets 
attached to the pods. Usually secrets are attached to the pod either by setting environment 
variables or mounting files into it. These detected secret locations are then transmitted 
to the pipeline pod for credential filtering.

### Secret Locations

The secret locations detected by the controller are transmitted to the entrypoint as 
a file with the following json format:

```json
{
  "environmentVariables": ["ENV1", "ENV2"],
  "files": ["/path/to/secre1", "/path/to/secret2"]
}
```
The file is stored in `/tekton/downward/secret-locations.json` and provided via a downward volume 
from an annotation `tekton.dev/secret-locations-<containerName>` added to the pod.

The entrypoint can then read the environment variables and file contents and redact them
from the output log stream.

### Secrets stored in Environment Variables

The controller detects secrets stored as environment variables from the following pod syntax:

```yaml
env:
- name: MY_SECRET_VALUE_IN_ENV
  valueFrom:
    secretKeyRef:
      name: my-k8s-secret
      key: secret_value_key
```

The secret key reference is the trigger to detect an environment variable that contains a secret
and that needs to be redacted.

### Secrets mounted as Files 

Secrets can also be mounted into pods via files in different ways. The following pod
syntax should be supported in the secret detection logic.

```yaml
volumes:
- name: secret-volume
  secret:
    secretName: my-k8s-secret
```

```yaml
volumes:
- name: secret-volume-csi
  csi:
    driver: secrets-store.csi.k8s.io
    readOnly: true
    volumeAttributes:
      secretProviderClass: secret-provider-class
```

Classic secret volumes and csi secret volumes with the driver `secrets-store.csi.k8s.io`
are supported. In both cases the volume directories or items in that volume will be added to
the detected secret locations.


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

We initially planned to store the secret location json in an environment variable but deemed the
necessary size of the json as to large for the environment.

The downward API volume should allow for far more space. An emptyDir volume with an init container 
writing the json to a file there would also be a possibility but the downward API approach seems 
to be reasonable for now.

## Future Work

There are still several ways how credential filtering can be improved in the future.

One important aspect is that secret values could be put in via pipeline run parameters by the user.
These could be filtered to further enhance the credential filtering process.

It would also be possible to filter credentials via pattern matching and static analysis. Ideas for
this could be found in the following references:

  - https://github.com/kubernetes/enhancements/blob/master/keps/sig-security/1933-secret-logging-static-analysis/README.md
  - https://github.com/zricethezav/gitleaks


## Implementation Plan

This TEP is already worked on in https://github.com/tektoncd/pipeline/pull/4837.


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

https://github.com/tektoncd/pipeline/issues/3373
