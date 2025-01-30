import re
import json
from dataclasses import dataclass
from enum import Enum

# Define severity levels based on category
CATEGORY_SEVERITY = {
    "Security Best Practices": "CRITICAL",
    "Base Image Selection & Versioning": "HIGH",
    "Dependency Management": "HIGH",
    "Build Optimization": "MEDIUM",
    "Maintainability": "MEDIUM",
    "CI/CD & Best Practices": "LOW"
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
    
    def __init__(self, rules_path="new_rules.json"):
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

        try:
            with open(dockerfile_path, 'r') as f:
                lines = f.readlines()

            full_content = ''.join(lines)

            # First pass: check for USER instructions and other rules
            for line_number, original_line in enumerate(lines, start=1):
                stripped_line = original_line.strip()
                
                # Skip comments and empty lines
                if not stripped_line or stripped_line.startswith('#'):
                    continue

                # Check if line contains USER instruction
                if stripped_line.upper().startswith('USER'):
                    has_user_instruction = True

                # Initialize set of matched rule IDs for this line
                if line_number not in matched_lines:
                    matched_lines[line_number] = set()

                # Check each rule's pattern on this line
                for rule in self.rules:
                    if rule.id in matched_lines[line_number]:
                        continue
                    
                    if rule.regex_pattern.search(stripped_line):
                        issues.append(LinterIssue(
                            line_number=line_number,
                            rule=rule,
                            line_content=original_line.rstrip('\n')
                        ))
                        matched_lines[line_number].add(rule.id)

            # After checking all lines, if no USER instruction was found
            if not has_user_instruction:
                # Find the "Ensure a non-root user is used" rule
                user_rule = next(
                    (rule for rule in self.rules 
                     if rule.title == "Use USER Instruction and specify a non root user"),
                    None
                )
                if user_rule:
                    issues.append(LinterIssue(
                        line_number=len(lines),  # End of file
                        rule=user_rule,
                        line_content="No USER instruction found in Dockerfile"
                    ))

            # Second pass: check multi-line patterns if necessary
            # (For demonstration, only rules containing "multiple_runs" in their ID.)
            for rule in self.rules:
                if "multiple_runs" in rule.id.lower():
                    matches = rule.regex_pattern.finditer(full_content)
                    for match in matches:
                        # Determine the line where the match starts
                        line_number = full_content[:match.start()].count('\n') + 1

                        # Ensure we don't report duplicates on the same line for this rule
                        if rule.id not in matched_lines.get(line_number, set()):
                            issues.append(LinterIssue(
                                line_number=line_number,
                                rule=rule,
                                line_content=match.group(0).split("\n")[0]
                            ))
                            matched_lines.setdefault(line_number, set()).add(rule.id)

        except FileNotFoundError:
            print(f"Error: Could not find Dockerfile at {dockerfile_path}")
            return []

        return issues
