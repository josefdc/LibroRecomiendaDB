# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
import sys

# Add the src directory to the Python path to allow imports
# Adjust the path as necessary based on your project structure
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import your Base and models - Ensure these imports work correctly
# You might need to adjust the import path depending on your structure
# It's often better to import Base from where it's defined, e.g., db.session or models.base
try:
    from librorecomienda.db.session import Base # Assuming Base is accessible here
    # Import all models to ensure they are registered with Base
    from librorecomienda.models import user, book, review
except ImportError as e:
    print(f"Error importing project modules in conftest.py: {e}")
    print("Please ensure 'src' is in the Python path and models are correctly defined.")
    # Optionally raise the error or exit if imports are critical for fixture setup
    # raise

# --- Test Database Setup ---
# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

# Create a fixture for the SQLAlchemy engine (scoped to the session)
@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    # Create all tables defined in your models
    Base.metadata.create_all(bind=engine)
    yield engine
    # Optional: Drop all tables after the test session finishes
    # Base.metadata.drop_all(bind=engine) # Usually not needed for :memory:

# Create a fixture for the SQLAlchemy sessionmaker (scoped to the session)
@pytest.fixture(scope="session")
def db_session_factory(db_engine):
    """Returns a SQLAlchemy session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

# Create a fixture for an individual test database session (scoped to function)
@pytest.fixture(scope="function")
def db_session(db_engine, db_session_factory, request):
    """Provides a transactional scope around a test function."""
    connection = db_engine.connect()
    # Begin a non-ORM transaction
    transaction = connection.begin()
    # Bind an individual Session to the connection
    # Session = db_session_factory(bind=connection)
    # Use the factory directly to create the session
    session = db_session_factory(bind=connection)

    # Mark the test function as using this session
    # This can be helpful for plugins or advanced scenarios
    # request.node.db_session = session

    try:
        yield session # Test function runs here
    finally:
        session.close()
        # --- Refined Rollback ---
        # Rollback the transaction after the test, unless it was already handled
        if transaction.is_active:
            try:
                transaction.rollback()
            except Exception as e:
                # Log or handle potential rollback errors if necessary
                print(f"Error during test transaction rollback: {e}")
        # ------------------------
        # Return the connection to the pool
        connection.close()

