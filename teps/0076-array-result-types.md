---
status: implementable
title: Array result types
creation-date: '2021-07-14'
last-updated: '2022-03-18'
authors:
- '@bobcatfish'
---

# TEP-0076: Expanded array support: results and indexing

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats](#notescaveats)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes expanding support for arrays in Tasks and Pipelines by adding:
* Support for indexing into arrays in variable replacement
  (in addition to [replacing entire lists](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#substituting-array-parameters))
* Support for array [results](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#emitting-results) (for both Pipelines and Tasks)

## Motivation

* [TEP-0075](https://github.com/tektoncd/community/pull/479) proposes adding dictionary (object) support in addition
  as params, and results, but today we only support arrays as params and not as results. If we add support for
  dictionary results and params, it would be inconsistent to continue to only support arrays as params and not as
  results as well.
  results (vs params) - but today we only allow string results. It seems confusingly
  inconsistent to imagine adding dictionary results but not array results (even though
  we support array params)
* Without indexing, arrays will only work with arrays. This means you cannot combine arrays with Tasks that
  only take string parameters and this limits the interoperabiltiy between Tasks.
* Future looping support: [use cases](#use-cases) for looping support in pipelines often need an array input;
  being able to produce an array from a Task to feed into a loop would enable some interesting CD use cases

### Goals

* Add two missing pieces of array support:
  * Using arrays as results
  * Indexing into arrays
* Take a step in the direction of allowing Tasks to have even more control
  over their params and results ([see pipelines#1393](https://github.com/tektoncd/pipeline/issues/1393))
* Be consistent in our treatment of arrays in Pipelines and Tasks and other types, e.g.
  dictionaries ([TEP-0075](https://github.com/tektoncd/community/pull/479))

### Non-Goals

* Adding complete [JSONPath](https://tools.ietf.org/id/draft-goessner-dispatch-jsonpath-00.html)
  syntax support
* Adding support for nesting, e.g. array params or results where the items in the array are themselves arrays
  (no reason we can't add that later but trying to keep it simple for now)

### Use Cases

1. **Use cases for array results** In order to support any kind of looping (whether via a custom task and a Run object,
   such as [the existing task-loops custom task](https://github.com/tektoncd/experimental/tree/main/task-loops) or one
   day via support in a Tekton API), it needs to be possible for the looping logic to:
   
   1. Consume arrays as parameters in order to have values to loop over - array params are possible today but what is
      not possible is to **consume an array that is the result of a previous Task**
      (i.e. providing values for an interface such as the task-loop custom task
      [iterateParam](https://github.com/tektoncd/experimental/tree/main/task-loops#specifying-the-iteration-parameter)
      (see the workaround added in [experimental#713](https://github.com/tektoncd/experimental/pull/713) which
      splits a string)
   2. **Produce** arrays as results after the looping has completed - since the looping logic has been doing multiple
      things (by design) it is likely each iteration will have its own result, and today the only way to emit those
      results would be to concatenate them together into a string (choosing some arbitrary separator such as a space or
      comma)
      
   *Concrete example #1: building images in a directory*
   
   In tektoncd/plumbing we have a directory of
   [images](https://github.com/tektoncd/plumbing/tree/main/tekton/images). Each directory contains a Dockerfile -
   in a Pipeline that builds all images in this repo, we would want to:
     1. determine which Dockerfiles need to be built
     2. for each of those Dockerfiles, build the image, using a Task which builds
        just one image (e.g. [the kaniko task](https://github.com/tektoncd/catalog/tree/main/task/kaniko/0.4)), and run
        it for each Dockerfile, instead of having to the task to take multiple Dockerfiles as input. This missing piece
        of this is supporting the Task which determines with Dockerfiles to build and provides them as an array (instead
        of encoded in a string).
     3. for each image that was built, emit the URL and the hashes as results (post
        [TEP-0075](https://github.com/tektoncd/community/pull/479) as an array of dictionaries, but that's another
        story!)

   ```
   filter-dockerfiles
        |
        | result: list of dockerfiles
        v
   (for each: filter-dockerfiles result)
      kaniko build
        |
        | result: list of built urls, list of built hashes
        v
   ```
   
   *Concrete example #2: test sharding*

   A quick way to speed up slow test suites (especially when their slowness is unavoidable, e.g. a suite of browser
   based tests) is to shard their execution, i.e. to split the tests up into groups, run the tests separately, and 
   combine the results. In order to support sharding, looping support would be required, but putting that aside, the
   in order to support more complex sharding use cases (without having to write testing tasks that having sharding logic),
   being able to produce array results could help a lot.
   
   For example imagine running golang based tests using [the golang-test task](https://github.com/tektoncd/catalog/tree/main/task/golang-test/0.2)
   and dividing them across shards by index:
   
   ```
   divide-tests-into-shards
        |
        | result: lists of starting and ending indexes for each shard,
        |   e.g. starting indices [0, 8, 15] and ending [7, 14, 23]
        |   (when we add nesting support this would more cleanly be [[0, 7], [8, 14], [15, 23]])
        |   or maybe the sharding is based on previous run information
        | result: list of the names of tests each shard should run, e.g. [[test_foo, test_bar], [test_baz]]
        v
   (for each: divide-tests-into-shards result)
      golang-test (the task would need to be updated to support running a subset of tests)
   ```

1. **Use case for array indexing: Unwinding loops (i.e. using one Task multiple times for some set of items)**
   Without looping support and without indexing, there will be no way to mix array results with tasks that expect
   strings.

   If we add support for array results before we add support for looping (and until we have an approved proposal, there is
   no guarantee we ever will!) there will be no way to use an array result from one Task with a Task that expects a
   string parameter.

   For example, without looping, folks can get the reuse they want by hard coding the Tasks explicitly, which would
   probably support a surprising number of use cases (but look ugly and involve a lot of copy and paste), e.g.:

   * Have a task that divides tests into 3 shards - if you know there are always 3 shards, you could add 3 go-test
     pipeline tasks and have each one use the result of the task that divides them:
     ```
        divide-tests-into-shards
                   |
                   | result: list of starting and ending indexes for each shard, e.g. [[0, 7], [8, 14], [15, 23]]
                 / | \
     go-test-0  go-test-1  go-test-2
       [0,7]      [8,14]   [15, 23]
     ```

   * If you know a repo contains 14 Dockerfiles (e.g.
     [tekton/images in plumbing contains 14 dockerfiles](https://github.com/tektoncd/plumbing/tree/main/tekton/images) to
     build, you could have a task that grabs the 14 paths, and then feed them into 14 kaniko pipeline tasks individually

1. **Use case for array indexing: Tasks that wrap CLIs**
   Array indexing would make it possible for Tasks that wrap generic CLIs to provide
   (short - see [size limits](#size-limit)) stdout output as array results which could be indexed by consuming tasks.
   For example [the gcloud CLI task](https://github.com/tektoncd/catalog/tree/main/task/gcloud/0.1): the CLI could be
   doing all kinds of different things depending on the arguments (e.g. `gcloud projects list` vs
   `gcloud container clusters list`). In order to consume the output in downstream tasks (with minimal effort), you
   could index into the result. (Note that the existing gcloud task provides no results at all.)

   Example gcloud output:

   ```
   # gcloud container clusters list
   NAME        LOCATION     MASTER_VERSION   MASTER_IP     MACHINE_TYPE   NODE_VERSION         NUM_NODES  STATUS
   eucalyptus  us-central1  1.18.20-gke.501  1.1.1.1  n1-standard-4  1.16.15-gke.6000 **  3          RUNNING
   ```

   Using this as a result would require supporting nested arrays, which this TEP is not proposing but would be a logical
   next step (e.g. `$tasks.gcloud.results.[1][1]` if you wanted the location of the first cluster OR even to get the
   entire line and provide it as an array param with `$tasks.gcloud.results[1]`).

## Requirements

* Must be possible for a result array to be empty
* Must be possible to use the array results of one Task in a Pipeline as the
  param of another Task in the pipeline which has an array param
* Must be possible to use one specific value in an array result of one Task
  in a Pipeline as the param of another Task in the pipeline which has a string param
  * If there is no value at the specified index, the Pipeline execution should fail
    (or we may be able to use [TEP-0048](https://github.com/tektoncd/community/pull/240)
    to specify a default value to use in that case instead)
* This must be support for all uses of results, including
  [pipeline results](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#emitting-results-from-a-pipeline)

## Proposal

Currently we treat the contents of
[a Task's result file(s)](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#emitting-results)
as a string. The file is located at `$(results.resultName.path)` which expands to `/tekton/results/resultName`.
In this proposal, the results section of the Task will inform the controller about whether it should interpret the
content of the result as [json](#why-json) or as a string:
  * If the type indicates that the result is an array, the controller will interpret the result as json and expect an
    array. If the content is not json or not an array, the TaskRun will fail
  * If the type indicates that the result is a string, the controller will simply use the result as is (i.e. the
    same logic as today)

Pros:
  * Completely backwards compatible

Cons:
  * Additional complexity in that the results file could contain two different kinds of content

This feature would be considered alpha and would be
[gated by the alpha flag](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#alpha-features).

### Why json?

This proposal suggests using `json` as the format for more complex types like arrays, and in
[TEP-0075](https://github.com/tektoncd/community/pull/479), dictionaries (technically "objects"). Possible other formats
we could use are:

* `yaml` - to expose a syntax for variable replacement, we'd likely still end up leaning on jsonpath, i.e. we'd end
  up mising yaml and JSON syntax (however we could likely add support for yaml results output in the future)
* `protobuf` (this would dramatically increase the difficulty in emitting structured results from tasks - either we'd
  see every Task including a step with protobuf tools in it or we'd need to include some by default)
* `xml` (seems more verbose than we'd need and afaik in cloud native tools isn't in wide use)
* `csv` (would also be easy to use but afaik it wouldn't support more complex types like dicts? or we'd need to add some
  kind of syntax on top of the csv format to define more complex types)

This proposal suggests using `json` because:
* It's human-readable
* It's possible for Tasks to write json content without needing extra tools
* We've added json specific support to other parts of our APIs (e.g. [in triggers](https://github.com/tektoncd/triggers/blob/f2380d7d33666547ee7ed965730cf7dbc1aa5421/docs/triggerbindings.md#accessing-data-in-http-json-payloads))
* Kubernetes supports `yaml` and `json`, so it makes sense to narrow our choices to at least these, as opposed to
  introducing a new format into the mix.
* Technically YAML (the default config language for many Kubernetes integrations) is a superset of json

We may want to consider also adding support for [JSON text sequences](#also-support-json-text-sequences) in future.

### Notes/Caveats

* Introducing typing to results raises questions about
  [validating the structure of the results emitted by Tasks](#validating-json-results-at-runtime)
* The way results are currently supported [constrains the size of results that can be emitted](#size-limits)

### Risks and Mitigations

* Changing the type of Task Result values from string to being ArrayOrString might be backwards incompatible
    * Mitigation: perform a manual test to make sure this isn't backwards incompatible (reconcile a TaskRun with a string
      result both before and after the change - e.g. create a TaskRun before the change, then restart the controller so
      it is re-reconciled; revisit this proposal if we can't find a way to make the change and be backward compatible)
    * Note this will be a change for folks consuming the library, e.g. the CLI, as a result implementing this TEP
      should include working with the CLI team to pull in the updates and make sure they are not negatively impacted

## Design Details

* [Emitting array results](#emitting-array-results)
* [Indexing into arrays with variable replacement](#indexing-into-arrays-with-variable-replacement)
* [Using array results with variable replacement](#using-array-results-with-variable-replacement)

### Emitting array results

We add support for writing json content to `/tekton/results/resultName`, supporting strings and arrays of strings.

For example, say we want the value of the Task foo's result `animals` to be "cat", "dog" and "squirrel":

1. The Task would declare a result with `type:array`:

  ```yaml
  apiVersion: tekton.dev/v1beta1
  kind: Task
  metadata:
    name: task-with-parameters
  spec:
    params: ...
    steps: ...
    results:
    - name: animals
      type: array # this field is new for results
  ```

  The `results.type` field would take the values `string` and `array`. _See [alternatives](#alternatives) for the option
  to deprecate the `type` field and embrace the json schema syntax proposed in [TEP-0075](https://github.com/tektoncd/community/pull/479)
  instead._

1. Write the following content to `$(results.animals.path)`:

   ```json
   ["cat", "dog", "squirrel"]
   ```

1. This would be written to the pod termination message as escaped json, for example (with a string example included as well):

   ```
   message: '[{"key":"animals","value":"[\"cat\",\"dog\",\"squirrel\"]","type":"TaskRunResult"},{"key":"someString","value":"aStringValue","type":"TaskRunResult"}]'
   ```

1. We would use the same
   [ArrayOrString type](https://github.com/tektoncd/pipeline/blob/1f5980f8c8a05b106687cfa3e5b3193c213cb66e/pkg/apis/pipeline/v1beta1/param_types.go#L89)
   (which in TEP-0075 could be expanded to support dictionaries as well) for
   task results, e.g. for the above example, the TaskRun would contain:

   ```yaml
     taskResults:
     - name: someString
       value: aStringValue
     - name: animals
       value:
       - cat
       - dog
       - squirrel
   ```

#### Validating JSON results at runtime

The contents of the json file may not match the expected format when array results are used (or in future if we
[add support for objects](https://github.com/tektoncd/community/pull/479)), specifically:

* The file could contain a string that is not formatted into the expected type (array), and/or content that is not valid
  json
* The file could contain json that is too large and will be truncated (also resulting in invalid json)
* The file could contain json we don't support (e.g. objects before we add support, nested arrays within arrays)

Ultimately the result when this happens is that the `TaskRun` should fail with an informative error. Validation will
have to occur at runtime (we won't know conclusively until the execution of the `Task` whether or not the results
will be in the correct format, and that can vary depending on the input).

Options for how to validate the result content:

1. [In the entrypoint binary](https://github.com/tektoncd/pipeline/tree/main/cmd/entrypoint)
   (i.e. before writing the results to be consumed by the controller)
2. In the controller (i.e. when consuming the results emitted by the entrypoint binary)

If we use (1) for all validation, we will need to add arguments to the entrypoint binary (or agument the entrypoint
binary to discover this information some other way, e.g. via annotations added to the pod) to inform it what formats
to expect. It would be less complicated to validate the specific expected type and format via (2) since the controller
already has this information. The entrypoint binary however could validate that the format is json (and could even
validate that it is supported json if desired) and could also validate that the result is not too large.

#### Size limits

Currently Tekton passes results from Tasks to back to the controller
[via the pod's termination message](https://github.com/tektoncd/pipeline/blob/main/docs/developers/README.md#how-task-results-are-defined-and-outputted-by-a-task).
[If the resulting termination message is > 4096 bytes it will be truncated](https://kubernetes.io/docs/tasks/debug-application-cluster/determine-reason-pod-failure/#customizing-the-termination-message).

Some of the space in the termination message is taken up by the start time, and by the metadata around the result itself,
for example for a container producing a result called `check`:

```
[{"key":"check","value":"","type":"TaskRunResult"},{"key":"StartedAt","value":"2021-08-11T23:28:47.398Z","type":"InternalTektonResult"}]
```

That's about 112 bytes of overhead.

When an array result is used, the value would contain escaped json, e.g.:

```
"value":"[\"cat\",\"dog\",\"squirrel\"]"
```

That's an additional 2 bytes for `[]`, and approximately an addition 5 bytes for each element in the array for the
escaped quotation marks and comma (ignoring that the last item only needs 4 bytes XD).

Imagining you want to make an array that contains `gnarly` as many times as possible:

```
num_gnarlys = (4096 bytes - 112 bytes of overhead - 2 bytes for `[]`) / (5 bytes + 6 bytes in "gnarly")
```

You would be able to fit 362 `gnarly`s in one result.

Supporting larger results would require us to explore an alternative way of emitting results
([pipelines#4012](https://github.com/tektoncd/pipeline/issues/4012),
[TEP-0086](https://github.com/tektoncd/community/pull/521)).

### Indexing into arrays with variable replacement

In addition to supporting [JSONPath](https://tools.ietf.org/id/draft-goessner-dispatch-jsonpath-00.html)
style [star notation](https://github.com/tektoncd/pipeline/issues/2041), we add support for
[the JSONPath subscript operator](https://tools.ietf.org/id/draft-goessner-dispatch-jsonpath-00.html#name-jsonpath-examples)
for accessing "child" members of the array by index.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
spec:
  pipelineRef:
    name: deploy
  params:
    - name: environments
      values:
        - 'staging'
        - 'qa'
        - 'prod'
---
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: deploy
...
spec:
  params:
    - name: environments
      type: array
...
  tasks:
    - name: deploy
      params:
        - name: environment
          value: '$(params.environments[0])'
```

The resulting taskRun would contain:

```yaml
  params:
    - name: environment
      value: 'staging'
```

This proposal does not include adding support for any additional syntax, e.g. slicing (though it could be added in the
future!)

### Using array results with variable replacement

#### To provide values for string params

The same syntax [above](#indexing-into-arrays-with-variable-replacement) could be used to access a specific value in
the results of a previous Task.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
...
spec:
tasks:
  - name: get-environments
  - name: deploy
    params:
      - name: environment
        value: '$(tasks.get-environments.results.environments[0])'
```

#### To provide values for array params

Additionally, array results can be passed directly to Tasks which take arrays as parameters using
[the `[*]` variable replacement syntax](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#substituting-array-parameters).

For example, when params `update-all-environments` in array type is substituted with another array type `tasks.get-environments.results.environments`:
```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
...
spec:
tasks:
  - name: update-all-environments
    params:
      - name: environments
        value: $(tasks.get-environments.results.environments[*])
```
What we will get will be:
```
params:
      - name: environments
        value:
        - 'value1'
        - 'value2'
```
Another example will be thw following if `tasks.get-environments.results.environments` and `environments` are both arrays of strings:
```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
...
spec:
tasks:
  - name: update-all-environments
    params:
      - name: environments
        value: '$(tasks.get-environments.results.environments[*])'
```
A third way for variable replacements can be:
```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
...
spec:
tasks:
  - name: update-all-environments
    params:
      - name: environments
        value:
          - '$(tasks.get-environments.results.environments[*])'
```

## Test Plan

In addition to unit tests the implementation would include:

* At least one reconciler level integration test which includes an array result
* A tested example of a Task that produces an array result with:
  * Another Task consuming that array
  * Another Task consuming one specific value from that array
* An integration test which verifies that complex json results do not cause problems in the controller, e.g. that if a
  Task provides a deeply nested dictionary as a result this is handled gracefully:
  * Does not take "significantly" increase processing time - we'll need to do a couple of measurements to determine the 
    correct value to use here
  * Gives the expected behavior of failing the TaskRun

## Design Evaluation

* [Reusability](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability):
  * Pro: This will improve the reusability of Tekton components by enabling the scenario of a Task providing an array result
    and then a Pipeline being able to loop over those value for subsequent Tasks (i.e. reusing Tasks which are designed
    for single inputs, but users want to use 'for each' item in an array)
* [Simplicity](https://github.com/tektoncd/community/blob/main/design-principles.md#simplicity)
  * Pro: This proposal reuses the existing array or string concept for params
  * Pro: This proposal continues [the precedent of using JSONPath syntax in variable replacement](https://github.com/tektoncd/pipeline/issues/1393#issuecomment-561476075)
* [Flexibility](https://github.com/tektoncd/community/blob/main/design-principles.md#flexibility)
  * Con: Although there is a precedent for including JSONPath syntax, this is a step toward including more hard coded
    expression syntax in the Pipelines API (without the ability to choose other language options)
* [Conformance](https://github.com/tektoncd/community/blob/main/design-principles.md#conformance)
  * Supporting array results and indexing syntax would be included in the conformance surface

## Drawbacks

* Increases the size of TaskRuns (by including arrays in termination messages and results)
* Only partial support for JSONPath (i.e. just array indexing support, nothing more)

## Alternatives

1. Do not support arrays explicitly - if we do this, we probably shouldn't do TEP-0075 either, i.e. results should
   always just be strings
1. Add support for array results, but don't add support for indexing into arrays
   * Con: In TEP-0075 we propose adding support for dictionaries; if we take the same approach as this proposal, this
     would mean not allowing the ability to get individual values out of those dictionaries which would significantly
     limit the number of Tasks this would be compatible with (i.e. we should be consistent between arrays and
     dictionaries)
   * Con: Without indexing, arrays will only work with arrays. This means you cannot combine arrays with Tasks that
     only take string parameters and this limits the interoperability between Tasks. (See [use cases](#use-cases))
1. Instead of relying on the Task spec to tell us whether or not to interpret the result as json, we add a second 
   result file with a `.json` extension. When Task authors want to use array results (or any other complex types if
   we later support them) the would write to `$(results.resultName.jsonPath)` instead of `$(results.resultName.path)`
   and the result would be interpreted as json
    * Con: The additional complexity of two different result files and needing to know when to use which (and never to
      use both)
1. Instead of relying on the Task spec to tell us whether or not to interpret the result as json, expect the content to
   always be json; i.e. require that json be escaped when the desire is to have a string result that contains json
   * Con: Backwards incompatible; anyone currently emitting json as a string would need to update their tasks to
     escape the content
   * Con: Asking Tasks to escape json means those Tasks would need to include a step that contains a tool that can
     escape the json
1. Instead of failing PipelineTasks which try to refer to values in Arrays that don't exist (e.g. empty arrays or going
  beyond the bounds of an array), we could skip them
  * Con: If this was done unintentionally, the user might not notice the skipped task
1. Include a syntax for obtaining the length of the array via syntax like `$params.somearray.length`
  * Con: if we adopt this for arrays now, we'll also need to adopt similar functionality for other types, e.g. if we
    add [dictionary support via TEP-0075](https://github.com/tektoncd/community/pull/479), or nested arrays, etc.
  * Con: if we just go ahead with `.length` we risk defining our own expression language; instead we could wait
    and incrementally adopt more json path, json schema, and even [CEL](https://github.com/tektoncd/community/pull/314)
    support and tackle this then
1. Adopt a different syntax
  * Con: would likely need to rethink our existing [star notation](https://github.com/tektoncd/pipeline/issues/2041)
    support as well
  * Examples of other options:
    * [JSON pointer](https://datatracker.ietf.org/doc/html/rfc6901) - this syntax is much smaller in scope than JSONPath
      which is appealing, however it doesn't support iteration that we may want to adopt such as array slicing
    * [CEL](https://github.com/google/cel-spec/blob/master/doc/langdef.md) - this syntax is much larger in scope
      than JSONPath which could potentially allow expressing more; see
      [pipelines#2812](https://github.com/tektoncd/pipeline/issues/2812) for more on adding an entire expression
      language
  * Choosing JSONPath as our preferred syntax has the advantage of supporting many use cases around accessing values
    within data structures for variable replacmeent without expanding the Tekton API to include an entire expression
    language.
1. Rely only on custom tasks for accessing values inside params (e.g.
  [this example of the CEL custom task](https://github.com/tektoncd/pipeline/issues/3255#issuecomment-765535707))
1. Use a format other than json (see [why json](#why-json))

### Also support JSON text sequences

In addition to supporting results files containing complex types defined in JSON, we could make it easier to for Tasks
to write arrays of data by adding support for [JSON text sequences](https://datatracker.ietf.org/doc/html/rfc7464).

For example, this proposal would require an array of strings to be written to the results file in a format like:

```json
[ "foo", "bar", "baz" ]
```

With JSON text sequences the braces could be dropped and the commas replaced with newlines:

```json
"foo"
"bar"
"baz"
```

Asuming
[support is also added for JSON objects](https://github.com/tektoncd/community/pull/479)), and support for more JSON
primitive data types, a complex JSON array written to a result file could look like:

```json
[ 1, 2, 3, "four", { "five": 5 }, [6], { "seven": [ 7, 7, "7" ] } ]
```

This could be expressed as a JSON text sequence like this:

```
1
2
3
"four"
{ "five": 5 }
[6]
{ "seven": [ 7, 7, "7" ] }
```

Support for JSON text sequences in the Tekton Task and Pipeline definitions could also make it easier to combine result
from multiple Tasks into one array parameter, for example:

```
task 1 result = "foo"\n
task 2 result = "bar"\n
task 3 result = "baz"\n

input to some array = task1 result + task2 result + task 3 result =
"foo"
"bar"
"baz"

-- an array with three elements in it
```

(Thanks @mogsie for the above info and content!)

Pros:
* Support for this syntax could be included in addition to the proposed syntax (i.e. both can be supported)
* Supporting this syntax would make it easier for Tasks that use tools that do not naturally produce JSON output to
  create
* Output can be truncated and still remain valid
* This syntax makes it easier to combine multiple lists together without having to parse and reformat JSON
Cons:
* There would be more than one accepted format for Task results - this would need to be supported in tooling and users
  would need to understand they can write in either format

## Upgrade & Migration Strategy

By adding an additional file path, we make this a completely backwards compatible change.

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

TBD

## References

* [pipelines#1393 Consider removing type from params (or _really_ support types)](https://github.com/tektoncd/pipeline/issues/1393)
* [pipelines#3255 Arguments of type array cannot be access via index](https://github.com/tektoncd/pipeline/issues/3255)
