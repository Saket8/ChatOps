# 📖 ChatOps CLI User Guide

A comprehensive guide to getting started with ChatOps CLI, from installation to advanced usage patterns.

## Table of Contents

- [Getting Started](#getting-started)
- [Installation](#installation)
- [First Steps](#first-steps)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Plugin Usage](#plugin-usage)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [FAQ](#faq)

## Getting Started

### What is ChatOps CLI?

ChatOps CLI is an intelligent command-line interface that combines the power of AI with traditional command execution. It allows you to:

- **Execute commands using natural language**
- **Use AI to generate complex command sequences**
- **Manage containers, systems, and applications through plugins**
- **Work with both cloud and local AI models**
- **Maintain security and audit trails**

### Key Benefits

- 🚀 **Faster Development**: Natural language to commands
- 🔒 **Security First**: Built-in validation and sandboxing
- 🤖 **AI-Powered**: Smart command generation and suggestions
- 🔌 **Extensible**: Plugin system for custom functionality
- 📊 **Comprehensive Logging**: Full audit trails and monitoring

## Installation

### System Requirements

- **Operating System**: Windows 10+, macOS 10.15+, or Linux
- **Python**: 3.11 or higher
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: 2GB free space
- **Network**: Internet connection for cloud AI features

### Step 1: Install Python

**Windows:**
```powershell
# Download from python.org or use winget
winget install Python.Python.3.11
```

**macOS:**
```bash
# Using Homebrew
brew install python@3.11

# Or download from python.org
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv
```

### Step 2: Install ChatOps CLI

**Option A: Using Poetry (Recommended)**

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Clone the repository
git clone https://github.com/Saket8/ChatOps.git
cd ChatOps

# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Install globally
poetry install --with dev
```

**Option B: Using pip**

```bash
# Clone the repository
git clone https://github.com/Saket8/ChatOps.git
cd ChatOps

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the CLI
pip install -e .
```

### Step 3: Install Ollama (Optional)

For local AI capabilities, install Ollama:

**Windows:**
```powershell
# Download from https://ollama.ai/download
# Or use winget
winget install Ollama.Ollama
```

**macOS/Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Pull a model:**
```bash
ollama pull mistral:7b
```

### Step 4: Get Groq API Key (Optional)

For cloud AI capabilities:

1. Visit [https://console.groq.com/](https://console.groq.com/)
2. Sign up for a free account
3. Create an API key
4. Note down your API key

## First Steps

### 1. Initialize Configuration

```bash
# Initialize the CLI
chatops config init

# Set up your API keys
chatops config set groq.api_key "your-groq-api-key"
chatops config set ollama.base_url "http://localhost:11434"
```

### 2. Test Installation

```bash
# Check if everything is working
chatops --version

# List available plugins
chatops plugins list

# Test basic functionality
chatops exec "echo 'Hello, ChatOps!'"
```

### 3. Start Interactive Chat

```bash
# Start the interactive chat mode
chatops chat
```

## Basic Usage

### Interactive Chat Mode

The most user-friendly way to use ChatOps CLI:

```bash
chatops chat
```

**Example conversation:**
```
Welcome to ChatOps CLI! Type 'help' for assistance.

You: Show me all running processes
ChatOps: I'll list all running processes for you...

You: Check disk usage
ChatOps: I'll check the disk usage on your system...

You: Stop the nginx container
ChatOps: I found an nginx container. This will stop it. Proceed? (y/N)
```

### Single Command Execution

Execute commands directly:

```bash
# Basic command execution
chatops exec "List all running processes"

# With specific AI provider
chatops exec --provider groq "Analyze this log file"

# Preview command without execution
chatops exec --dry-run "Delete all stopped containers"
```

### Plugin Commands

Use built-in plugins for specific tasks:

```bash
# Docker operations
chatops docker ps
chatops docker logs <container-name>
chatops docker stop <container-name>

# Kubernetes operations
chatops k8s get pods
chatops k8s describe pod <pod-name>
chatops k8s logs <pod-name>

# System operations
chatops system ps
chatops system disk
chatops system memory
```

## Advanced Features

### Configuration Profiles

Create different configurations for different environments:

```bash
# Create a development profile
chatops config profile create development
chatops config profile use development
chatops config set logging.level DEBUG

# Create a production profile
chatops config profile create production
chatops config profile use production
chatops config set logging.level WARNING
```

### Security Features

Use security features for safe command execution:

```bash
# Dry-run mode (preview only)
chatops exec --dry-run "rm -rf /tmp/important"

# Safe execution with confirmation
chatops exec --safe "docker stop production-container"

# Check command before execution
chatops exec --preview "kubectl delete pod critical-pod"
```

### Logging and Audit

Monitor your command history:

```bash
# View recent commands
chatops logs show

# Export audit trail
chatops logs export --format json > audit_trail.json

# Check security events
chatops logs security
```

### Advanced Configuration

```bash
# Set multiple configuration values
chatops config set groq.model "llama3-70b-8192"
chatops config set ollama.model "mistral:7b"
chatops config set logging.file "/var/log/chatops.log"

# Export configuration
chatops config export > config_backup.json

# Import configuration
chatops config import config_backup.json
```

## Plugin Usage

### Available Plugins

ChatOps CLI comes with several built-in plugins:

#### Docker Plugin

```bash
# Container management
chatops docker ps                    # List containers
chatops docker logs <container>      # View logs
chatops docker stop <container>      # Stop container
chatops docker start <container>     # Start container
chatops docker exec <container> <cmd> # Execute command in container
chatops docker build <path>          # Build image
chatops docker push <image>          # Push image
```

#### Kubernetes Plugin

```bash
# Pod management
chatops k8s get pods                 # List pods
chatops k8s describe pod <pod>       # Describe pod
chatops k8s logs <pod>               # View pod logs
chatops k8s port-forward <pod> <port> # Port forward

# Service management
chatops k8s get services             # List services
chatops k8s get deployments          # List deployments
chatops k8s scale deployment <name> <replicas> # Scale deployment
```

#### System Plugin

```bash
# System monitoring
chatops system ps                    # List processes
chatops system disk                  # Check disk usage
chatops system memory                # Check memory usage
chatops system network               # Check network status
chatops system cpu                   # Check CPU usage
chatops system uptime                # Check system uptime
```

### Custom Plugins

You can also create and use custom plugins:

```bash
# Load custom plugin
chatops plugins load /path/to/custom_plugin.py

# Enable/disable plugins
chatops plugins enable custom_plugin
chatops plugins disable docker

# Check plugin status
chatops plugins status
```

## Configuration

### Configuration Files

ChatOps CLI uses a hierarchical configuration system:

1. **Global config**: `~/.chatops/config.json`
2. **Project config**: `./chatops_config.json`
3. **Environment variables**: `CHATOPS_*`

### Environment Variables

Set environment variables for configuration:

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

### Configuration Commands

```bash
# View current configuration
chatops config show

# Set configuration values
chatops config set section.key "value"

# Get specific configuration
chatops config get groq.api_key

# List all configuration
chatops config list

# Reset configuration
chatops config reset
```

## Troubleshooting

### Common Issues

#### 1. "Command not found: chatops"

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Reinstall the CLI
pip install -e .

# Or use poetry
poetry install --with dev
```

#### 2. "Ollama connection failed"

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve

# Check configuration
chatops config get ollama.base_url
```

#### 3. "Groq API key invalid"

**Solution:**
```bash
# Verify API key
chatops config get groq.api_key

# Set correct API key
chatops config set groq.api_key "your-correct-api-key"

# Test API connection
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.groq.com/openai/v1/models
```

#### 4. "Permission denied" errors

**Solution:**
```bash
# Check file permissions
ls -la ~/.chatops/

# Fix permissions
chmod 600 ~/.chatops/config.json
chmod 755 ~/.chatops/

# On Windows, run as administrator if needed
```

#### 5. "Plugin not found"

**Solution:**
```bash
# List available plugins
chatops plugins list

# Check plugin status
chatops plugins status

# Enable plugin
chatops plugins enable <plugin-name>

# Reload plugins
chatops plugins reload
```

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Enable debug logging
export CHATOPS_LOG_LEVEL="DEBUG"

# Run with verbose output
chatops exec --verbose "your command"

# Check logs
tail -f ~/.chatops/chatops.log
```

### Performance Issues

```bash
# Check system resources
chatops system status

# Monitor response times
chatops exec --timing "your command"

# Use faster models
chatops config set ollama.model "mistral:7b"
chatops config set groq.model "llama3-8b-8192"
```

## Best Practices

### 1. Security Best Practices

- **Always use dry-run mode** for destructive commands
- **Review commands** before execution
- **Use safe execution mode** for production environments
- **Regularly check audit logs** for suspicious activity
- **Keep API keys secure** and rotate them regularly

### 2. Performance Optimization

- **Use appropriate models** for your use case
- **Cache frequently used commands** in plugins
- **Monitor resource usage** during heavy operations
- **Use local models** for sensitive data
- **Optimize prompts** for better AI responses

### 3. Configuration Management

- **Use profiles** for different environments
- **Backup configurations** regularly
- **Version control** your configuration files
- **Document custom settings** for team members
- **Test configurations** in development first

### 4. Plugin Development

- **Follow naming conventions** for consistency
- **Implement proper error handling** in plugins
- **Add comprehensive documentation** for custom plugins
- **Test plugins thoroughly** before deployment
- **Use the plugin template** for new plugins

### 5. Logging and Monitoring

- **Set appropriate log levels** for your environment
- **Regularly review audit trails** for compliance
- **Monitor security events** and investigate anomalies
- **Export logs** for long-term storage
- **Set up log rotation** to manage disk space

## FAQ

### Q: Can I use ChatOps CLI without internet?

**A:** Yes! You can use local Ollama models for offline operation. Only cloud AI features require internet connectivity.

### Q: Is it safe to run commands generated by AI?

**A:** ChatOps CLI includes multiple safety features:
- Command validation and blacklisting
- Dry-run mode for preview
- Confirmation prompts for destructive operations
- Sandboxed execution environments

### Q: How do I add my own commands?

**A:** You can create custom plugins or use the plugin system to add new commands. See the API documentation for examples.

### Q: Can I use ChatOps CLI in CI/CD pipelines?

**A:** Yes! ChatOps CLI is designed to work in automated environments. Use the `--non-interactive` flag for automated execution.

### Q: How do I update ChatOps CLI?

**A:** Pull the latest changes and reinstall:
```bash
git pull origin main
poetry install --with dev
```

### Q: What AI models are supported?

**A:** ChatOps CLI supports:
- **Groq**: llama3-8b, llama3-70b, and other models
- **Ollama**: Any model available in Ollama library
- **Custom**: You can add support for other providers

### Q: How do I contribute to the project?

**A:** We welcome contributions! See the [Contributing Guide](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute code.

---

For more detailed information, refer to the [API Documentation](API.md) and [Main README](README.md). 