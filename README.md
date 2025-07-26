# ChatOps CLI

Offline ChatOps CLI with LangChain + Local LLM

## Overview

A Python-based command-line assistant designed for DevOps and Cloud engineers who need to perform system administration tasks through natural language commands. The tool operates entirely offline, leveraging LangChain for natural language processing and local Large Language Models (LLMs) like Ollama.

## Project Status

🚧 **In Development** - Foundation setup complete!

## Features (Planned)

- **Offline Operation**: Complete functionality without external API dependencies
- **Natural Language Interface**: Transform conversational commands into executable system operations  
- **Plugin Architecture**: Extensible plugin system for custom commands
- **Local LLM Integration**: Ollama integration with Mistral, LLaMA3, and other models
- **Safety Features**: Command validation, dry-run mode, and operation rollback

## Development Setup

### Prerequisites

- Python 3.11+
- Poetry for dependency management
- Ollama (for local LLM models)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ChatOps

# Install dependencies (coming in Task 2)
python -m poetry install

# Test basic functionality
python -m chatops_cli.main
```

## Project Structure

```
chatops_cli/
├── __init__.py          # Main package
├── main.py             # Entry point
├── cli/                # Click-based CLI framework
├── core/               # Core functionality (LangChain, Ollama)
├── config/             # Configuration management
└── plugins/            # Plugin system
tests/                  # Test suite
```

## Contributing

This project follows the development workflow outlined in the PRD. Tasks are managed using TaskMaster.

## License

MIT License 