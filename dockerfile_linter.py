import re
import json
from dataclasses import dataclass
from enum import Enum
import os

# Define severity levels based on category
CATEGORY_SEVERITY = {
    "Security Best Practices": "CRITICAL",      # Security issues are most critical
    "Base Image Selection & Versioning": "HIGH", # Image selection affects security and stability
    "Dependency Management": "HIGH",            # Package versioning is crucial for reproducibility
    "Build Optimization": "MEDIUM",             # Performance and size optimizations
    "Maintainability": "MEDIUM",               # Code quality and maintainability
    "CI/CD & Best Practices": "LOW",        # General best practices
    "Runtime Configuration": "LOW"              # Optional improvements
}

class Severity(Enum):
    """Enumeration of possible severity levels for linting issues."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

@dataclass
class LinterRule:
    """Data class representing a single linting rule."""
    id: str
    title: str
    description: str
    severity: Severity
    regex_pattern: re.Pattern
    suggestion: str
    
@dataclass
class LinterIssue:
    """Data class representing a single linting issue found in the Dockerfile."""
    line_number: int
    rule: LinterRule
    line_content: str

class DockerfileLinter:
    """A linter for Dockerfiles that checks for best practices and security issues."""
    
    def __init__(self, rules_path=os.path.join(os.path.dirname(__file__), "Rules", "rules.json")):
        """Initialize the linter with rules from a JSON file."""
        self.rules_path = rules_path
        self.rules = self._load_rules()
        
    def _load_rules(self) -> list:
        """Load linting rules from a JSON file, precompile regex patterns."""
        try:
            with open(self.rules_path, "r") as file:
                rules_data = json.load(file)
        except FileNotFoundError:
            print(f"Error: Could not find {self.rules_path}. Ensure the rules file exists.")
            return []
        
        rules = []
        for index, rule_data in enumerate(rules_data):
            category = rule_data.get("category", "Maintainability")  # Default if missing
            severity_str = CATEGORY_SEVERITY.get(category, "LOW")    # Assign severity based on category
            # Precompile the regex pattern
            compiled_pattern = re.compile(
                rule_data["regex_pattern"],
                flags=re.IGNORECASE | re.MULTILINE
            )
            
            rules.append(LinterRule(
                id=f"DOCKER_{index:03d}",
                title=rule_data["title"],
                description=rule_data["description"],
                severity=Severity[severity_str],
                regex_pattern=compiled_pattern,
                suggestion=rule_data["suggestion"]
            ))
        return rules
    def lint_file(self, dockerfile_path: str) -> list:
        """Lint a Dockerfile and identify any rule violations."""
        issues = []
        matched_lines = {}
        has_user_instruction = False  # Track if any USER instruction exists
        has_named_stage = False # Track if any FROM uses 'as <name>'
        multiple_run_commands = []  # Track consecutive RUN commands

        try:
            with open(dockerfile_path, 'r') as f:
                lines = f.readlines()

            full_content = ''.join(lines)

            # Pre-check: Determine if any stage is named
            for line in lines:
                stripped = line.strip()
                if re.match(r"(?i)^\s*FROM\s+[\w\-]+(:[\w\.\-]+)?\s+(?i:as)\s+\w+$", stripped):
                    has_named_stage = True
                    break

            # First pass: check for USER instructions and other rules
            for line_number, original_line in enumerate(lines, start=1):
                stripped_line = original_line.strip()
                
                # Skip comments and empty lines
                if not stripped_line or stripped_line.startswith('#'):
                    continue

                # Track consecutive RUN commands
                if stripped_line.upper().startswith('RUN'):
                    multiple_run_commands.append((line_number, stripped_line))
                else:
                    # If we found multiple RUN commands and now we see a different instruction
                    if len(multiple_run_commands) > 1:
                        # Find the "Combine RUN commands to reduce layers" rule
                        combine_runs_rule = next(
                            (rule for rule in self.rules 
                             if rule.title == "Combine RUN commands to reduce layers"),
                            None
                        )
                        if combine_runs_rule:
                            issues.append(LinterIssue(
                                line_number=multiple_run_commands[0][0],
                                rule=combine_runs_rule,
                                line_content=f"Multiple RUN commands found starting at line {multiple_run_commands[0][0]}"
                            ))
                    # Reset the RUN commands tracker
                    multiple_run_commands = []

                # Check if line contains USER instruction
                if stripped_line.upper().startswith('USER'):
                    has_user_instruction = True

                # Initialize set of matched rule IDs for this line
                if line_number not in matched_lines:
                    matched_lines[line_number] = set()

                # Special handling for "RUN cd" pattern
                if "cd" in stripped_line and stripped_line.upper().startswith('RUN'):
                    # Find the "Use WORKDIR instead of RUN cd" rule
                    workdir_rule = next(
                        (rule for rule in self.rules 
                         if rule.title == "Use WORKDIR instead of RUN cd"),
                        None
                    )
                    if workdir_rule and workdir_rule.id not in matched_lines[line_number]:
                        issues.append(LinterIssue(
                            line_number=line_number,
                            rule=workdir_rule,
                            line_content=original_line.rstrip('\n')
                        ))
                        matched_lines[line_number].add(workdir_rule.id)

                # Check each rule's pattern on this line
                for rule in self.rules:
                    # Skip multi-stage check if a named stage exists
                    if rule.title == "Use multi-stage builds" and has_named_stage:
                        continue 
                        
                    if rule.id in matched_lines[line_number]:
                        continue
                    
                    if rule.regex_pattern.search(stripped_line):
                        issues.append(LinterIssue(
                            line_number=line_number,
                            rule=rule,
                            line_content=original_line.rstrip('\n')
                        ))
                        matched_lines[line_number].add(rule.id)

            # After checking all lines, apply global checks
            # Check for missing USER instruction
            if not has_user_instruction:
                user_rule = next((r for r in self.rules if r.title == "Use USER Instruction and specify a non root user"), None)
                if user_rule:
                    issues.append(LinterIssue(
                        line_number=max(len(lines) - 1, 0),  # Report at end of file or line 0
                        rule=user_rule,
                        line_content="No USER instruction found in Dockerfile"
                    ))
                    
            # Check for missing multi-stage build if no named stage was found
            if not has_named_stage:
                 multistage_rule = next((r for r in self.rules if r.title == "Use multi-stage builds"), None)
                 if multistage_rule:
                     # Find the first FROM line to report the issue on
                     first_from_line = 1
                     for i, line in enumerate(lines, 1):
                         if line.strip().upper().startswith("FROM"):
                             first_from_line = i
                             break
                     issues.append(LinterIssue(
                         line_number=first_from_line,
                         rule=multistage_rule,
                         line_content="No named stage (e.g., 'AS builder') found. Multi-stage build recommended."
                     ))

            # Check for consecutive RUN commands one last time at the end of file
            if len(multiple_run_commands) > 1:
                combine_runs_rule = next(
                    (rule for rule in self.rules 
                     if rule.title == "Combine RUN commands to reduce layers"),
                    None
                )
                if combine_runs_rule:
                    issues.append(LinterIssue(
                        line_number=multiple_run_commands[0][0],
                        rule=combine_runs_rule,
                        line_content=f"Multiple RUN commands found starting at line {multiple_run_commands[0][0]}"
                    ))

            # Second pass: check multi-line patterns (Optional - keep if relevant for other rules)
            # ... (keep existing multi-line check logic if needed for other rules) ...

        except FileNotFoundError:
            print(f"Error: Could not find Dockerfile at {dockerfile_path}")
            return []

        return issues
