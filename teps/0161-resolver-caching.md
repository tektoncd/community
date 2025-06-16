---
title: Resolver Caching for Task and Pipeline Resolution
authors:
  - "@bcook"
creation-date: 2024-06-15
last-updated: 2024-06-15
status: proposed
---

# TEP-0161: Resolver Caching for Task and Pipeline Resolution

## Summary

This TEP proposes adding caching capabilities to Tekton's remote resolvers to improve performance and reduce occurences of failed pipelines due to rate limiting by registries and git forges. The caching mechanism will be configurable per resolver type and will support different caching strategies based on the nature of the resolved resource.

## Motivation

- Avoid failed resolutions due to external services imposing rate limiting
- Reduce latency for frequently accessed resources
- Minimize external API calls and network traffic
- Improve reliability by serving cached content when external services are briefly unavailable
- Reduce load on external services (GitHub, OCI registries, etc.)

## Requirements

- Cache configuration should be flexible and configurable
- Support different caching modes (always, never, auto)
- Cache size and TTL should be configurable
- Cache should be shared across resolvers
- Cache keys should be deterministic and unique
- Cache should be configurable via ConfigMap

## Proposal

### User Stories

1. As a user, I want to cache git resolver requests to avoid git forge rate limiting
2. As a user, I want to cache OCI bundles to avoid registry rate limiting
3. As a user, I want to configure different caching strategies for different resolvers
4. As a user, I want to forcibly enable / disable caching for certain resources
5. As Tekton admin, I want to control cache size and TTL
6. As Tekton admin, I want to limit caching to in-memory strategies with short TTL to mitigate cache poisoning attacks.

### Design Details
Caching is automatically enabled for OCI bundles which are specified by digest and git revisions specified by commit hash. These immutable resources are always safe to cache. The user can opt-in to 5 minute caching of non-immutable resources like git or oci tags. This design should ensure that no existing users will notice any adverse effects from this change. It should be entirely transparent.

#### Cache Configuration

The cache will be configured via a ConfigMap with the following options:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: resolver-cache-config
  namespace: tekton-pipelines-resolvers
data:
  max-size: "1000"  # Maximum number of cache entries
  default-ttl: "5m" # Default time-to-live for cache entries
```

#### Caching Modes

Three caching modes will be supported:

1. `always`: Always use cache regardless of resource type
2. `never`: Never use cache
3. `auto`: Use cache only when appropriate (e.g., for immutable resources like Git commit hash or OCI digests)

#### Cache Implementation

- Use an in-memory LRU cache with configurable size
- Support TTL for cache entries
- Generate cache keys based on resolver type and resource parameters
- Share cache across resolvers
- Support cache invalidation

### API Changes

No API changes required. The caching behavior will be controlled through:

1. ConfigMap configuration
2. Resolver-specific parameters
3. Environment variables

### Security Considerations

- Cache keys should be namespace-aware to prevent cross-namespace access
- Cache should not store sensitive information
- Cache size limits should be enforced to prevent memory issues

### Performance Considerations

- Cache size and TTL should be configurable based on cluster resources
- Cache should be efficient for high-frequency access patterns

## Implementation Plan

1. Implement basic cache functionality
2. Add configuration support
3. Integrate with git and bundle resolvers.
4. Add metrics and monitoring
5. Add documentation and examples

## Alternatives Considered

1. Per-resolver caching
   - Rejected: Would lead to duplicate caching logic and increased memory usage
2. External caching service
   - Rejected: Adds complexity and potential failure points
3. No caching
   - Rejected: Would not address performance and reliability concerns

## Open Questions

1. Is it necessary to add a cache statistics API?
2. There is no way to fetch resources from HTTP servers with an immutable reference. HTTP servers rarely rate limit in the same way as registries and git forges. Is caching for HTTP resolver necessary?
3. Same question for Hub resolver?
4. And, same question for Cluster resolver? Caching seems unnecessary here.

## References

- [Remote Resolution TEP](https://github.com/tektoncd/community/blob/main/teps/0060-remote-resource-resolution.md)
- [Git Resolver Documentation](https://github.com/tektoncd/pipeline/blob/main/docs/git-resolver.md)
- [Bundle Resolver Documentation](https://github.com/tektoncd/pipeline/blob/main/docs/bundle-resolver.md)
