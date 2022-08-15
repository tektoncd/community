---
status: implementable
title: 'Ignore Task Failures'
creation-date: '2021-02-05'
last-updated: '2022-09-16'
authors:
- '@pritidesai'
- '@skaegi'
- '@QuanZhang-William'
---

# TEP-0050: Ignore Task Failures

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Ignored Failed Tasks with Retry](#ignored-failed-tasks-with-retry)
  - [Emit Results from Ignored Failed Tasks](#emit-results-from-ignored-failed-tasks)
  - [Tasks with Missing Resource Dependency](#tasks-with-missing-resource-dependency)
- [Alternatives](#alternatives)
  - [A bool flag](#a-bool-flag)
  - [A list of ignorable fail tasks in PipelineSpec](#a-list-of-ignorable-fail-tasks-in-pipelinespec)
- [Future Work](#future-work)
  - [Support parameterization for task.OnError](#support-parameterization-for-taskonerror)
- [References](#references)
<!-- /toc -->

## Summary

Tekton pipelines are defined as a collection of tasks in which each task is executed as a pod on a Kubernetes cluster.
Tasks are scheduled and executed in directed acyclic graph where each task represents a node on the graph. Two nodes
or two tasks are connected by an edge which is defined using either resource dependency (`from` or `task results`) or
ordering dependency (`runAfter`). One single task failure results in a pipeline failure i.e. a task resulting in a
failure blocks executing the rest of the graph. 

```yaml
$ kubectl get pr pipelinerun-with-failing-task-csmjr -o json | jq .status.conditions
[
  {
    "lastTransitionTime": "2021-02-05T18:51:15Z",
    "message": "Tasks Completed: 1 (Failed: 1, Cancelled 0), Skipped: 3",
    "reason": "Failed",
    "status": "False",
    "type": "Succeeded"
  }
]
```

Tekton [catalog](https://github.com/tektoncd/catalog) has a wide range of `tasks` which are designed to be reusable
in many pipelines. As a pipeline execution engine, we encourage the pipeline authors to utilize arbitrary tasks from
the Tekton catalog. But, many common pipelines have the requirement where a task failure must not block executing the
rest of the tasks.

A pipeline author has an option to utilize `finally` section of the pipeline in which all the final tasks are executed
after all the tasks in a graph have completed regardless of success or failure. `finally` has its own advantages and
very helpful in various use cases including notifications, cleanup, etc.

But, the pipeline authors does not have the flexibility to unblock executing the rest of the graph after experiencing a
single task failure.


## Motivation

It should be possible to utilize tasks from the Tekton catalog in a pipeline. A pipeline author has no
control over the task definitions but may desire to ignore a failure and continue executing the rest of the graph.


### Goals

* Design a task failure strategy so that the pipeline author can control the behavior of the underlying tasks 
  and decide whether to continue executing the rest of the graph in the event of failure.

* Be applicable to any pipeline with references to the tasks in a catalog or inlined task specifications.

### Non-Goals

* Not an alternative to combining the tasks in a pipeline which is covered in
  [TEP-0044 Composing Tasks with Tasks](https://github.com/tektoncd/community/pull/316).
* Not optimizing pipeline runtime which is covered in
  [TEP-0046 PipelineRun in a Pod](https://github.com/tektoncd/community/pull/318).
* Eventually users might want to specify both that a task should be permitted to fail, and also control the impact
  on the overall pipeline execution status (e.g. they may sometimes want the pipeline to continue but eventually fail)
  but in this proposal we will not provide that flexibility since it can be added later, and users could still get
  that behavior by having a `finally` task which looks at the status of the task that was allowed to fail, and it
  could decide to fail

## Requirements

* Users should be able to use any task from the catalog without having to alter its specification to allow that task to
  fail without stopping the execution of a pipeline.

* It should be possible to know that a task failed, and the rest of the graph was allowed to continue by observing
  the status of the `PipelineRun`.

* When this feature is used to allow a task to fail, the failure of that task should not cause the overall pipeline
  status to fail (i.e. the task would be considered "successful" for the purposes of determining the status of the
  pipeline)

### Use Cases

* As a pipeline author, I would like to design a pipeline where a task running
  [unit tests](https://github.com/tektoncd/catalog/tree/master/task/golang-test/0.1) might fail,
  but the pipeline can continue running integration tests and deploying an application to a staging cluster, so that the
  application can be shared with other developers for early feedback.

  For example, do not fail the pipeline if `unit tests` fail. Continue deploying to a staging cluster if integration tests
  succeed.

  ```
           |                     |
           v                     v
       unit tests      integration tests
                                |
                                v
                      deploy to staging cluster
  ```

* As a pipeline author, I would like to design a pipeline where a task running
  [linting](https://github.com/tektoncd/catalog/tree/master/task/golangci-lint/0.1) might fail,
  but can continue running tests, so that my pipeline can report failures from the linting and all the tests.

  For example, do not fail the pipeline if `linting` fail, continue reporting the linter analysis.

  ```
           |                     |
           v                     v
       linting               unit tests
           |                     |
           v                     v
   report linter output    integration tests
  ```

  In this example, `linting` and `unit tests` are executed in parallel. This specific use case can be
  supported by `pipeline in pipeline` approach by creating two separate pipelines,
  (1) `linting` -> `report linter output` and (2) `unit tests` -> `integration tests`.
  `pipeline in pipeline` approach would be better fit when you want `linting` to fail the pipeline.
  But, `linting` is a very expensive operation and do not want the pipeline to fail if `linting` fails.

* As a new Tekton user, I want to migrate existing workflows from the other CI/CD systems that allowed a
  similar task unit of failure.

  The following pipeline is represented in Jenkins. We can consider `stages` an equivalent of `tasks` in a `pipeline`.
  In this pipeline, `linting` and `unit test` are defined as `parallel` stages and starts executing at the same time.
  The `catchError` on `linting` ignores lint failure and repairs the overall build status such that the integration
  tests are executed.

  ```
  pipeline {
    agent any
    stages {
        stage('Lint and Unit Test'){
          parallel {
            stage('Lint') {
              options {catchError(message: "lint failed", buildResult: 'SUCCESS')}
              steps {
                sh 'make lint'
              }
            }
            stage('Unit Test') {
              steps {
                sh 'make check'
                junit 'reports/**/*.xml'
              }
            }
          }
        }
        stage('Integration Test') {
            steps {
                sh 'run-tests.sh'
                junit 'reports/**/TEST-*.xml'
            }
        }
    }
  }
  ```

  ![Jenkins Dashboard](images/0050-jenkins-dashboard.png)

  Jenkins Dashboard showing `linting` as `unstable` with `catchError` setting the stage result to `UNSTABLE`:

  ```
  options {catchError(message: "lint failed", stageResult: 'UNSTABLE', buildResult: 'SUCCESS')}
  ```

  ![Jenkins Dashboard](images/0050-jenkins-dashboard-with-unstable-stage.png)

  Jenkins Dashboard showing `linting` as `failed` with `catchError` setting the stage result to `FAILURE`:

  ```
  options {catchError(message: "lint failed", stageResult: 'FAILURE', buildResult: 'SUCCESS')}
  ```

  ![Jenkins Dashboard](images/0050-jenkins-dashboard-with-failure-stage.png)

## Proposal
We propose a new field ```OnError``` to the [PipelineTask](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#adding-tasks-to-the-pipeline) definition.

```go
type PipelineTask struct {
	Name string `json:"name,omitempty"`

	//...

	// OnError defines the termination behavior of a pipeline when the task is failed
	// can be set to [ continueAndFail | stopAndFail ]
	OnError OnErrorType `json:onError, "omitempty"`
}
```

```go
type OnErrorType string

const (
	// StopAndFail indicates to stop the pipeline if the task is failed
	StopAndFail OnErrorType = "stopAndFail"
	// ContinueAndFail indicates to fail the task run but continue executing the rest of the pipeline
	ContinueAndFail    OnErrorType = "continueAndFail"
)
```

Pipeline author can set the ```OnErrorType``` field to configure the task failure strategy. If set to ```StopAndFail```, the pipeline is stopped and failed when the task is failed. If set to ```ContinueAndFail```, the failure of task is ignored and the pipeline continues to execute the rest of the DAG.

```yaml
- name: task1
  onError: continueAndFail
  taskSpec:
    steps:
      - image: alpine
        name: exit-with-1
        script: |
          exit 1

```
This new field ```OnError``` will be implemented as an ```alpha``` feature and can be enabled by setting ```enable-api-fields``` to ```alpha```.

Setting ```OnError``` is optional, the default pipeline behavior is ```StopAndFail```

The task run information is available under the ```pipelineRun.status.childReferences```. Note that the original task run status remains as it is irrelevant of the value of ```OnError``` (i.e. a failed task with ```OnError: continueAndFail``` is still marked as failed). We introduce a new [TaskRunReason](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#taskrunreasonstring-alias) ```FailureIgnored``` indicating the taskrun is failed but the failure is ignored. The detailed failure information can be found in the ```message``` field of the task run.

```go
// TaskRunReasonFailureIgnored is the reason set when the Taskrun has failed and the failure is ignored
TaskRunReasonFailureIgnored TaskRunReason = "FailureIgnored"
```

 The task would be considered "successful" ONLY for the purposes of determining the status of the pipeline run, which is represented in ```pipelineRun.status.conditions``` (if using ```full``` embedded status) or ```pipelineRun.status.childReferences``` (if using ```minimum``` embedded status). Details can be found in [TEP-0100](https://github.com/tektoncd/community/blob/main/teps/0100-embedded-taskruns-and-runs-status-in-pipelineruns.md).


To distinguish pipeline run messages with and without ignored task failures, we explicitly add the ignored task failure count to ```pipelineRun.status.conditions.message``` in the following way if ignored task failure > 0: 

```
"Tasks Completed: A (Failed: B (Ignored: C), Cancelled D), Skipped: E"
```

Example Input:
```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata: 
  name: demo-pipeline-run
spec:
  pipelineSpec:
    tasks:
    - name: task1
      onError: continueAndFail
      taskSpec:
        steps:
          - image: alpine
            name: exit-with-1
            script: |
              exit 1
    - name: task2
      taskSpec:
        steps:
          - image: alpine
            name: exit-with-0
            script: |
              exit 0
```

Example Output:
```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
...
status:
  completionTime: "2022-08-15T17:26:15Z"
  conditions:
    - lastTransitionTime: "2022-08-15T17:26:15Z"
      message: "Tasks Completed: 2 (Failed: 1 (Ignored: 1), Cancelled 0), Skipped: 0"  
      reason: Succeeded
      status: "True"  # The failed task is considered "successful" when determining the state of pipelineRun
      type: Succeeded
  pipelineSpec:
    ...
  taskRuns:
    demo-pipeline-run-task1:
      pipelineTaskName: task1
      status:
        completionTime: "2022-08-15T17:26:13Z"
        conditions:
          - lastTransitionTime: "2022-08-15T17:26:13Z"
            message: ...
            reason: FailureIgnored
            status: "False" # The task is failed when OnError is set to continueAndFail
            type: Succeeded
          ...
    demo-pipeline-run-task2:
      pipelineTaskName: task2
      status:
        completionTime: "2022-08-15T17:26:15Z"
        conditions:
          - lastTransitionTime: "2022-08-15T17:26:15Z"
            message: All Steps have completed executing
            reason: Succeeded
            status: "True"
            type: Succeeded
          ...

```

### Ignored Failed Tasks with Retry
Setting ```Retry``` and ```OnError``` to ```continueAndFail``` at the same time is not allowed in this iteration of the TEP, as there is no point to retry a task that allows to fail. Pipeline validation will be added accordingly. We can support retries with ignored failed task in the future if needed.

### Emit Results from Ignored Failed Tasks
The task results that are initialized before the task fails will be emitted to ```pipelineResults``` and be available to the rest of the DAG if the task is set to ```onError:continueAndFail```.

In the following example, the ```pipelineRun``` has 2 tasks. The first task attempts to create 3 results. ```task1.result1``` and ```task1.result3``` are initialized before ```task1``` fails (```task1.step1``` already terminated before initializing ```task1.result2```). ```task1.result1``` and ```task1.result3``` are emitted to the pipeline result and are available to the resource-dependent ```task2```. ```task2``` (and the overall ```pipelineRun```) are therefore executed successfully.

Input
```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: demo
spec:
  pipelineSpec:
    tasks:
      - name: task1
        onError: continueAndFail
        taskSpec:
          results:
            - name: result1
            - name: result2
            - name: result3
          steps:
            - name: step1
              image: alpine
              onError: continue
              script: |
                echo -n "result val 1" > $(results.result1.path)
                exit 1
                echo -n "result val 2" > $(results.result2.path)
            - name: step2
              image: alpine
              onError: stopAndFail
              script: |
                echo -n "result val 3" > $(results.result3.path)
                exit 1
      - name: task2         
        taskSpec:
          params:
            - name: arg1
          steps:
            - name: step1
              image: alpine
              script: |
                echo "$(params.arg1)"
        params:
          - name: arg1
            value: "$(tasks.task1.results.result1)"
    results:
      - name: pipeline-result1
        value: $(tasks.task1.results.result1)
      - name: pipeline-result2
        value: $(tasks.task1.results.result2)        
      - name: pipeline-result3
        value: $(tasks.task1.results.result3)  
```

Output
```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
...
status:
  completionTime: "2022-09-16T18:59:19Z"
  conditions:
    - lastTransitionTime: "2022-09-16T18:59:19Z"
      message:
        "Tasks Completed: 2 (Failed: 1 (Ignored: 1), Cancelled: 0), Skipped:
        0"
      reason: Succeeded
      status: "True"
      type: Succeeded
  pipelineResults:
    - name: pipeline-result1
      value: result val 1
    - name: pipeline-result3
      value: result val 3
  ...
  taskRuns:
    demo5c4gd-task1:
      pipelineTaskName: task1
      status:
        completionTime: "2022-09-16T18:59:12Z"
        conditions:
          - lastTransitionTime: "2022-09-16T18:59:12Z"
            message: ...
            reason: FailureIgnored
            status: "False"
            type: Succeeded
        taskResults:
          - name: result1
            type: string
            value: result val 1
          - name: result3
            type: string
            value: result val 3
        ...
    demo5c4gd-task2:
      pipelineTaskName: task2
      status:
        completionTime: "2022-09-16T18:59:19Z"
        conditions:
          - lastTransitionTime: "2022-09-16T18:59:19Z"
            message: All Steps have completed executing
            reason: Succeeded
            status: "True"
            type: Succeeded
        ...
```

### Tasks with Missing Resource Dependency
The resource-dependent tasks will be skipped with reason ```Results were missing``` if the expected result is **NOT** emitted from a parent task with ```onError: continueAndFail```. Following the above example, if ```task2``` consumes a result that is **NOT** initialized (```task1.result2```), ```task2``` will be skipped with reason ```Results were missing``` .

Input 
```yaml
# rest of the yaml file is the same as above example
...
- name: task2         
       taskSpec:
         params:
           - name: arg1
         steps:
           - name: step1
             image: alpine
             script: |
               echo "$(params.arg1)"
       params:
         - name: arg1
           value: "$(tasks.task1.results.result2)"
...
```

Output 
```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
...
status:
  conditions:
    - message:
        "Tasks Completed: 1 (Failed: 1 (Ignored: 1), Cancelled 0), Skipped:
        1"
      reason: Completed
      status: "True"
      type: Succeeded
  skippedTasks:
    - name: task2
      reason: Results were missing
  taskRuns:
    demonzrlk-task1:
      pipelineTaskName: task1
      status:
        completionTime: "2022-08-18T15:08:25Z"
        conditions:
          - lastTransitionTime: "2022-08-18T15:08:25Z"
            message: ...
            reason: FailureIgnored
            status: "False"
            type: Succeeded
        ...
    ...
```

This behavior is consistent with [Guarding a Task only](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guarding-a-task-only). When we add support for [default Results](https://github.com/tektoncd/community/blob/main/teps/0048-task-results-without-results.md), then the resource-dependent Tasks may be executed if the default Results from the skipped parent Task are specified. 

## Alternatives
### A bool flag
Use a boolean flag indicating to ignore a task failure or not.

### A list of ignorable fail tasks in PipelineSpec
Add a new field ```IgnoreFailureTasks``` in ```PipelineSpec``` indicating the list of tasks that should not block the execution of the Pipeline when failed

```go
type PipelineSpec struct {
   Description string `json:"description,omitempty"`
   Resources []PipelineDeclaredResource `json:"resources,omitempty"`
   Tasks []PipelineTask `json:"tasks,omitempty"`
   Params []ParamSpec `json:"params,omitempty"`
   Workspaces []PipelineWorkspaceDeclaration `json:"workspaces,omitempty"`
   Results []PipelineResult `json:"results,omitempty"`
   Finally []PipelineTask `json:"finally,omitempty"`

   IgnoreFailureTasks []string `json:"ignoreFailureTasks,omitempty"`
}

```

## Future Work
### Support parameterization for task.OnError
The failure strategy proposed in this TEP supports only static constant values (```continueAndFail``` and ```stopAndFail```) for ```onError```. We could further extend the support to let users specify values as task parameters (for example ```onError: $(params.CONTINUE)```)

## References

* [TEP-0040 Ignore Step Errors](https://github.com/tektoncd/community/pull/302)
* [Jenkins Pipeline ](https://www.jenkins.io/doc/book/pipeline/)
* [Parallel Stages with Declarative Pipeline](https://www.jenkins.io/blog/2017/09/25/declarative-1/) - Thank you, Andrew Bayer!
* [Jenkins fail fast](https://stackoverflow.com/questions/40600621/continue-jenkins-pipeline-past-failed-stage)
* [Jenkins ignore failure in pipeline](https://stackoverflow.com/questions/44022775/jenkins-ignore-failure-in-pipeline-build-step)
