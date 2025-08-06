"""Vegas lines and value betting API endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime
from pydantic import BaseModel, Field
import logging

from ...analysis.vegas import VegasValidator, BetType, ValueBet, ValidationMetrics
from ...analysis.models import NFLPredictor
from ...models.game import GameModel
from ..dependencies import get_db_session
from .predictions import get_predictor

logger = logging.getLogger(__name__)

router = APIRouter()


class ValueBetResponse(BaseModel):
    """Response schema for value bet."""
    game_id: str
    home_team: str
    away_team: str
    game_date: date
    bet_type: str
    recommendation: str
    model_probability: float = Field(..., ge=0.0, le=1.0)
    vegas_probability: float = Field(..., ge=0.0, le=1.0)
    expected_value: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    
    class Config:
        from_attributes = True


class ValidationResponse(BaseModel):
    """Response schema for model validation."""
    total_predictions: int = Field(..., ge=0)
    agreement_rate: float = Field(..., ge=0.0, le=1.0)
    avg_probability_difference: float = Field(..., ge=0.0, le=1.0)
    calibration_error: float = Field(..., ge=0.0)
    value_bet_accuracy: float = Field(..., ge=0.0, le=1.0)
    kelly_criterion_roi: float
    sharpe_ratio: float
    max_drawdown: float = Field(..., ge=0.0)
    
    class Config:
        from_attributes = True


def get_vegas_validator(
    predictor: NFLPredictor = Depends(get_predictor),
    db: Session = Depends(get_db_session)
) -> VegasValidator:
    """Get or create Vegas validator instance."""
    return VegasValidator(db, predictor)


@router.get("/value-bets", response_model=List[ValueBetResponse])
async def get_value_bets(
    weeks_ahead: int = Query(1, ge=1, le=4, description="Weeks ahead to analyze"),
    season: Optional[int] = Query(None, description="Season year"),
    min_edge: float = Query(0.05, ge=0.01, le=0.20, description="Minimum edge required"),
    min_confidence: float = Query(0.6, ge=0.1, le=1.0, description="Minimum model confidence"),
    validator: VegasValidator = Depends(get_vegas_validator)
):
    """Get value betting opportunities for upcoming games.
    
    This endpoint identifies games where our model disagrees significantly
    with Vegas odds, potentially indicating value betting opportunities.
    """
    try:
        if not validator.predictor.is_trained:
            raise HTTPException(
                status_code=400,
                detail="Model must be trained before finding value bets. Please train the model first."
            )
        
        # Get value bets
        value_bets = validator.get_upcoming_value_bets(
            weeks_ahead=weeks_ahead,
            season=season,
            min_edge=min_edge
        )
        
        # Filter by confidence
        filtered_bets = [
            bet for bet in value_bets 
            if bet.confidence >= min_confidence
        ]
        
        # Convert to response format
        response_bets = []
        for bet in filtered_bets:
            response_bet = ValueBetResponse(
                game_id=bet.game_id,
                home_team=bet.home_team,
                away_team=bet.away_team,
                game_date=bet.game_date,
                bet_type=bet.bet_type.value,
                recommendation=bet.recommendation,
                model_probability=bet.model_probability,
                vegas_probability=bet.vegas_probability,
                expected_value=bet.expected_value,
                confidence=bet.confidence,
                reasoning=bet.reasoning
            )
            response_bets.append(response_bet)
        
        return response_bets
    
    except Exception as e:
        logger.error(f"Failed to get value bets: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get value bets: {str(e)}"
        )


@router.post("/validate")
async def validate_model(
    start_date: date = Query(..., description="Start date for validation period"),
    end_date: date = Query(..., description="End date for validation period"),
    season: Optional[int] = Query(None, description="Season year"),
    validator: VegasValidator = Depends(get_vegas_validator),
    db: Session = Depends(get_db_session)
):
    """Validate model performance against Vegas lines and actual results.
    
    This endpoint compares model predictions to Vegas lines and actual game
    outcomes to measure prediction quality and identify systematic biases.
    """
    try:
        if not validator.predictor.is_trained:
            raise HTTPException(
                status_code=400,
                detail="Model must be trained before validation. Please train the model first."
            )
        
        current_season = season or start_date.year
        
        # Get completed games in the validation period
        completed_games = db.query(GameModel).filter(
            GameModel.season == current_season,
            GameModel.game_date >= start_date,
            GameModel.game_date <= end_date,
            GameModel.home_score.isnot(None),
            GameModel.away_score.isnot(None)
        ).all()
        
        if not completed_games:
            raise HTTPException(
                status_code=404,
                detail="No completed games found in the specified period"
            )
        
        # Generate predictions for these games
        predictions = []
        actual_results = []
        
        for game in completed_games:
            try:
                prediction = validator.predictor.predict_game(
                    home_team=game.home_team,
                    away_team=game.away_team,
                    game_date=game.game_date,
                    season=current_season
                )
                predictions.append(prediction)
                
                # Determine actual winner
                if game.home_score > game.away_score:
                    actual_winner = game.home_team
                    actual_loser = game.away_team
                elif game.home_score < game.away_score:
                    actual_winner = game.away_team
                    actual_loser = game.home_team
                else:
                    # Skip ties
                    continue
                
                actual_results.append((actual_winner, actual_loser))
                
            except Exception as e:
                logger.warning(f"Failed to predict/analyze {game.game_id}: {e}")
                continue
        
        if not predictions:
            raise HTTPException(
                status_code=404,
                detail="No valid predictions could be generated for the specified period"
            )
        
        # Create mock Vegas lines for validation
        vegas_lines = validator.create_mock_vegas_lines(completed_games)
        
        # Validate predictions
        validation_metrics = validator.validate_predictions(
            predictions, vegas_lines, actual_results
        )
        
        # Convert to response format
        response = ValidationResponse(
            total_predictions=validation_metrics.total_predictions,
            agreement_rate=validation_metrics.agreement_rate,
            avg_probability_difference=validation_metrics.avg_probability_difference,
            calibration_error=validation_metrics.calibration_error,
            value_bet_accuracy=validation_metrics.value_bet_accuracy,
            kelly_criterion_roi=validation_metrics.kelly_criterion_roi,
            sharpe_ratio=validation_metrics.sharpe_ratio,
            max_drawdown=validation_metrics.max_drawdown
        )
        
        return {
            "message": f"Validated model on {len(predictions)} completed games",
            "validation_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "season": current_season,
                "games_analyzed": len(completed_games)
            },
            "metrics": response,
            "interpretation": {
                "agreement_with_vegas": "High" if validation_metrics.agreement_rate > 0.7 else 
                                      "Medium" if validation_metrics.agreement_rate > 0.5 else "Low",
                "calibration_quality": "Good" if validation_metrics.calibration_error < 0.1 else
                                     "Fair" if validation_metrics.calibration_error < 0.2 else "Poor",
                "value_betting_potential": "High" if validation_metrics.kelly_criterion_roi > 0.1 else
                                         "Medium" if validation_metrics.kelly_criterion_roi > 0.05 else "Low"
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model validation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Model validation failed: {str(e)}"
        )


@router.get("/odds-calculator")
async def calculate_odds(
    probability: float = Query(..., ge=0.01, le=0.99, description="Probability (0.01 to 0.99)"),
    validator: VegasValidator = Depends(get_vegas_validator)
):
    """Convert probability to American odds format.
    
    Utility endpoint to convert win probabilities to American odds format
    commonly used by sportsbooks.
    """
    try:
        american_odds = validator.probability_to_odds(probability)
        
        return {
            "probability": probability,
            "american_odds": american_odds,
            "decimal_odds": round(1 / probability, 2),
            "fractional_odds": f"{int(100 * (1 - probability))}:{int(100 * probability)}",
            "implied_probability": probability,
            "interpretation": {
                "favorite_or_underdog": "Favorite" if probability > 0.5 else "Underdog",
                "confidence_level": "Very High" if probability > 0.8 else
                                  "High" if probability > 0.65 else
                                  "Medium" if probability > 0.35 else "Low"
            }
        }
    
    except Exception as e:
        logger.error(f"Odds calculation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Odds calculation failed: {str(e)}"
        )


@router.get("/probability-calculator")
async def calculate_probability(
    american_odds: int = Query(..., ge=-1000, le=1000, description="American odds (-1000 to +1000)"),
    validator: VegasValidator = Depends(get_vegas_validator)
):
    """Convert American odds to implied probability.
    
    Utility endpoint to convert sportsbook odds to implied win probabilities.
    """
    try:
        if american_odds == 0:
            raise HTTPException(
                status_code=400,
                detail="American odds cannot be 0"
            )
        
        probability = validator.odds_to_probability(american_odds)
        
        return {
            "american_odds": american_odds,
            "implied_probability": round(probability, 4),
            "percentage": f"{round(probability * 100, 2)}%",
            "decimal_odds": round(1 / probability, 2),
            "interpretation": {
                "favorite_or_underdog": "Favorite" if american_odds < 0 else "Underdog",
                "confidence_level": "Very High" if probability > 0.8 else
                                  "High" if probability > 0.65 else
                                  "Medium" if probability > 0.35 else "Low",
                "betting_advice": "Strong favorite" if probability > 0.75 else
                                "Moderate favorite" if probability > 0.55 else
                                "Pick 'em" if 0.45 <= probability <= 0.55 else
                                "Moderate underdog" if probability > 0.25 else
                                "Long shot"
            }
        }
    
    except Exception as e:
        logger.error(f"Probability calculation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Probability calculation failed: {str(e)}"
        )


@router.post("/expected-value")
async def calculate_expected_value(
    model_probability: float = Query(..., ge=0.01, le=0.99, description="Model's predicted probability"),
    american_odds: int = Query(..., ge=-1000, le=1000, description="Sportsbook odds"),
    bet_size: float = Query(1.0, ge=0.01, le=1000.0, description="Bet size in units"),
    validator: VegasValidator = Depends(get_vegas_validator)
):
    """Calculate expected value and Kelly criterion for a potential bet.
    
    This endpoint helps determine if a bet has positive expected value
    and suggests optimal bet sizing using the Kelly criterion.
    """
    try:
        if american_odds == 0:
            raise HTTPException(
                status_code=400,
                detail="American odds cannot be 0"
            )
        
        # Calculate expected value
        expected_value = validator.calculate_expected_value(
            model_probability, american_odds, bet_size
        )
        
        # Calculate Kelly criterion
        kelly_fraction = validator.kelly_criterion(model_probability, american_odds)
        
        # Calculate Vegas implied probability
        vegas_probability = validator.odds_to_probability(american_odds)
        
        # Calculate edge
        edge = model_probability - vegas_probability
        
        return {
            "model_probability": model_probability,
            "vegas_probability": round(vegas_probability, 4),
            "american_odds": american_odds,
            "bet_size": bet_size,
            "expected_value": round(expected_value, 4),
            "edge": round(edge, 4),
            "kelly_fraction": round(kelly_fraction, 4),
            "kelly_bet_size": round(kelly_fraction * 100, 2),  # As percentage of bankroll
            "analysis": {
                "has_edge": edge > 0,
                "expected_value_per_unit": round(expected_value / bet_size, 4),
                "edge_percentage": f"{round(edge * 100, 2)}%",
                "recommendation": "Strong bet" if edge > 0.1 and kelly_fraction > 0.05 else
                                "Value bet" if edge > 0.05 and kelly_fraction > 0.02 else
                                "Marginal bet" if edge > 0.02 and kelly_fraction > 0.01 else
                                "Avoid bet" if edge <= 0 else
                                "Weak edge - proceed with caution",
                "risk_assessment": "Low" if kelly_fraction < 0.05 else
                                 "Medium" if kelly_fraction < 0.15 else "High"
            }
        }
    
    except Exception as e:
        logger.error(f"Expected value calculation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Expected value calculation failed: {str(e)}"
        )