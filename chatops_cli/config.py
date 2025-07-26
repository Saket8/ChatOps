"""
Configuration module for ChatOps CLI

Handles environment variables, API keys, and application settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


class Settings:
    """Application settings with environment variable support"""
    
    def __init__(self) -> None:
        # Load environment variables from .env file
        env_file = Path(".env")
        if env_file.exists():
            load_dotenv(env_file)
    
    # Groq API Settings (Free LLM API)
    @property
    def groq_api_key(self) -> str | None:
        return os.getenv("GROQ_API_KEY")
    
    @property
    def groq_model(self) -> str:
        return os.getenv("GROQ_MODEL", "llama3-8b-8192")
    
    # Ollama Settings (Local LLM)
    @property
    def ollama_base_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    @property
    def ollama_model(self) -> str:
        return os.getenv("OLLAMA_MODEL", "mistral:7b")
    
    # LLM Provider Selection
    @property
    def default_llm_provider(self) -> str:
        return os.getenv("DEFAULT_LLM_PROVIDER", "groq")
    
    # Application Settings
    @property
    def debug_mode(self) -> bool:
        return os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", "INFO")
    
    # LLM Generation Settings
    @property
    def max_tokens(self) -> int:
        return int(os.getenv("MAX_TOKENS", "1000"))
    
    @property
    def temperature(self) -> float:
        return float(os.getenv("TEMPERATURE", "0.1"))
    
    # Security Settings
    @property
    def require_confirmation(self) -> bool:
        return os.getenv("REQUIRE_CONFIRMATION", "true").lower() == "true"
    
    @property
    def safe_mode(self) -> bool:
        return os.getenv("SAFE_MODE", "true").lower() == "true"
    
    def validate_settings(self) -> list[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        if self.default_llm_provider == "groq" and not self.groq_api_key:
            issues.append("GROQ_API_KEY is required when using Groq as LLM provider")
        
        if self.default_llm_provider == "ollama":
            # Ollama validation could be added here
            pass
        
        return issues


# Global settings instance
settings = Settings() 