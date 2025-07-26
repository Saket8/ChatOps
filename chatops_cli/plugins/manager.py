"""
Plugin Manager for ChatOps CLI

This module provides the PluginManager class that handles plugin discovery,
loading, registration, lifecycle management, and hot-reloading capabilities.
"""

import logging
import asyncio
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Type, Set, Callable
from collections import defaultdict
from datetime import datetime
import importlib
import importlib.util
import inspect
import traceback
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .base import (
    BasePlugin,
    PluginInfo,
    PluginMetadata,
    PluginStatus,
    PluginCapability,
    PluginPriority,
    CommandPlugin,
    ExecutorPlugin,
    MonitoringPlugin,
)
from ..core.langchain_integration import DevOpsCommand


class PluginLoadError(Exception):
    """Exception raised when plugin loading fails"""

    pass


class PluginConflictError(Exception):
    """Exception raised when plugin conflicts are detected"""

    pass


class PluginFileWatcher(FileSystemEventHandler):
    """File system watcher for hot-reloading plugins"""

    def __init__(self, manager: "PluginManager"):
        self.manager = manager
        self.logger = logging.getLogger(__name__ + ".PluginFileWatcher")

    def on_modified(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix == ".py":
            self.logger.info(f"Plugin file modified: {file_path}")
            # Debounce rapid file changes
            asyncio.create_task(self.manager._reload_plugin_file(file_path))

    def on_created(self, event):
        if event.is_directory:
            return

        file_path = Path(event.src_path)
        if file_path.suffix == ".py":
            self.logger.info(f"New plugin file created: {file_path}")
            asyncio.create_task(self.manager._discover_and_load_file(file_path))


class PluginManager:
    """
    Manages the plugin system for ChatOps CLI.

    Handles plugin discovery, loading, registration, lifecycle management,
    and hot-reloading capabilities.
    """

    def __init__(self, plugin_directories: Optional[List[Path]] = None):
        self.logger = logging.getLogger(__name__)

        # Plugin storage
        self._plugins: Dict[str, PluginInfo] = {}
        self._plugins_by_capability: Dict[PluginCapability, List[str]] = defaultdict(
            list
        )
        self._plugins_by_priority: Dict[PluginPriority, List[str]] = defaultdict(list)

        # Plugin directories
        self.plugin_directories = plugin_directories or []
        self._default_plugin_dir = Path(__file__).parent / "builtin"
        if self._default_plugin_dir not in self.plugin_directories:
            self.plugin_directories.append(self._default_plugin_dir)

        # Hot-reloading
        self._hot_reload_enabled = False
        self._file_observer: Optional[Observer] = None
        self._watched_files: Set[Path] = set()

        # Event hooks
        self._before_load_hooks: List[Callable] = []
        self._after_load_hooks: List[Callable] = []
        self._before_unload_hooks: List[Callable] = []
        self._after_unload_hooks: List[Callable] = []

        # Configuration
        self._config: Dict[str, Any] = {}

        # Thread safety
        self._lock = asyncio.Lock()

    async def initialize(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Initialize the plugin manager.

        Args:
            config: Configuration dictionary

        Returns:
            bool: True if initialization successful
        """
        try:
            self._config = config or {}

            # Ensure plugin directories exist
            for directory in self.plugin_directories:
                directory.mkdir(parents=True, exist_ok=True)

            # Discover and load plugins
            await self.discover_plugins()

            # Enable hot reloading if configured
            if self._config.get("hot_reload", False):
                await self.enable_hot_reload()

            self.logger.info(
                f"Plugin manager initialized with {len(self._plugins)} plugins"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize plugin manager: {e}")
            return False

    async def shutdown(self) -> bool:
        """
        Shutdown the plugin manager and cleanup resources.

        Returns:
            bool: True if shutdown successful
        """
        try:
            # Disable hot reloading
            await self.disable_hot_reload()

            # Unload all plugins
            await self.unload_all_plugins()

            self.logger.info("Plugin manager shutdown complete")
            return True

        except Exception as e:
            self.logger.error(f"Error during plugin manager shutdown: {e}")
            return False

    async def discover_plugins(self) -> int:
        """
        Discover plugins in all configured directories.

        Returns:
            int: Number of plugins discovered
        """
        discovered_count = 0

        async with self._lock:
            for directory in self.plugin_directories:
                if not directory.exists():
                    continue

                self.logger.info(f"Discovering plugins in {directory}")

                for plugin_file in directory.rglob("*.py"):
                    if plugin_file.name.startswith("__"):
                        continue

                    try:
                        count = await self._discover_and_load_file(plugin_file)
                        discovered_count += count
                    except Exception as e:
                        self.logger.error(
                            f"Error loading plugin from {plugin_file}: {e}"
                        )

        self.logger.info(f"Discovered {discovered_count} plugins")
        return discovered_count

    async def _discover_and_load_file(self, plugin_file: Path) -> int:
        """
        Discover and load plugins from a specific file.

        Args:
            plugin_file: Path to the plugin file

        Returns:
            int: Number of plugins loaded from this file
        """
        loaded_count = 0

        try:
            # Create module spec
            module_name = f"plugin_{plugin_file.stem}_{int(time.time())}"
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)

            if spec is None or spec.loader is None:
                self.logger.warning(f"Could not create module spec for {plugin_file}")
                return 0

            # Load module
            module = importlib.util.module_from_spec(spec)

            # Add to sys.modules temporarily
            sys.modules[module_name] = module

            try:
                spec.loader.exec_module(module)

                # Find plugin classes in the module
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BasePlugin)
                        and obj is not BasePlugin
                        and not inspect.isabstract(obj)
                    ):
                        await self._load_plugin_class(obj, plugin_file)
                        loaded_count += 1

            finally:
                # Clean up sys.modules
                if module_name in sys.modules:
                    del sys.modules[module_name]

        except Exception as e:
            self.logger.error(f"Error loading plugin file {plugin_file}: {e}")
            self.logger.debug(traceback.format_exc())

        return loaded_count

    async def _load_plugin_class(
        self, plugin_class: Type[BasePlugin], file_path: Path
    ) -> bool:
        """
        Load a specific plugin class.

        Args:
            plugin_class: Plugin class to load
            file_path: Path to the plugin file

        Returns:
            bool: True if loaded successfully
        """
        try:
            # Create plugin instance
            plugin_instance = plugin_class()

            # Get metadata
            metadata = plugin_instance.metadata
            plugin_name = metadata.name

            # Check for conflicts
            if plugin_name in self._plugins:
                existing = self._plugins[plugin_name]
                if existing.file_path != file_path:
                    self.logger.warning(
                        f"Plugin name conflict: {plugin_name} already exists "
                        f"from {existing.file_path}"
                    )
                    return False

            # Check dependencies
            if not await self._check_dependencies(metadata):
                self.logger.error(f"Dependencies not met for plugin {plugin_name}")
                return False

            # Check conflicts
            if not await self._check_conflicts(metadata):
                self.logger.error(f"Conflicts detected for plugin {plugin_name}")
                return False

            # Execute before load hooks
            for hook in self._before_load_hooks:
                await hook(plugin_instance)

            # Initialize plugin
            if await plugin_instance.initialize():
                plugin_instance._is_initialized = True

                # Create plugin info
                plugin_info = PluginInfo(
                    metadata=metadata,
                    plugin_class=plugin_class,
                    instance=plugin_instance,
                    status=PluginStatus.ACTIVE,
                    file_path=file_path,
                    load_time=datetime.now(),
                )

                # Register plugin
                self._plugins[plugin_name] = plugin_info

                # Update capability mappings
                for capability in plugin_instance.capabilities:
                    self._plugins_by_capability[capability].append(plugin_name)

                # Update priority mappings
                self._plugins_by_priority[metadata.priority].append(plugin_name)

                # Track file for hot reloading
                self._watched_files.add(file_path)

                # Execute after load hooks
                for hook in self._after_load_hooks:
                    await hook(plugin_instance)

                self.logger.info(f"Loaded plugin: {plugin_name} v{metadata.version}")
                return True
            else:
                self.logger.error(f"Failed to initialize plugin {plugin_name}")
                return False

        except Exception as e:
            self.logger.error(
                f"Error loading plugin class {plugin_class.__name__}: {e}"
            )
            self.logger.debug(traceback.format_exc())
            return False

    async def _check_dependencies(self, metadata: PluginMetadata) -> bool:
        """
        Check if plugin dependencies are satisfied.

        Args:
            metadata: Plugin metadata to check

        Returns:
            bool: True if all dependencies are satisfied
        """
        for dependency in metadata.dependencies:
            if dependency not in self._plugins:
                self.logger.error(f"Missing dependency: {dependency}")
                return False

            dep_plugin = self._plugins[dependency]
            if dep_plugin.status != PluginStatus.ACTIVE:
                self.logger.error(f"Dependency {dependency} is not active")
                return False

        return True

    async def _check_conflicts(self, metadata: PluginMetadata) -> bool:
        """
        Check if plugin has conflicts with existing plugins.

        Args:
            metadata: Plugin metadata to check

        Returns:
            bool: True if no conflicts detected
        """
        for conflict in metadata.conflicts:
            if conflict in self._plugins:
                conflict_plugin = self._plugins[conflict]
                if conflict_plugin.status == PluginStatus.ACTIVE:
                    self.logger.error(f"Conflict with active plugin: {conflict}")
                    return False

        return True

    async def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a specific plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            bool: True if unloaded successfully
        """
        async with self._lock:
            if plugin_name not in self._plugins:
                self.logger.warning(f"Plugin {plugin_name} not found")
                return False

            plugin_info = self._plugins[plugin_name]
            plugin_instance = plugin_info.instance

            try:
                # Execute before unload hooks
                for hook in self._before_unload_hooks:
                    await hook(plugin_instance)

                # Cleanup plugin
                if plugin_instance:
                    await plugin_instance.cleanup()

                # Remove from mappings
                for capability in plugin_instance.capabilities:
                    if plugin_name in self._plugins_by_capability[capability]:
                        self._plugins_by_capability[capability].remove(plugin_name)

                priority = plugin_info.metadata.priority
                if plugin_name in self._plugins_by_priority[priority]:
                    self._plugins_by_priority[priority].remove(plugin_name)

                # Remove from watched files
                if plugin_info.file_path:
                    self._watched_files.discard(plugin_info.file_path)

                # Remove plugin
                del self._plugins[plugin_name]

                # Execute after unload hooks
                for hook in self._after_unload_hooks:
                    await hook(plugin_instance)

                self.logger.info(f"Unloaded plugin: {plugin_name}")
                return True

            except Exception as e:
                self.logger.error(f"Error unloading plugin {plugin_name}: {e}")
                return False

    async def unload_all_plugins(self) -> int:
        """
        Unload all plugins.

        Returns:
            int: Number of plugins unloaded
        """
        unloaded_count = 0
        plugin_names = list(self._plugins.keys())

        for plugin_name in plugin_names:
            if await self.unload_plugin(plugin_name):
                unloaded_count += 1

        return unloaded_count

    async def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a specific plugin.

        Args:
            plugin_name: Name of the plugin to reload

        Returns:
            bool: True if reloaded successfully
        """
        if plugin_name not in self._plugins:
            self.logger.warning(f"Plugin {plugin_name} not found")
            return False

        plugin_info = self._plugins[plugin_name]
        file_path = plugin_info.file_path

        # Unload current plugin
        if not await self.unload_plugin(plugin_name):
            return False

        # Reload from file
        if file_path and file_path.exists():
            count = await self._discover_and_load_file(file_path)
            return count > 0

        return False

    async def _reload_plugin_file(self, file_path: Path):
        """
        Reload all plugins from a specific file.

        Args:
            file_path: Path to the plugin file
        """
        # Find plugins from this file
        plugins_to_reload = []
        for plugin_name, plugin_info in self._plugins.items():
            if plugin_info.file_path == file_path:
                plugins_to_reload.append(plugin_name)

        # Reload each plugin
        for plugin_name in plugins_to_reload:
            await self.reload_plugin(plugin_name)

    async def enable_hot_reload(self) -> bool:
        """
        Enable hot reloading of plugins.

        Returns:
            bool: True if enabled successfully
        """
        try:
            if self._hot_reload_enabled:
                return True

            self._file_observer = Observer()
            event_handler = PluginFileWatcher(self)

            for directory in self.plugin_directories:
                if directory.exists():
                    self._file_observer.schedule(
                        event_handler, str(directory), recursive=True
                    )

            self._file_observer.start()
            self._hot_reload_enabled = True

            self.logger.info("Hot reloading enabled")
            return True

        except Exception as e:
            self.logger.error(f"Failed to enable hot reloading: {e}")
            return False

    async def disable_hot_reload(self) -> bool:
        """
        Disable hot reloading of plugins.

        Returns:
            bool: True if disabled successfully
        """
        try:
            if not self._hot_reload_enabled:
                return True

            if self._file_observer:
                self._file_observer.stop()
                self._file_observer.join(timeout=5)
                self._file_observer = None

            self._hot_reload_enabled = False

            self.logger.info("Hot reloading disabled")
            return True

        except Exception as e:
            self.logger.error(f"Failed to disable hot reloading: {e}")
            return False

    def get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """
        Get a plugin instance by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            BasePlugin instance or None if not found
        """
        plugin_info = self._plugins.get(plugin_name)
        return plugin_info.instance if plugin_info else None

    def get_plugins_by_capability(
        self, capability: PluginCapability
    ) -> List[BasePlugin]:
        """
        Get all plugins that provide a specific capability.

        Args:
            capability: Capability to search for

        Returns:
            List of plugin instances
        """
        plugin_names = self._plugins_by_capability.get(capability, [])
        plugins = []

        for name in plugin_names:
            plugin_info = self._plugins.get(name)
            if plugin_info and plugin_info.instance:
                plugins.append(plugin_info.instance)

        # Sort by priority
        plugins.sort(key=lambda p: p.metadata.priority.value, reverse=True)
        return plugins

    def get_all_plugins(self) -> Dict[str, BasePlugin]:
        """
        Get all loaded plugins.

        Returns:
            Dictionary of plugin name to plugin instance
        """
        return {
            name: info.instance for name, info in self._plugins.items() if info.instance
        }

    def get_plugin_info(self, plugin_name: str) -> Optional[PluginInfo]:
        """
        Get detailed information about a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginInfo or None if not found
        """
        return self._plugins.get(plugin_name)

    def get_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status information for all plugins.

        Returns:
            Dictionary with plugin status information
        """
        status = {}

        for name, info in self._plugins.items():
            status[name] = {
                "status": info.status.value,
                "version": info.metadata.version,
                "capabilities": [cap.value for cap in info.instance.capabilities]
                if info.instance
                else [],
                "load_time": info.load_time.isoformat() if info.load_time else None,
                "file_path": str(info.file_path) if info.file_path else None,
                "error_message": info.error_message,
            }

        return status

    async def find_handler(
        self, user_input: str, context: Dict[str, Any] = None
    ) -> Optional[BasePlugin]:
        """
        Find the best plugin to handle user input.

        Args:
            user_input: Natural language command from user
            context: Additional context information

        Returns:
            Plugin instance that can handle the input, or None
        """
        command_plugins = self.get_plugins_by_capability(
            PluginCapability.COMMAND_GENERATION
        )

        for plugin in command_plugins:
            if plugin.can_handle(user_input, context):
                # Update last used time
                plugin_name = plugin.metadata.name
                if plugin_name in self._plugins:
                    self._plugins[plugin_name].last_used = datetime.now()
                return plugin

        return None

    # Event hook methods
    def add_before_load_hook(self, hook: Callable):
        """Add a hook to be called before plugin loading"""
        self._before_load_hooks.append(hook)

    def add_after_load_hook(self, hook: Callable):
        """Add a hook to be called after plugin loading"""
        self._after_load_hooks.append(hook)

    def add_before_unload_hook(self, hook: Callable):
        """Add a hook to be called before plugin unloading"""
        self._before_unload_hooks.append(hook)

    def add_after_unload_hook(self, hook: Callable):
        """Add a hook to be called after plugin unloading"""
        self._after_unload_hooks.append(hook)

    def __len__(self) -> int:
        """Return number of loaded plugins"""
        return len(self._plugins)

    def __contains__(self, plugin_name: str) -> bool:
        """Check if plugin is loaded"""
        return plugin_name in self._plugins

    def __iter__(self):
        """Iterate over plugin names"""
        return iter(self._plugins.keys())
