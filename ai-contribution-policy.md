# AI Contribution Policy

This document outlines the Tekton community's policy on the use of Artificial Intelligence (AI) tools and Large Language Models (LLMs) in contributions to Tekton projects.

## Overview

The Tekton community recognizes that AI-powered tools can be valuable aids in software development. This policy establishes guidelines to ensure that AI-assisted contributions maintain our standards for quality, security, and community values while preserving human accountability and decision-making.

## Policy

### 1. AI Assistance is Permitted

Contributors **MAY** use AI assistance when contributing to Tekton projects, subject to the requirements outlined in this policy.

AI tools may be used for tasks including but not limited to:
- Code completion and suggestions
- Refactoring assistance
- Documentation writing and improvement
- Test case generation
- Grammar and spelling corrections
- Code review assistance
- Debugging support

### 2. Contributor Accountability

**Contributors are fully responsible and accountable for all AI-assisted contributions.**

This means:
- You must review, understand, and validate all AI-generated or AI-assisted content before submitting it
- You are accountable for the quality, correctness, security, and licensing compliance of your contributions
- You must ensure the contribution aligns with Tekton's [design principles](./design-principles.md), [standards](./standards.md), and [code of conduct](./code-of-conduct.md)
- The contributor is always considered the author of the contribution

### 3. Human Review Required

**All AI-assisted contributions MUST receive meaningful human review before submission.**

- Contributors must not submit code or documentation that they do not understand
- AI-generated code must be reviewed for security vulnerabilities (e.g., injection attacks, authentication bypasses, credential exposure)
- Contributors should verify that AI-generated content does not introduce unnecessary complexity or over-engineering
- Fully AI-generated contributions with minimal human review or understanding are not acceptable

### 4. Transparency and Disclosure

#### When Disclosure is Required

Contributors **MUST** disclose the use of AI tools when:
- AI tools generated substantial portions of code, documentation, or other content
- AI tools significantly influenced the design or architecture of a contribution
- The contribution includes non-trivial AI-generated content

#### When Disclosure is Not Required

Disclosure is **NOT** required for:
- Minor grammar, spelling, or formatting corrections
- Code completion of routine patterns (e.g., standard error handling, common idioms)
- Using AI tools to search documentation or understand existing code without generating new content

#### How to Disclose

Contributors should disclose AI assistance using one or more of the following methods:

**Preferred: Git commit message trailers**
```
Add support for custom retry policies

This commit implements configurable retry policies for TaskRuns,
allowing users to specify exponential backoff and jitter parameters.

Assisted-by: Claude 3.5 Sonnet
```

**Alternative: Pull request description**

Include a note in the PR description:
```markdown
This PR was developed with assistance from GitHub Copilot for code completion
and ChatGPT for documentation writing.
```

**For documentation: Document metadata or preamble**

Add a note at the beginning or in metadata where appropriate.

### 5. Decision-Making Authority

**AI tools MUST NOT be the sole decision-maker for:**
- Architectural or design decisions
- Evaluating the merit or quality of contributions
- Determining community standing, permissions, or roles
- Approving or rejecting pull requests
- Security-sensitive decisions

While AI tools may provide input or analysis, **final accountability always rests with human contributors and maintainers.**

Automated technical validation (e.g., automated tests, linters, security scanners) is encouraged and does not violate this principle.

### 6. Licensing and Legal Compliance

Contributors must ensure that AI-assisted contributions:
- Comply with the Apache License 2.0 and the [CDF Contributor License Agreement (CLA)](./process/README.md#cla)
- Do not introduce code with incompatible licenses
- Do not violate intellectual property rights
- Do not include proprietary code or trade secrets from the AI training data

**If you have concerns about the licensing of AI-generated content, ask for guidance before submitting.**

### 7. Large-Scale AI Initiatives

Significant initiatives involving AI, such as:
- Automated mass refactoring across multiple repositories
- AI-driven code generation tools integrated into Tekton workflows
- Large-scale documentation rewrites using AI

**MUST** be proposed through the [Tekton Enhancement Proposal (TEP) process](./process/tep-process.md) and discussed with the community before implementation.

### 8. Security Considerations

Contributors using AI tools must be especially vigilant about:
- **Credential exposure**: Ensure AI-generated code does not leak secrets, API keys, or credentials
- **Injection vulnerabilities**: Review AI-generated code for SQL injection, command injection, XSS, and other OWASP Top 10 vulnerabilities
- **Untrusted input handling**: Verify that AI-generated code properly validates and sanitizes user input
- **Authentication and authorization**: Ensure AI-generated security-sensitive code follows Tekton's security best practices

### 9. Quality Standards

AI-assisted contributions must meet the same quality standards as any other contribution:
- Code must be maintainable, readable, and follow Tekton's coding conventions
- Documentation must be clear, accurate, and helpful to users
- Contributions should not include unnecessary complexity, over-engineering, or speculative features
- All tests must pass, and new functionality should include appropriate test coverage

## Reporting Violations

If you believe a contribution violates this policy or have concerns about AI use in the project, please:

1. Raise the concern in the relevant pull request or issue
2. Contact the project maintainers via [Slack](./contact.md#slack) or the [mailing list](./contact.md#mailing-list)
3. For sensitive matters, contact [the governing board](./governance.md) directly

## Rationale

This policy aims to:
- **Encourage innovation**: Allow contributors to use modern AI tools to enhance productivity
- **Maintain quality**: Ensure all contributions meet Tekton's high standards regardless of how they were created
- **Preserve human judgment**: Keep human decision-making at the center of the project
- **Build trust**: Provide transparency about AI use in the codebase
- **Ensure compliance**: Protect the project from licensing and legal risks

## References

This policy was informed by:
- [Fedora AI Contributions Policy](https://docs.fedoraproject.org/en-US/council/policy/ai-contribution-policy/)
- [OpenInfra Foundation AI Policy](https://openinfra.org/legal/ai-policy/)
- Tekton community values and existing governance structures

## Amendments

This policy may be amended through the standard Tekton governance process. Any substantial changes require review and approval from at least 50% of the [governing board](./governance.md) as specified in [CONTRIBUTING.md](./CONTRIBUTING.md).

---

*Last updated: 2025-11-20*
