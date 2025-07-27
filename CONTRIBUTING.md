# 🤝 Contributing to ChatOps CLI

Thank you for your interest in contributing to ChatOps CLI! This document provides guidelines and information for contributors.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Plugin Development](#plugin-development)
- [Documentation](#documentation)
- [Code Review Process](#code-review-process)
- [Release Process](#release-process)

## Getting Started

### Before You Start

1. **Check existing issues** to see if your idea is already being worked on
2. **Join discussions** in GitHub Discussions to share ideas
3. **Read the documentation** to understand the project structure
4. **Set up your development environment** (see below)

### Types of Contributions

We welcome various types of contributions:

- 🐛 **Bug fixes** - Fix issues and improve stability
- ✨ **New features** - Add new functionality and capabilities
- 🔌 **Plugin development** - Create new plugins for specific use cases
- 📚 **Documentation** - Improve guides, examples, and API docs
- 🧪 **Testing** - Add tests and improve test coverage
- 🔧 **Infrastructure** - Improve CI/CD, tooling, and development experience
- 🎨 **UI/UX** - Enhance the user interface and experience

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Poetry (recommended) or pip
- Git
- Ollama (for local LLM testing)
- Groq API key (for cloud LLM testing)

### Local Development Setup

1. **Fork and clone the repository**

```bash
# Fork the repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/ChatOps.git
cd ChatOps
```

2. **Set up the development environment**

```bash
# Install Poetry if you haven't already
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install --with dev

# Activate the virtual environment
poetry shell
```

3. **Install pre-commit hooks**

```bash
# Install pre-commit
poetry run pip install pre-commit

# Install the git hook scripts
pre-commit install
```

4. **Set up configuration**

```bash
# Create a development configuration
cp .env.example .env

# Edit .env with your API keys
# GROQ_API_KEY=your_groq_api_key_here
# OLLAMA_BASE_URL=http://localhost:11434
```

5. **Verify setup**

```bash
# Run tests to ensure everything is working
poetry run pytest

# Run linting
poetry run black --check .
poetry run ruff check .
poetry run mypy chatops_cli/

# Test the CLI
poetry run python -m chatops_cli --help
```

### Development Tools

The project uses several development tools:

- **Poetry**: Dependency management
- **Black**: Code formatting
- **Ruff**: Linting and import sorting
- **MyPy**: Type checking
- **Pre-commit**: Git hooks for code quality
- **Pytest**: Testing framework
- **Coverage**: Test coverage reporting

## Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

- **Line length**: 88 characters (Black default)
- **String quotes**: Double quotes for docstrings, single quotes for strings
- **Import sorting**: Automatic with Ruff
- **Type hints**: Required for all public functions and methods

### Code Formatting

```bash
# Format code with Black
poetry run black .

# Sort imports with Ruff
poetry run ruff check --fix .

# Type checking with MyPy
poetry run mypy chatops_cli/
```

### Naming Conventions

- **Classes**: PascalCase (e.g., `ChatOpsCLI`)
- **Functions/Methods**: snake_case (e.g., `execute_command`)
- **Variables**: snake_case (e.g., `api_key`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_TIMEOUT`)
- **Files**: snake_case (e.g., `command_executor.py`)

### Documentation Standards

- **Docstrings**: Use Google style docstrings
- **Comments**: Explain why, not what
- **README**: Keep updated with new features
- **API docs**: Document all public interfaces

Example docstring:

```python
def execute_command(command: str, dry_run: bool = False) -> CommandResult:
    """Execute a command with validation and logging.
    
    Args:
        command: The command to execute
        dry_run: If True, preview the command without execution
        
    Returns:
        CommandResult: The result of command execution
        
    Raises:
        CommandValidationError: If the command fails validation
        SecurityError: If the command is blocked by security rules
    """
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=chatops_cli --cov-report=html

# Run specific test file
poetry run pytest tests/test_command_executor.py

# Run tests with verbose output
poetry run pytest -v

# Run tests in parallel
poetry run pytest -n auto
```

### Writing Tests

- **Test structure**: Use pytest fixtures and parametrize
- **Test naming**: `test_function_name_scenario`
- **Coverage**: Aim for 80%+ coverage
- **Mocking**: Use pytest-mock for external dependencies

Example test:

```python
import pytest
from chatops_cli.core.command_executor import CommandExecutor

class TestCommandExecutor:
    def test_execute_simple_command(self, command_executor):
        """Test executing a simple command."""
        result = command_executor.execute("echo 'hello'")
        assert result.success is True
        assert "hello" in result.output
    
    def test_execute_dry_run(self, command_executor):
        """Test dry-run mode."""
        result = command_executor.execute("rm -rf /", dry_run=True)
        assert result.success is True
        assert result.command == "rm -rf /"
        # Command should not actually execute
```

### Test Fixtures

Create reusable test fixtures in `tests/conftest.py`:

```python
import pytest
from chatops_cli.core.command_executor import CommandExecutor

@pytest.fixture
def command_executor():
    """Create a command executor for testing."""
    return CommandExecutor()

@pytest.fixture
def mock_llm_provider(mocker):
    """Mock LLM provider for testing."""
    return mocker.patch('chatops_cli.core.llm_manager.LLMManager')
```

## Submitting Changes

### Workflow

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

2. **Make your changes**

```bash
# Make your code changes
# Add tests for new functionality
# Update documentation
```

3. **Run quality checks**

```bash
# Format code
poetry run black .
poetry run ruff check --fix .

# Run tests
poetry run pytest

# Run type checking
poetry run mypy chatops_cli/

# Run security checks
poetry run bandit -r chatops_cli/
poetry run safety check
```

4. **Commit your changes**

```bash
# Use conventional commit format
git commit -m "feat: add new plugin for AWS operations"
git commit -m "fix: resolve command validation issue"
git commit -m "docs: update installation guide"
```

5. **Push and create a pull request**

```bash
git push origin feature/your-feature-name
```

### Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(plugins): add AWS plugin for S3 operations
fix(core): resolve command validation edge case
docs: update API documentation with examples
test(executor): add tests for dry-run mode
```

### Pull Request Guidelines

1. **Title**: Clear and descriptive
2. **Description**: Explain what and why, not how
3. **Related issues**: Link to relevant issues
4. **Screenshots**: For UI changes
5. **Testing**: Describe how to test the changes

Example PR description:

```markdown
## Description
Adds a new AWS plugin for S3 operations including upload, download, and listing.

## Changes
- New `AwsPlugin` class with S3 operations
- Integration with AWS SDK
- Comprehensive test coverage
- Updated documentation

## Testing
- [x] Unit tests pass
- [x] Integration tests with AWS S3
- [x] Manual testing with real S3 bucket

## Related Issues
Closes #123
```

## Plugin Development

### Creating a New Plugin

1. **Create plugin file**

```python
# chatops_cli/plugins/builtin/aws_plugin.py
from chatops_cli.plugins.base import BasePlugin
from chatops_cli.core.command_executor import CommandResult

class AwsPlugin(BasePlugin):
    name = "aws"
    description = "AWS operations plugin"
    version = "1.0.0"
    author = "Your Name"
    
    def setup_commands(self):
        """Setup plugin commands."""
        self.add_command("s3-list", self.list_s3_buckets)
        self.add_command("s3-upload", self.upload_to_s3)
    
    def list_s3_buckets(self, args):
        """List S3 buckets."""
        # Implementation here
        pass
    
    def upload_to_s3(self, args):
        """Upload file to S3."""
        # Implementation here
        pass
```

2. **Add tests**

```python
# tests/test_aws_plugin.py
import pytest
from chatops_cli.plugins.builtin.aws_plugin import AwsPlugin

class TestAwsPlugin:
    def test_list_s3_buckets(self):
        """Test listing S3 buckets."""
        plugin = AwsPlugin()
        result = plugin.list_s3_buckets({})
        assert result.success is True
    
    def test_upload_to_s3(self):
        """Test uploading to S3."""
        plugin = AwsPlugin()
        result = plugin.upload_to_s3({"file": "test.txt", "bucket": "test-bucket"})
        assert result.success is True
```

3. **Register plugin**

```python
# chatops_cli/plugins/__init__.py
from .builtin.aws_plugin import AwsPlugin

__all__ = ['AwsPlugin']
```

### Plugin Guidelines

- **Single responsibility**: Each plugin should have a clear purpose
- **Error handling**: Graceful error handling with meaningful messages
- **Configuration**: Support for plugin-specific configuration
- **Documentation**: Clear documentation for all commands
- **Testing**: Comprehensive test coverage

## Documentation

### Documentation Structure

```
docs/
├── API.md              # API documentation
├── USER_GUIDE.md       # User guide
├── PLUGIN_GUIDE.md     # Plugin development guide
├── DEPLOYMENT.md       # Deployment guide
└── examples/           # Code examples
    ├── basic_usage.py
    ├── plugin_examples.py
    └── configuration_examples.py
```

### Writing Documentation

- **Clear and concise**: Write for the target audience
- **Examples**: Include practical examples
- **Code blocks**: Use syntax highlighting
- **Links**: Link to related documentation
- **Images**: Include screenshots for UI features

### Updating Documentation

- Update documentation with code changes
- Add examples for new features
- Keep installation instructions current
- Review and update API documentation

## Code Review Process

### Review Guidelines

1. **Be respectful**: Constructive feedback only
2. **Be thorough**: Check code quality, tests, and documentation
3. **Be timely**: Respond within 48 hours
4. **Be specific**: Point out specific issues with suggestions

### Review Checklist

- [ ] Code follows style guidelines
- [ ] Tests are included and pass
- [ ] Documentation is updated
- [ ] No security vulnerabilities
- [ ] Performance considerations addressed
- [ ] Error handling is appropriate
- [ ] Logging is adequate

### Review Comments

Use review comments effectively:

```markdown
**Suggestion**: Consider using a more descriptive variable name here.

**Question**: Why do we need this additional check?

**Concern**: This might cause performance issues with large datasets.

**Great work**: This is a clean implementation!
```

## Release Process

### Version Management

We use [Semantic Versioning](https://semver.org/):

- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes (backward compatible)

### Release Steps

1. **Update version**

```bash
# Update version in pyproject.toml
poetry version patch  # or minor/major
```

2. **Update changelog**

```bash
# Add release notes to CHANGELOG.md
```

3. **Create release branch**

```bash
git checkout -b release/v1.2.0
git push origin release/v1.2.0
```

4. **Create pull request**

- Update version and changelog
- Run full test suite
- Get approval from maintainers

5. **Merge and tag**

```bash
git tag v1.2.0
git push origin v1.2.0
```

6. **Publish to PyPI**

```bash
poetry build
poetry publish
```

## Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code contributions
- **Email**: For sensitive issues

### Resources

- [Project README](README.md)
- [API Documentation](docs/API.md)
- [User Guide](docs/USER_GUIDE.md)
- [Development Setup](docs/DEVELOPMENT.md)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please read our [Code of Conduct](CODE_OF_CONDUCT.md) for details.

## License

By contributing to ChatOps CLI, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to ChatOps CLI! 🚀 