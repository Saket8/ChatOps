"""
System Plugin for ChatOps CLI

A built-in plugin that provides basic system information and monitoring commands.
Demonstrates the plugin architecture with command generation and execution capabilities.
"""

import re
import asyncio
import platform
import psutil
import shutil
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..base import (
    BasePlugin,
    CommandPlugin,
    PluginMetadata,
    PluginCapability,
    PluginPriority,
    plugin,
)
from ...core.langchain_integration import DevOpsCommand, CommandType, RiskLevel


@plugin(
    name="system",
    version="1.0.0",
    description="Basic system information and monitoring commands",
    author="ChatOps CLI Team",
    category="system",
    tags=["system", "monitoring", "info"],
    priority=PluginPriority.HIGH,
)
class SystemPlugin(CommandPlugin):
    """
    Plugin for basic system operations and information gathering.

    Provides commands for:
    - System information (OS, CPU, memory)
    - Disk usage
    - Process monitoring
    - Network information
    - Service status
    """

    def __init__(self):
        super().__init__()
        self._capabilities.extend(
            [PluginCapability.SYSTEM_MONITORING, PluginCapability.COMMAND_VALIDATION]
        )

        # Command patterns this plugin can handle
        self._command_patterns = [
            r".*system\s+info.*",
            r".*disk\s+usage.*",
            r".*memory\s+usage.*",
            r".*cpu\s+usage.*",
            r".*process.*list.*",
            r".*check\s+.*space.*",
            r".*show\s+.*info.*",
            r".*system\s+status.*",
            r".*uptime.*",
            r".*network\s+info.*",
        ]

    async def initialize(self) -> bool:
        """Initialize the system plugin"""
        try:
            # Test if we can access system information
            platform.system()
            psutil.cpu_percent()

            self.logger.info("System plugin initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize system plugin: {e}")
            return False

    async def cleanup(self) -> bool:
        """Cleanup system plugin resources"""
        self.logger.info("System plugin cleanup complete")
        return True

    def can_handle(self, user_input: str, context: Dict[str, Any] = None) -> bool:
        """Check if this plugin can handle the user input"""
        user_input_lower = user_input.lower()

        # Check against command patterns
        for pattern in self._command_patterns:
            if re.search(pattern, user_input_lower):
                return True

        # Check for system-related keywords
        system_keywords = [
            "system",
            "disk",
            "memory",
            "cpu",
            "process",
            "uptime",
            "space",
            "usage",
            "info",
            "status",
            "network",
            "hardware",
        ]

        return any(keyword in user_input_lower for keyword in system_keywords)

    async def generate_command(
        self, user_input: str, context: Dict[str, Any] = None
    ) -> Optional[DevOpsCommand]:
        """Generate a system command from natural language input"""
        user_input_lower = user_input.lower()

        # System information
        if any(
            keyword in user_input_lower
            for keyword in ["system info", "system information", "show system"]
        ):
            return DevOpsCommand(
                command="uname -a && lscpu | head -10 && free -h",
                description="Show system information including OS, CPU, and memory",
                command_type=CommandType.SYSTEM_INFO,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 1 second",
                prerequisites=["uname", "lscpu", "free"],
                alternative_commands=["hostnamectl", "cat /proc/cpuinfo | head -20"],
            )

        # Disk usage
        elif any(
            keyword in user_input_lower
            for keyword in ["disk usage", "disk space", "check space"]
        ):
            return DevOpsCommand(
                command="df -h",
                description="Show disk usage for all mounted filesystems",
                command_type=CommandType.SYSTEM_INFO,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 1 second",
                prerequisites=["df"],
                alternative_commands=["du -sh /*", "lsblk"],
            )

        # Memory usage
        elif any(
            keyword in user_input_lower
            for keyword in ["memory usage", "ram usage", "memory info"]
        ):
            return DevOpsCommand(
                command="free -h && cat /proc/meminfo | head -10",
                description="Show memory usage and detailed memory information",
                command_type=CommandType.SYSTEM_INFO,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 1 second",
                prerequisites=["free", "cat"],
                alternative_commands=["vmstat", "top -n 1 | head -5"],
            )

        # CPU usage
        elif any(
            keyword in user_input_lower
            for keyword in ["cpu usage", "cpu info", "processor"]
        ):
            return DevOpsCommand(
                command="top -bn1 | head -20",
                description="Show current CPU usage and top processes",
                command_type=CommandType.SYSTEM_INFO,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 2 seconds",
                prerequisites=["top"],
                alternative_commands=["htop -n", "vmstat 1 1", "mpstat"],
            )

        # Process list
        elif any(
            keyword in user_input_lower
            for keyword in ["process list", "running processes", "show processes"]
        ):
            return DevOpsCommand(
                command="ps aux | head -20",
                description="Show list of running processes",
                command_type=CommandType.PROCESS_MANAGEMENT,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 1 second",
                prerequisites=["ps"],
                alternative_commands=["pstree", "top -n 1"],
            )

        # Uptime
        elif "uptime" in user_input_lower:
            return DevOpsCommand(
                command="uptime && who",
                description="Show system uptime and logged in users",
                command_type=CommandType.SYSTEM_INFO,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 1 second",
                prerequisites=["uptime", "who"],
                alternative_commands=["w", "last | head -10"],
            )

        # Network information
        elif any(
            keyword in user_input_lower
            for keyword in ["network info", "network status", "ip address"]
        ):
            return DevOpsCommand(
                command="ip addr show && ip route show | head -10",
                description="Show network interfaces and routing information",
                command_type=CommandType.NETWORK,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 1 second",
                prerequisites=["ip"],
                alternative_commands=["ifconfig", "netstat -rn", "hostname -I"],
            )

        return None

    async def validate_command(
        self, command: DevOpsCommand, context: Dict[str, Any] = None
    ) -> bool:
        """Validate system commands before execution"""
        # Check if required tools are available
        for prereq in command.prerequisites:
            if not shutil.which(prereq):
                self.logger.warning(f"Required tool not found: {prereq}")
                return False

        # Additional safety checks for system commands
        dangerous_patterns = ["rm ", "del ", "format ", "> /dev/"]
        if any(pattern in command.command.lower() for pattern in dangerous_patterns):
            self.logger.error(
                f"Potentially dangerous command detected: {command.command}"
            )
            return False

        return True

    async def get_metrics(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get system metrics (implements MonitoringPlugin interface)"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": [
                    {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "percent": psutil.disk_usage(partition.mountpoint).percent,
                    }
                    for partition in psutil.disk_partitions()
                    if partition.fstype
                ],
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "load_average": list(psutil.getloadavg())
                if hasattr(psutil, "getloadavg")
                else None,
            }
        except Exception as e:
            self.logger.error(f"Error collecting system metrics: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on system plugin"""
        health = await super().health_check()

        try:
            # Additional health checks
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.virtual_memory().percent

            health.update(
                {
                    "cpu_usage": cpu_usage,
                    "memory_usage": memory_usage,
                    "high_cpu": cpu_usage > 90,
                    "high_memory": memory_usage > 90,
                    "system_platform": platform.system(),
                    "python_version": platform.python_version(),
                }
            )

            # Determine overall health
            if cpu_usage > 95 or memory_usage > 95:
                health["status"] = "warning"
                health["message"] = "High system resource usage detected"

        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)

        return health

    def get_help(self) -> str:
        """Return help text for the system plugin"""
        return """
🖥️  System Plugin v1.0.0

This plugin provides basic system information and monitoring commands.

Supported Commands:
• "system info" / "show system information"
  → Shows OS, CPU, and memory information
  
• "disk usage" / "check disk space"
  → Shows disk usage for all mounted filesystems
  
• "memory usage" / "ram usage"
  → Shows memory usage and detailed memory information
  
• "cpu usage" / "processor info"
  → Shows current CPU usage and top processes
  
• "process list" / "running processes"
  → Shows list of running processes
  
• "uptime"
  → Shows system uptime and logged in users
  
• "network info" / "ip address"
  → Shows network interfaces and routing information

Examples:
  chatops ask "show me system information"
  chatops ask "check disk space"
  chatops ask "what's the memory usage?"
  chatops ask "show running processes"

All commands are read-only and safe to execute.
        """.strip()

    async def configure(self, config: Dict[str, Any]) -> bool:
        """Configure the system plugin"""
        # System plugin doesn't require configuration
        # but we can accept settings like monitoring intervals
        self.logger.info("System plugin configuration updated")
        return True
