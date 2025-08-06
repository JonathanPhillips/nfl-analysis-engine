"""Vegas lines integration and validation framework.

This module provides functionality to:
- Fetch and store Vegas betting lines
- Compare model predictions against Vegas lines
- Calculate value betting opportunities
- Validate model performance against market consensus
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta
from enum import Enum
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.game import GameModel
from .models import Prediction, NFLPredictor

logger = logging.getLogger(__name__)


class BetType(Enum):
    """Types of bets available."""
    SPREAD = "spread"
    MONEYLINE = "moneyline"
    TOTAL = "total"


@dataclass
class VegasLine:
    """Represents a Vegas betting line."""
    game_id: str
    sportsbook: str
    bet_type: BetType
    home_line: Optional[float] = None
    away_line: Optional[float] = None
    home_odds: Optional[int] = None
    away_odds: Optional[int] = None
    total: Optional[float] = None
    over_odds: Optional[int] = None
    under_odds: Optional[int] = None
    timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "game_id": self.game_id,
            "sportsbook": self.sportsbook,
            "bet_type": self.bet_type.value,
            "home_line": self.home_line,
            "away_line": self.away_line,
            "home_odds": self.home_odds,
            "away_odds": self.away_odds,
            "total": self.total,
            "over_odds": self.over_odds,
            "under_odds": self.under_odds,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }


@dataclass
class ValueBet:
    """Represents a value betting opportunity."""
    game_id: str
    home_team: str
    away_team: str
    game_date: date
    bet_type: BetType
    recommendation: str  # "home", "away", "over", "under"
    model_probability: float
    vegas_probability: float
    expected_value: float
    confidence: float
    reasoning: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "game_id": self.game_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "game_date": self.game_date.isoformat(),
            "bet_type": self.bet_type.value,
            "recommendation": self.recommendation,
            "model_probability": round(self.model_probability, 4),
            "vegas_probability": round(self.vegas_probability, 4),
            "expected_value": round(self.expected_value, 4),
            "confidence": round(self.confidence, 4),
            "reasoning": self.reasoning
        }


@dataclass
class ValidationMetrics:
    """Model validation metrics against Vegas lines."""
    total_predictions: int
    agreement_rate: float  # How often model agrees with Vegas favorite
    avg_probability_difference: float  # Average difference in win probabilities
    calibration_error: float  # How well calibrated predictions are
    value_bet_accuracy: float  # Accuracy of identified value bets
    kelly_criterion_roi: float  # ROI using Kelly criterion
    sharpe_ratio: float  # Risk-adjusted returns
    max_drawdown: float  # Maximum losing streak
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_predictions": self.total_predictions,
            "agreement_rate": round(self.agreement_rate, 4),
            "avg_probability_difference": round(self.avg_probability_difference, 4),
            "calibration_error": round(self.calibration_error, 4),
            "value_bet_accuracy": round(self.value_bet_accuracy, 4),
            "kelly_criterion_roi": round(self.kelly_criterion_roi, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 4)
        }


class VegasValidator:
    """Validates model predictions against Vegas lines."""
    
    def __init__(self, db_session: Session, predictor: NFLPredictor):
        """Initialize Vegas validator.
        
        Args:
            db_session: Database session
            predictor: Trained NFL predictor
        """
        self.db_session = db_session
        self.predictor = predictor
        self.logger = logging.getLogger(__name__)
    
    def odds_to_probability(self, odds: int) -> float:
        """Convert American odds to implied probability.
        
        Args:
            odds: American odds (e.g., -110, +150)
            
        Returns:
            Implied probability (0.0 to 1.0)
        """
        if odds > 0:
            # Positive odds: probability = 100 / (odds + 100)
            return 100 / (odds + 100)
        else:
            # Negative odds: probability = abs(odds) / (abs(odds) + 100)
            return abs(odds) / (abs(odds) + 100)
    
    def probability_to_odds(self, probability: float) -> int:
        """Convert probability to American odds.
        
        Args:
            probability: Probability (0.0 to 1.0)
            
        Returns:
            American odds
        """
        if probability >= 0.5:
            # Favorite: negative odds
            return int(-100 * probability / (1 - probability))
        else:
            # Underdog: positive odds
            return int(100 * (1 - probability) / probability)
    
    def calculate_expected_value(self, model_prob: float, odds: int, bet_size: float = 1.0) -> float:
        """Calculate expected value of a bet.
        
        Args:
            model_prob: Model's predicted probability
            odds: Vegas odds
            bet_size: Bet size (default 1 unit)
            
        Returns:
            Expected value of the bet
        """
        if odds > 0:
            # Positive odds
            payout = bet_size * (odds / 100)
        else:
            # Negative odds
            payout = bet_size * (100 / abs(odds))
        
        win_return = payout
        lose_return = -bet_size
        
        return (model_prob * win_return) + ((1 - model_prob) * lose_return)
    
    def kelly_criterion(self, model_prob: float, odds: int) -> float:
        """Calculate optimal bet size using Kelly criterion.
        
        Args:
            model_prob: Model's predicted probability
            odds: Vegas odds
            
        Returns:
            Fraction of bankroll to bet (0.0 to 1.0)
        """
        if odds > 0:
            b = odds / 100  # Decimal odds - 1
        else:
            b = 100 / abs(odds)  # Decimal odds - 1
        
        # Kelly formula: f = (bp - q) / b
        # where p = probability of win, q = probability of loss, b = decimal odds - 1
        p = model_prob
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b
        
        # Cap at reasonable maximum (25% of bankroll)
        return max(0, min(kelly_fraction, 0.25))
    
    def create_mock_vegas_lines(self, games: List[GameModel]) -> List[VegasLine]:
        """Create mock Vegas lines for testing purposes.
        
        This simulates realistic Vegas lines based on team strength and historical patterns.
        In production, this would be replaced with real sportsbook API integration.
        
        Args:
            games: List of games to create lines for
            
        Returns:
            List of mock Vegas lines
        """
        vegas_lines = []
        
        # Mock sportsbooks
        sportsbooks = ["DraftKings", "FanDuel", "BetMGM", "Caesars"]
        
        for game in games:
            # Create moneyline odds based on simple team strength heuristic
            # This is a simplified model - real implementation would use historical data
            
            # Mock team strength (in production, derive from historical performance)
            team_strengths = {
                "KC": 0.65, "BUF": 0.62, "SF": 0.60, "DAL": 0.58,
                "PHI": 0.56, "MIA": 0.54, "CIN": 0.52, "JAX": 0.50,
                # Add more teams with realistic strength ratings
            }
            
            home_strength = team_strengths.get(game.home_team, 0.50)
            away_strength = team_strengths.get(game.away_team, 0.50)
            
            # Home field advantage
            home_advantage = 0.03
            adjusted_home_strength = min(0.85, home_strength + home_advantage)
            
            # Calculate win probability
            total_strength = adjusted_home_strength + away_strength
            if total_strength > 0:
                home_win_prob = adjusted_home_strength / total_strength
                away_win_prob = 1 - home_win_prob
            else:
                home_win_prob = away_win_prob = 0.5
            
            # Add some randomness to simulate market inefficiencies
            import random
            random.seed(hash(game.game_id))  # Consistent randomness
            noise = random.uniform(-0.05, 0.05)
            home_win_prob = max(0.1, min(0.9, home_win_prob + noise))
            away_win_prob = 1 - home_win_prob
            
            # Convert to odds
            home_odds = self.probability_to_odds(home_win_prob)
            away_odds = self.probability_to_odds(away_win_prob)
            
            # Create lines for each sportsbook with slight variations
            for i, sportsbook in enumerate(sportsbooks):
                # Add sportsbook-specific variation
                variance = random.uniform(-0.02, 0.02)
                sb_home_prob = max(0.1, min(0.9, home_win_prob + variance))
                sb_away_prob = 1 - sb_home_prob
                
                sb_home_odds = self.probability_to_odds(sb_home_prob)
                sb_away_odds = self.probability_to_odds(sb_away_prob)
                
                vegas_line = VegasLine(
                    game_id=game.game_id,
                    sportsbook=sportsbook,
                    bet_type=BetType.MONEYLINE,
                    home_odds=sb_home_odds,
                    away_odds=sb_away_odds,
                    timestamp=datetime.now() - timedelta(hours=random.randint(1, 48))
                )
                vegas_lines.append(vegas_line)
        
        return vegas_lines
    
    def find_value_bets(self, predictions: List[Prediction], 
                       vegas_lines: List[VegasLine],
                       min_edge: float = 0.05,
                       min_confidence: float = 0.6) -> List[ValueBet]:
        """Find value betting opportunities.
        
        Args:
            predictions: Model predictions
            vegas_lines: Vegas betting lines
            min_edge: Minimum edge required for value bet (default 5%)
            min_confidence: Minimum model confidence required
            
        Returns:
            List of value betting opportunities
        """
        value_bets = []
        
        # Create lookup for vegas lines by game_id
        lines_by_game = {}
        for line in vegas_lines:
            if line.game_id not in lines_by_game:
                lines_by_game[line.game_id] = []
            lines_by_game[line.game_id].append(line)
        
        for prediction in predictions:
            game_id = f"{prediction.game_date.year}_{prediction.game_date.month:02d}_{prediction.away_team}_{prediction.home_team}"
            
            if game_id not in lines_by_game:
                continue
            
            # Use best available odds (highest for the side we want to bet)
            game_lines = [line for line in lines_by_game[game_id] if line.bet_type == BetType.MONEYLINE]
            
            if not game_lines:
                continue
            
            # Find value bets for both home and away
            for side in ["home", "away"]:
                if side == "home":
                    model_prob = prediction.home_win_prob
                    best_odds = max((line.home_odds for line in game_lines if line.home_odds), default=None)
                else:
                    model_prob = prediction.away_win_prob
                    best_odds = max((line.away_odds for line in game_lines if line.away_odds), default=None)
                
                if best_odds is None or model_prob < min_confidence:
                    continue
                
                vegas_prob = self.odds_to_probability(best_odds)
                edge = model_prob - vegas_prob
                
                if edge >= min_edge:
                    expected_value = self.calculate_expected_value(model_prob, best_odds)
                    
                    if expected_value > 0:
                        reasoning = f"Model: {model_prob:.3f} vs Vegas: {vegas_prob:.3f} (Edge: {edge:.3f})"
                        
                        value_bet = ValueBet(
                            game_id=game_id,
                            home_team=prediction.home_team,
                            away_team=prediction.away_team,
                            game_date=prediction.game_date,
                            bet_type=BetType.MONEYLINE,
                            recommendation=side,
                            model_probability=model_prob,
                            vegas_probability=vegas_prob,
                            expected_value=expected_value,
                            confidence=prediction.confidence,
                            reasoning=reasoning
                        )
                        
                        value_bets.append(value_bet)
        
        # Sort by expected value descending
        value_bets.sort(key=lambda x: x.expected_value, reverse=True)
        
        return value_bets
    
    def validate_predictions(self, predictions: List[Prediction], 
                           vegas_lines: List[VegasLine],
                           actual_results: List[Tuple[str, str]]) -> ValidationMetrics:
        """Validate model predictions against Vegas lines and actual results.
        
        Args:
            predictions: Model predictions
            vegas_lines: Vegas betting lines
            actual_results: Actual game results (winner, loser) tuples
            
        Returns:
            Validation metrics
        """
        if len(predictions) != len(actual_results):
            raise ValueError("Predictions and actual results must have the same length")
        
        # Create lookup for vegas lines
        lines_by_game = {}
        for line in vegas_lines:
            if line.bet_type == BetType.MONEYLINE:
                if line.game_id not in lines_by_game:
                    lines_by_game[line.game_id] = line
        
        agreements = 0
        probability_differences = []
        model_correct = []
        vegas_correct = []
        kelly_returns = []
        
        for i, prediction in enumerate(predictions):
            game_id = f"{prediction.game_date.year}_{prediction.game_date.month:02d}_{prediction.away_team}_{prediction.home_team}"
            actual_winner, actual_loser = actual_results[i]
            
            # Check if we have Vegas line for this game
            if game_id not in lines_by_game:
                continue
            
            vegas_line = lines_by_game[game_id]
            
            # Determine Vegas favorite
            if vegas_line.home_odds and vegas_line.away_odds:
                vegas_home_prob = self.odds_to_probability(vegas_line.home_odds)
                vegas_away_prob = self.odds_to_probability(vegas_line.away_odds)
                
                vegas_favorite = prediction.home_team if vegas_home_prob > vegas_away_prob else prediction.away_team
                model_favorite = prediction.predicted_winner
                
                # Check agreement
                if vegas_favorite == model_favorite:
                    agreements += 1
                
                # Calculate probability differences
                if model_favorite == prediction.home_team:
                    prob_diff = abs(prediction.home_win_prob - vegas_home_prob)
                else:
                    prob_diff = abs(prediction.away_win_prob - vegas_away_prob)
                
                probability_differences.append(prob_diff)
                
                # Track correctness
                model_correct.append(actual_winner == model_favorite)
                vegas_correct.append(actual_winner == vegas_favorite)
                
                # Calculate Kelly returns
                if model_favorite == prediction.home_team:
                    model_prob = prediction.home_win_prob
                    odds = vegas_line.home_odds
                else:
                    model_prob = prediction.away_win_prob
                    odds = vegas_line.away_odds
                
                if odds and model_prob > self.odds_to_probability(odds) + 0.05:  # 5% edge minimum
                    kelly_fraction = self.kelly_criterion(model_prob, odds)
                    
                    if actual_winner == model_favorite:
                        # Win
                        if odds > 0:
                            return_rate = kelly_fraction * (odds / 100)
                        else:
                            return_rate = kelly_fraction * (100 / abs(odds))
                    else:
                        # Loss
                        return_rate = -kelly_fraction
                    
                    kelly_returns.append(return_rate)
        
        # Calculate metrics
        total_predictions = len([p for p in predictions if f"{p.game_date.year}_{p.game_date.month:02d}_{p.away_team}_{p.home_team}" in lines_by_game])
        
        if total_predictions == 0:
            return ValidationMetrics(
                total_predictions=0,
                agreement_rate=0.0,
                avg_probability_difference=0.0,
                calibration_error=0.0,
                value_bet_accuracy=0.0,
                kelly_criterion_roi=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0
            )
        
        agreement_rate = agreements / total_predictions if total_predictions > 0 else 0
        avg_prob_diff = sum(probability_differences) / len(probability_differences) if probability_differences else 0
        
        # Calibration error (simplified)
        model_accuracy = sum(model_correct) / len(model_correct) if model_correct else 0
        avg_model_confidence = sum(p.win_probability for p in predictions) / len(predictions)
        calibration_error = abs(model_accuracy - avg_model_confidence)
        
        value_bet_accuracy = sum(model_correct) / len(model_correct) if model_correct else 0
        
        # Kelly criterion ROI
        kelly_roi = sum(kelly_returns) if kelly_returns else 0
        
        # Sharpe ratio (simplified - assuming risk-free rate of 0)
        if kelly_returns and len(kelly_returns) > 1:
            import statistics
            avg_return = statistics.mean(kelly_returns)
            return_std = statistics.stdev(kelly_returns)
            sharpe_ratio = avg_return / return_std if return_std > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Maximum drawdown
        if kelly_returns:
            cumulative_returns = []
            cumsum = 0
            for ret in kelly_returns:
                cumsum += ret
                cumulative_returns.append(cumsum)
            
            peak = cumulative_returns[0]
            max_drawdown = 0
            
            for value in cumulative_returns:
                if value > peak:
                    peak = value
                drawdown = peak - value
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        else:
            max_drawdown = 0
        
        return ValidationMetrics(
            total_predictions=total_predictions,
            agreement_rate=agreement_rate,
            avg_probability_difference=avg_prob_diff,
            calibration_error=calibration_error,
            value_bet_accuracy=value_bet_accuracy,
            kelly_criterion_roi=kelly_roi,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown
        )
    
    def get_upcoming_value_bets(self, weeks_ahead: int = 1,
                              season: Optional[int] = None,
                              min_edge: float = 0.05) -> List[ValueBet]:
        """Get value betting opportunities for upcoming games.
        
        Args:
            weeks_ahead: Number of weeks ahead to analyze
            season: Season year (defaults to current year)
            min_edge: Minimum edge required for value bet
            
        Returns:
            List of value betting opportunities
        """
        if not self.predictor.is_trained:
            raise ValueError("Model must be trained before finding value bets")
        
        current_season = season or datetime.now().year
        start_date = date.today()
        end_date = start_date + timedelta(weeks=weeks_ahead)
        
        # Get upcoming games
        upcoming_games = self.db_session.query(GameModel).filter(
            GameModel.season == current_season,
            GameModel.game_date >= start_date,
            GameModel.game_date <= end_date,
            GameModel.home_score.is_(None)  # Only games that haven't been played
        ).all()
        
        if not upcoming_games:
            return []
        
        # Get model predictions
        predictions = []
        for game in upcoming_games:
            try:
                prediction = self.predictor.predict_game(
                    home_team=game.home_team,
                    away_team=game.away_team,
                    game_date=game.game_date,
                    season=current_season
                )
                predictions.append(prediction)
            except Exception as e:
                logger.warning(f"Failed to predict {game.game_id}: {e}")
                continue
        
        # Create mock Vegas lines (in production, fetch from sportsbook APIs)
        vegas_lines = self.create_mock_vegas_lines(upcoming_games)
        
        # Find value bets
        value_bets = self.find_value_bets(predictions, vegas_lines, min_edge=min_edge)
        
        return value_bets