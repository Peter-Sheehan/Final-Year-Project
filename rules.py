"""
Collection of regex patterns and suggestions for Dockerfile linting.
Each pattern includes a regex, suggestion, and severity level.
"""

from typing import Dict, Any

DOCKERFILE_PATTERNS: Dict[str, Dict[str, Any]] = {
    'multi_stage_builds': {
        'pattern': r'(?i)^\s*FROM\s+[\w\-]+(:[\w\.\-]+)?(\s+AS\s+\w+)?$',
        'suggestion': "Consider using multi-stage builds to reduce final image size. Add 'AS builder' to your build stage.",
        'severity': 'MEDIUM'
    },
    'reusable_stages': {
        'pattern': r'(?i)^\s*FROM\s+[\w\-]+(:[\w\.\-]+)?\s+AS\s+\w+$',
        'suggestion': "Use AS to name your build stages for better reusability and readability.",
        'severity': 'LOW'
    },
    'base_image': {
        'pattern': r'(?i)^\s*FROM\s+(alpine|debian|ubuntu|python|node|nginx|golang|rust)(:[\w\.\-]+)?$',
        'suggestion': "Consider using official images with specific version tags.",
        'severity': 'HIGH'
    },
    'latest_tag': {
        'pattern': r'(?i)^\s*FROM\s+[\w\-]+:latest$',
        'suggestion': "Avoid using 'latest' tag. Pin your base image version for better reproducibility.",
        'severity': 'CRITICAL'
    },
    'unnecessary_files': {
        'pattern': r'(?i)^\s*COPY\s+.+(\.git|\.log|\.md|node_modules|\.DS_Store)\b',
        'suggestion': "Use .dockerignore to exclude unnecessary files from the build context.",
        'severity': 'MEDIUM'
    },
    'non_ephemeral': {
        'pattern': r'(?i)^\s*RUN\s+.*(echo|touch|mkdir).*(/var/log|/var/tmp|/tmp/dir)\b',
        'suggestion': "Avoid writing to non-ephemeral directories. Use volumes for persistent data.",
        'severity': 'HIGH'
    },
    'unnecessary_packages': {
        'pattern': r'(?i)\bapt-get\s+install\b.*\b(vim|nano|curl|wget|man-db|dialog)\b',
        'suggestion': "Avoid installing unnecessary packages to reduce image size.",
        'severity': 'MEDIUM'
    },
    'multiple_processes': {
        'pattern': r'(?i)^\s*CMD\s+\[.*(&|;).*\]',
        'suggestion': "Run only one process per container. Use docker-compose for multiple services.",
        'severity': 'HIGH'
    },
    'apt_get_update': {
        'pattern': r'(?i)^\s*RUN\s+apt-get\s+update\s*$',
        'suggestion': "Combine 'apt-get update' with 'apt-get install' in the same RUN instruction.",
        'severity': 'HIGH'
    },
    'apt_get_install': {
        'pattern': r'(?i)^\s*RUN\s+apt-get\s+install\s+(?!.*--no-install-recommends).*$',
        'suggestion': "Use apt-get install with --no-install-recommends to minimize image size.",
        'severity': 'MEDIUM'
    },
    'add_vs_copy': {
        'pattern': r'(?i)^\s*ADD\s+(?!--chown=)[^h]',
        'suggestion': "Use COPY instead of ADD for adding local files. ADD should only be used for remote URLs and auto-extracting archives.",
        'severity': 'MEDIUM'
    },
    'root_user': {
        'pattern': r'(?i)^\s*USER\s+root\b',
        'suggestion': "Avoid running as root. Create a non-root user and use USER instruction to switch to it.",
        'severity': 'CRITICAL'
    },
    'workdir_cd': {
        'pattern': r'(?i)^\s*RUN\s+cd\s+[\w\/]+',
        'suggestion': "Use WORKDIR instead of RUN cd for changing directories.",
        'severity': 'LOW'
    },
    'expose_ports': {
        'pattern': r'(?i)^\s*EXPOSE\s+(22|3389)\s*$',
        'suggestion': "Avoid exposing sensitive ports (22, 3389). Use Docker exec for container access.",
        'severity': 'CRITICAL'
    },
    'empty_env': {
        'pattern': r'(?i)^\s*ENV\s+\w+\s*(?:=\s*$|$)',
        'suggestion': "ENV instructions should have a non-empty value",
        'severity': 'LOW'
    },
    'multiple_runs': {
        'pattern': r'(?i)(?:^|\n)RUN\s+(?:(?!&&).)*$\s*(?:^|\n)RUN\s+',
        'suggestion': "Combine multiple RUN commands using && to reduce layers",
        'severity': 'MEDIUM'
    },
    'apt_cleanup': {
        'pattern': r'(?i)^\s*RUN\s+apt-get\s+install\s+(?!.*rm -rf /var/lib/apt/lists/).*$',
        'suggestion': "Clean up apt cache using 'rm -rf /var/lib/apt/lists/*' in the same RUN instruction",
        'severity': 'MEDIUM'
    },
    'relative_workdir': {
        'pattern': r'(?i)^\s*WORKDIR\s+[^/]',
        'suggestion': "Use absolute paths in WORKDIR instructions",
        'severity': 'LOW'
    }
}

def get_pattern(pattern_id: str) -> Dict[str, Any]:
    """Get a specific pattern by ID"""
    return DOCKERFILE_PATTERNS.get(pattern_id, {})

def get_all_patterns() -> Dict[str, Dict[str, Any]]:
    """Get all patterns"""
    return DOCKERFILE_PATTERNS 