#!/usr/bin/env python3
"""
Main CLI interface for ChatOps CLI

This module provides the primary command-line interface using Click framework,
with command groups, global options, and integration with our core components.
"""

import sys
import logging
import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.ollama_client import OllamaClient, OllamaResponse
from ..core.langchain_integration import LangChainIntegration, DevOpsCommand, RiskLevel


# Global console for rich output
console = Console()


# Global context for CLI state
class CLIContext:
    def __init__(self):
        self.debug = False
        self.verbose = False
        self.config_file = None
        self.ollama_client = None
        self.langchain = None

    def setup_logging(self):
        """Setup logging based on debug/verbose flags"""
        level = (
            logging.DEBUG
            if self.debug
            else (logging.INFO if self.verbose else logging.WARNING)
        )
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
    ctx.ollama_client = OllamaClient()
    ctx.langchain = LangChainIntegration()

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
        # Check Ollama connection first
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Connecting to Ollama...", total=None)

            connected = asyncio.run(ctx.ollama_client.connect())
            if not connected:
                console.print("❌ [red]Failed to connect to Ollama service[/red]")
                console.print(
                    "💡 [yellow]Make sure Ollama is running: ollama serve[/yellow]"
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

            response = asyncio.run(
                ctx.ollama_client.generate_response(
                    prompt=prompt,
                    model=model,
                    max_tokens=200 if explain else 100,
                    temperature=0.1,
                )
            )

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
                _execute_command(command, ctx.verbose)

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
            connected = asyncio.run(ctx.ollama_client.connect())
            if not connected:
                # Fallback to offline explanation
                _offline_command_explanation(command)
                return

            progress.update(task, description="Generating explanation...")

            response = asyncio.run(
                ctx.ollama_client.generate_response(
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

    # Check Ollama connection
    try:
        connected = asyncio.run(ctx.ollama_client.connect())
        ollama_status = "✅ Connected" if connected else "❌ Disconnected"
        ollama_details = (
            "Ready for AI requests" if connected else "Run 'ollama serve' to start"
        )
    except:
        ollama_status = "❌ Error"
        ollama_details = "Ollama service not available"

    table.add_row("Ollama Service", ollama_status, ollama_details)

    # Check models
    if connected:
        try:
            models = ctx.ollama_client.list_models()
            model_count = len(models)
            working_models = sum(
                1 for m in models if ctx.ollama_client._test_model_memory(m.name)
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
                "✅" if ctx.ollama_client._test_model_memory(model.name) else "⚠️"
            )
            status_text = "Ready" if status_emoji == "✅" else "Memory Issue"
            model_table.add_row(model.name, model.size, f"{status_emoji} {status_text}")

        console.print(model_table)


@cli.command()
@pass_context
def examples(ctx: CLIContext):
    """
    Show example commands and usage patterns.
    """
    console.print(
        Panel("[bold green]ChatOps CLI Examples[/bold green]", border_style="green")
    )

    # Get examples from LangChain integration
    examples = ctx.langchain.get_command_examples()

    for category, commands in examples.items():
        console.print(f"\n[bold cyan]{category.replace('_', ' ').title()}[/bold cyan]")

        for cmd in commands:
            console.print(
                f"  [dim]Ask:[/dim] [yellow]chatops ask \"{cmd['input']}\"[/yellow]"
            )
            console.print(f"  [dim]Gets:[/dim] [green]{cmd['command']}[/green]")
            console.print(f"  [dim]Does:[/dim] {cmd['description']}")
            console.print()


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


def _execute_command(command: DevOpsCommand, verbose: bool):
    """Handle command execution with safety checks"""

    # Safety confirmation for risky commands
    if command.requires_confirmation or command.risk_level in [
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    ]:
        console.print(
            f"\n⚠️ [yellow]This command has {command.risk_level.value} risk level[/yellow]"
        )

        if not click.confirm("Do you want to proceed?"):
            console.print("⏹️ [yellow]Command execution cancelled[/yellow]")
            return

    # Note: Actual command execution will be implemented in Task 8
    console.print(
        "\n[dim]Note: Command execution will be implemented in Task 8 (Command Executor Service)[/dim]"
    )
    console.print(f"[dim]Would execute: {command.command}[/dim]")


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


if __name__ == "__main__":
    cli()
