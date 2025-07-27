# 🚀 ChatOps CLI

**Offline ChatOps CLI with LangChain + Local LLM Integration**

A powerful command-line interface that combines the capabilities of LangChain with local LLM providers (Ollama) and cloud APIs (Groq) to create an intelligent, offline-capable ChatOps solution.

[![CI](https://github.com/Saket8/ChatOps/actions/workflows/ci.yml/badge.svg)](https://github.com/Saket8/ChatOps/actions/workflows/ci.yml)
[![Security](https://github.com/Saket8/ChatOps/actions/workflows/security.yml/badge.svg)](https://github.com/Saket8/ChatOps/actions/workflows/security.yml)
[![Code Quality](https://github.com/Saket8/ChatOps/actions/workflows/code-quality.yml/badge.svg)](https://github.com/Saket8/ChatOps/actions/workflows/code-quality.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- 🤖 **Dual LLM Support**: Groq API (cloud) + Ollama (local)
- 🔧 **Plugin Architecture**: Extensible plugin system for custom commands
- 🐳 **Container Integration**: Built-in Docker and Kubernetes plugins
- 🔒 **Security First**: Command validation, dry-run mode, and sandboxing
- 📝 **Comprehensive Logging**: Audit trails and security event monitoring
- ⚙️ **Flexible Configuration**: Multi-provider config with profiles
- 🧪 **Testing Framework**: Complete test suite with coverage reporting
- 🚀 **CI/CD Ready**: GitHub Actions workflows for automated testing and deployment

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Plugin Development](#plugin-development)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## 🛠️ Installation

### Prerequisites

- Python 3.11 or higher
- Poetry (recommended) or pip
- Ollama (for local LLM support)
- Groq API key (optional, for cloud LLM support)

### Install with Poetry (Recommended)

```bash
# Clone the repository
git clone https://github.com/Saket8/ChatOps.git
cd ChatOps

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Install the CLI globally
poetry install --with dev
```

### Install with pip

```bash
# Clone the repository
git clone https://github.com/Saket8/ChatOps.git
cd ChatOps

# Install dependencies
pip install -r requirements.txt

# Install the CLI
pip install -e .
```

### Install Ollama (for local LLM support)

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# Download from https://ollama.ai/download

# Pull a model
ollama pull mistral:7b
```

## 🚀 Quick Start

### 1. Basic Setup

```bash
# Initialize configuration
chatops config init

# Set up your LLM providers
chatops config set groq.api_key "your-groq-api-key"
chatops config set ollama.base_url "http://localhost:11434"
```

### 2. Start Chatting

```bash
# Interactive chat mode
chatops chat

# Single command execution
chatops exec "List all running Docker containers"
```

### 3. Use Plugins

```bash
# Docker operations
chatops docker ps
chatops docker logs <container-name>

# Kubernetes operations
chatops k8s get pods
chatops k8s describe pod <pod-name>
```

## ⚙️ Configuration

### Configuration Files

The CLI uses a hierarchical configuration system:

- **Global config**: `~/.chatops/config.json`
- **Project config**: `./chatops_config.json`
- **Environment variables**: `CHATOPS_*`

### Configuration Commands

```bash
# View current configuration
chatops config show

# Set configuration values
chatops config set groq.api_key "your-key"
chatops config set ollama.model "mistral:7b"

# Create configuration profiles
chatops config profile create production
chatops config profile use production

# Export/Import configuration
chatops config export > config_backup.json
chatops config import config_backup.json
```

### Environment Variables

```bash
# LLM Configuration
export CHATOPS_GROQ_API_KEY="your-groq-api-key"
export CHATOPS_OLLAMA_BASE_URL="http://localhost:11434"
export CHATOPS_OLLAMA_MODEL="mistral:7b"

# Logging Configuration
export CHATOPS_LOG_LEVEL="INFO"
export CHATOPS_LOG_FILE="/path/to/chatops.log"

# Security Configuration
export CHATOPS_DRY_RUN="true"
export CHATOPS_CONFIRM_DESTRUCTIVE="true"
```

## 📖 Usage

### Interactive Chat Mode

```bash
# Start interactive chat
chatops chat

# Example conversation:
# You: "Show me all Docker containers"
# ChatOps: "I'll list all Docker containers for you..."
# 
# You: "Stop the nginx container"
# ChatOps: "I'll stop the nginx container. This will terminate the container..."
```

### Command Execution

```bash
# Execute single commands
chatops exec "List all running processes"
chatops exec "Check disk usage on /home"

# With specific LLM provider
chatops exec --provider groq "Analyze this log file"
chatops exec --provider ollama "Explain this error message"
```

### Plugin Commands

```bash
# Docker Plugin
chatops docker ps                    # List containers
chatops docker logs <container>      # View logs
chatops docker stop <container>      # Stop container
chatops docker exec <container> <cmd> # Execute command in container

# Kubernetes Plugin
chatops k8s get pods                 # List pods
chatops k8s describe pod <pod>       # Describe pod
chatops k8s logs <pod>               # View pod logs
chatops k8s port-forward <pod> <port> # Port forward

# System Plugin
chatops system ps                    # List processes
chatops system disk                  # Check disk usage
chatops system memory                # Check memory usage
chatops system network               # Check network status
```

### Advanced Features

```bash
# Dry-run mode (preview commands without execution)
chatops exec --dry-run "Delete all stopped containers"

# Verbose logging
chatops exec --verbose "Analyze system performance"

# Use specific configuration profile
chatops exec --profile production "Deploy to production"

# Save conversation history
chatops chat --save-history chat_session.json
```

## 🔌 Plugin Development

### Creating a Custom Plugin

```python
# plugins/custom_plugin.py
from chatops_cli.plugins.base import BasePlugin
from chatops_cli.core.command_executor import CommandResult

class CustomPlugin(BasePlugin):
    name = "custom"
    description = "Custom plugin for specific operations"
    
    def setup_commands(self):
        self.add_command("hello", self.hello_world)
        self.add_command("status", self.get_status)
    
    def hello_world(self, args):
        """Say hello to the world"""
        return CommandResult(
            success=True,
            output="Hello, World!",
            command="echo 'Hello, World!'"
        )
    
    def get_status(self, args):
        """Get system status"""
        return CommandResult(
            success=True,
            output="System is running normally",
            command="echo 'System status: OK'"
        )
```

### Plugin Registration

```python
# Register your plugin in main.py
from chatops_cli.plugins.custom_plugin import CustomPlugin

def main():
    # ... existing code ...
    plugin_manager.register_plugin(CustomPlugin())
```

### Plugin Configuration

```json
{
  "plugins": {
    "custom": {
      "enabled": true,
      "config": {
        "custom_setting": "value"
      }
    }
  }
}
```

## 📚 API Reference

### Core Classes

#### `ChatOpsCLI`
Main CLI application class.

```python
from chatops_cli.main import ChatOpsCLI

cli = ChatOpsCLI()
cli.run()
```

#### `LLMProvider`
Base class for LLM providers.

```python
from chatops_cli.core.llm_provider import LLMProvider

class CustomProvider(LLMProvider):
    def generate_response(self, prompt: str) -> str:
        # Implementation
        pass
```

#### `Plugin`
Base class for plugins.

```python
from chatops_cli.plugins.base import BasePlugin

class CustomPlugin(BasePlugin):
    def setup_commands(self):
        # Register commands
        pass
```

### Configuration Management

```python
from chatops_cli.config.manager import ConfigManager

config = ConfigManager()
config.set("section.key", "value")
value = config.get("section.key")
```

### Command Execution

```python
from chatops_cli.core.command_executor import CommandExecutor

executor = CommandExecutor()
result = executor.execute("ls -la")
print(result.output)
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve

# Check available models
ollama list
```

#### 2. Groq API Issues

```bash
# Verify API key
chatops config show groq.api_key

# Test API connection
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.groq.com/openai/v1/models
```

#### 3. Permission Issues

```bash
# Check file permissions
ls -la ~/.chatops/

# Fix permissions
chmod 600 ~/.chatops/config.json
```

#### 4. Plugin Loading Issues

```bash
# Check plugin status
chatops plugins list

# Enable/disable plugins
chatops plugins enable docker
chatops plugins disable kubernetes
```

### Debug Mode

```bash
# Enable debug logging
export CHATOPS_LOG_LEVEL="DEBUG"
chatops exec --verbose "your command"

# Check logs
tail -f ~/.chatops/chatops.log
```

### Performance Issues

```bash
# Check system resources
chatops system status

# Monitor LLM response times
chatops exec --timing "your command"

# Use faster models
chatops config set ollama.model "mistral:7b"
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/Saket8/ChatOps.git
cd ChatOps
poetry install --with dev

# Run tests
poetry run pytest

# Run linting
poetry run black .
poetry run ruff check .
poetry run mypy chatops_cli/

# Run security checks
poetry run bandit -r chatops_cli/
poetry run safety check
```

### Code Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [Ruff](https://ruff.rs/) for linting
- Use [MyPy](https://mypy.readthedocs.io/) for type checking

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## �� Acknowledgments

- [LangChain](https://langchain.com/) for the LLM integration framework
- [Ollama](https://ollama.ai/) for local LLM support
- [Groq](https://groq.com/) for cloud LLM API
- [Click](https://click.palletsprojects.com/) for CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output

## 📞 Support

- 📧 Email: [your-email@example.com]
- 🐛 Issues: [GitHub Issues](https://github.com/Saket8/ChatOps/issues)
- 📖 Documentation: [Wiki](https://github.com/Saket8/ChatOps/wiki)
- 💬 Discussions: [GitHub Discussions](https://github.com/Saket8/ChatOps/discussions)

---

**Made with ❤️ by the ChatOps CLI Team** 