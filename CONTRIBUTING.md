# Contributing to DDL Wizard

Thank you for your interest in contributing to DDL Wizard! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues
- Check existing issues before creating a new one
- Use the issue templates when available
- Provide detailed reproduction steps
- Include environment information (Python version, database version, OS)

### Feature Requests
- Describe the use case and problem you're trying to solve
- Explain why the feature would be valuable to other users
- Consider backward compatibility implications

### Code Contributions
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes following the coding standards
4. Add tests for new functionality
5. Update documentation as needed
6. Commit with clear, descriptive messages
7. Push to your fork: `git push origin feature/amazing-feature`
8. Create a Pull Request

## 🏗️ Development Setup

### Prerequisites
- Python 3.8+
- MariaDB or MySQL for testing
- Git

### Local Development
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/ddlwizard.git
cd ddlwizard

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (if available)
pip install -r requirements-dev.txt
```

### Testing
```bash
# Run tests (when test suite is available)
python -m pytest tests/

# Manual testing
python main.py --help

# Test with sample databases
python main.py --mode extract --source-host localhost --source-user test --source-password test --source-schema test_db
```

## 📝 Coding Standards

### Python Style
- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to all public functions and classes
- Keep functions focused and reasonably sized
- Use type hints where appropriate

### Code Structure
```python
"""
Module docstring explaining the purpose and functionality.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ExampleClass:
    """Class docstring explaining purpose and usage."""
    
    def __init__(self, parameter: str):
        """Initialize with clear parameter documentation."""
        self.parameter = parameter
    
    def public_method(self, arg: str) -> Optional[str]:
        """
        Public method with clear docstring.
        
        Args:
            arg: Description of the argument
            
        Returns:
            Description of return value
            
        Raises:
            ValueError: When specific condition occurs
        """
        try:
            # Implementation
            return self._private_method(arg)
        except Exception as e:
            logger.error(f"Error in public_method: {e}")
            raise
    
    def _private_method(self, arg: str) -> str:
        """Private method for internal use."""
        return f"processed_{arg}"
```

### Documentation
- Update README.md for new features
- Add docstrings to all public APIs
- Include usage examples for new functionality
- Update configuration documentation when adding new options

## 🧪 Testing Guidelines

### Test Categories
- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Database Tests**: Test with real database connections

### Test Structure
```python
import pytest
from unittest.mock import Mock, patch

class TestDDLAnalyzer:
    """Test suite for DDL Analyzer functionality."""
    
    def test_parse_create_table_basic(self):
        """Test basic CREATE TABLE parsing."""
        # Arrange
        ddl = "CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(100))"
        analyzer = DDLAnalyzer()
        
        # Act
        result = analyzer.parse_create_table(ddl)
        
        # Assert
        assert result.name == "users"
        assert len(result.columns) == 2
        assert "id" in result.columns
        assert "name" in result.columns
    
    @patch('ddl_analyzer.database_connection')
    def test_with_database_mock(self, mock_db):
        """Test with mocked database connection."""
        # Setup mock
        mock_db.execute.return_value = [{'table': 'users'}]
        
        # Test implementation
        pass
```

## 🔍 Code Review Process

### What We Look For
- **Functionality**: Does the code work as intended?
- **Code Quality**: Is it readable, maintainable, and well-structured?
- **Performance**: Are there any obvious performance issues?
- **Security**: Are there potential security vulnerabilities?
- **Documentation**: Is the code properly documented?
- **Tests**: Are there adequate tests for the new functionality?

### Review Checklist
- [ ] Code follows project style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] No breaking changes without deprecation warnings
- [ ] Error handling is appropriate
- [ ] Logging is consistent with existing patterns

## 🚀 Release Process

### Version Numbering
We follow Semantic Versioning (SemVer):
- **Major** (X.0.0): Breaking changes
- **Minor** (0.X.0): New features, backward compatible
- **Patch** (0.0.X): Bug fixes, backward compatible

### Release Checklist
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] Version numbers are bumped
- [ ] Release notes are prepared

## 📋 Issue Labels

### Type Labels
- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements or additions to documentation
- `question`: Further information is requested
- `help wanted`: Extra attention is needed
- `good first issue`: Good for newcomers

### Priority Labels
- `priority: critical`: Critical issues that need immediate attention
- `priority: high`: High priority issues
- `priority: medium`: Medium priority issues
- `priority: low`: Low priority issues

### Component Labels
- `component: parser`: DDL parsing functionality
- `component: comparison`: Schema comparison logic
- `component: migration`: Migration generation
- `component: safety`: Safety analysis features
- `component: config`: Configuration management
- `component: visualization`: Documentation and visualization

## 🌟 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes for significant contributions
- GitHub contributors page

## 📞 Getting Help

### Communication Channels
- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Code Reviews**: For implementation feedback

### Mentoring
- New contributors are welcome and encouraged
- Maintainers are available to help with questions
- Consider starting with issues labeled "good first issue"

## 📄 Legal

### License Agreement
By contributing to DDL Wizard, you agree that your contributions will be licensed under the MIT License.

### Code of Conduct
Please note that this project follows a Code of Conduct. By participating, you are expected to uphold this code.

---

Thank you for contributing to DDL Wizard! Your efforts help make database schema management better for everyone. 🧙‍♂️✨
