---
status: implemented
title: CEL in WhenExpression
creation-date: '2023-09-21'
last-updated: '2023-10-22'
authors:
- '@jerop'
- '@chitrangpatel'
- '@Yongxuanzhang'
collaborators: []
---

# TEP-0145: CEL in WhenExpression

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Use Cases](#use-cases)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Requirements](#requirements)
  - [Related Work](#related-work)
- [Proposal](#proposal)
  - [Syntax](#syntax)
    - [Use CEL to replace current WhenExpression](#use-cel-to-replace-current-whenexpression)
    - [Use CEL to Support ANY operator](#use-cel-to-support-any-operator)
    - [Use CEL to Support Numeric Comparisons](#use-cel-to-support-numeric-comparisons)
    - [Use CEL to Support Pattern Matching:](#use-cel-to-support-pattern-matching)
  - [Variables Substitution](#variables-substitution)
  - [Validation](#validation)
  - [Example](#example)
- [Design Evaluation](#design-evaluation)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Support More Operators in current WhenExpression](#support-more-operators-in-current-whenexpression)
  - [Use languages other than CEL](#use-languages-other-than-cel)
- [Implementation Plan](#implementation-plan)
  - [Update existing fields in v1 API](#update-existing-fields-in-v1-api)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes to add CEL (Common Expression Language) support in `when` expressions to enable more powerful conditional execution and improve the user experience by offering a more concise way of defining conditionals.


## Motivation

CEL is a non-Turing complete language designed for simplicity, speed, safety, and portability. Tekton has adopted CEL expressions in [Trigger] to match specific events to trigger PipelineRuns, and [CELCustomRun] is implemented to experiment with CEL in Tekton Pipelines without adding CEL directly to the Tekton API.

There are several feature requests in the community which can be met if CEL is supported in Tekton Pipeline:
- [#3591] calls for supporting ANY match behaviour in `WhenExpressions` to execute the task if any `params` is not empty.
- [#3149] suggests using CEL to split the string instead of adding an additional task to do the work.

Take a look at current [WhenExpressions]:

```yaml
when:
  - input: "$(params.path)"
    operator: in
    values: ["README.md"]
```

Current `WhenExpression` requires users to define three fields: `input`, `operator` and `values`. but CEL expressions can achieve the same functionality with a single string. Additionally, the current operator only supports `in` and `notin`, which can be limiting for complex use cases. For example, users will need to figure out [hacky workarounds][#3591] to support any in their case.

For these reasons, `WhenExpressions` would be a good place to start introducing CEL in Tekton Pipelines. This would allow users to write more concise and powerful conditional expressions, and it could be extended to other fields in the future.

### Use Cases

- Cover all the functionalities of current `WhenExpression` and offer a simpler way of having the conditional execution
- Support ANY: e.g. Execute the task with if any params is not empty
- Support numeric operators such as GreaterThan/LessThan, e.g. Execute the task if test coverage is large than a certain number.

### Goals
- Support CEL in `WhenExpression`.

### Non-Goals
- Support CEL in Pipeline API fields other than `WhenExpression`.

### Requirements
- The syntax should be extensible to support other expression languages in the future if needed.
- The pipeline authors cannot inject an entire CEL expression using a variable such as params or results i.e. CEL expression can include params and results which will be resolved but params and results cannot hold an entire valid CEL expression. This requirement is imposed due to a security concern as described in [TEP-0146](https://github.com/tektoncd/community/pull/1077).
- The CEL should support **string** variable substitutions of params, results and context, the results substitution would thus help to build graph dependency of Tasks.

### Related Work

Similar expression evaluations are supported in other CI/CD tools in the industry:
- [Argo][Argo]: `Workflows` support conditional execution using a when property to specify whether to run or skip a `Step` ([example][argo example]).
- [GitHub Actions][GitHub Actions]: supports evaluating expressions in `if` of a `step` to enable conditional execution.
- [Jenkins][Jenkins]: executes the stage when the specified Groovy expression evaluates to true.
- [Spinnaker][Spinnaker]: Uses string expressions, `Stages` only run when expressions evaluate to `True`.


## Proposal

This doc proposes to add a `string` type field `cel` under `WhenExpression`. Like [CelCustomRun][CELCustomRun], we propose to use [cel-go][cel-go] for the expression evaluation. This will allow users to craft any valid CEL expression as defined by the [cel-spec][cel-spec] language definition.


### Syntax

In this section we will show how CEL can support the [use cases](#use-cases).

#### Use CEL to replace current WhenExpression
```yaml
# current WhenWxpressions
when:
  - input: "foo"
    operator: "in"
    values: ["foo", "bar"]
  - input: "duh"
    operator: "notin"
    values: ["foo", "bar"]

# with cel
when:
  - cel: "'foo' in ['foo', 'bar']"
  - cel: "'duh' not in ['foo', 'bar']"
```

**Note:** The `WhenExpressions` contains a list of `WhenExpression`, if all `WhenExpressions` are true it will return true and allow execution. So we’re using AND to evaluate the list of `WhenExpressions`. And this will remain the same for this proposal as we propose to add a subfield `CEL` under `WhenExpression` and each existing `WhenExpression` can be replaced with a CEL expression.

Note that multiple WhenExpressions could be merged into 1 `CEL`, users can use `&&` or `||` operator to connect different expressions so we can overcome the limitations of current `WhenExpressions`:  (1) limited by a single operator (in or notin) for any given expression and (2) the list of expressions are evaluated using and operator.

#### Use CEL to Support ANY operator

This is the workaround from [#3591][#3591],
```yaml
whenAny:
  - input: "$(params.param1)"
    operator: notin
    values: [""]
  - input: "$(params.param2)"
    operator: in
    values: ["8.5", "8.6"]
```

With CEL we can use a more intuitive expression to support it.
```yaml
when:
  cel: "$(params.param1) != '' || $(params.param2) == '8.5' || $(params.param2) == '8.6'"
```

#### Use CEL to Support Numeric Comparisons

This is not possible with current `WhenExpression`. With CEL we can do:

```yaml
  when:
    - cel: "$(tasks.unit-test.results.test-coverage) >= 0.9"
```

[Note:][numeric note] currently there are no automatic arithmetic conversions for the numeric types (int, uint, and double), so the emitted results must be the same numeric type to make sure the evaluation works.

#### Use CEL to Support Pattern Matching:

This is not possible with current `WhenExpression`. With CEL we can do:

```yaml
  when:
    - cel: "$(params.branch).matches('release/.*')"
```

### Variables Substitution

The CEL in When Expressions should support current Tekton’s Params and Results [string substitutions](https://github.com/tektoncd/pipeline/blob/main/docs/variables.md#variables-available-in-a-pipeline) and whole Array and object substitutions are not supported.

We should support Tekton’s variable substitution for 2 reasons:
- This is consistent with all other variable substitution syntax in Tekton, and thus more intuitive for Tekton users;
- This would help to build the dag of Pipeline Tasks, as tasks in a pipeline will check the result reference and build the dependency between Tasks.

We cannot use the current Tekton's variable substitution directly. Because the current variables substitution has the the similar security concern as [TEP-0146](https://github.com/tektoncd/community/pull/1077), for example, users can inject a CEL expression from the `Param` and it could alter the result of the CEL which referenced that `Param` in `WhenExpression`, or execute a CEL which consume more resources than expected.

To address this, we need to:
- Prevent the attack by adding sanity check;
- Explicitly document that passing CEL expression from param is not allowed and won’t be executed.

The solution we proposed is to let CEL handle the variable substitution:
1. Add params, results, context variables to CEL's [environment](https://github.com/google/cel-go#environment-setup), similar like [Tekton Triggers](https://github.com/tektoncd/triggers/blob/main/pkg/interceptors/cel/cel.go#L104C1-L112)
2. Find all variable references in the CEL expression string and remove the '$()' from those references.
3. CEL would do the replacement with 1 and 2 with built-in variable substitution


### Validation

The new fields will be gated by `cel-in-whenexpression`, which will default to false while the feature is in alpha.

The validation webhook will validate
1. The feature flag is enabled
2. **If the flag is enabled, either the current when input+operator+values or cel is used, users cannot use both at the same time for one WhenExpression, but they can use different syntax for different WhenExpressions. Backward compatibility is maintained since users can still use existing syntax**
3. If the CEL expression is valid.

### Example

This is an E2E example:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: guarded-pr-
spec:
  pipelineSpec:
    params:
      - name: path
        type: string
        description: The path of the file to be created
      - name: branches
        type: array
        description: The list of branch names
    workspaces:
      - name: source
        description: |
          This workspace is shared among all the pipeline tasks to read/write common resources
    tasks:
      - name: create-file
        when:
          - cel: "$(params.path) == 'README.md'"
        workspaces:
          - name: source
            workspace: source
        taskSpec:
          workspaces:
            - name: source
              description: The workspace to create the readme file in
          steps:
            - name: write-new-stuff
              image: ubuntu
              script: 'touch $(workspaces.source.path)/README.md'
      - name: check-file
        params:
          - name: path
            value: "$(params.path)"
        workspaces:
          - name: source
            workspace: source
        runAfter:
          - create-file
        taskSpec:
          params:
            - name: path
          workspaces:
            - name: source
              description: The workspace to check for the file
          results:
            - name: exists
              description: indicates whether the file exists or is missing
          steps:
            - name: check-file
              image: alpine
              script: |
                if test -f $(workspaces.source.path)/$(params.path); then
                  printf yes | tee $(results.exists.path)
                else
                  printf no | tee $(results.exists.path)
                fi
      - name: echo-file-exists
        when:
          - cel: "$(tasks.check-file.results.exists) in ['yes']"
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: 'echo file exists'
    finally:
      - name: finally-task-should-be-executed
        when:
          - cel: "$(tasks.echo-file-exists.status) == 'Succeeded'"
          - cel: "$(tasks.status) ==  'Succeeded'"
          - cel: "$(tasks.check-file.results.exists) == 'yes'"
          - cel: "$(params.path) == 'README.md'"
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: 'echo finally done'
  params:
    - name: path
      value: README.md
    - name: branches
      value:
        - main
        - hotfix
  workspaces:
    - name: source
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 16Mi
```

## Design Evaluation

### Simplicity

The proposal helps to reduce the verbosity in Tekton by using 1 string of CEL expression instead of 3 (input+operator+values).

### Flexibility

CEL is a powerful expression language that can be used to perform a wide variety of tasks in CI/CD pipelines. This increases the flexibility of `WhenExpression` in Tekton to handle more complex conditions.

### Conformance

The proposal will introduce an additive change to the current API. It does not impact conformance in the inital release.

### User Experience

This proposal should help to improve the user experience by
- simplifying the syntax for `WhenExpression`
- support more complex conditional execution instead of hacky workaround

### Drawbacks

Users need to be familar with CEL expression syntax to use it properly, this may be a learning curve but they can choose to use current `WhenExpression` syntax for simple cases.


## Alternatives

### Support More Operators in current WhenExpression
Tekton can support more operators from [k8s apimachinery][k8s apimachinery] in `WhenExpression`'s `Operator`.

### Use languages other than CEL
CEL has been adopted in Tekton Triggers and CustomTask. We could add it first and consider other languages support as future work.

## Implementation Plan

### Update existing fields in v1 API

Add `CEL` to `WhenExpression`:
```go
type WhenExpression struct {
	// Input is the string for guard checking which can be a static input or an output from a parent Task
	Input string `json:"input"`

	// Operator that represents an Input's relationship to the values
	Operator selection.Operator `json:"operator"`

	// Values is an array of strings, which is compared against the input, for guard checking
	// It must be non-empty
	// +listType=atomic
	Values []string `json:"values"`

    // CEL is a CEL expression to evaluate, if follows the cel-spec language definition
	CEL string `json:"cel",omitempty`
}
```

### Upgrade and Migration Strategy

This feature will be introduced in alpha with a dedicated feature flag which is disabled by default.

When the feature is promoted to beta, the dedicated feature flag will be enabled by default.

When the feature is promoted to stable, the dedicated feature flag will be removed and the feature will be available by default.

### Implementation Pull Requests

The work is tracked by https://github.com/tektoncd/pipeline/issues/7244:

 - https://github.com/tektoncd/pipeline/pull/7245
 - https://github.com/tektoncd/pipeline/pull/7247
 - https://github.com/tektoncd/pipeline/pull/7251
 - https://github.com/tektoncd/pipeline/pull/7255

## References
- [Tekon Trigger][Trigger]
- [CELCustomRun][CELCustomRun]
- [cel-go][cel-go]

[Trigger]: https://tekton.dev/docs/triggers/cel_expressions/
[CELCustomRun]: https://github.com/tektoncd/experimental/tree/master/cel
[#3591]: https://github.com/tektoncd/pipeline/issues/3591
[#3149]: https://github.com/tektoncd/pipeline/issues/3149
[WhenExpressions]: https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guard-task-execution-using-when-expressions
[Argo]:https://github.com/argoproj/argo/tree/master/examples#conditionals
[argo example]: https://github.com/argoproj/argo/blob/master/examples/conditionals.yaml
[GitHub Actions]: https://docs.github.com/en/actions/learn-github-actions/expressions#example-expression-in-an-if-conditional
[Jenkins]: https://www.jenkins.io/doc/book/pipeline/syntax/#when
[Spinnaker]: https://www.spinnaker.io/guides/user/pipeline/expressions/#dynamically-skip-a-stage
[cel-go]:https://github.com/google/cel-go
[cel-spec]:https://github.com/google/cel-spec/blob/master/doc/langdef.md
[numeric note]: https://github.com/google/cel-spec/blob/master/doc/langdef.md#numeric-values
[k8s apimachinery]:https://pkg.go.dev/k8s.io/apimachinery/pkg/selection#Operator
