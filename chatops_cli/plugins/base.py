"""
Base plugin architecture for ChatOps CLI

This module provides the foundation for the extensible plugin system, including
abstract base classes, plugin metadata, and lifecycle management.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import importlib
import importlib.util
import inspect
from datetime import datetime

from ..core.langchain_integration import DevOpsCommand, CommandType, RiskLevel


class PluginStatus(Enum):
    """Status of a plugin in the system"""

    UNKNOWN = "unknown"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


class PluginPriority(Enum):
    """Priority levels for plugin execution order"""

    LOWEST = 1
    LOW = 25
    NORMAL = 50
    HIGH = 75
    HIGHEST = 100


@dataclass
class PluginMetadata:
    """Metadata for a plugin"""

    name: str
    version: str
    description: str
    author: str = "Unknown"
    email: str = ""
    website: str = ""
    license: str = "MIT"
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    min_python_version: str = "3.11"
    priority: PluginPriority = PluginPriority.NORMAL
    enabled: bool = True

    def __post_init__(self):
        if isinstance(self.priority, int):
            # Convert int to PluginPriority enum
            for priority in PluginPriority:
                if priority.value == self.priority:
                    self.priority = priority
                    break
            else:
                self.priority = PluginPriority.NORMAL


@dataclass
class PluginInfo:
    """Complete information about a plugin"""

    metadata: PluginMetadata
    plugin_class: Type["BasePlugin"]
    instance: Optional["BasePlugin"] = None
    status: PluginStatus = PluginStatus.UNKNOWN
    file_path: Optional[Path] = None
    load_time: Optional[datetime] = None
    error_message: Optional[str] = None
    last_used: Optional[datetime] = None


class PluginCapability(Enum):
    """Capabilities that plugins can provide"""

    COMMAND_GENERATION = "command_generation"
    COMMAND_EXECUTION = "command_execution"
    COMMAND_VALIDATION = "command_validation"
    OUTPUT_PROCESSING = "output_processing"
    SYSTEM_MONITORING = "system_monitoring"
    FILE_OPERATIONS = "file_operations"
    NETWORK_OPERATIONS = "network_operations"
    CONTAINER_MANAGEMENT = "container_management"
    CLOUD_OPERATIONS = "cloud_operations"


class BasePlugin(ABC):
    """
    Abstract base class for all ChatOps CLI plugins.

    All plugins must inherit from this class and implement the required methods.
    This provides a consistent interface for plugin discovery, loading, and execution.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._is_initialized = False
        self._capabilities: List[PluginCapability] = []
        self._command_patterns: List[str] = []

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass

    @property
    def capabilities(self) -> List[PluginCapability]:
        """Return list of capabilities this plugin provides"""
        return self._capabilities.copy()

    @property
    def command_patterns(self) -> List[str]:
        """Return list of command patterns this plugin can handle"""
        return self._command_patterns.copy()

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the plugin. Called once when the plugin is loaded.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def cleanup(self) -> bool:
        """
        Cleanup plugin resources. Called when plugin is unloaded.

        Returns:
            bool: True if cleanup successful, False otherwise
        """
        pass

    @abstractmethod
    def can_handle(self, user_input: str, context: Dict[str, Any] = None) -> bool:
        """
        Check if this plugin can handle the given user input.

        Args:
            user_input: Natural language command from user
            context: Additional context information

        Returns:
            bool: True if plugin can handle this input
        """
        pass

    @abstractmethod
    async def generate_command(
        self, user_input: str, context: Dict[str, Any] = None
    ) -> Optional[DevOpsCommand]:
        """
        Generate a DevOps command from natural language input.

        Args:
            user_input: Natural language command from user
            context: Additional context information

        Returns:
            DevOpsCommand: Generated command or None if cannot handle
        """
        pass

    async def validate_command(
        self, command: DevOpsCommand, context: Dict[str, Any] = None
    ) -> bool:
        """
        Validate a command before execution (optional override).

        Args:
            command: Command to validate
            context: Additional context information

        Returns:
            bool: True if command is valid and safe to execute
        """
        return True

    async def pre_execute(
        self, command: DevOpsCommand, context: Dict[str, Any] = None
    ) -> bool:
        """
        Hook called before command execution (optional override).

        Args:
            command: Command about to be executed
            context: Additional context information

        Returns:
            bool: True to continue execution, False to abort
        """
        return True

    async def post_execute(
        self, command: DevOpsCommand, result: Any, context: Dict[str, Any] = None
    ) -> Any:
        """
        Hook called after command execution (optional override).

        Args:
            command: Command that was executed
            result: Result from command execution
            context: Additional context information

        Returns:
            Any: Processed result (can modify the original result)
        """
        return result

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the plugin (optional override).

        Returns:
            Dict containing health status and details
        """
        return {
            "status": "healthy",
            "initialized": self._is_initialized,
            "capabilities": [cap.value for cap in self._capabilities],
            "timestamp": datetime.now().isoformat(),
        }

    def get_help(self) -> str:
        """
        Return help text for this plugin (optional override).

        Returns:
            str: Help text describing plugin usage
        """
        return f"""
Plugin: {self.metadata.name} v{self.metadata.version}
Description: {self.metadata.description}
Author: {self.metadata.author}

Capabilities: {', '.join([cap.value for cap in self._capabilities])}
Command Patterns: {', '.join(self._command_patterns) if self._command_patterns else 'Auto-detected'}

For more information, visit: {self.metadata.website or 'N/A'}
        """.strip()

    async def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the plugin with provided settings (optional override).

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if configuration successful
        """
        return True

    def get_version(self) -> str:
        """Get plugin version"""
        return self.metadata.version

    def is_compatible(self, other_plugin: "BasePlugin") -> bool:
        """
        Check if this plugin is compatible with another plugin.

        Args:
            other_plugin: Another plugin to check compatibility with

        Returns:
            bool: True if compatible
        """
        # Check for conflicts
        if other_plugin.metadata.name in self.metadata.conflicts:
            return False
        if self.metadata.name in other_plugin.metadata.conflicts:
            return False

        return True

    def __str__(self) -> str:
        return f"{self.metadata.name} v{self.metadata.version}"

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.metadata.name})>"


class CommandPlugin(BasePlugin):
    """
    Specialized base class for plugins that primarily generate commands.
    """

    def __init__(self):
        super().__init__()
        self._capabilities.append(PluginCapability.COMMAND_GENERATION)


class ExecutorPlugin(BasePlugin):
    """
    Specialized base class for plugins that primarily execute commands.
    """

    def __init__(self):
        super().__init__()
        self._capabilities.append(PluginCapability.COMMAND_EXECUTION)

    @abstractmethod
    async def execute_command(
        self, command: DevOpsCommand, context: Dict[str, Any] = None
    ) -> Any:
        """
        Execute a DevOps command.

        Args:
            command: Command to execute
            context: Additional context information

        Returns:
            Any: Execution result
        """
        pass


class MonitoringPlugin(BasePlugin):
    """
    Specialized base class for system monitoring plugins.
    """

    def __init__(self):
        super().__init__()
        self._capabilities.append(PluginCapability.SYSTEM_MONITORING)

    @abstractmethod
    async def get_metrics(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Get system metrics.

        Args:
            context: Additional context information

        Returns:
            Dict: System metrics
        """
        pass


# Plugin decorator for easy registration
def plugin(name: str, version: str, description: str, **kwargs):
    """
    Decorator to mark a class as a plugin and set its metadata.

    Args:
        name: Plugin name
        version: Plugin version
        description: Plugin description
        **kwargs: Additional metadata fields
    """

    def decorator(cls):
        if not issubclass(cls, BasePlugin):
            raise TypeError(f"Plugin class {cls.__name__} must inherit from BasePlugin")

        # Store metadata as class attribute
        metadata_kwargs = {
            "name": name,
            "version": version,
            "description": description,
            **kwargs,
        }

        # Create metadata property
        original_metadata = getattr(cls, "metadata", None)
        if original_metadata and callable(original_metadata):
            # If metadata is already a method, wrap it
            original_method = original_metadata

            def new_metadata(self):
                base_metadata = original_method(self)
                for key, value in metadata_kwargs.items():
                    setattr(base_metadata, key, value)
                return base_metadata

            cls.metadata = property(new_metadata)
        else:
            # Create new metadata property
            def metadata_property(self):
                return PluginMetadata(**metadata_kwargs)

            cls.metadata = property(metadata_property)

        return cls

    return decorator
