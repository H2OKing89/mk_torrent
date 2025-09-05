# Contributing to mk_torrent

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Quick Start

### Prerequisites
- Python 3.10 or higher
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/H2OKing89/mk_torrent.git
cd mk_torrent

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run tests to verify setup
pytest -q
```

## Development Workflow

### 1. Creating a Branch
Create a feature branch from `main`:

```bash
git checkout main
git pull origin main
git checkout -b feat/your-feature-name
```

### 2. Making Changes
- Write code following the existing patterns
- Add tests for new functionality
- Update documentation if needed
- Run pre-commit checks: `pre-commit run --all-files`

### 3. Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m metadata      # Metadata-related tests
pytest -m "not network" # Skip network tests (default)
pytest -m network       # Run network tests (requires internet)

# Run with coverage
pytest --cov=src
```

### 4. Commit Guidelines
Use semantic commit messages in your PR titles:

- `feat(metadata): add new audnexus parser`
- `fix(red): handle missing description fields`
- `refactor(core): extract metadata sources`
- `docs(api): update tracker integration guide`
- `test(utils): add path compliance tests`

### 5. Pull Request Process
1. Push your branch: `git push origin feat/your-feature-name`
2. Create a PR with a semantic title
3. Fill out the PR template
4. Wait for CI checks to pass
5. Address any review feedback

## Code Standards

### Python Style
- We use `ruff` for formatting and linting
- Follow PEP 8 conventions
- Maximum line length: 88 characters
- Use type hints where possible

### Testing
- Add tests for all new functionality
- Maintain test coverage above 70%
- Use descriptive test names: `test_should_extract_duration_from_valid_file`
- Group related tests in classes

### Documentation
- Update relevant documentation for new features
- Use docstrings for public functions and classes
- Keep README and docs up to date

## Project Structure

```
src/mk_torrent/
├── core/              # Core functionality
│   ├── metadata/      # Metadata extraction system
│   │   └── templates/ # ✅ Template system (BBCode generation)
│   └── validation/    # Data validation
├── api/               # External API integrations
│   ├── red/          # RED tracker integration
│   └── qbittorrent/  # qBittorrent API
├── utils/            # Utility functions
└── cli/              # Command-line interface

tests/
├── unit/             # Unit tests
├── integration/      # Integration tests
└── fixtures/         # Test data
```

## Common Tasks

### Adding a New Metadata Source
1. Create source class in `src/mk_torrent/core/metadata/sources/`
2. Implement the `MetadataSource` protocol
3. Add comprehensive tests in `tests/unit/core/metadata/sources/`
4. Update documentation

### Working with Template System
1. Templates are in `src/mk_torrent/core/metadata/templates/templates/`
2. Use Jinja2 syntax with BBCode output formatting
3. Test templates with `test_template_integration.py`
4. Follow Pydantic data models in `templates/models.py`

### Adding Tracker Support
1. Create tracker module in `src/mk_torrent/api/trackers/`
2. Implement required API methods
3. Add integration tests
4. Update configuration examples

### Debugging Tests
```bash
# Run specific test with verbose output
pytest -vvs tests/unit/test_specific.py::test_method

# Run tests with pdb on failure
pytest --pdb tests/unit/test_specific.py

# Run only failed tests from last run
pytest --lf
```

## Getting Help

- **Issues**: Check existing [issues](https://github.com/H2OKing89/mk_torrent/issues) or create a new one
- **Discussions**: Use [GitHub Discussions](https://github.com/H2OKing89/mk_torrent/discussions) for questions
- **Documentation**: Check the [docs](./docs/) directory

## Code of Conduct

Please be respectful and inclusive in all interactions. We aim to create a welcoming environment for all contributors.

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).
