import sqlite3
import os
import json
from datetime import datetime, timedelta
from contextlib import contextmanager


class DockerRulesDB:
    def __init__(self, db_path='docker_practices.db'):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
        finally:
            if conn:
                conn.close()

    def init_db(self):
        """Initialize the database with required schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS best_practices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                regex_pattern TEXT,
                suggestion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.commit()

    def save_practices(self, practices):
        """Save practices to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM best_practices')
            cursor.executemany(
                'INSERT INTO best_practices (title, description, regex_pattern, suggestion) VALUES (?, ?, ?, ?)',
                [(p['title'], p['description'], p.get('regex_pattern', None), p.get('suggestion', None)) for p in practices]
            )
            conn.commit()

    def needs_update(self, days_threshold=7):
        """Check if database needs updating"""
        try:
            if not os.path.exists(self.db_path):
                print("Database does not exist.")
                return True

            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='best_practices'
                ''')
                if not cursor.fetchone():
                    print("Database table does not exist.")
                    return True

                cursor.execute('SELECT created_at FROM best_practices ORDER BY created_at DESC LIMIT 1')
                result = cursor.fetchone()

                if not result:
                    print("No records in database.")
                    return True

                created_at = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                is_old = datetime.now() - created_at > timedelta(days=days_threshold)

                if is_old:
                    print(f"Database is older than {days_threshold} days (last updated: {created_at})")
                return is_old

        except Exception as e:
            print(f"Error checking database age: {e}")
            return True

    def get_all_practices(self):
        """Retrieve all practices from database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT title, description, regex_pattern, suggestion FROM best_practices')
            return cursor.fetchall()

    def query_practices(self):
        """Query and display database practices"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Count rows
            cursor.execute('SELECT COUNT(*) FROM best_practices')
            count = cursor.fetchone()[0]
            print(f"\nTotal number of practices: {count}")

            # Display sample rows
            print("\nFirst few practices:")
            cursor.execute('SELECT title, substr(description, 1, 100) FROM best_practices LIMIT 3')
            for title, desc in cursor.fetchall():
                print(f"\nTitle: {title}")
                print(f"Description preview: {desc}...")

    def load_practices_from_json(self, json_path):
        """Load practices from a JSON file and save to database"""
        with open(json_path, 'r', encoding='utf-8') as f:
            practices = json.load(f)
        self.save_practices(practices)


if __name__ == "__main__":
    db = DockerRulesDB()

    # Initialize the database
    print("Initializing database...")
    db.init_db()

    # Load practices from a JSON file
    json_file_path = 'docker_best_practices.json'
    if os.path.exists(json_file_path):
        print("Loading practices from JSON...")
        db.load_practices_from_json(json_file_path)
    else:
        print(f"JSON file '{json_file_path}' not found.")

    # Query the database for verification
    print("Querying database...")
    db.query_practices()

    # Check if the database needs updating
    print("\nChecking if database needs updating...")
    if db.needs_update(days_threshold=7):
        print("Database needs updating.")
    else:
        print("Database is up-to-date.")
