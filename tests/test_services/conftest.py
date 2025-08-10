"""Pytest configuration for service layer tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os

from src.models.base import Base
from src.models.team import TeamModel
from src.models.player import PlayerModel
from src.models.game import GameModel
from src.models.play import PlayModel


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine for the test session."""
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
    
    yield engine
    
    # Cleanup
    engine.dispose()
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a test database session with proper cleanup."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        # Ensure proper cleanup
        session.rollback()
        session.close()


@pytest.fixture
def sample_team(test_session):
    """Create a sample team for testing."""
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


@pytest.fixture
def sample_player(test_session):
    """Create a sample player for testing."""
    player = PlayerModel(
        player_id="00-0012345",
        player_name="John Doe",
        team_abbr="SF",
        position="QB",
        jersey_number=12,
        season=2024
    )
    test_session.add(player)
    test_session.commit()
    test_session.refresh(player)
    return player


@pytest.fixture
def sample_game(test_session):
    """Create a sample game for testing."""
    from datetime import date
    
    game = GameModel(
        game_id="2024_01_SF_KC",
        season=2024,
        season_type="REG",
        week=1,
        game_date=date(2024, 9, 5),
        home_team="KC",
        away_team="SF",
        home_score=24,
        away_score=21
    )
    test_session.add(game)
    test_session.commit()
    test_session.refresh(game)
    return game