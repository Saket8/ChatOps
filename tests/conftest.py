"""
Pytest configuration and fixtures for ChatOps CLI testing.

This module provides shared fixtures, test utilities, and mocking setup
for unit tests, integration tests, and command execution testing.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from click.testing import CliRunner

from chatops_cli.core.command_executor import ExecutionContext, ExecutionResult, ExecutionStatus
from chatops_cli.core.logging_system import LoggingSystem
from chatops_cli.core.security_system import SecuritySystem
from chatops_cli.settings import Settings


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security-related"
    )
    config.addinivalue_line(
        "markers", "logging: mark test as logging-related"
    )


# Test utilities
class MockDevOpsCommand:
    """Mock DevOpsCommand for testing."""
    
    def __init__(self, command: str, description: str = "", risk_level: str = "SAFE"):
        self.command = command
        self.description = description
        self.risk_level = MockRiskLevel(risk_level)
        self.command_type = MockCommandType("SYSTEM")


class MockRiskLevel:
    """Mock RiskLevel enum for testing."""
    
    def __init__(self, value: str):
        self.value = value


class MockCommandType:
    """Mock CommandType enum for testing."""
    
    def __init__(self, value: str):
        self.value = value


class MockOSInfo:
    """Mock OS information for testing."""
    
    def __init__(self, name: str = "Windows", is_windows: bool = True):
        self.name = name
        self.is_windows = is_windows
        self.shell = "powershell" if is_windows else "bash"
        self.version = "10" if is_windows else "Ubuntu 22.04"


# Fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_file(temp_dir):
    """Create a temporary file for testing."""
    temp_file = temp_dir / "test_file.txt"
    temp_file.write_text("Test content")
    return temp_file


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    return Settings(
        debug_mode=True,
        verbose_mode=True,
        logging=Settings.LoggingConfig(
            level="DEBUG",
            file_logging=False,
            log_directory=".test_logs"
        ),
        security=Settings.SecurityConfig(
            require_confirmation=False,
            safe_mode=True,
            command_validation=True,
            dry_run_default=True,
            blocked_commands=[]
        )
    )


@pytest.fixture
def mock_os_info():
    """Mock OS detection for testing."""
    return MockOSInfo()


@pytest.fixture
def mock_groq_response():
    """Mock Groq API response for testing."""
    mock_response = MagicMock()
    mock_response.content = "ls -la"
    mock_response.success = True
    mock_response.model = "llama3-8b-8192"
    mock_response.tokens_used = 150
    return mock_response


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response for testing."""
    mock_response = MagicMock()
    mock_response.content = "ls -la"
    mock_response.success = True
    mock_response.model = "mistral:7b"
    return mock_response


@pytest.fixture
def cli_runner():
    """Click CLI runner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_execution_context(temp_dir):
    """Mock execution context for testing."""
    return ExecutionContext(
        working_directory=temp_dir,
        environment_vars={"TEST": "true"},
        timeout_seconds=10,
        dry_run=True,
        interactive=False,
        log_execution=False
    )


@pytest.fixture
def mock_execution_result():
    """Mock execution result for testing."""
    return ExecutionResult(
        command="ls -la",
        status=ExecutionStatus.COMPLETED,
        return_code=0,
        stdout="total 8\ndrwxr-xr-x  2 user user 4096 Jan 20 10:00 .\ndrwxr-xr-x 10 user user 4096 Jan 20 10:00 ..",
        stderr="",
        execution_time=0.15,
        start_time=MagicMock(),
        end_time=MagicMock()
    )


@pytest.fixture
def mock_failed_execution_result():
    """Mock failed execution result for testing."""
    return ExecutionResult(
        command="invalid_command",
        status=ExecutionStatus.FAILED,
        return_code=127,
        stdout="",
        stderr="command not found: invalid_command",
        execution_time=0.05,
        start_time=MagicMock(),
        end_time=MagicMock(),
        error_message="Command not found"
    )


@pytest.fixture
def mock_devops_command():
    """Mock DevOpsCommand for testing."""
    return MockDevOpsCommand(
        command="ls -la",
        description="List directory contents",
        risk_level="SAFE"
    )


@pytest.fixture
def mock_dangerous_command():
    """Mock dangerous DevOpsCommand for testing."""
    return MockDevOpsCommand(
        command="rm -rf /",
        description="Dangerous system command",
        risk_level="CRITICAL"
    )


# Async fixtures
@pytest_asyncio.fixture
async def mock_logging_system():
    """Mock logging system for testing."""
    with patch('chatops_cli.core.logging_system.LoggingSystem') as mock:
        mock_instance = mock.return_value
        mock_instance.log_command_execution = AsyncMock()
        mock_instance.log_security_event = AsyncMock()
        mock_instance.log_plugin_event = AsyncMock()
        mock_instance.log_llm_event = AsyncMock()
        yield mock_instance


@pytest_asyncio.fixture
async def mock_security_system():
    """Mock security system for testing."""
    with patch('chatops_cli.core.security_system.SecuritySystem') as mock:
        mock_instance = mock.return_value
        mock_instance.analyze_command = MagicMock()
        mock_instance.validate_command = MagicMock(return_value=(True, []))
        mock_instance.should_require_confirmation = MagicMock(return_value=False)
        mock_instance.create_backup_if_needed = MagicMock(return_value=[])
        mock_instance.register_rollback_if_available = MagicMock()
        yield mock_instance


@pytest_asyncio.fixture
async def mock_groq_client():
    """Mock Groq client for testing."""
    with patch('chatops_cli.core.groq_client.GroqClient') as mock:
        mock_instance = mock.return_value
        mock_instance.connect = AsyncMock(return_value=True)
        mock_instance.generate_response = AsyncMock()
        mock_instance.is_connected = MagicMock(return_value=True)
        mock_instance.get_model_info = MagicMock(return_value={
            "provider": "groq",
            "model": "llama3-8b-8192",
            "connected": True
        })
        yield mock_instance


@pytest_asyncio.fixture
async def mock_ollama_client():
    """Mock Ollama client for testing."""
    with patch('chatops_cli.core.ollama_client.OllamaClient') as mock:
        mock_instance = mock.return_value
        mock_instance.connect = AsyncMock(return_value=True)
        mock_instance.generate_response = AsyncMock()
        mock_instance.is_connected = MagicMock(return_value=True)
        mock_instance.get_model_info = MagicMock(return_value={
            "provider": "ollama",
            "model": "mistral:7b",
            "connected": True
        })
        yield mock_instance


@pytest_asyncio.fixture
async def mock_plugin_manager():
    """Mock plugin manager for testing."""
    with patch('chatops_cli.plugins.manager.PluginManager') as mock:
        mock_instance = mock.return_value
        mock_instance.initialize = AsyncMock(return_value=True)
        mock_instance.discover_plugins = AsyncMock(return_value=2)
        mock_instance.get_all_plugins = MagicMock(return_value={})
        mock_instance.find_handler = AsyncMock(return_value=None)
        yield mock_instance


@pytest_asyncio.fixture
async def mock_command_executor():
    """Mock command executor for testing."""
    with patch('chatops_cli.core.command_executor.CommandExecutor') as mock:
        mock_instance = mock.return_value
        mock_instance.execute_command = AsyncMock()
        mock_instance.get_execution_history = MagicMock(return_value=[])
        mock_instance.get_running_commands = MagicMock(return_value=[])
        yield mock_instance


# Test data fixtures
@pytest.fixture
def sample_commands():
    """Sample commands for testing."""
    return [
        ("ls -la", "List directory contents", "SAFE"),
        ("cat file.txt", "Display file contents", "SAFE"),
        ("cp source.txt dest.txt", "Copy file", "MEDIUM"),
        ("rm file.txt", "Remove file", "HIGH"),
        ("systemctl restart nginx", "Restart service", "MEDIUM"),
        ("docker ps", "List containers", "SAFE"),
        ("kubectl get pods", "List pods", "SAFE"),
    ]


@pytest.fixture
def dangerous_commands():
    """Dangerous commands for security testing."""
    return [
        ("rm -rf /", "Remove root directory", "CRITICAL"),
        ("format c:", "Format system drive", "CRITICAL"),
        ("dd if=/dev/zero of=/dev/sda", "Zero out disk", "CRITICAL"),
        ("mkfs.ext4 /dev/sda", "Format filesystem", "CRITICAL"),
        ("userdel -r username", "Delete user with home", "HIGH"),
        ("iptables -F", "Flush firewall rules", "HIGH"),
    ]


@pytest.fixture
def test_log_data():
    """Sample log data for testing."""
    return [
        {
            "timestamp": "2025-01-20T10:00:00",
            "level": "INFO",
            "message": "Command executed: ls -la",
            "command": "ls -la",
            "risk_level": "SAFE",
            "return_code": 0,
            "execution_time": 0.15
        },
        {
            "timestamp": "2025-01-20T10:01:00",
            "level": "WARNING",
            "message": "Security event: Command validation failed",
            "command": "rm -rf /",
            "risk_level": "CRITICAL",
            "return_code": -1,
            "execution_time": 0.0
        }
    ]


# Environment fixtures
@pytest.fixture(autouse=True)
def setup_test_environment():
    """Setup test environment variables."""
    # Set test environment variables
    os.environ["CHATOPS_DEBUG_MODE"] = "true"
    os.environ["CHATOPS_VERBOSE_MODE"] = "true"
    os.environ["CHATOPS_LOGGING_LEVEL"] = "DEBUG"
    os.environ["CHATOPS_LOGGING_FILE_LOGGING"] = "false"
    os.environ["CHATOPS_SECURITY_SAFE_MODE"] = "true"
    os.environ["CHATOPS_SECURITY_DRY_RUN_DEFAULT"] = "true"
    os.environ["CHATOPS_SECURITY_BLOCKED_COMMANDS"] = ""
    
    # Mock API keys for testing
    os.environ["GROQ_API_KEY"] = "test_groq_api_key"
    os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
    
    yield
    
    # Cleanup
    for key in ["CHATOPS_DEBUG_MODE", "CHATOPS_VERBOSE_MODE", "CHATOPS_LOGGING_LEVEL",
                "CHATOPS_LOGGING_FILE_LOGGING", "CHATOPS_SECURITY_SAFE_MODE",
                "CHATOPS_SECURITY_DRY_RUN_DEFAULT", "GROQ_API_KEY", "OLLAMA_BASE_URL"]:
        os.environ.pop(key, None)


# Test utilities
class TestUtils:
    """Utility functions for testing."""
    
    @staticmethod
    def create_temp_config(temp_dir: Path, config_data: Dict[str, Any]) -> Path:
        """Create a temporary configuration file."""
        config_file = temp_dir / "test_config.json"
        config_file.write_text(json.dumps(config_data))
        return config_file
    
    @staticmethod
    def create_temp_log_file(temp_dir: Path, log_entries: List[Dict[str, Any]]) -> Path:
        """Create a temporary log file with test data."""
        log_file = temp_dir / "test.log"
        with open(log_file, 'w') as f:
            for entry in log_entries:
                f.write(json.dumps(entry) + '\n')
        return log_file
    
    @staticmethod
    def assert_execution_success(result: ExecutionResult):
        """Assert that execution was successful."""
        assert result.status == ExecutionStatus.COMPLETED
        assert result.return_code == 0
        assert result.error_message is None
    
    @staticmethod
    def assert_execution_failure(result: ExecutionResult, expected_error: Optional[str] = None):
        """Assert that execution failed."""
        assert result.status == ExecutionStatus.FAILED
        assert result.return_code != 0
        if expected_error:
            assert expected_error in result.error_message or expected_error in result.stderr
    
    @staticmethod
    def assert_command_validation_failure(result: ExecutionResult):
        """Assert that command validation failed."""
        assert result.status == ExecutionStatus.FAILED
        assert "validation" in result.error_message.lower() or "validation" in result.stderr.lower()


# Pytest configuration
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add markers based on test file names
        if "test_security" in item.nodeid:
            item.add_marker(pytest.mark.security)
        if "test_logging" in item.nodeid:
            item.add_marker(pytest.mark.logging)
        if "test_integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "test_unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker for tests that might be slow
        if any(keyword in item.nodeid for keyword in ["network", "api", "integration"]):
            item.add_marker(pytest.mark.slow) 