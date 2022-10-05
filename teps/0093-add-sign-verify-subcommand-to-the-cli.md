---
status: proposed
title: Add sign and verify subcommand to the CLI
creation-date: '2022-10-05'
last-updated: '2022-10-05'
authors:
- '@Yongxuanzhang'
- '@nadgowdas'
- '@lukehinds'
collaborators: []
---

# TEP-0093: Add sign and verify subcommand to the CLI

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
- [Design Details](#design-details)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This proposal aims at adding `sign` and `verify` to Tekton CLI to help Trusted Resources users to sign and verify Tekton Resources.


## Motivation

There is a growing open-source ecosystem around tekton [catalog](https://github.com/tektoncd/catalog) and [artifactHUB](https://artifacthub.io), where number of tasks/pipelines are made available ready-to-use in our CI/CD. These tasks provides commonly used functions like `git-clone`, `curl`, etc. And also includes vendor specific functions like `aws-cli`, `openshift-client`. Such a marketplace is essential in practicing DRY principle. But, as we are building such an open-distribution framework, we need to ensure task distribution is secure.

Objective in this proposal is to faciliate an easy and handy approach for task/pipeline providers to sign their files and for consumers to verify them using native `tkn cli` commands.

Also, this complements [TEP-0091](https://github.com/tektoncd/community/blob/main/teps/0091-trusted-resources.md). TEP-0091 proposes to apply verification at the controller and the signing is suggested to be implemented into Tekton CLI. This proposal suggests an CLI extension for developers to sign and verify tasks/pipelines YAML files.

### Goals

1. Add the ability to run `tkn {object} sign` and `tkn {object} verify` fom the CLI. `object` currently should support `task` and `pipeline`. `Sign` will take the private key and the resource yaml file, sign the resource object and attach signature to the annotation.
2. Support both key files and KMS key.
3. Support v1beta1 and v1 Task, Pipeline.

### Non-Goals

1. Keyless signing could be a future work
2. Integrate with Fulcio and Rekor could be future work
3. Store Signature to a remote storage
4. Sign and verify a list of files could be future work
5. Support resources other than v1beta1 Task and Pipeline could be future work
6. Distribution/Discovery of the public keys is out-of-scope and assumes it is already available for users

### Use Cases

**Catalog Users**: Catalog users consist of Tasks/Pipeline authors and users. For authors they can use tkn to sign their files, distribute and expose the public key to other users who want to use and verify. Other users can use tkn to verify the resources are not tampered with since they are signed by authors.

**Trusted Resources Users**: [TEP-0091](https://github.com/tektoncd/community/blob/main/teps/0091-trusted-resources.md) introduces the verification at pipeline controller but doesn't cover the signing. This tep can provide a tool for Trusted Resources Users to sign their resources.

### Requirements

* Signing a resource shouldn't change the `spec`, e.g. we should not call `Setdefaults` for these resources to add default values.
* The implementation shouldn't break the [security requirements](https://bestpractices.coreinfrastructure.org/en/projects/6510) of OpenSSF badge.

## Proposal

The `sign` and `verify` subcommands should be added to current `task` and `pipeline` commands.  Each subcommand has flags. Details will be discussed in next section.

## Design Details

### Command line specifications
**Sign:**
```shell
❯ tkn task sign --help
Sign Tekton Task

Usage:
tkn task sign [flags]

Examples:
 Sign a Task from yaml file and save the signed Task:
 tkn task sign examples/example-task.yaml  -K=cosign.key -f=signed.yaml

Flags:
  -h, --help        help for sign
  -K, --keyFile     private key file path
  -m, --kmsKey      kms key path
  -f, --targetFile  Filename of the signed file
```

**Verify:**
```shell
❯ tkn task verify --help
Verify Tekton Task

Usage:
tkn task verify [flags]

Examples:
 Verify a signed Task file:
 tkn task verify examples/signed.yaml  -K=cosign.pub

Flags:
  -h, --help        help for verify
  -K, --keyFile     public key file path
  -m, --kmsKey      kms key path
```

### Sign
To sign a resource file:
```bash
tkn task sign examples/example-task.yaml  -K=cosign.key -f=signed.yaml
```
Flags:

|  Flag | ShortFlag  |  Description  |
|---|---|---|
| keyFile  | K   |  private key file path |
| kmsKey  | m   | kms key path  |
| targetFile  |  f | Filename of the signed file  |

This will read private and unmarshal yaml files to get Tekton CRD (Task/Pipeline), signing function should sign the hashed bytes of the CRD, attach the base64 encoded signature to annotation with key as `tekton.dev/signature`.

**Note:** The resource shouldn't contain `tekton.dev/signature` before signing.

### Verify
To verify a file:
```bash
tkn task verify signed.yaml -K=cosign.pub -d=Task
```

|  Flag | ShortFlag  |  Description  |
|---|---|---|
| keyFile  | K   |  public key file path |
| kmsKey  | m   | kms key path  |

Logs in terminal should tell users whether verification succeed or not.

## Alternatives

1. Cosign cli
Cosign supports signing [tekton bundles](https://github.com/sigstore/cosign#tekton-bundles) and other type of data. But Cosign cli is out of Tekton ecosystem it would be better to have feature implemented into Tekton CLI.

2. tkn plugins
These functions can be stored in a separate repo and installed as tkn plugins. But that is not good for user experience.


## Implementation Plan

### Test Plan

- Unit test of `sign` and `verify`
- For the CLI, the tests should be similar to any other tekton command.


### Implementation Pull Requests



