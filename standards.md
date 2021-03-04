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
* [Commits](#commits)
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
    or removed if not applicable (refactoring, updating tests) (may be enforced
    via the [release-note Prow plugin](https://github.com/tektoncd/plumbing/blob/main/prow/plugins.yaml))

## Commits

* Follow [commit messages best practices](https://chris.beams.io/posts/git-commit/):
  1. Separate subject from body with a blank line
  2. Limit the subject line to 50 characters
  3. Capitalize the subject line
  4. Do not end the subject line with a period
  5. Use the imperative mood in the subject line
  6. Wrap the body at 72 characters
  7. Use the body to explain what and why vs. how. Don't just link to an issue and
      [aim for 2 paragraphs](https://www.youtube.com/watch?v=PJjmw9TRB7s), e.g.:
      * What is the problem being solved?
      * Why is this the best approach?
      * What other approaches did you consider?
      * What side effects will this approach have?
      * What future work remains to be done?
* Prefer one commit per PR; if there are multiple commits, ensure each is
  self-contained and makes sense without the context of the others in the PR

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
    * When introducting a partial feature, the documentation should include updates that
      indicates clearly that this functionality is not expected to work and point the reader
      toward how to follow progress (e.g. via an issue)

## Content

* Whenever logic is added that uses a container image that wasn’t used before, the image used should
  be configurable on the command line so that distributors can build images that meet their
  support and licensing requirements
* Refactoring should be merged separately from bug fixes and features
  * i.e. if you refactor as part of implementing something, commit it and merge it before merging the change
* Prefer small pull requests; if you can think of a way to break up the pull request into multiple, do it

## Code

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
    (and/or use a lib like [PrintWantGot](https://github.com/tektoncd/pipeline/blob/master/test/diff/print.go))
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
