---
title: Provide Shell-Escaped Parameters
authors:
  - "@coryrc"
creation-date: 2020-09-15
last-updated: 2020-09-15
status: proposed
---

# TEP-0017 Provide Shell-Escaped Parameters

## Table of Contents

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
    - [Story 1](#story-1)
    - [Story 2](#story-2)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [References](#references)
<!-- /toc -->

## Summary

It is difficult to safely use parameters in a `script:` scalar. This TEP proposes
offering a shell-escaped version of every parameter.

## Motivation

- More concise than the current workarounds
- Help users create more robust Tasks by default
- More clearly expresses intent

### Goals

Provide a way to place parameters directly into the default `script:` without being
interpreted by the shell.

### Non-Goals

1. Prevent purposeful interpretation of parameters when intended
2. Work with shells which are not the default for the `script:`
3. Be perfectly secure against arbitrary data

## Requirements

## Proposal

In a Task or Pipeline, for each parameter `foo`, provide `$(params.foo.shell-escaped)`.

This variable shall be escaped according to `printf '%q'` rules as used in bash.
For example, the literal string `Hello '\!"` becomes `Hello\ \'\\\!\"`. A script
which ran `echo $(params.foo.shell-escaped)` would print the literal string. The
escaped value would do the wrong thing when placed inside double or single quotes.

Support Bourne, Bourne-Again, Busybox, and Debian Almquist shells against
injection, but don't purposefully prevent its usage in other scenarios. This
does not require runtime analysis.

### User Stories

#### Story 1

My Task allows users to specify a destination filename. The user could pass
valid file names containing any of ` <>|\!*?;&"'` (or more) which would be
impossible to robustly address all possibilities when used directly in the
script. For example, single-quoting parameters could not protect against
`'; rm -fR *;'`.

#### Story 2

My Task has a `script:` to perform some function and I wish the user to be able
to provide their own script to be called by my script. The most concise way to
write my Task is to include the line:

```
printf '%s' $(params.foo.shell-escaped) > included-script.sh
```

### Risks and Mitigations

We may not have the resources to exhaustively test and security-harden this feature.

## Design Details

If the parameter type is an array, it will fail validation.

## Test Plan

Unit tests checking behavior against a set of strings generated from bash's
`printf '%q'`.

An e2e TaskRun checking a couple parameters work as expected.

## Drawbacks

More code is added to Tekton and must be supported.

## Alternatives

There are existing workarounds:

1. Place the value into an environment variable, explicitly or implicitly. I am
unsure if this is safe for all possible valid inputs but I have not been able to
break it. We should ensure any implicit environment variables cannot be any
special name (i.e. LD_PRELOAD); a `TKN_` prefix would probably be sufficient.

   ```
   steps:
    - env:
        - name: SCRIPT_CONTENTS
          value: $(params.script)
      script: |
        printf '%s' "${SCRIPT_CONTENTS}" > input-script.sh
        chmod +x input-script.sh
        cd "$(params.package)"
        runner.sh /input-script
   ```

2. Use it as an argument in a separate step. There are limits to argument size
which could be met and break things, but that is a rather high number.

```yaml
steps:
  - command:
    - executable-which-writes-args-to-a-file
  - args:
    - /tekton/workspace/some-file
    - $(params.script)
```

3. The parameters could also be provided in the same way results are supplied:
`/tekton/parameters/in` could be a file with the exact contents. I believe, in
bash at least, `command "$(cat /tekton/parameters/in)"` is as safe as the
environment variable approach.

Environment variables and files have the downside of possible hidden
dependencies in the image executables.

4. Alternative 1 could be made more concise by providing the expansion
`$(params.in.env)`; when used, the parameter's value is placed in an arbitrary
environment variable whose name is provided by that expansion. i.e.

```yaml
steps:
   script: |
        printf '%s' "${$(params.script.env)}" > input-script.sh
```

This name wouldn't be limited to scripts either and could be supplied as an
arg to any command, though the use case for that is very limited.

5. Keep being unsafe. For example, is param `in` is `'; rm -fR /;` and used:

```yaml
steps:
   script: |
        printf '%q' '$(params.in)'
```

it'll expand to `printf '%q' ''; rm -fR /;` deleting from the root, though you
can imagine worse things it could do.

## References

[Provide shell-escaped parameters for `script:`](https://github.com/tektoncd/pipeline/issues/3226)
