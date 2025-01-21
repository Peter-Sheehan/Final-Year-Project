import requests
from bs4 import BeautifulSoup
import json
from db_manager import DockerRulesDB

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
                practices.append({
                    "title": title,
                    "description": " ".join(description_parts)
                })
        
        return practices
    except Exception as e:
        print(f"Error fetching Docker best practices: {e}")
        return None

def update_rules():
    """Update Docker best practices in database and JSON"""
    practices = fetch_docker_best_practices()
    if not practices:
        return False
        
    try:
        # Save to JSON for backup/reference
        with open("docker_best_practices.json", "w", encoding='utf-8') as f:
            json.dump(practices, f, indent=4, ensure_ascii=False)
        
        # Save to database
        db = DockerRulesDB()
        db.init_db()
        db.save_practices(practices)
        return True
    except Exception as e:
        print(f"Error saving practices: {e}")
        return False

if __name__ == "__main__":
    if update_rules():
        print("Docker best practices updated successfully!")
    else:
        print("Failed to update Docker best practices.")
