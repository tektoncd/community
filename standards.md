# Tekton Pipelines Contributor and Reviewer Expectations

The purpose of this doc is to:

* Outline for contributors what we expect to see in a pull request
* Establish a baseline for reviewers so they know at a minimum what to look for

Design: Most designs should be first proposed via an issue and possibly a
[TEP](https://github.com/tektoncd/community/tree/main/teps#tekton-enhancement-proposals-teps).
API changes should be evaluated according to
[Tekton Design Principles](https://github.com/tektoncd/community/blob/main/design-principles.md).

Each Pull Request is expected to meet the following expectations around:

* [Pull Request Description](#pull-request-description)
* [Release Notes](#release-notes)
* [Commits](#commits)
  * [Example Commit Message](#example-commit-message)
* [Docs](#docs)
* [Functionality](#functionality)
* [Content](#content)
* [Code](#code)
  * [Tests](#tests)
  * [Reconciler/Controller Changes](#reconcilercontroller-changes)

_See also [the Tekton review process](https://github.com/tektoncd/community/blob/main/process.md#reviews)._

## Pull request description

* Include a link to the issue being addressed, but describe the context for the reviewer
  * If there is no issue, consider whether there should be one:
    * New functionality must be designed and approved, may require a TEP
    * Bugs should be reported in detail
  * If the template contains a checklist, it should be checked off
  * Release notes filled in for user visible changes (bugs + features),
    or removed if not applicable (refactoring, updating tests) (maybe enforced
    via the [release-note Prow plugin](https://github.com/tektoncd/plumbing/blob/main/prow/plugins.yaml)).
    * Please refer the [release-note](#release-notes) section for more details.
* Add the related [TEP-XXXX] at the beginning of a PR subject line
  * Consider adding the links of the related TEP, Feature Request thread, and related other implementation PRs

## Release Notes

Release notes section of a PR must summarize the changes being proposed in that PR.
Release notes section is a very important part of the GitHub release page. The users,
operators, and contributors rely on a GitHub release page to get the list of PRs which were
part of a particular release.

Refer to the following set of questions to help fill the release-note section.

* Does this PR introduce a user-facing change (bugs, features, deprecations, or documentation)?
  * If no, just write "NONE" in the release-note block.
  * If yes, a release note is required:
    * Enter detailed release note in the release-note block. If the PR requires additional action from users switching to the new release, include the string "ACTION REQUIRED".
    * If this PR addresses a publicly known CVE, include the CVE number in the release notes
  * If unsure, include release note.
    * It's recommended to include release note explaining the changes in the PR.


### None Release Note

A very few PRs in a project generally qualifies for "NONE" release-note section. "NONE" release-note can be
included in a PR proposing a minor refactoring of the existing code or adding changes to
increase the test coverage.

````
```release-note
NONE
```
````

### Example Release Note

#### Poor Release Note

* NONE release-note is not acceptable for the PRs introducing a new feature:

````
```release-note
NONE
```
````

* The following release-note is not sufficient for a PR introducing a new feature.
A new feature generally has a TEP associated with it. The release note does not include a
TEP number or a reference to TEP. If a new feature PR is introducing new CRD or config specification
or a change in existing specifications, include a code block or summary of specifications change.

````
```release-note
Workspaces are propagated in embedded specifications without mutations.
```
````

A few examples of good release-notes:


* Reasonable release note for introducing a new feature:

````
```release-note
A taskRun/Run in a pipeline will have a new label `tekton.dev/memberOf=tasks` for the task defined under "tasks" section and `tekton.dev/memberOf=finally` for the task defined under "finally" section.
```
````

* Detailed release note for introducing a new feature:

````
```release-note
A taskRun/Run in a pipeline will have a new label `tekton.dev/memberOf=tasks` for the task defined under "tasks" section and `tekton.dev/memberOf=finally` for the task defined under "finally" section.
Refer to the TEP-00XX for more details.
```
````

## Commits

* Use the body to explain [what and why vs. how](https://chris.beams.io/posts/git-commit/#why-not-how).
  Link to an issue whenever possible and [aim for 2 paragraphs](https://www.youtube.com/watch?v=PJjmw9TRB7s),
  e.g.:
  * What is the problem being solved?
  * Why is this the best approach?
  * What other approaches did you consider?
  * What side effects will this approach have?
  * What future work remains to be done?
* Prefer one commit per PR. For multiple commits ensure each makes sense without the context of the others.
* As much as possible try to stick to these general formatting guidelines:
  * Separate subject line from message body.
  * Write the subject line using the "imperative mood" ([see examples](https://chris.beams.io/posts/git-commit/#imperative)).
  * Keep the subject to 50 characters or less.
  * Try to keep the message wrapped at 72 characters.
  * Check [these seven best practices](https://chris.beams.io/posts/git-commit/#seven-rules) for more detail.
* Add the related [TEP-XXXX] at the beginning of a commit subject line

### Example Commit Message

Here's a commit message example to work from that sticks to the spirit
of the guidance outlined above:

```
[TEP-XXXX] Add example commit message to demo our guidance

Prior to this message being included in our standards there was no
canonical example of an "ideal" commit message for devs to quickly copy.

Providing a decent example helps clarify the intended outcome of our
commit message rules and offers a template for people to work from. We
could alternatively link to good commit messages in our repos but that
requires developers to follow more links rather than just showing
what we want.
```

## Docs

* Include Markdown doc updates for user visible features
* Spelling and grammar should be correct
* Try to make formatting look as good as possible (use preview mode to check)
* Follow [content](https://github.com/tektoncd/website/blob/main/content/en/doc-con-content.md)
  and [formatting](https://github.com/tektoncd/website/blob/main/content/en/doc-con-formatting.md) guidelines
* Should explain thoroughly how the new feature works
* If possible, in addition to code snippets, include a reference to an end to end example
* Ensure that all links and references are valid

## Functionality

* It should be safe to cut a release at any time, i.e. merging this PR should not
  put us into an unreleasable state
    * When incrementally adding new features, this may mean that a release could contain
      a partial feature, i.e. the type specification only but no functionality
    * When introducing a partial feature, the documentation should include updates that
      indicate clearly that this functionality is not expected to work and point the reader
      toward how to follow progress (e.g. via an issue)

## Content

* Whenever logic is added that uses a container image that wasn’t used before, the image used should
  be configurable on the command line so that distributors can build images that meet their
  support and licensing requirements
* Refactoring should be merged separately from bug fixes and features
  * i.e. if you refactor as part of implementing something, commit it and merge it before merging the change
* Prefer small pull requests; if you can think of a way to break up the pull request into multiple, do it

## Code

* Tekton projects follow the [Go Style Guide](https://google.github.io/styleguide/go/).
* Reviewers are expected to understand the changes well enough that they would feel confident
  saying the understand what is changing and why:
  * Read through all the code changes
  * Read through linked issues and pull requests, including the discussions
* Prefer small well factored packages with unit tests
* Pass kubernetes and tekton client functions into functions that need them as params so
  they can be easily mocked in unit tests
* [Go Code Review comments](https://github.com/golang/go/wiki/CodeReviewComments)
  * All public functions and attributes have docstrings
  * Don’t panic
  * Error strings are not capitalized
  * Handle all errors ([gracefully](https://dave.cheney.net/2016/04/27/dont-just-check-errors-handle-them-gracefully))
    * When returning errors, add more context with `fmt.Errorf` and `%v`
  * Use meaningful package names (avoid util, helper, lib)
  * Prefer short variable names

### Tests

* New features (and often/whenever possible bug fixes) have one or all of:
  * Examples (i.e. yaml tests)
  * End to end tests
* When API changes are introduced (e.g. changes to  `_types.go` files) corresponding changes are made to:
  * Validation + validation tests
* Unit tests:
  * Coverage should remain the same or increase
  * Test exported functions only, in isolation:
    * Each exported function should have tests
    * Each test should only test one function at a time
    * If you find yourself wanting to test an unexported function, consider whether
      it would make sense to move the test into another package and export it
* Test code
  * When using cmp.Diff the argument order is always (want, got) and in the error message include (-want +got)
    (and/or use a lib like [PrintWantGot](https://github.com/tektoncd/pipeline/blob/main/test/diff/print.go))
  * Table driven tests: do not use the same test for success and fail cases if the logic is different
    (e.g. do not have two sets of test logic, gated with `wantErr`)

### Reconciler/Controller changes

For projects that have [CRD controllers](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/#custom-controllers)
(also known as "reconcilers"):

* Avoid adding functions to the reconciler struct
* Avoid adding functions to the reconciler package
* [Return an error if you want the change to be re-queued](https://github.com/knative/pkg/blob/master/injection/README.md#generated-reconciler-responsibilities),
  otherwise [return an permanent error](https://github.com/knative/pkg/blob/5358179e7499b1a3a4581d9d3673f391240ec86d/controller/controller.go#L516-L521)
* Be sparing with the number of "reconciler" level tests as these are a kind of integration test
  (they pull in all components in the reconciler) and tend to be slow (on the order of seconds)
