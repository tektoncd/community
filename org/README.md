# Tektoncd Github Organization

This directory contains the configuration of the Tektoncd Github organization,
including GitHub maintainer and collaborator teams.
To add or remove members and admins, make changes to this file.

This system uses [peribolos](https://github.com/kubernetes/test-infra/tree/master/prow/cmd/peribolos)
to manage the org configuration.

Changes to this configuration are applied automatically via a GitHub trigger:

* https://github.com/tektoncd/plumbing/tree/main/tekton/resources/org-permissions

## Requirements

Feel free to open issues, comment, open pull requests or propose designs whether you
are a member of the tektoncd org or not!

If you are regularly contributing to repos in tektoncd, then you can become a
member of the Tekton GitHub organization in order to have tests run against your
pull requests without requiring [`ok-to-test`](process.md#prow-commands).
Being part of the org also makes it possible to have issues assigned.

To be eligible to become a member of the org you must (note that this is at the
discretion of [the governing board members](../governance.md)) do both of:

* Opened 5 pull requests against projects in tektoncd
* Reviewed 5 pull requests against projects in tektoncd

OR you can be endorsed by existing contributors (e.g. if you are joining a team that
is working on Tekton).
