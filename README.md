# ChatOps CLI

Offline ChatOps CLI with LangChain + Local LLM

## Overview

A Python-based command-line assistant designed for DevOps and Cloud engineers who need to perform system administration tasks through natural language commands. The tool provides both **offline plugin-based commands** for speed and **AI-powered command generation** for complex scenarios, featuring comprehensive cross-platform support for Windows PowerShell, Linux, and macOS.

**Key Architecture Highlights:**
- **Hybrid Command Generation**: Fast local plugins + smart AI fallback
- **Cross-Platform Intelligence**: Automatic OS detection with appropriate command mapping
- **Extensible Plugin System**: Modular architecture for custom command handlers
- **Multiple LLM Backends**: Groq API (fast, free) + Local Ollama support
- **TaskMaster Integration**: Comprehensive project management and progress tracking

## Project Status

🚀 **Active Development** - Plugin Architecture Complete! (Task 6/15 ✅)

**Current Progress: 6/15 Tasks Complete (40%)**
- ✅ Foundation & Dependencies
- ✅ LangChain Integration  
- ✅ CLI Framework
- ✅ **Plugin Architecture Design** (Just Completed!)
- 🎯 **Next**: Command Executor Service (Task 8)

📊 **Live Dashboard**: [https://saket8.github.io/ChatOps/](https://saket8.github.io/ChatOps/)

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

### **Development Workflow**

This project uses **TaskMaster** for project management:

```bash
# View current tasks and progress
task-master list

# Get next task to work on  
task-master next

# View specific task details
task-master show 8

# Update task status
task-master set-status --id=8 --status=in-progress
```

## Project Structure

```
ChatOps/
├── .taskmaster/                 # TaskMaster project management
│   ├── tasks/tasks.json        # Task definitions and status
│   ├── dashboard.html          # Project dashboard  
│   └── config.json             # TaskMaster configuration
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
# Test plugin system
python test_plugin_system.py

# Test Groq integration  
python test_groq.py

# Test cross-platform commands
python test_windows_commands.py

# Run full test suite (coming in Task 13)
python -m pytest
```

## Contributing

### **Development Process**

1. **Check TaskMaster Dashboard**: [https://saket8.github.io/ChatOps/](https://saket8.github.io/ChatOps/)
2. **Pick Next Task**: Use `task-master next` to see available tasks
3. **Create Feature Branch**: `git checkout -b feature/task-X-description`
4. **Implement & Test**: Follow task requirements and test strategy
5. **Update Task Status**: Mark progress using `task-master set-status`
6. **Submit PR**: Include task completion evidence

### **Architecture Guidelines**

- **Plugin Development**: Extend `CommandPlugin` for new command categories
- **Cross-Platform**: Use `os_detection` for platform-specific implementations  
- **LLM Integration**: Leverage both local and cloud LLM backends
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Testing**: Unit tests for plugins, integration tests for full workflows

## Roadmap

### **Immediate (Next 2 Tasks)**
- **Task 8**: Command Executor Service with validation and sandboxing
- **Task 9**: Interactive Chat Mode for conversational commands

### **Short Term (Tasks 10-12)**  
- **Configuration Management**: Advanced settings and profiles
- **Logging & Audit System**: Comprehensive command tracking
- **Safety & Security Features**: Command validation and rollback

### **Medium Term (Tasks 13-15)**
- **Testing Framework**: Automated testing infrastructure  
- **CI/CD Pipeline**: GitHub Actions automation
- **Documentation & Examples**: Comprehensive user guides

## License

MIT License

---

**Dashboard**: [https://saket8.github.io/ChatOps/](https://saket8.github.io/ChatOps/) | **Repository**: [GitHub](https://github.com/Saket8/ChatOps) | **TaskMaster**: Comprehensive project management integrated 