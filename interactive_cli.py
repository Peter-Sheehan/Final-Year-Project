# interactive_cli.py

import click
from typing import Optional
import os
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from getpass import getpass
from github import Github

from main import DockerfileOptimiser, get_config_dir, DOCKER_AVAILABLE
from dotenv import set_key


console = Console()

def get_github_token() -> str:
    """Get GitHub token from environment or prompt user."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        console.print("\n[yellow]GitHub Personal Access Token not found in environment or .env file.[/yellow]")
        token = getpass("Enter your GitHub Personal Access Token (input will be hidden): ")
        if not token:
            raise ValueError("GitHub token is required for repository analysis")
        
        try:
            config_dir = get_config_dir()
            env_path = config_dir / ".env"
            set_key(dotenv_path=env_path, key_to_set="GITHUB_TOKEN", value_to_set=token)
            console.print(f"[green]Saved GitHub token to {env_path}[/green]")
            os.environ["GITHUB_TOKEN"] = token 
        except Exception as e:
            console.print(f"[red]Error saving GitHub token to {env_path}: {e}[/red]")
        
        try:
            g = Github(token)
            user = g.get_user().login
            console.print(f"[green]✓ Successfully authenticated as GitHub user: {user}[/green]")
        except Exception as e:
            raise ValueError(f"GitHub authentication failed: {str(e)}")
    
    return token

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Interactive CLI for Dockerfile analysis and optimisation"""
    if ctx.invoked_subcommand is None:
        ctx.invoke(analyse)

@cli.command()
def analyse():
    """Analyse a Dockerfile for optimisation opportunities"""
    try:
        optimiser = DockerfileOptimiser()
        
        analysis_type = click.prompt(
            "\nChoose analysis type:\n1. Local Dockerfile\n2. GitHub Repository\n3. Quit\nEnter choice (1/2/3)",
            type=click.Choice(['1', '2', '3'], case_sensitive=False),
            show_choices=False
        )
        if analysis_type.upper() == '3':
            console.print("[blue]Goodbye![/blue]")
            return
        
        if DOCKER_AVAILABLE:
            if Confirm.ask("\nAttempt to build images for size comparison? (Requires Docker to be running)", default=True, show_default=False):
                optimiser.attempt_docker_builds = True
                console.print("[cyan]Docker image builds enabled. Will attempt to connect to Docker daemon when build analysis is performed.[/cyan]")
            else:
                optimiser.attempt_docker_builds = False
                console.print("[yellow]Docker image build analysis will be skipped.[/yellow]")
        else:
            console.print("[yellow]Docker Python library not found. Skipping Docker image build analysis automatically.[/yellow]")
            optimiser.attempt_docker_builds = False
        
        if analysis_type == '2':
            repo_url = click.prompt("\nEnter the GitHub repository URL")
            if not repo_url:
                console.print("[red]Error: GitHub repository URL is required[/red]")
                return
                
            token = get_github_token()
            if token:
                optimiser.github_token = token
                console.print("[blue]Analysing GitHub repository...[/blue]")
                
                analysis = optimiser.analyse_from_github(repo_url)
                
                optimiser.print_analysis(analysis)
                
                if Confirm.ask("\nWould you like to create a Pull Request with these changes?"):
                    pr_url = optimiser.create_pull_request(repo_url, analysis)
                    console.print(f"\n[green]✓ Pull Request created successfully![/green]")
                    console.print(f"[blue]View it here: {pr_url}[/blue]")
            else:
                console.print("[red]Error: GitHub token is required for repository analysis[/red]")
                return
        else:
            while True:
                dockerfile_path = click.prompt("\nEnter the path to your local Dockerfile")
                if os.path.exists(dockerfile_path):
                    break
                console.print(f"[red]Error: File not found at {dockerfile_path}[/red]")
                if not click.confirm("Would you like to try another path?"):
                    return
            
            console.print("[blue]Analysing local Dockerfile...[/blue]")
            analysis = optimiser.analyse_dockerfile(dockerfile_path)
            optimiser.print_analysis(analysis)
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        return

if __name__ == "__main__":
    cli()