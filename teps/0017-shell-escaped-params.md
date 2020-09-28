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

Support Bourne, Bourne-Again, Busybox, and Debian Almquist shells against
injection, but don't purposefully prevent its usage in other scenarios.

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
printf '%s' "$(params.foo)" > included-script.sh
```

### Risks and Mitigations

We may not have the resources to exhaustively test and security-harden this feature.

## Design Details

Arrays will be treated as flattened strings.

## Test Plan

Unit tests checking behavior against a set of strings generated from bash's
`printf '%q'`.

An e2e TaskRun checking a couple parameters work as expected.

## Drawbacks

More code is added to Tekton and must be supported.

## Alternatives

There are existing workarounds:

1. Place the value into an environment variable. I am unsure if this is safe for
all possible valid inputs.

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
which could be met and break things.

```yaml
steps:
  - command:
    - executable-which-writes-args-to-a-file
  - args:
    - /tekton/workspace/some-file
    - $(params.script)
```

The parameters could also be provided in the same way results are supplied:
`/tekton/parameters/in` could be a file with the exact contents. I believe, in
bash at least, `command "$(cat /tekton/parameters/in)"` is as safe as the
environment variable approach.

## References

[Provide shell-escaped parameters for `script:`](https://github.com/tektoncd/pipeline/issues/3226)
