# tests/models/test_user_model.py
import pytest
from sqlalchemy.exc import IntegrityError

# Adjust imports based on your project structure
from librorecomienda.models.user import User
from librorecomienda.core.security import get_password_hash

def test_create_user(db_session):
    """Test creating a valid User instance."""
    email = "test@example.com"
    password = "password123"
    hashed_password = get_password_hash(password) # Use your actual hashing function

    user = User(email=email, hashed_password=hashed_password)
    db_session.add(user)
    db_session.commit()

    # Query the user back
    retrieved_user = db_session.query(User).filter(User.email == email).first()

    assert retrieved_user is not None
    assert retrieved_user.email == email
    assert retrieved_user.is_active is True # Check default value
    assert retrieved_user.hashed_password == hashed_password
    assert retrieved_user.id is not None
    assert retrieved_user.created_at is not None
    assert retrieved_user.updated_at is not None

def test_create_user_duplicate_email(db_session):
    """Test that creating a user with a duplicate email raises IntegrityError."""
    email = "duplicate@example.com"
    password = "password123"
    hashed_password = get_password_hash(password)

    # Create the first user
    user1 = User(email=email, hashed_password=hashed_password)
    db_session.add(user1)
    db_session.commit()

    # Attempt to create the second user with the same email
    user2 = User(email=email, hashed_password=hashed_password)
    db_session.add(user2)

    # Expect an IntegrityError due to the unique constraint on email
    with pytest.raises(IntegrityError):
        db_session.commit()

def test_user_repr(db_session):
    """Test the __repr__ method of the User model."""
    email = "repr_test@example.com"
    password = "password123"
    hashed_password = get_password_hash(password)

    user = User(email=email, hashed_password=hashed_password)
    db_session.add(user)
    db_session.commit()
    # Refresh to get the ID assigned by the database
    db_session.refresh(user)

    expected_repr = f"<User(id={user.id}, email='{email}')>"
    assert repr(user) == expected_repr

# Add more tests here for other constraints (e.g., nullable fields if applicable)
# and relationships once they are more complex.
