---
title: 0023-Implicit-mapping
authors:
  - "@Peaorl"
creation-date: 2020-10-01
last-updated: 2020-10-01
status: proposed
---

# TEP-0023: Implicit Parameter and Resource Mapping in the `Pipeline` specification

- [Summary](#summary)
- [Motivation](#motivation)
  - [Goal](#goal)
  - [Non Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes](#notes)
  - [Caveats](#caveats)
    - [Common parameter and resource names](#common-parameter-and-resource-names)
    - [Non-standardized parameter and resource names](#non-standardized-parameter-and-resource-names)
  - [Performance](#performance)
- [Design Details](#design-details)
  - [API Spec](#api-spec)
  - [Design](#design)
    - [Implicit parameter mapping](#implicit-parameter-mapping)
    - [Implicit resource mapping](#implicit-resource-mapping)
  - [Alternatives](#alternatives)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [References](#references)

## Summary

A `Pipeline` specification with many `Task's` that have parameters and resources can quickly become verbose.
Additionally, writing up such a `Pipeline` specification can be tedious for a `Pipeline` author.
In this TEP, implicit parameter and resource mapping is introduced.
This feature allows `Pipeline` authors to write an implicit `Pipeline` specification by omitting parameters and resources that go with a `PipelineTask`.
Instead, Tekton automatically fills in the values for parameters and resources listed in the embedded *taskSpec* or in the `Task` referenced by a *taskRef*, with the values of parameters and resources listed in the Pipeline's `spec.params` and `spec.resources` fields.
Additionally, the latest result from previous `Task's` is automatically used as value for `Task` parameters if the two match in name.

## Motivation

Writing a `Pipeline` specification can be a tedious task.
As the number of `Tasks` that have parameters and resources in a `Pipeline` specification grow, the YAML specification can quickly become verbose.
The `Pipeline` author needs to explicitly specify the values for `Task` parameters and resources as shown for the following *deploy* `Task`.

``` yaml
    - name: deploy
      runAfter: [verify]
      taskRef:
        name: install-tekton-release
      params:
        - name: projectName
          value: $(params.projectName)
        - name: version
          value: $(params.version)
        - name: namespace
          value: $(params.namespace)
      resources:
        inputs:
          - name: release-bucket
            resource: bucket
          - name: k8s-cluster
            resource: test-cluster
          - name: plumbing-library
            resource: plumbing
```
In this TEP we propose to reduce the verbosity of a `Pipeline` YAML and increase the ease of writing a `Pipeline` specification.
This can be achieved by implicit mapping of `Pipeline` specification parameters and resources to `Task` parameters and resources that match in name.
I.e., a `Pipeline` author will be able to omit parameters and resources for a `PipelineTask`.
As a result, the previously listed *deploy* `Task` could be specified as followed in a `Pipeline` specification:

```yaml
    - name: deploy
      runAfter: [verify]
      taskRef:
        name: install-tekton-release
```

### Goal
- Simplify the `Pipeline` specification and therefore the `Pipeline` YAML by:
  - Allowing a `Pipeline` author to omit parameters and resources from `PipelineTasks` that match in name with parameters and resources listed under the `Pipeline.spec.params` and `Pipeline.spec.resources` fields.

* Support finally `Tasks` for parameters and resources (no support for using results from previous `Tasks`)

### Non Goals
- Support implicit mapping for parameters and resources in `Conditions`.

## Requirements

<!--
List the requirements for this TEP.
-->

|#|Requirement                                                                                                                                                                                                                                                                                                                                                                          |
|-|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|1| A `Pipeline` author can omit the explicit specification of parameters and resources for some, or any, `Task` in the `Pipeline.spec.tasks` field if:<br><br> <ul><li> The pipeline is annotated for implicit mapping <i><br>AND<br></i> <li> The omitted parameters and resources can be resolved according to Req. 2 </li></ul>|
|2| Tekton tries to resolve omitted parameters and resources for a pipeline `Task` in the following order: <br><br> <ol><li> If any preceding `Task` has a `Task` result whose name matches an implicit parameter name of the `Task`, resolve the implicit parameter value with the last produced `Task` result that matches. <li> If a parameter or resource name in the `Pipeline.spec` field matches a `Task's` implicit parameter or resource name, resolve the parameter and/or resource values. </li> <li> Tekton produces an error if parameters or resources can't be matched. <br> *\*Explicitly specified params and resources always take precedence.*

[DISCUSSION]: Additionally, omitting input resources that use the output resource of a previous task by using the [`from`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-the-from-parameter) parameter could be supported.
This could mean making the `from` parameter optional.
When omitted, Tekton can match an input resource to the latest matching output resource.

## Proposal

Allow for an implicit specification of a `Pipeline` wherein parameters and resources for a `PipelineTask` can be omitted.

<!-- #### User Story
As a `Pipeline` author, writing a `Pipeline` specification with many `Task`s that have parameters and resources can become tedious.
The `Pipeline` specification can become verbose and contains redundant information.
With implicit parameter and resource mapping I can omit parameters and resources for PipelineTasks.
As a result, writing a `Pipeline` specification becomes less tedious, and the `Pipeline` specification is easier to read due to reduced verbosity.
--->

### Notes

- The VSCode Tekton plugin need not be updated to support implicit `Pipeline` specifications
- Potentially, the Tekton Dashboard needs to be updated to support implicit `Pipeline` specifications

### Caveats
#### Common parameter and resource names
Certain parameter or resource names may be relatively common and therefore carry a different meaning between different `Tasks`.
`Tasks` with the same parameter and resource names that require different input could therefore inadvertently acquire the wrong value.
We consider it the `Pipeline` author's responsibility to guard against these errors. 

#### Non-standardized parameter and resource names
Since parameter and resource names are not standardized, it may occur that a `Pipeline` parameter or resource should be passed to differently named parameters and resources across `Tasks`.
To combat this, we could propose an alias for `Pipeline` parameters and resources in order to match parameters and resources across multiple `Tasks`.

### Performance

- Tekton's validating/mutating webhook will become somewhat slower with implicit mapping because it will perform `Pipeline` specification transformations.
Nevertheless, the slowdown is expected to be negligible.  

## Design Details

### API Spec

The `Pipeline` specification is extended with a new boolean variable called `implicitMapping` in order to enable or disable implicit mapping.
If this variable is omitted, Tekton requires explicit specification of parameters and resources.

The table below compares the same `Pipeline` specification written explicitly and implicitly:

<table>
<tr>
<th>Explicit Pipeline Specification</th>
<th>Implicit Pipeline Specification</th>
</tr>
<tr>
<td style="vertical-align:top;">

```yaml






apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: verify-deploy-test-tekton-release
spec:

  params:
  - name: git-url
    description: The url for the git repository
  - name: git-revision
    description: The git revision 
    (branch, tag, or sha) that should be built
    default: master
  - name: expected-sha
    type: string
    description: The expected SHA to be received
    for the supplied revision.
  - name: projectName
    description: Name of the Tekton
    project to install 
    default: pipeline
  - name: package
    description: Name of the Tekton package
    default: github.com/tektoncd/pipeline
  - name: version
    description: The vX.Y.Z version
    that we want to install
  - name: namespace
    description: Namespace where the
    Tekton project is installed by the
    release
  - name: resources
    description: space separated
    list of resources to be deleted
  - name: container-registry
    description: Container registry
    where to upload images during tests
  resources:
  - name: bucket
    type: storage
  - name: test-cluster
    type: cluster
  - name: plumbing
    type: git
  - name: tests
    type: git
  - name: results-bucket
    type: storage
  tasks:
    - name: setup
      taskSpec:
        params:
          - name: git-url
            type: string
          - name: git-revision
            type: string
        results:
          - name: received-sha 
        steps:
          - name: clone
            image: alpine
            script: |
            ...
            echo -n "$RESULT_SHA" > $(results.received-sha.path)
      params:
        - name: git-url
          value: $(params.git-url)
        - name: git-revision
          value: $(params.git-revision)
    - name: validate
      runAfter: [setup]
      taskRef:
          validate-revision-sha
      params:
      - name: expected-sha
        value: $(params.expected-sha)
      - name: received-sha
        value: $(tasks.setup.results.received-sha)
    - name: verify
      runAfter: [validate]
      taskSpec:
        resources:
          inputs:
          - name: release-bucket
            type: storage
        params:
        - name: projectName
          type: string
        - name: version
          type: string
        steps:
        - name: verify-tekton-release-github
          image: alpine
          script: |
          ...
      params:
        - name: projectName
          value: $(params.projectName)
        - name: version
          value: $(params.version)
      resources:
        inputs:
          - name: release-bucket
            resource: bucket
    - name: deploy
      runAfter: [verify]
      taskRef:
        name: install-tekton-release
      params:
        - name: projectName
          value: $(params.projectName)
        - name: version
          value: $(params.version)
        - name: namespace
          value: $(params.namespace)
      resources:
        inputs:
          - name: release-bucket
            resource: bucket
          - name: k8s-cluster
            resource: test-cluster
          - name: plumbing-library
            resource: plumbing
    - name: log
      runAfter: [deploy]
      taskRef:
        name: log-test-image-tools
      resources:
        inputs:
          - name: plumbing-library
            resource: plumbing
    - name: e2e-test
      runAfter: [log]
      taskRef:
        name: e2e-tests
      params:
      - name: package
        value: $(params.package)
      - name: container-registry
        value: $(params.container-registry)
      resources:
        inputs:
          - name: plumbing-library
            resource: plumbing
          - name: tests
            resource: tests
          - name: test-cluster
            resource: test-cluster
        outputs:
          - name: results-bucket
            resource: results-bucket
    - name: cleanup
      runAfter: [e2e-test]
      taskRef:
        name: cleanup-tekton-release
      params:
        - name: projectName
          value: $(params.projectName)
        - name: namespace
          value: $(params.namespace)
        - name: resources
          value: $(params.resources)
        - name: version
          value: $(params.version)
      resources:
        inputs:
          - name: plumbing-library
            resource: plumbing
          - name: k8s-cluster
            resource: test-cluster
    - name: test-results
      runAfter: [cleanup]
      taskRef:
        name: test-results
      resources:
        inputs:
          - name: results-bucket
            resource: results-bucket
```
</td>
<td style="vertical-align:top;">

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: verify-deploy-test-tekton-release
spec:
  implicitMapping: true
  params:
  - name: git-url
    description: The url for the git repository
  - name: git-revision
    description: The git revision 
    (branch, tag, or sha) that should be built
    default: master
  - name: expected-sha
    type: string
    description: The expected SHA to be received
    for the supplied revision.
  - name: projectName
    description: Name of the Tekton
    project to install
    default: pipeline
  - name: package
    description: Name of the Tekton package
    default: github.com/tektoncd/pipeline
  - name: version
    description: The vX.Y.Z version
    that we want to install
  - name: namespace
    description: Namespace where the
    Tekton project is installed by the 
    release
  - name: resources
    description: space separated
    list of resources to be deleted
  - name: container-registry
    description: Container registry
    where to upload images during tests
  resources:
  - name: release-bucket
    type: storage
  - name: k8s-cluster
    type: cluster
  - name: plumbing-library
    type: git
  - name: tests
    type: git
  - name: results-bucket
    type: storage
  tasks:
    - name: setup
      taskSpec:
        params:
          - name: git-url
            type: string
          - name: git-revision
            type: string
        results:
          - name: received-sha 
        steps:
          - name: clone
            image: alpine
            script: |
            ...
            echo -n "$RESULT_SHA" > $(results.received-sha.path)





    - name: validate
      runAfter: [setup]
      taskRef:
          validate-revision-sha





    - name: verify
      runafter: [validate]
      taskSpec:
        resources:
          inputs:
          - name: release-bucket
            type: storage
        params:
        - name: projectName
          type: string
        - name: version
          type: string
        steps:
        - name: verify-tekton-release-github
          image: alpine
          script: |
          ...









    - name: deploy
      runAfter: [verify]
      taskRef:
        name: install-tekton-release















    - name: log
      runAfter: [deploy]
      taskRef:
        name: log-test-image-tools




    - name: e2e-test
      runAfter: [log]
      taskRef:
        name: e2e-tests
















    - name: cleanup
      runAfter: [e2e-test]
      taskRef:
        name: cleanup-tekton-release















    - name: test-results
      runAfter: [cleanup]
      taskRef:
        name: test-results
```

</td>
</tr>
</table>

With implicit specification, the parameters and resources for a `Pipeline` task can be omitted.
For this to work properly, the names of the parameters and resources listed in the embedded *taskSpec* or the `Task` referenced in the *taskRef*, should match with the names of the parameters and resources listed in the Pipeline's `spec.params` and `spec.resources` field. 

### Design

With implicit mapping enabled, Tekton's validating/mutating webhook resolves the parameter and resource fields in a `PipelineTask` struct.
This transforms the implicitly specified `Pipeline` specification into an explicitly specified `Pipeline` specification.
After the transformation, the webhook performs the regular `Pipeline` specification validation checks.
As a result, no modifications to the `PipelineRun` reconciler are required as it can operate on an explicitly specified `Pipeline` specification.

Additionally, any application that depends on the `Pipeline` specification stored in a cluster need not be updated.

#### Implicit parameter mapping

In accordance with requirement 2, the mutating webhook resolves the `PipelineTask.Params` field as follows:

```
INITIALIZATION
hashmap results[result.Name][task.Name]
hashmap specParams[param.Name][param.Value]
hashset explicitTaskParams[param.Name]
hashmap implicitTaskParams[param.Name][param.DefaultValue]
taskResults[]
m = taskResults.size()
n = PipelineTasks[i].Params.size()
k = PipelineTasks.size()
END INITIALIZATION

FOR EVERY param IN spec.params
  specParams[param.Name] = param.Value
END

FOR i = 0; i < k; i++

  IF PipelineTasks[i].taskSpec == nil THEN
    Resolve PipelineTasks[i].taskRef to find implicit task parameters and results
  ENDIF

  Store implicit task parameters with default values and results in implicitTaskParams and taskResults[] variables respectively

  FOR j = 0; j < n; j++
    explicitTaskParams.insert(PipelineTasks[i].Params[j])
  END

  FOR j = 0; j < m; j++
    results[taskResults[j]] = PipelineTasks[i].Name
  END

  FOR taskParam, taskDefaultValue in implicitTaskParams
    IF explicitTaskParams[taskParam]
      continue;
    ENDIF
    taskName = results[taskParams]
    paramValue = specParam[taskParams]
    IF taskName THEN
      PipelineTasks[i].Params = append(PipelineTasks[i].Params, Params{taskName.result})
    ELSEIF paramValue THEN
      PipelineTasks[i].Params = append(PipelineTasks[i].Params, Params{paramValue})
    ELSEIF taskDefaultValue == nil
      return error //Param can not be matched and does not have a task default value
    ENDIF
  END

  explicitTaskParams.erase()

END
```

#### Implicit resource mapping

In accordance with requirement 2, the mutating webhook resolves the `PipelineTask.Resources` field as follows:

```
INITIALIZATION
hashmap specResources[resource.Name][resource.Value]
hashset explicitTaskResources[resource.Name]
implicitTaskResources[]
k = PipelineTasks.size()
m = PipelineTasks[i].Resources.size()
n = implicitTaskResources.size()
END INITIALIZATION

FOR EVERY resource IN spec.resources
  specResources[resource.Name]= resource.Value
END

FOR i = 0; i < k; i++

  IF PipelineTasks[i].taskSpec == nil THEN
    Resolve PipelineTasks[i].taskRef
  ENDIF

  Store implicit task resources in implicitTaskResources[] 

  FOR j = 0; j < n; j++
    explicitTaskResources.insert(PipelineTask[i].Resources[j])
  END

  FOR j = 0; j < n; i++;
    IF explicitTaskResources[PipelineTask[i].Resources[j]]
      continue
    ENDIF
    resourceValue = specResources[implicitTaskResources[j]]
    IF resourceValue THEN
      PipelineTasks[i].Resources = append(PipelineTasks[i].Resources, Resource{resourceValue})
    ELSE
      return error
    ENDIF
  ENDIF
  END

  explicitResourceParams.erase()

END
```

### Alternatives
- If a *taskRef* is used, the empty *taskSpec* field could be populated with the fetched *taskRef*.
Instead of iterating over an implicit parameter or resource hashmap/array, Tekton can iterate over the parameters and resources in the *taskSpec*.
Additionally, since the webhook has updated the *taskSpec* field, the reconciler would not need to fetch the *taskRef* on every reconcile loop. 
This could be considered an attractive option that would require a separate PR.
Partially because this can happen without implicit mapping as well.
- The mutating webhook could validate an implicit `Pipeline` specification without altering the `Pipeline` spec.
This would still require resolving parameters and resources which would additionally need to be performed by the `PipelineRun` reconciler again.
Considering the amount of duplicate work performed by Tekton this is not considered an attractive option.


## Test Plan

- Unit tests for checking that the webhook correctly transforms an implicit `Pipeline` specification into an explicit `Pipeline` specification

## Drawbacks

- Implicit `Pipeline` specifications could be more error prone

## References

1. [Passing parameters and resource `Pipeline` -> `Task`](https://github.com/tektoncd/pipeline/issues/1484)
1. [Add support for implicit param mapping](https://github.com/tektoncd/pipeline/issues/3050)
1. [Non-standardized parameter and resource names](https://github.com/tektoncd/pipeline/issues/1484)
1. [Common parameter and resource names](https://github.com/tektoncd/pipeline/issues/1484#issuecomment-546697625)
