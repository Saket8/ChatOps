"""
Groq API Client for ChatOps CLI

Provides integration with Groq's free, fast LLM API service.
Groq offers lightning-fast inference with models like Llama3, Mixtral, and Gemma.
"""

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from ..config import settings


@dataclass
class GroqResponse:
    """Response from Groq API"""
    content: str
    success: bool
    error: str | None = None
    model: str | None = None
    tokens_used: int | None = None


class GroqClient:
    """
    Client for interacting with Groq's free LLM API.
    
    Groq provides ultra-fast LLM inference with generous free tiers.
    Perfect for development and production use cases.
    """
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._client: ChatGroq | None = None
        self._connected = False
    
    async def connect(self) -> bool:
        """Initialize connection to Groq API"""
        try:
            if not settings.groq_api_key:
                self.logger.error("GROQ_API_KEY not found in environment variables")
                return False
            
            self._client = ChatGroq(
                api_key=settings.groq_api_key,
                model=settings.groq_model,
                temperature=settings.temperature,
                max_tokens=settings.max_tokens,
            )
            
            # Test the connection with a simple query
            test_response = await self._client.ainvoke([
                HumanMessage(content="Hello")
            ])
            
            if test_response:
                self._connected = True
                self.logger.info(
                    f"Connected to Groq API with model: {settings.groq_model}"
                )
                return True
            else:
                self.logger.error("Failed to get response from Groq API")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Groq API: {e}")
            self._connected = False
            return False
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> GroqResponse:
        """
        Generate response using Groq API.
        
        Args:
            prompt: User prompt/question
            system_prompt: Optional system prompt for context
            model: Override default model
            max_tokens: Override default max tokens
            temperature: Override default temperature
            
        Returns:
            GroqResponse with generated content
        """
        if not self._connected or not self._client:
            if not await self.connect():
                return GroqResponse(
                    content="",
                    success=False,
                    error="Not connected to Groq API"
                )
        
        try:
            # Prepare messages
            messages = []
            
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            messages.append(HumanMessage(content=prompt))
            
            # Update client settings if overrides provided
            if model or max_tokens or temperature:
                self._client = ChatGroq(
                    api_key=settings.groq_api_key,
                    model=model or settings.groq_model,
                    temperature=temperature or settings.temperature,
                    max_tokens=max_tokens or settings.max_tokens,
                )
            
            # Generate response
            response = await self._client.ainvoke(messages)
            
            return GroqResponse(
                content=response.content,
                success=True,
                model=model or settings.groq_model,
                tokens_used=getattr(response, 'usage', {}).get('total_tokens')
            )
            
        except Exception as e:
            self.logger.error(f"Groq API request failed: {e}")
            return GroqResponse(
                content="",
                success=False,
                error=str(e)
            )
    
    def is_connected(self) -> bool:
        """Check if client is connected to Groq API"""
        return self._connected
    
    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model"""
        return {
            "provider": "groq",
            "model": settings.groq_model,
            "max_tokens": settings.max_tokens,
            "temperature": settings.temperature,
            "api_key_configured": bool(settings.groq_api_key),
            "connected": self._connected,
        }
    
    def list_available_models(self) -> list[str]:
        """List available Groq models"""
        return [
            "llama3-8b-8192",      # Llama 3 8B (fastest)
            "llama3-70b-8192",     # Llama 3 70B (most capable)
            "mixtral-8x7b-32768",  # Mixtral 8x7B (good balance)
            "gemma-7b-it",         # Google Gemma 7B
            "gemma2-9b-it",        # Google Gemma 2 9B
        ] 