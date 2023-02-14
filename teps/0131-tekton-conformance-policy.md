---
status: proposed
title: Tekton Conformance Policy
creation-date: '2023-02-14'
last-updated: '2023-02-14'
authors:
- '@xinruzhang@'
collaborators: ['@dibyom@', '@vdemeester@']
---

# TEP-0131: Tekton Conformance Policy

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Glossary](#glossary)
- [Proposal](#proposal)
  - [Conformant Services](#conformant-services)
  - [Conformance API Specification](#conformance-api-specification)
  - [Conformance Policy Versioning](#conformance-policy-versioning)
  - [Policy Update Procedure](#policy-update-procedure)
  - [Conformance Test Suites](#conformance-test-suites)
  - [Q&amp;A](#qa)
    - [1. Do field requirements mean the same for Tekton users and vendors?](#1-do-field-requirements-mean-the-same-for-tekton-users-and-vendors)
    - [2 Tekton Conformance Policy (this doc) v.s. <a href="https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md">Tekton API Compatibility Policy</a>.](#2-tekton-conformance-policy-this-doc-vs-tekton-api-compatibility-policy)
    - [3. Do we only include GA primitives in the conformance policy?](#3-do-we-only-include-ga-primitives-in-the-conformance-policy)
    - [4. Should we define the Conformance Policy per Tekton Services?](#4-should-we-define-the-conformance-policy-per-tekton-services)
  - [Open Questions](#open-questions)
    - [1. How long do we want the policy update notice to be ahead of?](#1-how-long-do-we-want-the-policy-update-notice-to-be-ahead-of)
    - [2. Do we consider the previous Conformance version valid after the new version is released?](#2-do-we-consider-the-previous-conformance-version-valid-after-the-new-version-is-released)
    - [3. What to do with field deprecation?](#3-what-to-do-with-field-deprecation)
- [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes **Tekton Conformance Policy** which lays out the detailed
requirements that Tekton vendors need to satisfy to claim Tekton [`<Primitive Type>`](#glossary)
Conformance on a Service that the vendor provides. It guarantees portability
of Tekton Conformant Primitives in the Tekton ecosystem and interoperability
of Tekton Conformant Primitives across Tekton vendors. It defines:
* **Conformance Primitive Types**: vendors can claim Conformance of a ***Tekton Primitive Type*** on the services they provide.
* **Conformance Requirements**: requirements of claiming the conformance:
  * Tekton APIs to be implemented.
  * Syntactical and semantical requirements of each API field.
* **Conformance Policy Versioning**: use versioning to keep track of updates of the policy.
* **Conformance Policy Update Procedure**: standard procedure to update the policy.

## Motivation

Starting from Tekton release v0.43.0, Tekton has released **V1 CRDs** including `Task`, `TaskRun`, `Pipeline`, `PipelineRun`. As our APIs reach stable state, we want to explore how to build a better Tekton ecosystem that both **Tekton users** and **Tekton vendors** can benefit from.

![Benefits of Tekton Conformance Policy](/teps/images/0131-benefits-of-tekton-conformance-policy.png)

The left side is the world we are in today, for **Tekton users** who want to use Tekton, they have to:
- manage their own kubernetes cluster
- install Tekton Pipelines on the cluster
- write YAMLs to define their CI/CD pipelines

The right side is the world we want to live after we have the conformance policy:
- **Vendors** provide Conformant Tekton Services
- **Users** write YAMLs to define their CI/CD pipelines


For **Tekton users** who use Tekton conformant primitives to define CI/CD pipelines, the benefits are obvious:
- **Convenience**: users can use Tekton conformant services as an alternative to managing their own.
- **Interoperability**: users are able to move conformant primitives between vendors, thereby avoiding vendor lock-in.


For **Tekton vendors** who provide a service that conforms to this Policy, they can:
* **Leverage community effort**:  leverage ecosystem-driven tasks and pipelines, docs, community support via slack channels.
* **Take advantage of the community's success**: Tekton users can bring their conformant primitives (`v1.PipelineRun`, `v1.TaskRun`, `v1.Pipeline`, `v1.Task` in the current policy version) to the vendor's platform.
* **Have portability guarantees** for their users.

### Goals

* Defines a **detailed conformance policy** that vendors can claim conformance to on the service they provide.
* Defines a **versioning story** on the Conformance Policy to enable us make updates on the policy.
* Defines a **policy update procedure**.
* Defines a **way to enforce the policy**.

### Non-Goals

* **HTTP API Conformance**: built upon the current conformance policy, may require vendors to support certain HTTP verbs, expose HTTP API Endpoints that conform to a specific format, support a certain format of request body and response body, support certain response codes etc.


## Glossary

**Tekton Primitives**: are a set of basic data types in Tekton, providing common abstractions for describing and executing container-based, run-to-completion workflows, typically in service of CI/CD scenarios. There are three **Primitive Types**:
* **Pipelines Primitives**: defines workloads execution pipeline
  * Task, TaskRun, Pipeline, PipelineRun, CustomRun.
* **Triggers Primitives**: defines events listening and handling
  * Triggers, TriggerBindings.
* **Results Primitives**: defines execution history of workloads defined by Pipeline Primitives.
  * Results, Records

**Tekton API Specification**: describes ***Tekton Primitives*** in detail. <br/>
**Tekton GA API Specifications**: describes ***GA (V1 for now) Tekton Primitives*** in detail.

**Tekton Pipelines API Specification**: describes ***Tekton Pipelines Primitives*** (`Task`, `TaskRun`, `Pipeline`, `PipelineRun`, `CustomRun` of all version tracks) in detail.<br/>
**Tekton GA Pipelines API Specification**: describes ***Tekton GA Pipelines Primitives*** (`v1.Task`, `v1.TaskRun`, `v1.Pipeline`, `v1.PipelineRun`) in detail.

**Tekton Conformance API Specification**: subset of the ***Tekton GA API Specification*** each vendor MUST implement, fields existing in the Tekton API Specification but not in the Conformance API Specification are `OPTIONAL` for the Conformance Policy by default.<br/>
**Tekton Pipelines Conformance API Specification**: ***core Tekton GA Pipelines API Specification*** each vendor MUST implement, including core fields of `v1.TaskRun` and `v1.PipelineRun`, within where `v1.Task` and `v1.Pipeline` can be incorporated by reference.

**Tekton Users**: use ***Tekton Primitives*** to define CI/CD pipelines.<br/>
**Tekton Vendors**: provide a product built upon Tekton that conforms to the ***Tekton Conformance Policy***.

## Proposal

Vendors can claim **Tekton `<Primitive Type>` Conformance** on the Services they provide. For example, a vendor can claim that its product conforms to "pipelines.v1.0" Conformance Policy, which is the initial version of Tekton Pipelines V1 Conformance Policy. See this section to know details about versioning.

### Conformant Services

Conformant Services are services that can serve **Tekton Conformance API Specifications**. We only define Conformance API Specifications for **Tekton GA Primitives**. For now, only **Tekton Pipelines Primitives** are eligible. *Worth noting that one prerequisite for a primitive to be part of the conformance API is that it reaches GA; however not every primitive that is GA is automatically part of the conformance API.*

Vendors must be able to accept **Tekton `<Primitive Type>` Conformance API Specification**, defined in **YAML or JSON**, submitted **in any way** as long as the schema conforms to the policy[^schema_submission], then schedule workloads, produce outputs (resource conditions and results) as declared. Noted that vendor can define how the `PipelineRuns` and `TaskRuns` are submitted and retrieved, which means, a Conformant Pipeline Service is not guaranteed to be compatible with CLI, dashboard, triggers, chains or any other Tekton components.

For now, only Tekton Pipelines Conformance API Specification is defined (APIs of Triggers and Results are out of scope): a ***Conformant Pipeline Service*** must be able to accept a `v1.PipelineRun`, `v1.TaskRun`, within where `v1.Task` and `v1.Pipeline` can be incorporated by reference. Which means a Conformant Pipeline Service is not required to host the definition of `Task`s and `Pipeline`s. 

Tekton users are able to reuse tasks from Hub/ArtifactHub across ***conformant Tekton Pipelines Services*** or bring ***Conformant Tekton Pipelines Primitives*** from one conformant Tekton Pipelines Service to another.


### Conformance API Specification

WIP, will iterate based on https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md


### Conformance Policy Versioning

Three kinds of changes could happen:
1. **GA API Version**: in the future, we may want to define Tekton V2 API.
1. **The Conformance API**: we promote a field from `OPTIONAL` to `REQUIRED`.
1. **The Policy Itself**: for example,  in the future, we may want to define several conformance levels that vendors can choose to conform to, or we may change the definition of the conformance.

The versioning format: `<Tekton Primitive Type>-<GA API Version>.<Policy / API  Update>`
* **pipelines.v1.0**: the initial version of **Tekton Pipelines V1 Conformance Policy**.
* **pipelines.v2.1**: added a new required field in **Tekton Pipelines V2 Conformance APIs**.
* **results.v2.0**: the initial version of **Tekton Results V2 Conformance Policy**.
* **results.v2.1**: some policy change on **Tekton Results V2 Conformance Policy**.

Worth noting that even if we bump up the policy version, vendors can still claim the conformance on a previous Policy version until we deprecate / remote that API version.

### Policy Update Procedure
* **Open a PR** to propose the update.
* **The PR** must be approved by more than half of [the project OWNERS][project owners] (i.e. 50% + 1) when it involves actual requirements changes (as opposed to typo/grammar fixing).
* **Update Notice** ahead of time.
  * Nice to have: conformance test kit can pop up the update notice when vendors run it.
  * How long do we want the update notice to be ahead of is an open question.

### Future Work

#### Conformance Test Suites

We can follow "[duck test][duck test]", we provide inputs (YAMLs including all required fields) and outputs (status, results etc.) to see if vendors meet the requirements (vendors will need to convert the YAMLs to the format they support). Vendors are required to open a PR containing an instruction doc for reproducing the test result, and the community reviews and approves the PR (Borrowed the idea from [Kubernetes Conformance Test][Kubernetes Conformance Test]). This is a one-time test, but the test result MUST be reproducible while the Conformance claim is valid.

### Q&A
#### 1. Do field requirements mean the same for Tekton users and vendors?

The question is the same as: **Do field requirements mean the same in "_Tekton API Specification_" v.s. "_Tekton Conformance API Specification_"?** Tekton **users** refer to **_Tekton API Specification_** when writing Tekton YAMLs, while Tekton **vendors** refer to **_Tekton Conformance API Specification_** when implementing a _Tekton Conformant Service_. 

The short answer is no.

"REQUIRED" in the conformance policy context is, **vendors** have to support this field, while for **users** when submitting Tekton Primitives, those fields are not necessarily required. **Required fields in Tekton APIs must be all included in the required fields of Tekton Conformance APIs.**

For instance, say `TaskRun.Spec.Param` is required in the **Tekton Conformance APIs**, while it is an optional field in the **Tekton APIs**:
* Tekton **users** are **NOT** required to specify the `Param` field when defining a TaskRun.
* Tekton **vendors MUST** support that field so that Tekton ***users*** are able to use it.

**Required fields in _Tekton APIs_ must be all included in the required fields of _Tekton Conformance APIs_.**

![Required fields in Tekton APIs v.s. Tekton Conformance APIs](/teps/images/0131-conformance-vs-compatibility-policy.png
)

Here is an example if we allow this to happen: If a field is required in Tekton APIs, say `taskSpec.steps`, but is not
required in Conformance APIs, vendors have the freedom to not support that field. Then when users submit a YAML file to
the vendor with `taskSpec.steps` specified, the Vendor service will reject the request because `steps` field is unknown
to it. 

Say **Vendor A** doesn't support `taskSpec.steps` in its Conformant Tekton Pipeline Service – **Service A**. Then users are not able to reuse any Tasks that work for the community Tekton Pipelines Service to the **Service A**, because the required (from Tekton APIs perspective) `taskSpec.steps` is an unknown field to Service A.

#### 2 Tekton Conformance Policy (this doc) v.s. [Tekton API Compatibility Policy][Tekton API Compatibility Policy].

The two policies resemble each other in many aspects: they both define Tekton API fields, breaking changes, and  the practice of making API changes. However, in essence, they are different:

The ***Conformance Policy*** defines ***Tekton Conformance API Specification*** that **vendors** MUST implement.
* It only includes **Tekton GA Primitives**.
* **Tekton Open Source Community** is like a "vendor" that provides the community version of Tekton "product" that contains a reference implementation that conforms to the Conformance Policy.

The **Compatibility Policy** defines rules to follow when making changes on **Tekton APIs**, so that Tekton users can use it to define their CI/CD Pipeline.

On the other hand, **Tekton APIs** drive the **Tekton Conformance APIs**, i.e. fields are added to the **Tekton Conformance APIs** as they graduate from **Tekton APIs**. The lifecycle of a field is:
* Added to Tekton APIs as alpha
* Updated to beta
* Updated to GA (become an OPTIONAL field to Conformance APIs)
* Added to Conformance APIs as REQUIRED

Once the Conformance Policy is defined, the Tekton Compatibility Policy needs to be updated accordingly:

If a field required for conformance is modified, even in a way that is backwards compatible for users of the API, this is
a backwards incompatible change to the conformance policy. For example, adding a new REQUIRED [`ResultType`](https://github.com/tektoncd/pipeline/blob/58712bbdf5a03228e6d304ad6a8ae0457171c810/pkg/apis/pipeline/v1/result_types.go#L62-L66). 
Such a change requires a new conformance policy version and approval of >50% of owners.

#### 3. Do we only include GA primitives in the conformance policy?
Yes, because GA primitives are reliable – making breaking changes for Tekton GA APIs are exceedingly costly. Vendors wouldn't want to invest a lot on APIs that are not stable enough.

#### 4. Should we define the Conformance Policy per Tekton Services?
I.e. Tekton Pipelines Conformance Policy, Tekton Triggers Conformance Policy, Tekton Results Conformance Policy.

Yes because those services can exist independently, a vendor doesn't have to support all services to claim the Conformance.

### Open Questions

#### 1. How long do we want the policy update notice to be ahead of?
Promoting a field to required is considered a breaking change for the Conformance Policy: vendors' conformant services become nonconformant on the new version of the conformance where a new field is promoted to "required". Therefore, we need to notify vendors ahead of time.

9 months, open to suggestions.

#### 2. Do we consider the previous Conformance version valid after the new version is released?
Yes, the previous version should still be valid.

#### 3. What to do with field deprecation?
Policy bump is required at the time when a field that was required in the conformance spec becomes optional for
conformance, because once we deprecate a field, **vendors** have the freedom to not support this field, which is a
breaking change:

Say I have a previously conformant yaml:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
name: "conformant-taskrun"
spec:
  params:
  - name: "greet"
    value: "hello"
```

Then the vendor stops supporting the `params` field. That's said, the `param` field is unknown to vendors, so this
conformant YAML becomes invalid, because the vendor service does not understand what `param` is.

## Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

* [Kubernetes Conformance Test]
* [Duck Test]
* [Project OWNERs]
* [Tekton API Compatibility Policy]


[^schema_submission]: A user can submit a conformant v1.PipelineRun defined in YAML or json format to a Tekton Pipelines Service by either using a command line tool provided by the vendor, or sending the HTTP requests to an API endpoint that the vendor exposes. As long as the service is able to understand the data submitted, then schedule workloads, produce outputs accordingly. Such that the Tekton Pipelines Service can claim the Conformance on the policy pipelines.v1.x

[Project OWNERs]: https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md
[Duck Test]: https://en.wikipedia.org/wiki/Duck_test
[Kubernetes Conformance Test]: https://github.com/cncf/k8s-conformance/blob/master/instructions.md
[Tekton API Compatibility Policy]: https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md
