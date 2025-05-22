import os
import re
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import csv
from datetime import datetime
from enum import Enum, auto
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
import openai
from dotenv import load_dotenv, set_key
import click
from github import Github
import tempfile
import shutil
import time
import fnmatch
import yaml
from webscraper import update_rules
import platform  # Import platform module

# Import from the linter files
from dockerfile_linter import DockerfileLinter, LinterIssue

@dataclass
class Analysis:
    issues: List[LinterIssue]
    suggestions: List[str]
    score: float
    original_size: int
    optimized_size: Optional[int] = None
    layer_count: Optional[int] = None
    optimized_layer_count: Optional[int] = None
    optimized_content: Optional[str] = None  # for the extracted Dockerfile
    explanation: Optional[str] = None        # for AI's explanation
    builds_attempted: bool = False # True if user opted-in and docker lib is available

class VersionMatch(Enum):
    NO_MATCH = auto()
    EXACT_STRING_MATCH = auto()
    WILDCARD_PATTERN_MATCH = auto()
    # Could also add: NO_CATALOG_ENTRY_FOR_PACKAGE, NO_CATALOG_ENTRY_FOR_DISTRO
    # For now, these will result in NO_MATCH

class DockerfileOptimizer:
    def __init__(self):
        self.console = Console()
        self.config_dir = get_config_dir() # Get application configuration directory
        self.docker_python_lib_available = DOCKER_AVAILABLE # Stores if 'docker' lib was imported
        self.client = None # initialised by _ensure_docker_client
        self.docker_daemon_connected = False # Tracks if self.client is valid and connected
        self.attempt_docker_builds = False # User's choice to attempt builds (set by CLI)
        
        # Load API keys and tokens from .env file in config dir
        env_path = self.config_dir / ".env"
        load_dotenv(dotenv_path=env_path)
        openai.api_key = os.getenv("OPENAI_API_KEY")

        if openai.api_key: # If the key was found in the environment
            # Strip any leading/trailing whitespace (including newlines) from the API key
            openai.api_key = openai.api_key.strip()
            
        self.github_token = os.getenv("GITHUB_TOKEN") 

        # Check if the APi key is not found
        if not openai.api_key:
            self.console.print(f"[yellow]Warning: OpenAI API key not found in {env_path} or environment variables.[/yellow]")
            # Prompt the user for the OpenAI API key
            api_key_input = click.prompt("Enter your OpenAI API key", hide_input=True)
            openai.api_key = api_key_input.strip() # Also strip input from prompt
            # Save the entered key to the .env file
            try:
                # Use set_key which handles file creation/update
                set_key(dotenv_path=env_path, key_to_set="OPENAI_API_KEY", value_to_set=openai.api_key)
                self.console.print(f"[green]Saved API key to {env_path}[/green]")
            except Exception as e:
                self.console.print(f"[red]Error saving API key to {env_path}: {e}[/red]")

            
        # Define path for best practices JSON in config dir
        self.best_practices_path = self.config_dir / "docker_best_practices.json"
        self.best_practices_text = self._load_best_practices_from_json(self.best_practices_path)
        
        # Determine the directory of the current script
        script_dir = Path(__file__).resolve().parent

        # Construct the path to rules.json relative to the script's directory
        rules_file_path = script_dir / 'Rules' / 'rules.json'

        # Initialise the linter with the correct path
        self.linter = DockerfileLinter(rules_path=str(rules_file_path))

        # Load package catalog for distro-based pin validation
        catalog_path = script_dir / 'Rules' / 'package_catalog.yaml'  ## test does this work ? !!

        try:
            self.package_catalog = yaml.safe_load(open(catalog_path, 'r'))
        except FileNotFoundError:
            self.console.print(f"[yellow]Warning: package catalog not found at {catalog_path}[/yellow]")
            self.package_catalog = {}


    def _ensure_docker_client(self): # Boolean: 
        """
        Ensures Docker client is running and connected if builds are attempted and library is available.
        
        Manages connection attempts and warnings.
        Boolean:
        Returns True if client is ready for use, False otherwise.
        """
        if not self.attempt_docker_builds:
            # User opted out, no console message needed here as CLI handles it.
            return False

        if not self.docker_python_lib_available:
            self.console.print("[yellow]Warning: Docker Python library not installed. Cannot perform Docker builds.[/yellow]")
            return False

        # If already connected and client is valid
        if self.client and self.docker_daemon_connected:
            return True

        # If client exists but previous connection attempt failed
        if self.client and not self.docker_daemon_connected:
            self.console.print("[yellow]Skipping Docker operation: previous connection attempt to Docker daemon failed.[/yellow]")
            return False

        # First attempt to connect (or re-attempt if client is None but previous attempt failed)
        try:
            self.console.print("[cyan]Attempting to connect to Docker daemon...[/cyan]")
            self.console.print("[bold yellow]Warning: This operation requires Docker Desktop (or your Docker daemon) to be running. If it's not, this step will fail or be skipped.[/bold yellow]")
            # Add a timeout for responsiveness, e.g., 10 seconds
            self.client = docker.from_env(timeout=10) 
            
            # Test connection with ping
            if self.client.ping(): # ping() returns True on success, raises APIError on failure
                self.console.print("[green]Successfully connected and pinged Docker daemon.[/green]")
                self.docker_daemon_connected = True
                return True
            else:
                # This case should ideally not be reached if ping() raises an error on failure.
                self.console.print("[red]Connected to Docker daemon but ping failed. Assuming daemon is not ready.[/red]")
                self.docker_daemon_connected = False
                self.client = None # Reset client
                return False

        except docker.errors.DockerException as e: # Catches APIError from ping, connection errors etc.
            self.console.print(f"[red]Failed to connect to Docker daemon (is Docker Desktop/service running?): {e}[/red]")
            self.docker_daemon_connected = False
            self.client = None # Reset client
            return False
        except Exception as e: # Catch other potential errors (e.g. unexpected timeout behavior if not DockerException)
            self.console.print(f"[red]An unexpected error occurred while trying to connect to Docker daemon: {e}[/red]")
            self.docker_daemon_connected = False
            self.client = None # Reset client
            return False


    def _load_best_practices_from_json(self, json_path: Path):  #returns formatted best practices as a string
        """Load best practices from a JSON file (prompt to fetch if missing)."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                practices = json.load(f)
            formatted_practices = "\n".join([
                f"- **{practice['title']}**: {practice['description']}"
                for practice in practices
            ])
            return formatted_practices
        
        except FileNotFoundError:
            # JSON missing: ask the user if they want to fetch the latest best practices
            self.console.print(f"[yellow]Warning: Best practices file not found at {json_path}[/yellow]")
            if click.confirm("Would you like to fetch the latest Docker best practices from the web?", default=True):
                from webscraper import update_rules
                # Pass the config directory to the update function
                success = update_rules(self.config_dir)
                if success:
                    self.console.print("[green]Fetched and saved Docker best practices![/green]")
                    try:
                        # Use self.best_practices_path directly, as json_path seems unreliable here
                        reload_path = self.best_practices_path
                        # Add a check to see if the file exists at the expected path RIGHT before opening
                        if not reload_path.exists():
                            self.console.print(f"[bold red]Error: File does not exist at {reload_path} immediately after saving![/bold red]")
                            return "" # Return empty string as we can't load it
                            
                        # Use the correct path (json_path) which was passed into the function
                        with open(reload_path, 'r', encoding='utf-8') as f:
                            practices = json.load(f)
                        return "\n".join([
                            f"- **{p['title']}**: {p['description']}" for p in practices
                        ])
                    except Exception as e:
                        self.console.print(f"[red]Error re-loading best practices: {e}[/red]")
                        return ""
                else:
                    self.console.print("[red]Failed to fetch Docker best practices.[/red]")
            return ""
        except Exception as e:
            self.console.print(f"[red]Error loading best practices: {e}[/red]")
            return ""

    def _get_image_info(self, dockerfile_path: str, tag: str = "temp_image_optimizer"): #returns size and layer count as a tuple.
        """Get Docker image size and layer count."""
        if not self._ensure_docker_client():
            self.console.print(f"[yellow]Skipping Docker build and analysis for '{tag}' due to Docker settings or connection status.[/yellow]")
            return 0, 0

        self.console.print(f"Building image from: {dockerfile_path} with tag {tag}")
        try:
            # Build the image with a simple progress bar (spinner + time elapsed)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=self.console,
                transient=True # Remove progress bar on completion
            ) as progress:
                build_task = progress.add_task(f"[cyan]Building Docker image ({tag})...", total=None)
                
                # Build the image - DO NOT iterate over build_log here
                image, build_log_stream = self.client.images.build(
                    path=str(Path(dockerfile_path).parent),
                    dockerfile=Path(dockerfile_path).name,
                    tag=tag,
                    rm=True,  # Remove intermediate containers
                    forcerm=True, # Always remove intermediate containers
                    timeout=300 # Add a 5-minute timeout
                )
                progress.update(build_task, completed=True, description="[green]Build finished.")

            self.console.print(f"[green]Image built successfully: {image.id}[/green]")
            
            # Get layer count
            layer_count = len(image.history())
            size = image.attrs['Size']
            
            # Clean up the temporary image
            try:
                self.client.images.remove(tag, force=True)
                self.console.print("[green]Temporary image removed.")
            except docker.errors.ImageNotFound:
                self.console.print("[yellow]Temporary image removal skipped (not found).")
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not remove temporary image: {e}[/yellow]")

            return size, layer_count
        except docker.errors.BuildError as build_err:
            self.console.print(f"[red]Docker Build Error: {build_err}[/red]")
            # Print build logs from the error if available
            if hasattr(build_err, 'build_log') and build_err.build_log:
                for line in build_err.build_log:
                    if isinstance(line, dict) and 'stream' in line:
                        self.console.print(f"[red]Build Log: {line['stream'].strip()}[/red]")
        except docker.errors.DockerException as docker_err:
            # Catch potential timeouts or other Docker API errors
            if 'timeout' in str(docker_err).lower():
                 self.console.print(f"[red]Docker Build Timed Out for {tag} after 5 minutes: {docker_err}[/red]")
            else:
                 self.console.print(f"[red]Docker API Error during build for {tag}: {docker_err}[/red]")
            return 0, 0 # Indicate failure
        except Exception as e:
            self.console.print(f"[red]Error getting image info for {tag}: {e}[/red]")
            return 0, 0

    def _download_repo_contents(self, repo, path: str, target_dir: str):
        """Recursively download repository contents."""
        contents = repo.get_contents(path)
        for content in contents:
            local_path = os.path.join(target_dir, content.path)
            if content.type == "dir":
                os.makedirs(local_path, exist_ok=True)
                self._download_repo_contents(repo, content.path, target_dir)
            else:
                try:
                    # Ensure parent directory exists before writing file
                    os.makedirs(os.path.dirname(local_path), exist_ok=True)
                    with open(local_path, "wb") as f:
                        f.write(content.decoded_content)
                    self.console.print(f"[blue]Downloaded: {content.path}[/blue]")
                except Exception as e:
                    self.console.print(f"[yellow]Warning: Could not download {content.path}: {str(e)}[/yellow]")

    def _build_optimized_dockerfile(self, original_path: str, optimized_content: str) -> str:
        """Build and get size of optimized Dockerfile."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Write the optimized content to a new Dockerfile
            optimized_path = os.path.join(temp_dir, "Dockerfile")
            self.console.print(f"[blue]Writing optimized Dockerfile to: {optimized_path}[/blue]")
            with open(optimized_path, 'w') as f:
                f.write(optimized_content)
            
            # Copy necessary files to temp directory
            original_dir = os.path.dirname(original_path)
            required_files = ['requirements.txt', 'app.py', 'myapp_scripts.sh']
            for file in required_files:
                src = os.path.join(original_dir, file)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(temp_dir, file))
                    self.console.print(f"[blue]Copied {file} to temporary directory[/blue]")
                else:
                    # If a file like myapp_scripts.sh is optional, this warning is okay.
                    # If it's essential for a specific Dockerfile, its absence here is problematic before the build.
                    self.console.print(f"[yellow]Warning: Required context file {file} not found in {original_dir}[/yellow]")
            
            # Get size of optimized image
            self.console.print("[blue]Attempting to build optimized image...[/blue]")
            size, layer_count = self._get_image_info(optimized_path, "temp_optimized_image")
            if size is not None and layer_count is not None: # Check both were returned
                self.console.print(f"[green]Successfully built optimized image. Size: {size / 1024 / 1024:.2f} MB, Layers: {layer_count}[/green]")
            return size, layer_count
        except Exception as e:
            self.console.print(f"[red]Error in _build_optimized_dockerfile: {str(e)}[/red]")
            return 0, 0
        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
                self.console.print("[blue]Cleaned up temporary directory[/blue]")
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not clean up temporary directory: {str(e)}[/yellow]")

    def _post_process_optimized_content(self, optimized_content: str) -> str:
        """
        Removes or generalizes potentially incompatible version pins from package manager install commands.
        Currently targets 'apt-get install'. Adds a comment indicating the change.
        If a pin matches an exact string in the catalog, it's kept.
        If a pin matches a wildcard pattern in the catalog, it's generalized (pin removed).
        If a pin has no match in the catalog, it's stripped (pin removed).
        """
        distro = self._detect_distro(optimized_content)
        cleaned_lines = []
        version_pin_regex = re.compile(r"([\w\.\-]+(?:\\[[\w\.\-]+\\])?)=([\d:\.\+\~\-\w]+)")
        apt_install_regex = re.compile(r"apt-get\s+(?:.*\s+)?install\b", re.IGNORECASE)

        lines = optimized_content.splitlines()
        i = 0
        overall_modified = False
        while i < len(lines):
            line = lines[i]
            if line.strip().startswith("RUN "):
                current_line_index = i
                install_command_lines = [line]
                temp_line = line
                while temp_line.rstrip().endswith('\\') and current_line_index + 1 < len(lines):
                    current_line_index += 1
                    temp_line = lines[current_line_index]
                    install_command_lines.append(temp_line)
                
                block_text = "\n".join(install_command_lines)
                if apt_install_regex.search(block_text):
                    block_modified = False
                    cleaned_command_lines = []
                    for l_idx, l_content in enumerate(install_command_lines):
                        current_cleaned_line = l_content
                        pins_found = version_pin_regex.findall(l_content)
                        if pins_found:
                            modified_in_this_line = False
                            # Iterate over a copy for modification, or build the new line segment by segment
                            temp_processing_line = current_cleaned_line
                            for pkg, ver in pins_found:
                                match_type = self._package_version_ok(distro, pkg, ver)
                                
                                # Decision logic based on match_type
                                if match_type == VersionMatch.EXACT_STRING_MATCH:
                                    # Pin is an exact match to a non-wildcard catalog entry, keep it.
                                    continue 
                                elif match_type == VersionMatch.WILDCARD_PATTERN_MATCH:
                                    # Matched a wildcard. Generalize by removing the pin.
                                    # self.console.print(f"[debug] Generalizing pin for {pkg}={ver} (wildcard match)") # Optional debug
                                    regex_pattern = fr"\b{re.escape(pkg)}={re.escape(ver)}\b"
                                    temp_processing_line = re.sub(regex_pattern, pkg, temp_processing_line)
                                    modified_in_this_line = True
                                elif match_type == VersionMatch.NO_MATCH:
                                    # No match in catalog or package not found. Strip pin.
                                    # self.console.print(f"[debug] Stripping pin for {pkg}={ver} (no match)") # Optional debug
                                    regex_pattern = fr"\b{re.escape(pkg)}={re.escape(ver)}\b"
                                    temp_processing_line = re.sub(regex_pattern, pkg, temp_processing_line)
                                    modified_in_this_line = True
                            
                            if modified_in_this_line:
                                current_cleaned_line = temp_processing_line
                                block_modified = True

                        cleaned_command_lines.append(current_cleaned_line)
                    
                    if block_modified:
                        overall_modified = True
                        last_line_idx = len(cleaned_command_lines) -1
                        # Append comment logic carefully to the correct line if it was part of a multi-line RUN
                        # For simplicity, adding to the last line of the processed block for now.
                        last_line_content = cleaned_command_lines[last_line_idx]
                        if ' # ' in last_line_content:
                            comment_start_index = last_line_content.find(' # ')
                            main_part = last_line_content[:comment_start_index].rstrip()
                            existing_comment = last_line_content[comment_start_index + 3:]
                            if "Pins modified by post-processor" not in existing_comment:
                                cleaned_command_lines[last_line_idx] = f"{main_part} # {existing_comment}; Pins modified by post-processor for compatibility"
                        elif "# Pins modified by post-processor for compatibility" not in last_line_content:
                             cleaned_command_lines[last_line_idx] = last_line_content.rstrip() + " # Pins modified by post-processor for compatibility"
                    
                    cleaned_lines.extend(cleaned_command_lines)
                else:
                    cleaned_lines.extend(install_command_lines)
                i = current_line_index + 1
            else:
                cleaned_lines.append(line)
                i += 1
        
        if overall_modified:
             self.console.print("[bold yellow]Warning: Some package version pins were generalized or removed by the post-processor for better compatibility. Manual review of 'apt-get install' commands is recommended.[/bold yellow]")

        final_content = "\n".join(cleaned_lines)
        return final_content

    def analyse_dockerfile(self, dockerfile_path: str) -> Analysis:
        """Analyze a Dockerfile using the linter and AI, return suggestions."""
        content = self._read_dockerfile(dockerfile_path)

        # Run the linter first
        linter_issues = self.linter.lint_file(dockerfile_path)
        
        # Get AI suggestions, providing linter context
        suggestions = self._get_ai_suggestions(content, linter_issues)
        
        # Try to get original image info
        try:
            original_size, original_layer_count = self._get_image_info(dockerfile_path, "temp_original_image")
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not build original image: {e}[/yellow]")
            original_size, original_layer_count = 0, 0

        # Try to build and get optimized image info
        optimized_size, optimized_layer_count = 0, 0
        processed_optimized_content = None # Use this for build and final result
        explanation = None
        try:
            # Extract the optimized Dockerfile content and explanation from suggestions
            raw_optimized_content, explanation = self._extract_dockerfile_content(suggestions)
            
            if raw_optimized_content:
                # <<< NEW: Post-process the AI content >>>
                processed_optimized_content = self._post_process_optimized_content(raw_optimized_content)
                
                # Build using the processed content
                optimized_size, optimized_layer_count = self._build_optimized_dockerfile(
                    dockerfile_path,
                    processed_optimized_content # Use cleaned content for build
                )
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not build optimized image: {e}[/yellow]")
        
        return Analysis(
            issues=linter_issues,
            suggestions=suggestions,
            score=1.0,
            original_size=original_size,
            optimized_size=optimized_size,
            layer_count=original_layer_count,
            optimized_layer_count=optimized_layer_count,
            optimized_content=processed_optimized_content,
            explanation=explanation,
            builds_attempted=self.attempt_docker_builds # Store if builds were meant to be run
        )

    def _read_dockerfile(self, path: str) -> str:
        """Read Dockerfile content."""
        with open(path, 'r') as f:
            return f.read()

    def _extract_dockerfile_content(self, ai_response: List[str]) -> Tuple[str, str]:
        """Extract optimized Dockerfile content and explanation from AI response."""
        dockerfile_content = []
        explanation_lines = []
        in_dockerfile = False
        in_explanation = False
        seen_explanations = set()  # Track unique explanations
        
        for line in ai_response:
            stripped = line.strip()
            if stripped.startswith("```dockerfile"):
                in_dockerfile = True
                in_explanation = False # Ensure we are not in explanation when dockerfile starts
                continue
            elif stripped == "```" and in_dockerfile:
                in_dockerfile = False
                # After Dockerfile block ends, subsequent content might be explanation or other text.
                # We only switch to in_explanation if the specific header is found.
                continue
            elif stripped.startswith("### Explanation of Changes:"):
                in_explanation = True
                in_dockerfile = False # Ensure we are not in dockerfile when explanation starts
                continue
            
            if in_dockerfile:
                dockerfile_content.append(line)
            elif in_explanation:
                # Heuristic: if the line doesn't look like a list item or a continuation,
                # and it's not empty, assume the explanation section has ended.
                # Common list markers: -, *, or digits followed by . or )
                is_list_item = stripped.startswith(('-', '*', '+')) or (len(stripped) > 1 and stripped[0].isdigit() and stripped[1] in ('.', ')'))
                
                if not stripped: # Allow empty lines within the explanation block (handled by later cleanup)
                    explanation_lines.append(line) # Keep blank line for now, will be stripped/deduped
                elif is_list_item or (explanation_lines and explanation_lines[-1].strip() and stripped.startswith('  ')): # Basic check for continuation (starts with spaces)
                    # Only add non-empty lines that haven't been seen before (original logic)
                    explanation_lines.append(line)
                else:
                    # Line is not empty, not a list item, not a simple continuation. Stop explanation.
                    in_explanation = False
                    # Do not process this line as part of the explanation.
                    # The main loop will continue and might process it based on other rules if necessary.
            
        # Clean up the explanation to ensure proper formatting
        explanation = "\n".join(explanation_lines).strip()
        
        # Deduplicate explanation lines while preserving original order
        lines = explanation.split("\n")
        seen = set()
        deduped = []
        for line in lines:
            ls = line.strip()
            if ls and ls not in seen:
                deduped.append(line)
                seen.add(ls)
        final_explanation = "\n".join(deduped)
        
        return ("\n".join(dockerfile_content).strip(), final_explanation)

    def _get_ai_suggestions(self, content: str, linter_issues: List[LinterIssue]) -> List[str]:
        """Get AI-powered optimization suggestions, including linter context."""
        prompt = self._create_optimization_prompt(content, linter_issues)
        
        # Add note about BuildKit limitations
        prompt += "\n\nNote: Do not use BuildKit-specific features like --mount in the Dockerfile as they are not enabled."
        
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a Dockerfile optimization expert. Analyze the provided Dockerfile, considering the linter issues and best practices, then provide an optimized version and explanation. Do not use BuildKit-specific features."}, 
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content.split('\n')

    def _format_linter_issues_for_prompt(self, linter_issues: List[LinterIssue]) -> str:
        """Formats linter issues for inclusion in the AI prompt."""
        if not linter_issues:
            return "No specific issues found by the linter."
        
        formatted = ["Linter found the following issues:"]
        for issue in linter_issues:
             formatted.append(f"- Line {issue.line_number} ({issue.rule.severity.value}): {issue.rule.title}. Suggestion: {issue.rule.suggestion}. (Line: `{issue.line_content}`)")
        return "\n".join(formatted)

    def _create_optimization_prompt(self, content: str, linter_issues: List[LinterIssue]) -> str:
        """Create prompt for AI optimization, including linter issues."""
        linter_summary = self._format_linter_issues_for_prompt(linter_issues)
        
        return f"""
You are a Platform Engineer with deep knowledge of Dockerfiles. You have access to a workspace.
Use the read, write and build tools to complete the following assignment:

Assignment: Analyse and optimise the Dockerfile (found at "$dockerfile") for reducing its size, number of layers, and build time. Also, increase the security level of the image by implementing best practices.

Important Context:
1.Linter Analysis:
{linter_summary}

2.General Best Practices:
{self.best_practices_text}

Your Task:
Based on the Dockerfile content, the linter analysis, and the general best practices, provide an optimized version of the Dockerfile.

Follow these guidelines:
- Address the issues identified by the linter where appropriate.
- Apply relevant best practices from the list provided.
- Make all the optimizations you can think of at once; don't optimize step-by-step.
- Ensure you never downgrade any image version found in the original Dockerfile.
- Pay close attention to the base image's OS distribution (e.g., Debian, Ubuntu, Alpine). When installing system packages (e.g., using `apt-get`, `apk`), ensure package names and versions are compatible with that specific distribution. Avoid hardcoding versions from one OS (like Ubuntu) onto a different base (like Debian).**
- CRITICAL: If you change the base image OS (e.g., from Debian 10 to Debian 12, or Ubuntu to Alpine), DO NOT pin package versions copied from the original Dockerfile unless you are certain they exist in the new base image's repositories. It is safer to remove the version pin or install the latest compatible version.
- If the Dockerfile is already optimized or requires no changes based on the context, explain why.
- Ensure the new Dockerfile builds correctly and write it to the workspace, replacing the old one.
- Skip explanations of intermediate steps before the final answer.

Final Output Format:
1.  Provide ONLY the complete optimised Dockerfile content enclosed in ```dockerfile ... ```.
2.  Immediately after the Dockerfile block, provide a section titled `### Explanation of Changes:`.
3.  In the explanation, provide a numbered list of changes, each with:
    - A clear, concise title
    - The specific changes made
    - Which linter issues or best practices it addresses
    - A brief explanation of the benefits

Original Dockerfile:
```dockerfile
{content}
```
"""

    def analyse_from_github(self, repo_url: str) -> Analysis:
        """Analyze a Dockerfile from a GitHub repository."""
        if not self.github_token:
            error_message = "GitHub token is required for repository analysis. Please ensure GITHUB_TOKEN is set in your environment or .env file, or provide it interactively if using the interactive CLI."
            self.console.print(f"[red]{error_message}[/red]")
            raise ValueError(error_message)
            
        try:
            # Extract owner and repo from URL
            repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")
            if "/" not in repo_path:
                raise ValueError(f"Invalid GitHub repository URL format: {repo_url}")
                
            owner, repo = repo_path.split("/")
            
            # Initialize GitHub client and verify authentication
            g = Github(self.github_token)
            try:
                user = g.get_user().login
            except Exception as auth_error:
                raise ValueError(f"GitHub authentication failed: {str(auth_error)}")
            
            # Get repository
            try:
                repository = g.get_repo(f"{owner}/{repo}")
            except Exception as repo_error:
                raise ValueError(f"Could not access repository {owner}/{repo}: {str(repo_error)}")
            
            # Create a temporary directory for all files
            temp_dir = tempfile.mkdtemp()
            try:
                # List repository contents and look for Dockerfile
                self.console.print("[blue]Downloading repository contents...[/blue]")
                self._download_repo_contents(repository, "", temp_dir)
                
                # Find the Dockerfile path within the downloaded structure
                dockerfile_path = None
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.lower().startswith("dockerfile"):
                            dockerfile_path = os.path.join(root, file)
                            break
                    if dockerfile_path:
                        break
                        
                if not dockerfile_path:
                     raise ValueError("No Dockerfile found in the downloaded repository content.")
                
                self.console.print(f"[green]Found Dockerfile at: {dockerfile_path}[/green]")
                
                try:
                    # Analyze and optimize
                    analysis = self.analyse_dockerfile(dockerfile_path)
                    return analysis
                finally:
                    # Clean up
                    try:
                        shutil.rmtree(temp_dir)
                        self.console.print("[blue]Cleaned up temporary directory[/blue]")
                    except Exception as e:
                        self.console.print(f"[yellow]Warning: Could not clean up temporary directory: {str(e)}[/yellow]")
                    
            except Exception as e:
                # Clean up on error
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                raise e
                
        except Exception as e:
            self.console.print(f"[red]GitHub Analysis Error: {str(e)}[/red]")
            raise

    def optimize_from_github(self, repo_url: str) -> str:
        """Create a PR with optimizations for a GitHub repository."""
        if not self.github_token:
            error_message = "GitHub token is required for creating a Pull Request. Please ensure GITHUB_TOKEN is set in your environment or .env file, or provide it interactively if using the interactive CLI."
            self.console.print(f"[red]{error_message}[/red]")
            raise ValueError(error_message)

        analysis = self.analyse_from_github(repo_url) # This will also check for the token
            
        # Extract owner and repo from URL
        repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")
        owner, repo = repo_path.split("/")
        
        # Initialize GitHub client and get repository
        g = Github(self.github_token)
        repository = g.get_repo(f"{owner}/{repo}")
            
            # Create pull request
        self._create_pull_request(repository, analysis)
            
        return "Pull request created successfully"

    def _create_pull_request(self, repository, analysis: Analysis):
        """Create a pull request with the optimizations."""
        if not self.github_token:
            error_message = "GitHub token is required for creating a Pull Request. Please ensure GITHUB_TOKEN is set in your environment or .env file, or provide it interactively if using the interactive CLI."
            self.console.print(f"[red]{error_message}[/red]")
            raise ValueError(error_message)

        # Create a new branch
        base_branch = repository.default_branch
        new_branch = f"dockerfile-optimization-{int(time.time())}"
        
        # Create branch
        repository.create_git_ref(f"refs/heads/{new_branch}", repository.get_git_ref(f"heads/{base_branch}").object.sha)
        
        # Update Dockerfile
        dockerfile = repository.get_contents("Dockerfile")
        repository.update_file(
            "Dockerfile",
            "Optimize Dockerfile based on best practices",
            analysis.suggestions[0],  # Use first suggestion as the optimized version
            dockerfile.sha,
            branch=new_branch
        )
        
        # Create pull request
        repository.create_pull(
            title="Dockerfile Optimization",
            body=self._create_pr_body(analysis),
            head=new_branch,
            base=base_branch
        )

    def _create_pr_body(self, analysis: Analysis) -> str:
        """Create pull request description (update to include linter issues)."""
        linter_issues_str = "\n".join([f"- Line {i.line_number} ({i.rule.severity.value}): {i.rule.title}" for i in analysis.issues])
        if not analysis.issues: # Check if the list is empty
            linter_issues_str = "No issues found by linter."

        # Use the extracted explanation, default to "No explanation provided." if empty
        explanation_str = analysis.explanation if analysis.explanation else "No explanation provided."
        
        # Calculate size improvement if both sizes are available
        size_improvement_str = ""
        if analysis.original_size > 0 and analysis.optimized_size > 0:
            improvement = (analysis.original_size - analysis.optimized_size) / analysis.original_size * 100
            size_improvement_str = f"\n- **Size Improvement**: {improvement:.1f}%"
        
        # Format Build Analysis Results
        build_results = []
        original_size_str = f"{analysis.original_size / 1024 / 1024:.2f} MB"
        if analysis.original_size == 0:
            original_size_str += " (Build failed or size unavailable)"
        build_results.append(f"- **Original Image Size**: {original_size_str}")
        build_results.append(f"- **Original Layer Count**: {analysis.layer_count if analysis.layer_count is not None else 'N/A'}")

        if analysis.optimized_size is not None:
            optimized_size_str = f"{analysis.optimized_size / 1024 / 1024:.2f} MB"
            if analysis.optimized_size == 0:
                optimized_size_str += " (Build failed or size unavailable)"
            build_results.append(f"- **Optimized Image Size**: {optimized_size_str}")
        build_results.append(f"- **Optimized Layer Count**: {analysis.optimized_layer_count if analysis.optimized_layer_count is not None else 'N/A'}")

        build_results_str = "\n".join(build_results) + size_improvement_str

        return f"""
# Dockerfile Optimization

This PR contains optimizations for the Dockerfile based on AI analysis, considering linter results and best practices.

## Optimization Explanation
{explanation_str}

## Linter Issues Found
{linter_issues_str}

## Build Analysis Results
{build_results_str}
"""

    def print_analysis(self, analysis: Analysis):
        """Print analysis results in a pretty format, including linter issues."""
        # Print file header and summary
        self.console.print("\n## Linter Results\n")
        
        # Group issues by severity
        issues_by_severity = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}
        for issue in analysis.issues:
            issues_by_severity[issue.rule.severity.value].append(issue)
        
        # Print summary with color codes
        self.console.print("Summary:")
        self.console.print(f"Total Issues Found: {len(analysis.issues)}")
        
        severity_colors = {
            "CRITICAL": "[bold red1]",
            "HIGH": "[red]",
            "MEDIUM": "[yellow]",
            "LOW": "[cyan]"
        }
        
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = len(issues_by_severity[severity])
            if count > 0:
                self.console.print(f"- {severity_colors[severity]}{severity}[/]: {count} issue{'s' if count > 1 else ''}")
        
        self.console.print("\nErrors:")
        self.console.print("___\n")
        
        # Print issues by severity with color codes
        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            severity_issues = issues_by_severity[severity]
            if severity_issues:
                self.console.print(f"\n### {severity_colors[severity]}{severity}[/] Severity Issues\n")
                
                for issue in severity_issues:
                    self.console.print(f"**Line {issue.line_number}**: {issue.line_content}")
                    self.console.print(f"- **Rule**: {severity_colors[severity]}{issue.rule.title}[/]")
                    self.console.print(f"- **Issue**: {issue.rule.description}")
                    self.console.print(f"- **Fix**: {issue.rule.suggestion}")
                    self.console.print("\n---")
        
        # Print build metrics
        self.console.print("\n## Build Analysis\n")
        metrics_table = Table(show_header=False)
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="green")
        
        size_note_original = ""
        if not analysis.builds_attempted:
            size_note_original = " (Docker builds not attempted)"
        elif analysis.original_size == 0: # Implies build failed or image was invalid if builds_attempted is true
            size_note_original = " (Build failed or size unavailable)"
        
        metrics_table.add_row("Original Image Size", f"{analysis.original_size / 1024 / 1024:.2f} MB{size_note_original}")
        metrics_table.add_row("Original Layer Count", f"{str(analysis.layer_count if analysis.layer_count is not None else 'N/A')}{size_note_original}")
        
        if analysis.optimized_content: # Only show optimized if it exists
            size_note_optimized = ""
            if not analysis.builds_attempted:
                size_note_optimized = " (Docker builds not attempted)"
            elif analysis.optimized_size is None or analysis.optimized_size == 0: # Optimized might fail to build
                 size_note_optimized = " (Build failed or size unavailable)"

            metrics_table.add_row("Optimized Image Size", f"{analysis.optimized_size / 1024 / 1024:.2f} MB{size_note_optimized}" if analysis.optimized_size is not None else f"N/A{size_note_optimized}")
            metrics_table.add_row("Optimized Layer Count", f"{str(analysis.optimized_layer_count if analysis.optimized_layer_count is not None else 'N/A')}{size_note_optimized}")

            if analysis.builds_attempted and analysis.original_size > 0 and analysis.optimized_size is not None and analysis.optimized_size > 0:
                improvement = (analysis.original_size - analysis.optimized_size) / analysis.original_size * 100
                improvement_color = "red" if improvement < 0 else "green"
                metrics_table.add_row("Size Improvement", f"[{improvement_color}]{improvement:.1f}%[/{improvement_color}]")
            elif analysis.builds_attempted:
                metrics_table.add_row("Size Improvement", "N/A (Could not compare sizes)")

        self.console.print(metrics_table)
        
        # Print optimized Dockerfile
        if analysis.optimized_content:
            self.console.print("\n## Optimized Dockerfile\n")
            self.console.print(Panel(analysis.optimized_content, title="Optimized Version"))
        
        # Print explanation
        if analysis.explanation:
            self.console.print("\n## Optimization Explanation\n")
            self.console.print(Panel(analysis.explanation, title="Changes Explained"))

    def create_pull_request(self, repo_url: str, analysis: Analysis) -> str:
        """Create a pull request with the optimizations."""
        if not self.github_token:
            error_message = "GitHub token is required for creating a Pull Request. Please ensure GITHUB_TOKEN is set in your environment or .env file, or provide it interactively if using the interactive CLI."
            self.console.print(f"[red]{error_message}[/red]")
            raise ValueError(error_message)

        try:
            # Extract owner and repo from URL
            repo_path = repo_url.replace("https://github.com/", "").replace(".git", "")
            owner, repo = repo_path.split("/")
            
            # Initialize GitHub client and get repository
            g = Github(self.github_token)
            repository = g.get_repo(f"{owner}/{repo}")
            
            # Create a new branch
            base_branch = repository.default_branch
            new_branch = f"dockerfile-optimization-{int(time.time())}"
            
            # Get base branch SHA
            base_ref = repository.get_git_ref(f"heads/{base_branch}")
            
            # Create new branch
            repository.create_git_ref(f"refs/heads/{new_branch}", base_ref.object.sha)
            
            # Find the Dockerfile in the repository
            contents = repository.get_contents("")
            dockerfile_path = None
            for content in contents:
                if content.name.lower().startswith("dockerfile"):
                    dockerfile_path = content.path
                    dockerfile = content
                    break
                
            if not dockerfile_path:
                raise ValueError("Could not find Dockerfile in repository")
            
            self.console.print(f"[blue]Found Dockerfile at: {dockerfile_path}[/blue]")
            
            # Update Dockerfile with optimized version
            if analysis.optimized_content:
                commit_message = "Optimize Dockerfile based on best practices"
                repository.update_file(
                    dockerfile_path,  # Use the found path
                    commit_message,
                    analysis.optimized_content,
                    dockerfile.sha,
                    branch=new_branch
                )
                
                # Create pull request
                pr = repository.create_pull(
                    title="Dockerfile Optimization",
                    body=self._create_pr_body(analysis),
                    head=new_branch,
                    base=base_branch
                )
                
                return pr.html_url
            else:
                raise ValueError("No optimized content available to create pull request")
            
        except Exception as e:
            self.console.print(f"[red]Error creating pull request: {str(e)}[/red]")
            raise

    # --- added helper methods for distro-aware pin validation ---
    def _detect_distro(self, content: str) -> str:
        for line in content.splitlines():
            if line.strip().startswith("FROM"):
                img = line.split()[1].lower()
                if "alpine" in img:
                    return "alpine"
                if "ubuntu" in img:
                    return "ubuntu"
                if "debian" in img:
                    return "debian"
        return "debian"

    def _package_version_ok(self, distro: str, pkg: str, ver: str) -> VersionMatch:
        info = self.package_catalog.get(distro, {})
        if isinstance(info, list): # Simplistic catalog: list of allowed packages (no versions)
            # If the package name is in the list, but a version is specified,
            # it's effectively a mismatch because this catalog format doesn't support versions for this distro.
            # If pkg in info and ver: return VersionMatch.NO_MATCH (or a more specific enum)
            # For now, this path implies no specific versioning info, so any pin is "not okay" by this simple list rule.
            return VersionMatch.NO_MATCH

        pkg_specific_config = info.get(pkg, {})

        if not pkg_specific_config: # Package not found in catalog for this distro
            return VersionMatch.NO_MATCH

        if isinstance(pkg_specific_config, list):
            # Case: package config is a direct list of allowed exact versions
            if ver in pkg_specific_config:
                # Check if the matched string in the catalog itself contains a wildcard.
                # This is unlikely for a direct list of versions but good for consistency.
                if any("*" in s or "?" in s or "[" in s for s in pkg_specific_config if s == ver):
                    return VersionMatch.WILDCARD_PATTERN_MATCH # Matched an exact string that happened to be a pattern
                else:
                    return VersionMatch.EXACT_STRING_MATCH
            else:
                return VersionMatch.NO_MATCH
        elif isinstance(pkg_specific_config, dict):
            versions_patterns = pkg_specific_config.get("versions", [])
            if not versions_patterns: # Package is listed, but no versions/patterns specified
                 return VersionMatch.NO_MATCH # Or perhaps a "NO_VERSION_SPECIFIED_IN_CATALOG"

            for pattern in versions_patterns:
                if fnmatch.fnmatch(ver, pattern):
                    # Check if the pattern itself is a wildcard or an exact string
                    if "*" in pattern or "?" in pattern or "[" in pattern:
                        return VersionMatch.WILDCARD_PATTERN_MATCH
                    elif ver == pattern: # It was an exact match to a non-wildcard pattern string
                        return VersionMatch.EXACT_STRING_MATCH
            return VersionMatch.NO_MATCH # No pattern matched
        
        # Default: Malformed entry or unhandled case in catalog for this package
        return VersionMatch.NO_MATCH

def generate_csv_report(issues: List[LinterIssue], output_path: str):
    """Generate a CSV report of linting issues."""
    output_dir = os.path.dirname(output_path)
    if output_dir: # Ensure directory exists if a path other than just filename is given
        os.makedirs(output_dir, exist_ok=True)

    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Severity', 'Line', 'Rule ID', 'Rule Title', 'Description', 'Suggestion', 'Line Content']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for issue in issues:
                writer.writerow({
                    'Severity': issue.rule.severity.value,
                    'Line': issue.line_number,
                    'Rule ID': issue.rule.id,
                    'Rule Title': issue.rule.title,
                    'Description': issue.rule.description,
                    'Suggestion': issue.rule.suggestion,
                    'Line Content': issue.line_content
                })
        Console().print(f"Linter CSV report generated: {output_path}")
    except Exception as e:
        Console().print(f"[red]Error generating CSV report: {e}[/red]")

def get_config_dir() -> Path:
    """Get the application's standard user configuration directory path."""
    if platform.system() == "Windows":
        # Use %APPDATA% on Windows
        base_path = Path(os.getenv("APPDATA"))
    else:
        # Use ~/.config on Linux/macOS
        base_path = Path.home() / ".config"
    
    config_dir = base_path / "DockerAI"
    config_dir.mkdir(parents=True, exist_ok=True) # Ensure it exists
    return config_dir

@click.group()
def cli():
    """Dockerfile Optimizer and Linter CLI"""
    pass

@cli.command()
@click.argument('dockerfile_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Choice(['text', 'json']), default='text', help="Output format for console display (text/json)")
@click.option('--output-csv', type=click.Path(), default=None, help="Path to save linter issues as a CSV file.")
@click.option('--output-optimized-dockerfile', type=click.Path(), default=None, help="Path to save the optimized Dockerfile content.")
@click.option('--output-explanation', type=click.Path(), default=None, help="Path to save the optimization explanation text.")
@click.option('--perform-docker-builds', is_flag=True, default=False, help="Attempt to build Docker images to compare sizes (requires Docker to be running).")
def analyse(dockerfile_path: str, output: str, output_csv: Optional[str], output_optimized_dockerfile: Optional[str], output_explanation: Optional[str], perform_docker_builds: bool):
    """Analyze a Dockerfile using linter and AI, then suggest optimizations."""
    try:
        optimizer = DockerfileOptimizer()
        optimizer.attempt_docker_builds = perform_docker_builds # Set the user's choice

        if perform_docker_builds:
            # This initial message sets user expectation. _ensure_docker_client will print more specific warnings when it tries to connect.
            optimizer.console.print("[cyan]Docker image builds enabled by user. Will attempt to connect to Docker daemon if/when build analysis is performed.[/cyan]")

        # --- BEGIN Timing Addition ---
        start_time = time.monotonic()
        # --- END Timing Addition ---

        analysis = optimizer.analyse_dockerfile(dockerfile_path)

        # --- BEGIN Timing Addition ---
        end_time = time.monotonic()
        duration_seconds = end_time - start_time
        optimizer.console.print(f"[dim]Analysis completed in {duration_seconds:.2f} seconds.[/dim]") # Optional: print duration
        # --- END Timing Addition ---

        if output == 'json':
            # Convert LinterIssue objects for JSON serialization
            serializable_issues = [
                {
                    'line_number': issue.line_number,
                    'line_content': issue.line_content,
                    'rule_id': issue.rule.id,
                    'title': issue.rule.title,
                    'description': issue.rule.description,
                    'severity': issue.rule.severity.value,
                    'suggestion': issue.rule.suggestion
                }
                for issue in analysis.issues
            ]
            # --- BEGIN JSON Output Addition ---
            # Get Dockerfile size for context
            try:
                dockerfile_size_bytes = os.path.getsize(dockerfile_path)
            except Exception:
                dockerfile_size_bytes = 0 # Default if size cannot be read
            # --- END JSON Output Addition ---

            print(json.dumps({
                'score': analysis.score, # Keep score even if unused for now
                'linter_issues': serializable_issues,
                'ai_suggestions': analysis.suggestions, # Note: This includes the optimized file + explanation
                'original_size': analysis.original_size, # Image size in bytes
                'optimized_size': analysis.optimized_size, # Image size in bytes
                'layer_count': analysis.layer_count, # Original layer count
                'optimized_layer_count': analysis.optimized_layer_count, # Optimized layer count
                'builds_attempted': analysis.builds_attempted, # Boolean flag
                'duration_seconds': duration_seconds,
                'dockerfile_size_bytes': dockerfile_size_bytes
            }, indent=2))
        else:
            optimizer.print_analysis(analysis)
            # Optionally print duration in text mode too
            # optimizer.console.print(f"\nAnalysis Duration: {duration_seconds:.2f} seconds")

        # --- BEGIN File Output Addition ---
        # Save CSV report if requested
        if output_csv:
            generate_csv_report(analysis.issues, output_csv)

        # Save optimized Dockerfile if requested and available
        if output_optimized_dockerfile:
            if analysis.optimized_content:
                try:
                    # Ensure directory exists
                    output_dir = os.path.dirname(output_optimized_dockerfile)
                    if output_dir:
                         os.makedirs(output_dir, exist_ok=True)
                    with open(output_optimized_dockerfile, 'w', encoding='utf-8') as f:
                        f.write(analysis.optimized_content)
                    optimizer.console.print(f"Optimized Dockerfile saved to: {output_optimized_dockerfile}")
                except Exception as e:
                    optimizer.console.print(f"[red]Error saving optimized Dockerfile: {e}[/red]")
            else:
                optimizer.console.print("[yellow]Warning: No optimized Dockerfile content available to save.[/yellow]")

        # Save explanation if requested and available
        if output_explanation:
            if analysis.explanation:
                try:
                    # Ensure directory exists
                    output_dir = os.path.dirname(output_explanation)
                    if output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                    with open(output_explanation, 'w', encoding='utf-8') as f:
                        f.write(analysis.explanation)
                    optimizer.console.print(f"Optimization explanation saved to: {output_explanation}")
                except Exception as e:
                    optimizer.console.print(f"[red]Error saving explanation: {e}[/red]")
            else:
                optimizer.console.print("[yellow]Warning: No explanation available to save.[/yellow]")
        # --- END File Output Addition ---

    except Exception as e:
        Console().print_exception(show_locals=True)
        click.echo(f"An error occurred: {e}", err=True)
        exit(1) # Exit with error code

@cli.command()
@click.argument('repo_url')
def optimize_github(repo_url: str):
    """Optimize Dockerfile from a GitHub repository and create a PR."""
    try:
        optimizer = DockerfileOptimizer()
        result = optimizer.optimize_from_github(repo_url)
        print(result)
    except Exception as e:
        Console().print_exception(show_locals=True)
        click.echo(f"An error occurred: {e}", err=True)
        exit(1) # Exit with error code

if __name__ == '__main__':
    cli() 