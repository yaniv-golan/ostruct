import re
from datetime import datetime
from typing import Any, Dict, Optional


class UserService:
    """User management service demonstrating real-world patterns."""

    def __init__(self, db):
        self.db = db
        self.email_pattern = re.compile(
            r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        )

    def create_user(
        self, username: str, email: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Create a new user if validation passes."""
        # Validate username
        if not (3 <= len(username) <= 20) or not username.isalnum():
            return None

        # Validate email
        if not self.email_pattern.match(email):
            return None

        # Check if username exists
        if self.db.users.find_one({"username": username}):
            return None

        # Create user document
        user = {
            "username": username,
            "email": email,
            "password_hash": f"hashed_{password}",  # Simplified for example
            "created_at": datetime.utcnow(),
        }

        self.db.users.insert_one(user)
        return user
