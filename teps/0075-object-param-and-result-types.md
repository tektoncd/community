---
status: implementable
title: Object/Dictionary param and result types
creation-date: '2021-07-14'
last-updated: '2022-03-18'
authors:
- '@bobcatfish'
- '@skaegi' # I didn't check with @skaegi before adding his name here, but I wanted to credit him b/c he proposed most of this in https://github.com/tektoncd/pipeline/issues/1393 1.5 years ago XD
---

# TEP-0075: Object/Dictionary param and result types

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
    - [User Experience](#user-experience)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [Potential future work](#potential-future-work)
- [Implementation Pull request(s)](#implementation-pull-request-s)
- [References](#references)

<!-- /toc -->

## Summary

_Recommendation: read
[TEP-0076 (array support in results and indexing syntax)](https://github.com/tektoncd/community/pull/477)
before this TEP, as this TEP builds on that one._

This TEP proposes adding object (aka dictionary) types to Tekton Task and Pipeline
[results](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#emitting-results)
and [params](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-parameters), as well as adopting a
small subset of [JSONPath](https://tools.ietf.org/id/draft-goessner-dispatch-jsonpath-00.html)
syntax (precedent in
[the array expansion syntax we are using](jhttps://github.com/tektoncd/pipeline/issues/1393#issuecomment-561476075))
for accessing values in these objects.

This proposal is dependent on
[TEP-0076 (array support in results and indexing syntax)](https://github.com/tektoncd/community/pull/477)
in that this TEP should follow the precedents set there and also in that if we decide not to support array results, we
probably won't support object results either.

This proposal also includes adding support for limited use of
[json object schema](https://json-schema.org/understanding-json-schema/reference/object.html), to express the expected
structure of the object.

_Dictionary vs. object: The intended feature was supporting "dictionaries", but JSON Schema calls these "objects" so
this proposal tries to use "objects" as the term for this type._

## Motivation

Tasks declare workspaces, params, and results, and these can be linked in a Pipeline, but external tools looking at
these Pipelines cannot reliably tell when images are being built, or git repos are being used. Current ways around this
are:

* [PipelineResources](https://github.com/tektoncd/pipeline/blob/main/docs/resources.md) (proposed to be deprecated
  in [TEP-0074](https://github.com/tektoncd/community/pull/480))
* Defining param names with special meaning, for example
  [Tekton Chains type hinting](https://github.com/tektoncd/chains/blob/main/docs/config.md#chains-type-hinting))

This proposal takes the param name type hinting a step further by introducing object types for results: allowing Tasks
to define structured results. These structured results can be used to define interfaces, for example the values that are
expected to be produced by Tasks which do `git clone`. This is possible with just string results, but without a grouping
mechanisms, all results and params are declared at the same level and it is not obvious which results are complying with
an interface and which are specific to the task.

### Goals

* Tidy up Task interfaces by allowing Tasks to group related parameters (similar to the
  [long parameter list](https://www.arhohuttunen.com/long-parameter-list/) or
  [too many parameters](https://dev.to/thinkster/code-smell-too-many-parameters-435e) "code smell")
* Enabled defining well known structured interfaces for Tasks (typing), for example, defining the values that a Task
  should produce when it builds an image, so that other tools can interface with them (e.g.
  [Tekton Chains type hinting](https://github.com/tektoncd/chains/blob/main/docs/config.md#chains-type-hinting))
* Take a step in the direction of allowing Tasks to have even more control over their params and
  results ([see pipelines#1393](https://github.com/tektoncd/pipeline/issues/1393))
  (e.g. one day providing built in validation for params as part of their declaration)

### Non-Goals

* Adding complete [JSONPath](https://tools.ietf.org/id/draft-goessner-dispatch-jsonpath-00.html)
  syntax support
* Adding support for nesting, e.g. object params where the values are themselves objects or arrays
  (no reason we can't add that later but trying to keep it simple for now)
* Adding complete [JSON schema](https://json-schema.org/) syntax support
* Supporting use of the entire object in a Task or Pipeline field, i.e. as the values for a field that requires a
  object, the way we do
  [for arrays](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#substituting-array-parameters). Keeping this
  out of scope because we would need to explictly decide what fields we want to support this for. We'll likely add it
  later; at that point we'd want to support the same syntaxes we use
  [for arrays](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#substituting-array-parameters) (including
  `[*]`)

### Use Cases

1. Grouping related params and results such that users and tools can make inferences about the tasks. For example
   allowing [Tekton Chains](https://github.com/tektoncd/chains/blob/main/docs/config.md#chains-type-hinting) and other
   tools to be able to understand what types of artifacts a Pipeline is operating on.

   Tekton could also define known interfaces, to make it easier to build these tools. For example:
    * Images - Information such as the URL and digest
    * Wheels and other package formats (see below)
    * Git metadata - e.g. the state of a git repo after a clone, pull, checkout, etc.
    * Git repo configuration - e.g. the info you need to connect to a git repo including url, proxy configuration, etc.

   For example [the upload-pypi Task](https://github.com/tektoncd/catalog/tree/main/task/upload-pypi/0.1)
   defines 4 results which are meant to express the attributes of the built
   [wheel](https://www.python.org/dev/peps/pep-0427/):

   ```yaml
     results:
     - name: sdist_sha
       description: sha256 (and filename) of the sdist package
     - name: bdist_sha
       description: sha256 (and filename) of the bdist package
     - name: package_name
       description: name of the uploaded package
     - name: package_version
       description: version of the uploaded package
   ```

   Some interesting things are already happening in this example: `sdist_sha` contains both the filename and the sha -
   an attempt to group related information.

   With object results, we could define the above with a bit more structure like this:

   ```yaml
     results:
       - name: sdist
         description: |
           The source distribution
            * sha: The sha256 of the contents
            * path: Path to the resulting tar.gz
         type: object
         properties:
           sha:
            type: string
           path:
            type: string
       - name: bdist
         description: |
           The built distribution
            * sha: The sha256 of the contents
            * path: Path to the resulting .whl file
         type: object
         properties:
           sha:
            type: string
           path:
            type: string
       - name: package
         description: |
           Details about the created package
            * name: The name of the package
            * version: The version of the package
         type: object
         properties:
           name:
            type: string
           version:
            type: string
   ```

   Eventually when we have nested support, we could define a `wheel` interface which contains all of the above.

2. Grouping related params to create simpler interfaces, and allowing similar Tasks to easily define pieces of their
   interface. For
   example [the git-clone task has 15 parameters](https://github.com/tektoncd/catalog/blob/main/task/git-clone/0.4/README.md#parameters)
   ,
   and [the git-rebase task has 10 parameters](https://github.com/tektoncd/catalog/blob/main/task/git-rebase/0.1/README.md#parameters)
   . Some observations:
    * Each has potential groupings which stand out, for example:
        * The git-rebase task could group the `PULL` and `PUSH` remote params; each object would need the same params,
          which could become an interface for "git remotes"
        * Potential groupings for the git-clone task stand out as well, for example the proxy configuration
        * On that note, since the git-rebase task is using git and accessing remote repos, it probably needs the same
          proxy configuration, so what they probably both need is some kind of interface for what values to provide when
          accessing a remote git repo Other examples
          include [okra-deploy](https://github.com/tektoncd/catalog/tree/main/task/orka-deploy/0.1) which is using param
          name prefixes to group related params (e.g. `ssh-`, `okra-vm`, `okra-token`).

## Requirements

* Must be possible to programmatically determine the structure of the object
* Must be possible for a result object to be empty
* Must be possible to use the object results of one Task in a Pipeline as the param of another Task in the pipeline
  which has a object param when the interface matches (more detail in
  [required vs optional keys](#required-vs-optional-keys))
* Must be possible to use one specific value in an object result of one Task in a Pipeline as the param of another Task
  in the pipeline which has a string param
    * If there is no value for the specified key, the Pipeline execution should fail
      (or we may be able to use [TEP-0048](https://github.com/tektoncd/community/pull/240)
      to specify a default value to use in that case instead)

## Proposal

* We would add support for object types for results and params, in addition to the existing string and array support
    * Initially we would only support string values, eventually we can expand this to all values (string, array, object)
      (note that this is the case for arrays as well, we don't yet support arrays of arrays)
    * Only string key types would be supported (which is
      [the only key type supported by json](https://datatracker.ietf.org/doc/html/rfc7159#section-4))
* We would use [json object schema syntax](https://json-schema.org/understanding-json-schema/reference/object.html)
  ([as previously suggested](https://github.com/tektoncd/pipeline/issues/1393#issuecomment-558833526) - and see also
  [why JSON Schema](#why-json-schema)) to express the object structure
* To support object results, we would support writing json results to the results file, as described in
  [TEP-0076 Array results and indexing](https://github.com/tektoncd/community/pull/477)
  (see "why json" in that proposal)

This feature would be considered alpha and would be
[(optional)gated by the alpha flag](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#alpha-features).

* [Defaulting to string types for values](#defaulting-to-string-types-for-values)
* [Adding additional JSON Schema properties](#adding-additional-json-schema-properties)
* [Why JSON Schema?](#why-json-schema)
* [Matching interfaces and extra keys](#matching-interfaces-and-extra-keys)
* [Required vs optional keys](#required-vs-optional-keys)

### Defaulting to string types for values

As an optimization, we'd support defaulting to string types for keys without the Task author needing to explicitly
specify this. For example this more verbose specification:

```yaml
 - name: sdist
   description: |
     The source distribution
      * sha: The sha256 of the contents
      * path: Path to the resulting tar.gz
   type: object
   properties:
     sha:
       type: string
     path:
       type: string
```

Would be equivalent to:

```yaml
 - name: sdist
   description: |
     The source distribution
      * sha: The sha256 of the contents
      * path: Path to the resulting tar.gz
   type: object
   properties:
     sha: { } # type:string is implied
     path: { } # type:string is implied
```

This would be supported in recognition that:

a. Only string types would initially be supported b. Even when other types are supported, the most common usage of
objects will likely use string values

### Adding additional JSON Schema properties

This proposal suggests adding a new `properties` section to param and result definition. If we later support more json
schema attribute such as `additionalProperties` and `required`, we'd also support them at the same level as the
`properties` field here. (
See [Alternative #1 adding a schema section](#alternative-1--introduce-a-schema-section-specifically-for-the-type-schema)
.)
(At that point we should also consider whether we want to adopt strict JSON schema syntax or if we want to support Open
API schema instead; see [why JSON Schema](#why-json-schema).)

### Why JSON Schema?

Assuming we move forward with using JSON to specify results (see "why json" in
[TEP-0076 Array results and indexing](https://github.com/tektoncd/community/pull/477)), we'll need a syntax that allows
us to define schemas for JSON.

Since JSON schema was created for exactly that purpose, it seems like a reasonable choice
([see original suggestion](https://github.com/tektoncd/pipeline/issues/1393#issuecomment-558833526).
[OpenAPI schema objects](https://swagger.io/specification/#schema-object) are an interesting alternative which builds on
JSON schema and are already used by Kubernetes
[to publish schema valiation for CRDs](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#publish-validation-schema-in-openapi-v2)
. The subset of JSON Schema that we are proposing to adopt in this TEP is compatible with OpenAPI schema
([Open API supported JSON Schema Keywords](https://swagger.io/docs/specification/data-models/keywords/)), so at the
point when we start proposing more JSON Schema support we should consider if we want to support the Open API schema
variations instead.

#### Alternative: CUE

The language [CUE](https://cuelang.org/) also provides a syntax for defining schemas.
[It allows using less text to express the same schema](https://cuelang.org/docs/usecases/datadef/#json-schema--openapi)

Pros:
* Less text required; much more succinct to express complex validation
* [CUE can be used to validate JSON](https://cuelang.org/docs/integrations/json/) so if we decided to use CUE for
  expressing schemas, Tasks could still output results in JSON (i.e. no additional complication for Task authors when
  writing steps and no need for additional tools to generate results in the right format)

Cons:
* CUE is a superset of json; in order to express CUE within our existing yaml and json types, we'd need a way to
  encode CUE within those types
* CUE is intended for more than just expressing schemas, it is intended also for
  [code generation, and expressing configuration](https://cuelang.org/docs/about/#applications). (Instead of embedding
  it into Tekton types, maybe a Tekton integration that takes advantage of all CUE has to offer would be to use CUE
  to generate Tekton types?)
* In the [open API schema comparison](https://cuelang.org/docs/usecases/datadef/#json-schema--openapi) the open api
  version can be read without needing to learn a specific syntax (e.g. the difference between `max?: uint & <100` the
  verbose Open API version which specifies max is an integer with minimum 0 and exclusive maximum 100).
* Our [flexibility design standard](https://github.com/tektoncd/community/blob/main/design-principles.md#flexibility)
  recommends we prefer that when we need to pull in some other language, we use existing languages which are widely
  used and supported. Instead of being an early adopter of CUE we could wait until it is more popular and then consider
  using it (we can also delay this decision until we want to add more schema support).

### Matching interfaces and extra keys

An object provided by one Task (as a result) will be considered to match the object expected by another Task (as a
params) if the object in the result contains _at least_ the [required](#required-vs-optional-keys) keys declared by the
param in the consuming Task. The extra keys will be ignored, allowing us to take a
[duck typing](https://en.wikipedia.org/wiki/Duck_typing) approach and maximize interoperabiltiy between tasks.

For example imagine a Task which requires a param object that contains `url` and `httpsProxy`. Another task produces an
object with those two keys in addition to other keys. It should be possible to pass the object with the additional keys
directly to the Task which requires only `url` and `httpsProxy` without needing to modify the object in between.

If we expand our JSON Schema support in the future (and we have use cases to support it) we could allow Tasks to express
if they would like to override this and not allow additional keys to be provided via
[JSON Schema's `additionalProperties` field](https://json-schema.org/understanding-json-schema/reference/object.html#additional-properties)
(which defaults to allowing additional properties).

**When the Task writes more keys than it declares in its results:**

- The TaskRun will succeed
- The additional keys will not be included in the TaskRun status
- The additional keys will not be available for variable replacement in a Pipeline; only the declared keys will be
  available

**When a Task uses the result of a previous Task which declares more keys in addition to what the Task needs:**

- This will be allowed
- The TaskRun will be created with only the keys that the Task needs; the rest will be ignored

### Required vs optional keys

We have several options for how we define and handle required and optional keys:

1. Embrace the optional by default behavior of JSON Schema; instead of validating the presences of "required" keys via
   jsonschema, we could do the validation based on the declared variable replacement, e.g. say a Task declares it needs
   an object called `foo` with an attribute called `bar`. At runtime if the Task is provided with an object
   `foo` that doesn't have an attribute called `bar` this will be okay unless the Task contains variable replacement
   that uses it (`$(params.foo.bar)`). Con: weird because effectively we're implying `required` (assuming the fields are
   used, and if they aren't used, why are they there) even though the JSON Schema declaration says the fields are
   optional.
2. Infer that all keys are required, e.g. take
   the [TEP-0023 implicit param approach](https://github.com/tektoncd/community/blob/main/teps/0023-implicit-mapping.md)
   and in a mutating admission controller, add the `required` section for all properties in the dictionary (unless
   a `required` field is already added). Con: TEP-0023 deals with making changes to runtime types (PipelineRun, TaskRun)
   and it would be strange to mutate instances that will be reused; in fact mutations like this would interfere with
   efforts we might explore in the future to provides hashes of Tasks and Pipelines so folks can ensure the are running
   what they think they are running.
3. Like the previous version but instead of mutating the Tasks and Pipelines, imply this implicitly (i.e. make the
   assumption in the controller but do not reflect it in the types themselves). Pro: We are already suggesting infering
   some things such as
   [that `type: string` is being used for empty properties](#declaring-object-results-and-params), so adding this kind
   of inference as well isn't totally out of the question. Con: Anyone reading the JSON Schema in the Task would think the
   attributes are optional when they are not
4. Make our version of JSON Schema deviate from the official version: default to `required` and instead introduce syntax
   for `optional` (in fact
   [early versions of JSON Schema used `optional` instead of `required`](https://datatracker.ietf.org/doc/html/draft-zyp-json-schema-03#appendix-A))
5. [Create our own JSON Schema based syntax instead](#alternative-2-create-a-wrapper-for-json-schema)

This proposal suggests we take approach (1) as it allows us to use JSON Schema as is and gives us the behavior we want.
Additionally, optional by default behavior will be useful if we pursue
[the future option of supporting pre-defined schemas](#potential-future-work): optional by default will allow Tasks to
refer to schemas for their params, and additive changes can be made to those schemas without requiring all Tasks using
them to be updated.

### Notes/Caveats

[See also TEP-0076 Array results and indexing](https://github.com/tektoncd/community/pull/477) for notes and caveats
specific to supporting json results.

* Since [json only supports string types for keys (aka "names")](https://datatracker.ietf.org/doc/html/rfc7159#section-4)
  we would only support string types for keys
* What if a Pipeline tries to use a object key that doesn't exist in a param or result?
    * Some of this could be caught at creation time, i.e. pipeline params would declare the keys each object param will
      contain, and we could validate at creation time that those keys exist
    * For invalid uses that can only be caught at runtime (e.g. after fetching the task spec), the PipelineRun would
      fail

### Risks and Mitigations

[See TEP-0076 Array results and indexing](https://github.com/tektoncd/community/pull/477) for risks and mitigations
specific to expanding ArrayOrString to support more types, including size limitations caused by our implementation of
results ([pipelines#4012](https://github.com/tektoncd/pipeline/issues/4012)).

### User Experience

* Using the JSON Schema syntax to describe the structure of the object is a bit verbose but looking at our
  [Alternatives](#alternatives) this seems like the best option assuming we want to support more complex types
  in the future.

## Design Details

* [Declaring object results and params](#declaring-object-results-and-params)
* [Emitting object results](#emitting-object-results)
* [Using objects in variable replacement](#using-objects-in-variable-replacement)

### Declaring object results and params

We would use [JSON object schema syntax](https://json-schema.org/understanding-json-schema/reference/object.html) to
declare the structure of the object.

Declaring defaults for parameters that are of type object would follow the pattern we have already established with
[array param defaults](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-parameters) which is
to declare the value in the expected format in yaml (which is treated as json by the k8s APIs).

If a value is provided for the param, the default will not be used (i.e. there will be no behavior to merge the
default with the provided value, if for example the provided value specified some fields but not others).

Params example with default value:

```yaml
  params:
    - name: pull_remote
      description: JSON Schema has no "description" fields, so we'd have to include documentation about the structure in this field
      type: object
      properties:
        url: {
          type: string
        }
        path: {
          type: string
        }
      default:
        url: https://github.com/somerepo
        path: ./my/directory/
```

Results example:

```yaml
  results:
    - name: sdist
      description: JSON Schema has no "description" fields, so we'd have to include documentation about the structure in this field
      type: object
      properties:
        sha: {
          type: string
        }
        path: {
          type: string
        }
```

### Emitting object results

As described in
[TEP-0076 Array results and indexing](https://github.com/tektoncd/community/pull/477), we add support for writing json
content to `/tekton/results/resultName`, supporting strings, objects and arrays of strings.

For example, say we want to write to emit a built image's url and digest in a dictionary called `image`:

1. Write the following content to `$(results.image.path)`:

   ```json
   {"url": "gcr.io/somerepo/someimage", "digest": "a61ed0bca213081b64be94c5e1b402ea58bc549f457c2682a86704dd55231e09"}
   ```

2. This would be written to the pod termination message as escaped json, for example (with a string example included as
   well):

   ```
   message: '[{"key":"image","value":"{\"url\": \"gcr.io\/somerepo\/someimage\", \"digest\": \"a61ed0bca213081b64be94c5e1b402ea58bc549f457c2682a86704dd55231e09\"}","type":"TaskRunResult"},{"key":"someString","value":"aStringValue","type":"TaskRunResult"}]'
   ```

3. We would use the same
   [ArrayOrString type](https://github.com/tektoncd/pipeline/blob/1f5980f8c8a05b106687cfa3e5b3193c213cb66e/pkg/apis/pipeline/v1beta1/param_types.go#L89)
   (expanded to support dictionaries, and in TEP-0074, arrays) for task results, e.g. for the above example, the TaskRun
   would contain:

   ```yaml
     taskResults:
     - name: someString
       value: aStringValue
     - name: image
       value:
         url: gcr.io/somerepo/someimage
         digest: a61ed0bca213081b64be94c5e1b402ea58bc549f457c2682a86704dd55231e09
   ```

### Using objects in variable replacement

We add support for
[the JSONPath subscript operator](https://tools.ietf.org/id/draft-goessner-dispatch-jsonpath-00.html#name-jsonpath-examples)
for accessing "child" members of the object by name in variable replacement.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
...
spec:
  params:
    - name: gitrepo
      type: object
      properties:
        url: {}
        commitish: {}
...
tasks:
  - name: notify-slack-before
    params:
      - name: message
        value: "about to clone $(params.gitrepo.url) at $(params.gitrepo.commitish)"
  - name: clone-git
    runAfter: [ 'notify-slack' ]
    params:
      - name: gitrepo
        value: $(params.gitrepo[*])
    results:
      - name: cloned-gitrepo
        type: object
        properties:
          url: {}
          commitish: {}
    taskSpec:
      params:
        - name: gitrepo
          type: object
          properties:
            url: {}
            commitish: {}
      steps:
        - name: do-the-clone
          image: some-git-image
          args:
            - "-url=$(params.gitrepo.url)"
  - name: notify-slack-after
    params:
      - name: message
        value: "cloned $(tasks.cloned-git.results.cloned-gitrepo.url) at $(tasks.cloned-git.results.cloned-gitrepo.commitish)"
```

_This proposal does not include adding support for any additional syntax (though it could be added in the future!)._

#### Variable replacement with object params

**When providing values for objects** Task and Pipeline authors can provide an entire object as a value only when the
value is also an object (see [matching interface and extra keys](#matching-interfaces-and-extra-keys)) by using
[the same `[*]` syntax used to provide entire arrays](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#substituting-array-parameters)
.

In the above example:

```yaml
params:
  - name: gitrepo
    value: $(params.gitrepo[*])
```

**When providing values for strings**, Task and Pipeline authors can access individual attributes of an object param;
they cannot access the object as whole (we could add support for this later).

In the above example, within a Pipeline Task:

```yaml
value: "about to clone $(params.gitrepo.url) at $(params.gitrepo.commitish)"
```

In the above example, within a Task spec:

```yaml
- "-url=$(params.gitrepo.url)"
```

When populating a string field, It would be invalid (at least initially) to attempt to do variable replacement on the
entire `gitrepo` object (`$(params.gitrepo)`). If we choose to support this later we could potentially replace the value
with the json representation of the object directly.

#### Variable replacement with object results

#### Within a Task

Within the context of a Task, Task authors would continue to have access to the `path` attribute of a result (identified
by name) and would not have any additional variable replacement access to the keys.

In the above example:

```bash
cat /place/with/actual/cloned/gitrepo.json > $(results.cloned-gitrepo.path)
```

`$(results.cloned-gitrepo.path)` refers to the path at which to write the `clone-gitrepo` object as json (it does not
refer to an attribute of `cloned-gitrepo` called `path`, and even if `cloned-gitrepo` had a `path` attribute, there
would be no collision because variable replacement for individual attributes of the result is not supported within the
Task.

(See [emitting object reesults](#emitting-object-results) for more details.)

#### Within a Pipeline Task

Within the context of a Pipeline Task, the Pipeline author can refer to individual attributes of the object results of
other Tasks.

In the above example:

```yaml
value: "cloned $(tasks.cloned-git.results.cloned-gitrepo.url) at $(tasks.cloned-git.results.cloned-gitrepo.commitish)"
```

[As with params](#variable-replacement-with-object-params) only access to individual keys will be allowed initially.

#### Collisions with builtin variable replacement

Tekton provides builtin variable replacements which may one day conflict with the keys in a dictionary. Existing
variable replacements will not conflict (the closest candidate is `path`, as in `$(results.foo.path)` but since this is
only used in the context of writing Tasks results, there will be no conflict - see
[variable replacement with object params](#variable-replacement-with-object-params) for more detail).

But still, features we add in the future may conflict, for example if we added an optional params feature, we might
provide a variable replacement like `$params.foo.bound`. What if the `foo` param was an object with a key called `bound` ?

For example:

```yaml
results:
  - name: foo
    type: object
    properties:
      bound: {
        type: string
      }
```

[TEP-0080](https://github.com/tektoncd/community/blob/main/teps/0080-support-domainscoped-parameterresult-names.md#proposal)
added support for using `[]` syntax instead of `.` to support variables which are have names that include `.`. Resolving
the ambiguity here would only require using `$params.foo.bound` to refer to the built in variable replacement, and
`$params.foo["bound"]` to unambiguously refer to the key `bound` within `foo`. Other options include:

1. Do not allow keys to be defined which conflict with variable replacement
    * Con: this means that a Task which is perfectly fine today might break tomorrow if we introduce new variable
      replacement - in the above example, `foo.bound` is perfectly valid today and would be allowed but would suddenly
      stop working after the `bound` feature is introduced
2. Let the defined object override the variable replacement; i.e. in this case the built in replacement will not be
   available

## Test Plan

In addition to unit tests the implementation would include:

* At least one reconciler level integration test which includes an object param and an object result
* A tested example of a Task, used in a Pipeline, which:
    * Declares an object param
    * Emits an object result
    * In the Pipeline, another Task consumes a specific value from the object

## Design Evaluation

[See also the TEP-0076 Array results and indexing](https://github.com/tektoncd/community/pull/477) design evaluation.

* [Reusability](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability):
    * Pro: PipelineResources provided a way to make it clear what artifacts a Pipeline/Task is acting on, but
      [using them made a Task less resuable](https://github.com/tektoncd/pipeline/blob/main/docs/resources.md#why-arent-pipelineresources-in-beta)
      - this proposal introduces an alternative that does not involve making a Task less reusable (especially once
      coupled
      with [TEP-0044](https://github.com/tektoncd/community/blob/main/teps/0044-decouple-task-composition-from-scheduling.md))
* [Simplicity](https://github.com/tektoncd/community/blob/main/design-principles.md#simplicity)
    * Pro: Support for emitting object results builds on [TEP-0076](https://github.com/tektoncd/community/pull/477)
    * Pro: This proposal reuses the existing array or string concept for params
    * Pro: This proposal
      continues [the precedent of using JSONPath syntax in variable replacement](https://github.com/tektoncd/pipeline/issues/1393#issuecomment-561476075)
* [Flexibility](https://github.com/tektoncd/community/blob/main/design-principles.md#flexibility)
    * Pro: Improves support for structured interfaces which tools can rely on
    * Con: Although there is a precedent for including JSONPath syntax, this is a step toward including more hard coded
      expression syntax in the Pipelines API (without the ability to choose other language options)
    * Con: We're also introducing and committing to [JSON Schema](#why-json-schema)! Seems worth it for what we get tho
* [Conformance](https://github.com/tektoncd/community/blob/main/design-principles.md#conformance)
    * Supporting this syntax would be part of the conformance surface; the JSON Schema syntax is a bit verbose for
      simple cases (but paves hte way for the more complex cases we can support later, including letting Tasks express
      how to validate their own parameters)

## Drawbacks

[See also TEP-0076 Array results and indexing](https://github.com/tektoncd/community/pull/477) for more drawbacks.

* In the current form, this sets a precedent for pulling in more schema support ([why JSON Schema](#why-json-schema))
* This improves the ability to make assertions about Task interfaces but doesn't (explicitly) include workspaces at all.
  For example, say you had a “git” param for a pipeline containing a commitish and a url. This is likely going to be
  used to clone from git into a workspace, and there will be some guarantees that can be made about the data that ends
  up in the workspace (e.g. the presence of a .git directory). But there is no way of expressing the link between the
  workspace and the params.

## Alternatives

## Alternative #1:  Introduce a `schema` section specifically for the type schema

Instead of embedding the details of the type in the param/result definition, we could introduce a new `schema` section.

For example, instead of the proposed syntax where we allow a new value `object` for `type` and we add `properties`:

```yaml
params:
  - name: someURL
    type: string
  - name: flags
    type: array
  - name: sdist
    type: object
    properties:
      sha: { }
      path: { }
```

We could add an explicit new `schema` section:

```yaml
params:
  - name: someURL
    schema:
      type: string
  - name: flags
    schema:
      type: array
  - name: sdist
    schema:
      type: object
      properties:
        sha: { }
        path: { }
```

Pros

* It's very clear where the schema is defined; specifically which part of the Task/Pipeline spec is considered JSON
  Schema. In the current proposal the JSON Schema is mixed in with our own fields (specifically `name`).

Cons

* For simple types this is more verbose - once we allow more complex objects the extra level of indentation won't be as
  noticeable, but when defining simple types it feels unnecessary.
* If we go this route, we'll have to grapple with the question of what to do
  with [the existing `type` field](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-parameters).
  For example, if we add the syntax suggested here to the existing `type` syntax, their uses would look like:

  ```yaml
  params:
  - name: someURL
    type: string
  - name: flags
    type: array
  - name: sdist
    schema:
      type: object
      properties:
        sha: {
          type: string
        }
        path: {
          type: string
        }
  ```

  If we deprecated the type syntax and only used JSON Schema, the above would become very verbose:

  ```yaml
  params:
  - name: someURL
    schema:
      type: string
  - name: flags
    schema:
      type: array
  - name: sdist
    schema:
      type: object
      properties:
        sha: {
          type: string
        }
        path: {
          type: string
        }
  ```

## Alternative #2: Create a wrapper for JSON Schema

We could also go one step further and create a syntax which we translate into JSON Schema inside the controller, but is
customized to meet our needs, specifically:

- Add "descriptions" for keys
- [Use required by default (aka provide `optional` syntax)](#required-vs-optional-keys)

For example, instead of:

```yaml
params:
  - name: someURL
    description: ""
    schema:
      type: string
  - name: flags
    description: ""
    schema:
      type: array
  - name: sdist
    description: ""
    schema:
      type: object
      properties:
        sha: {
          type: string
        }
        path: {
          type: string
        }
```

We could have:

```yaml
params:
  - name: someURL
    description: ""
    type: string
  - name: flags
    description: ""
    type: array
  - name: sdist
    description: ""
    type: dict # use dict intead of object
    keys: # use keys instead of properties
      sha: {
        description: "" # add description section for each key
      }
      path: { }
  optional: [ ] # add "optional" and have required by default
```

But the big differences are cosmetic (dict vs object, keys vs properties), and with the current proposal we could
reasonably add our own `description` field into the existing property dictionaries (and `description` is already
supported by [Open API schema!](#why-json-schema).

## Alternative #3: Create our own syntax just for dictionaries

We could make our own syntax, specific to dictionaries, however if we later add more JSON Schema support we'd need to
revisit this. For example:

```yaml
 results:
   - name: sdist
     type: dict
     keys: [ 'sha', 'path' ]
```

This is clean and clear when we're talking about a dictionary of just strings, but what if we want to allow nesting,
e.g. array or dict values?

### More alternatives

1. Add support for nested types right away
1. Add complete JSON Schema support
1. Use something other than JSON Schema (or our own syntax proposed in Alternative #1) for expressing the
   object/dictionary structure It feels at this point like it's better to adopt a syntax that already handles these
   cases. (See [why JSON Schema](#why-json-schema))
1. Reduce the scope, e.g.:
    * Don't add support for grabbing individual items in a dictionary
        * We need this eventually for the future to be useful
    * Don't let dictionaries declare their keys (e.g. avoid bringing in JSON Schema)
        * Without a programmatic way to know what keys a dictionary needs/provides, we actually take a step backward in
          clarity, i.e. a list of strings has more information than a dictionary where you don't know the keys

## Upgrade & Migration Strategy

[As mentioned in TEP-0076 Array results and indexing](https://github.com/tektoncd/community/pull/477) this update will
be completely backwards compatible.

## Potential future work

Once Task and Pipeline authors are able to define object schemas for Tasks and Params, it would be very useful to:

1. Allow definition reuse instead of having to copy and paste them around
2. If we ship a known set of these with the Tekton Pipelines controller, they could define interfaces that tools such
   as [Tekton Chains](https://github.com/tektoncd/chains/blob/main/docs/config.md) could rely on and build around.

We could add a way to for users to define these, for example a new CRD such as:

```yaml
apiversion: tekton.dev/v1
kind: ParamSchema
metadata:
  name: GitRepo
spec:
  type: object # see question below
  properties:
    url: {
      type: string # for now, all values are strings, so we could imply it
    }
    path: { } # example of implying type: string
```

(Or support something like the above via a ConfigMap.)

Which could be used in Tasks and Pipelines:

```yaml
params:
  - name: pull_remote
    schemaRef: GitRepo
```

We could also pursue supporting [JSON Schema refs](http://json-schema.org/draft/2020-12/json-schema-core.html#ref).

_(Thanks to @wlynch for the suggestion and above example!)_

## Implementation Pull request(s)

TBD.

## References

- [pipelines#1393 Consider removing type from params (or _ really_ support types) ](https://github.com/tektoncd/pipeline/issues/1393)
