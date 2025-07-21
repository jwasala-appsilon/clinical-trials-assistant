# 🤝 Contributing to Clinical Trials Assistant

Thank you for your interest in contributing to the Clinical Trials Assistant! 🎉 We're excited to have you as part of our community.

## 📋 Table of Contents

- [🚀 Getting Started](#-getting-started)
- [🔄 Development Workflow](#-development-workflow)
- [📝 Commit Guidelines](#-commit-guidelines)
- [🧪 Testing](#-testing)
- [🎨 Code Style](#-code-style)
- [📖 Documentation](#-documentation)
- [🐛 Bug Reports](#-bug-reports)
- [💡 Feature Requests](#-feature-requests)
- [❓ Questions](#-questions)

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13+** 🐍
- **Poetry** for dependency management 📦
- **Git** for version control 🗂️

### Setting up the Development Environment

1. **Fork the repository** 🍴
   ```bash
   # Click the "Fork" button on GitHub
   ```

2. **Clone your fork** 📥
   ```bash
   git clone https://github.com/YOUR_USERNAME/clinical-trials-assistant.git
   cd clinical-trials-assistant
   ```

3. **Add upstream remote** 🔗
   ```bash
   git remote add upstream https://github.com/jwasala/clinical-trials-assistant.git
   ```

4. **Install dependencies** 📦
   ```bash
   poetry install
   ```

5. **Set up environment variables** ⚙️
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

6. **Verify installation** ✅
   ```bash
   make test
   make lint
   ```

## 🔄 Development Workflow

### 1. Create a Feature Branch

```bash
# Update your main branch
git checkout main
git pull upstream main

# Create a new branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 2. Make Your Changes

- Write clean, readable code 📝
- Add tests for new functionality 🧪
- Update documentation as needed 📚
- Follow our coding standards 🎨

### 3. Test Your Changes

**Always run these commands before committing:**

```bash
# Run all tests
make test

# Lint and format code
make lint

# Check linting without auto-fixing
make dry_lint
```

### 4. Commit Your Changes

Follow our [commit guidelines](#-commit-guidelines) when making commits.

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub! 🚀

## 📝 Commit Guidelines

We follow **Conventional Commits** specification with **gitmojis** encouraged! 🎨

### Commit Message Format

```
<gitmoji> <type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

- **feat**: ✨ A new feature
- **fix**: 🐛 A bug fix
- **docs**: 📚 Documentation only changes
- **style**: 💄 Changes that do not affect the meaning of the code
- **refactor**: ♻️ A code change that neither fixes a bug nor adds a feature
- **perf**: ⚡ A code change that improves performance
- **test**: ✅ Adding missing tests or correcting existing tests
- **chore**: 🔧 Changes to the build process or auxiliary tools

### Examples

```bash
# Good commits
✨ feat(providers): add new clinical trial data provider
🐛 fix(nodes): resolve state management issue in graph
📚 docs: update installation instructions
🧪 test(providers): add integration tests for API calls
♻️ refactor(main): improve streamlit component structure

# Bad commits
fix bug
add feature
update
```

### Recommended Gitmojis

| Emoji | Code | Description |
|-------|------|-------------|
| ✨ | `:sparkles:` | Introduce new features |
| 🐛 | `:bug:` | Fix a bug |
| 📚 | `:books:` | Add or update documentation |
| ♻️ | `:recycle:` | Refactor code |
| ✅ | `:white_check_mark:` | Add, update, or pass tests |
| 🔧 | `:wrench:` | Add or update configuration files |
| 💄 | `:lipstick:` | Add or update the UI and style files |
| ⚡ | `:zap:` | Improve performance |
| 🔒 | `:lock:` | Fix security issues |
| 🎨 | `:art:` | Improve structure/format of the code |

## 🧪 Testing

### Writing Tests

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **Coverage**: Aim for high test coverage on new code

### Test Structure

```python
# tests/test_example.py
import pytest
from clinical_trials_assistant.example import ExampleClass

class TestExampleClass:
    def test_example_functionality(self):
        # Arrange
        instance = ExampleClass()
        
        # Act
        result = instance.do_something()
        
        # Assert
        assert result == expected_value
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
poetry run pytest tests/test_providers.py

# Run with coverage
poetry run pytest --cov=clinical_trials_assistant

# Run tests in watch mode
poetry run pytest --watch
```

## 🎨 Code Style

We use **Ruff** for linting and formatting to ensure consistent code style.

### Running Linting

```bash
# Auto-fix and format code
make lint

# Check without auto-fixing
make dry_lint
```

## 📖 Documentation

### Updating Documentation

- Update docstrings for new/modified functions
- Update README.md if you add new features
- Add examples for new functionality
- Update type hints

### Documentation Style

- Use clear, concise language
- Provide examples where helpful
- Include type information
- Document edge cases and exceptions

## 💡 Feature Requests

We welcome feature requests! Please:

1. **Search existing issues** to avoid duplicates
2. **Describe the feature** clearly
3. **Explain the use case** and benefits
4. **Consider the scope** - start small and iterate

## ❓ Questions

### Getting Help

- **GitHub Discussions**: For general questions and discussions
- **GitHub Issues**: For bug reports and feature requests
- **Email**: Contact [jakub@randomseed.eu](mailto:jakub@randomseed.eu) for private matters

### Community Guidelines

- **Be respectful** and constructive in all interactions 🤝
- **Search existing issues** before creating new ones 🔍
- **Provide clear context** in questions and reports 📝
- **Help others** when you can 💪

## 🎉 Recognition

Contributors will be recognized in:

- GitHub contributors list
- Release notes for significant contributions
- Project documentation

Thank you for contributing to Clinical Trials Assistant! 🙏

---

<div align="center">
Made with 💙 by the Clinical Trials Assistant community
</div>