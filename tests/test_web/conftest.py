"""Test configuration for web interface tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os

from src.models.base import Base
from src.models.team import TeamModel


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary test database."""
    # Create temporary file for SQLite database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # Create engine with SQLite
    engine = create_engine(
        f"sqlite:///{db_path}",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session maker
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    try:
        yield TestingSessionLocal, engine
    finally:
        # Cleanup
        os.close(db_fd)
        os.unlink(db_path)


@pytest.fixture(scope="function")
def test_session(test_db):
    """Create a test database session."""
    TestingSessionLocal, engine = test_db
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sample_team(test_session):
    """Create a sample team in the test database."""
    team = TeamModel(
        team_abbr="SF",
        team_name="San Francisco",
        team_nick="49ers",
        team_conf="NFC",
        team_division="West"
    )
    test_session.add(team)
    test_session.commit()
    test_session.refresh(team)
    return team