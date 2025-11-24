# Contributing to FlowForge (DWP)

First off, thank you for considering contributing to FlowForge! It's people like you that make FlowForge such a great tool.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Process](#development-process)
- [Plugin Development](#plugin-development)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

This project and everyone participating in it is governed by our commitment to fostering an open and welcoming environment. Please be respectful and constructive in all interactions.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards others

**Unacceptable behavior includes:**
- Harassment, trolling, or discriminatory comments
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 14+ and npm
- Docker and Docker Compose
- Git
- A GitHub account

### Development Setup

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/dwp.git
   cd dwp
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/pedroanisio/dwp.git
   ```

4. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   npm install
   ```

6. **Build frontend assets**:
   ```bash
   npm run build-css
   ```

7. **Run tests to verify setup**:
   ```bash
   pytest
   ```

8. **Start the development server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report, please check existing issues to avoid duplicates.

**When filing a bug, include:**
- **Clear title**: Descriptive summary of the issue
- **Description**: Detailed explanation of the problem
- **Steps to reproduce**: Numbered steps to recreate the issue
- **Expected behavior**: What you expected to happen
- **Actual behavior**: What actually happened
- **Environment**: OS, Python version, Docker version
- **Logs/Screenshots**: Any relevant error messages or screenshots
- **Possible solution**: If you have ideas on how to fix it

**Example bug report**:
```
Title: Chain execution fails with circular dependency

Description:
When creating a chain with nodes A → B → C → A, the validation
passes but execution hangs indefinitely.

Steps to Reproduce:
1. Go to /chain-builder
2. Add nodes with IDs: node-a, node-b, node-c
3. Connect: A → B, B → C, C → A
4. Save chain
5. Execute chain with any input

Expected: Validation should reject circular dependencies
Actual: Validation passes, execution hangs

Environment:
- OS: Ubuntu 22.04
- Python: 3.11
- Docker: 24.0.5

Logs:
[Paste relevant log output here]
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues.

**Include:**
- **Clear title**: Brief description of the enhancement
- **Use case**: Why is this enhancement needed?
- **Detailed description**: How should it work?
- **Alternatives**: Other solutions you've considered
- **Mockups/Examples**: Visual aids if applicable

### Contributing Code

1. **Pick an issue** or create one to discuss your changes
2. **Create a branch** from `main` for your work
3. **Make your changes** following our coding standards
4. **Write/update tests** to cover your changes
5. **Update documentation** as needed
6. **Submit a pull request**

---

## Development Process

### Branching Strategy

We use **feature branch workflow**:

```
main (production-ready)
  ↓
feature/your-feature-name (your changes)
```

**Branch naming conventions**:
- `feature/` - New features (e.g., `feature/plugin-marketplace`)
- `fix/` - Bug fixes (e.g., `fix/chain-validation-error`)
- `docs/` - Documentation changes (e.g., `docs/improve-readme`)
- `refactor/` - Code refactoring (e.g., `refactor/chain-executor`)
- `test/` - Test additions/fixes (e.g., `test/add-plugin-tests`)

### Workflow

1. **Sync with upstream**:
   ```bash
   git checkout main
   git pull upstream main
   ```

2. **Create feature branch**:
   ```bash
   git checkout -b feature/my-awesome-feature
   ```

3. **Make changes and commit**:
   ```bash
   git add .
   git commit -m "feat: add awesome feature"
   ```

4. **Keep branch updated**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/my-awesome-feature
   ```

6. **Create pull request** on GitHub

---

## Plugin Development

### Creating a New Plugin

Plugins are the core extensibility mechanism. Here's how to create one:

#### 1. Create Plugin Directory
```bash
mkdir app/plugins/my_plugin
cd app/plugins/my_plugin
touch __init__.py manifest.json plugin.py
```

#### 2. Write manifest.json
```json
{
  "id": "my_plugin",
  "name": "My Plugin",
  "description": "What my plugin does",
  "version": "1.0.0",
  "author": "Your Name",
  "category": "Text Processing",
  "tags": ["text", "processing"],
  "inputs": [
    {
      "name": "text",
      "type": "text",
      "label": "Input Text",
      "required": true,
      "validation": {
        "minLength": 1,
        "maxLength": 10000
      }
    }
  ],
  "outputs": [
    {
      "name": "result",
      "type": "text",
      "description": "Processed text"
    }
  ],
  "dependencies": {
    "external": [],
    "python": []
  }
}
```

#### 3. Implement plugin.py
```python
from typing import Dict, Any, Type
from pydantic import Field
from ...models.plugin import BasePlugin, BasePluginResponse

class MyPluginResponse(BasePluginResponse):
    """Response model for My Plugin"""
    result: str = Field(..., description="Processed text")
    word_count: int = Field(..., description="Number of words")

class Plugin(BasePlugin):
    """My Plugin implementation"""

    @classmethod
    def get_response_model(cls) -> Type[BasePluginResponse]:
        return MyPluginResponse

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin logic"""
        text = data.get("text", "")

        # Your processing logic here
        processed = text.upper()
        word_count = len(text.split())

        return {
            "result": processed,
            "word_count": word_count
        }
```

#### 4. Add Tests
```python
# tests/unit/test_my_plugin.py
import pytest
from app.plugins.my_plugin.plugin import Plugin

def test_my_plugin_execution():
    plugin = Plugin()
    result = plugin.execute({"text": "hello world"})

    assert result["result"] == "HELLO WORLD"
    assert result["word_count"] == 2

def test_my_plugin_response_model():
    assert Plugin.get_response_model() is not None
```

#### 5. Test Your Plugin
```bash
# Reload plugins
curl -X POST http://localhost:8000/api/refresh-plugins

# Test execution
curl -X POST http://localhost:8000/api/plugin/my_plugin/execute \
  -H "Content-Type: application/json" \
  -d '{"text": "hello world"}'
```

### Plugin Best Practices

- **✅ DO**: Define clear Pydantic response models
- **✅ DO**: Validate all inputs thoroughly
- **✅ DO**: Handle errors gracefully
- **✅ DO**: Write comprehensive tests
- **✅ DO**: Document your plugin in manifest.json

- **❌ DON'T**: Use blocking I/O without thread pools
- **❌ DON'T**: Hardcode file paths or credentials
- **❌ DON'T**: Return unvalidated data
- **❌ DON'T**: Forget to specify dependencies

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

- **Line length**: 100 characters (not 79)
- **Imports**: Use absolute imports
- **Type hints**: Required for public functions
- **Docstrings**: Google style for public APIs

### Code Formatting

We use **Black** and **isort**:

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Check (CI will run this)
black --check app/ tests/
isort --check-only app/ tests/
```

### Linting

We use **flake8** for linting:

```bash
flake8 app/ tests/ --max-line-length=100
```

### Example Code Style

```python
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    """Clear, descriptive docstring.

    Args:
        name: Description of name parameter
        count: Description of count parameter

    Returns:
        Description of return value

    Raises:
        ValueError: When invalid input is provided
    """
    name: str = Field(..., description="User-friendly description")
    count: int = Field(default=0, ge=0, description="Non-negative count")

    def process(self, data: Dict[str, Any]) -> List[str]:
        """Process data and return results.

        This is a more detailed explanation of what the method does,
        including any important details or edge cases.
        """
        if not data:
            raise ValueError("Data cannot be empty")

        results: List[str] = []
        for key, value in data.items():
            results.append(f"{key}={value}")

        return results
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── test_plugins/
│   ├── test_chain_executor.py
│   └── test_auth.py
└── integration/             # Integration tests
    └── test_api.py
```

### Writing Tests

```python
import pytest
from app.core.plugin_manager import PluginManager

@pytest.fixture
def plugin_manager():
    """Create a PluginManager instance for testing"""
    return PluginManager()

def test_plugin_discovery(plugin_manager):
    """Test that all plugins are discovered"""
    plugins = plugin_manager.get_all_plugins()
    assert len(plugins) > 0
    assert all(p.get("id") for p in plugins)

def test_plugin_execution(plugin_manager):
    """Test plugin execution"""
    result = plugin_manager.execute_plugin(
        "text_stat",
        {"text": "hello world"}
    )
    assert result["success"] is True
    assert "word_count" in result["data"]
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_plugins.py

# Run tests matching pattern
pytest -k "test_plugin"

# Run with verbose output
pytest -v
```

### Test Coverage

- **Minimum**: 70% overall coverage
- **Goal**: 80%+ coverage
- **Critical paths**: 100% coverage for auth, chain execution, plugin system

---

## Documentation

### What to Document

- **Public APIs**: All public functions and classes
- **Configuration**: Environment variables and settings
- **Plugins**: Usage examples and parameters
- **Architecture**: Design decisions and patterns

### Documentation Style

```python
def execute_chain(chain_id: str, input_data: Dict[str, Any]) -> ChainResult:
    """Execute a plugin chain with the given input data.

    This function loads the chain definition, validates it, and executes
    all nodes in topological order. Nodes that have no dependencies are
    executed in parallel.

    Args:
        chain_id: Unique identifier for the chain to execute
        input_data: Input data to pass to the chain's entry nodes

    Returns:
        ChainResult object containing execution status, output data,
        execution time, and per-node results.

    Raises:
        ChainNotFoundError: If the chain_id doesn't exist
        ValidationError: If the chain structure is invalid
        ExecutionError: If execution fails

    Example:
        >>> result = execute_chain("my-chain-123", {"text": "hello"})
        >>> print(result.success)
        True
    """
    pass
```

---

## Commit Messages

We follow **Conventional Commits**:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(plugins): add sentiment analysis plugin

Implemented a new plugin that performs sentiment analysis on text
using NLTK's VADER sentiment analyzer.

- Added manifest.json with plugin configuration
- Implemented Plugin class with execute method
- Added unit tests with 90% coverage
- Updated documentation

Closes #123
```

```
fix(chain-executor): handle circular dependencies

Added cycle detection in chain validation to prevent infinite loops
during execution. Now throws ValidationError with clear message.

Fixes #456
```

```
docs(readme): update installation instructions

Updated README with clearer Docker setup steps and added
troubleshooting section for common issues.
```

---

## Pull Request Process

### Before Submitting

1. **✅ Tests pass**: Run `pytest` locally
2. **✅ Code formatted**: Run `black` and `isort`
3. **✅ Linter happy**: Run `flake8`
4. **✅ Docs updated**: Update relevant documentation
5. **✅ CHANGELOG updated**: Add entry if user-facing change

### PR Template

```markdown
## Description
Brief description of what this PR does.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran and how to reproduce them.

- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code where needed
- [ ] I have updated the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix/feature works
- [ ] New and existing tests pass locally
- [ ] Any dependent changes have been merged

## Screenshots (if applicable)
Add screenshots to help explain your changes.

## Related Issues
Closes #issue_number
```

### Review Process

1. **Automated checks**: CI must pass (tests, linting)
2. **Code review**: At least one maintainer approval
3. **Documentation review**: Docs must be clear and complete
4. **Testing verification**: Tests must cover new code

### After Merge

- Delete your feature branch
- Update your local main branch
- Celebrate! 🎉

---

## Questions?

- **General questions**: Open a GitHub Discussion
- **Bug reports**: Create a GitHub Issue
- **Feature requests**: Create a GitHub Issue with [Feature Request] tag
- **Security issues**: Email directly (see SECURITY.md)

---

## Recognition

Contributors are recognized in several ways:
- Listed in README contributors section
- Mentioned in release notes
- GitHub contributor badge

Thank you for contributing to FlowForge! 🚀
