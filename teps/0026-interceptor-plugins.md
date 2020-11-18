---
title: interceptor-plugins
authors:
  - "@dibyom"
creation-date: 2020-10-08
last-updated: 2020-10-08
status: implementable
---
# TEP-0026: Pluggable Interceptors

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Constraints/Caveats](#notesconstraintscaveats)
  - [Performance](#performance)
- [Design Details](#design-details)
  - [HTTP Interface](#http-interface)
    - [Request](#request)
    - [Response](#response)
    - [Example](#example)
  - [Installing Interceptors](#installing-interceptors)
  - [Using Interceptors in Triggers](#using-interceptors-in-triggers)
- [Alternatives](#alternatives)
  - [Implement new HTTP interface without Interceptor CRD](#implement-new-http-interface-without-interceptor-crd)
  - [Use go-plugin for built-in interceptors](#use-go-plugin-for-built-in-interceptors)
  - [Allow operators to disable some built-in interceptors](#allow-operators-to-disable-some-built-in-interceptors)
  - [Implement built-in interceptors using the current webhook interface](#implement-built-in-interceptors-using-the-current-webhook-interface)
    - [Use a versioned Request/Response types to the HTTP API](#use-a-versioned-requestresponse-types-to-the-http-api)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [Work Plan](#work-plan)
- [References](#references)
<!-- /toc -->

## Summary

This is a Triggers proposal to make interceptors more pluggable and
extensible by making the API uniform across built-in and webhook interceptors
(i.e. using HTTP), and by updating the API to support some missing use cases.
This should allow operators to select which interceptors they'd like to
support as part of their installation. In addition, this allows for better
auditability (see TEP-0022), the ability to distinguish between unexpected
errors and filtered events (i.e. processing is successful but we don't need
to continue; see [#336](https://github.com/tektoncd/triggers/issues/336)),
and leaves the room open to easily extend the interceptor interface in the
future.

## Motivation
Interceptors provide an extensible way to do event processing such as
validating event payloads, filtering etc. When an EventListener receives an
event, it will first process any configured interceptors for each trigger
before further processing.

Interceptors have two API surfaces:

1. Configuration: This is the part of the EventListener spec where users
configure the interceptor to use (e.g. the CEL interceptor) along with
addition configuration e.g. a CEL filter expression
([example](https://github.com/tektoncd/triggers/blob/master/examples/github/github-eventlistener-interceptor.yaml#L10))
2. The [runtime
interface](https://github.com/tektoncd/triggers/blob/master/pkg/interceptors/interceptors.go#L30)
that defines what information gets passed on to the interceptor code for
processing and what information the interceptor has to return (e.g a modified
event body, a yes/no on whether to continue processing etc.)

Today, interceptors come in two flavors -
[built-in](https://github.com/tektoncd/triggers/blob/master/docs/eventlisteners.md#interceptors)
and
[webhook](https://github.com/tektoncd/triggers/blob/master/docs/eventlisteners.md#Webhook-Interceptors).
They differ both in the end user interface as well as the runtime interface.
Built in interceptors are part of the Triggers source tree and are executed
as in process function calls. Users can provide additional configuration
params such as filter expressions.To use a built-in interceptor, a user
simply adds it to their EventListener spec. To debug any issues with a
built-in interceptor, a user can check the EventListener logs for error
messages.

On the other hand, Webhook interceptors allow users to write their own code
for processing in their own service. With the exception of adding additional
HTTP headers, there aren't any ways to provide additional parameters. The
interface relies on HTTP status codes to indicate if processing should
continue or not. This makes it hard to distinguish between a interceptor
telling Triggers to stop processing and an interceptor returning an
unexpected error (see
[#336](https://github.com/tektoncd/triggers/issues/336)) To configure a
webhook interceptor, a user has to setup a deployment and service and then
configure the EventListener spec to use that service. They also have to
manually look at the logs for both the Listener and their service to debug
any issues.

Today built in interceptors are more powerful, faster, and easier to use and
debug. But they are not pluggable or extensible. To add a new built in
interceptor, one would have to add it to the Triggers source tree. Webhook
Interceptors are pluggable but aren't as powerful as built-in interceptors.

The goal of this proposal is to reconcile these differences and come with a
unified interceptor interface that supports both the pluggability of webhook
interceptors with the advantages of the current built in interceptors

### Goals

1. Interceptors are pluggable i.e an operator can configure exactly which interceptors their installation of Tekton Triggers should support.

2. Unify the interfaces i.e. users should be able to use and supply configuration for both built in and webhook interceptors in the same way ideally using fields in the Trigger spec.

3. Provide a consistent way to represent that Trigger processing should continue without having to throw an error.


### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

## Requirements

1. Operators can install one or more built-in interceptors.
2. Operators can remove any of the built-in interceptors.
3. Users can configure Interceptors with custom parameters including references to Secrets.
4. Interceptor authors can add new interceptors that have the same features as any built in interceptors, namely access to the entire request and any custom user parameters
5. Any current Interceptor configuration is still usable (until beta) in the new model without requiring any manual changes on part of the end user. As part of beta, we can deprecate the old syntax.


## Proposal

1. Interceptors run as separate processes that communicate with the EventListener over HTTP. The EventListener will send a request to the interceptor with a body that includes incoming event details (headers, body, url), as well as any parameters needed by the interceptor (filter expression, refs to secrets etc). The interceptor response body follows a predefined format that includes information on whether processing should continue or not, as well as any additional fields that the interceptor can add to the event body. This is in line with TEP-0022 which proposes a change to make the incoming event body immutable to improve auditability, and thus interceptors can only add extra fields instead of being able to modify the body or headers.
 
2. Interceptors are configured or installed via an Interceptor CRD that describes an address for the Interceptor as well as  a list of valid parameters that the interceptor accepts.

3. Built-in interceptors are still packaged as part of Triggers but run as separate processes instead of in the controller.

4. Users configure interceptors in their Triggers and EventListeners. There will be a change in the syntax but we will support both the old and new syntax to allow for backwards compatibility:

```yaml
# OLD:
interceptors:
  - cel:
    filter: "header.match("EventType", "push")

# NEW:
interceptors:
  - type: CEL
    params:
    - name: "filter"
      value: header.match("EventType", "push") 
```


5. For backwards compatibility, we will keep supporting the old WebhookInterceptor interface until beta. However, we will recommend users use the new Interceptor interface instead for writing any new Interceptors.

See the [Design Details](#design-details) section below for more.


### Notes/Constraints/Caveats

1. Deployment Footprint and Scaling Concerns

  The proposal suggests one interceptor deployment per cluster. This can cause scaling concerns. With one interceptor serving multiple EventListeners, it is possible that one EL that has many incoming events (or has many triggers with many interceptors) starts making too many requests to the interceptor. This could result in Listeners being bottle-necked on the interceptor processing and then failing to process their triggers (or building up a large queue of triggers/events to process).
  
  The proposal also increases the deployment footprint for Triggers since now the 4 built-in interceptors are deployed as separate pods. In practice, these should be fairly small stateless services that are only created once per cluster. In addition, a HorizontalPodAutoscaler can be configured to scale the resources if needed. Finally, we could also consider bundling all 4 built-in interceptors into one service. 

2. Logging/Debugging

    Fetching logs from the Interceptor pods to debug a failed trigger is going to be cumbersome. So, each interceptor should return a descriptive errorMessage/status/summary in its response that will be logged by the EventListener as well as sent back as a response to the incoming event

3. Backwards Compatibility

    This model [diverges](#http-interface) from the existing WebHookInterceptor model. For backwards compatibility, we can keep supporting the existing [WebhookInterceptor interface](https://github.com/tektoncd/triggers/blob/master/docs/eventlisteners.md#event-interceptor-services) for a few releases or until beta.

4. Secrets and RBAC concerns 

    Today, if an interceptor needs access to a secret (e.g GitHub payload validation), the service account for the EventListener needs to get access to secrets. With the proposed model, this is no longer the case. Instead the GitHub interceptor deployment should use a role that has read access to secrets. This role would have to be a cluster role if it needs access to secrets across multiple namespaces. A security conscious admin might want to use [resourceNames](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#referring-to-resources) to lock down the list of secrets the deployment has access to.


### Performance

With this proposal, the number of HTTP roundtrips scales linearly with the number of interceptors. The path based Trigger approach laid out in [TEP-009](./0009-trigger-crd.md) should help reduce the number of calls since the EventListener will only process a single or a subset of all Triggers instead of every Trigger associated with an EventListener. In addition, Interceptors can be horizontally scaled so that they can handle more requests. Further, there are some low hanging fruits with respect to performance (tektoncd/triggers#797 and tektoncd/triggers#594) that we can tackle to improve performance of the EventListener. Finally, there has been a alternative proposal to chain multiple interceptors into a single "meta interceptor" to reduce HTTP calls (https://github.com/tektoncd/community/pull/229#discussion_r504698565).


## Design Details

This section describes the two major portions of the proposal -- the changes to
the Interceptor interface to make it more typed, and the new CRD to
install/create interceptors.

### HTTP Interface

This diverges from the current HTTP interface that simply forwards the given request and uses HTTP response codes. Instead the proposed way uses typed response bodies for both requests and response (similar to the AdmissionReviewRequest and Response in AdmissionControllers)


#### Request

EL Sink sends incoming events to interceptors over HTTP using a typed format:

```go
type InterceptorRequest struct {  
	// Body is the incoming HTTP event body
	Body []byte `json:"body,omitempty"`
	// Header are the headers for the incoming HTTP event
	Header map[string][]string `json:"header,omitempty"`

  // Extensions are additional fields that are added by previous 
  // interceptors in the chain. See TEP-0222 for details.
  Extensions ma[string]interface{} `json:"extensions,omitempty"`

	// InterceptorParams are the per interceptor params specified in the Trigger
	InterceptorParams map[string]interface{} `json:"interceptor_params,omitempty"`

	Context *TriggerContext
}

type TriggerContext struct {
	// EventUrl is the URL of the incoming event
	EventUrl string `json:"url,omitempty"`
	// EventID is a unique ID assigned by Triggers to each event
	EventID string `json:"event_id,omitempty"`
	// TriggerID is of the form namespace/$ns/triggers/$name
	TriggerID string `json:"trigger_id,omitempty"`
}
```

#### Response

Interceptors in turn return a message with a fixed type:

```go
type InterceptorResponse struct {
	// Extensions are  additional fields that is added to the interceptor event.
	// See TEP-0022. Naming TBD.
	Extensions map[string]interface{} `json:"extensions,omitempty"`
	// Continue indicates if the EventListener should continue processing the Trigger or not
	Continue bool `json:"continue,omitempty"`
	// Status is an Error status as specifed by https://google.aip.dev/193
	Status grpc.Status `json:"status,omitempty"`
}
```

#### Example
With this, an example JSON payload sent to the CEL Interceptor will look like the following:
```json
{
  "body": {}, // some body
  "header": {
    "eventType": "push",
  }, 
  "interceptor_params": {
    "filter": "header.Match(\"eventType\",\"push\""),
    "overlays": [{"key": "branch_name", "expression": "body.ref.split('/')[2]"}]
  },
  "extensions": {}, // Extra fields added by previous interceptors. See TEP-0022
  "context": {
    "event_id": "random-string",
    "trigger_id": "namespaces/default/triggers/cel-trigger"
  }
}

```
And a sucessful response back will be as follows:

```json
{
  "continue": true,
  "extensions": {
    "branch_name": "master"
  }
}
```

While a failed response will look like:

```json
{
  "continue": false,
  "status": {
    "code": "9", // Failed Precondition. See https://developers.google.com/maps-booking/reference/grpc-api/status_codes
    "message": "filter evaluated to false"
  },
}
```

### Installing Interceptors
Interceptors are installed via the InterceptorConfiguration CRD. At minimum
the spec declares a `clientConfig` field that describes how the EventListener
should send requests to the Interceptor Service.
The interceptor spec can also contain option parameters fields that declares
any parameters that an interceptor requires. Use cases for this include
expressions for CEL interceptor, a reference to shared secret for
GitHub/GitLab interceptors etc.

The InterceptorConfiguration CRD conforms to the
[Callable](https://github.com/knative/eventing/blob/master/docs/spec/interfaces.md#callable)
Interface contract from Knative.

In the future, we can consider explicitly allowing Interceptors to support
one ore more version of the Interceptor API by adding a supportedVersions
field to the `spec` (similar to [AdmissionReviewVersions](https://github.com/kubernetes/api/blob/master/admissionregistration/v1beta1/types.go#L452))

```go
type InterceptorConfigurationSpec struct {
	// ClientConfig defines how to communicate with the interceptor service
	// Required
	ClientConfig InterceptorClientConfig `json:"clientConfig"`

	// Params declare interceptor specific fields thatthe user can configure per Trigger.
  Params []InterceptorParamSpec `json:"params"`
  
}

type InterceptorClientConfig struct {
	// `url` gives the location of the webhook, in standard URL form
	// (`scheme://host:port/path`). Exactly one of `url` or `service`
	// must be specified.
	// +optional
	URL *string `json:"url,omitempty"`

	// `service` is a reference to the service for this webhook. Either
	// `service` or `url` must be specified.
	// +optional
	Service *ServiceReference `json:"service,omitempty"`

  // `caBundle` is a PEM encoded CA bundle which will be used to validate the webhook's server certificate.
  // required if the field is the URL scheme is HTTPS
	// +optional
	CABundle []byte `json:"caBundle,omitempty"`
}

type InterceptorParamSpec struct {
	// Name is the name of the param field
	Name string `json:"name"`
	// Optional is true if the field is optional
	Optional bool `json:"optional"`
}

```

As an example, this is how the InterceptorConfiguration for the current CEL interceptor will look like:

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: InterceptorConfiguration
metadata:
  name: CEL
spec:
  clientConfig:
    service:
      name: "cel-interceptor"
      namespace: "tekton-pipelines"
  params:
    - name: filter
      optional: true
    - name: overlay
      optional: true
status:
  address:
    url: "url-to-interceptor-svc"
```

### Using Interceptors in Triggers

Currently, a user can configure an Interceptor in the following way:

```yaml
# OLD:
interceptors:
  - cel:
    filter: "header.match("EventType", "push")
```

This propoal changes that syntax to include an explicit `type` field for the
Interceptor that has to match the name of the Interceptor from the CRD above.
In addition, it switches the input of the interceptor params from a map of
key values to an array of name value pairs:
```yaml
# NEW:
interceptors:
  - type: CEL
    params:
    - name: "filter"
      value: header.match("EventType", "push") 

```
To keep this change backwards compatible, we will support both syntaxes for
the current built in interceptors until beta. In addition, we will use out
mutating webhook to automatically upgrade any newly created Triggers to the
new syntax.


## Alternatives

### Implement new HTTP interface without Interceptor CRD

In this approach, we'll only implement the new typed HTTP based interface for interceptors and rewrite our built-in interceptors using this model. However, we will not introduce the new Interceptor CRD. The Triggers controller/EL needs to know some basic info about the interceptor that is provided by the Interceptor CRD. Let's look at alternatives for those:
*  At minimum, the EventListener needs to know the name of the interceptor (e.g. CEL) and its address (which can be the address of a Kubernetes service: cel.ns.svc.local). As an alternative to fetching this information from the CRD, we could use a Interceptors configMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-interceptors
data:
 # Format is interceptor name: address
 cel: "cel.default.svc.local"
 github: "github.default.svc.local".
```

* The interceptor CRD also provides information on what parameters the interceptor accepts (e.g. CEL expects a filter and/or overlay). Without this information, we cannot validate the interceptor confifuration at Trigger creation time (one would have to create the Trigger, and then send a request to the EventListener instead).

* Extensibility: Having a CRD allows us to add new features to Interceptors down the line. For instance, we might want to support a `tlsClientConfig` field that allows the listener to communicate with the interceptor over TLS (similar to admission webhook's [client config](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.19/#webhookclientconfig-v1-admissionregistration-k8s-io)). It also leaves open the possibility in the future of support alternate transports (e.g. GRPC instead of HTTP).

### Use go-plugin for built-in interceptors 

We'd leverage a library like HashiCorp's go-plugin for built-in interceptors while keeping the existing webhhok interface for extensibility. In this model, the interceptor will run as separate processes but within the same pod. They will communicate with the listener over RPC. So, in many ways this is similar to the proposal but the key difference is that everything runs in the same pod. This is a reasonable alternative. But it does lead us to having to maintain two different interceptor models - one for plugin one for webhooks. The main implications are:    
*   We can keep using the same service account model as before.
*   No additional deployments to manage or scale.
*   Interceptor authors will have to understand the go-plugin library to add a new "built-in" interceptor
*   Since the built-in interceptors have to run within EventListener pod, we'd still have to support the existing Webhook interceptor model for easy extensiblity.
*   We'd have to figure out the contract for these go-plugin interceptors (e.g. how will they work with the Interceptor CRD?).
    *   One idea. the Interceptor CRD defines a containerSpec which we mount at a specific location in the EL pod.

### Allow operators to disable some built-in interceptors

We'll package in built-in interceptors as we do now, but an operator can turn some of the interceptors "off" using a flag or a config map. This is similar to Kubernetes where some admission controllers are [compiled in](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/) and can only be [enabled ](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/#how-do-i-turn-on-an-admission-controller)or disabled. Uses can extend by writing and registering their own [dynamic admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/) (similar to webhook interceptors).

### Implement built-in interceptors using the current webhook interface 

In this model, the built-in interceptors will still be implemented as separate services but they will use the existing Webhook Interface. 
* Passing interceptors params (e.g. the CEL filter expression) would be much more verbose. We'd have to invent extra headers to pass this information through. As an example, this is what an CEL interceptor usage would look like:
```yaml
triggers:
- name: "my-cel-trigger"
  interceptors:
    - webhook:
        objectRef:
          kind: Service
          name: cel-interceptor
        headers:
          - name: "filter"
            value: "header.match('X-GitHub-Event', 'pull_request')"        
```

* This will be harder to debug since in the current webhook interface, the interceptor service does not return any extra debugging information. Again, we could try to cram this information into some special headers but that is a very hacky approach (EL will have to know about these special headers and log them).

#### Use a versioned Request/Response types to the HTTP API

To allow changes to the Interceptor HTTP interface, we can version the request and response types by embedding them in a `InterceptorMessage` type which contains an inline `TypeMeta`. This explicit versioning can be useful and is something we should consider in the future as use cases arise. For now, we will not implement this in order to keep the scope narrow.

```go
type InterceptorMessage struct {
    metav1.TypeMeta `json:",inline"`
    // +optional
    Request *InterceptorRequest `json:"request,omitempty"`
    // +optional
    Response *InterceptorResponse `json:"response,omitempty"`
}
```

With this, an example JSON payload sent to the CEL Interceptor will look like the following:
```json
{
  "apiVersion": "triggers.tekton.dev/v1alpha1",
  "kind": "InterceptorMessage",
  "request": {
    "body": {}, // some body
    "header": {
      "eventType": "push",
    }, 
    "interceptor_params": {
      "filter": "header.Match(\"eventType\",\"push\"")
    },
    "context": {
      "event_id": "random-string",
      "trigger_id": "namespaces/default/triggers/cel-trigger"
    }
  }
}
```
And a sucessful response back will be as follows:

```json
{
  "apiVersion": "triggers.tekton.dev/v1alpha1",
  "kind": "InterceptorMessage",
  "response": {
    "continue": true,
  }
}
```
While a failed response will look like:

```json
{
  "apiVersion": "triggers.tekton.dev/v1alpha1",
  "kind": "InterceptorMessage",
  "response": {
    "continue": false,
    "status": {
      "code": "9", // Failed Precondition. See https://developers.google.com/maps-booking/reference/grpc-api/status_codes
      "message": "filter evaluated to false"
    },
  }
}
```


## Upgrade & Migration Strategy

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

* We'll keep supporting the current [webhook interface](https://github.com/tektoncd/triggers/blob/master/docs/eventlisteners.md#event-interceptor-services) until beta.

## Work Plan

  1. Migrate core interceptor to new interface structs - We'll migrate the core interceptors to use the new API. In this step, the core interceptors will still run inside the EventListener but will use go structs from the new API. This will also require implementing [TEP-0022](https://github.com/tektoncd/community/pull/218)

  2. Move the core interceptors to their own deployments - This will involve implementing the core interceptors to their own deployment and using HTTP to communicate. In addition, we will also be adding the InterceptorConfiguration CRD as part of this.

  3. Add TLS support - This will involve adding suport for the `caBundle` field to allow for TLS communication between EventListener and Interceptor.

  4. Implement additional features - extra context for debugging, versioning etc.

## References

*   [Using Admission Controllers](https://kubernetes.io/docs/reference/access-authn-authz/admission-controllers/)
*   [Dynamic Admission Control](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)
*   [Immutable Input Events](https://github.com/tektoncd/community/pull/218)
*   Github Issue: https://github.com/tektoncd/triggers/issues/271
*   [Original Design Doc](https://docs.google.com/document/d/1zIG295nyWonCXhb8XcOC41q4YVP9o2Hgg8uAoL4NdPA/edit#heading=h.8z1iarlx6yyx)

