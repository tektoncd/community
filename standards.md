# Tekton Pipelines Contributor and Reviewer Expectations

The purpose of this doc is to:

* Outline for contributors what we expect to see in a pull request
* Establish a baseline for reviewers so they know at a minimum what to look for

Design: Most designs should be first proposed via an issue and possibly a
[TEP](https://github.com/tektoncd/community/tree/main/teps#tekton-enhancement-proposals-teps).
API changes should be evaluated according to
[Tekton Design Principles](https://github.com/tektoncd/community/blob/main/design-principles.md).

Pull request reviewers are expected to meet [reviewer responsibilities](#reviewer-responsibilities).

Each Pull Request is expected to meet the following expectations around:

* [Pull Request Description](#pull-request-description)
* [Release Notes](#release-notes)
* [Commit Messages](#commits)
  * [Example Commit Message](#example-commit-message)
* [Small Pull Requests](#small-pull-requests)
* [Incremental Feature Development](#incremental-feature-development)
* [Docs](#docs)
* [Functionality](#functionality)
* [Content](#content)
* [Code](#code)
  * [Go packages](#go-packages)
  * [Tests](#tests)
  * [Reconciler/Controller Changes](#reconcilercontroller-changes)

_See also [the Tekton review process](https://github.com/tektoncd/community/blob/main/process.md#reviews)._

## Reviewer Responsibilities

* Reviewers are expected to understand the changes well enough that they would feel confident
  saying they understand what is changing and why:
  * Read through all the code changes
  * Read through linked issues and pull requests, including the discussions

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
* Add the Milestones to the pull request or the issue
  * For tracking the status of each Milestone, please link to the Milestones if the pull request or the issue targets specific releases.

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
* If a feature is implemented incrementally, use a release note only when it is complete and ready to be used
  * See [Incremental Feature Development](#incremental-feature-development) for more info

### None Release Note

A very few PRs in a project generally qualifies for "NONE" release-note section. "NONE" release-note can be
included in a PR proposing a minor refactoring of the existing code or adding changes to
increase the test coverage.

````
```release-note
NONE
```
````

### Example Release Notes

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

#### Good Release Notes


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

While commit messages explain what changes are being made to the code and why, good release notes should explain the impact on the user.
For example, if your commit message title is "Add resolvers deployment, with release and e2e integration",
a great release note could be:

````
```release-note
action required: The separate Resolutions project has been folded into Pipeline. If currently using Resolution, remove the tekton-remote-resolution namespace before upgrading and installing the new "resolvers.yaml". 
```
````

## Commit Messages

* Use the body to explain [what and why vs. how](https://chris.beams.io/posts/git-commit/#why-not-how).
  Link to an issue whenever possible and [aim for 2 paragraphs](https://www.youtube.com/watch?v=PJjmw9TRB7s),
  e.g.:
  * What is the problem being solved?
  * Why is this the best approach?
  * What other approaches did you consider?
  * What side effects will this approach have?
  * What future work remains to be done?
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

## Small Pull Requests

* Small pull requests that make a single, self-contained change are easier to review and easier to roll back or backport.
  * If you can think of a way to break up a pull request into smaller changes, do it
* Tests and documentation (where applicable) should always be part of the same pull request when introducing a change
* Use one commit per PR unless there is a strong reason not to
  * For multiple commits, ensure each makes sense without the context of the others.
* Refactoring should be merged before bug fixes and features
  * If you refactor as a prerequisite that will simplify or enable your new changes,
  commit and merge the refactor before merging your new changes

## Incremental Feature Development

* New features and API fields should be gated by feature flags.
* Features may be implemented incrementally to keep pull requests small.
* When introducing a partial feature, the documentation should include updates that
  indicate clearly that this functionality is not expected to work and point the reader
  toward how to follow progress (e.g. via an issue)
* For example, you could split a new feature into a PR adding new API fields, and a PR implementing those fields.
  * The first PR would have a commit title like "TEP-XXX: Add field XYZ to API", and no release notes.
  It would document these fields, including a sentence like "This field is under development and not yet functional.
  See issue #1234 for more information."
  * The second PR would have a commit title like "TEP-XXX: Implement support for field XYZ". It would contain release
  notes explaining the feature and remove documentation references to the feature being under development.

## Docs

* Include Markdown doc updates for user visible features
* Spelling and grammar should be correct
* Try to make formatting look as good as possible (use preview mode to check)
* Follow [content](https://github.com/tektoncd/website/blob/main/content/en/doc-con-content.md)
  and [formatting](https://github.com/tektoncd/website/blob/main/content/en/doc-con-formatting.md) guidelines
* Should explain thoroughly how the new feature works
* If possible, in addition to code snippets, include a reference to an end to end example
* Ensure that all links and references are valid

## Content

* Whenever logic is added that uses a container image that wasn’t used before, the image used should
  be configurable on the command line so that distributors can build images that meet their
  support and licensing requirements

## Code

* Tekton projects follow the [Go Style Guide](https://google.github.io/styleguide/go/) and [Effective Go](https://go.dev/doc/effective_go).
* Pass kubernetes and tekton client functions into functions that need them as params so
  they can be easily mocked in unit tests
* [Go Code Review comments](https://github.com/golang/go/wiki/CodeReviewComments)
  * All public functions and attributes have docstrings
  * Don’t panic
  * Error strings are not capitalized
  * Handle all errors ([gracefully](https://dave.cheney.net/2016/04/27/dont-just-check-errors-handle-them-gracefully))
    * When returning errors, add more context with `fmt.Errorf` and `%v`
  * Prefer short variable names

### Go packages

* Prefer small, well-factored packages with unit tests
* Use meaningful package names (avoid util, helper, lib). See https://go.dev/blog/package-names
* Only export functions that provide a meaningful API for consumers of the package
* All exported functions should have tests
  * Test exported functions only, since these are the functions package consumers will use.
    If you find yourself wanting to test an unexported function, consider whether
    it would make sense to move the test into another package and export it,
    or to refactor the package so that tests use the same functions as package importers
  * If your package is named "foo", prefer putting tests in a "foo_test" package in the same folder
    to ensure that only exported functions are tested

### Tests

* New features (and often/whenever possible bug fixes) have one or all of:
  * Examples (i.e. yaml tests)
  * End to end tests
* When API changes are introduced (e.g. changes to  `_types.go` files) corresponding changes are made to:
  * Validation + validation tests
* Unit tests
  * Coverage should remain the same or increase
  * Each test should only test one function at a time
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
