"""Test configuration for analysis tests."""

import pytest
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os
from datetime import date, timedelta

from src.models.base import Base
from src.models.team import TeamModel
from src.models.game import GameModel
from src.models.player import PlayerModel
from src.models.play import PlayModel
from src.analysis.features import FeatureEngineer
from src.analysis.models import NFLPredictor


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
def sample_teams(test_session):
    """Create sample teams for testing."""
    teams_data = [
        {
            "team_abbr": "SF",
            "team_name": "San Francisco",
            "team_nick": "49ers",
            "team_conf": "NFC",
            "team_division": "West"
        },
        {
            "team_abbr": "KC",
            "team_name": "Kansas City",
            "team_nick": "Chiefs",
            "team_conf": "AFC",
            "team_division": "West"
        },
        {
            "team_abbr": "DAL",
            "team_name": "Dallas",
            "team_nick": "Cowboys",
            "team_conf": "NFC",
            "team_division": "East"
        },
        {
            "team_abbr": "BUF",
            "team_name": "Buffalo",
            "team_nick": "Bills",
            "team_conf": "AFC",
            "team_division": "East"
        }
    ]
    
    teams = []
    for team_data in teams_data:
        team = TeamModel(**team_data)
        test_session.add(team)
        teams.append(team)
    
    test_session.commit()
    return teams


@pytest.fixture
def sample_games(test_session, sample_teams):
    """Create sample games for testing."""
    base_date = date(2023, 9, 10)  # Start of 2023 season
    
    games_data = []
    
    # Create games for multiple weeks
    for week in range(1, 6):  # 5 weeks of games
        week_start = base_date + timedelta(weeks=week-1)
        
        # Create games between different team combinations (mix of home/away wins)
        matchups = [
            ("SF", "KC", 24, 21),   # SF wins (home)
            ("DAL", "BUF", 14, 28), # BUF wins (away)
            ("KC", "DAL", 17, 31),  # DAL wins (away) 
            ("SF", "BUF", 21, 20),  # SF wins (home)
        ]
        
        for i, (home, away, home_score, away_score) in enumerate(matchups):
            game_date = week_start + timedelta(days=i)
            
            game = GameModel(
                game_id=f"2023_{week:02d}_{away}_{home}",
                season=2023,
                season_type="REG",
                week=week,
                game_date=game_date,
                home_team=home,
                away_team=away,
                home_score=home_score,
                away_score=away_score,
                total_score=home_score + away_score,
                result=1 if home_score > away_score else 0
            )
            
            test_session.add(game)
            games_data.append(game)
    
    test_session.commit()
    return games_data


@pytest.fixture
def feature_engineer(test_session):
    """Create feature engineer with test session."""
    return FeatureEngineer(test_session)


@pytest.fixture
def nfl_predictor(test_session):
    """Create NFL predictor with test session."""
    # Create temporary directory for models
    model_dir = tempfile.mkdtemp()
    return NFLPredictor(test_session, model_dir)


@pytest.fixture
def trained_predictor(nfl_predictor, sample_games):
    """Create a trained NFL predictor."""
    # Train with available data
    try:
        nfl_predictor.train(seasons=[2023], test_size=0.3, optimize_hyperparameters=False)
        return nfl_predictor
    except ValueError as e:
        # If not enough training data, return untrained predictor
        pytest.skip(f"Not enough training data: {e}")


@pytest.fixture
def sample_predictions():
    """Sample prediction data for testing."""
    from src.analysis.models import Prediction
    
    predictions = [
        Prediction(
            home_team="SF",
            away_team="KC",
            game_date=date(2023, 10, 1),
            predicted_winner="SF",
            win_probability=0.65,
            home_win_prob=0.65,
            away_win_prob=0.35,
            confidence=0.30,
            features={"home_win_pct": 0.6, "away_win_pct": 0.5}
        ),
        Prediction(
            home_team="DAL",
            away_team="BUF",
            game_date=date(2023, 10, 2),
            predicted_winner="BUF",
            win_probability=0.55,
            home_win_prob=0.45,
            away_win_prob=0.55,
            confidence=0.10,
            features={"home_win_pct": 0.4, "away_win_pct": 0.7}
        )
    ]
    
    return predictions