"""
LangChain Integration Layer for ChatOps CLI

This module provides LangChain components for natural language processing,
prompt engineering, and structured output parsing for DevOps commands.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import BaseOutputParser, PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, Field, validator
import yaml


class CommandType(Enum):
    """Types of DevOps commands"""

    SYSTEM_INFO = "system_info"
    PROCESS_MANAGEMENT = "process_management"
    FILE_OPERATIONS = "file_operations"
    NETWORK = "network"
    DOCKER = "docker"
    SERVICE_MANAGEMENT = "service_management"
    MONITORING = "monitoring"
    SECURITY = "security"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Risk levels for commands"""

    SAFE = "safe"  # Read-only, no system changes
    LOW = "low"  # Minor changes, easily reversible
    MEDIUM = "medium"  # Significant changes, reversible with effort
    HIGH = "high"  # Major changes, difficult to reverse
    CRITICAL = "critical"  # Irreversible or system-critical changes


@dataclass
class DevOpsCommand:
    """Structured representation of a DevOps command"""

    command: str
    description: str
    command_type: CommandType
    risk_level: RiskLevel
    requires_sudo: bool = False
    requires_confirmation: bool = False
    estimated_duration: str = "< 1 second"
    prerequisites: List[str] = None
    alternative_commands: List[str] = None

    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []
        if self.alternative_commands is None:
            self.alternative_commands = []


class DevOpsCommandModel(BaseModel):
    """Pydantic model for structured command output"""

    command: str = Field(description="The shell command to execute")
    description: str = Field(description="Brief description of what the command does")
    command_type: str = Field(
        description="Type of command (system_info, process_management, etc.)"
    )
    risk_level: str = Field(description="Risk level: safe, low, medium, high, critical")
    requires_sudo: bool = Field(
        default=False, description="Whether the command requires sudo privileges"
    )
    requires_confirmation: bool = Field(
        default=False, description="Whether to ask for user confirmation"
    )
    estimated_duration: str = Field(
        default="< 1 second", description="Estimated execution time"
    )
    prerequisites: List[str] = Field(
        default_factory=list, description="Required tools or conditions"
    )
    alternative_commands: List[str] = Field(
        default_factory=list, description="Alternative ways to achieve the same result"
    )

    @validator("command_type")
    def validate_command_type(cls, v):
        valid_types = [ct.value for ct in CommandType]
        if v not in valid_types:
            return CommandType.UNKNOWN.value
        return v

    @validator("risk_level")
    def validate_risk_level(cls, v):
        valid_levels = [rl.value for rl in RiskLevel]
        if v not in valid_levels:
            return RiskLevel.MEDIUM.value
        return v


class DevOpsOutputParser(BaseOutputParser[DevOpsCommand]):
    """Custom output parser for DevOps commands"""

    def parse(self, text: str) -> DevOpsCommand:
        """Parse LLM output into DevOpsCommand object"""
        try:
            # Try to parse as JSON first
            if text.strip().startswith("{"):
                data = json.loads(text.strip())
            else:
                # Try to extract JSON from text
                json_match = re.search(r"\{.*\}", text, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    # Fallback: parse as simple command
                    return self._parse_simple_command(text)

            # Validate with Pydantic model
            model = DevOpsCommandModel(**data)

            return DevOpsCommand(
                command=model.command,
                description=model.description,
                command_type=CommandType(model.command_type),
                risk_level=RiskLevel(model.risk_level),
                requires_sudo=model.requires_sudo,
                requires_confirmation=model.requires_confirmation,
                estimated_duration=model.estimated_duration,
                prerequisites=model.prerequisites,
                alternative_commands=model.alternative_commands,
            )

        except Exception as e:
            logging.warning(f"Failed to parse structured output: {e}")
            return self._parse_simple_command(text)

    def _parse_simple_command(self, text: str) -> DevOpsCommand:
        """Fallback parser for simple command text"""
        # Extract command from common patterns
        command_patterns = [
            r"`([^`]+)`",  # Code blocks
            r'"([^"]+)"',  # Quoted text
            r"'([^']+)'",  # Single quoted
            r"^(\S+.*?)(?:\n|$)",  # First line
        ]

        command = text.strip()
        for pattern in command_patterns:
            match = re.search(pattern, text)
            if match:
                command = match.group(1).strip()
                break

        # Determine command type and risk level based on command content
        command_type = self._classify_command(command)
        risk_level = self._assess_risk(command)

        return DevOpsCommand(
            command=command,
            description=f"Execute: {command}",
            command_type=command_type,
            risk_level=risk_level,
            requires_sudo=self._requires_sudo(command),
            requires_confirmation=risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL],
        )

    def _classify_command(self, command: str) -> CommandType:
        """Classify command type based on command content"""
        command_lower = command.lower()

        # Classification patterns
        classifications = {
            CommandType.SYSTEM_INFO: [
                "df",
                "free",
                "top",
                "ps",
                "uname",
                "whoami",
                "id",
                "uptime",
                "lscpu",
            ],
            CommandType.PROCESS_MANAGEMENT: [
                "kill",
                "killall",
                "pkill",
                "nohup",
                "jobs",
                "bg",
                "fg",
            ],
            CommandType.FILE_OPERATIONS: [
                "ls",
                "cp",
                "mv",
                "rm",
                "chmod",
                "chown",
                "find",
                "grep",
                "cat",
                "tail",
                "head",
            ],
            CommandType.NETWORK: [
                "ping",
                "curl",
                "wget",
                "netstat",
                "ss",
                "iptables",
                "ufw",
            ],
            CommandType.DOCKER: ["docker", "docker-compose", "podman"],
            CommandType.SERVICE_MANAGEMENT: [
                "systemctl",
                "service",
                "nginx",
                "apache2",
                "mysql",
                "postgres",
            ],
            CommandType.MONITORING: ["htop", "iotop", "watch", "vmstat", "iostat"],
            CommandType.SECURITY: ["sudo", "su", "passwd", "chroot", "selinux"],
        }

        for cmd_type, keywords in classifications.items():
            if any(keyword in command_lower for keyword in keywords):
                return cmd_type

        return CommandType.UNKNOWN

    def _assess_risk(self, command: str) -> RiskLevel:
        """Assess risk level based on command content"""
        command_lower = command.lower()

        # Critical risk patterns
        critical_patterns = ["rm -rf /", "dd if=", "mkfs", "fdisk", "parted"]
        if any(pattern in command_lower for pattern in critical_patterns):
            return RiskLevel.CRITICAL

        # High risk patterns
        high_patterns = ["rm -rf", "rm -r", "kill -9", "shutdown", "reboot", "halt"]
        if any(pattern in command_lower for pattern in high_patterns):
            return RiskLevel.HIGH

        # Medium risk patterns
        medium_patterns = [
            "rm ",
            "mv ",
            "chmod",
            "chown",
            "systemctl stop",
            "systemctl restart",
        ]
        if any(pattern in command_lower for pattern in medium_patterns):
            return RiskLevel.MEDIUM

        # Low risk patterns
        low_patterns = ["cp ", "mkdir", "touch", "echo", "systemctl status"]
        if any(pattern in command_lower for pattern in low_patterns):
            return RiskLevel.LOW

        # Default to safe for read-only commands
        safe_patterns = [
            "ls",
            "cat",
            "grep",
            "find",
            "ps",
            "top",
            "df",
            "free",
            "uname",
        ]
        if any(pattern in command_lower for pattern in safe_patterns):
            return RiskLevel.SAFE

        return RiskLevel.MEDIUM  # Default

    def _requires_sudo(self, command: str) -> bool:
        """Check if command typically requires sudo"""
        sudo_commands = [
            "systemctl",
            "service",
            "apt",
            "yum",
            "dnf",
            "pacman",
            "mount",
            "umount",
            "iptables",
            "ufw",
            "nginx",
            "apache2",
        ]
        command_lower = command.lower()
        return any(cmd in command_lower for cmd in sudo_commands)


class LangChainIntegration:
    """
    Main LangChain integration class for ChatOps CLI.

    Handles prompt templates, chains, and output parsing for
    converting natural language to DevOps commands.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.output_parser = DevOpsOutputParser()
        self._init_prompt_templates()

    def _init_prompt_templates(self):
        """Initialize prompt templates for different use cases"""

        # Main command generation template
        self.command_template = PromptTemplate(
            input_variables=["user_input", "context"],
            template="""You are a DevOps assistant that converts natural language requests into shell commands.

User Request: {user_input}
System Context: {context}

Generate a JSON response with the following structure:
{{
    "command": "the exact shell command to execute",
    "description": "brief description of what this command does",
    "command_type": "one of: system_info, process_management, file_operations, network, docker, service_management, monitoring, security, unknown",
    "risk_level": "one of: safe, low, medium, high, critical",
    "requires_sudo": true/false,
    "requires_confirmation": true/false,
    "estimated_duration": "estimated time like '< 1 second', '2-5 seconds', etc.",
    "prerequisites": ["list", "of", "required", "tools"],
    "alternative_commands": ["alternative", "commands", "if", "any"]
}}

Rules:
1. Provide only standard, safe commands that exist on most Linux/Unix systems
2. Mark destructive operations with high/critical risk and requires_confirmation: true
3. Include sudo requirement only when absolutely necessary
4. Provide helpful alternatives when possible
5. Be conservative with risk assessment - err on the side of caution

Examples:
- "check disk space" → "df -h" (safe, system_info)
- "restart nginx" → "systemctl restart nginx" (medium, service_management, requires_sudo)
- "delete all files" → "rm -rf *" (critical, file_operations, requires_confirmation)
""",
        )

        # Command explanation template
        self.explanation_template = PromptTemplate(
            input_variables=["command"],
            template="""Explain what this shell command does in simple terms:

Command: {command}

Provide a clear, beginner-friendly explanation including:
1. What the command does
2. What each part/flag means
3. Potential risks or side effects
4. When you would typically use it

Keep it concise but informative.""",
        )

        # Safety analysis template
        self.safety_template = PromptTemplate(
            input_variables=["command"],
            template="""Analyze the safety of this shell command:

Command: {command}

Assess:
1. Risk level (safe/low/medium/high/critical)
2. Potential side effects
3. Whether it requires sudo
4. Whether user confirmation is needed
5. Any prerequisites or warnings

Provide JSON response:
{{
    "risk_level": "safe/low/medium/high/critical",
    "requires_sudo": true/false,
    "requires_confirmation": true/false,
    "warnings": ["list", "of", "warnings"],
    "prerequisites": ["required", "tools", "or", "conditions"]
}}""",
        )

    def generate_command(self, user_input: str, context: str = "") -> DevOpsCommand:
        """
        Generate a DevOps command from natural language input.

        Args:
            user_input: Natural language description of what to do
            context: Additional context about the system or situation

        Returns:
            DevOpsCommand object with structured command information
        """
        try:
            # Format the prompt
            prompt = self.command_template.format(
                user_input=user_input, context=context or "Linux/Unix system"
            )

            self.logger.debug(f"Generated prompt for: {user_input}")
            return prompt  # Return prompt for LLM processing

        except Exception as e:
            self.logger.error(f"Failed to generate command prompt: {e}")
            # Return a safe fallback
            return DevOpsCommand(
                command="echo 'Command generation failed'",
                description="Fallback command due to processing error",
                command_type=CommandType.UNKNOWN,
                risk_level=RiskLevel.SAFE,
            )

    def generate_prompt(self, user_input: str, context: str = "") -> str:
        """
        Generate a prompt string for LLM processing.

        Args:
            user_input: Natural language description of what to do
            context: Additional context about the system or situation

        Returns:
            Formatted prompt string for LLM
        """
        try:
            # Format the prompt
            prompt = self.command_template.format(
                user_input=user_input, context=context or "Linux/Unix system"
            )

            self.logger.debug(f"Generated prompt for: {user_input}")
            return prompt

        except Exception as e:
            self.logger.error(f"Failed to generate prompt: {e}")
            return f"Please help with: {user_input}"

    def parse_llm_response(self, llm_response: str) -> DevOpsCommand:
        """
        Parse LLM response into structured DevOpsCommand.

        Args:
            llm_response: Raw response from LLM

        Returns:
            DevOpsCommand object
        """
        return self.output_parser.parse(llm_response)

    def explain_command(self, command: str) -> str:
        """
        Generate explanation prompt for a command.

        Args:
            command: Shell command to explain

        Returns:
            Formatted prompt for LLM
        """
        return self.explanation_template.format(command=command)

    def analyze_safety(self, command: str) -> str:
        """
        Generate safety analysis prompt for a command.

        Args:
            command: Shell command to analyze

        Returns:
            Formatted prompt for LLM
        """
        return self.safety_template.format(command=command)

    def get_command_examples(self) -> Dict[str, List[Dict[str, str]]]:
        """
        Get example commands by category.

        Returns:
            Dictionary of command examples organized by type
        """
        return {
            "system_info": [
                {
                    "input": "check disk space",
                    "command": "df -h",
                    "description": "Show disk usage in human-readable format",
                },
                {
                    "input": "show memory usage",
                    "command": "free -h",
                    "description": "Display memory usage statistics",
                },
                {
                    "input": "list running processes",
                    "command": "ps aux",
                    "description": "Show all running processes",
                },
            ],
            "file_operations": [
                {
                    "input": "list files",
                    "command": "ls -la",
                    "description": "List all files with details",
                },
                {
                    "input": "find large files",
                    "command": "find / -type f -size +100M",
                    "description": "Find files larger than 100MB",
                },
                {
                    "input": "show file content",
                    "command": "cat filename",
                    "description": "Display file contents",
                },
            ],
            "service_management": [
                {
                    "input": "restart nginx",
                    "command": "systemctl restart nginx",
                    "description": "Restart nginx web server",
                },
                {
                    "input": "check service status",
                    "command": "systemctl status servicename",
                    "description": "Show service status",
                },
                {
                    "input": "start docker",
                    "command": "systemctl start docker",
                    "description": "Start Docker service",
                },
            ],
            "network": [
                {
                    "input": "test connectivity",
                    "command": "ping google.com",
                    "description": "Test network connectivity",
                },
                {
                    "input": "show open ports",
                    "command": "netstat -tuln",
                    "description": "Display listening ports",
                },
                {
                    "input": "download file",
                    "command": "wget https://example.com/file",
                    "description": "Download file from URL",
                },
            ],
        }

    def get_safety_guidelines(self) -> Dict[str, List[str]]:
        """
        Get safety guidelines for different risk levels.

        Returns:
            Dictionary of safety guidelines by risk level
        """
        return {
            "safe": [
                "Read-only operations",
                "No system changes",
                "Can be run by any user",
                "No confirmation needed",
            ],
            "low": [
                "Minor changes only",
                "Easily reversible",
                "Usually safe to run",
                "Minimal system impact",
            ],
            "medium": [
                "Significant changes possible",
                "Review command before running",
                "May require privileges",
                "Consider backup first",
            ],
            "high": [
                "Major system changes",
                "Requires confirmation",
                "Difficult to reverse",
                "Potential service disruption",
            ],
            "critical": [
                "Irreversible changes",
                "System-wide impact",
                "Mandatory confirmation",
                "Expert supervision recommended",
            ],
        }
