---
title: "Enhance Tekton Results CLI"
tep-number: "0160"
authors:
  - "@divyansh42"
status: "proposed"
creation-date: "2025-02-11"
last-updated: "2025-03-13"
---

# TEP-0160:  Enhance Tekton Results CLI for Improved Usability and Integration

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
  - [Functional Requirements](#functional-requirements)
  - [Non-Functional Requirements](#non-functional-requirements)
- [Proposal](#proposal)
- [Design Details](#design-details)
  - [Commands](#commands)
  - [Architecture](#architecture)
  - [Dependencies](#dependencies)
- [Alternatives Considered](#alternatives-considered)
- [Impact](#impact)
  - [Backward Compatibility](#backward-compatibility)
  - [Security Considerations](#security-considerations)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
- [References](#references)
<!-- /toc -->

## Summary

`Tekton Results` provides a mechanism to store and query the execution history of `PipelineRuns` and `TaskRuns`. However, the [existing CLI](https://github.com/tektoncd/results/tree/main/pkg/cli) for interacting with Results is not user-friendly. This proposal introduces a dedicated `CLI tool` that simplifies querying and managing Tekton Results, allowing users to retrieve, inspect, and analyze results efficiently. Additionally, this new CLI can be used as a standalone tool or as a plugin to the `tkn` CLI, ensuring seamless integration with existing Tekton workflows.

## Motivation

Currently, Tekton users lack a streamlined way to interact with `PipelineRun` and `TaskRun` stored in Tekton Results. Tekton CLI (`tkn`)  does not natively support fetching historical execution data from the `Results API`. Users must manually query the API, which can be inefficient and complex. Additionally, an existing CLI for interacting with Tekton Results does exist, but it is not very useful due to its limited functionality, lack of intuitive commands, and suboptimal user experience.

### Goals

- Provide a user-friendly CLI for interacting with Tekton Results.
- Improve accessibility and usability over the existing CLI.
- Enable users to retrieve and analyze PipelineRun and TaskRun results efficiently.
- Ensure authentication mechanisms are secure and easy to configure.
- Allow the CLI to function both as a standalone tool and as a plugin to tkn CLI.

### Non-Goals

- This proposal is not intended to modify the archived PipelineRuns and TaskRuns.
- This proposal doesn't explore possible deep integration with tkn (e.g. transparently query results when doing a `tkn pr list`), it would be another proposal later once we are happy with this CLI.

### Use Cases

- As a `Developer`, I want to `list` my past PipelineRuns and TaskRuns without writing custom API queries.
- As a `Tekton admin`, I want to `describe` specific runs to debug failures.
- As a `DevOps engineer`, I want to `fetch logs` of past runs.
- As a `Tekton user`, I want to use the CLI as a plugin within `tkn` to keep all pipeline-related commands under a single tool.

## Requirements

### Functional Requirements

- Retrieve a `list` of PipelineRuns and TaskRuns from Tekton Results.
- Describe a `specific` PipelineRun or TaskRun with details.
- Fetch `logs` of a PipelineRun or TaskRun.
- Authenticate with the `Tekton Results API` using token-based authentication.
- Support filtering results based on the flags passed.
- Allow users to paginate through results interactively, ensuring efficient navigation through large datasets.

### Non-Functional Requirements

- Consistent command syntax, following `tkn` CLI conventions.
- Formatted output, similar to the tkn CLI.
- Provide clear and actionable `error messages`.
- Support partial API response feature
- Support fetching results in the paginated form using `page_size` and `page_token` 

## Proposal

This proposal introduces a new CLI tool, `tkn-results`, designed to simplify interaction with Tekton Results. The CLI will provide commands to list, describe, and retrieve logs for `PipelineRuns` and `TaskRuns` stored in the Results API. Additionally, it will include authentication support to ensure secure access. The goal is to improve usability and efficiency over the existing CLI while maintaining a familiar command structure for Tekton users. The CLI will also be designed to work as a `plugin` to `tkn`, allowing users to execute commands seamlessly from within their existing Tekton CLI environment.

## Design Details

### Commands

#### Configuration

The configuration will allow users to provide the following options:
- **Host**: The host address for the client to connect.
- **Token**: The authentication token for secure API access.
- **API Path**: The specific API endpoint path.
- **Skip TLS verification**: Skip TLS verification for the API access (default: false)

These values can be automatically fetched and will have default values when possible.

```sh
tkn-results config set        # Set authentication and configuration parameters
tkn-results config reset      # Reset the configuration to default values
tkn-results config view       # View the current configuration
```

##### **Global Flags**
- `--kubeconfig`: Provide a custom kubeconfig file instead of using the default one (default: $HOME/.kube/config).
- `--context`: The name of the kubeconfig context to use (default: kubectl config current-context).
- `--namespace`: The namespace to use (default: from $KUBECONFIG).
- `--host`: The host address for the client to connect
- `--token`: The Bearer token for authentication to the API server
- `--api-path`: The specific API end point to use
- `--insecure-skip-tls-verify`: If true, the server's certificate will not be checked for validity. This will make your HTTPS connections insecure (default: false)

**Note:**
- Default values for `host`, `token`, `api-path` and `insecure-skip-tls-verify` are the values provided in the `config set` command

##### **Additional Flags**
- `--no-prompt`: Apply default values without prompting the user for input.

#### Fetching PipelineRuns and TaskRuns

```sh
tkn-results pr ls      # Get list of PipelineRuns in a namespace  
tkn-results tr ls      # Get list of TaskRuns in a namespace  
```
##### **Pagination Feature**

- The CLI fetches results using the Tekton Results API `page_size` and `page_token` parameters. The first request retrieves the initial `--limit` number of results.
- If `--single-page=false`, the CLI waits for user input before fetching the next set of results using the `page_token` from the previous response.
- Pagination continues until there are no more results or the user chooses to exit.

##### **Additional Flags**

- `--all-namespace`: List PipelineRuns from all namespaces.
- `--label`: A selector (label query) to filter results.
- `--limit`: Specify the number of results returned in the first iteration of pagination. (default: `10`)
- `--single-page`: Disable pagination and exit after the first iteration. (default: `false`)

#### Describing Runs

```sh
tkn-results pr describe <pr-name> -n <namespace>  # Get details of a specific PipelineRun  
tkn-results tr describe <tr-name> -n <namespace>  # Get details of a specific TaskRun  
```

#### Fetching Logs

```sh
tkn-results pr logs <pr-name> -n <namespace>  # Fetch logs of a specific PipelineRun  
tkn-results tr logs <tr-name> -n <namespace>  # Fetch logs of a specific TaskRun  
```

### Architecture

- The CLI will fetch the host and the authentication token from the user's kubeconfig file when possible, ensuring seamless authentication without manual configuration.

- The CLI will interact directly with `Tekton Results API` to fetch records.

- Retrieved records will be parsed and structured as `PipelineRun` or `TaskRun` objects, and their details will be formatted and displayed on the CLI.

- The CLI will fetch results in paginated form using `page_size` and `page_token` parameters from the Tekton Results API. This will allow users to retrieve results efficiently without overwhelming the API.

- The CLI will make use of the [Partial Response feature](https://github.com/tektoncd/results/blob/main/docs/api/README.md#filtering-response) and request only the necessary fields from the API, reducing payload size and improving performance.

- It will use `token-based authentication` to secure API requests.

### Dependencies

- Golang-based CLI framework (e.g., `cobra` for command parsing).
- Tekton Results API v1 as the backend.
- `k8s.io/apimachinery` for Kubernetes API object manipulation.
- `k8s.io/client-go` for interacting with Kubernetes clusters.

## Alternatives Considered

1. `Custom API Scripts`: Users could write their own scripts, but this lacks standardization and usability.

## Impact

### Backward Compatibility

Existing `tkn-results` CLI commands should not break. We should add a deprecation message to the old commands to inform users about the new structure and provide guidance on transitioning to the updated CLI.

### Security Considerations

- Authentication will use secure `token-based mechanisms`.
- Users must configure authentication before accessing results.

## Implementation Plan

1. `Research & API Study` – Understand Tekton Results API structure.
2. `CLI Skeleton & Command Parsing` – Implement base command structure.
3. `Resources Retrieval` – Implement `ls` commands for PipelineRuns/TaskRuns.
4. `Logs Fetching` – Implement `logs` command with streaming support.
5. `Authentication Handling` – Implement secure authentication mechanisms.
6. `Testing & Documentation` – Provide examples and user guides.

### Test Plan

- Unit tests for each command to ensure correctness.

## References
- Inspired by the [kubectl plugin](https://github.com/sayan-biswas/kubectl-tekton) developed by [@sayan-biswas](https://github.com/sayan-biswas)
