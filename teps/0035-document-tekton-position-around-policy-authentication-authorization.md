---
title: document-tekton-position-around-policy-authentication-authorization
authors:
  - "@gabemontero"
creation-date: 2020-07-15
last-updated: 2020-12-09
status: implementable
---

# TEP-0035: Document Tekton position around Policy Authentication Authorization 

<!-- toc -->
- [TEP-0035: Document Tekton position around Policy Authentication Authorization](#tep-0035-document-tekton-position-around-policy-authentication-authorization)
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
  - [Requirements](#requirements)
  - [Proposal](#proposal)
    - [Pod Security Policy (PSP)](#pod-security-policy-psp)
    - [K8S RBAC](#k8s-rbac)
      - [Validate ServiceAccounts with TaskRun / PipelineRun can reference ClusterTasks](#validate-serviceaccounts-with-taskrun--pipelinerun-can-reference-clustertasks)
      - [Use of actual K8s RBAC](#use-of-actual-k8s-rbac)
    - [Authentication for paths in Tekton that bypass K8s authentication](#authentication-for-paths-in-tekton-that-bypass-k8s-authentication)
    - [User Stories (optional)](#user-stories-optional)
    - [Notes/Constraints/Caveats (optional)](#notesconstraintscaveats-optional)
    - [Risks and Mitigations](#risks-and-mitigations)
    - [User Experience (optional)](#user-experience-optional)
    - [Performance (optional)](#performance-optional)
  - [Design Details](#design-details)
  - [Test Plan](#test-plan)
  - [Drawbacks](#drawbacks)
  - [Alternatives](#alternatives)
    - [If 'TaskRun' and 'PipelineRun' APIs had the 'requesting user' set on them, then I could do authorizations based on them](#if-taskrun-and-pipelinerun-apis-had-the-requesting-user-set-on-them-then-i-could-do-authorizations-based-on-them)
  - [Infrastructure Needed (optional)](#infrastructure-needed-optional)
  - [Upgrade & Migration Strategy (optional)](#upgrade--migration-strategy-optional)
<!-- /toc -->

## Summary

Consider the following with the Tekton API and the "out of the box" Tekton experience include:

- providing of `PodSecurityPolicy` instances, per the Kubernetes policy/v1beta1 group API, for both the pipelines and triggers
projects
- API Object to API Object referencing, including:

    - a PipelineRun can reference a Pipeline, Task, or ClusterTask
    - a TaskRun can reference a Task or ClusterTask
    - Today, these references just work for all PipelineRun and TaskRun instances because the controller(s) have permissions, 
      via the default Role/RoleBinding and ClusterRole/ClusterRoleBinding definitions in the config/ folder, to read all 
      these different objects.


- the ability to associate authentication identities that are distinct from the various Tekton controllers/reconcilers
and then perform authorizations with t:

    - both PipelineRun and TaskRun have optional ServiceAccount references that ultimately map to the ServiceAccount
set on the resulting Pod object
    - if the optional ServiceAccount is not set, then the "default" ServiceAccount is used
    - then consider possible access control around namespace scoped or cluster scoped assets as *Run's are executed 
    
- the ability to inject data into the Tekton controllers/reconcilers outside of the classic, authenticated, 
K8s client to server API flow or Pod Security Policy validation:

    - A part of triggers is pulling in events over an unauthenticated K8s service
    - see [this issue](https://github.com/tektoncd/triggers/issues/610) as an example of how upstream users have noticed this

As new users come to the various [https://github.com/tektoncd](https://github.com/tektoncd) repositories to investigate and hopefully adopt the 
various projects, they may value some of these potential concerns.

Documenting the strategy and approach for assisting users in addressing such concerns is what follows in this TEP.

**NOTE:** This [doc on the Tekton project's shared drive](https://docs.google.com/document/d/1fOTZM7j9eH5qQHW0zvG82eRBrdnhdw2Z05d-vdlJph8/edit#heading=h.l0ysfwvdrqaw)
provides a large amount of Kubernetes reference information and links around Kubernetes security, poilicy, RBAC, etc. 
referenced or inferred later in this document.  This document will attempt to minimize duplication of all that background.  But if 
you are unfamiliar with a concept referenced here, that document may accelerate your research, so please join tekton-dev
if need be and bring it up.  


## Motivation

As noted at the top of the [Tekton Pipelines README.md](https://github.com/tektoncd/pipeline/blob/master/README.md),
the first of its main, high level, advantages is that Tekton is Cloud Native, implemented as Kubernetes, and thus
inherently has the ability to integrate into key Kubernetes facilities around:

- Scheduling
- Typing
- Decoupling
- Extensibility
- Security, policy, authentication, and authorization

All those are a big advantage over pre-existing CI/CD systems, created before Containers and Kubernetes came en vogue, that have
had to face challenges in trying to integrate their non-Kubernetes implementations of these system elements on
a Kubernetes cluster.  

Maximizing this advantage with respect to "Security, policy, authentication, and authorization", in order to press this advantage Tekton has 
over other CI/CD systems that strive to run on top of Kubernetes, is the motivation for this TEP.

### Goals

The goal of the TEP is to achieve consensus on how we document, and only document, how users can achieve the level
of security, policy, authentication, and authorization they desire related to Tekton.

That documentation can be:

- Explicit markdown documentation files in the repositories themselves
- Parallel / polished versions of the such information in any Tekton related documentation beyond code repository 
markdown files
- References to third party implementations and associated libraries and catalogs of policy definitions that can solve 
various concerns around security, policy, authentication, and authorization with respect to Tekton:
  
  - There is some preliminary work already underway with the [OPA project](https://github.com/open-policy-agent/gatekeeper-library)
    directly and with [intermediaries](https://github.com/redhat-cop/rego-policies/tree/master/policy/tekton) working with that project. 
  - And even under the OPA umbrella, there are some styllistic choices are your disposal:
  
    - Even with in Gatekeeper, there are [Rego policies that stand on their own](https://github.com/open-policy-agent/library/blob/master/docker/example.rego)
    - As well as [Rego policies embedded in Kubernets Object YAML](https://github.com/open-policy-agent/gatekeeper-library/blob/master/library/pod-security-policy/proc-mount/template.yaml)
    - And finally, [there are example Kubernetes policies as part of core OPA](https://github.com/open-policy-agent/library)
       
  - Admittedly, there is a reasonable debate around whether we should host third party policy engine examples
    related to Tekton in our github organization.  The rationale for not proposing such an approach:
    
    - It is easiest to be "policy engine agnostic" if you do not host any policy engine examples
    - Community member bandwidth around obtaining sufficient SME level skill for supporting policy examples; in addition
    to not adding policy engine like complexity in the Tekton code base, let's minimize the amount of time spent
    potentially debugging third party policy engine issues in the time community members have budgeted to work on
    Tekton 
    - Maximizing engagement with the various policy engine SMEs by interacting with them in their communities
    - Lastly, nothing prevents us in the future from pulling external catalog content into https://github.com/tektoncd
    as our ecosystem evolves and that content reaches some set of validation; in some sense, prudence / caution
    steers us to not doing it *initially*

Also note, any documentation in this space should always be considered "evolving" in the sense that the Kubernetes ecosystem
continues to evolve in this space.  As we learn of new upstream Kubernetes or Knative enhancements, or as new scenarios
arise via user questions and issues, the project will need to react and adapt.

Look no further than the [upstream Kubernetes KEP around Pod Security Policy](https://github.com/kubernetes/enhancements/issues/5),
where the ultimate fate of the current PSP, possible follow on's to PSP within K8s, growing third party solution
ecosystem, all point to PSP's still being very much "in progress".  

And as part of being proactive and staying as current as reasonably possibe with the discussion going in that KEP, we'll
investigate options discussed there.  As a result, some of the third party solutions noted there
will be touched upon in the more detailed sections of this TEP.

### Non-Goals

As the community has iterated over the subject matter over the past year, the community has come to the conclusion that we do not want to provide
"baked in" solutions around such items.

So, feature items like [Tekton specific admission webhooks to enforce RBAC](https://github.com/tektoncd/pipeline/pull/2797)
are not a direction the community will be going in.

Similarly, constructing official reference implementations or catalogs around policies to inject into thrid party solutions
will not be a goal of this TEP.  Instead, as noted in the Goals section, we will work with those third parties to provide possible Tekton policies, 
either by Tekton community members submitting policies for approval on those third part sites, or working with their
community members to translate our scenarios into implementation, using their skills as SMEs in their particular 
solution.

It is a philosophical alignment with one of the recently listed approaches in the PSP KEP previously noted above,
namely utilizing the growing ecosystem of third party options. 

## Requirements

Kubernetes administrators need as much guidance as the Tekton contributors community can provide on how to 
satisfy the various security/policy related concerns typical in Kubernetes clusters, with the premise that 
there are sufficient third party solutions we can work with in order to meet those concerns.

## Proposal

We augment documentation, much like what exists [for Authentication](https://github.com/tektoncd/pipeline/blob/master/docs/auth.md)
for the other typical security concerns.  Here is a current sampling of scenarios, where of course this is a moment in time snapshot,
and perhaps not even a complete one at that (we can grow documentation iteratively of course):

### Pod Security Policy (PSP)

Providing some concise background / and or details on why [the current Pod Security Policy](https://github.com/tektoncd/pipeline/blob/master/config/101-podsecuritypolicy.yaml)
has what it has could prove helpful to new users.

Perhaps mine the PRs associated with the history of changes.  Avoid simply repeating k8s documentation for the fields.
But provide useful context.

Then, we can mention we are tracking KEP 5 closely.  Including keeping an eye on the various third part vendors
that are providing admission webhook based alternatives (perhaps list a few).

We already know of, and I'm sure we will learn more, with running on various Kubernetes distributions with PSP, or
the third party solution PSP alternatives, as we gain experience with them, that we can convey in the documentation.

For example, with OpenShift, while it wants non-root UIDs with its [SCC (Security Context Constratints)](https://docs.openshift.com/container-platform/4.6/authentication/managing-security-context-constraints.html), 
which is on by default, OpenShift and SCC also want to be the ones that randomly assign the UID
for the containres in non-privileged Pods, versus the user doing it.  So I have to comment out the `runAsUser` line from those webhook/controller 
deployments when I run upstream Tekton on OpenShift.  Or I have to assign the 'AnyUID' SCC to their ServiceAccount.

A sampling of policy engines documenting actual PSP or PSP like enforcement, that we could reference:

- [OPA](https://github.com/open-policy-agent/) including [OPA Gatekeepr](https://github.com/open-policy-agent/gatekeeper-library/tree/master/library/pod-security-policy)
- [Styra (Costs money / Downstream offering of OPA)](https://www.styra.com/kubernetes-security-guardrails-with-styra-das-and-open-policy-agent)
- [Falco](https://falco.org/docs/psp-support/)
- [K-Rail](https://github.com/cruise-automation/k-rail#supported-policies)
- [Polaris](https://github.com/FairwindsOps/polaris/blob/master/docs/check-documentation/security.md)
- [Kube-Bench](https://github.com/aquasecurity/kube-bench)
- [Kyverno](https://github.com/kyverno/kyverno)

The documentation will strive to be "policy engine agnostic" as much as possible.  Though we will not necessarily 
have performed prototyping or validation with everyone when documentation is updated.  It will be an iterative effort.

### K8S RBAC

Use of [OPA Gatekeeper](https://github.com/open-policy-agent/gatekeeper) in the same cluster hosting Tekton
has been validated as a means of approximating RBAC styled access control with Tekton objects, facilitating 
the user stories noted below.

The policy engine [Kyverno](https://github.com/kyverno/kyverno/) also seems to have enough pattern matching potential
to be used for some RBAC-like scenarios, but currently does not have support for CRDs.  [A feature request](https://github.com/kyverno/kyverno/issues/1218)
has been opened on their repository.

#### Validate ServiceAccounts with TaskRun / PipelineRun can reference ClusterTasks


See [https://github.com/tektoncd/pipeline/issues/2962](https://github.com/tektoncd/pipeline/issues/2962) for the full
details. 

This writer's interpretation of that issue and how it can be solved today with a third party policy engine RBAC solution: 

- a CI/CD system within a namespace has both data developers can use, and data they cannot (say tokens for the production
environment that developers cannot manipulate, but ops can)
- the developers leverage the CI/CD system not by getting access to the CI/CD system namespace and starting runs directly,
but through source code management (SCM) pull requests that leverages Tekton Triggers to initiate Runs
- while ops can get access to the namespace directly, they can also interface via the SCM pull request mechanism 
- policy is needed to enforce that the ops folks via SCM can access the sensitive data within the namespace, but 
devs cannot
- with the EventListenerTrigger/TriggerSpec objects pair having a ServiceAccount reference field, and Tekton Triggers
able to do K8s impersonation using those ServiceAccounts, admission webhooks now have to inputs available to perform
the authorization needed to see if that ServiceAccount can use any Tasks or ClusterTasks that can access the 
sensitive data

The "approximating RBAC" [OPA examples](https://www.openpolicyagent.org/docs/latest/comparison-to-other-systems/#role-based-access-control-rbac)
can enforce such a policy.

There is *NOT* the literal use of the RBAC related objects in Kubernetes like `Roles`, `RoleBindings`, `ClusterRoles`,
`ClusterRoleBindings`, and `SubjectAccessReviews`, but rather storage of the analogous permission bindings in
either the Rego templates themselves, or in more generic Kubernetes objects like `ConfigMaps` the Rego templates access, where the data 
to be used for pattern matching results in admission or denial by the underlying
admission webhook that OPA Gatekeeper employs.

Say for example that certain ServiceAccounts in the namespace can access the sensitive data, and others cannot.  Ops
and devs get triggers associated with different ServiceAccounts accordingly.

The `yaml` for the OPA Gatekeep objects used in the initial POC are listed below for reference.  
NOTE: moving both the list of valid "users" and which Tekton objects to validate against to `ConfigMaps` or some
such is a productization item outside the scope of this TEP.  We are working with some upstream OPA policy 
catalog curators to "productize" the sample below.

But ultimately, the sample below

The OPA `ConstraintTemplate` (which needs to be constructed first):

```yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: tektonclustertaskallowedserviceaccounts
spec:
  crd:
    spec:
      names:
        kind: TektonClusterTaskAllowedServiceAccounts
        listKind: TektonClusterTaskAllowedServiceAccountsList
        plural: tektonclustertaskallowedserviceaccounts
        singular: tektonclustertaskallowedserviceaccounts
      validation:
        # Schema for the `parameters` field
        openAPIV3Schema:
          properties:
            taskRef:
              type: object
              properties:
                name:
                  type: string
                kind:
                  type: string
            allowedServiceAccounts:
              type: array
              items:
                type: object
                properties:
                  serviceAccountName:
                    type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package tektonclustertaskallowedserviceaccounts

        violation[{"msg": msg, "details": {}}] {
            sa := input_serviceaccountname[_]
            not input_serviceaccounts_allowed(sa)
            msg := sprintf("ServiceAccount %v is not allowed to use ClusterTask %v, TaskRun: %v. Allowed ServiceAccounts: %v", [sa, input.parameters.taskRef, input.review.object.metadata.name, input.parameters.allowedServiceAccounts])
        }
        input_serviceaccounts_allowed(taskrun) {
            input.parameters.allowedServiceAccounts[_].serviceAccountName == taskrun.serviceAccountName
        }
        input_serviceaccountname[s] {
            s := input.review.object.spec
            has_field(s, "serviceAccountName")
        }
        # has_field returns whether an object has a field
        has_field(object, field) = true {
            object[field]
        }
```

The OPA `Constraint` (which needs to corresponding `ConstraintTemplate` present in order to be registered with
OPA Gatekeeper):

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: TektonClusterTaskAllowedServiceAccounts
metadata:
  name: taskrun-serviceaccount-allowed-clustertask
spec:
  match:
    kinds:
      - apiGroups: ["tekton.dev"]
        kinds: ["TaskRun"]
    namespaces:
      - "your-namespace"
  parameters:
    taskRef:
      name: echo-hello-world
      kind: ClusterTask
    allowedServiceAccounts:
      - serviceAccountName: allowed-serviceaccount-name

```

#### Use of actual K8s RBAC

[This issue](https://github.com/tektoncd/pipeline/issues/2917) elaborates in greater detail, but cluster administrators
might expect K8s RBAC (Role, RoleBinding, ClusterRole, ClusterRoleBinding) to hold both when 

- namespaced scope objects access cluster scoped objects, like a TaskRun (and its associated ServiceAccount, including
the `default` ServiceAccount if no ServiceAccount is specified) accessing a ClusterTask
- and when considering the prior section's scenario, where there is sensitive data within a namespace, and not all users 
in a namespace are equals, and say certain Tasks that access that sensitive data are by extension sensitive, administrators
want to control that via traditional RBAC, since the less privileged users still have access to the namespace.
    - so why not just create separate namespaces?  Clusters can become constrained :-)  Ultimately, there are limits with
     ETCD storage for all the different API objects, node CPU and memory costs as Pods run, such deploying many instances
     of Tekton across different namespaces is not viable.

For this scenario, actual use of `SubjectAccessReviews` in the from an OPA Gatekeeper `ConstraintTemplate` has also been 
successfully validated as a means of K8s RBAC based authorization.

So, after creating a `ClusterRole` and `ClusterRoleBinding` that controls whether a given `ServiceAccount` can
`get` a `ClusterTask`, the following `ConstratintTemplate`

````yaml
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: tektonclustertaskallowedserviceaccounts
spec:
  crd:
    spec:
      names:
        kind: TektonClusterTaskAllowedServiceAccounts
        listKind: TektonClusterTaskAllowedServiceAccountsList
        plural: tektonclustertaskallowedserviceaccounts
        singular: tektonclustertaskallowedserviceaccounts
      validation:
        # Schema for the `parameters` field
        openAPIV3Schema:
          properties:
            apiServerURL:
              type: string
            bearerTokenHeader:
              type: string
            sarVerb:
              type: string
            sarGroup:
              type: string
            sarResource:
              type: string
            sarResourceName:
              type: string
            taskRef:
              type: object
              properties:
                name:
                  type: string
                kind:
                  type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package tektonclustertaskallowedserviceaccounts

        #import data.kubernetes.lib

        sar_raw(user) = output {
           body := {
              "apiVersion": "authorization.k8s.io/v1",
              "kind": "SubjectAccessReview",
              "spec": {
                "resourceAttributes": {
                  "apiVersion": "authorization.k8s.io/v1",
                  "kind": "ResourceAttributes",
                  "verb": input.parameters.sarVerb,
                  "group": input.parameters.sarGroup,
                  "name": input.parameters.sarResourceName,
                  "resource": input.parameters.sarResource,
                },
                "user": user,
              },
           }

           req := {
              "method": "post",
              "url": input.parameters.apiServerURL,
              "headers": {"Content-Type": "application/json", "Authorization": input.parameters.bearerTokenHeader},
              # eventually allow for injenction of api server cert
              "tls_insecure_skip_verify": true,
              "body": body,
           }

           http.send(req, output)
        }

        sar_allowed(user) = allowed {
            output := sar_raw(user)
            output.status_code == 201
            allowed = output.body.status.allowed
        }

        violation[{"msg": msg, "details": {}}] {
            sa := input_serviceaccountname[_]
            user := sprintf("system:serviceaccount:%v:%v",[input.review.object.metadata.namespace, sa.serviceAccountName])
            not sar_allowed(user)
            msg := sprintf("ServiceAccount %s user %v is not allowed to use ClusterTask %v, TaskRun: %v"  , [sa.serviceAccountName, user, input.parameters.taskRef, input.review.object.metadata.name])
        }
        input_serviceaccountname[s] {
            s := input.review.object.spec
            has_field(s, "serviceAccountName")
        }
        # has_field returns whether an object has a field
        has_field(object, field) = true {
            object[field]
        }
````

And the following `Constraint`

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: TektonClusterTaskAllowedServiceAccounts
metadata:
  name: taskrun-serviceaccount-allowed-clustertask
spec:
  match:
    kinds:
      - apiGroups: ["tekton.dev"]
        kinds: ["TaskRun"]
    namespaces:
      - "your-namespace"
  parameters:
    # UDPATE with your cluster's URL
    apiServerURL: https://<your api server external host and https port>/apis/authorization.k8s.io/v1/subjectaccessreviews
    # UPDATE with a token from your cluster that can create SARS ...
    bearerTokenHeader: Bearer you-actual-token
    sarVerb: get
    sarGroup: tekton.dev
    sarResource: clustertasks
    sarResourceName: your-clustertask-id
    taskRef:
      name: your-clustertask-id
      kind: ClusterTask

```
   
was able to properly confirm whether the `serviceAccountName` associated with any `TaskRun` from the `your-namespace`
Namespace has sufficient permissions via Kubernetes RBAC to access the `ClusterTask` named `your-clustertask-id`. 

### Authentication for paths in Tekton that bypass K8s authentication

As mentioned in the Summary, [this Tekton Triggers issue](https://github.com/tektoncd/triggers/issues/610) is the 
source for raising this scenario here, and has a bunch of good detailed discussion.

In that issue, an approach using the [Tekton Trigger (Custom) Webhook Interceptor](https://github.com/tektoncd/triggers/blob/main/docs/eventlisteners.md#webhook-interceptors)
could serve as the means to engage with [OPA's support for validating JWT Token (e.g OpenID Connect)](https://github.com/tektoncd/triggers/blob/main/docs/eventlisteners.md#webhook-interceptors)
to validate whether the user's tokens in incoming HTTP payload can access the referenced Trigger and the Task/TaskRuns etc.
the Trigger can initiate.

To date, nobody has had bandwidth the attempt the proposed solution.

### User Stories (optional)

- As a Kubernetes cluster administrator, where the token associated with a `ServiceAccount` has access to production level
environments, I need to be able to ensure that `ServiceAccount` must only be used for a "verified" deployment 
`ClusterTasks`.  In other words, developers must not be able to create a print-token-task and then use the production level
ServiceAccount with `ClusterTasks` that have not been verified for production environments.

- As a Kubernetes cluster administrator where a) provisioning a namespace is not considered a cheap operation, so the 
number of namespaces in a cluster is controlled (imagine by corporate mandate a lot of features installed in each 
namespace whenever a namesapce is created, and those features increase the per namespace etcd footprint), 
b) each development team gets one and only one namesapce , and c) members within a development teams have 
varying levels of permissions around which pipeline related logic they can execute, then I need to allow for control 
of which elements of the pipeline (`Task`, `ClusterTask`, `Pipeline`) a given developer can use, either by actualy
use of K8s RBAC or acceptable approximations of K8s RBAC. 


- As a Kubernetes cluster administrator who is looking at migrating to Tekton from an existing CI/CD system that integrates 
with Kubernetes RBAC, as part of transferring analogous pieces of that system to the Tekton CRDs, I would like to be
able to convert my existing use of Kubernetes RBAC such that the subject users in my `RoleBindings` and `ClusterRoleBindings`
stay the same, but the analogous `Roles` and `ClusterRoles` reference the Tekton resources I have mapped the pipelines of the old 
CI/CD system to.

- As a Kubernetes cluster administrator who looks to leverage Tekton Triggers to initiate Pipeline/Tasks from source
code management (SCM) events like a pull request, I need to be able to employ more stringent forms of authentication available 
for such SCM events than the default token approach most SCMs employ, whether those tokens are not from those more
stringent offerings, which undoubtedly are even used as the K8s cluster's configured authentication implementation.

### Notes/Constraints/Caveats (optional)


### Risks and Mitigations

"Security first" is a mantra often heard amongst Kubernetes cluster administrators.  The fact that some form of 
security enforcement is not on by default very possibly will come under scrutiny.  

For mitigation on that point, we can use Kubernetes experience around `PodSecurityPolicy` as an example to learn from.
In particular, the pattern of a new Kubernetes cluster deployment first standing up as "non-secure", and then 
migrating to more secure usage on a namespace by namespace basis arose early in the ecosystem.  `PodSecurityPolicy` and
its all or nothing approach did not allow for that pattern and hence it was met with resistance.  The `sig-auth` group
in charge of `PodSecurityPolicy` has noted that shortcoming as a failing both at various KubeCon's and in the still
[active KEP](https://github.com/kubernetes/enhancements/issues/5) around `PodSecurityPolicy`.

And certainly use of for example any OPA integrations can be employ from the start whenever a new cluster is created if such an
approache is tenable.

So for now, as we consider this for Tekton, we are focused on facilitating easy migration to more security.

### User Experience (optional)

The documentation we are looking to provide stems from the motivation to assist the user experience in the
security/policy/authentication/authorization relam.

### Performance (optional)

Some points of note with OPA Gatekeeper's implementation and performance:

- it injects itself into the Kubernetes cluster as and admission webhook
- the `match` section of the `spec` in the `Constraint` OPA CRD serves as a filter for which API objects the webhook deals with
- Gatekeeper employs the Kubernetes controller / watch / informer constructs for providing that data requested in 
`parameters` section of the `spec` in the `Constraint` OPA CRD.  What that means is the latest versions of those objects
are obtained in the background, and then when the `ConstraintTemplate` is executed, instead of explicit calls to the
API server to retrieve those objects, the controller cache is leveraged.

Between the `match` filtering and use of a controller cache, and that general admission webhook overhead is generally accepted
in the Kubernetes ecosystem as more than tolerable, the only overhead of note will be OPA's Rego processing engine.



## Design Details

At this time, with documentations and possibly references to policies hosted outside of https://github.com/tektoncd
there is no coding design within Tekton to declare.

We are building upon the fact that prior K8s design choices that allow for plugging in such solutions (i.e. admission
webhooks) is the key design point here.
 
## Test Plan

For now, any testing of third party catalogs of existing policies would at least initially be the providence of 
those third party sources.

That said, if our comfort level for:

- the stability of the third party reference policy
- the fact that it can be obtained by a `wget` HTTP GET just as easily as Tekton's various K8s yaml config files
- and there is a containable means of installing said third party policy engines in our existing e2e's

We can eventually see about validating the scenarios discussed here in Tekton CI.

## Drawbacks

Having to install a separate components like Gatekeeper into a cluster vs. having solutions land with just the 
installing Pipelines may displease some consumers.  We'll have to track community response as things progress and
adjust if needed.  But so far, there has been more acceptance than pushback.

## Alternatives

As briefly alluded to in the non-goal section, some preliminary discussion of the proposal has already occurred via 
demos in the main WG, submission of a design doc per the pre-TEP process, discussion in the API WG, and discussion in 
associated github issues and PRs related to the prototype PR previously noted, for solutions backed into Tekton, which 
has been turned down.

There is one element with respect to possible changes to Tekton code that will be detailed here, most likely a 
"tl;dr" things for most :-), in the following subsection, simply for historical reference.  To date, no explicit
use case or feature request has come in explicitly asking for what is in the next subsection.

### If 'TaskRun' and 'PipelineRun' APIs had the 'requesting user' set on them, then I could do authorizations based on them

Now, on the use of the ServiceAccount associated with any Pod (or object like TaskRun that is ultimately translated 
into a Pod) for authorization, either explicitly supplied or default if non supplied, for the permission check,
a combination of advice from members of the Kubernetes sig-auth who I have talked to directly, as well as guidance
from Kubernets sig-auth at the [2019 North American KubeCon Auth Deep Dive](https://www.youtube.com/watch?v=SFtHRmPuhEw),
using the ServiceAccount for Pod security is better.  And at the end of the day, Tekton is ultimately about 
translating high level objects and abstractions into Pods/Containers.

The other choice is the "requesting user", which in the case of Tekton, at the moment is the various Tekton 
controllers/reconcilers.  They are the entity that creates Objects.  Then consider:

- And Tekton controllers create Pods
- And in creating Pods, the Tekton APIs expose the entire surface of the Pod definition, including all the security
and privileged related settings
- So if the Tekton controllers are given escalated permissions to set any of the fields in a Pod around SecurityContext, 
that means unprivileged users who can create TaskRuns or PipelineRuns, but not privileged Pods, would be able to do 
the same via Tekton

Use of "requesting user" from a generic perspective has been frowned upon by sig-auth.  If you listen to the regrets 
listed on the flawed auth model of the PodSecurityPolicy admission plugin, from timestampls 19:11 to 21:14, you'll hear 

- "Granting permissions to the requesting user is intuitive, but it breaks controllers" ... i.e. the escalated 
permission possibility noted above
- "Dual mode weakens security ... you cannot have a privileged controller create pods on behalf of a user"

But that "intuitive" nature of "requesting user" based policy is still attractive to some in the community.

That said, at the moment this point is moot because the "requesting user" is not stored in the `TaskRun` or `PipelineRun`.
API changes to those objects, as well as a mutating admission webhook in https://github.com/tektoncd/pipelines would 
be needed to provide the "requesting user" in those objects for subsequent evaluation in the same manner the `ServiceAccount` 
references are evaluated. 

At this time, since the providers of the scenarios this TEP highlight desire `ServiceAccount` based authorization policies, 
along with the added work involved with adding "requesting user" to the Tekton APIs, this 
proposal will not venture into "requesting user" territory at this time.  Certainly we should continue to track
scenarios of this ilk as a community, and if the need for "requesting user" based scenarios reaches a sufficient point,
as new TEP aimed at introducing "requesting user" to the core API, and then updating this TEP or construct a follow 
on TEP for vetting use of OPA Gateway with those new fields, is warranted.



## Infrastructure Needed (optional)



## Upgrade & Migration Strategy (optional)


