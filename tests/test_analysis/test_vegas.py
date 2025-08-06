"""Tests for Vegas lines validation framework."""

import pytest
import numpy as np
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from src.analysis.vegas import (
    VegasValidator, VegasLine, ValueBet, ValidationMetrics,
    BetType
)
from src.analysis.models import Prediction
from src.models.game import GameModel


class TestVegasLine:
    """Test VegasLine class."""
    
    def test_vegas_line_creation(self):
        """Test VegasLine object creation."""
        line = VegasLine(
            game_id="2023_10_KC_SF",
            sportsbook="DraftKings",
            bet_type=BetType.MONEYLINE,
            home_odds=-110,
            away_odds=+105,
            timestamp=datetime(2023, 10, 1, 12, 0)
        )
        
        assert line.game_id == "2023_10_KC_SF"
        assert line.sportsbook == "DraftKings"
        assert line.bet_type == BetType.MONEYLINE
        assert line.home_odds == -110
        assert line.away_odds == +105
    
    def test_vegas_line_to_dict(self):
        """Test conversion to dictionary."""
        line = VegasLine(
            game_id="2023_10_KC_SF",
            sportsbook="FanDuel",
            bet_type=BetType.SPREAD,
            home_line=-3.5,
            away_line=+3.5,
            timestamp=datetime(2023, 10, 1, 12, 0)
        )
        
        result = line.to_dict()
        
        assert isinstance(result, dict)
        assert result['game_id'] == "2023_10_KC_SF"
        assert result['bet_type'] == "spread"
        assert result['home_line'] == -3.5
        assert result['timestamp'] == "2023-10-01T12:00:00"


class TestValueBet:
    """Test ValueBet class."""
    
    def test_value_bet_creation(self):
        """Test ValueBet object creation."""
        bet = ValueBet(
            game_id="2023_10_KC_SF",
            home_team="SF",
            away_team="KC",
            game_date=date(2023, 10, 1),
            bet_type=BetType.MONEYLINE,
            recommendation="home",
            model_probability=0.65,
            vegas_probability=0.55,
            expected_value=0.08,
            confidence=0.30,
            reasoning="Model edge: 10%"
        )
        
        assert bet.home_team == "SF"
        assert bet.recommendation == "home"
        assert bet.expected_value == 0.08
    
    def test_value_bet_to_dict(self):
        """Test conversion to dictionary."""
        bet = ValueBet(
            game_id="2023_10_KC_SF",
            home_team="SF",
            away_team="KC",
            game_date=date(2023, 10, 1),
            bet_type=BetType.MONEYLINE,
            recommendation="away",
            model_probability=0.45,
            vegas_probability=0.35,
            expected_value=0.12,
            confidence=0.25,
            reasoning="Value on underdog"
        )
        
        result = bet.to_dict()
        
        assert isinstance(result, dict)
        assert result['game_date'] == "2023-10-01"
        assert result['bet_type'] == "moneyline"
        assert result['expected_value'] == 0.12


class TestValidationMetrics:
    """Test ValidationMetrics class."""
    
    def test_validation_metrics_creation(self):
        """Test ValidationMetrics object creation."""
        metrics = ValidationMetrics(
            total_predictions=100,
            agreement_rate=0.68,
            avg_probability_difference=0.08,
            calibration_error=0.05,
            value_bet_accuracy=0.62,
            kelly_criterion_roi=0.15,
            sharpe_ratio=1.2,
            max_drawdown=0.08
        )
        
        assert metrics.total_predictions == 100
        assert metrics.agreement_rate == 0.68
        assert metrics.kelly_criterion_roi == 0.15
    
    def test_validation_metrics_to_dict(self):
        """Test conversion to dictionary."""
        metrics = ValidationMetrics(
            total_predictions=50,
            agreement_rate=0.72,
            avg_probability_difference=0.06,
            calibration_error=0.03,
            value_bet_accuracy=0.58,
            kelly_criterion_roi=0.12,
            sharpe_ratio=0.8,
            max_drawdown=0.05
        )
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result['total_predictions'] == 50
        assert result['agreement_rate'] == 0.72
        assert result['kelly_criterion_roi'] == 0.12


class TestVegasValidator:
    """Test VegasValidator class."""
    
    @pytest.fixture
    def vegas_validator(self, test_session, trained_predictor):
        """Create VegasValidator with trained predictor."""
        return VegasValidator(test_session, trained_predictor)
    
    @pytest.fixture
    def sample_vegas_lines(self):
        """Create sample Vegas lines."""
        return [
            VegasLine(
                game_id="2023_01_KC_SF",
                sportsbook="DraftKings",
                bet_type=BetType.MONEYLINE,
                home_odds=-120,
                away_odds=+100,
                timestamp=datetime(2023, 9, 10, 12, 0)
            ),
            VegasLine(
                game_id="2023_01_BUF_DAL",
                sportsbook="FanDuel",
                bet_type=BetType.MONEYLINE,
                home_odds=+105,
                away_odds=-125,
                timestamp=datetime(2023, 9, 10, 14, 0)
            )
        ]
    
    def test_initialization(self, test_session, trained_predictor):
        """Test VegasValidator initialization."""
        validator = VegasValidator(test_session, trained_predictor)
        
        assert validator.db_session == test_session
        assert validator.predictor == trained_predictor
    
    def test_odds_to_probability_negative(self, vegas_validator):
        """Test conversion of negative odds to probability."""
        # -110 odds should be approximately 0.524 probability
        prob = vegas_validator.odds_to_probability(-110)
        assert abs(prob - 0.524) < 0.01
        
        # -200 odds should be approximately 0.667 probability
        prob = vegas_validator.odds_to_probability(-200)
        assert abs(prob - 0.667) < 0.01
    
    def test_odds_to_probability_positive(self, vegas_validator):
        """Test conversion of positive odds to probability."""
        # +100 odds should be 0.5 probability
        prob = vegas_validator.odds_to_probability(+100)
        assert abs(prob - 0.5) < 0.01
        
        # +200 odds should be approximately 0.333 probability
        prob = vegas_validator.odds_to_probability(+200)
        assert abs(prob - 0.333) < 0.01
    
    def test_probability_to_odds_favorite(self, vegas_validator):
        """Test conversion of probability to odds for favorites."""
        # 0.6 probability should be negative odds
        odds = vegas_validator.probability_to_odds(0.6)
        assert odds < 0
        
        # Should be approximately -150
        assert abs(odds - (-150)) < 20
    
    def test_probability_to_odds_underdog(self, vegas_validator):
        """Test conversion of probability to odds for underdogs."""
        # 0.4 probability should be positive odds
        odds = vegas_validator.probability_to_odds(0.4)
        assert odds > 0
        
        # Should be approximately +150
        assert abs(odds - 150) < 30
    
    def test_calculate_expected_value_positive(self, vegas_validator):
        """Test expected value calculation for positive odds."""
        # Model thinks 60% chance, Vegas has +150 odds (40% implied)
        ev = vegas_validator.calculate_expected_value(0.6, +150, 1.0)
        
        # EV = 0.6 * 1.5 - 0.4 * 1.0 = 0.9 - 0.4 = 0.5
        assert ev > 0  # Should be positive expected value
        assert abs(ev - 0.5) < 0.1
    
    def test_calculate_expected_value_negative(self, vegas_validator):
        """Test expected value calculation for negative odds."""
        # Model thinks 50% chance, Vegas has -200 odds (67% implied)
        ev = vegas_validator.calculate_expected_value(0.5, -200, 1.0)
        
        assert ev < 0  # Should be negative expected value
    
    def test_kelly_criterion_value_bet(self, vegas_validator):
        """Test Kelly criterion for value bet."""
        # Model: 65% chance, Vegas: +100 odds (50% implied)
        kelly_fraction = vegas_validator.kelly_criterion(0.65, +100)
        
        assert kelly_fraction > 0  # Should recommend betting
        assert kelly_fraction <= 0.25  # Capped at 25%
    
    def test_kelly_criterion_no_edge(self, vegas_validator):
        """Test Kelly criterion when no edge exists."""
        # Model: 50% chance, Vegas: +100 odds (50% implied)
        kelly_fraction = vegas_validator.kelly_criterion(0.5, +100)
        
        assert kelly_fraction == 0  # Should not recommend betting
    
    def test_create_mock_vegas_lines(self, vegas_validator, sample_games):
        """Test creation of mock Vegas lines."""
        lines = vegas_validator.create_mock_vegas_lines(sample_games)
        
        assert len(lines) > 0
        assert len(lines) == len(sample_games) * 4  # 4 sportsbooks per game
        
        for line in lines:
            assert isinstance(line, VegasLine)
            assert line.bet_type == BetType.MONEYLINE
            assert line.home_odds is not None
            assert line.away_odds is not None
            assert line.sportsbook in ["DraftKings", "FanDuel", "BetMGM", "Caesars"]
    
    def test_find_value_bets_no_edge(self, vegas_validator, sample_predictions):
        """Test finding value bets when no edge exists."""
        # Create lines that match model predictions closely
        vegas_lines = [
            VegasLine(
                game_id="2023_10_KC_SF",
                sportsbook="DraftKings",
                bet_type=BetType.MONEYLINE,
                home_odds=vegas_validator.probability_to_odds(0.65),  # Match model
                away_odds=vegas_validator.probability_to_odds(0.35)
            ),
            VegasLine(
                game_id="2023_10_BUF_DAL",
                sportsbook="DraftKings",
                bet_type=BetType.MONEYLINE,
                home_odds=vegas_validator.probability_to_odds(0.45),  # Match model
                away_odds=vegas_validator.probability_to_odds(0.55)
            )
        ]
        
        value_bets = vegas_validator.find_value_bets(
            sample_predictions, vegas_lines, min_edge=0.05
        )
        
        assert len(value_bets) == 0  # No value bets when no edge
    
    def test_find_value_bets_with_edge(self, vegas_validator):
        """Test finding value bets when edge exists."""
        # Create prediction with high confidence
        predictions = [
            Prediction(
                home_team="SF",
                away_team="KC",
                game_date=date(2023, 10, 1),
                predicted_winner="SF",
                win_probability=0.70,
                home_win_prob=0.70,
                away_win_prob=0.30,
                confidence=0.40,
                features={}
            )
        ]
        
        # Create Vegas line that undervalues SF
        vegas_lines = [
            VegasLine(
                game_id="2023_10_KC_SF",
                sportsbook="DraftKings",
                bet_type=BetType.MONEYLINE,
                home_odds=+120,  # Implies ~45% probability
                away_odds=-150   # Implies ~60% probability
            )
        ]
        
        value_bets = vegas_validator.find_value_bets(
            predictions, vegas_lines, min_edge=0.05, min_confidence=0.35
        )
        
        assert len(value_bets) > 0
        assert value_bets[0].recommendation == "home"
        assert value_bets[0].expected_value > 0
    
    def test_validate_predictions_agreement(self, vegas_validator):
        """Test validation when model agrees with Vegas."""
        predictions = [
            Prediction(
                home_team="SF",
                away_team="KC", 
                game_date=date(2023, 9, 10),
                predicted_winner="SF",
                win_probability=0.60,
                home_win_prob=0.60,
                away_win_prob=0.40,
                confidence=0.20,
                features={}
            )
        ]
        
        vegas_lines = [
            VegasLine(
                game_id="2023_09_KC_SF",
                sportsbook="DraftKings",
                bet_type=BetType.MONEYLINE,
                home_odds=-130,  # SF favorite in Vegas too
                away_odds=+110
            )
        ]
        
        actual_results = [("SF", "KC")]  # SF won
        
        metrics = vegas_validator.validate_predictions(
            predictions, vegas_lines, actual_results
        )
        
        assert metrics.total_predictions == 1
        assert metrics.agreement_rate == 1.0  # Model and Vegas agree
        assert 0 <= metrics.avg_probability_difference <= 1
    
    def test_validate_predictions_disagreement(self, vegas_validator):
        """Test validation when model disagrees with Vegas."""
        predictions = [
            Prediction(
                home_team="SF",
                away_team="KC",
                game_date=date(2023, 9, 10), 
                predicted_winner="KC",  # Model picks KC
                win_probability=0.55,
                home_win_prob=0.45,
                away_win_prob=0.55,
                confidence=0.10,
                features={}
            )
        ]
        
        vegas_lines = [
            VegasLine(
                game_id="2023_09_KC_SF",
                sportsbook="DraftKings",
                bet_type=BetType.MONEYLINE,
                home_odds=-120,  # Vegas picks SF
                away_odds=+100
            )
        ]
        
        actual_results = [("KC", "SF")]  # KC won (model was right)
        
        metrics = vegas_validator.validate_predictions(
            predictions, vegas_lines, actual_results
        )
        
        assert metrics.total_predictions == 1
        assert metrics.agreement_rate == 0.0  # Model and Vegas disagree
    
    def test_validate_predictions_empty(self, vegas_validator):
        """Test validation with empty inputs."""
        metrics = vegas_validator.validate_predictions([], [], [])
        
        assert metrics.total_predictions == 0
        assert metrics.agreement_rate == 0.0
        assert metrics.avg_probability_difference == 0.0
        assert metrics.calibration_error == 0.0
    
    def test_validate_predictions_length_mismatch(self, vegas_validator):
        """Test validation with mismatched input lengths."""
        predictions = [Mock()]
        actual_results = [("SF", "KC"), ("DAL", "BUF")]  # Different length
        
        with pytest.raises(ValueError, match="same length"):
            vegas_validator.validate_predictions(predictions, [], actual_results)
    
    @patch.object(VegasValidator, 'create_mock_vegas_lines')
    def test_get_upcoming_value_bets_untrained(self, mock_lines, test_session):
        """Test getting value bets with untrained predictor."""
        from src.analysis.models import NFLPredictor
        
        untrained_predictor = NFLPredictor(test_session)
        validator = VegasValidator(test_session, untrained_predictor)
        
        with pytest.raises(ValueError, match="Model must be trained"):
            validator.get_upcoming_value_bets()
    
    def test_get_upcoming_value_bets_no_games(self, vegas_validator):
        """Test getting value bets when no upcoming games exist."""
        # All sample games are in the past
        value_bets = vegas_validator.get_upcoming_value_bets(weeks_ahead=1)
        
        assert isinstance(value_bets, list)
        assert len(value_bets) == 0
    
    @patch('src.analysis.vegas.date')
    def test_get_upcoming_value_bets_success(self, mock_date, vegas_validator, 
                                           test_session):
        """Test successful value bet identification."""
        # Mock today's date to be before our sample games
        mock_date.today.return_value = date(2023, 9, 1)
        
        # Create future game for testing
        future_game = GameModel(
            game_id="2023_99_KC_SF",  # Use unique game_id
            season=2023,
            season_type="REG",
            week=2,
            game_date=date(2023, 9, 17),  # Future date
            home_team="SF",
            away_team="KC"
        )
        test_session.add(future_game)
        test_session.commit()
        
        value_bets = vegas_validator.get_upcoming_value_bets(weeks_ahead=4)
        
        assert isinstance(value_bets, list)
        # Should have at least some analysis even if no value bets found
    
    def test_odds_conversion_roundtrip(self, vegas_validator):
        """Test that odds conversion is consistent."""
        test_probs = [0.3, 0.45, 0.5, 0.55, 0.7, 0.8]
        
        for prob in test_probs:
            odds = vegas_validator.probability_to_odds(prob)
            converted_prob = vegas_validator.odds_to_probability(odds)
            
            # Should be within 1% due to rounding
            assert abs(prob - converted_prob) < 0.01
    
    def test_kelly_criterion_edge_cases(self, vegas_validator):
        """Test Kelly criterion edge cases."""
        # Very high probability
        kelly = vegas_validator.kelly_criterion(0.95, +100)
        assert kelly > 0
        assert kelly <= 0.25  # Capped
        
        # Very low probability
        kelly = vegas_validator.kelly_criterion(0.05, +100)
        assert kelly == 0
        
        # Exactly break-even
        kelly = vegas_validator.kelly_criterion(0.5, +100)
        assert kelly == 0
    
    def test_expected_value_edge_cases(self, vegas_validator):
        """Test expected value calculation edge cases."""
        # Certain win with positive odds
        ev = vegas_validator.calculate_expected_value(1.0, +100, 1.0)
        assert ev == 1.0  # Should win exactly the payout
        
        # Certain loss
        ev = vegas_validator.calculate_expected_value(0.0, +100, 1.0)
        assert ev == -1.0  # Should lose the bet amount
        
        # Large bet size
        ev = vegas_validator.calculate_expected_value(0.6, +100, 10.0)
        expected_ev = vegas_validator.calculate_expected_value(0.6, +100, 1.0) * 10
        assert abs(ev - expected_ev) < 0.01