# Final-Year-Project

Enhancing Dockerfile Quality and Security through Advanced Linting

Thesis https://www.overleaf.com/read/wgfvcsfvwrhh#a119cc

Trello board: https://trello.com/b/FgghCc1H/trello-agile-sprint-board-template

Jenkins job (sucessful run):http://localhost:8080/job/Docker%20Linter/18/

## Installation Guide

This guide will walk you through setting up and installing the DockerAI tool.

### Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python**: Version 3.8 or higher.
- **pip**: Python package installer (usually comes with Python).
- **Git**: For cloning the repository.
- **Docker**: (Optional) Required if you want to use the feature that attempts to build Docker images for size comparison. Ensure Docker Desktop or Docker Engine is running.

### Installation Steps

1.  **Clone the Repository:**
    Open your terminal and clone the project repository:

    ```bash
    git clone https://github.com/Peter-Sheehan/Final-Year-Project.git
    cd Final-Year-Project
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    It's highly recommended to use a virtual environment to manage project dependencies.

    ```bash
    python -m venv venv
    ```

    Activate the virtual environment:

    - On Windows:
      ```bash
      venv\Scripts\activate
      ```
    - On macOS and Linux:
      ```bash
      source venv/bin/activate
      ```

3.  **Install the Package:**
    With the virtual environment activated, ensure you are in the root directory of the `Final-Year-Project` (where `setup.py` is located). Then, install the `dockerai` package using pip:
    ```bash
    pip install .
    ```
    This command will read the `setup.py` file and install the `dockerai` tool along with all its required dependencies (like `openai`, `click`, `rich`, etc.).

### Configuration: API Keys

The DockerAI tool requires API keys for some of its features:

- **OpenAI API Key**: For AI-powered suggestions and optimisations.
- **GitHub Personal Access Token**: For analysing Dockerfiles from GitHub repositories and creating Pull Requests.

These keys are typically stored in a `.env` file in the application's configuration directory. The tool will prompt you to enter them if they are not found, and will attempt to save them for future use.

The configuration directory is usually:

- **Windows**: `%APPDATA%\DockerAI\`
- **Linux/macOS**: `~/.config/DockerAI/`

**Note on GitHub Token Scopes:**
When creating your GitHub Personal Access Token, ensure it has the necessary scopes. For analysing public repositories, the `public_repo` scope is usually sufficient. For private repositories or creating Pull Requests, you might need `repo` scope.

### Verification

Once installed and configured, you should be able to run the tool from your terminal:

```bash
DockerAI
```

This should launch the interactive command-line interface. You can also try:

```bash
DockerAI --help
```

to see available commands and options.

If you encounter any issues, please refer to the error messages or check the project's issue tracker.
