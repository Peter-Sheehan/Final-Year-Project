import argparse
import os
import json
from dockerfile_linter import DockerfileLinter

# Add these color constants at the top of lint_cli.py
SEVERITY_COLORS = {
    'CRITICAL': '\033[38;5;196m',  # Darker/Deep Red (256-color mode)
    'HIGH': '\033[31m',            # Regular Red
    'MEDIUM': '\033[33m',          # Yellow
    'LOW': '\033[36m',             # Cyan
    'RESET': '\033[0m'             # Reset color
}

HIGHLIGHT_COLOR = '\033[1m'  # Bold
ERROR_COLOR = '\033[91m'     # Bright Red for error highlights

def main():
    parser = argparse.ArgumentParser(description='Dockerfile Linter')
    parser.add_argument('dockerfile', help='Path to the Dockerfile to lint')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                      help='Output format (default: text)')
    args = parser.parse_args()

    # Validate Dockerfile path
    if not os.path.exists(args.dockerfile):
        print(f"Error: Dockerfile not found at {args.dockerfile}")
        return

    # Initialise linter
    try:
        linter = DockerfileLinter()
    except Exception as e:
        print(f"Error initializing linter: {e}")
        return

    # Lint the file
    try:
        issues = linter.lint_file(args.dockerfile)
    except Exception as e:
        print(f"Error linting Dockerfile: {e}")
        return

    # Generate and print report
    if args.format == 'text':
        print(format_linter_errors(args.dockerfile, issues))
    elif args.format == 'json':
        json_report = {
            'dockerfile': args.dockerfile,
            'total_issues': len(issues),
            'issues': [
                {
                    'line_number': issue.line_number,
                    'line_content': issue.line_content,
                    'rule_id': issue.rule.id,
                    'title': issue.rule.title,
                    'description': issue.rule.description,
                    'severity': issue.rule.severity.value,
                    'suggestion': issue.rule.suggestion
                }
                for issue in issues
            ]
        }
        print(json.dumps(json_report, indent=2))

def format_linter_errors(dockerfile_path: str, issues: list) -> str:
    """Format linter errors in a clear, structured way.
    
    Args:
        dockerfile_path: Path to the Dockerfile being analyzed
        issues: List of LinterIssue objects
        
    Returns:
        Formatted string containing all linting errors
    """
    if not issues:
        return """## Linter Results
        
✅ No issues found in your Dockerfile!
"""
    
    # Group issues by severity
    issues_by_severity = {
        'CRITICAL': [],
        'HIGH': [],
        'MEDIUM': [],
        'LOW': []
    }
    
    for issue in issues:
        issues_by_severity[issue.rule.severity.value].append(issue)
    
    # Build the report
    report = [
        "## Linter Errors\n",
        f"File Name: {dockerfile_path}",
        "\nSummary:",
        f"Total Issues Found: {len(issues)}",
    ]
    
    # Add summary counts by severity with colors
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = len(issues_by_severity[severity])
        if count > 0:
            colored_severity = f"{SEVERITY_COLORS[severity]}{severity}{SEVERITY_COLORS['RESET']}"
            report.append(f"- {colored_severity}: {count} issue{'s' if count > 1 else ''}")
    
    report.extend([
        "\nErrors:",
        "___\n"
    ])
    
    # Add detailed issues by severity with colors
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        severity_issues = issues_by_severity[severity]
        if severity_issues:
            colored_severity = f"{SEVERITY_COLORS[severity]}{severity}{SEVERITY_COLORS['RESET']}"
            report.append(f"### {colored_severity} Severity Issues")
            
            for issue in severity_issues:
                report.extend([
                    f"\n**Line {issue.line_number}**: {issue.line_content}",
                    f"- **Rule**: {HIGHLIGHT_COLOR}{SEVERITY_COLORS[severity]}{issue.rule.title}{SEVERITY_COLORS['RESET']}",
                    f"- **Issue**: {issue.rule.description}",
                    f"- **Fix**: {issue.rule.suggestion}",
                    "\n---"
                ])
    
    report.append("\n___")
    
    return "\n".join(report)

if __name__ == "__main__":
    main() 