import os
import re
import json
from typing import Optional, Tuple
import openai
from dotenv import load_dotenv
import click
from rich.console import Console

# --- OpenAI Key Loading ---
console = Console()
try:
    # Attempt to read from .openai_key file in the parent directory
    key_path = os.path.join(os.path.dirname(__file__), '..', '.openai_key')
    with open(key_path, 'r') as f:
        openai.api_key = f.read().strip()
    # console.print(f"[dim]Using OpenAI key from: {key_path}[/dim]") # Optional Debug
except FileNotFoundError:
    # console.print("[yellow]Warning: OpenAI key file (.openai_key) not found in parent directory. Trying environment variable OPENAI_API_KEY.[/yellow]") # Optional Debug
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env')) # Load .env from parent
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        console.print("[red]Error: OpenAI API key not found in file or environment variables.[/red]")
        exit(1)
    # else:
        # console.print("[dim]Using OpenAI key from environment variable.[/dim]") # Optional Debug
except Exception as e:
    console.print(f"[red]Error reading OpenAI key: {e}[/red]")
    exit(1)


def read_dockerfile(path: str) -> str:
    """Read Dockerfile content."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        console.print(f"[red]Error: Input Dockerfile not found at {path}[/red]")
        exit(1)
    except Exception as e:
        console.print(f"[red]Error reading Dockerfile {path}: {e}[/red]")
        exit(1)

def extract_dockerfile_content(ai_response: str) -> Optional[str]:
    """Extract optimised Dockerfile content from AI response."""
    # Regex to find ```dockerfile ... ``` block
    match = re.search(r"```dockerfile\s*\n(.*?)\n```", ai_response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: Maybe it just gave the code without fences
    if ai_response.strip().lower().startswith("from"):
         return ai_response.strip()
    console.print("[yellow]Warning: Could not extract Dockerfile content using ```dockerfile fence. Check response format.[/yellow]")
    return None # Indicate failure to extract

def get_baseline_optimisation(content: str) -> Optional[str]:
    """Get baseline optimisation using gpt-4o with a minimal prompt."""
    prompt = f"""Optimise the following Dockerfile for size, build speed, and security. Provide only the optimised Dockerfile content within a ```dockerfile code block.

```dockerfile
{content}
```
"""
    try:
        console.print("[cyan]Sending request to OpenAI API (gpt-4o)...[/cyan]")
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a Dockerfile optimisation tool. Respond only with the optimised Dockerfile inside a ```dockerfile block."},
                {"role": "user", "content": prompt}
            ]
        )
        ai_response_content = response.choices[0].message.content
        # console.print(f"[dim]Raw OpenAI Response:\n{ai_response_content}[/dim]") # Optional Debug
        return extract_dockerfile_content(ai_response_content)
    except openai.AuthenticationError:
        console.print("[red]OpenAI API Error: Authentication failed. Check your API key.[/red]")
        return None
    except openai.RateLimitError:
         console.print("[red]OpenAI API Error: Rate limit exceeded. Please wait and try again.[/red]")
         return None
    except Exception as e:
        console.print(f"[red]Error calling OpenAI API: {e}[/red]")
        return None

def save_optimised_dockerfile(content: str, output_path: str):
    """Save the optimised Dockerfile content to a file."""
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        console.print(f"[green]✓ Baseline optimised Dockerfile saved to: {output_path}[/green]")
    except Exception as e:
        console.print(f"[red]Error saving optimised Dockerfile to {output_path}: {e}[/red]")
        exit(1)

@click.command()
@click.argument('input_dockerfile', type=click.Path(exists=True, dir_okay=False))
@click.argument('output_dockerfile', type=click.Path(writable=True, dir_okay=False))
def main(input_dockerfile: str, output_dockerfile: str):
    """
    Optimises a Dockerfile using OpenAI GPT-4o with a minimal prompt (baseline).

    INPUT_DOCKERFILE: Path to the original Dockerfile.
    OUTPUT_DOCKERFILE: Path where the baseline optimised Dockerfile will be saved.
    """
    console.print(f"Reading Dockerfile: {input_dockerfile}")
    original_content = read_dockerfile(input_dockerfile)

    console.print("Generating baseline optimisation...")
    optimised_content = get_baseline_optimisation(original_content)

    if optimised_content:
        save_optimised_dockerfile(optimised_content, output_dockerfile)
    else:
        console.print("[red]Failed to generate or extract baseline optimisation.[/red]")
        exit(1)

if __name__ == '__main__':
    main() 