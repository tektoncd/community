# AI Contribution Policy

Tekton welcomes contributions that use AI tools, as long as the contributor takes accountability for the content and respects the policy in this document.

## Core Rules

**All AI usage must be disclosed.** You should state the extent that the work was AI-assisted. Mentioning the specific tool (e.g., Claude, Copilot, ChatGPT) is encouraged, as it can help reviewers understand the generated code and some tools support `Co-authored-by` trailers natively.

**Transparency and clarification.** If a maintainer suspects undisclosed AI usage, they may ask for clarification. If the AI usage cannot be clarified or the contributor cannot engage directly, maintainers may close the pull request to preserve review bandwidth.

**Contributors are responsible for all AI-assisted contributions.** Please review, understand, and test all AI-generated content before submitting. Contributions that are fully AI-generated with minimal human review are not acceptable.

**No automated AI interactions.** You must not use AI tools to generate replies to code review comments, GitHub issues, or maintainer questions. Maintainers invest valuable time to review your work and expect to communicate directly with the human contributor.

**AI-assisted reviews must be disclosed and verified.** If you use AI to assist in reviewing a pull request or issue, you must disclose that the review was AI-assisted. Posting unverified AI reviews, hallucinations, or unsolicited automated review summaries is considered spam.

## When Disclosure is Required

Disclosure is **required** when:
- AI tools generated substantial portions of code, documentation, or other content
- AI tools significantly influenced the design or architecture of a contribution
- The contribution includes non-trivial AI-generated content

Disclosure is **not required** for:
- Minor grammar, spelling, or formatting corrections
- Code completion of routine patterns (e.g., standard error handling, common idioms)
- Using AI to search documentation or understand existing code

## How to Disclose

**Preferred: Git commit message trailer**
```
Add support for custom retry policies

Assisted-by: Claude 5.5 Sonnet
```

**Alternative: Pull request description**
```markdown
This PR was developed with assistance from GitHub Copilot.
```

## Contributor Responsibilities

All AI-assisted contributions must:
- Align with Tekton's [design principles](./design-principles.md), [standards](./standards.md), and [code of conduct](./code-of-conduct.md)
- Be fully reviewed and tested by the contributor before opening for maintainer review
- Be reviewed for security vulnerabilities (injection attacks, credential exposure, OWASP Top 10)
- Meet the same quality standards as any other contribution
- Include appropriate test coverage
- Keep pull requests small and focused — AI tools make it easy to generate large changes, but the review burden remains on maintainers

## Review Expectations

Code review requires active human participation. Maintainers may close a pull request or issue without detailed debugging if:
- AI usage is undisclosed or unclear upon inquiry
- The contributor cannot explain the changes or relies on AI-generated replies during review
- The submission is an unverified AI dump that creates an unreasonable review burden

Maintainers may close such PRs with a brief link to this policy, encouraging the contributor to test and understand the work before reopening.

## Security Considerations

Contributors using AI tools must be especially vigilant about:
- **Credential exposure**: Ensure AI-generated code does not leak secrets or API keys
- **Injection vulnerabilities**: Review for SQL injection, command injection, XSS
- **Untrusted input handling**: Verify proper input validation and sanitization
- **Malicious or hallucinated packages:** Ensure that AI-suggested external dependencies are legitimate, well-maintained packages and not typosquatted malware.

## Large-Scale AI Initiatives

Significant AI initiatives (mass refactoring, AI-driven code generation tools, large documentation rewrites) **must** be proposed through the [TEP process](./process/tep-process.md) first. Unsolicited, autonomous bot submissions without prior TEP approval will be closed.

## Reporting Violations

1. Raise the concern in the relevant pull request or issue
2. Contact maintainers via [Slack](./contact.md#slack) or the [mailing list](./contact.md#mailing-list)
3. For sensitive matters, contact [the governing board](./governance.md)

## References

This policy was informed by:
- [Fedora AI Contributions Policy](https://docs.fedoraproject.org/en-US/council/policy/ai-contribution-policy/)
- [Ghostty AI Usage Policy](https://github.com/ghostty-org/ghostty/blob/main/AI_POLICY.md)
- [OpenInfra Foundation AI Policy](https://openinfra.org/legal/ai-policy/)
- [Tekton Community Discussion #1300](https://github.com/tektoncd/community/discussions/1300)
- [CNCF Foundation Issue #1285](https://github.com/cncf/foundation/issues/1285)

---

*Last updated: 2026-11-08*
