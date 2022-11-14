
---
title: Configmap and Secret as Param Value Source
authors:
  - "@rpajay"
 
creation-date: 2022-10-28\
last-updated: 2022-10-28\
status: proposed

---
# TEP-0110: Configmap and Secret as Taskrun or Pipelinerun Param's Value Source

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Contract](#contract)
  - [API](#api)
  - [User Stories (optional)](#user-stories-optional)
    - [Versioned <code>Task</code>s and <code>Pipeline</code>s and Pipeline-as-code](#versioned-s-and-s-and-pipeline-as-code)
    - [Shipping catalog resources as OCI images](#shipping-catalog-resources-as-oci-images)
    - [Tooling](#tooling)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
<!-- /toc -->

## Summary

This proposal is to be able to reference `ConfigMap` or `Secret` as value source for `TaskRun` or `PipelineRun` `Params`.
This is to support Kubernetes native options (ConfigMap or Secret) as value source along with direct value passed to `TaskRun` and `PipelineRun`.

## Motivation

`PipelineRun` and `TaskRun` Params support passing direct value during its creation. Two supported options to pass values from Secret / ConfigMap are
- `TEP 0029-step-workspaces`  where Secret / ConfigMap is mounted as file inside container.
- Assigning `Env` from `ConfigMap / Secret` reference for each container / step on creation of pipeline.

To understand the problem let's take an example. 
[jib-maven](https://github.com/tektoncd/catalog/blob/main/task/jib-maven/0.4/jib-maven.yaml)

```yaml
steps:
- name: build-and-push
  image: $(params.MAVEN_IMAGE)
  # Make sh evaluate $HOME.
  script: |
   #!/bin/bash
   [[ -f /tekton-custom-certs/$(params.CACERTFILE) ]] && \
   keytool -import -keystore $JAVA_HOME/lib/security/cacerts -storepass "changeit" -file /tekton-custom-certs/$(params.CACERTFILE) -noprompt
   mvn -B \
   -Duser.home=$HOME \
   -Djib.allowInsecureRegistries=$(params.INSECUREREGISTRY) \
   -Djib.to.image=$(params.IMAGE) \
   compile \
   com.google.cloud.tools:jib-maven-plugin:build
```

In this tekton hub task where 2 params are
- `MAVEN_IMAGE` : Either of the above mentioned solution  doesn't work as the value isn't a param but as an env variable inside the container
- `CACERTFILE` : Secret doesn't work out of the box as to access env variable `$(params.CACERTFILE)` needs to be replaced with `$CACERTFILE`

### Goals

To reference `PipelineRun` or `TaskRun` param value from ConfigMap or Secret. 

It has following advantages
- All values passed either as value in param or referenced from `ConfigMap / Secret` can be consistently accessed in a task or all tasks in a pipeline.
-  Offloads the source of value in a param to its usage in `Pipeline` and `Task`  giving the option to decide the param value on creation of `PipelineRun` or `TaskRun`.
- Minimises changing of `Pipeline` or `Task` based on source of the value when executing in multiple clusters / namespace promoting reusability.

### Non-Goals


## Requirements

- Users should be able to pass `ConfigMap` or `Secret` reference as part of `TaskRun` or `PipelineRun` params along with value.

## Proposal

To achieve the requirement, lets take inspiration from `Kubernetes API Env section of each Container`

```go
// EnvVar represents an environment variable present in a Container.

type  EnvVar  struct {
	Name string  `json:"name" protobuf:"bytes,1,opt,name=name"`
	Value string  `json:"value,omitempty" protobuf:"bytes,2,opt,name=value"`
	ValueFrom *EnvVarSource `json:"valueFrom,omitempty" protobuf:"bytes,3,opt,name=valueFrom"`
}

// EnvVarSource represents a source for the value of an EnvVar.
type  EnvVarSource  struct {
	FieldRef *ObjectFieldSelector `json:"fieldRef,omitempty" protobuf:"bytes,1,opt,name=fieldRef"`
	ResourceFieldRef *ResourceFieldSelector `json:"resourceFieldRef,omitempty" protobuf:"bytes,2,opt,name=resourceFieldRef"`
	ConfigMapKeyRef *ConfigMapKeySelector `json:"configMapKeyRef,omitempty" protobuf:"bytes,3,opt,name=configMapKeyRef"`
	SecretKeyRef *SecretKeySelector `json:"secretKeyRef,omitempty" protobuf:"bytes,4,opt,name=secretKeyRef"`
}

```

From context of `PipelineRun` and `TaskRun` params 
```yaml
- FieldRef : May not fit the context of  `PipelineRun` and `TaskRun` params as its used to reference field of the pod.
- ResourceFieldRef : May not fit the context of  `PipelineRun` and `TaskRun` params as its used to reference resource of the container.
- ConfigMapKeyRef : To reference ConfigMap value
- SecretKeyRef : To reference Secret value
```

### Contract

### API

To support the feature supported outlined above, we also propose a small addition to the API. 
In `ParamSpec` need to `TaskRef` and `PipelineRef` objects will include a `ValueFrom` field.

```go
type  Param  struct {
	Name string  `json:"name"`
	Value ArrayOrString `json:"value"`
	// Additional field ValueFrom to fetch value from ConfigMap or Secret
	ValueFrom *ValueSource `json:"valueFrom,omitempty" protobuf:"bytes,3,opt,name=valueFrom"`
}

// ValueSource represents a source for the value.
type  ValueSource  struct {
	ConfigMapKeyRef *corev1.ConfigMapKeySelector `json:"configMapKeyRef,omitempty" protobuf:"bytes,3,opt,name=configMapKeyRef"`
	SecretKeyRef *corev1.SecretKeySelector `json:"secretKeyRef,omitempty" protobuf:"bytes,4,opt,name=secretKeyRef"`
}
```

For users trying to refer param in  `PipelineRun` or `TaskRun` the options would look like

```yaml
spec:
  params:
    - name: FROM_CONFIGMAP
      valueFrom:
       configMapKeyRef:
        name: pipeline-run-configmap
        key: HELLO_WORLD_KEY
    - name: FROM_SECRET
      valueFrom:
       secretKeyRef:
        name: pipeline-run-secret
        key: HELLO_WORLD_KEY
    - name: AS_VALUE
      value: hello-world 
```


### User Stories (optional)

#### Versioned `Task`s and `Pipeline`s and Pipeline-as-code


#### Tooling


### Risks and Mitigations

## Test Plan

Will need to test all three possible scenarios
 - With param value passed from Secret key
 - With param value passed from Configmap key
 - With param value passed as value  

## Drawbacks

- Controller will need access to `Secrets` and `Configmaps` across all namespaces
- 
## Alternatives

1. TEP 0029-step-workspaces or step env variable

   - pros: not all params values can be passed this way
   - cons: only script section can use its values


## Infrastructure Needed (optional)

None.
