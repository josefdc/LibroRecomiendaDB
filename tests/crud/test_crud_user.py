# tests/crud/test_crud_user.py
import pytest
from sqlalchemy.exc import IntegrityError

# Adjust imports based on your project structure
from librorecomienda.crud import create_user, get_user_by_email, get_users
from librorecomienda.schemas.user import UserCreate
from librorecomienda.models.user import User # Needed for direct query checks

def test_create_user_crud(db_session):
    """Test the create_user CRUD function."""
    email = "crud_test@example.com"
    password = "password123"
    user_in = UserCreate(email=email, password=password)

    created_user = create_user(db=db_session, user=user_in)

    assert created_user is not None
    assert created_user.email == email
    assert created_user.is_active is True
    assert hasattr(created_user, 'hashed_password') # Check if password was hashed
    assert created_user.hashed_password is not None
    # Verify it's actually in the DB
    db_user = db_session.query(User).filter(User.email == email).first()
    assert db_user is not None
    assert db_user.id == created_user.id

def test_create_user_crud_duplicate(db_session):
    """Test that create_user CRUD function handles duplicate emails."""
    email = "crud_duplicate@example.com"
    password = "password123"
    user_in = UserCreate(email=email, password=password)

    # Create first user
    create_user(db=db_session, user=user_in)

    # Attempt to create second user with same email
    # The CRUD function should ideally catch the IntegrityError or let it propagate
    with pytest.raises(IntegrityError):
         # Re-create the schema object if needed, or reuse if immutable
        user_in_dup = UserCreate(email=email, password="anotherpassword")
        create_user(db=db_session, user=user_in_dup)
        # Note: The actual behavior (catching vs. propagating) depends on create_user implementation.
        # This test assumes it propagates IntegrityError.

def test_get_user_by_email_found(db_session):
    """Test get_user_by_email when the user exists."""
    email = "findme@example.com"
    password = "password123"
    user_in = UserCreate(email=email, password=password)
    create_user(db=db_session, user=user_in) # Use the CRUD function to create

    found_user = get_user_by_email(db=db_session, email=email)

    assert found_user is not None
    assert found_user.email == email

def test_get_user_by_email_not_found(db_session):
    """Test get_user_by_email when the user does not exist."""
    email = "nosuchuser@example.com"

    found_user = get_user_by_email(db=db_session, email=email)

    assert found_user is None

def test_get_users(db_session):
    """Test the get_users CRUD function."""
    # Create some users
    user1_in = UserCreate(email="user1@example.com", password="pw1")
    user2_in = UserCreate(email="user2@example.com", password="pw2")
    create_user(db=db_session, user=user1_in)
    create_user(db=db_session, user=user2_in)

    # Get users (default skip/limit)
    users = get_users(db=db_session)

    assert len(users) >= 2 # Check if at least the created users are returned
    user_emails = [u.email for u in users]
    assert "user1@example.com" in user_emails
    assert "user2@example.com" in user_emails
    # Check if password hash is NOT returned (as per get_users implementation)
    for u in users:
        assert not hasattr(u, 'hashed_password') or u.hashed_password is None

def test_get_users_skip_limit(db_session):
    """Test get_users with skip and limit parameters."""
    # Ensure enough users exist or create more
    emails = [f"skiplimit{i}@example.com" for i in range(5)]
    for email in emails:
        # Check if user exists before creating to avoid IntegrityError in repeated test runs if needed
        existing = get_user_by_email(db=db_session, email=email)
        if not existing:
            create_user(db=db_session, user=UserCreate(email=email, password="pw"))

    # Get users with skip and limit
    users_skip1_limit2 = get_users(db=db_session, skip=1, limit=2)

    assert len(users_skip1_limit2) == 2
    # Add more specific assertions if the order is guaranteed (e.g., by ID or email)
    # For example, if ordered by ID:
    # all_users = get_users(db=db_session) # Assuming ordered by ID
    # assert users_skip1_limit2[0].email == all_users[1].email
    # assert users_skip1_limit2[1].email == all_users[2].email

# Add tests for other CRUD user functions if they exist (e.g., update_user, delete_user)
