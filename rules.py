import json
from typing import Dict, Any

def get_all_patterns() -> Dict[str, Dict[str, Any]]:
    """Load and return all linting patterns from new_rules.json"""
    filename = 'new_rules.json'
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            rules = json.load(f)
            return {
                rule['title'].lower().replace(' ', '_'): {
                    'pattern': rule['regex_pattern'],
                    'suggestion': rule['suggestion'],
                    'description': rule['description'],
                    'category': rule['category']
                }
                for rule in rules
            }
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filename}: {e}")
        return {}