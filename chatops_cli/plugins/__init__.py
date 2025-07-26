"""
Plugin System for ChatOps CLI

This package provides the complete plugin architecture for ChatOps CLI,
including base classes, plugin manager, and built-in plugins.
"""

from .base import (
    BasePlugin,
    CommandPlugin,
    ExecutorPlugin,
    MonitoringPlugin,
    PluginMetadata,
    PluginInfo,
    PluginStatus,
    PluginCapability,
    PluginPriority,
    plugin,
)

from .manager import PluginManager, PluginLoadError, PluginConflictError

# Built-in plugins
from .builtin.system_plugin import SystemPlugin

__version__ = "0.1.0"

__all__ = [
    # Base classes
    "BasePlugin",
    "CommandPlugin",
    "ExecutorPlugin",
    "MonitoringPlugin",
    # Metadata and enums
    "PluginMetadata",
    "PluginInfo",
    "PluginStatus",
    "PluginCapability",
    "PluginPriority",
    # Manager and decorators
    "PluginManager",
    "PluginLoadError",
    "PluginConflictError",
    "plugin",
    # Built-in plugins
    "SystemPlugin",
]
