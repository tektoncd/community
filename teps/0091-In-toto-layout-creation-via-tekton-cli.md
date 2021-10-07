---
status: proposed
title: In-toto Layout Creation via Tekton CLI
creation-date: '2021-10-07'
last-updated: '2021-10-07'
authors:
- '@pxp928'
---

# TEP-0091: In-toto Layout Creation via Tekton CLI

<!--
**Note:** When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the SIG that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly.  The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved.  Any TEP
marked as a `proposed` is a working document and subject to change.  You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused.  If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP.  Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/NNNN-TEP-template/README.md).

-->

<!--
This is the title of your TEP.  Keep it short, simple, and descriptive.  A good
title can help communicate what the TEP is and should be considered as part of
any review.
-->

<!--
A table of contents is helpful for quickly jumping to sections of a TEP and for
highlighting any additional information provided beyond the standard TEP
template.

Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-request-s)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This proposal adds to improve how tekton chains and in-toto can be used together to perform verification.
Currently Tekton Chains already produces the in-toto attestations for each taskruns. The next step to use
this attestation within in-toto is to produce a layout file that can be fed into `in-toto verify` to validate
the steps that each taskrun took. This proposal seeks to add a new command to Tekton CLI (via library) or third party tool that can be called on 
an existing task, taskrun, pipeline or pipelinerun and automatically create a specific layout file for ingestion by `in-toto verify`.


## Motivation

Currently there is a disconnect between the two tools. Having an automated way to create the layout file breaks the
barrier to entry. This new addition would allow users to use both Tekton Chains along with in-toto to verify their work.
Creating a layout file that can be used by in-toto is a non-trivial task. 

Example of a layout file that would be used by in-toto verify: https://github.com/in-toto/in-toto-golang/blob/master/certs/layout.tmpl


### Goals

Add a new CLI command or third party tool that would create a in-toto layout file based on a specifying a task, taskrun, pipeline or pipelinerun from within Tekton.
Determine the format of the layout file that both Tekton and In-toto communities can agree on and would work with `in-toto verify`.

POC has been created: [tkn-intoto-formatter](https://github.com/tap8stry/tkn-intoto-formatter). See below [References (optional)](#references-optional).

### Non-Goals

Nothing as of now.

### Use Cases (optional)

#### Use Case 1

Create in-toto layout file by using Tekton CLI from a pipelinerun:

```bash
$ tkn chains layout tutorial-pipeline-run-1-r-nwl5x <path to store layout>
```

or

Create via third party:

```bash
% tkn-intoto-formatter convert -i sample-pipeline/pr-bom.yaml -f ./pr-bom-attest.json
```

This command would create a layout file similar to this (work in progress - not final format and missing information):

```json
{
    "signed": {
        "_type": "run-image-pipelinerun",
        "steps": [
            {
                "_type": "step",
                "pubkeys": null,
                "expected_command": null,
                "threshold": 0,
                "name": "clone",
                "expected_materials": [
                    [
                        "ALLOW",
                        "pkg:docker/tekton-releases/github.com/tektoncd/pipeline/cmd/git-init@sha256:c0b0ed1cd81090ce8eecf60b936e9345089d9dfdb6ebdd2fd7b4a0341ef4f2b9?repository_url=gcr.io"
                    ],
                    [
                        "DISALLOW",
                        "*"
                    ]
                ],
                "expected_products": null
            },
            {
                "_type": "step",
                "pubkeys": null,
                "expected_command": [
                    "--env-vars"
                ],
                "threshold": 0,
                "name": "prepare",
                "expected_materials": [
                    [
                        "ALLOW",
                        "pkg:docker/bash@sha256:b208215a4655538be652b2769d82e576bc4d0a2bb132144c060efc5be8c3f5d6"
                    ],
                    [
                        "DISALLOW",
                        "*"
                    ]
                ],
                "expected_products": null
            },
            {
                "_type": "step",
                "pubkeys": null,
                "expected_command": [
                    "/cnb/lifecycle/creator",
                    "-cache-dir=$(workspaces.cache.path)",
                    "-cache-image=ttl.sh/30306a73f25d8293fa234d5250761d25/slsapoc-cache",
                    "-layers=/layers",
                    "-platform=/platform",
                    "-report=/layers/report.toml",
                    "-previous-image=ttl.sh/30306a73f25d8293fa234d5250761d25/slsapoc",
                    "ttl.sh/30306a73f25d8293fa234d5250761d25/slsapoc"
                ],
                "threshold": 0,
                "name": "create",
                "expected_materials": [
                    [
                        "ALLOW",
                        "pkg:docker/cnbs/sample-builder@sha256:6c03dd604503b59820fd15adbc65c0a077a47e31d404a3dcad190f3179e920b5"
                    ],
                    [
                        "DISALLOW",
                        "*"
                    ]
                ],
                "expected_products": null
            },
            {
                "_type": "step",
                "pubkeys": null,
                "expected_command": null,
                "threshold": 0,
                "name": "results",
                "expected_materials": [
                    [
                        "ALLOW",
                        "pkg:docker/bash@sha256:b208215a4655538be652b2769d82e576bc4d0a2bb132144c060efc5be8c3f5d6"
                    ],
                    [
                        "DISALLOW",
                        "*"
                    ]
                ],
                "expected_products": null
            }
        ],
        "inspect": null,
        "keys": {},
        "expires": "2021-12-22T20:34:35Z",
        "readme": ""
    },
    "signatures": null
}
```

#### Use Case 2

Create in-toto layout file by using Tekton CLI from a pipeline:

```bash
$ tkn chains layout tutorial-pipeline <path to store layout>
```

or

Create via third party:

```bash
% tkn-intoto-formatter convert -i sample-pipeline/pipeline-bom.yaml -f ./pipeline-bom-attest.json
```

This command would create a layout file similar to this (work in progress - not final format and missing information):

```json
{
    "_type": "pipeline-with-parameters",
    "steps": [
        {
            "_type": "pylint",
            "pubkeys": null,
            "expected_command": [],
            "threshold": 0,
            "name": "lint-repo",
            "expected_materials": [
                [
                    "in-resource-name=workspace",
                    "in-resource=my-repo",
                    "in-resource-from="
                ],
                [],
                []
            ],
            "expected_products": null
        },
        {
            "_type": "make-test",
            "pubkeys": null,
            "expected_command": [],
            "threshold": 0,
            "name": "test-app",
            "expected_materials": [
                [
                    "in-resource-name=workspace",
                    "in-resource=my-repo",
                    "in-resource-from="
                ],
                [],
                []
            ],
            "expected_products": null
        },
        {
            "_type": "kaniko-build-app",
            "pubkeys": null,
            "expected_command": [
                "run-after=test-app"
            ],
            "threshold": 0,
            "name": "build-app",
            "expected_materials": [
                [
                    "in-resource-name=workspace",
                    "in-resource=my-repo",
                    "in-resource-from="
                ],
                [
                    "out-resource-name=image",
                    "out-resource=my-app-image"
                ],
                []
            ],
            "expected_products": null
        },
        {
            "_type": "kaniko-build-frontend",
            "pubkeys": null,
            "expected_command": [
                "run-after=test-app"
            ],
            "threshold": 0,
            "name": "build-frontend",
            "expected_materials": [
                [
                    "in-resource-name=workspace",
                    "in-resource=my-repo",
                    "in-resource-from="
                ],
                [
                    "out-resource-name=image",
                    "out-resource=my-frontend-image"
                ],
                []
            ],
            "expected_products": null
        },
        {
            "_type": "deploy-kubectl",
            "pubkeys": null,
            "expected_command": [],
            "threshold": 0,
            "name": "deploy-all",
            "expected_materials": [
                [
                    "in-resource-name=my-app-image",
                    "in-resource=my-app-image",
                    "in-resource-from=build-app",
                    "in-resource-name=my-frontend-image",
                    "in-resource=my-frontend-image",
                    "in-resource-from=build-frontend"
                ],
                [],
                []
            ],
            "expected_products": null
        }
    ],
    "inspect": null,
    "keys": null,
    "expires": "",
    "readme": ""
}
```

#### Use Case 3

Create in-toto layout file by using Tekton CLI from a taskrun:

```bash
$ tkn chains layout tutorial-taskrun <path to store layout>
```

or

Create via third party:

```bash
% tkn-intoto-formatter convert -i sample-pipeline/taskrun-bom.yaml -f ./taskrun-bom-attest.json
```

This command would create a layout file similar to this (work in progress - not final format and missing information):

```json
{
    "signed": {
        "_type": "cache-image-pipelinerun-b9qkl-r-sjdrq-build-trusted-jln9g",
        "steps": [
            {
                "_type": "step",
                "pubkeys": null,
                "expected_command": [
                    "--env-vars"
                ],
                "threshold": 0,
                "name": "prepare",
                "expected_materials": [
                    [
                        "ALLOW",
                        "pkg:docker/bash@sha256:b208215a4655538be652b2769d82e576bc4d0a2bb132144c060efc5be8c3f5d6"
                    ],
                    [
                        "DISALLOW",
                        "*"
                    ]
                ],
                "expected_products": [
                    [
                        "ALLOW",
                        "ttl.sh/61c1d13f8c912e4ec4d545244a29fa4a/slsapoc"
                    ]
                ]
            },
            {
                "_type": "step",
                "pubkeys": null,
                "expected_command": [
                    "/cnb/lifecycle/creator",
                    "-cache-dir=$(workspaces.cache.path)",
                    "-cache-image=ttl.sh/61c1d13f8c912e4ec4d545244a29fa4a/slsapoc-cache",
                    "-uid=1000",
                    "-gid=1000",
                    "-layers=/layers",
                    "-platform=/platform",
                    "-report=/layers/report.toml",
                    "-process-type=web",
                    "-previous-image=ttl.sh/61c1d13f8c912e4ec4d545244a29fa4a/slsapoc",
                    "ttl.sh/61c1d13f8c912e4ec4d545244a29fa4a/slsapoc"
                ],
                "threshold": 0,
                "name": "create",
                "expected_materials": [
                    [
                        "ALLOW",
                        "pkg:docker/cnbs/sample-builder@sha256:6c03dd604503b59820fd15adbc65c0a077a47e31d404a3dcad190f3179e920b5"
                    ],
                    [
                        "DISALLOW",
                        "*"
                    ]
                ],
                "expected_products": [
                    [
                        "ALLOW",
                        "ttl.sh/61c1d13f8c912e4ec4d545244a29fa4a/slsapoc"
                    ]
                ]
            },
            {
                "_type": "step",
                "pubkeys": null,
                "expected_command": null,
                "threshold": 0,
                "name": "results",
                "expected_materials": [
                    [
                        "ALLOW",
                        "pkg:docker/bash@sha256:b208215a4655538be652b2769d82e576bc4d0a2bb132144c060efc5be8c3f5d6"
                    ],
                    [
                        "DISALLOW",
                        "*"
                    ]
                ],
                "expected_products": [
                    [
                        "ALLOW",
                        "ttl.sh/61c1d13f8c912e4ec4d545244a29fa4a/slsapoc"
                    ]
                ]
            }
        ],
        "inspect": [
            {
                "_type": "Inspect",
                "run": [
                    ""
                ],
                "name": "prepare",
                "expected_materials": null,
                "expected_products": null
            },
            {
                "_type": "Inspect",
                "run": [
                    ""
                ],
                "name": "create",
                "expected_materials": null,
                "expected_products": null
            },
            {
                "_type": "Inspect",
                "run": [
                    ""
                ],
                "name": "results",
                "expected_materials": null,
                "expected_products": null
            }
        ],
        "keys": {},
        "expires": "2021-12-23T08:34:17Z",
        "readme": ""
    },
    "signatures": null
}
```

#### Use Case 4

Create in-toto layout file by using Tekton CLI from a task:

```bash
$ tkn chains layout tutorial-task <path to store layout>
```

or

Create via third party:

```bash
% tkn-intoto-formatter convert -i sample-pipeline/task-bom.yaml -f ./task-bom-attest.json
```

This command would create a layout file similar to this (work in progress - not final format and missing information):

```json
{
    "_type": "print-date",
    "steps": [
        {
            "_type": "print-date-unix-timestamp",
            "pubkeys": null,
            "expected_command": [
                "script: #!/usr/bin/env bash\ndate +%s | tee $(results.current-date-unix-timestamp.path)\n"
            ],
            "threshold": 0,
            "name": "print-date-unix-timestamp",
            "expected_materials": [
                [
                    "image : bash:latest"
                ]
            ],
            "expected_products": null
        },
        {
            "_type": "print-date-human-readable",
            "pubkeys": null,
            "expected_command": [
                "script: #!/usr/bin/env bash\ndate | tee $(results.current-date-human-readable.path)\n"
            ],
            "threshold": 0,
            "name": "print-date-human-readable",
            "expected_materials": [
                [
                    "image : bash:latest"
                ]
            ],
            "expected_products": null
        }
    ],
    "inspect": null,
    "keys": null,
    "expires": "",
    "readme": ""
}
```

## Requirements

Before final implementation, need to determine format of the in-toto layout that is
accepted by both the Tekton community and the In-toto community.


## Proposal

Via Tekton CLI

```shell
Manage Tekton Chains

Usage:
tkn chains [flags]
tkn chains [command]

Available Commands:
  layout      Print In-toto layout for a specific pipelinerun

Flags:
  -h, --help       help for chains
  -C, --no-color   disable coloring (default: false)

Use "tkn chains [command] --help" for more information about a command.
```

Via third party tool:

```shell
% tkn-intoto-formatter -h
tkn-intoto-formatter is tool to manage various attestation functions, including
		conversion to intoto format and comparisons.

Usage:
  tkn-intoto-formatter [command]

Available Commands:
  completion  generate the autocompletion script for the specified shell
  convert     converts yaml tekton spec to specified format
  help        Help about any command
  version     tkn-intoto-formatter version

Flags:
      --config string   config file (default is $HOME/.tkn-intoto-formatter.yaml)
  -h, --help            help for tkn-intoto-formatter
  -t, --toggle          Help message for toggle

Use "tkn-intoto-formatter [command] --help" for more information about a command.
```

### Notes/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

### Risks and Mitigations

None.
<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

### User Experience (optional)

Adding this new proposed feature would allow for users to use tekton chains in-conjunction with in-toto.


### Performance (optional)

None.

## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable.  This may include API specs (though not always
required) or even code snippets.  If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->

## Test Plan

Unit testing along with testing with `in-toto verify` to ensure that the layout file and the attestation created by taskruns will result in pass for verification.

## Design Evaluation

None.

## Drawbacks

None.

## Alternatives

Alternative is to create a layout file by hand for each pipelinerun, pipeline, taskrun or task. That can be time consuming and prone to error.

## Infrastructure Needed (optional)

None.

## Upgrade & Migration Strategy (optional)

None.

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References (optional)

POC has been started in a [tkn-intoto-formatter](https://github.com/tap8stry/tkn-intoto-formatter).

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
