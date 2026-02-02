# AI Contribution Policy

## Core Rules

**All AI usage must be disclosed.** You must state the tool you used (e.g., Claude, Copilot, ChatGPT) along with the extent that the work was AI-assisted.

**If AI isn't disclosed but a maintainer suspects its use, the PR or issue may be closed.** Maintainers have discretion to request clarification before taking action.

**Contributors are fully responsible for all AI-assisted contributions.** You must review, understand, and test all AI-generated content before submitting. Fully AI-generated contributions with minimal human review are not acceptable.

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

Assisted-by: Claude 3.5 Sonnet
```

**Alternative: Pull request description**
```markdown
This PR was developed with assistance from GitHub Copilot.
```

## Contributor Responsibilities

All AI-assisted contributions must:
- Align with Tekton's [design principles](./design-principles.md), [standards](./standards.md), and [code of conduct](./code-of-conduct.md)
- Be reviewed for security vulnerabilities (injection attacks, credential exposure, OWASP Top 10)
- Meet the same quality standards as any other contribution
- Include appropriate test coverage

**You must not submit code that you do not understand.**

## Security Considerations

Contributors using AI tools must be especially vigilant about:
- **Credential exposure**: Ensure AI-generated code does not leak secrets or API keys
- **Injection vulnerabilities**: Review for SQL injection, command injection, XSS
- **Untrusted input handling**: Verify proper input validation and sanitization

## Large-Scale AI Initiatives

Significant AI initiatives (mass refactoring, AI-driven code generation tools, large documentation rewrites) **must** be proposed through the [TEP process](./process/tep-process.md) first.

## Reporting Violations

1. Raise the concern in the relevant pull request or issue
2. Contact maintainers via [Slack](./contact.md#slack) or the [mailing list](./contact.md#mailing-list)
3. For sensitive matters, contact [the governing board](./governance.md)

## References

This policy was informed by:
- [Fedora AI Contributions Policy](https://docs.fedoraproject.org/en-US/council/policy/ai-contribution-policy/)
- [Ghostty AI Usage Policy](https://github.com/ghostty-org/ghostty/blob/main/AI_POLICY.md)
- [OpenInfra Foundation AI Policy](https://openinfra.org/legal/ai-policy/)

---

*Last updated: 2025-11-20*
