import os
import sqlite3
import json
from datetime import datetime, timedelta
from db_manager import DockerRulesDB
from webscraper import fetch_docker_best_practices, update_rules
from dockerfile_linter import DockerfileLinter
import time

class TestRunner:
    def __init__(self):
        self.db = DockerRulesDB()
        self.test_results = []
        self.conn = None
        self.cursor = None

    def connect_db(self):
        """Create a database connection"""
        if self.conn is None:
            self.conn = sqlite3.connect('docker_practices.db')
            self.cursor = self.conn.cursor()

    def close_db(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None

    def run_test(self, test_name, test_func):
        """Run a test and record its result"""
        try:
            print(f"\nRunning test: {test_name}")
            test_func()
            self.test_results.append(f"✅ {test_name}")
            print(f"Test passed: {test_name}")
        except Exception as e:
            self.test_results.append(f"❌ {test_name}: {str(e)}")
            print(f"Test failed: {test_name}")
            print(f"Error: {e}")
        finally:
            self.close_db()  # Ensure connection is closed after each test

    def setup_test_database(self, days_old=0):
        """Create a test database with records of specified age"""
        try:
            # Ensure any existing connection is closed
            self.close_db()
            
            # Wait a moment for the file to be released
            time.sleep(0.1)
            
            self.connect_db()
            
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS best_practices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            
            self.cursor.execute('DELETE FROM best_practices')
            
            test_date = datetime.now() - timedelta(days=days_old)
            self.cursor.execute('''
            INSERT INTO best_practices (title, description, created_at) 
            VALUES (?, ?, ?)
            ''', ('Test Rule', 'Test Description', test_date.strftime('%Y-%m-%d %H:%M:%S')))
            
            self.conn.commit()
        finally:
            self.close_db()

    def cleanup_database(self):
        """Remove test database"""
        max_attempts = 3
        delay = 0.5  # seconds
        
        for attempt in range(max_attempts):
            try:
                self.close_db()  # Ensure our connection is closed
                time.sleep(delay)  # Wait for file to be released
                
                if os.path.exists('docker_practices.db'):
                    os.remove('docker_practices.db')
                return
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(f"Cleanup attempt {attempt + 1} failed, retrying...")
                    time.sleep(delay)
                else:
                    print(f"Warning: Could not clean up database after {max_attempts} attempts: {e}")

    def test_webscraper(self):
        """Test webscraper functionality"""
        def test_fetch_practices():
            practices = fetch_docker_best_practices()
            assert practices is not None, "Failed to fetch practices"
            assert len(practices) > 0, "No practices fetched"
            assert all(['title' in p and 'description' in p for p in practices]), "Invalid practice format"

        def test_update_rules():
            self.cleanup_database()  # Ensure clean state
            assert update_rules() is True, "Failed to update rules"
            assert os.path.exists('docker_best_practices.json'), "JSON file not created"
            assert os.path.exists('docker_practices.db'), "Database not created"

        self.run_test("Fetch Docker Best Practices", test_fetch_practices)
        self.run_test("Update Rules", test_update_rules)

    def test_database_operations(self):
        """Test database operations"""
        def test_db_creation():
            self.cleanup_database()
            time.sleep(0.5)  # Add delay after cleanup
            self.db.init_db()
            assert os.path.exists('docker_practices.db'), "Database not created"

        def test_needs_update_checks():
            self.cleanup_database()
            time.sleep(0.5)  # Add delay after cleanup
            assert self.db.needs_update() is True, "Should need update when no database exists"

            self.setup_test_database(days_old=1)
            assert self.db.needs_update() is False, "Should not need update with fresh database"

            self.setup_test_database(days_old=8)
            assert self.db.needs_update() is True, "Should need update with old database"

        def test_save_and_retrieve():
            self.cleanup_database()  # Ensure clean state
            test_practices = [
                {"title": "Test1", "description": "Desc1"},
                {"title": "Test2", "description": "Desc2"}
            ]
            self.db.init_db()
            self.db.save_practices(test_practices)
            saved_practices = self.db.get_all_practices()
            assert len(saved_practices) == 2, "Not all practices were saved"

        self.run_test("Database Creation", test_db_creation)
        self.run_test("Update Check Logic", test_needs_update_checks)
        self.run_test("Save and Retrieve Practices", test_save_and_retrieve)

    def test_linter(self):
        """Test linter functionality"""
        def test_linter_initialization():
            self.cleanup_database()
            # Setup a fresh database with some rules
            test_practices = [
                {"title": "USER", "description": "Don't run as root"},
                {"title": "FROM", "description": "Don't use latest tag"}
            ]
            self.db.init_db()
            self.db.save_practices(test_practices)
            
            linter = DockerfileLinter()
            assert linter is not None, "Failed to initialize linter"

        def test_dockerfile_linting():
            # Create a test Dockerfile
            with open('test.Dockerfile', 'w') as f:
                f.write('''
FROM ubuntu:latest
USER root
RUN apt-get update
                ''')

            linter = DockerfileLinter()
            issues = linter.lint_file('test.Dockerfile')
            assert len(issues) > 0, "No issues found in problematic Dockerfile"

            # Cleanup
            os.remove('test.Dockerfile')

        self.run_test("Linter Initialization", test_linter_initialization)
        self.run_test("Dockerfile Linting", test_dockerfile_linting)

    def print_results(self):
        """Print test results summary"""
        print("\n=== Test Results ===")
        for result in self.test_results:
            print(result)
        print(f"\nTotal tests: {len(self.test_results)}")
        passed = sum(1 for r in self.test_results if r.startswith('✅'))
        print(f"Passed: {passed}")
        print(f"Failed: {len(self.test_results) - passed}")

def run_all_tests():
    """Run all tests"""
    runner = TestRunner()
    
    try:
        print("Starting tests...")
        runner.test_webscraper()
        runner.test_database_operations()
        runner.test_linter()
    finally:
        runner.cleanup_database()
        runner.print_results()

if __name__ == "__main__":
    run_all_tests() 