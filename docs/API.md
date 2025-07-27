# 📚 ChatOps CLI API Documentation

This document provides comprehensive API documentation for the ChatOps CLI project, including all classes, methods, interfaces, and usage examples.

## Table of Contents

- [Core Classes](#core-classes)
- [Plugin System](#plugin-system)
- [LLM Providers](#llm-providers)
- [Configuration Management](#configuration-management)
- [Command Execution](#command-execution)
- [Logging System](#logging-system)
- [Security System](#security-system)
- [CLI Interface](#cli-interface)
- [Examples](#examples)

## Core Classes

### ChatOpsCLI

Main application class that orchestrates the entire CLI system.

```python
from chatops_cli.main import ChatOpsCLI

class ChatOpsCLI:
    """Main ChatOps CLI application class."""
    
    def __init__(self):
        """Initialize the ChatOps CLI application."""
        self.config_manager = ConfigManager()
        self.plugin_manager = PluginManager()
        self.llm_manager = LLMManager()
        self.command_executor = CommandExecutor()
        self.logger = LoggingSystem()
    
    def run(self):
        """Run the CLI application."""
        pass
    
    def setup(self):
        """Setup the application components."""
        pass
    
    def cleanup(self):
        """Cleanup resources."""
        pass
```

**Methods:**
- `run()`: Main entry point for the CLI application
- `setup()`: Initialize all components and configurations
- `cleanup()`: Clean up resources and connections
- `get_help()`: Display help information

## Plugin System

### BasePlugin

Abstract base class for all plugins.

```python
from chatops_cli.plugins.base import BasePlugin

class BasePlugin:
    """Base class for all ChatOps plugins."""
    
    name: str = "base"
    description: str = "Base plugin"
    version: str = "1.0.0"
    author: str = "Unknown"
    
    def __init__(self):
        """Initialize the plugin."""
        self.commands = {}
        self.config = {}
    
    def setup_commands(self):
        """Setup plugin commands. Override in subclasses."""
        pass
    
    def initialize(self):
        """Initialize the plugin."""
        pass
    
    def cleanup(self):
        """Cleanup plugin resources."""
        pass
    
    def add_command(self, name: str, handler: callable):
        """Add a command to the plugin."""
        self.commands[name] = handler
    
    def get_command(self, name: str) -> callable:
        """Get a command handler by name."""
        return self.commands.get(name)
    
    def list_commands(self) -> list:
        """List all available commands."""
        return list(self.commands.keys())
```

### PluginManager

Manages plugin discovery, loading, and lifecycle.

```python
from chatops_cli.plugins.manager import PluginManager

class PluginManager:
    """Manages plugin discovery, loading, and lifecycle."""
    
    def __init__(self):
        """Initialize the plugin manager."""
        self.plugins = {}
        self.plugin_dirs = []
    
    def discover_plugins(self, plugin_dirs: list = None):
        """Discover plugins in specified directories."""
        pass
    
    def load_plugin(self, plugin_path: str):
        """Load a plugin from a file or directory."""
        pass
    
    def register_plugin(self, plugin: BasePlugin):
        """Register a plugin instance."""
        pass
    
    def unregister_plugin(self, plugin_name: str):
        """Unregister a plugin by name."""
        pass
    
    def get_plugin(self, name: str) -> BasePlugin:
        """Get a plugin by name."""
        return self.plugins.get(name)
    
    def list_plugins(self) -> list:
        """List all registered plugins."""
        return list(self.plugins.keys())
    
    def execute_command(self, plugin_name: str, command: str, args: dict):
        """Execute a command on a specific plugin."""
        pass
```

### CommandResult

Data class for command execution results.

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class CommandResult:
    """Result of a command execution."""
    
    success: bool
    output: str
    command: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'success': self.success,
            'output': self.output,
            'command': self.command,
            'error': self.error,
            'metadata': self.metadata,
            'execution_time': self.execution_time
        }
```

## LLM Providers

### LLMProvider (Abstract Base Class)

Base class for all LLM providers.

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM provider."""
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        pass
    
    def validate_config(self) -> bool:
        """Validate the provider configuration."""
        pass
```

### GroqClient

Groq API integration for cloud LLM access.

```python
from chatops_cli.core.groq_client import GroqClient

class GroqClient(LLMProvider):
    """Groq API client for cloud LLM access."""
    
    def __init__(self, api_key: str, model: str = "llama3-8b-8192"):
        """Initialize the Groq client."""
        super().__init__({'api_key': api_key, 'model': model})
        self.api_key = api_key
        self.model = model
        self.client = None
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using Groq API."""
        pass
    
    def is_available(self) -> bool:
        """Check if Groq API is available."""
        pass
    
    def get_models(self) -> list:
        """Get available Groq models."""
        pass
    
    def get_usage_info(self) -> dict:
        """Get API usage information."""
        pass
```

### OllamaClient

Ollama integration for local LLM access.

```python
from chatops_cli.core.ollama_client import OllamaClient

class OllamaClient(LLMProvider):
    """Ollama client for local LLM access."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral:7b"):
        """Initialize the Ollama client."""
        super().__init__({'base_url': base_url, 'model': model})
        self.base_url = base_url
        self.model = model
        self.client = None
    
    def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using local Ollama."""
        pass
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        pass
    
    def list_models(self) -> list:
        """List available local models."""
        pass
    
    def pull_model(self, model_name: str):
        """Pull a model from Ollama library."""
        pass
```

### LLMManager

Manages multiple LLM providers and routing.

```python
from chatops_cli.core.llm_manager import LLMManager

class LLMManager:
    """Manages multiple LLM providers and routing."""
    
    def __init__(self):
        """Initialize the LLM manager."""
        self.providers = {}
        self.default_provider = None
    
    def register_provider(self, name: str, provider: LLMProvider):
        """Register an LLM provider."""
        pass
    
    def get_provider(self, name: str) -> LLMProvider:
        """Get a provider by name."""
        return self.providers.get(name)
    
    def set_default_provider(self, name: str):
        """Set the default LLM provider."""
        pass
    
    def generate_response(self, prompt: str, provider: str = None) -> str:
        """Generate response using specified or default provider."""
        pass
    
    def list_providers(self) -> list:
        """List all available providers."""
        return list(self.providers.keys())
    
    def get_provider_status(self) -> dict:
        """Get status of all providers."""
        pass
```

## Configuration Management

### ConfigManager

Manages application configuration across multiple sources.

```python
from chatops_cli.config.manager import ConfigManager

class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_file: str = None):
        """Initialize the configuration manager."""
        self.config_file = config_file
        self.config = {}
        self.profiles = {}
        self.current_profile = "default"
    
    def load_config(self, config_file: str = None):
        """Load configuration from file."""
        pass
    
    def save_config(self, config_file: str = None):
        """Save configuration to file."""
        pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        pass
    
    def set(self, key: str, value: Any):
        """Set a configuration value."""
        pass
    
    def create_profile(self, name: str):
        """Create a new configuration profile."""
        pass
    
    def use_profile(self, name: str):
        """Switch to a configuration profile."""
        pass
    
    def export_config(self, format: str = "json") -> str:
        """Export configuration in specified format."""
        pass
    
    def import_config(self, config_data: str, format: str = "json"):
        """Import configuration from string."""
        pass
```

## Command Execution

### CommandExecutor

Executes commands with security and validation.

```python
from chatops_cli.core.command_executor import CommandExecutor

class CommandExecutor:
    """Executes commands with security and validation."""
    
    def __init__(self, config: dict = None):
        """Initialize the command executor."""
        self.config = config or {}
        self.security_system = SecuritySystem()
        self.logger = LoggingSystem()
    
    def execute(self, command: str, dry_run: bool = False) -> CommandResult:
        """Execute a command with validation."""
        pass
    
    def validate_command(self, command: str) -> bool:
        """Validate a command for security."""
        pass
    
    def preview_command(self, command: str) -> str:
        """Preview what a command would do."""
        pass
    
    def execute_safe(self, command: str, confirm: bool = True) -> CommandResult:
        """Execute a command with safety checks."""
        pass
    
    def rollback_command(self, command: str) -> CommandResult:
        """Rollback a previously executed command."""
        pass
```

## Logging System

### LoggingSystem

Comprehensive logging and audit system.

```python
from chatops_cli.core.logging_system import LoggingSystem

class LoggingSystem:
    """Comprehensive logging and audit system."""
    
    def __init__(self, config: dict = None):
        """Initialize the logging system."""
        self.config = config or {}
        self.loggers = {}
        self.audit_log = []
    
    def setup_logging(self, log_level: str = "INFO", log_file: str = None):
        """Setup logging configuration."""
        pass
    
    def log_command(self, command: str, result: CommandResult):
        """Log a command execution."""
        pass
    
    def log_security_event(self, event_type: str, details: dict):
        """Log a security event."""
        pass
    
    def log_error(self, error: Exception, context: dict = None):
        """Log an error."""
        pass
    
    def get_audit_trail(self, start_time: datetime = None, end_time: datetime = None) -> list:
        """Get audit trail for specified time period."""
        pass
    
    def export_logs(self, format: str = "json") -> str:
        """Export logs in specified format."""
        pass
    
    def rotate_logs(self):
        """Rotate log files."""
        pass
```

## Security System

### SecuritySystem

Security validation and sandboxing.

```python
from chatops_cli.core.security_system import SecuritySystem

class SecuritySystem:
    """Security validation and sandboxing system."""
    
    def __init__(self, config: dict = None):
        """Initialize the security system."""
        self.config = config or {}
        self.blacklist = set()
        self.whitelist = set()
        self.sandbox_config = {}
    
    def validate_command(self, command: str) -> bool:
        """Validate a command for security risks."""
        pass
    
    def is_blacklisted(self, command: str) -> bool:
        """Check if command is blacklisted."""
        pass
    
    def is_whitelisted(self, command: str) -> bool:
        """Check if command is whitelisted."""
        pass
    
    def add_to_blacklist(self, pattern: str):
        """Add a pattern to the blacklist."""
        pass
    
    def add_to_whitelist(self, pattern: str):
        """Add a pattern to the whitelist."""
        pass
    
    def create_sandbox(self, command: str) -> dict:
        """Create a sandbox environment for command execution."""
        pass
    
    def cleanup_sandbox(self, sandbox_id: str):
        """Cleanup a sandbox environment."""
        pass
```

## CLI Interface

### Click Commands

The CLI interface is built using Click framework.

```python
import click
from chatops_cli.cli.main import cli

@cli.command()
@click.option('--provider', '-p', help='LLM provider to use')
@click.option('--dry-run', is_flag=True, help='Preview command without execution')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.argument('command', nargs=-1)
def exec(provider, dry_run, verbose, command):
    """Execute a command using AI assistance."""
    pass

@cli.command()
@click.option('--save-history', help='Save conversation history to file')
def chat(save_history):
    """Start interactive chat mode."""
    pass

@cli.group()
def config():
    """Manage configuration."""
    pass

@config.command()
def show():
    """Show current configuration."""
    pass

@config.command()
@click.argument('key')
@click.argument('value')
def set(key, value):
    """Set a configuration value."""
    pass

@cli.group()
def plugins():
    """Manage plugins."""
    pass

@plugins.command()
def list():
    """List available plugins."""
    pass

@plugins.command()
@click.argument('plugin_name')
def enable(plugin_name):
    """Enable a plugin."""
    pass

@plugins.command()
@click.argument('plugin_name')
def disable(plugin_name):
    """Disable a plugin."""
    pass
```

## Examples

### Creating a Custom Plugin

```python
from chatops_cli.plugins.base import BasePlugin
from chatops_cli.core.command_executor import CommandResult

class CustomPlugin(BasePlugin):
    name = "custom"
    description = "Custom plugin for specific operations"
    version = "1.0.0"
    author = "Your Name"
    
    def setup_commands(self):
        """Setup plugin commands."""
        self.add_command("hello", self.hello_world)
        self.add_command("status", self.get_status)
        self.add_command("process", self.process_data)
    
    def hello_world(self, args):
        """Say hello to the world."""
        return CommandResult(
            success=True,
            output="Hello, World!",
            command="echo 'Hello, World!'"
        )
    
    def get_status(self, args):
        """Get system status."""
        return CommandResult(
            success=True,
            output="System is running normally",
            command="echo 'System status: OK'"
        )
    
    def process_data(self, args):
        """Process data with custom logic."""
        # Custom processing logic here
        return CommandResult(
            success=True,
            output="Data processed successfully",
            command="custom_process_command"
        )
```

### Using the LLM Manager

```python
from chatops_cli.core.llm_manager import LLMManager
from chatops_cli.core.groq_client import GroqClient
from chatops_cli.core.ollama_client import OllamaClient

# Initialize LLM manager
llm_manager = LLMManager()

# Register providers
groq_client = GroqClient(api_key="your-api-key")
ollama_client = OllamaClient()

llm_manager.register_provider("groq", groq_client)
llm_manager.register_provider("ollama", ollama_client)

# Set default provider
llm_manager.set_default_provider("groq")

# Generate responses
response = llm_manager.generate_response("Explain Docker containers")
print(response)
```

### Configuration Management

```python
from chatops_cli.config.manager import ConfigManager

# Initialize config manager
config = ConfigManager()

# Set configuration values
config.set("groq.api_key", "your-api-key")
config.set("ollama.base_url", "http://localhost:11434")
config.set("logging.level", "INFO")

# Create profiles
config.create_profile("development")
config.create_profile("production")

# Switch profiles
config.use_profile("development")
config.set("logging.level", "DEBUG")

# Export configuration
config_json = config.export_config("json")
print(config_json)
```

### Command Execution with Security

```python
from chatops_cli.core.command_executor import CommandExecutor

# Initialize command executor
executor = CommandExecutor()

# Execute commands safely
result = executor.execute_safe("ls -la", confirm=True)
print(result.output)

# Preview commands
preview = executor.preview_command("rm -rf /")
print(preview)

# Dry run
result = executor.execute("docker stop container", dry_run=True)
print(result.command)  # Shows what would be executed
```

This API documentation provides a comprehensive overview of all the classes, methods, and interfaces available in the ChatOps CLI project. For more detailed examples and usage patterns, refer to the individual module documentation and the main README file. 