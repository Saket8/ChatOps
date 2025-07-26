"""
Ollama Integration Module for ChatOps CLI

This module provides the core integration with Ollama LLM service,
including connection management, model loading, and inference capabilities.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum

import ollama
from ollama import Client
import aiohttp
import requests


class ModelStatus(Enum):
    """Status of an Ollama model"""

    AVAILABLE = "available"
    LOADED = "loaded"
    UNAVAILABLE = "unavailable"
    MEMORY_ERROR = "memory_error"
    NOT_FOUND = "not_found"


@dataclass
class ModelInfo:
    """Information about an Ollama model"""

    name: str
    id: str
    size: str
    status: ModelStatus
    memory_required: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class OllamaResponse:
    """Response from Ollama inference"""

    content: str
    model: str
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None


class OllamaClient:
    """
    Client for interacting with Ollama LLM service.

    Handles connection management, model loading, inference requests,
    and error handling including memory constraints.
    """

    def __init__(
        self,
        host: str = "http://localhost:11434",
        timeout: int = 30,
        preferred_models: Optional[List[str]] = None,
    ):
        """
        Initialize OllamaClient.

        Args:
            host: Ollama service host URL
            timeout: Request timeout in seconds
            preferred_models: List of preferred models in order of preference
        """
        self.host = host
        self.timeout = timeout
        self.preferred_models = preferred_models or [
            "qwen3:latest",
            "phi4:3.8b",
            "devstral:latest",
            "qwen3:14b",
        ]
        self.client = Client(host=host)
        self.logger = logging.getLogger(__name__)
        self._current_model: Optional[str] = None
        self._model_cache: Dict[str, ModelInfo] = {}

    async def connect(self) -> bool:
        """
        Test connection to Ollama service.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Test basic connectivity
            response = requests.get(f"{self.host}/api/version", timeout=5)
            if response.status_code == 200:
                self.logger.info(f"Connected to Ollama at {self.host}")
                return True
            else:
                self.logger.error(
                    f"Ollama service not responding: {response.status_code}"
                )
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to connect to Ollama: {e}")
            return False

    def list_models(self) -> List[ModelInfo]:
        """
        List all available models with their status.

        Returns:
            List of ModelInfo objects
        """
        models = []
        try:
            response = self.client.list()
            for model_data in response.get("models", []):
                name = model_data.get("name", "")
                model_info = ModelInfo(
                    name=name,
                    id=model_data.get("digest", ""),
                    size=self._format_size(model_data.get("size", 0)),
                    status=ModelStatus.AVAILABLE,
                )
                models.append(model_info)
                self._model_cache[name] = model_info

        except Exception as e:
            self.logger.error(f"Failed to list models: {e}")

        return models

    def get_best_available_model(self) -> Optional[str]:
        """
        Get the best available model that can actually run.

        Returns:
            Model name if available, None otherwise
        """
        available_models = self.list_models()
        available_names = [m.name for m in available_models]

        # Try preferred models in order
        for model in self.preferred_models:
            if model in available_names:
                # Test if model can actually run
                if self._test_model_memory(model):
                    self.logger.info(f"Selected model: {model}")
                    return model
                else:
                    self.logger.warning(
                        f"Model {model} available but cannot run due to memory constraints"
                    )

        self.logger.error("No suitable model found that can run on this system")
        return None

    def _test_model_memory(self, model_name: str) -> bool:
        """
        Test if a model can load without memory errors.

        Args:
            model_name: Name of the model to test

        Returns:
            True if model can load, False if memory error
        """
        try:
            # Try a very simple inference to test memory
            response = self.client.generate(
                model=model_name,
                prompt="Hi",
                options={"num_ctx": 512},  # Limit context to reduce memory usage
            )
            if response:
                self.logger.info(f"Model {model_name} loaded successfully")
                return True
        except Exception as e:
            error_msg = str(e).lower()
            if "memory" in error_msg or "system memory" in error_msg:
                self.logger.warning(f"Model {model_name} failed memory test: {e}")
                # Update model cache with memory error status
                if model_name in self._model_cache:
                    self._model_cache[model_name].status = ModelStatus.MEMORY_ERROR
                    self._model_cache[model_name].error_message = str(e)
                return False
            else:
                self.logger.error(f"Model {model_name} test failed: {e}")
                return False
        return False

    async def generate_response(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> OllamaResponse:
        """
        Generate response from Ollama model.

        Args:
            prompt: Input prompt
            model: Model name (auto-select if None)
            max_tokens: Maximum tokens to generate
            temperature: Response randomness (0.0 to 1.0)

        Returns:
            OllamaResponse object with result or error
        """
        import time

        start_time = time.time()

        # Auto-select model if not specified
        if not model:
            model = self._current_model or self.get_best_available_model()

        if not model:
            return OllamaResponse(
                content="",
                model="none",
                success=False,
                error="No suitable model available",
            )

        try:
            response = self.client.generate(
                model=model,
                prompt=prompt,
                options={
                    "num_predict": max_tokens,
                    "temperature": temperature,
                    "num_ctx": 2048,  # Context length
                },
            )

            content = response.get("response", "")
            response_time = time.time() - start_time

            self.logger.info(
                f"Generated response using {model} in {response_time:.2f}s"
            )
            self._current_model = model

            return OllamaResponse(
                content=content, model=model, success=True, response_time=response_time
            )

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Generation failed with {model}: {error_msg}")

            # Handle memory errors with fallback
            if "memory" in error_msg.lower():
                self.logger.warning(f"Memory error with {model}, trying fallback")
                return await self._try_fallback_model(
                    prompt, model, max_tokens, temperature
                )

            return OllamaResponse(
                content="", model=model or "unknown", success=False, error=error_msg
            )

    async def _try_fallback_model(
        self, prompt: str, failed_model: str, max_tokens: int, temperature: float
    ) -> OllamaResponse:
        """
        Try fallback models when primary model fails.

        Args:
            prompt: Original prompt
            failed_model: Model that failed
            max_tokens: Maximum tokens
            temperature: Temperature setting

        Returns:
            OllamaResponse from fallback model or error
        """
        # Get remaining models to try
        remaining_models = [m for m in self.preferred_models if m != failed_model]

        for fallback_model in remaining_models:
            if self._test_model_memory(fallback_model):
                self.logger.info(f"Trying fallback model: {fallback_model}")
                return await self.generate_response(
                    prompt,
                    model=fallback_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

        return OllamaResponse(
            content="",
            model=failed_model,
            success=False,
            error="All fallback models failed due to memory constraints",
        )

    def get_model_status(self, model_name: str) -> ModelInfo:
        """
        Get detailed status of a specific model.

        Args:
            model_name: Name of the model

        Returns:
            ModelInfo object with current status
        """
        if model_name in self._model_cache:
            return self._model_cache[model_name]

        # Try to get fresh info
        models = self.list_models()
        for model in models:
            if model.name == model_name:
                return model

        return ModelInfo(
            name=model_name,
            id="",
            size="",
            status=ModelStatus.NOT_FOUND,
            error_message="Model not found",
        )

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format byte size to human readable string"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def get_system_info(self) -> Dict[str, Any]:
        """
        Get system and Ollama service information.

        Returns:
            Dictionary with system info
        """
        info = {
            "host": self.host,
            "timeout": self.timeout,
            "current_model": self._current_model,
            "preferred_models": self.preferred_models,
            "available_models": [m.name for m in self.list_models()],
            "model_cache_size": len(self._model_cache),
        }

        try:
            # Try to get Ollama version
            response = requests.get(f"{self.host}/api/version", timeout=5)
            if response.status_code == 200:
                info["ollama_version"] = response.json()
        except:
            info["ollama_version"] = "unknown"

        return info
    
    async def test_connection(self) -> bool:
        """Test connection to Ollama service"""
        try:
            # Try to connect and get a simple response
            response = requests.get(f"{self.host}/api/version", timeout=5)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Ollama test connection failed: {e}")
            return False
