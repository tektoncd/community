# Tekton Release Cycles

## Support Policy

The Tekton project maintains four release branches for each project, created one every three months,
which results in a overall support window of approximately one year for each of these releases.

This approach means that Tekton supports **four** releases at any point in time, called long term
support (LTS) releases. Throughout the support period, patch releases may be created to resolve:

- CVEs (under the advisement of the Tekton Vulnerability Team)
- dependency issues (including base image updates)
- critical core component issues

Tekton is made of a collection of projects, and each project may define its own release cadence, as long as
this [support policy](#support-policy) is followed.

Examples:

- A project may release on a monthly basis, and maintain a release branch for every fourth release
- A project may release every four months, and maintain a release branch for the three most recent minor
  releases

Individual projects may provide short support windows for non-LTS major or minor releases, which may last
until the next major or minor release is available.

Note that the support policy is independent from the any API stability policy provided by projects.
If a release by mistake broke an API stability policy, during the support period that would justify
the creation a patch release to resolve the issue.

Deprecations are not affected by support: if a feature or API version is deprecated in a release, the
deprecation is effective immediately, for both LTS and non-LTS release. On the flip side, regular support
for the release is provided until the release EOL, regardless on any deprecation it may include.

## Release Numbers

Tekton uses [semantic versioning][semantic] to version its own releases. Release numbers are in the format
MAJOR.MINOR.PATCH `vX.Y.Z`. The [support policy](#support-policy) applies to MAJOR and MINOR releases alike.

## Release Tags and Branches

Every time a Tekton project produces a release, a new tag `vX.Y.Z` is created, as well as a new branch that
initially points to the git tag `vX.Y.Z`.

- Supported releases:
    - branch name: `release-vX.N-lts`
    - support window: until `release-vX.N+3`

- Any other major or minor release:
    - branch name: `release-vX.M`
    - support window: until `release-vX.M+1`

Once a release support window expires, the corresponding branch is deleted. Tags are never deleted.
It is recommended (but not mandatory) to make major releases coincide with supported ones.

## Milestones

Tekton projects may use [GitHub milestones][github-milestones] to plan their next release. This helps the
maintainer and reviewer teams to focus their work for the release and it gives users visibility on what they
may expect for the upcoming releases.

When used, milestone names must include the release number in `v<MAJOR>.<MINOR>` format.
Once a release is made the milestone is closed. Patch releases are not tracked as part of the milestone.

## Project Requirements

Project must include release documentation in a `releases.md` file, which must include:

- The release frequency adopted by the project
- The first release where this [support policy](#support-policy) applies
- A list of one year worth of releases. For each release:
    - Number, name, date released, link to [release notes][release-notes-guidelines]
    - End of life (EOL) date
    - List of patch releases, each with link to [release notes][release-notes-guidelines]

The document may include extra project-specific, user-facing release documentation.

## Nightly Builds

Tekton projects are encouraged to produce nightly builds, also called nightly releases.
Nightly builds are produced for the benefit of Tekton users and developers but are not supported
after they are produced. Users who rely on nightly builds must move to a newer nightly build or release to
pick up any required bugfix, security patch or new feature.

Tekton projects always strive to keep the main branch in a consistent and usable state, however it may be
possible for nightly builds to include partially implemented features and removal of deprecated features
that will be thoroughly documented in the next upcoming release.

The [plumbing][nightly-plumbing] repository contains the Tekton resources to be used to produce nightly
builds. The plumbing repository includes examples of [nightly-build pipelines][nightly-pipeline] that projects
may use to created their own. Nightly builds are triggered by [cronjobs][nightly-triggers] running
in the *dogfooding* cluster.

Nightly builds are not tagged in git. The container images associated to nightly builds are tagged.
The tag includes the date and short version of the git sha:

```shell
VERSION_TAG="v$(date +"%Y%m%d")-$(echo $GIT_SHA | cut -c 1-10)"
```

## Nightly releases

Tekton projects may decide to migrate from nightly builds to nightly releases, and use nightly releases to
replace other releases completely. If a projects decides to do so, it must still comply with the
[support policy](#support-policy), so the following requirements must be met:

- fully automated release notes associated to each nightly release
- the project must choose one nightly release every four months, give it a semantic version, create a release branch
  and support the release according to the [support policy](#support-policy)
- the project documentation on the [Tekton website]tekton-web] must include the latest nightly release plus all
  currently supported long term releases


[kube-releases]: https://kubernetes.io/releases/
[semantic]: https://semver.org/
[github-milestones]: https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones
[nightly-plumbing]: https://github.com/tektoncd/plumbing/tree/main/tekton/resources/nightly-release
[nightly-pipeline]: https://github.com/tektoncd/plumbing/tree/main/tekton/ci/cluster-interceptors/build-id/tekton
[nightly-triggers]: https://github.com/tektoncd/plumbing/tree/main/tekton/cronjobs/dogfooding/releases
[tekton-web]: https://tekton.dev/docs
[release-notes-guidelines]: https://github.com/tektoncd/community/blob/main/standards.md#release-notes