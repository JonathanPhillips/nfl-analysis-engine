"""Pytest configuration for API tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os

from src.api.main import create_app
from src.api.dependencies import get_db_session
from src.models.base import Base
from src.models.team import TeamModel as Team
from src.models.player import PlayerModel as Player
from src.models.game import GameModel as Game
from src.models.play import PlayModel as Play


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


@pytest.fixture(scope="function")
def test_client(test_session):
    """Create a test client with database session override."""
    
    def override_get_db_session():
        """Override database session dependency."""
        try:
            yield test_session
        except Exception:
            test_session.rollback()
            raise
    
    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db_session
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_team_data():
    """Sample team data for testing."""
    return {
        "team_abbr": "SF",
        "team_name": "San Francisco",
        "team_nick": "49ers",
        "team_conf": "NFC",
        "team_division": "West",
        "team_color": "#AA0000",
        "team_color2": "#B3995D"
    }


@pytest.fixture
def sample_team(test_session, sample_team_data):
    """Create a sample team in the test database."""
    team = Team(**sample_team_data)
    test_session.add(team)
    test_session.commit()
    test_session.refresh(team)
    return team


@pytest.fixture
def sample_player_data():
    """Sample player data for testing."""
    return {
        "player_id": "00-0012345",
        "full_name": "John Doe",
        "first_name": "John",
        "last_name": "Doe",
        "team_abbr": "SF",
        "position": "QB",
        "jersey_number": 12,
        "status": "active",
        "height": 74,
        "weight": 220,
        "age": 28,
        "rookie_year": 2018
    }


@pytest.fixture
def sample_player(test_session, sample_player_data):
    """Create a sample player in the test database."""
    player = Player(**sample_player_data)
    test_session.add(player)
    test_session.commit()
    test_session.refresh(player)
    return player


@pytest.fixture
def sample_game_data():
    """Sample game data for testing."""
    return {
        "game_id": "2023_01_SF_KC",
        "season": 2023,
        "season_type": "REG",
        "week": 1,
        "home_team": "KC",
        "away_team": "SF",
        "home_score": 24,
        "away_score": 21,
        "total": 45,
        "overtime": False,
        "stadium": "Arrowhead Stadium",
        "roof": "outdoors",
        "surface": "grass"
    }


@pytest.fixture
def sample_game(test_session, sample_game_data):
    """Create a sample game in the test database."""
    from datetime import date
    game_data = sample_game_data.copy()
    game_data["game_date"] = date(2023, 9, 7)
    
    game = Game(**game_data)
    test_session.add(game)
    test_session.commit()
    test_session.refresh(game)
    return game


@pytest.fixture
def sample_play_data():
    """Sample play data for testing."""
    return {
        "play_id": "2023_01_SF_KC_1",
        "game_id": "2023_01_SF_KC",
        "season": 2023,
        "week": 1,
        "posteam": "SF",
        "defteam": "KC",
        "play_type": "pass",
        "desc": "J.Doe pass complete to J.Smith for 12 yards",
        "qtr": 1,
        "down": 1,
        "ydstogo": 10,
        "yardline_100": 75,
        "yards_gained": 12,
        "touchdown": False,
        "first_down": True,
        "ep": 1.2,
        "epa": 0.8,
        "wp": 0.52,
        "wpa": 0.02
    }


@pytest.fixture
def sample_play(test_session, sample_play_data):
    """Create a sample play in the test database."""
    play = Play(**sample_play_data)
    test_session.add(play)
    test_session.commit()
    test_session.refresh(play)
    return play