"""
Test utilities for ChatOps CLI testing.

Provides helper functions, test data generators, and common testing patterns.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock

import pytest


class TestDataGenerator:
    """Generate test data for various components."""
    
    @staticmethod
    def create_mock_devops_command(
        command: str = "ls -la",
        description: str = "List directory contents",
        risk_level: str = "SAFE"
    ) -> MagicMock:
        """Create a mock DevOpsCommand for testing."""
        mock_command = MagicMock()
        mock_command.command = command
        mock_command.description = description
        mock_command.risk_level = MagicMock(value=risk_level)
        mock_command.command_type = MagicMock(value="SYSTEM")
        return mock_command
    
    @staticmethod
    def create_mock_execution_result(
        command: str = "ls -la",
        status: str = "completed",
        return_code: int = 0,
        stdout: str = "file1.txt\nfile2.txt",
        stderr: str = "",
        execution_time: float = 0.15,
        error_message: Optional[str] = None
    ) -> MagicMock:
        """Create a mock ExecutionResult for testing."""
        mock_result = MagicMock()
        mock_result.command = command
        mock_result.status = MagicMock(value=status)
        mock_result.return_code = return_code
        mock_result.stdout = stdout
        mock_result.stderr = stderr
        mock_result.execution_time = execution_time
        mock_result.error_message = error_message
        mock_result.start_time = MagicMock()
        mock_result.end_time = MagicMock()
        return mock_result
    
    @staticmethod
    def create_mock_llm_response(
        content: str = "ls -la",
        success: bool = True,
        model: str = "llama3-8b-8192",
        tokens_used: int = 150
    ) -> MagicMock:
        """Create a mock LLM response for testing."""
        mock_response = MagicMock()
        mock_response.content = content
        mock_response.success = success
        mock_response.model = model
        mock_response.tokens_used = tokens_used
        return mock_response
    
    @staticmethod
    def create_test_config() -> Dict[str, Any]:
        """Create a test configuration dictionary."""
        return {
            "debug_mode": True,
            "verbose_mode": True,
            "logging": {
                "level": "DEBUG",
                "file_logging": False,
                "log_directory": ".test_logs"
            },
            "security": {
                "require_confirmation": False,
                "safe_mode": True,
                "command_validation": True,
                "dry_run_default": True
            },
            "groq": {
                "api_key": "test_groq_api_key",
                "model": "llama3-8b-8192",
                "max_tokens": 1000,
                "temperature": 0.1
            },
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "mistral:7b",
                "max_tokens": 1000,
                "temperature": 0.1
            }
        }
    
    @staticmethod
    def create_test_log_entries() -> List[Dict[str, Any]]:
        """Create test log entries."""
        return [
            {
                "timestamp": "2025-01-20T10:00:00",
                "level": "INFO",
                "message": "Command executed: ls -la",
                "command": "ls -la",
                "risk_level": "SAFE",
                "return_code": 0,
                "execution_time": 0.15,
                "user_id": "test_user"
            },
            {
                "timestamp": "2025-01-20T10:01:00",
                "level": "WARNING",
                "message": "Security event: Command validation failed",
                "command": "rm -rf /",
                "risk_level": "CRITICAL",
                "return_code": -1,
                "execution_time": 0.0,
                "user_id": "test_user"
            },
            {
                "timestamp": "2025-01-20T10:02:00",
                "level": "INFO",
                "message": "Plugin loaded: docker_plugin",
                "plugin_name": "docker_plugin",
                "success": True,
                "user_id": "test_user"
            }
        ]
    
    @staticmethod
    def create_test_commands() -> List[tuple]:
        """Create test commands for testing."""
        return [
            ("ls -la", "List directory contents", "SAFE"),
            ("cat file.txt", "Display file contents", "SAFE"),
            ("cp source.txt dest.txt", "Copy file", "MEDIUM"),
            ("rm file.txt", "Remove file", "HIGH"),
            ("systemctl restart nginx", "Restart service", "MEDIUM"),
            ("docker ps", "List containers", "SAFE"),
            ("kubectl get pods", "List pods", "SAFE"),
        ]
    
    @staticmethod
    def create_dangerous_commands() -> List[tuple]:
        """Create dangerous commands for security testing."""
        return [
            ("rm -rf /", "Remove root directory", "CRITICAL"),
            ("format c:", "Format system drive", "CRITICAL"),
            ("dd if=/dev/zero of=/dev/sda", "Zero out disk", "CRITICAL"),
            ("mkfs.ext4 /dev/sda", "Format filesystem", "CRITICAL"),
            ("userdel -r username", "Delete user with home", "HIGH"),
            ("iptables -F", "Flush firewall rules", "HIGH"),
        ]


class TestFileUtils:
    """File utilities for testing."""
    
    @staticmethod
    def create_temp_file(content: str = "Test content", suffix: str = ".txt") -> Path:
        """Create a temporary file with content."""
        temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        temp_file.write(content.encode('utf-8'))
        temp_file.close()
        return Path(temp_file.name)
    
    @staticmethod
    def create_temp_config_file(config_data: Dict[str, Any], format: str = "json") -> Path:
        """Create a temporary configuration file."""
        temp_file = tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False)
        
        if format == "json":
            temp_file.write(json.dumps(config_data, indent=2).encode('utf-8'))
        elif format == "yaml":
            import yaml
            temp_file.write(yaml.dump(config_data).encode('utf-8'))
        
        temp_file.close()
        return Path(temp_file.name)
    
    @staticmethod
    def create_temp_log_file(log_entries: List[Dict[str, Any]]) -> Path:
        """Create a temporary log file with entries."""
        temp_file = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
        
        with open(temp_file.name, 'w') as f:
            for entry in log_entries:
                f.write(json.dumps(entry) + '\n')
        
        temp_file.close()
        return Path(temp_file.name)
    
    @staticmethod
    def cleanup_temp_files(*files: Path):
        """Clean up temporary files."""
        for file_path in files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors


class TestAssertionUtils:
    """Assertion utilities for testing."""
    
    @staticmethod
    def assert_execution_success(result):
        """Assert that execution was successful."""
        assert result.status.value == "completed"
        assert result.return_code == 0
        assert result.error_message is None
    
    @staticmethod
    def assert_execution_failure(result, expected_error: Optional[str] = None):
        """Assert that execution failed."""
        assert result.status.value == "failed"
        assert result.return_code != 0
        if expected_error:
            assert expected_error in result.error_message or expected_error in result.stderr
    
    @staticmethod
    def assert_command_validation_failure(result):
        """Assert that command validation failed."""
        assert result.status.value == "failed"
        assert "validation" in result.error_message.lower() or "validation" in result.stderr.lower()
    
    @staticmethod
    def assert_log_entry_structure(log_entry: Dict[str, Any]):
        """Assert that a log entry has the correct structure."""
        required_fields = ["timestamp", "level", "message"]
        for field in required_fields:
            assert field in log_entry, f"Missing required field: {field}"
        
        assert isinstance(log_entry["timestamp"], str)
        assert isinstance(log_entry["level"], str)
        assert isinstance(log_entry["message"], str)
    
    @staticmethod
    def assert_security_preview_structure(preview):
        """Assert that a security preview has the correct structure."""
        required_attributes = [
            "command", "description", "risk_level", "operation_type",
            "estimated_impact", "requires_confirmation", "rollback_available"
        ]
        
        for attr in required_attributes:
            assert hasattr(preview, attr), f"Missing required attribute: {attr}"


class TestMockUtils:
    """Mock utilities for testing."""
    
    @staticmethod
    def create_mock_async_function(return_value: Any = None, side_effect: Any = None):
        """Create a mock async function."""
        mock_func = MagicMock()
        if side_effect:
            mock_func.side_effect = side_effect
        else:
            mock_func.return_value = return_value
        return mock_func
    
    @staticmethod
    def create_mock_context_manager(enter_value: Any = None, exit_value: Any = None):
        """Create a mock context manager."""
        mock_cm = MagicMock()
        mock_cm.__enter__.return_value = enter_value
        mock_cm.__exit__.return_value = exit_value
        return mock_cm
    
    @staticmethod
    def create_mock_subprocess_result(
        returncode: int = 0,
        stdout: str = "",
        stderr: str = ""
    ) -> MagicMock:
        """Create a mock subprocess result."""
        mock_result = MagicMock()
        mock_result.returncode = returncode
        mock_result.stdout = stdout.encode('utf-8') if isinstance(stdout, str) else stdout
        mock_result.stderr = stderr.encode('utf-8') if isinstance(stderr, str) else stderr
        return mock_result


# Pytest fixtures that can be used across test modules
@pytest.fixture
def test_data_generator():
    """Provide test data generator."""
    return TestDataGenerator


@pytest.fixture
def test_file_utils():
    """Provide test file utilities."""
    return TestFileUtils


@pytest.fixture
def test_assertion_utils():
    """Provide test assertion utilities."""
    return TestAssertionUtils


@pytest.fixture
def test_mock_utils():
    """Provide test mock utilities."""
    return TestMockUtils


@pytest.fixture
def sample_config():
    """Provide sample configuration for testing."""
    return TestDataGenerator.create_test_config()


@pytest.fixture
def sample_log_entries():
    """Provide sample log entries for testing."""
    return TestDataGenerator.create_test_log_entries()


@pytest.fixture
def sample_commands():
    """Provide sample commands for testing."""
    return TestDataGenerator.create_test_commands()


@pytest.fixture
def dangerous_commands():
    """Provide dangerous commands for security testing."""
    return TestDataGenerator.create_dangerous_commands() 