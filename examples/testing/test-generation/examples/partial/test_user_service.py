import pytest

from .user_service import UserService


class MockDB:
    """Mock database for testing."""

    def __init__(self):
        self.users = MockCollection()


class MockCollection:
    """Mock database collection."""

    def __init__(self):
        self.data = []

    def insert_one(self, doc):
        doc["_id"] = len(self.data)
        self.data.append(doc)

    def find_one(self, query):
        for doc in self.data:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None


@pytest.fixture
def db():
    """Fixture providing a mock database."""
    return MockDB()


@pytest.fixture
def service(db):
    """Fixture providing a UserService instance."""
    return UserService(db)


def test_create_user_success(service):
    """Test successful user creation."""
    user = service.create_user("testuser", "test@example.com", "password123")
    assert user is not None
    assert user["username"] == "testuser"
    assert user["email"] == "test@example.com"
    assert "password_hash" in user
    assert "created_at" in user


def test_create_user_invalid_username(service):
    """Test user creation with invalid username."""
    # Too short
    assert service.create_user("t", "test@example.com", "password123") is None

    # Too long
    assert (
        service.create_user("a" * 21, "test@example.com", "password123")
        is None
    )

    # Invalid characters
    assert (
        service.create_user("test@user", "test@example.com", "password123")
        is None
    )


def test_create_user_duplicate_username(service):
    """Test user creation with duplicate username."""
    # Create first user
    assert (
        service.create_user("testuser", "test@example.com", "password123")
        is not None
    )

    # Try to create another user with same username
    assert (
        service.create_user("testuser", "other@example.com", "password456")
        is None
    )


# Note: Missing tests for:
# - Email validation
# - Password validation
# - Authentication
# - Session management
# - Session expiration
# - Active sessions retrieval
