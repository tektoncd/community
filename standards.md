# Tekton Development Standards

This doc contains the standards we try to uphold across all project
in the Tekton org.

## Principles

When possbile, try to practice:

- **Documentation driven development** - Before implementing anything, write
  docs to explain how it will work
- **Test driven development** - Before implementing anything, write tests to
  cover it

Minimize the number of integration tests written and maximize the unit tests!
Unit test coverage should increase or stay the same with every PR.

This means that most PRs should include both:

1. Tests
2. Documentation updates

## Commit Messages

All commit messages should follow
[these best practices](https://chris.beams.io/posts/git-commit/), specifically:

- Start with a subject line
- Contain a body that explains _why_ you're making the change you're making
- Reference an issue number one exists, closing it if applicable (with text such
  as
  ["Fixes #245" or "Closes #111"](https://help.github.com/articles/closing-issues-using-keywords/))

Aim for [2 paragraphs in the body](https://www.youtube.com/watch?v=PJjmw9TRB7s).
Not sure what to put? Include:

- What is the problem being solved?
- Why is this the best approach?
- What other approaches did you consider?
- What side effects will this approach have?
- What future work remains to be done?

## Coding standards

### Go

- [Go code review comments](https://github.com/golang/go/wiki/CodeReviewComments)