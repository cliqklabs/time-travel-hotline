# Contributing to Time Travel Hotline 🕰️📞

Thank you for your interest in contributing to the Time Travel Hotline project! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### **Reporting Bugs**
- Use the [GitHub Issues](https://github.com/yourusername/time-travel-hotline/issues) page
- Include detailed steps to reproduce the bug
- Provide system information (OS, Python version, hardware)
- Include error messages and logs

### **Suggesting Features**
- Use the [GitHub Discussions](https://github.com/yourusername/time-travel-hotline/discussions) page
- Describe the feature and its use case
- Consider implementation complexity
- Check if similar features already exist

### **Code Contributions**
1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes
4. **Test** your changes thoroughly
5. **Commit** with clear messages (`git commit -m 'Add amazing feature'`)
6. **Push** to your branch (`git push origin feature/amazing-feature`)
7. **Open** a Pull Request

## 🛠️ Development Setup

### **Prerequisites**
- Python 3.8+
- Git
- API keys for OpenAI, Deepgram, and ElevenLabs

### **Local Development**
```bash
# Clone your fork
git clone https://github.com/yourusername/time-travel-hotline.git
cd time-travel-hotline

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up API keys
export OPENAI_API_KEY="your-key"
export DEEPGRAM_API_KEY="your-key"
export ELEVEN_API_KEY="your-key"

# Run tests
python -m pytest

# Run linting
flake8 .
```

## 📝 Code Style

### **Python Style Guide**
- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and under 50 lines when possible

### **Commit Messages**
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor" not "Moves cursor")
- Limit first line to 72 characters
- Reference issues and pull requests when applicable

### **Example Commit Messages**
```
Add text mode for quiet testing

- Add --text-mode command line argument
- Implement console input for questions
- Skip audio validation in text mode
- Add proper error handling

Fixes #123
```

## 🧪 Testing

### **Running Tests**
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=.

# Run specific test file
python -m pytest test_hotline.py

# Run with verbose output
python -m pytest -v
```

### **Writing Tests**
- Test both success and failure cases
- Mock external API calls
- Test edge cases and error conditions
- Use descriptive test names

### **Example Test**
```python
def test_character_selection():
    """Test that character selection works correctly."""
    # Arrange
    expected_character = "Albert Einstein"
    
    # Act
    result = get_character_by_number("3")
    
    # Assert
    assert result["name"] == expected_character
```

## 🔧 Adding New Features

### **Adding New Characters**
1. Add character to `CHARACTERS` dictionary
2. Add system prompt to `SYSTEM_PROMPTS`
3. Test character responses
4. Update documentation

### **Adding New Hardware Support**
1. Add hardware detection logic
2. Implement GPIO functions
3. Add error handling
4. Update documentation and pin mappings

### **Adding New Audio Features**
1. Test with different audio devices
2. Consider latency implications
3. Add configuration options
4. Update audio validation

## 📚 Documentation

### **Code Documentation**
- Add docstrings to all functions
- Include parameter types and return values
- Provide usage examples
- Document exceptions and error conditions

### **User Documentation**
- Update README.md for new features
- Add examples and use cases
- Include troubleshooting steps
- Update hardware setup guides

## 🔒 Security

### **API Key Security**
- Never commit API keys to the repository
- Use environment variables for sensitive data
- Add new API keys to .gitignore
- Document required environment variables

### **Code Security**
- Validate all user inputs
- Sanitize data before processing
- Use secure random number generation
- Follow OWASP security guidelines

## 🚀 Release Process

### **Before Release**
1. Update version numbers
2. Update CHANGELOG.md
3. Run full test suite
4. Update documentation
5. Create release notes

### **Release Steps**
1. Create release branch
2. Update version in code
3. Tag the release
4. Create GitHub release
5. Update documentation

## 📞 Getting Help

### **Resources**
- [GitHub Issues](https://github.com/yourusername/time-travel-hotline/issues)
- [GitHub Discussions](https://github.com/yourusername/time-travel-hotline/discussions)
- [Project Wiki](https://github.com/yourusername/time-travel-hotline/wiki)

### **Community Guidelines**
- Be respectful and inclusive
- Help others learn and grow
- Share knowledge and experiences
- Follow the project's code of conduct

## 🙏 Recognition

Contributors will be recognized in:
- Project README.md
- Release notes
- Contributor hall of fame
- GitHub contributors page

Thank you for contributing to the Time Travel Hotline project! 🕰️📞
