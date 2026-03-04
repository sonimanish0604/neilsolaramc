# Contributing

Thanks for your interest in contributing to All Solar AMC SaaS. A few guidelines to make contributions smooth and consistent:

- Discussion & Issues: Open an Issue describing the change or bug before working on a PR. Include steps to reproduce and expected behavior for bugs.
- Branches: Use feature branches named `feature/<short-desc>` or `fix/<short-desc>`.
- Commits: Write clear, small commits. Use present-tense messages, e.g. "feat: add tenant model" or "fix: validate phone number".
- PRs: Link the related Issue and include a short description of the change, testing steps, and any migration notes.
- Code style: Follow the project's Python style (configured lints such as `ruff`). Keep lines reasonably short and prefer explicit typing where helpful.
- Tests: Add tests for bug fixes and new features when applicable. CI runs on push/PR — please ensure tests pass locally before opening a PR.
- Security & secrets: Never commit secrets, credentials, or private keys. Use the `secrets/` folder pattern or environment variables and Secret Manager in production.

Maintainers will review PRs and may request changes. Thanks — your contributions help improve the project!

See also: `docs/README.md` for architecture and project goals.
