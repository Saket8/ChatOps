# ChatOps CLI

Offline ChatOps CLI with LangChain + Local LLM

## Overview

A Python-based command-line assistant designed for DevOps and Cloud engineers who need to perform system administration tasks through natural language commands. The tool provides both **offline plugin-based commands** for speed and **AI-powered command generation** for complex scenarios, featuring comprehensive cross-platform support for Windows PowerShell, Linux, and macOS.

**Key Features:**
- **Hybrid Command Generation**: Fast local plugins for common tasks + smart AI for complex scenarios
- **Cross-Platform Intelligence**: Automatically generates Windows PowerShell, Linux, or macOS commands
- **Extensible Plugin System**: Add new command categories and specialized operations
- **Multiple LLM Backends**: Choose between fast cloud API or private local models
- **Natural Language Interface**: Ask questions in plain English, get executable commands

## Project Status

🚀 **Active Development** - Core functionality implemented and working

📊 **Project Dashboard**: [https://saket8.github.io/ChatOps/](https://saket8.github.io/ChatOps/)

## Features

### ✅ **Implemented Features**

- **🔌 Plugin Architecture**: Extensible system with automatic discovery and lifecycle management
- **🪟 Cross-Platform Commands**: 
  - Windows: PowerShell commands (`Get-Process`, `Get-WmiObject`, etc.)
  - Linux/macOS: Bash commands (`ps`, `df`, `ls`, etc.)
- **🤖 Dual LLM Support**:
  - **Groq API**: Fast, free cloud inference (recommended)
  - **Local Ollama**: Privacy-focused local models
- **⚡ Hybrid Execution**:
  - Simple commands → Plugin system (instant)
  - Complex commands → AI generation (smart)
- **📋 TaskMaster Integration**: Comprehensive project management system
- **🛡️ OS Detection**: Automatic platform detection and command mapping
- **🎯 SystemPlugin**: Built-in plugin for system monitoring commands

### 🚧 **Planned Features**

- **Safety Features**: Command validation, dry-run mode, and operation rollback
- **Docker Plugin**: Container operations and management
- **Interactive Chat Mode**: Conversational command interface  
- **Logging & Audit**: Comprehensive command tracking and security events
- **Testing Framework**: Automated testing for plugins and commands
- **CI/CD Pipeline**: GitHub Actions for automated testing and deployment

## Architecture Overview

### **Core Components**

```
chatops_cli/
├── cli/main.py              # Click-based CLI interface & context management
├── core/
│   ├── groq_client.py       # Groq API integration with OS-aware prompts
│   ├── ollama_client.py     # Local Ollama LLM integration  
│   ├── langchain_integration.py  # LangChain components & prompt engineering
│   └── os_detection.py      # Cross-platform OS detection & command mapping
├── plugins/
│   ├── base.py              # Abstract plugin interfaces & decorators
│   ├── manager.py           # Plugin discovery, loading & lifecycle
│   └── builtin/
│       └── system_plugin.py # Built-in system monitoring commands
├── settings.py              # Centralized configuration management
└── main.py                  # Application entry point
```

### **Plugin System Design**

The extensible plugin architecture supports:

- **Abstract Base Classes**: `BasePlugin`, `CommandPlugin` for consistent interfaces
- **Automatic Discovery**: Plugins discovered from `builtin/` and external directories
- **Lifecycle Management**: `initialize()`, `cleanup()`, hot-reloading support
- **Metadata System**: Rich plugin information with capabilities and priorities
- **Command Routing**: Smart handler selection based on user input patterns

### **Cross-Platform Command Mapping**

The OS detection system provides intelligent command translation:

```python
# Example: "check disk usage"
Windows → Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, Size, FreeSpace
Linux   → df -h
macOS   → df -h
```

**Supported Command Types:**
- Disk usage monitoring
- Process listing and management  
- Memory usage analysis
- Network interface information
- File operations and searching
- Service status monitoring

## Development Setup

### **Prerequisites**

- **Python 3.11+** with Poetry for dependency management
- **Optional**: Ollama for local LLM models
- **Optional**: Groq API key for cloud inference (free tier available)

### **Installation**

```bash
# Clone the repository
git clone https://github.com/Saket8/ChatOps.git
cd ChatOps

# Install dependencies with Poetry
python -m poetry install

# Set up environment (optional - for AI features)
cp .env.example .env
# Edit .env with your API keys
```

### **Configuration**

Create a `.env` file for AI integration:

```bash
# Groq API (Recommended - Fast & Free)
GROQ_API_KEY=your_groq_api_key_here
DEFAULT_LLM_PROVIDER=groq
GROQ_MODEL=llama3-8b-8192

# Or Local Ollama  
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b
DEFAULT_LLM_PROVIDER=ollama
```

**Get Free Groq API Key**: See [SETUP_GROQ.md](SETUP_GROQ.md) for detailed instructions.

### **Usage Examples**

```bash
# Test plugin system (works offline)
python -m poetry run python -m chatops_cli plugins --list

# Test OS-appropriate commands
python -m poetry run python -m chatops_cli ask "check disk usage" --dry-run

# View available commands  
python -m poetry run python -m chatops_cli ask "help"

# Test AI integration (requires API key)
python -m poetry run python -m chatops_cli ask "find files larger than 100MB" --dry-run
```

### **Quick Start**

```bash
# Basic usage - works without AI setup
python -m poetry run python -m chatops_cli plugins --list

# With AI integration (requires API key)
python -m poetry run python -m chatops_cli ask "check disk usage" --dry-run
```

## Project Structure

```
ChatOps/
├── chatops_cli/                # Main application package
│   ├── cli/main.py            # CLI interface & Click commands
│   ├── core/                  # Core functionality
│   │   ├── groq_client.py     # Groq API integration
│   │   ├── ollama_client.py   # Local Ollama integration
│   │   ├── langchain_integration.py  # LangChain components
│   │   └── os_detection.py    # Cross-platform support
│   ├── plugins/               # Plugin system
│   │   ├── base.py           # Plugin interfaces
│   │   ├── manager.py        # Plugin management  
│   │   └── builtin/          # Built-in plugins
│   │       └── system_plugin.py  # System commands
│   ├── settings.py           # Configuration management
│   └── main.py              # Entry point
├── tests/                    # Test suite (coming in Task 13)
├── docs/                     # Documentation
├── pyproject.toml           # Poetry configuration
├── README.md               # This file
└── .env.example           # Environment template
```

## Testing

```bash
# Test plugin system (offline)
python -m poetry run python -m chatops_cli plugins --list

# Test command generation (requires API key)
python -m poetry run python -m chatops_cli ask "show running processes" --dry-run

# Run full test suite (coming soon)
python -m pytest
```

## Contributing

### **How to Contribute**

1. **Fork the repository** and create a feature branch
2. **Implement your changes**: Bug fixes, new plugins, or improvements
3. **Test thoroughly**: Ensure cross-platform compatibility
4. **Submit a Pull Request**: Include clear description and test examples

### **Architecture Guidelines**

- **Plugin Development**: Extend `CommandPlugin` for new command categories
- **Cross-Platform**: Use `os_detection` for platform-specific implementations  
- **LLM Integration**: Leverage both local and cloud LLM backends
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Testing**: Unit tests for plugins, integration tests for full workflows

## Roadmap

### **Coming Soon**
- **Docker Plugin**: Container management and operations
- **Interactive Chat Mode**: Conversational command interface
- **Command Validation**: Dry-run mode and safety features

### **Future Features**  
- **Advanced Configuration**: Custom profiles and settings
- **Audit Logging**: Track all commands and operations
- **Command Rollback**: Undo operations safely
- **More Plugins**: Kubernetes, AWS, GCP integrations

## License

MIT License

---

**Dashboard**: [https://saket8.github.io/ChatOps/](https://saket8.github.io/ChatOps/) | **Repository**: [GitHub](https://github.com/Saket8/ChatOps) 