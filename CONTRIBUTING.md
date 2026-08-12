# Contributing

Thanks for wanting to help make **agent-bridge** better. This project is
deliberately small, so contributions that keep it simple are the most welcome.

## How to contribute

1. **Fork** the repository.
2. Create a feature branch: `git checkout -b feat/my-change`.
3. Make your changes. Keep the spirit: small, readable, dependency-light.
   The standard library (plus Playwright for `web` mode) is preferred.
4. If your change adds behaviour, add a short note to the README.
5. Open a **Pull Request** describing what and why.

## What we value

- **Simplicity** — one file per responsibility, no framework magic.
- **Composability** — new `Manager`/`Worker` types should be ~50 lines.
- **Documentation** — docstrings on every public class/method.
- **No floating code** — unused dependencies are removed, secrets never
  committed (use `${ENV_VAR}` in config).

## Tests

There is no test suite yet — the project is kept minimal on purpose. If you
add one, use `pytest` and keep it dependency-light.

## Code of conduct

Be kind. This is a tiny project built for learning and sharing — PRs that
are clear and friendly merge fastest.