"""
Enhanced Configuration module for ChatOps CLI

Handles environment variables, API keys, configuration files, and application settings
with support for multiple LLM providers, profiles, and advanced validation.
"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator


class LLMProviderConfig(BaseModel):
    """Configuration for individual LLM providers"""
    
    name: str
    enabled: bool = True
    api_key: Optional[str] = None
    model: str = "default"
    base_url: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.1
    timeout: int = 30
    
    @validator('api_key', pre=True, always=True)
    def validate_api_key(cls, v, values):
        """Validate API key is present when provider is enabled and requires it"""
        # Only validate API key for providers that require it (like Groq)
        # Ollama doesn't require an API key
        if values.get('name') == 'groq' and values.get('enabled', True) and not v:
            raise ValueError("API key is required for Groq provider")
        return v


class PluginConfig(BaseModel):
    """Configuration for plugin system"""
    
    auto_discovery: bool = True
    hot_reload: bool = False
    plugin_directories: List[str] = Field(default_factory=lambda: ["plugins/builtin"])
    enabled_plugins: List[str] = Field(default_factory=list)
    disabled_plugins: List[str] = Field(default_factory=list)


class SecurityConfig(BaseModel):
    """Security-related configuration"""
    
    require_confirmation: bool = True
    safe_mode: bool = True
    command_validation: bool = True
    dry_run_default: bool = False
    max_command_length: int = 1000
    allowed_domains: List[str] = Field(default_factory=list)
    blocked_commands: List[str] = Field(default_factory=lambda: ["rm -rf /", "format c:"])


class LoggingConfig(BaseModel):
    """Logging configuration"""
    
    level: str = "INFO"
    file_logging: bool = True
    log_directory: str = ".chatops_logs"
    max_log_size: int = 10 * 1024 * 1024  # 10MB
    log_retention_days: int = 30
    include_timestamps: bool = True
    log_commands: bool = True
    log_errors: bool = True


class Settings(BaseModel):
    """Enhanced application settings with comprehensive configuration support"""
    
    # LLM Provider Configurations
    groq: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            name="groq",
            model="llama3-8b-8192",
            max_tokens=1000,
            temperature=0.1
        )
    )
    
    ollama: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            name="ollama",
            model="mistral:7b",
            base_url="http://localhost:11434",
            max_tokens=1000,
            temperature=0.1
        )
    )
    
    # Provider Selection
    default_llm_provider: str = "groq"
    
    # Application Settings
    debug_mode: bool = False
    verbose_mode: bool = False
    
    # Plugin Configuration
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    
    # Security Configuration
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Logging Configuration
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Execution Settings
    execution_timeout: int = 60
    max_concurrent_commands: int = 3
    working_directory: Optional[str] = None
    
    # UI/UX Settings
    rich_output: bool = True
    color_output: bool = True
    progress_bars: bool = True
    
    # Profile Management
    current_profile: str = "default"
    profiles: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    class Config:
        env_prefix = "CHATOPS_"
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def __init__(self, **kwargs):
        # Load environment variables first
        self._load_environment()
        
        # Load configuration file if exists
        config_data = self._load_config_file()
        
        # Load provider-specific API keys from environment
        config_data = self._load_provider_api_keys(config_data)
        
        # Merge with kwargs
        merged_data = {**config_data, **kwargs}
        
        super().__init__(**merged_data)
    
    def _load_environment(self) -> None:
        """Load environment variables from .env file"""
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
    
    def _load_provider_api_keys(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load API keys for different providers from environment variables"""
        # Groq API Key
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            if 'groq' not in config_data:
                config_data['groq'] = {}
            config_data['groq']['api_key'] = groq_api_key
        
        # Ollama doesn't need API key, but check for base URL
        ollama_base_url = os.getenv("OLLAMA_BASE_URL")
        if ollama_base_url:
            if 'ollama' not in config_data:
                config_data['ollama'] = {}
            config_data['ollama']['base_url'] = ollama_base_url
        
        # Provider selection
        default_provider = os.getenv("DEFAULT_LLM_PROVIDER")
        if default_provider in ["groq", "ollama"]:
            config_data['default_llm_provider'] = default_provider
        
        return config_data
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from JSON/YAML file"""
        config_files = [
            Path("chatops_config.json"),
            Path("chatops_config.yaml"),
            Path("chatops_config.yml"),
            Path("config/chatops.json"),
            Path("config/chatops.yaml"),
            Path("config/chatops.yml"),
            Path(".chatops/config.json"),
            Path(".chatops/config.yaml"),
            Path(".chatops/config.yml")
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        if config_file.suffix.lower() in ['.yaml', '.yml']:
                            return yaml.safe_load(f) or {}
                        else:
                            return json.load(f)
                except (json.JSONDecodeError, yaml.YAMLError, IOError) as e:
                    print(f"Warning: Could not load config file {config_file}: {e}")
        
        return {}
    
    def save_config(self, config_file: Optional[Path] = None, format: str = "json") -> None:
        """Save current configuration to file"""
        if config_file is None:
            if format.lower() in ["yaml", "yml"]:
                config_file = Path("chatops_config.yaml")
            else:
                config_file = Path("chatops_config.json")
        
        # Ensure directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict, excluding sensitive data
        config_dict = self.dict(exclude={'groq': {'api_key'}, 'ollama': {'api_key'}})
        
        with open(config_file, 'w', encoding='utf-8') as f:
            if format.lower() in ["yaml", "yml"]:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            else:
                json.dump(config_dict, f, indent=2, default=str)
    
    def load_profile(self, profile_name: str) -> bool:
        """Load a specific configuration profile"""
        if profile_name not in self.profiles:
            return False
        
        profile_data = self.profiles[profile_name]
        
        # Update current settings with profile data
        for key, value in profile_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        self.current_profile = profile_name
        return True
    
    def save_profile(self, profile_name: str) -> None:
        """Save current settings as a profile"""
        # Convert current settings to dict, excluding sensitive data
        profile_data = self.dict(exclude={'groq': {'api_key'}, 'ollama': {'api_key'}})
        
        self.profiles[profile_name] = profile_data
    
    def list_profiles(self) -> List[str]:
        """List all available configuration profiles"""
        return list(self.profiles.keys())
    
    def delete_profile(self, profile_name: str) -> bool:
        """Delete a configuration profile"""
        if profile_name in self.profiles:
            del self.profiles[profile_name]
            if self.current_profile == profile_name:
                self.current_profile = "default"
            return True
        return False
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        # Validate LLM provider configuration
        if self.default_llm_provider == "groq":
            if not self.groq.enabled:
                issues.append("Groq is set as default provider but is disabled")
            elif not self.groq.api_key:
                issues.append("GROQ_API_KEY is required when using Groq as default provider")
        
        elif self.default_llm_provider == "ollama":
            if not self.ollama.enabled:
                issues.append("Ollama is set as default provider but is disabled")
        
        # Validate plugin directories
        for plugin_dir in self.plugins.plugin_directories:
            if not Path(plugin_dir).exists():
                issues.append(f"Plugin directory does not exist: {plugin_dir}")
        
        # Validate logging directory
        if self.logging.file_logging:
            log_dir = Path(self.logging.log_directory)
            if not log_dir.exists():
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    issues.append(f"Cannot create log directory {log_dir}: {e}")
        
        # Validate working directory
        if self.working_directory:
            work_dir = Path(self.working_directory)
            if not work_dir.exists():
                issues.append(f"Working directory does not exist: {work_dir}")
            elif not work_dir.is_dir():
                issues.append(f"Working directory is not a directory: {work_dir}")
        
        return issues
    
    def get_provider_config(self, provider_name: str) -> Optional[LLMProviderConfig]:
        """Get configuration for a specific LLM provider"""
        if provider_name == "groq":
            return self.groq
        elif provider_name == "ollama":
            return self.ollama
        return None
    
    def is_provider_enabled(self, provider_name: str) -> bool:
        """Check if a specific LLM provider is enabled"""
        provider_config = self.get_provider_config(provider_name)
        return provider_config is not None and provider_config.enabled
    
    def get_available_providers(self) -> List[str]:
        """Get list of available and enabled LLM providers"""
        providers = []
        if self.is_provider_enabled("groq"):
            providers.append("groq")
        if self.is_provider_enabled("ollama"):
            providers.append("ollama")
        return providers
    
    def export_env_template(self, output_file: Optional[Path] = None) -> None:
        """Export environment variable template"""
        if output_file is None:
            output_file = Path(".env.template")
        
        template_content = """# ChatOps CLI Environment Configuration Template

# LLM Provider API Keys
GROQ_API_KEY=your_groq_api_key_here
OLLAMA_BASE_URL=http://localhost:11434

# Provider Selection
DEFAULT_LLM_PROVIDER=groq

# Application Settings
CHATOPS_DEBUG_MODE=false
CHATOPS_VERBOSE_MODE=false

# Security Settings
CHATOPS_REQUIRE_CONFIRMATION=true
CHATOPS_SAFE_MODE=true

# Logging Settings
CHATOPS_LOG_LEVEL=INFO
CHATOPS_FILE_LOGGING=true
CHATOPS_LOG_DIRECTORY=.chatops_logs

# Execution Settings
CHATOPS_EXECUTION_TIMEOUT=60
CHATOPS_MAX_CONCURRENT_COMMANDS=3
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(template_content)
    
    # Backward compatibility properties
    @property
    def groq_api_key(self) -> Optional[str]:
        return self.groq.api_key
    
    @property
    def groq_model(self) -> str:
        return self.groq.model
    
    @property
    def ollama_base_url(self) -> str:
        return self.ollama.base_url or "http://localhost:11434"
    
    @property
    def ollama_model(self) -> str:
        return self.ollama.model
    
    @property
    def max_tokens(self) -> int:
        provider_config = self.get_provider_config(self.default_llm_provider)
        return provider_config.max_tokens if provider_config else 1000
    
    @property
    def temperature(self) -> float:
        provider_config = self.get_provider_config(self.default_llm_provider)
        return provider_config.temperature if provider_config else 0.1
    
    @property
    def require_confirmation(self) -> bool:
        return self.security.require_confirmation
    
    @property
    def safe_mode(self) -> bool:
        return self.security.safe_mode
    
    @property
    def log_level(self) -> str:
        return self.logging.level


# Global settings instance
settings = Settings() 