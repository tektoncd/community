---
status: implemented
title: WhenExpressions in Steps
creation-date: '2024-04-15'
last-updated: '2024-07-25'
authors:
- '@ericzzzzzzz'
---

# TEP-0156: WhenExpressions in Steps

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
   - [Goals](#goals)
   - [Non-Goals](#non-goals)
- [Proposal](#proposal)
   - [When Expressions Evaluation](#when-expressions-evaluation)
   - [Supported Expression Languages](#supported-expression-languages)
- [Test Plan](#test-plan)
- [Alternatives](#alternatives)

## Summary
This TEP proposes the addition of When Expressions to individual Steps within a Task. This will allow for fine-grained control over the execution of steps based on conditions like the status of previous step results. This enhancement will provide greater flexibility and control in defining task logic, enabling more complex and dynamic workflows.
## Motivation
Currently, Tekton Tasks execute steps sequentially without the ability to control their execution based on conditions within the Task itself. This limitation restricts the ability to create dynamic workflows that adapt to different scenarios or respond to the outcomes of previous steps.
By introducing When Expressions to Steps, users will be able to:
 - **Create conditional workflows**: Execute steps only when specific conditions are met, such as the success or failure of a previous step, the value of a result, or the presence of a specific parameter.
 - **Improve error handling**: Implement robust error handling strategies by executing specific steps only when errors occur in previous steps.
 - **Enhance reusability**: Develop more versatile Tasks that can adapt their behavior based on different input parameters or runtime conditions.

## Goals
 - Enable the use of When Expressions to control the execution of individual Steps within a Task.
## Non-Goals
 - Introduce new expression syntax or operators beyond what is already available in When Expressions.

## Proposal
We propose extending the Step definition in Tekton Tasks to include an optional when field, similar to the existing implementation for Tasks and Pipelines. The when field will accept a list of When Expressions that define the conditions for executing the Step.

### When Expressions Evaluation

When expressions are evaluated at the entrypointer level. This allows us to use step results produced from previous steps to determine if a step should be skipped. To indicate a skipped step, the exit code will be 0 (showing a step is complete) and the TerminationReason will be Skipped.

### Variable Substitution 

With the introduction of When Expressions at the Step level, it's important to clarify which fields can be referenced within these expressions for variable substitution.
 - Task-based fields:
   - Task Results: You can access the results of any previously executed Task within the same TaskRun using the syntax $(tasks.<taskName>.results.<resultName>).
 - Workspaces: You can reference the names of workspaces declared in the Task using the syntax $(workspaces.<workspaceName>.bound). This allows you to check if a workspace is bound and make decisions based on its availability.
 - Params: Access input parameters defined in the Task using the familiar syntax $(params.<paramName>). This enables conditional logic based on the values passed into the Task.
 - Step Results: The results of previously executed steps within the same Task are accessible using $(steps.<stepName>.results.<resultName>). This is crucial for creating dynamic workflows where subsequent steps depend on the outcomes of earlier ones.
 - Step Status: Access the reason why a step terminated with $(steps.<stepName>.status.terminationReason). This field can take on values like "Error", "Completed", "Skipped", "TimeOut", or "Cancelled", providing insights into the step's execution and enabling more refined decision-making within When Expressions.

### Impact On Task Results
When a step designed to produce a TaskResult is skipped due to a failing when expression, it should be treated like a task that produces results being skipped in a pipeline.
The Task author is responsible for controlling the flow of the steps, including the production of Task Results, and the when expression acts as a mechanism to control this flow. Subsequent steps relying on an unavailable result  due to step being skipped might encounter errors. The Task author should carefully consider the dependencies between steps and ensure the Task logic can handle scenarios where steps producing results are skipped, potentially adding additional steps or using alternative workflow strategies for defaults.

### Supported Expression Languages

Just like when expressions in Task Level, when expressions in Step Level will also be supporting both Operator-based expressions and CEL(Common Expression Language) expressions. 
**Examples**
 - Operator-based when expressions in steps.
```yaml
  apiVersion: tekton.dev/v1
  kind: TaskRun
  metadata:
    generateName: operator-based-
  spec:
    workspaces:
      - name: custom
        persistentVolumeClaim:
        claimName: my-pvc-2
    taskSpec: 
      steps:
        - name: produce-step
          image: alpine
          results:
             - name: result2
               type: string
          script: |
             echo -n "foo" | tee $(step.results.result2.path)
        - name: run-based-on-step-results
          image: alpine
          script: |
             echo "wooooooo"
          when:
             - input: "$(steps.produce-step.results.result2)"
               operator: in
               values: ["bar"]   
```

- CEL when expressions in steps.

```yaml
  apiVersion: tekton.dev/v1
  kind: TaskRun
  metadata:
     generateName: cel-based-
  spec:
    taskSpec:
      steps:
        - name: skipped-step-cel
          image: alpine
          when:
            - cel: "'monday'=='friday'"
          script: |
            echo -n "should not see me"
```
### Example Usage
Here are some use cases that showcase the power of this feature:

**1. Caching with Conditional Steps:**

Imagine a Task that performs complex calculations. To improve performance, you want to implement caching but only when certain conditions are met:

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: my-complex-task
spec:
  steps:
    - name: check-cache
      image: alpine
      results:
        - name: cacheHit
          type: string
      script: |
        ## some logic to check cache and fetch if cache is available and set cacheHit to true
        echo -n "true" >> $(step.results.cacheHit.path)
    - name: calculate-results
      image: alpine
      when:
        - input: "$(steps.check-cache.results.cacheHit)"
          operator: notin
          values: ["true"]
      script: |
        echo "Performing complex calculations"
```

In this example, if the `CacheHit` is set to "true" in the `check-cache` step the `calculate-results` step will be skipped.

**2. Reporting and Failure Handling:**

You might want to add a reporting step that summarizes the outcome of a previous step, only when that step fails:

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: my-task-handling-error
spec:
  steps:
    - name: main-task
      image: alpine
      script: |
        echo 123
        exit 1
      onError: "continue"
    - name: report-error
      image: alpine
      when:
        - input: "$(steps.main-task.status.terminationReason)"
          operator: in
          values: ["Continued"]
      script: |
        echo "reporting error!"
```

Here, the `report-error` step will only run if the `main-task` step terminates with a "Continued" status.  This allows you to specifically handle failures without executing the reporting logic every time. 
ote that `onError` needs to be set to `continue` to allow subsequent steps to execute.  
**3. Conditional Workflows with Step Actions Based on Step Results:**

Consider a Task that processes data in multiple stages:

```yaml
apiVersion: tekton.dev/v1beta1
kind: StepAction
metadata:
  name: step-action-1
spec:
  image: alpine
  script: |
    echo "I am a Step Action 1!!!"
---
apiVersion: tekton.dev/v1beta1
kind: StepAction
metadata:
  name: step-action-2
spec:
  image: alpine
  script: |
    echo "I am a Step Action 2!!!"
---
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: multi-stage-processing
spec:
  steps:
    - name: stage1
      image: alpine
      script: |
        echo "Stage 1 complete"
      results:
        - name: stage1Result
          type: string
    - name: stage2
      when:
        - input: "$(steps.stage1.results.stage1Result)"
          operator: in
          values: ["success"]
      ref:
        name: step-action-1
    - name: stage3
      when:
        - input: "$(steps.stage1.results.stage1Result)"
          operator: notin
          values: ["success"]
      ref:
        name: step-action-2
```

In this case, the `stage2` and `stage3` steps are conditionally executed based on the `stage1Result`. If `stage1Result` is "success", stage 2 runs, while if it's anything else, `stage3` runs. This lets you build dynamic workflows that adapt to the outcomes of previous stages.


## Test Plan
 - Unit tests for the When Expressions parser and evaluator, specific to Step contexts.
 - Integration tests to validate the behavior of Steps with When Expressions in various scenarios.
 - End-to-end tests covering common use cases and error conditions.

## Alternatives
An alternative approach would be to evaluate When Expressions before creating the pods for the steps. If a When Expression evaluates to false, the corresponding step container would not be created at all.
 - **Pros**:
   - **Resource Efficiency**: This approach can save time and resources by avoiding unnecessary image pulls and container creation for steps that won't be executed.
 - **Cons**:
   - **Limited Context**: When Expressions evaluated at this stage cannot access results from previous steps. This restricts the ability to create conditional workflows based on dynamic runtime data.

## Implementation PRs

https://github.com/tektoncd/pipeline/pull/7746
