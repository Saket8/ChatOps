"""
Docker Operations Plugin for ChatOps CLI

Provides Docker container and image management commands through natural language.
Supports container lifecycle, inspection, and image operations with safety validations.
"""

import re
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
from ...core.os_detection import os_detection


@plugin(
    name="docker",
    version="1.0.0",
    description="Docker container and image management operations",
    author="ChatOps CLI Team",
    category="containers",
    tags=["docker", "containers", "images", "devops"],
    priority=PluginPriority.HIGH,
)
class DockerPlugin(CommandPlugin):
    """
    Plugin for Docker operations and container management.

    Provides commands for:
    - Container lifecycle (start, stop, restart, remove)
    - Container inspection (ps, logs, inspect, stats)
    - Image management (list, pull, push, remove)
    - Network operations (list, inspect)
    - Volume operations (list, inspect)
    """

    def __init__(self):
        super().__init__()
        self._capabilities.extend([
            PluginCapability.CONTAINER_MANAGEMENT,
            PluginCapability.COMMAND_VALIDATION,
            PluginCapability.SYSTEM_MONITORING
        ])

        # Docker command patterns this plugin can handle
        self._command_patterns = [
            r".*docker\s+.*",
            r".*container[s]?\s+.*",
            r".*image[s]?\s+.*",
            r".*start\s+container.*",
            r".*stop\s+container.*", 
            r".*restart\s+container.*",
            r".*list\s+containers.*",
            r".*show\s+containers.*",
            r".*docker\s+ps.*",
            r".*container\s+logs.*",
            r".*pull\s+image.*",
            r".*remove\s+image.*",
            r".*docker\s+images.*",
        ]

        # Safe Docker commands whitelist
        self._safe_commands = {
            'ps', 'images', 'version', 'info', 'stats', 'logs', 'inspect', 
            'history', 'network', 'volume', 'system', 'search'
        }

        # Commands requiring extra caution
        self._dangerous_commands = {
            'rm', 'rmi', 'kill', 'stop', 'remove', 'prune', 'system prune'
        }

    async def initialize(self) -> bool:
        """Initialize the Docker plugin"""
        try:
            # Check if Docker is available
            if not shutil.which("docker"):
                self.logger.warning("Docker command not found in PATH")
                return False

            # Test Docker connectivity (optional - may not have Docker running)
            self.logger.info("Docker plugin initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Docker plugin: {e}")
            return False

    async def cleanup(self) -> bool:
        """Cleanup Docker plugin resources"""
        self.logger.info("Docker plugin cleanup complete")
        return True

    def can_handle(self, user_input: str, context: Dict[str, Any] = None) -> bool:
        """Check if this plugin can handle the user input"""
        user_input_lower = user_input.lower()

        # Check against command patterns
        for pattern in self._command_patterns:
            if re.search(pattern, user_input_lower):
                return True

        # Check for Docker-related keywords
        docker_keywords = [
            "docker", "container", "containers", "image", "images",
            "dockerfile", "compose", "registry", "hub"
        ]

        return any(keyword in user_input_lower for keyword in docker_keywords)

    async def generate_command(
        self, user_input: str, context: Dict[str, Any] = None
    ) -> Optional[DevOpsCommand]:
        """Generate Docker command from natural language input"""
        user_input_lower = user_input.lower()
        os_info = os_detection.get_os_info()

        # Container Lifecycle Operations
        if any(keyword in user_input_lower for keyword in ["start container", "run container"]):
            return self._generate_container_start_command(user_input_lower)
        
        elif any(keyword in user_input_lower for keyword in ["stop container", "kill container"]):
            return self._generate_container_stop_command(user_input_lower)
        
        elif any(keyword in user_input_lower for keyword in ["restart container"]):
            return self._generate_container_restart_command(user_input_lower)
        
        elif any(keyword in user_input_lower for keyword in ["remove container", "delete container"]):
            return self._generate_container_remove_command(user_input_lower)

        # Container Inspection
        elif any(keyword in user_input_lower for keyword in ["list containers", "show containers", "docker ps", "containers running"]):
            return DevOpsCommand(
                command="docker ps -a --format 'table {{.ID}}\\t{{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'",
                description="List all Docker containers with detailed information",
                command_type=CommandType.DOCKER,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 2 seconds",
                prerequisites=["docker"],
                alternative_commands=["docker ps", "docker container ls -a"]
            )

        elif any(keyword in user_input_lower for keyword in ["container logs", "show logs", "docker logs"]):
            return self._generate_container_logs_command(user_input_lower)

        elif any(keyword in user_input_lower for keyword in ["container stats", "docker stats"]):
            return DevOpsCommand(
                command="docker stats --no-stream --format 'table {{.Container}}\\t{{.CPUPerc}}\\t{{.MemUsage}}\\t{{.MemPerc}}\\t{{.NetIO}}\\t{{.BlockIO}}'",
                description="Show Docker container resource usage statistics",
                command_type=CommandType.MONITORING,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["docker"],
                alternative_commands=["docker stats"]
            )

        # Image Management
        elif any(keyword in user_input_lower for keyword in ["list images", "show images", "docker images"]):
            return DevOpsCommand(
                command="docker images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.ID}}\\t{{.Size}}\\t{{.CreatedSince}}'",
                description="List all Docker images with detailed information",
                command_type=CommandType.DOCKER,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 2 seconds",
                prerequisites=["docker"],
                alternative_commands=["docker images", "docker image ls"]
            )

        elif any(keyword in user_input_lower for keyword in ["pull image", "download image"]):
            return self._generate_image_pull_command(user_input_lower)

        elif any(keyword in user_input_lower for keyword in ["remove image", "delete image"]):
            return self._generate_image_remove_command(user_input_lower)

        # Docker System Information
        elif any(keyword in user_input_lower for keyword in ["docker info", "docker version", "docker system"]):
            return DevOpsCommand(
                command="docker info && echo '\\n--- Docker Version ---' && docker version",
                description="Show Docker system information and version details",
                command_type=CommandType.SYSTEM_INFO,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 3 seconds",
                prerequisites=["docker"],
                alternative_commands=["docker system info", "docker --version"]
            )

        # Network Operations
        elif any(keyword in user_input_lower for keyword in ["docker networks", "list networks"]):
            return DevOpsCommand(
                command="docker network ls --format 'table {{.ID}}\\t{{.Name}}\\t{{.Driver}}\\t{{.Scope}}'",
                description="List Docker networks",
                command_type=CommandType.NETWORK,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 2 seconds",
                prerequisites=["docker"],
                alternative_commands=["docker network ls"]
            )

        # Volume Operations  
        elif any(keyword in user_input_lower for keyword in ["docker volumes", "list volumes"]):
            return DevOpsCommand(
                command="docker volume ls --format 'table {{.Driver}}\\t{{.Name}}'",
                description="List Docker volumes",
                command_type=CommandType.FILE_OPERATIONS,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 2 seconds",
                prerequisites=["docker"],
                alternative_commands=["docker volume ls"]
            )

        return None

    def _generate_container_start_command(self, user_input: str) -> DevOpsCommand:
        """Generate container start/run command"""
        # Extract container name or image if provided
        if "run" in user_input:
            return DevOpsCommand(
                command="docker run -d --name <container_name> <image_name>",
                description="Start a new Docker container (replace placeholders with actual values)",
                command_type=CommandType.DOCKER,
                risk_level=RiskLevel.MEDIUM,
                requires_sudo=False,
                estimated_duration="< 10 seconds",
                prerequisites=["docker"],
                alternative_commands=["docker run -it <image_name>", "docker create <image_name>"]
            )
        else:
            return DevOpsCommand(
                command="docker start <container_name_or_id>",
                description="Start an existing Docker container (replace with actual container name/ID)",
                command_type=CommandType.DOCKER,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 5 seconds",
                prerequisites=["docker"],
                alternative_commands=["docker restart <container_name>"]
            )

    def _generate_container_stop_command(self, user_input: str) -> DevOpsCommand:
        """Generate container stop command"""
        return DevOpsCommand(
            command="docker stop <container_name_or_id>",
            description="Stop a running Docker container (replace with actual container name/ID)",
            command_type=CommandType.DOCKER,
            risk_level=RiskLevel.MEDIUM,
            requires_sudo=False,
            estimated_duration="< 10 seconds",
            prerequisites=["docker"],
            alternative_commands=["docker kill <container_name>"]
        )

    def _generate_container_restart_command(self, user_input: str) -> DevOpsCommand:
        """Generate container restart command"""
        return DevOpsCommand(
            command="docker restart <container_name_or_id>",
            description="Restart a Docker container (replace with actual container name/ID)",
            command_type=CommandType.DOCKER,
            risk_level=RiskLevel.MEDIUM,
            requires_sudo=False,
            estimated_duration="< 15 seconds",
            prerequisites=["docker"],
            alternative_commands=["docker stop <container> && docker start <container>"]
        )

    def _generate_container_remove_command(self, user_input: str) -> DevOpsCommand:
        """Generate container remove command"""
        return DevOpsCommand(
            command="docker rm <container_name_or_id>",
            description="Remove a Docker container (replace with actual container name/ID)",
            command_type=CommandType.DOCKER,
            risk_level=RiskLevel.HIGH,
            requires_sudo=False,
            estimated_duration="< 5 seconds",
            prerequisites=["docker"],
            alternative_commands=["docker rm -f <container_name>"]
        )

    def _generate_container_logs_command(self, user_input: str) -> DevOpsCommand:
        """Generate container logs command"""
        return DevOpsCommand(
            command="docker logs --tail 50 <container_name_or_id>",
            description="Show recent logs from a Docker container (replace with actual container name/ID)",
            command_type=CommandType.MONITORING,
            risk_level=RiskLevel.SAFE,
            requires_sudo=False,
            estimated_duration="< 3 seconds",
            prerequisites=["docker"],
            alternative_commands=["docker logs -f <container>", "docker logs --since 1h <container>"]
        )

    def _generate_image_pull_command(self, user_input: str) -> DevOpsCommand:
        """Generate image pull command"""
        return DevOpsCommand(
            command="docker pull <image_name:tag>",
            description="Pull a Docker image from registry (replace with actual image name)",
            command_type=CommandType.DOCKER,
            risk_level=RiskLevel.SAFE,
            requires_sudo=False,
            estimated_duration="< 60 seconds",
            prerequisites=["docker"],
            alternative_commands=["docker pull <image>:latest"]
        )

    def _generate_image_remove_command(self, user_input: str) -> DevOpsCommand:
        """Generate image remove command"""
        return DevOpsCommand(
            command="docker rmi <image_name_or_id>",
            description="Remove a Docker image (replace with actual image name/ID)",
            command_type=CommandType.DOCKER,
            risk_level=RiskLevel.HIGH,
            requires_sudo=False,
            estimated_duration="< 10 seconds",
            prerequisites=["docker"],
            alternative_commands=["docker image rm <image>", "docker rmi -f <image>"]
        )

    async def validate_command(
        self, command: DevOpsCommand, context: Dict[str, Any] = None
    ) -> bool:
        """Validate Docker commands before execution"""
        # Check if Docker is available
        if not shutil.which("docker"):
            self.logger.error("Docker command not found in PATH")
            return False

        # Extract base Docker command
        cmd_parts = command.command.split()
        if not cmd_parts or cmd_parts[0] != "docker":
            return False

        # Check for dangerous operations
        cmd_str = command.command.lower()
        for dangerous_cmd in self._dangerous_commands:
            if dangerous_cmd in cmd_str:
                self.logger.warning(f"Potentially dangerous Docker command: {dangerous_cmd}")
                # Allow but flag as high risk
                if command.risk_level == RiskLevel.SAFE:
                    command.risk_level = RiskLevel.HIGH

        return True

    def get_help(self) -> str:
        """Return help text for the Docker plugin"""
        return """
🐳 Docker Plugin v1.0.0

This plugin provides Docker container and image management commands.

Container Lifecycle:
• "start container <name>" / "run container <image>"
  → Start existing container or run new one
  
• "stop container <name>" / "kill container <name>"
  → Stop running container
  
• "restart container <name>"
  → Restart container
  
• "remove container <name>"
  → Delete container (⚠️ permanent)

Container Inspection:
• "list containers" / "show containers" / "docker ps"
  → Show all containers with status
  
• "container logs <name>" / "show logs <name>"
  → Display container logs
  
• "container stats" / "docker stats"
  → Show resource usage statistics

Image Management:
• "list images" / "show images" / "docker images"
  → Show all Docker images
  
• "pull image <name>" / "download image <name>"
  → Pull image from registry
  
• "remove image <name>"
  → Delete image (⚠️ permanent)

System Information:
• "docker info" / "docker version"
  → Show Docker system information
  
• "docker networks" / "list networks"
  → Show Docker networks
  
• "docker volumes" / "list volumes"
  → Show Docker volumes

Examples:
  chatops ask "list running containers"
  chatops ask "show logs for nginx container"
  chatops ask "pull ubuntu image"
  chatops ask "docker system info"

⚠️ Note: Commands marked with placeholders like <container_name> 
require you to replace them with actual values before execution.
        """.strip()

    async def get_metrics(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get Docker metrics"""
        try:
            return {
                "timestamp": datetime.now().isoformat(),
                "docker_available": bool(shutil.which("docker")),
                "plugin_status": "active",
                "supported_operations": [
                    "container_lifecycle", "container_inspection",
                    "image_management", "network_operations", "volume_operations"
                ]
            }
        except Exception as e:
            self.logger.error(f"Error collecting Docker metrics: {e}")
            return {"error": str(e)} 