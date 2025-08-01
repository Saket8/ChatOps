#!/usr/bin/env python3
"""
Main CLI interface for ChatOps CLI

This module provides the primary command-line interface using Click framework,
with command groups, global options, and integration with our core components.
"""

import sys
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Try to import readline, but make it optional (not available on Windows)
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from ..settings import settings
from ..core.groq_client import GroqClient, GroqResponse
from ..core.langchain_integration import LangChainIntegration, DevOpsCommand, RiskLevel
from ..core.command_executor import CommandExecutor, ExecutionContext, ExecutionStatus
from ..plugins import PluginManager


# Global console for rich output
console = Console()


# Global context for CLI state
class CLIContext:
    def __init__(self) -> None:
        self.debug = False
        self.verbose = False
        self.config_file: Optional[str] = None
        self.groq_client: Optional[GroqClient] = None
        self.langchain: Optional[LangChainIntegration] = None
        self.plugin_manager: Optional[PluginManager] = None
        self.command_executor: Optional[CommandExecutor] = None
        self.logging_system: Optional[Any] = None  # Will be set in setup_logging
        # Interactive session state
        self.chat_history: list[dict[str, Any]] = []
        self.session_context: str = ""
        self.session_start_time: Optional[datetime] = None
        self.command_count: int = 0

    def setup_logging(self) -> None:
        """Setup logging based on debug/verbose flags"""
        # Initialize the comprehensive logging system
        from ..core.logging_system import initialize_logging
        
        # Configure logging level based on flags
        if self.debug:
            settings.logging.level = "DEBUG"
        elif self.verbose:
            settings.logging.level = "INFO"
        else:
            settings.logging.level = "WARNING"
        
        # Initialize the logging system
        self.logging_system = initialize_logging()
        
        # Start a new session for this CLI run
        session_id = f"cli_{int(datetime.now().timestamp())}"
        self.logging_system.start_session(session_id)
        
        # Setup basic logging for backward compatibility
        level = getattr(logging, settings.logging.level)
        logging.basicConfig(
            level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )


# Click context object
pass_context = click.make_pass_decorator(CLIContext, ensure=True)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug mode with detailed logging")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--config", "-c", type=click.Path(exists=True), help="Path to configuration file"
)
@click.version_option(version="0.1.0", prog_name="ChatOps CLI")
@pass_context
def cli(ctx: CLIContext, debug: bool, verbose: bool, config: Optional[str]):
    """
    ChatOps CLI - Offline DevOps Assistant with LangChain + Local LLM

    A command-line tool that converts natural language into DevOps commands,
    running completely offline with local LLM models.

    Examples:
        chatops ask "check disk space"
        chatops explain "df -h"
        chatops --verbose ask "restart nginx"
    """
    ctx.debug = debug
    ctx.verbose = verbose
    ctx.config_file = config
    ctx.setup_logging()

    # Initialize core components
    ctx.groq_client = GroqClient()
    ctx.langchain = LangChainIntegration()
    ctx.plugin_manager = PluginManager()
    ctx.command_executor = CommandExecutor()

    if debug:
        console.print("[dim]Debug mode enabled[/dim]", style="blue")


@cli.command()
@click.argument("request", required=True)
@click.option("--dry-run", is_flag=True, help="Show command without executing")
@click.option(
    "--explain", is_flag=True, help="Explain the command instead of generating"
)
@click.option("--model", "-m", help="Specific Ollama model to use")
@click.option("--context", "-ctx", help="Additional context for command generation")
@pass_context
def ask(
    ctx: CLIContext,
    request: str,
    dry_run: bool,
    explain: bool,
    model: Optional[str],
    context: Optional[str],
):
    """
    Ask the AI to generate a DevOps command from natural language.

    REQUEST is your natural language description of what you want to do.

    Examples:
        chatops ask "check disk space"
        chatops ask "restart nginx service"
        chatops ask --dry-run "delete all log files"
        chatops ask --context "Ubuntu 20.04" "update system packages"
    """
    if ctx.verbose:
        console.print(f"[dim]Processing request: {request}[/dim]")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            # Initialize plugin manager if not already done
            if not ctx.plugin_manager._plugins:
                task = progress.add_task("Initializing plugins...", total=None)
                success = asyncio.run(
                    ctx.plugin_manager.initialize({"hot_reload": ctx.debug})
                )
                if not success:
                    console.print(
                        "⚠️ [yellow]Warning: Plugin system initialization failed[/yellow]"
                    )

                if ctx.verbose:
                    plugin_count = len(ctx.plugin_manager)
                    console.print(f"[dim]Loaded {plugin_count} plugins[/dim]")

            # Try plugin system first
            task = progress.add_task("Finding plugin handler...", total=None)

            plugin_context = {
                "user_request": request,
                "additional_context": context,
                "explain_mode": explain,
                "dry_run": dry_run,
            }

            handler_plugin = asyncio.run(
                ctx.plugin_manager.find_handler(request, plugin_context)
            )

            if handler_plugin:
                progress.update(
                    task, description=f"Using {handler_plugin.metadata.name} plugin..."
                )

                # Generate command using plugin
                command = asyncio.run(
                    handler_plugin.generate_command(request, plugin_context)
                )

                if command:
                    if ctx.verbose:
                        console.print(
                            f"[dim]Command generated by {handler_plugin.metadata.name} plugin[/dim]"
                        )

                    # Validate command with plugin
                    if asyncio.run(
                        handler_plugin.validate_command(command, plugin_context)
                    ):
                        if explain:
                            # Show explanation for the command
                            explanation = handler_plugin.get_help()
                            console.print(
                                Panel(
                                    explanation,
                                    title=f"Plugin Help: {handler_plugin.metadata.name}",
                                    border_style="blue",
                                )
                            )
                        else:
                            # Display and potentially execute the command
                            _display_command(command, dry_run, ctx.verbose)

                            if not dry_run:
                                asyncio.run(_execute_command(command, ctx, ctx.verbose))
                        return
                    else:
                        console.print(
                            "⚠️ [yellow]Plugin command validation failed, falling back to AI[/yellow]"
                        )

            # Fallback to original LangChain + Ollama approach
            if ctx.verbose:
                console.print("[dim]No plugin found, using AI fallback...[/dim]")

            task = progress.add_task("Connecting to Ollama...", total=None)

            connected = asyncio.run(ctx.groq_client.connect())
            if not connected:
                console.print("❌ [red]Failed to connect to Groq API[/red]")
                console.print(
                    "💡 [yellow]Check your GROQ_API_KEY in .env file[/yellow]"
                )
                sys.exit(1)

            progress.update(task, description="Generating command...")

            # Generate prompt using LangChain
            prompt = ctx.langchain.generate_command(request, context or "")

            if explain:
                # Use explanation template instead
                prompt = ctx.langchain.explain_command(request)
                progress.update(task, description="Generating explanation...")

            # Get response from Ollama
            progress.update(task, description="Waiting for AI response...")

            response = asyncio.run(ctx.groq_client.generate_response(
                prompt=prompt,
                max_tokens=200 if explain else 100,
                temperature=0.1,
            ))

        if not response.success:
            console.print(f"❌ [red]AI request failed: {response.error}[/red]")

            # Show helpful suggestions based on error
            if "memory" in response.error.lower():
                console.print("\n💡 [yellow]Memory constraint detected. Try:[/yellow]")
                console.print(
                    "   • Use a smaller model: [cyan]ollama pull phi4:3.8b[/cyan]"
                )
                console.print("   • Check available models: [cyan]ollama list[/cyan]")
                console.print("   • Use --dry-run mode to see prompts without AI")

            sys.exit(1)

        if explain:
            # Show explanation directly
            console.print(
                Panel(
                    response.content.strip(),
                    title=f"Command Explanation: {request}",
                    border_style="blue",
                )
            )
        else:
            # Parse response into structured command
            command = ctx.langchain.parse_llm_response(response.content)

            # Display command information
            _display_command(command, dry_run, ctx.verbose)

            # Execute if not dry run and user confirms
            if not dry_run:
                asyncio.run(_execute_command(command, ctx, ctx.verbose))

    except KeyboardInterrupt:
        console.print("\n⏹️ [yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        if ctx.debug:
            console.print_exception()
        else:
            console.print(f"❌ [red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--model", "-m", help="Specific model to use for the session")
@click.option("--context", "-ctx", help="Initial context for the chat session")
@click.option("--save-history", is_flag=True, help="Save chat history to file on exit")
@pass_context
def chat(
    ctx: CLIContext,
    model: Optional[str],
    context: Optional[str],
    save_history: bool,
):
    """
    Start an interactive chat session with persistent context and command history.
    
    This mode allows you to have ongoing conversations with the AI, where each
    command builds on the previous context. Perfect for complex troubleshooting
    or multi-step operations.
    
    Commands:
        /help     - Show available commands
        /history  - Show conversation history
        /clear    - Clear conversation history
        /context  - Show current session context
        /save     - Save current conversation to file
        /exit     - Exit chat mode
        
    Examples:
        chatops chat
        chatops chat --context "Ubuntu 20.04 server"
        chatops chat --save-history
    """
    # Initialize session
    ctx.session_start_time = datetime.now()
    ctx.command_count = 0
    
    if context:
        ctx.session_context = context
        console.print(f"[dim]Session context set to: {context}[/dim]")
    
    # Setup readline for command history and editing (if available)
    if READLINE_AVAILABLE:
        try:
            readline.parse_and_bind("tab: complete")
            readline.parse_and_bind('"\\e[A": history-search-backward')
            readline.parse_and_bind('"\\e[B": history-search-forward')
            if ctx.debug:
                console.print("[dim]Readline support enabled[/dim]")
        except Exception as e:
            if ctx.debug:
                console.print(f"[dim]Warning: Readline setup failed: {e}[/dim]")
    else:
        if ctx.debug:
            console.print("[dim]Readline not available (Windows) - using basic input[/dim]")
    
    # Initialize systems
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            # Initialize core components if not already done
            if not ctx.langchain:
                ctx.langchain = LangChainIntegration()
            if not ctx.command_executor:
                ctx.command_executor = CommandExecutor()
                
            # Initialize plugin manager
            if not ctx.plugin_manager._plugins:
                task = progress.add_task("Initializing plugins...", total=None)
                success = asyncio.run(
                    ctx.plugin_manager.initialize({"hot_reload": ctx.debug})
                )
                if not success:
                    console.print("⚠️ [yellow]Warning: Plugin system initialization failed[/yellow]")
                    
            # Initialize AI connection
            task = progress.add_task("Connecting to AI service...", total=None)
            connected = asyncio.run(ctx.groq_client.connect())
            if not connected:
                console.print("❌ [red]Failed to connect to Groq API[/red]")
                console.print("💡 [yellow]Check your GROQ_API_KEY in .env file[/yellow]")
                sys.exit(1)
                
    except Exception as e:
        console.print(f"❌ [red]Failed to initialize chat session: {e}[/red]")
        sys.exit(1)
    
    # Welcome message
    _display_chat_welcome(ctx)
    
    # Main interactive loop
    try:
        while True:
            try:
                # Get user input with readline support
                user_input = _get_user_input(ctx).strip()
                
                if not user_input:
                    continue
                    
                # Handle special commands
                if user_input.startswith('/'):
                    if _handle_chat_command(user_input, ctx, save_history):
                        break  # Exit requested
                    continue
                
                # Process regular chat input
                ctx.command_count += 1
                _process_chat_input(user_input, ctx, model)
                
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Use /exit to quit or Ctrl+C again to force exit[/yellow]")
                try:
                    # Give user a chance to type /exit
                    continue
                except KeyboardInterrupt:
                    console.print("\n[red]Force exit requested[/red]")
                    break
                    
            except EOFError:
                # Ctrl+D pressed
                console.print("\n[yellow]EOF detected, exiting chat...[/yellow]")
                break
                
    except Exception as e:
        if ctx.debug:
            console.print_exception()
        else:
            console.print(f"❌ [red]Chat session error: {e}[/red]")
    
    # Clean exit
    _cleanup_chat_session(ctx, save_history)


@cli.command()
@click.argument("command", required=True)
@pass_context
def explain(ctx: CLIContext, command: str):
    """
    Explain what a shell command does.

    COMMAND is the shell command you want explained.

    Examples:
        chatops explain "df -h"
        chatops explain "systemctl restart nginx"
        chatops explain "docker ps -a"
    """
    try:
        # Use LangChain explanation template
        prompt = ctx.langchain.explain_command(command)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Connecting to AI...", total=None)

            # Check connection
            connected = asyncio.run(ctx.groq_client.connect())
            if not connected:
                # Fallback to offline explanation
                _offline_command_explanation(command)
                return

            progress.update(task, description="Generating explanation...")

            response = asyncio.run(
                ctx.groq_client.generate_response( # Changed from ctx.ollama_client to ctx.groq_client
                    prompt=prompt, max_tokens=300, temperature=0.2
                )
            )

        if response.success:
            console.print(
                Panel(
                    response.content.strip(),
                    title=f"Command Explanation: {command}",
                    border_style="green",
                )
            )
        else:
            # Fallback to offline explanation
            _offline_command_explanation(command)

    except Exception as e:
        if ctx.debug:
            console.print_exception()
        else:
            console.print(f"❌ [red]Error explaining command: {e}[/red]")
            _offline_command_explanation(command)


@cli.command()
@pass_context
def status(ctx: CLIContext):
    """
    Show system status and available models.
    """
    console.print(
        Panel("[bold blue]ChatOps CLI System Status[/bold blue]", border_style="blue")
    )

    # Create status table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="dim")

    # Check Groq connection
    try:
        connected = asyncio.run(ctx.groq_client.connect())
        groq_status = "✅ Connected" if connected else "❌ Disconnected"
        groq_details = (
            "Ready for AI requests" if connected else "Check GROQ_API_KEY in .env"
        )
    except:
        groq_status = "❌ Error"
        groq_details = "Groq service not available"

    table.add_row("Groq Service", groq_status, groq_details)

    # Check models
    model_count = 0
    if connected:
        try:
            models = ctx.groq_client.list_models() # Changed from ctx.ollama_client to ctx.groq_client
            model_count = len(models)
            working_models = sum(
                1 for m in models if ctx.groq_client._test_model_memory(m.name) # Changed from ctx.ollama_client to ctx.groq_client
            )
            model_details = f"{working_models}/{model_count} models can run"
        except:
            model_details = "Unable to check models"
    else:
        model_details = "Service offline"

    table.add_row(
        "AI Models",
        f"{model_count} available" if connected else "Unknown",
        model_details,
    )

    # LangChain status
    try:
        examples = ctx.langchain.get_command_examples()
        langchain_status = "✅ Ready"
        langchain_details = f"{len(examples)} command categories loaded"
    except:
        langchain_status = "❌ Error"
        langchain_details = "LangChain integration failed"

    table.add_row("LangChain", langchain_status, langchain_details)

    console.print(table)

    # Show available models if connected
    if connected and model_count > 0:
        console.print("\n[bold]Available Models:[/bold]")
        model_table = Table(show_header=True)
        model_table.add_column("Model", style="cyan")
        model_table.add_column("Size", style="yellow")
        model_table.add_column("Status", style="green")

        for model in models:
            status_emoji = (
                "✅" if ctx.groq_client._test_model_memory(model.name) else "⚠️" # Changed from ctx.ollama_client to ctx.groq_client
            )
            status_text = "Ready" if status_emoji == "✅" else "Memory Issue"
            model_table.add_row(model.name, model.size, f"{status_emoji} {status_text}")

        console.print(model_table)


@cli.command()
@pass_context
def logs(ctx: CLIContext):
    """Manage and view application logs and audit trails"""
    from rich.table import Table
    from rich.panel import Panel
    
    # Get logging system
    logging_system = ctx.logging_system
    
    # Show log file locations
    log_dir = Path(settings.logging.log_directory)
    
    table = Table(title="Log Files")
    table.add_column("File", style="cyan")
    table.add_column("Size", style="green")
    table.add_column("Last Modified", style="yellow")
    
    log_files = [
        ("chatops.log", "Application logs"),
        ("audit.log", "Audit trail"),
        ("security.log", "Security events")
    ]
    
    for filename, description in log_files:
        file_path = log_dir / filename
        if file_path.exists():
            size = file_path.stat().st_size
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            table.add_row(
                f"{filename} ({description})",
                f"{size / 1024:.1f} KB",
                mtime.strftime("%Y-%m-%d %H:%M:%S")
            )
        else:
            table.add_row(f"{filename} ({description})", "Not created", "N/A")
    
    console.print(table)
    
    # Show recent command history
    console.print("\n")
    history = logging_system.get_command_history(limit=10)
    
    if history:
        history_table = Table(title="Recent Command History")
        history_table.add_column("Time", style="cyan")
        history_table.add_column("Command", style="green")
        history_table.add_column("Risk", style="yellow")
        history_table.add_column("Status", style="magenta")
        
        for event in history[-10:]:
            status = "✅" if event.return_code == 0 else "❌"
            history_table.add_row(
                event.timestamp.strftime("%H:%M:%S"),
                event.command[:50] + "..." if len(event.command) > 50 else event.command,
                event.risk_level or "N/A",
                status
            )
        
        console.print(history_table)
    else:
        console.print(Panel("No command history available", style="yellow"))


@cli.command()
@click.option("--limit", "-l", type=int, default=50, help="Number of entries to show")
@click.option("--session", "-s", help="Filter by session ID")
@click.option("--start-time", help="Filter from start time (YYYY-MM-DD HH:MM:SS)")
@click.option("--end-time", help="Filter to end time (YYYY-MM-DD HH:MM:SS)")
@click.option("--level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "AUDIT", "SECURITY"]), help="Filter by log level")
@pass_context
def audit(ctx: CLIContext, limit: int, session: Optional[str], start_time: Optional[str], end_time: Optional[str], level: Optional[str]):
    """View audit trail and security events"""
    from rich.table import Table
    from rich.panel import Panel
    
    logging_system = ctx.logging_system
    
    # Parse time filters
    start_dt = None
    end_dt = None
    if start_time:
        try:
            start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            console.print(f"[red]Invalid start time format: {start_time}[/red]")
            return
    
    if end_time:
        try:
            end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            console.print(f"[red]Invalid end time format: {end_time}[/red]")
            return
    
    # Get audit trail
    from ..core.logging_system import LogLevel, EventType
    
    event_types = None
    log_level = None
    
    if level:
        log_level = LogLevel(level)
    
    audit_events = logging_system.get_audit_trail(
        event_types=event_types,
        start_time=start_dt,
        end_time=end_dt,
        level=log_level
    )
    
    if not audit_events:
        console.print(Panel("No audit events found for the specified criteria", style="yellow"))
        return
    
    # Display audit events
    table = Table(title=f"Audit Trail ({len(audit_events)} events)")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Level", style="yellow")
    table.add_column("Event Type", style="green")
    table.add_column("Message", style="white")
    table.add_column("Session", style="magenta")
    
    for event in audit_events[-limit:]:
        timestamp = event.get('timestamp', 'N/A')
        if timestamp != 'N/A':
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        table.add_row(
            timestamp,
            event.get('level', 'N/A'),
            event.get('event_type', 'N/A'),
            event.get('message', 'N/A')[:60] + "..." if len(event.get('message', '')) > 60 else event.get('message', 'N/A'),
            event.get('session_id', 'N/A')[:10] + "..." if len(event.get('session_id', '')) > 10 else event.get('session_id', 'N/A')
        )
    
    console.print(table)


@cli.command()
@click.option("--days", "-d", type=int, default=30, help="Number of days to retain logs")
@pass_context
def cleanup_logs(ctx: CLIContext, days: int):
    """Clean up old log files based on retention policy"""
    from rich.panel import Panel
    
    logging_system = ctx.logging_system
    
    console.print(f"[yellow]Cleaning up logs older than {days} days...[/yellow]")
    
    cleaned_count = logging_system.cleanup_old_logs(retention_days=days)
    
    if cleaned_count > 0:
        console.print(Panel(f"Cleaned up {cleaned_count} old log files", style="green"))
    else:
        console.print(Panel("No old log files found to clean up", style="blue"))


@cli.command()
@click.argument("command", required=True)
@pass_context
def preview(ctx: CLIContext, command: str):
    """Preview a command with security analysis before execution"""
    from rich.panel import Panel
    from rich.table import Table
    from rich.console import Console
    
    console = Console()
    
    # Get security system
    from ..core.security_system import get_security_system
    security_system = get_security_system()
    
    # Analyze command
    preview = security_system.analyze_command(command, "Command preview")
    
    # Display preview
    console.print(Panel(f"[bold blue]Command Preview[/bold blue]\n[green]{command}[/green]", 
                       title="🔍 Security Analysis"))
    
    # Risk assessment
    risk_color = {
        "safe": "green",
        "low": "yellow", 
        "medium": "orange",
        "high": "red",
        "critical": "red"
    }.get(preview.risk_level.value, "white")
    
    console.print(f"[bold]Risk Level:[/bold] [{risk_color}]{preview.risk_level.value.upper()}[/{risk_color}]")
    console.print(f"[bold]Operation Type:[/bold] {preview.operation_type.value}")
    console.print(f"[bold]Estimated Impact:[/bold] {preview.estimated_impact}")
    console.print(f"[bold]Requires Confirmation:[/bold] {'Yes' if preview.requires_confirmation else 'No'}")
    console.print(f"[bold]Rollback Available:[/bold] {'Yes' if preview.rollback_available else 'No'}")
    
    # Affected files
    if preview.affected_files:
        console.print(f"\n[bold]Affected Files:[/bold]")
        for file_path in preview.affected_files:
            console.print(f"  📄 {file_path}")
    
    # Affected services
    if preview.affected_services:
        console.print(f"\n[bold]Affected Services:[/bold]")
        for service in preview.affected_services:
            console.print(f"  🔧 {service}")
    
    # Safety checks
    if preview.safety_checks:
        console.print(f"\n[bold]Safety Checks:[/bold]")
        for check in preview.safety_checks:
            console.print(f"  ✅ {check}")
    
    # Warnings
    if preview.warnings:
        console.print(f"\n[bold red]Warnings:[/bold red]")
        for warning in preview.warnings:
            console.print(f"  ⚠️  {warning}")
    
    # Rollback command
    if preview.rollback_command:
        console.print(f"\n[bold]Rollback Command:[/bold]")
        console.print(f"  🔄 {preview.rollback_command}")


@cli.command()
@pass_context
def security_status(ctx: CLIContext):
    """Show security system status and configuration"""
    from rich.table import Table
    from rich.panel import Panel
    
    # Get security system
    from ..core.security_system import get_security_system
    security_system = get_security_system()
    
    # Get security report
    report = security_system.get_security_report()
    
    # Display security settings
    settings_table = Table(title="Security Settings")
    settings_table.add_column("Setting", style="cyan")
    settings_table.add_column("Value", style="green")
    
    for key, value in report["security_settings"].items():
        settings_table.add_row(key.replace("_", " ").title(), str(value))
    
    console.print(settings_table)
    
    # Display blacklist status
    blacklist_table = Table(title="Blacklist Status")
    blacklist_table.add_column("Type", style="cyan")
    blacklist_table.add_column("Count", style="green")
    
    for blacklist_type, items in report["blacklist_status"].items():
        count = len(items) if isinstance(items, list) else "N/A"
        blacklist_table.add_row(blacklist_type.title(), str(count))
    
    console.print(blacklist_table)
    
    # Display statistics
    stats_table = Table(title="Security Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")
    
    stats_table.add_row("Command History", str(report["command_history_count"]))
    stats_table.add_row("Rollback Operations", str(report["rollback_operations_count"]))
    
    console.print(stats_table)


@cli.command()
@click.option("--command", "-c", help="Command to add to blacklist")
@click.option("--reason", "-r", help="Reason for blacklisting")
@click.option("--remove", is_flag=True, help="Remove command from blacklist instead")
@pass_context
def blacklist(ctx: CLIContext, command: Optional[str], reason: Optional[str], remove: bool):
    """Manage command blacklist"""
    from rich.panel import Panel
    
    if not command:
        console.print(Panel("Please provide a command with --command option", style="red"))
        return
    
    # Get security system
    from ..core.security_system import get_security_system
    security_system = get_security_system()
    
    if remove:
        success = security_system.blacklist.remove_from_blacklist(command)
        if success:
            console.print(Panel(f"✅ Removed '{command}' from blacklist", style="green"))
        else:
            console.print(Panel(f"❌ Failed to remove '{command}' from blacklist", style="red"))
    else:
        success = security_system.blacklist.add_to_blacklist(command, reason or "User request")
        if success:
            console.print(Panel(f"✅ Added '{command}' to blacklist", style="green"))
        else:
            console.print(Panel(f"❌ Failed to add '{command}' to blacklist", style="red"))


@cli.command()
@click.argument("command_id", required=True)
@pass_context
def rollback(ctx: CLIContext, command_id: str):
    """Execute a rollback operation for a previous command"""
    from rich.panel import Panel
    import asyncio
    
    # Get security system
    from ..core.security_system import get_security_system
    security_system = get_security_system()
    
    console.print(f"[yellow]Executing rollback for command {command_id}...[/yellow]")
    
    # Execute rollback
    success = asyncio.run(security_system.execute_rollback(command_id))
    
    if success:
        console.print(Panel(f"✅ Rollback completed successfully for {command_id}", style="green"))
    else:
        console.print(Panel(f"❌ Rollback failed for {command_id}", style="red"))


@cli.command()
@click.option("--limit", "-l", type=int, default=10, help="Number of operations to show")
@pass_context
def rollback_history(ctx: CLIContext, limit: int):
    """Show rollback operation history"""
    from rich.table import Table
    
    # Get security system
    from ..core.security_system import get_security_system
    security_system = get_security_system()
    
    # Get rollback history
    history = security_system.rollback_manager.get_rollback_history(limit=limit)
    
    if not history:
        console.print("No rollback operations found.")
        return
    
    # Display history
    table = Table(title=f"Rollback History (Last {len(history)} operations)")
    table.add_column("Command ID", style="cyan")
    table.add_column("Original Command", style="green")
    table.add_column("Rollback Command", style="yellow")
    table.add_column("Timestamp", style="magenta")
    table.add_column("Status", style="white")
    
    for op in history:
        status = "✅ Success" if op.success else "❌ Failed"
        table.add_row(
            str(op.timestamp.strftime("%Y-%m-%d %H:%M:%S")),
            op.original_command[:50] + "..." if len(op.original_command) > 50 else op.original_command,
            op.rollback_command[:50] + "..." if len(op.rollback_command) > 50 else op.rollback_command,
            op.timestamp.strftime("%H:%M:%S"),
            status
        )
    
    console.print(table)


@cli.command()
@pass_context
def examples(ctx: CLIContext):
    """Show example commands and usage patterns"""
    console.print(Panel.fit(
        "[bold blue]ChatOps CLI Examples[/bold blue]\n\n"
        "[green]Basic Commands:[/green]\n"
        "  chatops ask 'check disk space'\n"
        "  chatops ask 'restart nginx service'\n"
        "  chatops ask 'show running containers'\n\n"
        "[green]Interactive Mode:[/green]\n"
        "  chatops chat\n"
        "  chatops chat --model llama3-8b-8192\n\n"
        "[green]Command Explanation:[/green]\n"
        "  chatops explain 'docker ps -a'\n"
        "  chatops explain 'kubectl get pods'\n\n"
        "[green]Plugin Management:[/green]\n"
        "  chatops plugins --list\n"
        "  chatops plugins --status\n"
        "  chatops plugins --help-plugin docker\n\n"
        "[green]Configuration:[/green]\n"
        "  chatops config --validate\n"
        "  chatops config --export-template\n"
        "  chatops config --save-profile production\n\n"
        "[green]Advanced Options:[/green]\n"
        "  chatops --verbose ask 'analyze system performance'\n"
        "  chatops --debug ask 'troubleshoot network issues'\n"
        "  chatops ask --dry-run 'delete old log files'",
        title="[bold cyan]Example Commands[/bold cyan]"
    ))


@cli.group()
@pass_context
def config(ctx: CLIContext):
    """Configuration management commands"""
    pass


@config.command()
@click.option("--format", "output_format", type=click.Choice(["json", "yaml"]), default="json", help="Output format")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@pass_context
def export(ctx: CLIContext, output_format: str, output: Optional[str]):
    """Export current configuration to file"""
    try:
        output_path = Path(output) if output else None
        settings.save_config(output_path, output_format)
        
        if output_path:
            console.print(f"✅ Configuration exported to: {output_path}")
        else:
            console.print(f"✅ Configuration exported to: chatops_config.{output_format}")
            
    except Exception as e:
        console.print(f"❌ Failed to export configuration: {e}")


@config.command()
@pass_context
def validate(ctx: CLIContext):
    """Validate current configuration"""
    issues = settings.validate_configuration()
    
    if not issues:
        console.print("✅ Configuration is valid")
        return
    
    console.print("[bold red]Configuration Issues Found:[/bold red]")
    for issue in issues:
        console.print(f"  • {issue}")


@config.command()
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@pass_context
def export_template(ctx: CLIContext, output: Optional[str]):
    """Export environment variable template"""
    try:
        output_path = Path(output) if output else None
        settings.export_env_template(output_path)
        
        if output_path:
            console.print(f"✅ Environment template exported to: {output_path}")
        else:
            console.print("✅ Environment template exported to: .env.template")
            
    except Exception as e:
        console.print(f"❌ Failed to export template: {e}")


@config.command()
@click.argument("profile_name")
@pass_context
def save_profile(ctx: CLIContext, profile_name: str):
    """Save current settings as a named profile"""
    try:
        settings.save_profile(profile_name)
        console.print(f"✅ Profile '{profile_name}' saved successfully")
    except Exception as e:
        console.print(f"❌ Failed to save profile: {e}")


@config.command()
@click.argument("profile_name")
@pass_context
def load_profile(ctx: CLIContext, profile_name: str):
    """Load a named configuration profile"""
    try:
        if settings.load_profile(profile_name):
            console.print(f"✅ Profile '{profile_name}' loaded successfully")
        else:
            console.print(f"❌ Profile '{profile_name}' not found")
    except Exception as e:
        console.print(f"❌ Failed to load profile: {e}")


@config.command()
@pass_context
def list_profiles(ctx: CLIContext):
    """List all available configuration profiles"""
    profiles = settings.list_profiles()
    
    if not profiles:
        console.print("No profiles found")
        return
    
    table = Table(title="Configuration Profiles")
    table.add_column("Profile Name", style="cyan")
    table.add_column("Current", style="green")
    
    for profile in profiles:
        current = "✓" if profile == settings.current_profile else ""
        table.add_row(profile, current)
    
    console.print(table)


@config.command()
@click.argument("profile_name")
@pass_context
def delete_profile(ctx: CLIContext, profile_name: str):
    """Delete a configuration profile"""
    try:
        if settings.delete_profile(profile_name):
            console.print(f"✅ Profile '{profile_name}' deleted successfully")
        else:
            console.print(f"❌ Profile '{profile_name}' not found")
    except Exception as e:
        console.print(f"❌ Failed to delete profile: {e}")


@config.command()
@pass_context
def show(ctx: CLIContext):
    """Show current configuration (excluding sensitive data)"""
    # Create a safe copy of settings for display
    safe_config = settings.dict(exclude={'groq': {'api_key'}, 'ollama': {'api_key'}})
    
    console.print("[bold blue]Current Configuration:[/bold blue]")
    
    # Display basic settings
    console.print(f"  Default LLM Provider: {safe_config.get('default_llm_provider', 'N/A')}")
    console.print(f"  Current Profile: {safe_config.get('current_profile', 'N/A')}")
    console.print(f"  Debug Mode: {safe_config.get('debug_mode', False)}")
    console.print(f"  Verbose Mode: {safe_config.get('verbose_mode', False)}")
    
    # Display provider configurations
    if 'groq' in safe_config:
        groq_config = safe_config['groq']
        console.print(f"  Groq Model: {groq_config.get('model', 'N/A')}")
        console.print(f"  Groq Enabled: {groq_config.get('enabled', False)}")
    
    if 'ollama' in safe_config:
        ollama_config = safe_config['ollama']
        console.print(f"  Ollama Model: {ollama_config.get('model', 'N/A')}")
        console.print(f"  Ollama Base URL: {ollama_config.get('base_url', 'N/A')}")
        console.print(f"  Ollama Enabled: {ollama_config.get('enabled', False)}")
    
    # Display available profiles
    profiles = settings.list_profiles()
    if profiles:
        console.print(f"  Available Profiles: {', '.join(profiles)}")


@cli.command()
@click.option("--list", "list_plugins", is_flag=True, help="List all available plugins")
@click.option("--status", is_flag=True, help="Show plugin status and health")
@click.option("--help-plugin", help="Show help for a specific plugin")
@click.option("--reload", help="Reload a specific plugin")
@pass_context
def plugins(
    ctx: CLIContext,
    list_plugins: bool,
    status: bool,
    help_plugin: Optional[str],
    reload: Optional[str],
):
    """
    Manage and view information about plugins.

    Examples:
        chatops plugins --list
        chatops plugins --status
        chatops plugins --help-plugin system
        chatops plugins --reload system
    """
    try:
        # Initialize plugin manager if needed
        if not ctx.plugin_manager._plugins:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Initializing plugins...", total=None)
                success = asyncio.run(
                    ctx.plugin_manager.initialize({"hot_reload": ctx.debug})
                )
                if not success:
                    console.print("❌ [red]Failed to initialize plugin system[/red]")
                    return

        # List plugins
        if list_plugins:
            plugins_table = Table(title="🔌 Available Plugins")
            plugins_table.add_column("Name", style="cyan", no_wrap=True)
            plugins_table.add_column("Version", style="magenta")
            plugins_table.add_column("Status", style="green")
            plugins_table.add_column("Capabilities", style="blue")
            plugins_table.add_column("Description", style="white")

            all_plugins = ctx.plugin_manager.get_all_plugins()

            for name, plugin in all_plugins.items():
                info = ctx.plugin_manager.get_plugin_info(name)
                status_emoji = "✅" if info.status.value == "active" else "❌"
                capabilities = ", ".join([cap.value for cap in plugin.capabilities])

                plugins_table.add_row(
                    name,
                    plugin.metadata.version,
                    f"{status_emoji} {info.status.value}",
                    capabilities,
                    plugin.metadata.description,
                )

            console.print(plugins_table)
            console.print(f"\n📊 Total plugins loaded: {len(all_plugins)}")
            return

        # Show plugin status
        if status:
            status_info = ctx.plugin_manager.get_plugin_status()

            for plugin_name, info in status_info.items():
                status_color = "green" if info["status"] == "active" else "red"
                console.print(f"\n�� [bold]{plugin_name}[/bold] v{info['version']}")
                console.print(
                    f"   Status: [{status_color}]{info['status']}[/{status_color}]"
                )
                console.print(f"   Capabilities: {', '.join(info['capabilities'])}")
                if info.get("load_time"):
                    console.print(f"   Loaded: {info['load_time']}")
                if info.get("error_message"):
                    console.print(f"   Error: [red]{info['error_message']}[/red]")
            return

        # Show help for specific plugin
        if help_plugin:
            plugin = ctx.plugin_manager.get_plugin(help_plugin)
            if plugin:
                help_text = plugin.get_help()
                console.print(
                    Panel(
                        help_text,
                        title=f"Plugin Help: {plugin.metadata.name}",
                        border_style="blue",
                    )
                )
            else:
                console.print(f"❌ [red]Plugin '{help_plugin}' not found[/red]")
            return

        # Reload specific plugin
        if reload:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(f"Reloading plugin '{reload}'...", total=None)
                success = asyncio.run(ctx.plugin_manager.reload_plugin(reload))

                if success:
                    console.print(
                        f"✅ [green]Plugin '{reload}' reloaded successfully[/green]"
                    )
                else:
                    console.print(f"❌ [red]Failed to reload plugin '{reload}'[/red]")
            return

        # Default: show brief plugin info
        all_plugins = ctx.plugin_manager.get_all_plugins()
        if all_plugins:
            console.print("🔌 [bold]Plugin System Active[/bold]")
            console.print(f"Loaded plugins: {', '.join(all_plugins.keys())}")
            console.print("\nUse --list for detailed information")
        else:
            console.print("⚠️ [yellow]No plugins loaded[/yellow]")

    except Exception as e:
        if ctx.debug:
            console.print(f"[red]Plugin command error: {e}[/red]")
            import traceback

            console.print(traceback.format_exc())
        else:
            console.print(f"❌ [red]Plugin operation failed: {e}[/red]")


def _display_command(command: DevOpsCommand, dry_run: bool, verbose: bool):
    """Display command information in a formatted way"""

    # Risk level styling
    risk_colors = {
        RiskLevel.SAFE: "green",
        RiskLevel.LOW: "yellow",
        RiskLevel.MEDIUM: "orange3",
        RiskLevel.HIGH: "red",
        RiskLevel.CRITICAL: "bold red",
    }

    risk_color = risk_colors.get(command.risk_level, "white")

    # Create info panel
    info_lines = [
        f"[bold]Command:[/bold] [cyan]{command.command}[/cyan]",
        f"[bold]Description:[/bold] {command.description}",
        f"[bold]Type:[/bold] {command.command_type.value}",
        f"[bold]Risk Level:[/bold] [{risk_color}]{command.risk_level.value}[/{risk_color}]",
        f"[bold]Duration:[/bold] {command.estimated_duration}",
    ]

    if command.requires_sudo:
        info_lines.append("[bold]Privileges:[/bold] [red]Requires sudo[/red]")

    if command.prerequisites:
        prereqs = ", ".join(command.prerequisites)
        info_lines.append(f"[bold]Prerequisites:[/bold] {prereqs}")

    if command.alternative_commands and verbose:
        alts = ", ".join(command.alternative_commands)
        info_lines.append(f"[bold]Alternatives:[/bold] {alts}")

    panel_title = "Generated Command (Dry Run)" if dry_run else "Generated Command"
    console.print(
        Panel("\n".join(info_lines), title=panel_title, border_style=risk_color)
    )


async def _execute_command(command: DevOpsCommand, ctx: CLIContext, verbose: bool):
    """Handle command execution with safety checks using CommandExecutor"""
    
    # Create execution context
    execution_context = ExecutionContext(
        working_directory=Path.cwd(), 
        environment_vars={},
        timeout_seconds=60,
        dry_run=False,
        interactive=True,
        log_execution=True
    )
    
    # User confirmation callback
    async def confirm_execution(dev_ops_cmd: DevOpsCommand) -> bool:
        console.print(
            f"\n⚠️ [yellow]This command has {dev_ops_cmd.risk_level.value} risk level[/yellow]"
        )
        console.print(f"[bold]Command:[/bold] [cyan]{dev_ops_cmd.command}[/cyan]")
        console.print(f"[bold]Description:[/bold] {dev_ops_cmd.description}")
        
        return click.confirm("\nDo you want to proceed with execution?")
    
    try:
        # Execute command using CommandExecutor (without nested Progress)
        console.print("[dim]Executing command...[/dim]")
        
        result = await ctx.command_executor.execute_command(
            command,
            execution_context,
            confirm_execution
        )
        
        # Display results
        _display_execution_result(result, verbose)
        
    except Exception as e:
        console.print(f"❌ [red]Execution error: {e}[/red]")
        if verbose:
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")


def _display_execution_result(result, verbose: bool):
    """Display command execution results"""
    status_colors = {
        ExecutionStatus.COMPLETED: "green",
        ExecutionStatus.FAILED: "red", 
        ExecutionStatus.CANCELLED: "yellow",
        ExecutionStatus.TIMEOUT: "orange3"
    }
    
    status_color = status_colors.get(result.status, "white")
    
    # Status line
    console.print(f"\n[{status_color}]● {result.status.value.upper()}[/{status_color}] "
                 f"({result.execution_time:.2f}s) [dim]- Return code: {result.return_code}[/dim]")
    
    # Output
    if result.stdout.strip():
        console.print(f"\n[bold]Output:[/bold]")
        console.print(result.stdout.strip())
    
    if result.stderr.strip():
        console.print(f"\n[bold]Error Output:[/bold]")
        console.print(f"[red]{result.stderr.strip()}[/red]")
    
    if result.error_message and verbose:
        console.print(f"\n[bold]Error Details:[/bold] [red]{result.error_message}[/red]")
    
    if result.user_cancelled:
        console.print("⏹️ [yellow]Command execution was cancelled by user[/yellow]")


def _offline_command_explanation(command: str):
    """Provide basic offline command explanation"""

    # Basic command explanations (fallback when AI is unavailable)
    explanations = {
        "df": "Shows disk space usage for mounted filesystems",
        "df -h": "Shows disk space usage in human-readable format (KB, MB, GB)",
        "free": "Displays memory usage information",
        "free -h": "Displays memory usage in human-readable format",
        "ps": "Shows running processes",
        "ps aux": "Shows all running processes with detailed information",
        "ls": "Lists files and directories",
        "ls -la": "Lists all files including hidden ones with detailed information",
        "top": "Shows real-time process activity",
        "htop": "Enhanced version of top with better interface",
        "ping": "Tests network connectivity to a host",
        "wget": "Downloads files from web servers",
        "curl": "Transfers data from or to servers",
        "systemctl": "Controls systemd services",
        "docker": "Manages Docker containers and images",
    }

    # Extract base command
    base_cmd = command.split()[0]

    explanation = explanations.get(command) or explanations.get(base_cmd)

    if explanation:
        console.print(
            Panel(
                explanation, title=f"Basic Explanation: {command}", border_style="dim"
            )
        )
        console.print(
            "[dim]💡 For detailed explanations, ensure Ollama is running[/dim]"
        )
    else:
        console.print(
            Panel(
                f"No offline explanation available for '{command}'.\nTry starting Ollama for AI-powered explanations.",
                title="Explanation Not Available",
                border_style="red",
            )
        )


# Interactive Chat Helper Functions

def _display_chat_welcome(ctx: CLIContext) -> None:
    """Display welcome message for interactive chat mode."""
    welcome_panel = Panel(
        "[bold green]🤖 ChatOps Interactive Mode[/bold green]\n\n"
        "Type your requests naturally and I'll help you with DevOps tasks.\n"
        "Use [cyan]/help[/cyan] to see available commands.\n"
        "Use [cyan]/exit[/cyan] to quit when done.\n\n"
        f"[dim]Session started: {ctx.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
        title="Welcome to Interactive Chat",
        border_style="green"
    )
    console.print(welcome_panel)
    console.print()


def _get_user_input(ctx: CLIContext) -> str:
    """Get user input with prompt and readline support."""
    prompt_text = f"[bold cyan]ChatOps[/bold cyan] [{ctx.command_count + 1}]> "
    try:
        return Prompt.ask(prompt_text, default="", show_default=False)
    except (EOFError, KeyboardInterrupt):
        raise


def _handle_chat_command(command: str, ctx: CLIContext, save_history: bool) -> bool:
    """Handle special chat commands. Returns True if exit was requested."""
    command = command.lower().strip()

    if command == "/exit" or command == "/quit":
        console.print("[yellow]Exiting chat mode...[/yellow]")
        return True

    elif command == "/help":
        _display_chat_help()

    elif command == "/history":
        _display_chat_history(ctx)

    elif command == "/clear":
        ctx.chat_history.clear()
        console.print("[green]Chat history cleared[/green]")

    elif command == "/context":
        _display_session_context(ctx)

    elif command == "/save":
        _save_chat_history(ctx)

    else:
        console.print(f"[red]Unknown command: {command}[/red]")
        console.print("[dim]Type /help to see available commands[/dim]")

    return False


def _display_chat_help() -> None:
    """Display help for chat commands."""
    help_table = Table(title="Chat Commands", show_header=True, header_style="bold magenta")
    help_table.add_column("Command", style="cyan", no_wrap=True)
    help_table.add_column("Description", style="dim")
    
    commands = [
        ("/help", "Show this help message"),
        ("/history", "Show conversation history"),
        ("/clear", "Clear conversation history"),
        ("/context", "Show current session context"),
        ("/save", "Save current conversation to file"),
        ("/exit", "Exit chat mode"),
    ]
    
    for cmd, desc in commands:
        help_table.add_row(cmd, desc)
    
    console.print(help_table)
    console.print("\n[dim]You can also just type natural language requests for DevOps tasks.[/dim]")


def _display_chat_history(ctx: CLIContext) -> None:
    """Display the current chat history."""
    if not ctx.chat_history:
        console.print("[yellow]No chat history yet[/yellow]")
        return
    
    console.print(f"\n[bold]Chat History[/bold] (last {len(ctx.chat_history)} interactions)")
    console.print("=" * 60)
    
    for i, entry in enumerate(ctx.chat_history, 1):
        timestamp = entry.get('timestamp', 'Unknown')
        console.print(f"\n[dim]{i}. {timestamp}[/dim]")
        console.print(f"[cyan]You:[/cyan] {entry.get('user_input', 'N/A')}")
        
        if 'command_generated' in entry:
            console.print(f"[green]Generated:[/green] {entry['command_generated']}")
        
        if 'ai_response' in entry:
            console.print(f"[blue]AI:[/blue] {entry['ai_response'][:100]}...")
        
        if 'plugin_used' in entry:
            console.print(f"[magenta]Plugin:[/magenta] {entry['plugin_used']}")
    
    console.print("=" * 60)


def _display_session_context(ctx: CLIContext) -> None:
    """Display current session context and statistics."""
    context_panel = Panel(
        f"[bold]Session Context:[/bold] {ctx.session_context or 'None set'}\n"
        f"[bold]Started:[/bold] {ctx.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"[bold]Commands Processed:[/bold] {ctx.command_count}\n"
        f"[bold]History Length:[/bold] {len(ctx.chat_history)} interactions\n"
        f"[bold]Session Duration:[/bold] {datetime.now() - ctx.session_start_time}",
        title="Session Information",
        border_style="blue"
    )
    console.print(context_panel)


def _save_chat_history(ctx: CLIContext) -> None:
    """Save chat history to a file."""
    if not ctx.chat_history:
        console.print("[yellow]No chat history to save[/yellow]")
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chatops_history_{timestamp}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"ChatOps Interactive Session History\n")
            f.write(f"Session started: {ctx.session_start_time}\n")
            f.write(f"Commands processed: {ctx.command_count}\n")
            f.write(f"Session context: {ctx.session_context or 'None'}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, entry in enumerate(ctx.chat_history, 1):
                f.write(f"[{i}] {entry.get('timestamp', 'Unknown')}\n")
                f.write(f"User: {entry.get('user_input', 'N/A')}\n")
                
                if 'command_generated' in entry:
                    f.write(f"Generated Command: {entry['command_generated']}\n")
                
                if 'ai_response' in entry:
                    f.write(f"AI Response: {entry['ai_response']}\n")
                
                if 'plugin_used' in entry:
                    f.write(f"Plugin Used: {entry['plugin_used']}\n")
                
                f.write("-" * 40 + "\n\n")
        
        console.print(f"[green]Chat history saved to: {filename}[/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to save chat history: {e}[/red]")


def _process_chat_input(user_input: str, ctx: CLIContext, model: Optional[str]) -> None:
    """Process a regular chat input (not a special command)."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Add to history
    history_entry = {
        'timestamp': timestamp,
        'user_input': user_input,
    }
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            
            # Build context for this request
            context_prompt = _build_chat_context(ctx, user_input)
            
            # Try plugin system first
            task = progress.add_task("Finding plugin handler...", total=None)
            
            plugin_context = {
                "user_request": user_input,
                "additional_context": ctx.session_context,
                "chat_history": ctx.chat_history[-5:],  # Last 5 interactions for context
                "explain_mode": False,
                "dry_run": False,
            }

            handler_plugin = asyncio.run(
                ctx.plugin_manager.find_handler(user_input, plugin_context)
            )

            if handler_plugin:
                progress.update(task, description=f"Using {handler_plugin.metadata.name} plugin...")
                
                # Special handling for LLM plugin - call process_llm_request directly
                if handler_plugin.metadata.name == "llm" and hasattr(handler_plugin, 'process_llm_request'):
                    try:
                        ai_response = asyncio.run(handler_plugin.process_llm_request(user_input, plugin_context))
                        history_entry['plugin_used'] = handler_plugin.metadata.name
                        history_entry['ai_response'] = ai_response

                        # Display AI response directly
                        console.print(Panel(
                            ai_response,
                            title="🤖 AI Response",
                            border_style="blue"
                        ))

                    except Exception as e:
                        console.print(f"❌ [red]AI processing failed: {e}[/red]")
                        history_entry['ai_error'] = str(e)
                        _fallback_to_ai(context_prompt, ctx, history_entry, model)

                else:
                    # Regular plugin handling for command generation
                    command = asyncio.run(
                        handler_plugin.generate_command(user_input, plugin_context)
                    )

                    if command:
                        history_entry['plugin_used'] = handler_plugin.metadata.name
                        history_entry['command_generated'] = command.command

                        # Validate and display command
                        if asyncio.run(handler_plugin.validate_command(command, plugin_context)):
                            _display_command(command, False, ctx.verbose)

                            # Ask for confirmation in chat mode
                            if _confirm_command_execution():
                                asyncio.run(_execute_command(command, ctx, ctx.verbose))
                                history_entry['executed'] = True
                            else:
                                history_entry['executed'] = False
                                console.print("[yellow]Command execution skipped[/yellow]")
                        else:
                            console.print("⚠️ [yellow]Plugin command validation failed, falling back to AI[/yellow]")
                            _fallback_to_ai(context_prompt, ctx, history_entry, model)
                    else:
                        console.print("⚠️ [yellow]Plugin couldn't generate command, falling back to AI[/yellow]")
                        _fallback_to_ai(context_prompt, ctx, history_entry, model)
            else:
                # No plugin found, use AI
                if ctx.verbose:
                    console.print("[dim]No plugin found, using AI...[/dim]")
                _fallback_to_ai(context_prompt, ctx, history_entry, model)

    except Exception as e:
        console.print(f"❌ [red]Error processing request: {e}[/red]")
        if ctx.debug:
            console.print_exception()
        history_entry['error'] = str(e)
    
    # Add to chat history
    ctx.chat_history.append(history_entry)


def _build_chat_context(ctx: CLIContext, current_input: str) -> str:
    """Build context prompt including chat history."""
    context_parts = []
    
    if ctx.session_context:
        context_parts.append(f"Session Context: {ctx.session_context}")
    
    if ctx.chat_history:
        context_parts.append("Recent conversation:")
        # Include last 3 interactions for context
        for entry in ctx.chat_history[-3:]:
            context_parts.append(f"- User asked: {entry.get('user_input', 'N/A')}")
            if 'command_generated' in entry:
                context_parts.append(f"  Generated: {entry['command_generated']}")
    
    context_parts.append(f"Current request: {current_input}")
    
    return "\n".join(context_parts)


def _confirm_command_execution() -> bool:
    """Ask user to confirm command execution in chat mode."""
    try:
        confirm = Prompt.ask(
            "[yellow]Execute this command?[/yellow]", 
            choices=["y", "n", "yes", "no"], 
            default="y",
            show_choices=False
        )
        return confirm.lower() in ["y", "yes"]
    except (EOFError, KeyboardInterrupt):
        return False


def _fallback_to_ai(context_prompt: str, ctx: CLIContext, history_entry: dict[str, Any], model: Optional[str]) -> None:
    """Fallback to AI when plugins can't handle the request."""
    try:
        # Generate prompt using LangChain with chat context
        prompt = ctx.langchain.generate_prompt(context_prompt)
        
        # Get AI response
        response = asyncio.run(ctx.groq_client.chat(prompt, model))
        
        if response and response.content:
            history_entry['ai_response'] = response.content
            
            # Try to parse as command
            try:
                command = ctx.langchain.parse_llm_response(response.content)
                
                # Check if we got a valid command (not just a fallback)
                if command and command.command and command.command != "command":
                    history_entry['command_generated'] = command.command
                    
                    # Display and potentially execute
                    _display_command(command, False, ctx.verbose)
                    
                    if _confirm_command_execution():
                        asyncio.run(_execute_command(command, ctx, ctx.verbose))
                        history_entry['executed'] = True
                    else:
                        history_entry['executed'] = False
                        console.print("[yellow]Command execution skipped[/yellow]")
                else:
                    # Invalid command, treat as explanation
                    raise ValueError("Invalid command structure")
                    
            except Exception as e:
                # If not a command, just show the AI response
                console.print(Panel(
                    response.content,
                    title="🤖 AI Response",
                    border_style="blue"
                ))
        else:
            console.print("❌ [red]No response from AI[/red]")
            
    except Exception as e:
        console.print(f"❌ [red]AI processing failed: {e}[/red]")
        history_entry['ai_error'] = str(e)


def _cleanup_chat_session(ctx: CLIContext, save_history: bool) -> None:
    """Clean up and optionally save chat session."""
    session_duration = datetime.now() - ctx.session_start_time
    
    # Display session summary
    summary_panel = Panel(
        f"[bold]Session Summary[/bold]\n\n"
        f"Duration: {session_duration}\n"
        f"Commands processed: {ctx.command_count}\n"
        f"Interactions: {len(ctx.chat_history)}\n"
        f"Context: {ctx.session_context or 'None set'}",
        title="Chat Session Complete",
        border_style="green"
    )
    console.print(summary_panel)
    
    # Auto-save if requested
    if save_history and ctx.chat_history:
        _save_chat_history(ctx)
    
    # Reset session state
    ctx.chat_history.clear()
    ctx.session_context = ""
    ctx.session_start_time = None
    ctx.command_count = 0


if __name__ == "__main__":
    cli()
