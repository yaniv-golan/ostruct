import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class UserService:
    """Service for managing user accounts and authentication."""

    def __init__(self, db_connection):
        self.db = db_connection
        self.sessions: Dict[str, Dict] = {}  # In-memory session storage

    def create_user(
        self, username: str, email: str, password: str
    ) -> Optional[Dict]:
        """
        Create a new user account.

        Args:
            username: Desired username (3-20 chars, alphanumeric)
            email: User's email address
            password: Password (min 8 chars)

        Returns:
            User dict if created, None if validation fails
        """
        # Validate username
        if not re.match(r"^[a-zA-Z0-9]{3,20}$", username):
            return None

        # Validate email
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return None

        # Validate password
        if len(password) < 8:
            return None

        # Check if username exists
        if self.get_user_by_username(username):
            return None

        # Create user
        user = {
            "username": username,
            "email": email,
            "password_hash": self._hash_password(password),
            "created_at": datetime.utcnow().isoformat(),
        }

        self.db.users.insert_one(user)
        return user

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate user and create session.

        Args:
            username: User's username
            password: User's password

        Returns:
            Session token if authenticated, None if failed
        """
        user = self.get_user_by_username(username)
        if not user:
            return None

        if user["password_hash"] != self._hash_password(password):
            return None

        # Create session
        session_token = self._generate_session_token()
        self.sessions[session_token] = {
            "user_id": user["_id"],
            "expires": datetime.utcnow() + timedelta(hours=24),
        }

        return session_token

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user by username.

        Args:
            username: Username to look up

        Returns:
            User dict if found, None if not found
        """
        return self.db.users.find_one({"username": username})

    def get_active_sessions(self) -> List[Dict]:
        """
        Get all active (non-expired) sessions.

        Returns:
            List of active session details
        """
        now = datetime.utcnow()
        active = []

        for token, session in self.sessions.items():
            if session["expires"] > now:
                active.append(
                    {
                        "token": token,
                        "user_id": session["user_id"],
                        "expires": session["expires"],
                    }
                )

        return active

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def _generate_session_token(self) -> str:
        """Generate random session token."""
        return hashlib.sha256(
            str(datetime.utcnow().timestamp()).encode()
        ).hexdigest()
