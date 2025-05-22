import requests
from bs4 import BeautifulSoup
import json

URL = "https://docs.docker.com/develop/dev-best-practices/"

def fetch_docker_best_practices():
    """Fetch best practices from Docker documentation"""
    try:
        response = requests.get(URL)
        response.raise_for_status()  # Raise exception for bad status codes
        
        soup = BeautifulSoup(response.content, "html.parser")
        main_content = soup.find('main')
        
        if not main_content:
            raise ValueError("Could not find main content section")
        
        practices = []
        headings = main_content.find_all(['h2', 'h3'])
        
        for heading in headings:
            title = heading.get_text(strip=True)
            description_parts = []
            current = heading.find_next_sibling()
            
            while current and current.name not in ['h2', 'h3']:
                if current.name == 'p':
                    description_parts.append(current.get_text(strip=True))
                current = current.find_next_sibling()
            
            if description_parts:
                # Join the description parts first
                full_description = " ".join(description_parts)

                # --- Correctly chain the cleaning steps --- START ---
                # Start with the full description
                cleaned_description = full_description
                # 1. Replace newlines
                cleaned_description = cleaned_description.replace('\n', ' ')
                # 2. Replace curly quotes with standard quotes globally
                cleaned_description = cleaned_description.replace('"', '"').replace('"', '"')
                # 3. Specifically fix the LABEL rule sequence by escaping the standard quote
                cleaned_description = cleaned_description.replace('characters (")', 'characters (\\")')
                # 4. Specifically fix the USER rule sequence by escaping the standard quotes
                cleaned_description = cleaned_description.replace('"gosu"', '\\"gosu\\"') # Escape quotes around gosu
                # --- Correctly chain the cleaning steps --- END ---

                practices.append({
                    "title": title,
                    # Use the correctly cleaned description
                    "description": cleaned_description
                })
        
        return practices
    except Exception as e:
        print(f"Error fetching Docker best practices: {e}")
        return None

def update_rules(config_dir):
    """Update Docker best practices JSON in the specified config directory."""
    practices = fetch_docker_best_practices()
    if not practices:
        return False
        
    try:
        # Save to JSON for backup/reference
        json_path = config_dir / "docker_best_practices.json"
        # Ensure the directory exists (though get_config_dir should have done it)
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding='utf-8') as f:
            json.dump(practices, f, indent=4, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error saving practices: {e}")
        return False

if __name__ == "__main__":
    # Example usage if run directly (requires config dir logic)
    # For simplicity, we might remove direct execution or add config dir finding here too
    print("Running webscraper directly is not the intended use.")
    # If you want to allow direct running, you'd need to duplicate
    # the get_config_dir logic here or import it from main.
    pass # Placeholder to avoid syntax error