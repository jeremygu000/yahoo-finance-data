# Contributing to Market Terminal

Thank you for your interest in contributing to Market Terminal! This guide will help you get started with the development process.

## Prerequisites

Before you begin, make sure you have the following installed:

- **Python 3.12+** — Backend development
- **uv** — Python package manager (install via `pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node.js 22+** — Frontend development
- **pnpm** — JavaScript package manager (install via `npm install -g pnpm`)
- **Git** — Version control

## Getting Started

### 1. Fork and Clone

Fork the repository on GitHub, then clone your fork locally:

```bash
git clone git@github.com:YOUR_USERNAME/yahoo-finance-data.git
cd yahoo-finance-data
```

### 2. Set Up Backend

Install Python dependencies:

```bash
uv sync
```

This will create a virtual environment and install all backend dependencies.

### 3. Set Up Frontend

Navigate to the web directory and install dependencies:

```bash
cd web
pnpm install
cd ..
```

## Development Workflow

### Branch Naming

Use descriptive branch names following these patterns:

- Features: `feature/short-description`
- Bugfixes: `fix/short-description`
- Documentation: `docs/short-description`
- Refactoring: `refactor/short-description`

Example: `feature/add-portfolio-tracking` or `fix/missing-dividend-data`

### Running Tests

Backend tests:

```bash
uv run pytest -v
```

Frontend tests (if applicable):

```bash
cd web
pnpm test
cd ..
```

### Running Linters and Formatters

Format Python code:

```bash
uv run black src/ tests/ --line-length 120
```

Type check Python:

```bash
uv run mypy src/market_data/ --strict
```

Lint and build frontend:

```bash
cd web
pnpm lint
pnpm build
cd ..
```

### Running the Development Server

Backend API (runs on `http://localhost:8100`):

```bash
uv run market-data fetch
```

Frontend development:

```bash
cd web
pnpm dev
```

## Code Style

We maintain consistent code quality through automated tools. All code must pass before merging:

- **Python formatting**: Black with 120-character line length
- **Python type checking**: mypy in strict mode
- **JavaScript formatting**: ESLint (enforced by `pnpm lint`)
- **Consistency**: Follow existing patterns in the codebase

## Commit Message Conventions

Use Conventional Commits for clear, consistent messages:

- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation changes
- `style:` — Code style changes (formatting, missing semicolons, etc.)
- `refactor:` — Code refactoring without feature changes
- `perf:` — Performance improvements
- `test:` — Adding or updating tests
- `chore:` — Dependency updates, tooling changes

Examples:

```
feat: add portfolio comparison endpoint
fix: handle missing dividend data in ETFs
docs: update API endpoint documentation
test: add integration tests for OHLCV data
```

## Pull Request Process

### Before Submitting

1. Make sure all tests pass: `uv run pytest -v`
2. Format code: `uv run black src/ tests/ --line-length 120`
3. Type check: `uv run mypy src/market_data/ --strict`
4. Frontend checks (if applicable): `cd web && pnpm lint && pnpm build`
5. Commit with conventional commit messages
6. Push to your fork

### Submitting a PR

1. Create a PR against the `main` branch
2. Fill out the PR template completely
3. Ensure the title follows conventional commits format
4. Link any related issues (use `Closes #123` or `Fixes #456`)
5. Wait for CI checks to pass
6. Request review from maintainers

### PR Review

- Be open to feedback and suggestions
- Keep discussions professional and focused on code
- Small, focused PRs are reviewed faster
- Update your branch if it falls behind main

## Questions?

- Open a GitHub Discussion for questions
- Check existing issues before reporting bugs
- Read the README for project overview and architecture

Thank you for contributing to Market Terminal!
