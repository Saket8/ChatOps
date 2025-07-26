"""
LLM AI Plugin for ChatOps CLI

Provides direct access to Large Language Model capabilities for conversations,
code generation, explanations, and general AI assistance beyond command generation.
"""

import re
from datetime import datetime
from typing import Any, Optional

from ..base import (
    CommandPlugin,
    PluginCapability,
    PluginPriority,
    plugin,
)
from ...core.groq_client import GroqClient
from ...core.langchain_integration import CommandType, DevOpsCommand, RiskLevel
from ...core.ollama_client import OllamaClient
from ...core.os_detection import os_detection


@plugin(
    name="llm",
    version="1.0.0",
    description="Direct LLM AI assistance for conversations, code generation, and explanations",  # noqa: E501
    author="ChatOps CLI Team",
    category="ai",
    tags=["llm", "ai", "chat", "code", "assistant", "gpt", "ollama"],
    priority=PluginPriority.HIGH,
)
class LLMPlugin(CommandPlugin):
    """
    Plugin for direct Large Language Model interactions.

    Provides commands for:
    - Natural language conversations
    - Code generation and explanation
    - Technical documentation
    - Problem solving assistance
    - Multi-turn conversations with context
    """

    def __init__(self) -> None:
        super().__init__()
        self._capabilities.extend([
            PluginCapability.COMMAND_GENERATION,
            PluginCapability.OUTPUT_PROCESSING,
        ])

        # LLM command patterns this plugin can handle
        self._command_patterns = [
            r".*ask\s+ai.*",
            r".*chat\s+.*",
            r".*explain\s+.*",
            r".*generate\s+.*",
            r".*write\s+.*",
            r".*help\s+with.*",
            r".*how\s+to.*",
            r".*what\s+is.*",
            r".*tell\s+me.*",
            r".*create\s+.*",
            r".*code\s+.*",
            r".*debug\s+.*",
            r".*review\s+.*",
        ]

        # Conversation history for context
        self._conversation_history = []
        self._max_history = 10

        # LLM clients
        self._ollama_client = None
        self._groq_client = None

    async def initialize(self) -> bool:
        """Initialize the LLM plugin"""
        try:
            # Initialize LLM clients
            self._ollama_client = OllamaClient()
            self._groq_client = GroqClient()

            # Test connectivity (optional)
            try:
                await self._ollama_client.test_connection()
                self.logger.info("Ollama client initialized successfully")
            except Exception as e:
                self.logger.warning(f"Ollama not available: {e}")

            try:
                await self._groq_client.test_connection()
                self.logger.info("Groq client initialized successfully")
            except Exception as e:
                self.logger.warning(f"Groq not available: {e}")

            self.logger.info("LLM plugin initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize LLM plugin: {e}")
            return False

    async def cleanup(self) -> bool:
        """Cleanup LLM plugin resources"""
        if self._ollama_client:
            await self._ollama_client.close()
        if self._groq_client:
            await self._groq_client.close()
        
        self.logger.info("LLM plugin cleanup complete")
        return True

    def can_handle(self, user_input: str, context: Optional[dict[str, Any]] = None) -> bool:
        """Check if this plugin can handle the user input"""
        user_input_lower = user_input.lower()

        # Check against command patterns
        for pattern in self._command_patterns:
            if re.search(pattern, user_input_lower):
                return True

        # Check for AI/LLM-related keywords
        ai_keywords = [
            "ai", "llm", "gpt", "chat", "explain", "generate", "write",
            "help", "how", "what", "why", "code", "debug", "review",
            "create", "build", "design", "optimize", "fix"
        ]

        # Check for conversation starters (but exclude system commands)
        conversation_starters = [
            "tell me", "can you", "please", "i need", "help with",
            "teach me", "explain", "what is", "how do"
        ]
        
        # Don't catch system commands that start with "show"
        system_commands = [
            "show memory", "show disk", "show cpu", "show process", 
            "show system", "show network", "show available", "show running"
        ]
        
        # If it's a system command, let the system plugin handle it
        if any(cmd in user_input_lower for cmd in system_commands):
            return False

        return any(keyword in user_input_lower for keyword in ai_keywords + conversation_starters)

    async def generate_command(
        self, user_input: str, context: Optional[dict[str, Any]] = None
    ) -> Optional[DevOpsCommand]:
        """Generate LLM response command from natural language input"""
        user_input_lower = user_input.lower()

        # Determine the type of AI assistance needed
        if any(keyword in user_input_lower for keyword in ["code", "write code", "generate code", "programming"]):
            return self._generate_code_assistance_command(user_input)
        
        elif any(keyword in user_input_lower for keyword in ["explain", "what is", "how does", "tell me about"]):
            return self._generate_explanation_command(user_input)
        
        elif any(keyword in user_input_lower for keyword in ["debug", "fix", "error", "troubleshoot"]):
            return self._generate_debugging_command(user_input)
        
        elif any(keyword in user_input_lower for keyword in ["review", "check", "analyze", "optimize"]):
            return self._generate_review_command(user_input)
        
        elif any(keyword in user_input_lower for keyword in ["create", "build", "design", "plan"]):
            return self._generate_creation_command(user_input)
        
        else:
            # General conversation
            return self._generate_chat_command(user_input)

    def _generate_code_assistance_command(self, user_input: str) -> DevOpsCommand:
        """Generate code assistance command"""
        if os_detection.get_os_info().is_windows:
            cmd = f"Write-Host 'AI Code Assistant Request: {user_input}'; Write-Host 'Generating code solution...'"
        else:
            cmd = f"echo 'AI Code Assistant Request: {user_input}' && echo 'Generating code solution...'"
        
        return DevOpsCommand(
            command=cmd,
            description=f"AI code generation and assistance for: {user_input[:60]}{'...' if len(user_input) > 60 else ''}",
            command_type=CommandType.SYSTEM_INFO,
            risk_level=RiskLevel.SAFE,
            requires_sudo=False,
            estimated_duration="< 10 seconds",
            prerequisites=["llm_client"],
            alternative_commands=["Ask specific programming language", "Request step-by-step tutorial"]
        )

    def _generate_explanation_command(self, user_input: str) -> DevOpsCommand:
        """Generate explanation command with OS-specific commands for system queries"""
        user_input_lower = user_input.lower()
        
        # Check if this is a system information query we can provide a real command for
        if any(term in user_input_lower for term in ["memory", "ram", "system memory"]):
            # Use OS-specific memory command
            memory_cmd = os_detection.smart_translate("memory usage")
            return DevOpsCommand(
                command=memory_cmd,
                description=f"Show system memory information",
                command_type=CommandType.SYSTEM_INFO,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 5 seconds",
                prerequisites=[],
                alternative_commands=["Task Manager", "Resource Monitor"]
            )
        
        elif any(term in user_input_lower for term in ["disk", "storage", "space"]):
            # Use OS-specific disk command  
            disk_cmd = os_detection.smart_translate("disk usage")
            return DevOpsCommand(
                command=disk_cmd,
                description=f"Show disk usage information",
                command_type=CommandType.SYSTEM_INFO,
                risk_level=RiskLevel.SAFE,
                requires_sudo=False,
                estimated_duration="< 5 seconds",
                prerequisites=[],
                alternative_commands=["File Explorer Properties"]
            )
        
        else:
            # For other explanations, use OS-appropriate echo command
            if os_detection.get_os_info().is_windows:
                echo_cmd = f"Write-Host 'AI Explanation Request: {user_input}'; Write-Host 'Preparing detailed explanation...'"
            else:
                echo_cmd = f"echo 'AI Explanation Request: {user_input}' && echo 'Preparing detailed explanation...'"
            
            return DevOpsCommand(
                command=echo_cmd,
                description=f"AI explanation and educational content for: {user_input[:60]}{'...' if len(user_input) > 60 else ''}",
            command_type=CommandType.SYSTEM_INFO,
            risk_level=RiskLevel.SAFE,
            requires_sudo=False,
            estimated_duration="< 8 seconds",
            prerequisites=["llm_client"],
            alternative_commands=["Request simpler explanation", "Ask for examples"]
        )

    def _generate_debugging_command(self, user_input: str) -> DevOpsCommand:
        """Generate debugging assistance command"""
        return DevOpsCommand(
            command=f"echo 'AI Debug Assistant: {user_input}' && echo 'Analyzing issue and suggesting solutions...'",
            description=f"AI debugging and troubleshooting assistance for: {user_input[:60]}{'...' if len(user_input) > 60 else ''}",
            command_type=CommandType.SYSTEM_INFO,
            risk_level=RiskLevel.SAFE,
            requires_sudo=False,
            estimated_duration="< 12 seconds",
            prerequisites=["llm_client"],
            alternative_commands=["Provide error logs", "Share code snippet"]
        )

    def _generate_review_command(self, user_input: str) -> DevOpsCommand:
        """Generate code/system review command"""
        return DevOpsCommand(
            command=f"echo 'AI Code/System Review: {user_input}' && echo 'Performing analysis and providing feedback...'",
            description=f"AI review and optimization suggestions for: {user_input[:60]}{'...' if len(user_input) > 60 else ''}",
            command_type=CommandType.SYSTEM_INFO,
            risk_level=RiskLevel.SAFE,
            requires_sudo=False,
            estimated_duration="< 15 seconds",
            prerequisites=["llm_client"],
            alternative_commands=["Focus on specific aspects", "Request security review"]
        )

    def _generate_creation_command(self, user_input: str) -> DevOpsCommand:
        """Generate creation/design assistance command"""
        return DevOpsCommand(
            command=f"echo 'AI Creation Assistant: {user_input}' && echo 'Designing solution and implementation plan...'",
            description=f"AI creation and design assistance for: {user_input[:60]}{'...' if len(user_input) > 60 else ''}",
            command_type=CommandType.SYSTEM_INFO,
            risk_level=RiskLevel.SAFE,
            requires_sudo=False,
            estimated_duration="< 20 seconds",
            prerequisites=["llm_client"],
            alternative_commands=["Request architecture diagram", "Ask for step-by-step plan"]
        )

    def _generate_chat_command(self, user_input: str) -> DevOpsCommand:
        """Generate general chat command"""
        return DevOpsCommand(
            command=f"echo 'AI Chat: {user_input}' && echo 'Processing your request...'",
            description=f"AI conversation and general assistance for: {user_input[:60]}{'...' if len(user_input) > 60 else ''}",
            command_type=CommandType.SYSTEM_INFO,
            risk_level=RiskLevel.SAFE,
            requires_sudo=False,
            estimated_duration="< 8 seconds",
            prerequisites=["llm_client"],
            alternative_commands=["Be more specific", "Ask follow-up questions"]
        )

    async def process_llm_request(self, user_input: str, context: Optional[dict[str, Any]] = None) -> str:
        """Process LLM request and return response"""
        try:
            # Add to conversation history
            self._conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })

            # Limit history size
            if len(self._conversation_history) > self._max_history * 2:
                self._conversation_history = self._conversation_history[-self._max_history:]

            # Prepare context for LLM
            conversation_context = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in self._conversation_history[-6:]  # Last 6 messages for context
            ])

            # Try Groq first (faster), fall back to Ollama
            response = None
            try:
                if self._groq_client:
                    response = await self._groq_client.generate_response(
                        prompt=user_input,
                        system_prompt=conversation_context
                    )
            except Exception as e:
                self.logger.warning(f"Groq request failed: {e}")

            if not response and self._ollama_client:
                try:
                    # Ollama doesn't support separate context, include it in prompt
                    full_prompt = f"{conversation_context}\n\nUser: {user_input}\nAssistant:"
                    response = await self._ollama_client.generate_response(
                        prompt=full_prompt
                    )
                except Exception as e:
                    self.logger.warning(f"Ollama request failed: {e}")

            if response:
                # Add response to history
                self._conversation_history.append({
                    "role": "assistant",
                    "content": response.content,
                    "timestamp": datetime.now().isoformat()
                })
                return response.content
            else:
                return "Sorry, I'm having trouble connecting to the AI service. Please check your LLM configuration."

        except Exception as e:
            self.logger.error(f"Error processing LLM request: {e}")
            return f"Error processing AI request: {str(e)}"

    async def validate_command(
        self, command: DevOpsCommand, context: Optional[dict[str, Any]] = None
    ) -> bool:
        """Validate LLM commands (all are safe by design)"""
        return True

    def get_help(self) -> str:
        """Return help text for the LLM plugin"""
        return """
🤖 LLM AI Plugin v1.0.0

This plugin provides direct access to Large Language Model capabilities
for conversations, code generation, and AI assistance.

Code Assistance:
• "write code for <task>"
• "generate a Python script to <action>"
• "create a function that <does_something>"
• "show me how to implement <feature>"

Explanations:
• "explain <concept>"
• "what is <technology>?"
• "how does <system> work?"
• "tell me about <topic>"

Debugging Help:
• "debug this error: <error_message>"
• "fix this code: <code_snippet>"
• "troubleshoot <issue>"
• "why is <something> not working?"

Code Review:
• "review this code: <code>"
• "optimize this script: <script>"
• "check for security issues in <code>"
• "analyze this architecture: <description>"

Creation & Design:
• "create a plan for <project>"
• "design a system that <requirements>"
• "build a workflow for <process>"
• "architect a solution for <problem>"

General Chat:
• "help me with <anything>"
• "can you <request>?"
• "i need advice on <topic>"
• "what would you recommend for <situation>?"

Examples:
  chatops ask "write a Python function to parse JSON"
  chatops ask "explain microservices architecture"
  chatops ask "debug this Docker error: container won't start"
  chatops ask "review my bash script for security issues"
  chatops ask "create a CI/CD pipeline design"

🧠 Features:
• Maintains conversation context
• Supports multiple LLM backends (Ollama, Groq)
• Code generation and explanation
• Technical problem solving
• Educational content

⚙️ Prerequisites: Ollama or Groq API configured
        """.strip()

    async def get_metrics(self, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Get LLM plugin metrics"""
        try:
            ollama_available = bool(self._ollama_client and await self._ollama_client.test_connection())
            groq_available = bool(self._groq_client and await self._groq_client.test_connection())
            
            return {
                "timestamp": datetime.now().isoformat(),
                "ollama_available": ollama_available,
                "groq_available": groq_available,
                "conversation_history_length": len(self._conversation_history),
                "plugin_status": "active",
                "supported_operations": [
                    "code_generation", "explanations", "debugging_assistance",
                    "code_review", "system_design", "general_conversation"
                ]
            }
        except Exception as e:
            self.logger.error(f"Error collecting LLM metrics: {e}")
            return {"error": str(e)}

    def clear_history(self) -> None:
        """Clear conversation history"""
        self._conversation_history = []
        self.logger.info("Conversation history cleared")

    def get_history(self) -> list[dict[str, str]]:
        """Get conversation history"""
        return self._conversation_history.copy() 