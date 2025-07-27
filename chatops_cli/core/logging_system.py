"""
Comprehensive Logging and Audit System for ChatOps CLI

This module provides structured logging with different levels, audit trails for executed commands,
security event logging, and configurable output formats with log rotation and retention policies.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from contextlib import contextmanager

from ..settings import settings


class LogLevel(Enum):
    """Log levels for different types of events"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    AUDIT = "AUDIT"
    SECURITY = "SECURITY"
    
    def to_logging_level(self) -> int:
        """Convert to standard logging level"""
        mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
            "AUDIT": logging.INFO,  # Map AUDIT to INFO
            "SECURITY": logging.WARNING,  # Map SECURITY to WARNING
        }
        return mapping.get(self.value, logging.INFO)


class EventType(Enum):
    """Types of events that can be logged"""
    COMMAND_EXECUTION = "COMMAND_EXECUTION"
    COMMAND_VALIDATION = "COMMAND_VALIDATION"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    SECURITY_EVENT = "SECURITY_EVENT"
    PLUGIN_LOAD = "PLUGIN_LOAD"
    PLUGIN_ERROR = "PLUGIN_ERROR"
    LLM_REQUEST = "LLM_REQUEST"
    LLM_RESPONSE = "LLM_RESPONSE"
    CONFIGURATION_CHANGE = "CONFIGURATION_CHANGE"
    USER_ACTION = "USER_ACTION"
    SYSTEM_EVENT = "SYSTEM_EVENT"


@dataclass
class AuditEvent:
    """Structured audit event data"""
    timestamp: datetime
    event_type: EventType
    level: LogLevel
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    command: Optional[str] = None
    risk_level: Optional[str] = None
    return_code: Optional[int] = None
    execution_time: Optional[float] = None
    working_directory: Optional[str] = None
    ip_address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['event_type'] = self.event_type.value
        data['level'] = self.level.value
        return data


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def __init__(self, include_metadata: bool = True):
        super().__init__()
        self.include_metadata = include_metadata
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present, handling MagicMock objects
        if hasattr(record, 'event_type'):
            log_entry['event_type'] = str(record.event_type)
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = str(record.user_id)
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = str(record.session_id)
        if hasattr(record, 'command'):
            log_entry['command'] = str(record.command)
        if hasattr(record, 'risk_level'):
            log_entry['risk_level'] = str(record.risk_level)
        if hasattr(record, 'metadata'):
            # Handle metadata carefully to avoid MagicMock serialization issues
            try:
                if hasattr(record.metadata, '__dict__'):
                    log_entry['metadata'] = str(record.metadata)
                else:
                    log_entry['metadata'] = record.metadata
            except:
                log_entry['metadata'] = str(record.metadata)
        
        # Ensure all values are JSON serializable
        def make_serializable(obj):
            if hasattr(obj, '__class__') and 'MagicMock' in str(obj.__class__):
                return str(obj)
            return obj
        
        # Convert all values to be JSON serializable
        for key, value in log_entry.items():
            log_entry[key] = make_serializable(value)
        
        return json.dumps(log_entry, ensure_ascii=False)


class AuditLogger:
    """Dedicated audit logger for security and compliance events"""
    
    def __init__(self, log_directory: Path):
        self.log_directory = log_directory
        self.audit_file = log_directory / "audit.log"
        self.security_file = log_directory / "security.log"
        
        # Create audit logger
        self.audit_logger = logging.getLogger("chatops.audit")
        self.audit_logger.setLevel(logging.INFO)
        
        # Create security logger
        self.security_logger = logging.getLogger("chatops.security")
        self.security_logger.setLevel(logging.INFO)
        
        # Setup handlers
        self._setup_audit_handlers()
        self._setup_security_handlers()
    
    def _setup_audit_handlers(self):
        """Setup audit log handlers with rotation"""
        audit_handler = logging.handlers.RotatingFileHandler(
            self.audit_file,
            maxBytes=settings.logging.max_log_size,
            backupCount=5,
            encoding='utf-8'
        )
        audit_handler.setFormatter(StructuredFormatter())
        self.audit_logger.addHandler(audit_handler)
    
    def _setup_security_handlers(self):
        """Setup security log handlers with rotation"""
        security_handler = logging.handlers.RotatingFileHandler(
            self.security_file,
            maxBytes=settings.logging.max_log_size,
            backupCount=5,
            encoding='utf-8'
        )
        security_handler.setFormatter(StructuredFormatter())
        self.security_logger.addHandler(security_handler)
    
    def log_audit_event(self, event: AuditEvent):
        """Log an audit event"""
        extra = {
            'event_type': event.event_type.value,
            'user_id': event.user_id,
            'session_id': event.session_id,
            'command': event.command,
            'risk_level': event.risk_level,
            'metadata': event.metadata
        }
        
        if event.level in [LogLevel.SECURITY, LogLevel.CRITICAL]:
            self.security_logger.log(
                event.level.to_logging_level(),
                event.message,
                extra=extra
            )
        else:
            self.audit_logger.log(
                event.level.to_logging_level(),
                event.message,
                extra=extra
            )
    
    def cleanup(self):
        """Clean up audit logger handlers"""
        # Close audit logger handlers
        for handler in self.audit_logger.handlers[:]:
            handler.close()
            self.audit_logger.removeHandler(handler)
        
        # Close security logger handlers
        for handler in self.security_logger.handlers[:]:
            handler.close()
            self.security_logger.removeHandler(handler)


class LoggingSystem:
    """
    Comprehensive logging system for ChatOps CLI
    
    Provides structured logging, audit trails, security event logging,
    and configurable output formats with log rotation and retention policies.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Handle both dict config and direct Path object for backward compatibility
        if isinstance(config, (str, Path)):
            self.log_directory = Path(config)
        elif config and 'log_directory' in config:
            self.log_directory = Path(config['log_directory'])
        else:
            self.log_directory = Path(settings.logging.log_directory)
        
        self.log_directory.mkdir(exist_ok=True)
        
        # Initialize audit logger
        self.audit_logger = AuditLogger(self.log_directory)
        
        # Setup main application logging
        self._setup_application_logging()
        
        # Create main logger reference
        self.main_logger = logging.getLogger("chatops.main")
        
        # Create security logger reference
        self.security_logger = logging.getLogger("chatops.security")
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Session tracking
        self._current_session_id: Optional[str] = None
        self._session_start_time: Optional[datetime] = None
        
        # Command history for audit trail
        self._command_history: List[AuditEvent] = []
        self._max_history_size = 1000
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Logging system initialized")
    
    @property
    def current_session_id(self):
        """Get the current session ID"""
        return self._current_session_id
    
    def initialize_logging(self):
        """Initialize the logging system (alias for compatibility)"""
        # Logging is already initialized in __init__, this is for compatibility
        self.logger.info("Logging system initialization called")
    
    def _setup_application_logging(self):
        """Setup main application logging with rotation and formatting"""
        # Main application log file
        app_log_file = self.log_directory / "chatops.log"
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=settings.logging.max_log_size,
            backupCount=5,
            encoding='utf-8'
        )
        
        # Set formatter
        if settings.logging.include_timestamps:
            formatter = StructuredFormatter()
        else:
            formatter = logging.Formatter(
                '%(levelname)s - %(name)s - %(message)s'
            )
        
        file_handler.setFormatter(formatter)
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.logging.level))
        root_logger.addHandler(file_handler)
        
        # Console handler for development
        if settings.debug_mode:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
    
    def start_session(self, session_id: Optional[str] = None, user_id: Optional[str] = None):
        """Start a new logging session"""
        with self._lock:
            if session_id is None:
                session_id = f"session_{int(datetime.now().timestamp())}"
            
            self._current_session_id = session_id
            self._session_start_time = datetime.now()
            
            event = AuditEvent(
                timestamp=datetime.now(),
                event_type=EventType.SYSTEM_EVENT,
                level=LogLevel.INFO,
                message=f"Session started: {session_id}",
                user_id=user_id,
                session_id=session_id,
                metadata={'session_start_time': self._session_start_time.isoformat()}
            )
            
            self.audit_logger.log_audit_event(event)
            self.logger.info(f"Logging session started: {session_id}")
            
            return session_id
    
    def end_session(self):
        """End the current logging session"""
        if self._current_session_id and self._session_start_time:
            session_duration = datetime.now() - self._session_start_time
            
            event = AuditEvent(
                timestamp=datetime.now(),
                event_type=EventType.SYSTEM_EVENT,
                level=LogLevel.INFO,
                message=f"Session ended: {self._current_session_id}",
                session_id=self._current_session_id,
                metadata={
                    'session_duration_seconds': session_duration.total_seconds(),
                    'commands_executed': len(self._command_history)
                }
            )
            
            self.audit_logger.log_audit_event(event)
            self.logger.info(f"Logging session ended: {self._current_session_id}")
            
            self._current_session_id = None
            self._session_start_time = None
    
    async def log_command_execution(
        self,
        command: str,
        return_code: int,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        execution_time: float = 0.0,
        risk_level: str = "UNKNOWN",
        user_id: Optional[str] = None,
        description: Optional[str] = None,
        working_directory: Optional[str] = None,
        dry_run: bool = False,
        user_cancelled: bool = False,
        error_message: Optional[str] = None
    ):
        """Log command execution for audit trail"""
        event_type = EventType.COMMAND_EXECUTION
        level = LogLevel.INFO
        
        if error_message:
            level = LogLevel.ERROR
        elif user_cancelled:
            level = LogLevel.WARNING
        
        message = f"Command executed: {description}"
        if dry_run:
            message = f"[DRY RUN] {message}"
        if user_cancelled:
            message = f"[CANCELLED] {message}"
        
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            level=level,
            message=message,
            user_id=user_id,
            session_id=self._current_session_id,
            command=command,
            risk_level=risk_level,
            return_code=return_code,
            execution_time=execution_time,
            working_directory=working_directory,
            metadata={
                'dry_run': dry_run,
                'user_cancelled': user_cancelled,
                'error_message': error_message,
                'stdout': stdout,
                'stderr': stderr
            }
        )
        
        with self._lock:
            self.audit_logger.log_audit_event(event)
            self._command_history.append(event)
            
            # Maintain history size
            if len(self._command_history) > self._max_history_size:
                self._command_history = self._command_history[-self._max_history_size:]
    
    async def log_security_event(
        self,
        event_type: Union[EventType, str],
        message: Optional[str] = None,
        command: Optional[str] = None,
        risk_level: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        details: Optional[str] = None,
        severity: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Log security-related events"""
        # Handle string event types
        if isinstance(event_type, str):
            # Try to find matching EventType enum
            try:
                event_type_enum = EventType(event_type)
            except ValueError:
                # For custom event types, we'll use SECURITY_EVENT but store the original string
                event_type_enum = EventType.SECURITY_EVENT
                if metadata is None:
                    metadata = {}
                metadata['original_event_type'] = event_type
        else:
            event_type_enum = event_type
        
        # Use details as message if message is not provided
        if message is None and details is not None:
            message = details
        
        # Use severity as risk_level if risk_level is not provided
        if risk_level is None and severity is not None:
            risk_level = severity
        
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=event_type_enum,
            level=LogLevel.SECURITY,
            message=message,
            user_id=user_id,
            session_id=self._current_session_id,
            command=command,
            risk_level=risk_level,
            metadata=metadata
        )
        
        self.audit_logger.log_audit_event(event)
        self.logger.warning(f"Security event: {message}")
    
    async def log_validation_failure(
        self,
        command: str,
        reason: str,
        risk_level: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Log command validation failures"""
        await self.log_security_event(
            EventType.COMMAND_VALIDATION,
            f"Command validation failed: {reason}",
            command=command,
            risk_level=risk_level,
            user_id=user_id,
            metadata={'validation_reason': reason}
        )
    
    async def log_plugin_event(
        self,
        plugin_name: str,
        event_type: EventType,
        message: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        plugin_version: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Log plugin-related events"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            level=level,
            message=f"Plugin {plugin_name}: {message}",
            session_id=self._current_session_id,
            metadata={
                'plugin_name': plugin_name,
                'success': success,
                'error_message': error_message
            }
        )
        
        self.audit_logger.log_audit_event(event)
    
    async def log_llm_event(
        self,
        event_type: EventType,
        provider: str,
        model: str,
        message: Optional[str] = None,
        success: bool = True,
        response_time: Optional[float] = None,
        token_count: Optional[int] = None,
        model_version: Optional[str] = None,
        prompt: Optional[str] = None,
        tokens_used: Optional[int] = None
    ):
        """Log LLM-related events"""
        level = LogLevel.INFO if success else LogLevel.ERROR
        if message is None:
            message = "LLM event"
        event = AuditEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            level=level,
            message=f"LLM {provider}/{model}: {message}",
            session_id=self._current_session_id,
            metadata={
                'provider': provider,
                'model': model,
                'success': success,
                'response_time': response_time,
                'token_count': token_count,
                'tokens_used': tokens_used
            }
        )
        self.audit_logger.log_audit_event(event)
    
    def get_command_history(
        self,
        limit: Optional[int] = None,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[AuditEvent]:
        """Get command execution history with optional filtering"""
        with self._lock:
            history = self._command_history.copy()
        
        # Apply filters
        if session_id:
            history = [e for e in history if e.session_id == session_id]
        
        if start_time:
            history = [e for e in history if e.timestamp >= start_time]
        
        if end_time:
            history = [e for e in history if e.timestamp <= end_time]
        
        # Apply limit
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_audit_trail(
        self,
        event_types: Optional[List[EventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        level: Optional[LogLevel] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get comprehensive audit trail from log files"""
        audit_events = []
        
        # Read from audit log file
        audit_file = self.log_directory / "audit.log"
        if audit_file.exists():
            with open(audit_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        event_time = datetime.fromisoformat(data['timestamp'])
                        
                        # Apply filters
                        if start_time and event_time < start_time:
                            continue
                        if end_time and event_time > end_time:
                            continue
                        if event_types and data.get('event_type') not in [et.value for et in event_types]:
                            continue
                        if level and data.get('level') != level.value:
                            continue
                        
                        audit_events.append(data)
                    except json.JSONDecodeError:
                        continue
        
        # Apply limit if specified
        if limit:
            audit_events = audit_events[-limit:]
        
        return audit_events
    
    def cleanup_old_logs(self, retention_days: Optional[int] = None, days: Optional[int] = None):
        """Clean up old log files based on retention policy"""
        retention_days = retention_days or days or settings.logging.log_retention_days
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        log_files = [
            self.log_directory / "chatops.log",
            self.log_directory / "audit.log",
            self.log_directory / "security.log"
        ]
        
        cleaned_count = 0
        for log_file in log_files:
            if log_file.exists():
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_time < cutoff_date:
                    try:
                        log_file.unlink()
                        cleaned_count += 1
                        self.logger.info(f"Cleaned up old log file: {log_file}")
                    except Exception as e:
                        self.logger.error(f"Failed to clean up {log_file}: {e}")
        
        return cleaned_count
    
    def cleanup(self):
        """Clean up logging system and close handlers"""
        # Close all handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            handler.close()
            root_logger.removeHandler(handler)
        
        # Close audit logger handlers
        if hasattr(self, 'audit_logger'):
            self.audit_logger.cleanup()
    
    @contextmanager
    def log_context(self, context_name: str, metadata: Optional[Dict[str, Any]] = None):
        """Context manager for logging operations with automatic start/end events"""
        start_time = datetime.now()
        context_id = f"{context_name}_{int(start_time.timestamp())}"
        
        # Log start
        start_event = AuditEvent(
            timestamp=start_time,
            event_type=EventType.SYSTEM_EVENT,
            level=LogLevel.INFO,
            message=f"Context started: {context_name}",
            session_id=self._current_session_id,
            metadata={'context_id': context_id, **(metadata or {})}
        )
        self.audit_logger.log_audit_event(start_event)
        
        try:
            yield context_id
        except Exception as e:
            # Log error
            error_event = AuditEvent(
                timestamp=datetime.now(),
                event_type=EventType.SYSTEM_EVENT,
                level=LogLevel.ERROR,
                message=f"Context error: {context_name}",
                session_id=self._current_session_id,
                metadata={
                    'context_id': context_id,
                    'error': str(e),
                    **(metadata or {})
                }
            )
            self.audit_logger.log_audit_event(error_event)
            raise
        finally:
            # Log end
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            end_event = AuditEvent(
                timestamp=end_time,
                event_type=EventType.SYSTEM_EVENT,
                level=LogLevel.INFO,
                message=f"Context ended: {context_name}",
                session_id=self._current_session_id,
                metadata={
                    'context_id': context_id,
                    'duration_seconds': duration,
                    **(metadata or {})
                }
            )
            self.audit_logger.log_audit_event(end_event)


# Global logging system instance
_logging_system: Optional[LoggingSystem] = None


def get_logging_system() -> LoggingSystem:
    """Get the global logging system instance"""
    global _logging_system
    if _logging_system is None:
        _logging_system = LoggingSystem()
    return _logging_system


def initialize_logging(config: Optional[Dict[str, Any]] = None) -> LoggingSystem:
    """Initialize the global logging system"""
    global _logging_system
    _logging_system = LoggingSystem(config)
    return _logging_system 