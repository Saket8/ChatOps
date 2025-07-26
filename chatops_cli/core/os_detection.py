"""
OS Detection and Command Mapping Module

Provides smart OS detection and command translation for cross-platform compatibility.
Windows, Linux, and macOS support with appropriate command mappings.
"""

import platform
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class OSInfo:
    """Operating system information"""
    name: str           # windows, linux, macos
    version: str        # OS version
    shell: str          # cmd, powershell, bash, zsh
    is_windows: bool
    is_linux: bool
    is_macos: bool


class OSDetection:
    """
    Smart OS detection and command mapping for cross-platform support.
    
    Automatically detects the operating system and provides appropriate
    command equivalents for common DevOps operations.
    """
    
    def __init__(self):
        self._os_info = self._detect_os()
        self._command_mappings = self._build_command_mappings()
    
    def _detect_os(self) -> OSInfo:
        """Detect current operating system and shell"""
        system = platform.system().lower()
        version = platform.version()
        
        # Determine OS type
        is_windows = system == "windows"
        is_linux = system == "linux" 
        is_macos = system == "darwin"
        
        # Determine likely shell
        if is_windows:
            # Windows: assume PowerShell (modern default)
            shell = "powershell"
            name = "windows"
        elif is_macos:
            # macOS: likely zsh (modern default) or bash
            shell = "zsh" 
            name = "macos"
        else:
            # Linux: likely bash
            shell = "bash"
            name = "linux"
        
        return OSInfo(
            name=name,
            version=version,
            shell=shell,
            is_windows=is_windows,
            is_linux=is_linux,
            is_macos=is_macos
        )
    
    def _build_command_mappings(self) -> Dict[str, Dict[str, str]]:
        """Build command mappings for different operating systems"""
        return {
            # Disk Usage Commands
            "disk_usage": {
                "windows": "Get-WmiObject -Class Win32_LogicalDisk | Select-Object DeviceID, @{Name='Size(GB)';Expression={[math]::Round($_.Size/1GB,2)}}, @{Name='FreeSpace(GB)';Expression={[math]::Round($_.FreeSpace/1GB,2)}}",
                "linux": "df -h",
                "macos": "df -h"
            },
            
            # Process Listing
            "list_processes": {
                "windows": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 ProcessName, CPU, WorkingSet",
                "linux": "ps aux --sort=-%cpu | head -10",
                "macos": "ps aux -r | head -10"
            },
            
            # Memory Usage
            "memory_usage": {
                "windows": "Get-WmiObject -Class Win32_ComputerSystem | Select-Object TotalPhysicalMemory; Get-WmiObject -Class Win32_OperatingSystem | Select-Object FreePhysicalMemory",
                "linux": "free -h",
                "macos": "vm_stat"
            },
            
            # Network Information
            "network_info": {
                "windows": "Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object Name, InterfaceDescription, LinkSpeed",
                "linux": "ip addr show",
                "macos": "ifconfig"
            },
            
            # File Finding (large files)
            "find_large_files": {
                "windows": "Get-ChildItem -Path C:\\ -Recurse -File | Where-Object {$_.Length -gt 100MB} | Sort-Object Length -Descending | Select-Object -First 10 FullName, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}}",
                "linux": "find / -type f -size +100M -exec ls -lh {} \\; 2>/dev/null | head -10",
                "macos": "find / -type f -size +100M -exec ls -lh {} \\; 2>/dev/null | head -10"
            },
            
            # System Information
            "system_info": {
                "windows": "Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, TotalPhysicalMemory, CsProcessors",
                "linux": "uname -a && cat /proc/cpuinfo | grep 'model name' | head -1 && cat /proc/meminfo | grep MemTotal",
                "macos": "system_profiler SPSoftwareDataType SPHardwareDataType"
            },
            
            # Directory Listing
            "list_directory": {
                "windows": "Get-ChildItem -Force | Format-Table -AutoSize",
                "linux": "ls -la",
                "macos": "ls -la"
            },
            
            # Current Directory
            "current_directory": {
                "windows": "Get-Location",
                "linux": "pwd",
                "macos": "pwd"
            },
            
            # Service Status
            "service_status": {
                "windows": "Get-Service | Where-Object Status -eq 'Running' | Select-Object -First 10 Name, Status",
                "linux": "systemctl --type=service --state=running | head -10",
                "macos": "launchctl list | head -10"
            }
        }
    
    def get_os_info(self) -> OSInfo:
        """Get current OS information"""
        return self._os_info
    
    def map_command(self, command_type: str) -> str:
        """
        Get OS-appropriate command for a given command type.
        
        Args:
            command_type: Type of command (e.g., 'disk_usage', 'list_processes')
            
        Returns:
            OS-appropriate command string
        """
        if command_type not in self._command_mappings:
            return f"# Unknown command type: {command_type}"
        
        return self._command_mappings[command_type].get(
            self._os_info.name, 
            f"# No mapping for {command_type} on {self._os_info.name}"
        )
    
    def smart_translate(self, intent: str) -> str:
        """
        Smart translation of natural language intent to OS-specific command.
        
        Args:
            intent: Natural language description of desired action
            
        Returns:
            OS-appropriate command
        """
        intent_lower = intent.lower()
        
        # Disk usage patterns
        if any(phrase in intent_lower for phrase in ["disk usage", "disk space", "free space", "storage"]):
            return self.map_command("disk_usage")
        
        # Process patterns  
        elif any(phrase in intent_lower for phrase in ["processes", "running", "tasks", "ps aux"]):
            return self.map_command("list_processes")
        
        # Memory patterns
        elif any(phrase in intent_lower for phrase in ["memory", "ram", "free memory"]):
            return self.map_command("memory_usage")
        
        # Network patterns
        elif any(phrase in intent_lower for phrase in ["network", "interface", "ip", "adapter"]):
            return self.map_command("network_info")
        
        # Large files patterns
        elif any(phrase in intent_lower for phrase in ["large files", "big files", "find files", "100mb"]):
            return self.map_command("find_large_files")
        
        # System info patterns
        elif any(phrase in intent_lower for phrase in ["system info", "system information", "computer info"]):
            return self.map_command("system_info")
        
        # Directory listing patterns
        elif any(phrase in intent_lower for phrase in ["list files", "show files", "directory", "ls", "dir"]):
            return self.map_command("list_directory")
        
        # Current directory patterns
        elif any(phrase in intent_lower for phrase in ["current directory", "where am i", "pwd"]):
            return self.map_command("current_directory")
        
        # Service patterns
        elif any(phrase in intent_lower for phrase in ["services", "running services", "service status"]):
            return self.map_command("service_status")
        
        else:
            # Fallback: no specific mapping found
            return f"# No OS-specific mapping found for: {intent}"
    
    def get_shell_prefix(self) -> str:
        """Get appropriate shell prefix for the current OS"""
        if self._os_info.is_windows:
            return "PS> "
        else:
            return "$ "
    
    def format_command_output(self, command: str, description: str = "") -> str:
        """Format command with OS-appropriate shell prompt"""
        prefix = self.get_shell_prefix()
        
        if description:
            return f"# {description}\n{prefix}{command}"
        else:
            return f"{prefix}{command}"


# Global instance for easy access
os_detection = OSDetection() 