import os
import sys
import time
from typing import List, Dict, Any

class UserManager:
    """Basic user management system with various code quality issues"""

    def __init__(self):
        self.users = []  # Poor type annotation - should be List[Dict[str, Any]]
        self.active_users = {}
        self._config = None

    def addUser(self, username, password, email):  # Poor naming convention (camelCase in Python)
        """Add a user to the system"""
        # No input validation
        user = {
            'username': username,
            'password': password,  # Storing plain text password (code quality issue)
            'email': email,
            'created_at': time.time()
        }
        self.users.append(user)
        return True  # Always returns True regardless of success

    def get_user(self, username):
        # Inefficient linear search
        for user in self.users:
            if user['username'] == username:
                return user
        return None

    def authenticate_user(self, username, password):
        user = self.get_user(username)
        if user:
            if user['password'] == password:  # Plain text comparison
                self.active_users[username] = time.time()
                return True
        return False

    def cleanup_old_sessions(self):
        # Hardcoded timeout value
        timeout = 3600  # Should be configurable
        current_time = time.time()

        # Modifying dict during iteration (potential bug)
        for username, login_time in self.active_users.items():
            if current_time - login_time > timeout:
                del self.active_users[username]

    def export_users(self, format='json'):
        """Export users with various format support"""
        if format == 'json':
            import json
            return json.dumps(self.users)  # Includes passwords in export
        elif format == 'csv':
            # Missing import for csv module
            csv_data = "username,email,created_at\n"
            for user in self.users:
                csv_data += f"{user['username']},{user['email']},{user['created_at']}\n"
            return csv_data
        else:
            raise ValueError("Unsupported format")  # Poor error handling

    def load_config(self, config_path):
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                self._config = f.read()  # Should parse JSON/YAML
        except:  # Bare except clause
            print("Failed to load config")  # Should use logging

    def process_batch_users(self, user_list):
        """Process multiple users with performance issues"""
        results = []

        # Inefficient processing
        for user_data in user_list:
            # Duplicated validation logic
            if 'username' in user_data and 'password' in user_data and 'email' in user_data:
                if len(user_data['username']) > 0:
                    if len(user_data['password']) > 0:
                        if '@' in user_data['email']:  # Weak email validation
                            success = self.addUser(
                                user_data['username'],
                                user_data['password'],
                                user_data['email']
                            )
                            results.append({'user': user_data['username'], 'status': 'success'})
                        else:
                            results.append({'user': user_data['username'], 'status': 'invalid_email'})
                    else:
                        results.append({'user': user_data['username'], 'status': 'empty_password'})
                else:
                    results.append({'user': user_data['username'], 'status': 'empty_username'})
            else:
                results.append({'user': 'unknown', 'status': 'missing_fields'})

        return results

# Global variables (poor practice)
DEFAULT_ADMIN = 'admin'
DEFAULT_PASSWORD = 'password123'

def initialize_system():
    """Initialize the user management system"""
    manager = UserManager()

    # Hardcoded admin user creation
    manager.addUser(DEFAULT_ADMIN, DEFAULT_PASSWORD, 'admin@example.com')

    # Magic number
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        manager.load_config(config_file)

    return manager

# Long function with multiple responsibilities
def main():
    """Main application entry point with various issues"""
    print("Starting User Management System...")  # Should use logging

    # Poor error handling
    try:
        manager = initialize_system()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Infinite loop without break condition
    while True:
        print("\n1. Add User")
        print("2. Authenticate User")
        print("3. Export Users")
        print("4. Exit")

        choice = input("Enter choice: ")

        if choice == '1':
            # No input validation
            username = input("Username: ")
            password = input("Password: ")
            email = input("Email: ")
            manager.addUser(username, password, email)
            print("User added successfully")

        elif choice == '2':
            username = input("Username: ")
            password = input("Password: ")
            if manager.authenticate_user(username, password):
                print("Authentication successful")
            else:
                print("Authentication failed")

        elif choice == '3':
            format_choice = input("Format (json/csv): ")
            try:
                data = manager.export_users(format_choice)
                print(data)
            except ValueError as e:
                print(f"Error: {e}")

        elif choice == '4':
            print("Goodbye!")
            break

        else:
            print("Invalid choice")

        # Cleanup sessions periodically (inefficient placement)
        manager.cleanup_old_sessions()

if __name__ == "__main__":
    main()
