"""
Comprehensive Security System for ChatOps CLI

This module provides advanced security features including command preview,
enhanced validation, operation rollback, and comprehensive safety mechanisms.
"""

import asyncio
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import pickle

from ..settings import settings
from .os_detection import os_detection


class SecurityLevel(Enum):
    """Security levels for different operations"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OperationType(Enum):
    """Types of operations that can be performed"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    NETWORK = "network"
    SYSTEM = "system"
    DESTRUCTIVE = "destructive"


@dataclass
class CommandPreview:
    """Preview information for a command before execution"""
    command: str
    description: str
    risk_level: SecurityLevel
    operation_type: OperationType
    affected_files: List[str] = field(default_factory=list)
    affected_services: List[str] = field(default_factory=list)
    estimated_impact: str = ""
    rollback_available: bool = False
    rollback_command: Optional[str] = None
    requires_confirmation: bool = False
    safety_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class RollbackOperation:
    """Information about a rollback operation"""
    original_command: str
    rollback_command: str
    timestamp: datetime
    success: bool = False
    error_message: Optional[str] = None
    backup_files: List[str] = field(default_factory=list)


class CommandBlacklist:
    """Manages blacklisted commands and patterns"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".CommandBlacklist")
        
        # Critical commands that should never be executed
        self._critical_blacklist = {
            # System destruction commands
            "rm -rf /",
            "rm -rf /*",
            "format c:",
            "format /",
            "mkfs.ext4 /dev/sda",
            "dd if=/dev/zero of=/dev/sda",
            
            # User management (dangerous)
            "userdel -r",
            "deluser --remove-home",
            
            # Network (dangerous)
            "iptables -F",
            "firewall-cmd --set-default-zone=drop",
            
            # Windows specific
            "del /s /q c:\\",
            "rmdir /s /q c:\\",
            "format c: /q",
        }
        
        # Pattern-based blacklist
        self._pattern_blacklist = [
            r'rm\s+-rf\s+/[^/]*$',  # rm -rf /something (but not /something/else)
            r'rm\s+-rf\s+/\*',
            r'dd\s+.*of=/dev/[hs]d[a-z]',
            r'mkfs\..*\s+/dev/[hs]d[a-z]',
            r'fdisk\s+/dev/[hs]d[a-z]',
            r'format\s+[a-zA-Z]:\s*/q',
            r'del\s+/s\s+/q\s+[a-zA-Z]:\\',
        ]
        
        # Dynamic blacklist (can be updated at runtime)
        self._dynamic_blacklist: Set[str] = set()
        
        # Load custom blacklist from settings
        if hasattr(settings, 'security') and hasattr(settings.security, 'blocked_commands'):
            for cmd in settings.security.blocked_commands:
                self._dynamic_blacklist.add(cmd.lower())
    
    def is_blacklisted(self, command: str) -> Tuple[bool, str]:
        """Check if a command is blacklisted"""
        cmd_lower = command.lower().strip()
        
        # Check exact matches
        if cmd_lower in self._critical_blacklist:
            return True, f"Command is in critical blacklist: {command}"
        
        if cmd_lower in self._dynamic_blacklist:
            return True, f"Command is in dynamic blacklist: {command}"
        
        # Check pattern matches
        for pattern in self._pattern_blacklist:
            if re.search(pattern, command, re.IGNORECASE):
                return True, f"Command matches blacklist pattern: {pattern}"
        
        return False, ""
    
    def add_to_blacklist(self, command: str, reason: str = "") -> bool:
        """Add a command to the dynamic blacklist"""
        try:
            self._dynamic_blacklist.add(command.lower().strip())
            self.logger.info(f"Added to blacklist: {command} (reason: {reason})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add to blacklist: {e}")
            return False
    
    def remove_from_blacklist(self, command: str) -> bool:
        """Remove a command from the dynamic blacklist"""
        try:
            self._dynamic_blacklist.discard(command.lower().strip())
            self.logger.info(f"Removed from blacklist: {command}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove from blacklist: {e}")
            return False
    
    def get_blacklist(self) -> Dict[str, List[str]]:
        """Get current blacklist status"""
        return {
            "critical": list(self._critical_blacklist),
            "dynamic": list(self._dynamic_blacklist),
            "patterns": self._pattern_blacklist
        }


class CommandPreviewer:
    """Analyzes commands and provides detailed previews"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".CommandPreviewer")
        
        # File operation patterns
        self._file_operations = {
            'read': [r'cat\s+', r'head\s+', r'tail\s+', r'less\s+', r'more\s+', r'type\s+'],
            'write': [r'>\s*', r'>>\s*', r'echo\s+.*>', r'cp\s+', r'mv\s+', r'copy\s+', r'move\s+'],
            'delete': [r'rm\s+', r'del\s+', r'rmdir\s+', r'Remove-Item\s+', r'Remove-Child\s+'],
        }
        
        # Service operation patterns
        self._service_operations = {
            'start': [r'systemctl\s+start', r'service\s+.*start', r'Start-Service\s+'],
            'stop': [r'systemctl\s+stop', r'service\s+.*stop', r'Stop-Service\s+'],
            'restart': [r'systemctl\s+restart', r'service\s+.*restart', r'Restart-Service\s+'],
        }
        
        # Rollback command mappings
        self._rollback_mappings = {
            'cp': 'rm',  # Copy -> Remove
            'mv': 'mv',  # Move -> Move back
            'mkdir': 'rmdir',  # Create dir -> Remove dir
            'New-Item': 'Remove-Item',  # PowerShell create -> remove
        }
    
    def preview_command(self, command: str, description: str = "") -> CommandPreview:
        """Generate a detailed preview of a command"""
        preview = CommandPreview(
            command=command,
            description=description,
            risk_level=self._assess_risk_level(command),
            operation_type=self._determine_operation_type(command),
            affected_files=self._extract_affected_files(command),
            affected_services=self._extract_affected_services(command),
            estimated_impact=self._estimate_impact(command),
            rollback_available=self._can_rollback(command),
            rollback_command=self._generate_rollback_command(command),
            requires_confirmation=self._requires_confirmation(command),
            safety_checks=self._generate_safety_checks(command),
            warnings=self._generate_warnings(command)
        )
        
        return preview
    
    def _assess_risk_level(self, command: str) -> SecurityLevel:
        """Assess the risk level of a command"""
        cmd_lower = command.lower()
        
        # Critical risk patterns
        critical_patterns = [
            r'rm\s+-rf\s+/', r'format\s+[a-zA-Z]:', r'dd\s+.*of=/dev/',
            r'mkfs\..*\s+/dev/', r'fdisk\s+/dev/', r'del\s+/s\s+/q\s+[a-zA-Z]:\\'
        ]
        
        for pattern in critical_patterns:
            if re.search(pattern, cmd_lower):
                return SecurityLevel.CRITICAL
        
        # High risk patterns
        high_patterns = [
            r'rm\s+-rf', r'rmdir\s+/s', r'Remove-Item\s+-Recurse\s+-Force',
            r'systemctl\s+(stop|disable)', r'Stop-Service', r'Disable-Service'
        ]
        
        for pattern in high_patterns:
            if re.search(pattern, cmd_lower):
                return SecurityLevel.HIGH
        
        # Medium risk patterns
        medium_patterns = [
            r'rm\s+', r'del\s+', r'mv\s+', r'move\s+', r'cp\s+', r'copy\s+',
            r'systemctl\s+restart', r'Restart-Service'
        ]
        
        for pattern in medium_patterns:
            if re.search(pattern, cmd_lower):
                return SecurityLevel.MEDIUM
        
        # Low risk patterns
        low_patterns = [
            r'ls\s+', r'dir\s+', r'cat\s+', r'type\s+', r'head\s+', r'tail\s+',
            r'ps\s+', r'Get-Process', r'df\s+', r'Get-WmiObject'
        ]
        
        for pattern in low_patterns:
            if re.search(pattern, cmd_lower):
                return SecurityLevel.LOW
        
        return SecurityLevel.SAFE
    
    def _determine_operation_type(self, command: str) -> OperationType:
        """Determine the type of operation"""
        cmd_lower = command.lower()
        
        # Check for destructive operations
        if any(re.search(pattern, cmd_lower) for pattern in self._file_operations['delete']):
            return OperationType.DESTRUCTIVE
        
        # Check for system operations
        if 'systemctl' in cmd_lower or 'service' in cmd_lower:
            return OperationType.SYSTEM
        
        # Check for network operations
        if any(word in cmd_lower for word in ['netstat', 'ping', 'curl', 'wget', 'ssh', 'scp']):
            return OperationType.NETWORK
        
        # Check for write operations
        if any(re.search(pattern, cmd_lower) for pattern in self._file_operations['write']):
            return OperationType.WRITE
        
        # Check for read operations
        if any(re.search(pattern, cmd_lower) for pattern in self._file_operations['read']):
            return OperationType.READ
        
        return OperationType.EXECUTE
    
    def _extract_affected_files(self, command: str) -> List[str]:
        """Extract files that will be affected by the command"""
        files = []
        
        # Extract file paths from command
        # This is a simplified version - in production, you'd want more sophisticated parsing
        file_patterns = [
            r'(\S+\.\w+)',  # Files with extensions
            r'([a-zA-Z]:\\[^\s]+)',  # Windows paths
            r'(/[^\s]+)',  # Unix paths
        ]
        
        for pattern in file_patterns:
            matches = re.findall(pattern, command)
            files.extend(matches)
        
        return list(set(files))  # Remove duplicates
    
    def _extract_affected_services(self, command: str) -> List[str]:
        """Extract services that will be affected by the command"""
        services = []
        
        # Extract service names from systemctl commands
        systemctl_match = re.search(r'systemctl\s+\w+\s+(\S+)', command)
        if systemctl_match:
            services.append(systemctl_match.group(1))
        
        # Extract service names from PowerShell commands
        ps_match = re.search(r'(Start|Stop|Restart)-Service\s+(\S+)', command)
        if ps_match:
            services.append(ps_match.group(2))
        
        return services
    
    def _estimate_impact(self, command: str) -> str:
        """Estimate the impact of the command"""
        risk_level = self._assess_risk_level(command)
        operation_type = self._determine_operation_type(command)
        
        if risk_level == SecurityLevel.CRITICAL:
            return "CRITICAL: May cause system damage or data loss"
        elif risk_level == SecurityLevel.HIGH:
            return "HIGH: May affect system stability or delete important data"
        elif risk_level == SecurityLevel.MEDIUM:
            return "MEDIUM: May modify files or services"
        elif risk_level == SecurityLevel.LOW:
            return "LOW: Read-only or safe operations"
        else:
            return "SAFE: No significant impact expected"
    
    def _can_rollback(self, command: str) -> bool:
        """Check if the command can be rolled back"""
        cmd_lower = command.lower()
        
        # Commands that can be rolled back
        rollbackable_patterns = [
            r'cp\s+', r'copy\s+', r'mv\s+', r'move\s+', r'mkdir\s+', r'New-Item\s+',
            r'systemctl\s+start', r'Start-Service\s+'
        ]
        
        return any(re.search(pattern, cmd_lower) for pattern in rollbackable_patterns)
    
    def _generate_rollback_command(self, command: str) -> Optional[str]:
        """Generate a rollback command if possible"""
        if not self._can_rollback(command):
            return None
        
        # Simple rollback logic - in production, you'd want more sophisticated rollback strategies
        cmd_lower = command.lower()
        
        if re.search(r'cp\s+', cmd_lower):
            # For copy operations, rollback is to remove the destination
            parts = command.split()
            if len(parts) >= 3:
                return f"rm {parts[-1]}"  # Remove the last argument (destination)
        
        elif re.search(r'mkdir\s+', cmd_lower):
            # For directory creation, rollback is to remove the directory
            parts = command.split()
            if len(parts) >= 2:
                return f"rmdir {parts[-1]}"  # Remove the last argument (directory)
        
        elif re.search(r'systemctl\s+start', cmd_lower):
            # For service start, rollback is to stop the service
            return command.replace('start', 'stop')
        
        return None
    
    def _requires_confirmation(self, command: str) -> bool:
        """Check if the command requires confirmation"""
        risk_level = self._assess_risk_level(command)
        operation_type = self._determine_operation_type(command)
        
        return (risk_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL] or
                operation_type == OperationType.DESTRUCTIVE)
    
    def _generate_safety_checks(self, command: str) -> List[str]:
        """Generate safety checks for the command"""
        checks = []
        
        # File existence checks
        affected_files = self._extract_affected_files(command)
        for file_path in affected_files:
            if file_path and not file_path.startswith(('-', '--')):
                checks.append(f"Verify file exists: {file_path}")
        
        # Service existence checks
        affected_services = self._extract_affected_services(command)
        for service in affected_services:
            checks.append(f"Verify service exists: {service}")
        
        # Permission checks
        if 'rm' in command.lower() or 'del' in command.lower():
            checks.append("Verify write permissions for target directory")
        
        return checks
    
    def _generate_warnings(self, command: str) -> List[str]:
        """Generate warnings for the command"""
        warnings = []
        
        risk_level = self._assess_risk_level(command)
        
        if risk_level == SecurityLevel.CRITICAL:
            warnings.append("⚠️  CRITICAL: This command may cause irreversible damage")
        elif risk_level == SecurityLevel.HIGH:
            warnings.append("⚠️  HIGH RISK: This command may delete important data")
        elif risk_level == SecurityLevel.MEDIUM:
            warnings.append("⚠️  MEDIUM RISK: This command will modify files or services")
        
        # Specific warnings
        if 'rm -rf' in command.lower():
            warnings.append("⚠️  Recursive delete - all files and subdirectories will be removed")
        
        if 'format' in command.lower():
            warnings.append("⚠️  Format operation - all data will be erased")
        
        return warnings


class RollbackManager:
    """Manages rollback operations for reversible commands"""
    
    def __init__(self, backup_directory: Optional[Path] = None):
        self.logger = logging.getLogger(__name__ + ".RollbackManager")
        self.backup_directory = backup_directory or Path(".chatops_backups")
        self.backup_directory.mkdir(exist_ok=True)
        
        # Store rollback operations
        self._rollback_operations: Dict[str, RollbackOperation] = {}
        self._rollback_file = self.backup_directory / "rollback_history.pkl"
        
        # Load existing rollback history
        self._load_rollback_history()
    
    def _load_rollback_history(self):
        """Load rollback history from file"""
        try:
            if self._rollback_file.exists():
                with open(self._rollback_file, 'rb') as f:
                    self._rollback_operations = pickle.load(f)
                self.logger.info(f"Loaded {len(self._rollback_operations)} rollback operations")
        except Exception as e:
            self.logger.error(f"Failed to load rollback history: {e}")
            self._rollback_operations = {}
    
    def _save_rollback_history(self):
        """Save rollback history to file"""
        try:
            with open(self._rollback_file, 'wb') as f:
                pickle.dump(self._rollback_operations, f)
        except Exception as e:
            self.logger.error(f"Failed to save rollback history: {e}")
    
    def create_backup(self, file_path: Path) -> Optional[Path]:
        """Create a backup of a file before modification"""
        try:
            if not file_path.exists():
                return None
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.name}.backup_{timestamp}"
            backup_path = self.backup_directory / backup_name
            
            # Copy the file
            shutil.copy2(file_path, backup_path)
            self.logger.info(f"Created backup: {backup_path}")
            
            return backup_path
        except Exception as e:
            self.logger.error(f"Failed to create backup for {file_path}: {e}")
            return None
    
    def register_rollback(self, command_id: str, original_command: str, 
                         rollback_command: str, backup_files: List[str] = None):
        """Register a rollback operation"""
        rollback_op = RollbackOperation(
            original_command=original_command,
            rollback_command=rollback_command,
            timestamp=datetime.now(),
            backup_files=backup_files or []
        )
        
        self._rollback_operations[command_id] = rollback_op
        self._save_rollback_history()
        
        self.logger.info(f"Registered rollback for command {command_id}")
    
    async def execute_rollback(self, command_id: str) -> bool:
        """Execute a rollback operation"""
        if command_id not in self._rollback_operations:
            self.logger.error(f"No rollback operation found for {command_id}")
            return False
        
        rollback_op = self._rollback_operations[command_id]
        
        try:
            # Execute the rollback command
            process = await asyncio.create_subprocess_shell(
                rollback_op.rollback_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                rollback_op.success = True
                self.logger.info(f"Rollback successful for {command_id}")
            else:
                rollback_op.success = False
                rollback_op.error_message = stderr.decode()
                self.logger.error(f"Rollback failed for {command_id}: {stderr.decode()}")
            
            # Update rollback history
            self._save_rollback_history()
            
            return rollback_op.success
            
        except Exception as e:
            rollback_op.success = False
            rollback_op.error_message = str(e)
            self.logger.error(f"Rollback execution error for {command_id}: {e}")
            self._save_rollback_history()
            return False
    
    def get_rollback_history(self, limit: int = 50) -> List[RollbackOperation]:
        """Get rollback operation history"""
        operations = list(self._rollback_operations.values())
        operations.sort(key=lambda x: x.timestamp, reverse=True)
        return operations[:limit]
    
    def cleanup_old_backups(self, days: int = 30):
        """Clean up old backup files"""
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for backup_file in self.backup_directory.glob("*.backup_*"):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    backup_file.unlink()
                    cleaned_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to clean up {backup_file}: {e}")
        
        self.logger.info(f"Cleaned up {cleaned_count} old backup files")
        return cleaned_count


class SecuritySystem:
    """
    Comprehensive security system for ChatOps CLI
    
    Provides command preview, enhanced validation, rollback capabilities,
    and advanced safety features.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.blacklist = CommandBlacklist()
        self.previewer = CommandPreviewer()
        self.rollback_manager = RollbackManager()
        
        # Security settings
        self.require_confirmation = self.config.get('require_confirmation', True)
        self.safe_mode = self.config.get('safe_mode', True)
        self.dry_run_default = self.config.get('dry_run_default', False)
        
        # Command history for analysis
        self._command_history: List[str] = []
        self._max_history_size = 1000
        
        self.logger.info("Security system initialized")
    
    def analyze_command(self, command: str, description: str = "") -> CommandPreview:
        """Analyze a command and provide comprehensive preview"""
        # Check blacklist first
        is_blacklisted, reason = self.blacklist.is_blacklisted(command)
        if is_blacklisted:
            preview = CommandPreview(
                command=command,
                description=description,
                risk_level=SecurityLevel.CRITICAL,
                operation_type=OperationType.DESTRUCTIVE,
                estimated_impact=f"BLOCKED: {reason}",
                rollback_available=False,
                requires_confirmation=False,
                warnings=[f"🚫 Command is blacklisted: {reason}"]
            )
            return preview
        
        # Generate detailed preview
        preview = self.previewer.preview_command(command, description)
        
        # Add to command history
        self._command_history.append(command)
        if len(self._command_history) > self._max_history_size:
            self._command_history = self._command_history[-self._max_history_size:]
        
        return preview
    
    def validate_command(self, command: str, preview: CommandPreview) -> Tuple[bool, List[str]]:
        """Validate a command with enhanced security checks"""
        errors = []
        
        # Check blacklist
        is_blacklisted, reason = self.blacklist.is_blacklisted(command)
        if is_blacklisted:
            errors.append(f"Command is blacklisted: {reason}")
        
        # Check command length
        if len(command) > settings.security.max_command_length:
            errors.append(f"Command too long (max {settings.security.max_command_length} characters)")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'[;&|`]',  # Command separators
            r'\$\{.*\}',  # Variable substitution
            r'\\x[0-9a-fA-F]{2}',  # Hex escapes
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, command):
                errors.append(f"Suspicious pattern detected: {pattern}")
        
        # OS-specific validations
        os_info = os_detection.get_os_info()
        if os_info.is_windows:
            # Windows-specific checks
            if 'format' in command.lower() and 'c:' in command.lower():
                errors.append("Attempted format of system drive")
        else:
            # Unix-specific checks
            if '>' in command and '/dev/' in command:
                errors.append("Potential device file manipulation")
        
        return len(errors) == 0, errors
    
    def should_require_confirmation(self, preview: CommandPreview) -> bool:
        """Determine if confirmation should be required"""
        if not self.require_confirmation:
            return False
        
        return (preview.requires_confirmation or 
                preview.risk_level in [SecurityLevel.HIGH, SecurityLevel.CRITICAL] or
                preview.operation_type == OperationType.DESTRUCTIVE)
    
    def create_backup_if_needed(self, command: str, preview: CommandPreview) -> List[str]:
        """Create backups for files that will be affected"""
        backup_files = []
        
        if preview.operation_type in [OperationType.WRITE, OperationType.DESTRUCTIVE]:
            for file_path in preview.affected_files:
                if file_path and os.path.exists(file_path):
                    backup_path = self.rollback_manager.create_backup(Path(file_path))
                    if backup_path:
                        backup_files.append(str(backup_path))
        
        return backup_files
    
    def register_rollback_if_available(self, command_id: str, command: str, 
                                     preview: CommandPreview, backup_files: List[str]):
        """Register rollback operation if available"""
        if preview.rollback_available and preview.rollback_command:
            self.rollback_manager.register_rollback(
                command_id=command_id,
                original_command=command,
                rollback_command=preview.rollback_command,
                backup_files=backup_files
            )
    
    async def execute_rollback(self, command_id: str) -> bool:
        """Execute a rollback operation"""
        return await self.rollback_manager.execute_rollback(command_id)
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate a comprehensive security report"""
        return {
            "blacklist_status": self.blacklist.get_blacklist(),
            "command_history_count": len(self._command_history),
            "rollback_operations_count": len(self.rollback_manager._rollback_operations),
            "security_settings": {
                "require_confirmation": self.require_confirmation,
                "safe_mode": self.safe_mode,
                "dry_run_default": self.dry_run_default,
                "max_command_length": settings.security.max_command_length
            }
        }


# Global security system instance
_security_system: Optional[SecuritySystem] = None


def get_security_system() -> SecuritySystem:
    """Get the global security system instance"""
    global _security_system
    if _security_system is None:
        _security_system = SecuritySystem()
    return _security_system


def initialize_security_system(config: Optional[Dict[str, Any]] = None) -> SecuritySystem:
    """Initialize the global security system"""
    global _security_system
    _security_system = SecuritySystem(config)
    return _security_system 