from setuptools import setup

setup(
    name="dockerai",
    version="0.1.0",
    description="Dockerfile optimization tool with AI and linter support",
    py_modules=[
        "main",
        "interactive_cli",
        "lint_cli",
        "dockerfile_linter",
        "webscraper"
    ],
    install_requires=[
        "click",
        "rich",
        "python-dotenv",
        "docker",
        "PyGithub",
        "PyYAML",
        "openai",
        "requests",
        "beautifulsoup4"
    ],
    entry_points={
        "console_scripts": [
            "DockerAI=interactive_cli:cli"
        ],
    },
    include_package_data=True,
) 