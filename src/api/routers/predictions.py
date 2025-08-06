"""Predictions API endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field
import logging

from ...analysis.models import NFLPredictor, Prediction
from ...models.game import GameModel
from ..dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()

# Global predictor instance
predictor_instance = None


def get_predictor(db: Session = Depends(get_db_session)) -> NFLPredictor:
    """Get or create predictor instance."""
    global predictor_instance
    if predictor_instance is None:
        predictor_instance = NFLPredictor(db)
        # Try to load existing model
        try:
            predictor_instance.load_model()
            logger.info("Loaded existing NFL prediction model")
        except FileNotFoundError:
            logger.info("No existing model found - will need to train first")
    
    return predictor_instance


class PredictionRequest(BaseModel):
    """Request schema for game prediction."""
    home_team: str = Field(..., min_length=2, max_length=3, description="Home team abbreviation")
    away_team: str = Field(..., min_length=2, max_length=3, description="Away team abbreviation") 
    game_date: date = Field(..., description="Game date")
    season: Optional[int] = Field(None, description="Season year (defaults to current year)")


class PredictionResponse(BaseModel):
    """Response schema for game prediction."""
    home_team: str
    away_team: str
    game_date: date
    predicted_winner: str
    win_probability: float
    home_win_prob: float
    away_win_prob: float
    confidence: float
    season: int
    
    class Config:
        from_attributes = True


class TrainingRequest(BaseModel):
    """Request schema for model training."""
    seasons: List[int] = Field(..., description="Seasons to use for training")
    test_size: float = Field(0.2, ge=0.1, le=0.5, description="Test size fraction")
    optimize_hyperparameters: bool = Field(False, description="Whether to optimize hyperparameters")
    min_games_played: int = Field(4, ge=1, le=10, description="Minimum games played before including in training")


class TrainingResponse(BaseModel):
    """Response schema for model training."""
    success: bool
    message: str
    training_samples: int
    validation_samples: int
    training_accuracy: float
    validation_accuracy: float
    feature_count: int
    training_time_seconds: Optional[float] = None


@router.post("/train", response_model=TrainingResponse)
async def train_model(
    training_request: TrainingRequest,
    background_tasks: BackgroundTasks,
    predictor: NFLPredictor = Depends(get_predictor)
):
    """Train the NFL prediction model."""
    try:
        start_time = datetime.now()
        
        # Train the model
        predictor.train(
            seasons=training_request.seasons,
            test_size=training_request.test_size,
            optimize_hyperparameters=training_request.optimize_hyperparameters,
            min_games_played=training_request.min_games_played
        )
        
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Save the trained model
        predictor.save_model()
        
        return TrainingResponse(
            success=True,
            message=f"Model trained successfully on {len(training_request.seasons)} seasons",
            training_samples=predictor.training_metrics.samples,
            validation_samples=predictor.validation_metrics.samples,
            training_accuracy=predictor.training_metrics.accuracy,
            validation_accuracy=predictor.validation_metrics.accuracy,
            feature_count=len(predictor.feature_names),
            training_time_seconds=training_time
        )
    
    except Exception as e:
        logger.error(f"Model training failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Model training failed: {str(e)}")


@router.post("/predict", response_model=PredictionResponse)
async def predict_game(
    prediction_request: PredictionRequest,
    predictor: NFLPredictor = Depends(get_predictor)
):
    """Predict the outcome of a single game."""
    if not predictor.is_trained:
        raise HTTPException(
            status_code=400, 
            detail="Model has not been trained yet. Please train the model first."
        )
    
    try:
        season = prediction_request.season or prediction_request.game_date.year
        
        prediction = predictor.predict_game(
            home_team=prediction_request.home_team.upper(),
            away_team=prediction_request.away_team.upper(),
            game_date=prediction_request.game_date,
            season=season
        )
        
        return PredictionResponse(
            home_team=prediction.home_team,
            away_team=prediction.away_team,
            game_date=prediction.game_date,
            predicted_winner=prediction.predicted_winner,
            win_probability=prediction.win_probability,
            home_win_prob=prediction.home_win_prob,
            away_win_prob=prediction.away_win_prob,
            confidence=prediction.confidence,
            season=season
        )
    
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/predict/upcoming")
async def predict_upcoming_games(
    weeks_ahead: int = Query(1, ge=1, le=4, description="Number of weeks ahead to predict"),
    season: Optional[int] = Query(None, description="Season year"),
    predictor: NFLPredictor = Depends(get_predictor),
    db: Session = Depends(get_db_session)
):
    """Predict upcoming games in the next N weeks."""
    if not predictor.is_trained:
        raise HTTPException(
            status_code=400, 
            detail="Model has not been trained yet. Please train the model first."
        )
    
    try:
        current_season = season or datetime.now().year
        start_date = date.today()
        end_date = start_date + timedelta(weeks=weeks_ahead)
        
        # Get upcoming games from database
        upcoming_games = db.query(GameModel).filter(
            GameModel.season == current_season,
            GameModel.game_date >= start_date,
            GameModel.game_date <= end_date,
            GameModel.home_score.is_(None)  # Only games that haven't been played
        ).all()
        
        if not upcoming_games:
            return {
                "message": f"No upcoming games found in the next {weeks_ahead} weeks",
                "predictions": [],
                "total_games": 0
            }
        
        # Make predictions for each game
        predictions = []
        for game in upcoming_games:
            try:
                prediction = predictor.predict_game(
                    home_team=game.home_team,
                    away_team=game.away_team,
                    game_date=game.game_date,
                    season=current_season
                )
                
                pred_dict = prediction.to_dict()
                pred_dict['game_id'] = game.game_id
                pred_dict['week'] = game.week
                predictions.append(pred_dict)
                
            except Exception as e:
                logger.warning(f"Failed to predict {game.game_id}: {e}")
                continue
        
        # Sort by game date
        predictions.sort(key=lambda x: x['game_date'])
        
        return {
            "message": f"Generated {len(predictions)} predictions for upcoming games",
            "predictions": predictions,
            "total_games": len(predictions),
            "weeks_ahead": weeks_ahead
        }
    
    except Exception as e:
        logger.error(f"Failed to predict upcoming games: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to predict upcoming games: {str(e)}")


@router.get("/model/status")
async def get_model_status(predictor: NFLPredictor = Depends(get_predictor)):
    """Get current model status and performance metrics."""
    try:
        status = {
            "is_trained": predictor.is_trained,
            "feature_count": len(predictor.feature_names) if predictor.is_trained else 0,
            "model_type": "Random Forest Classifier"
        }
        
        if predictor.is_trained:
            status["training_metrics"] = predictor.training_metrics.to_dict() if predictor.training_metrics else None
            status["validation_metrics"] = predictor.validation_metrics.to_dict() if predictor.validation_metrics else None
            
            # Get feature importance
            try:
                feature_importance = predictor.get_feature_importance(top_n=10)
                status["top_features"] = feature_importance
            except Exception as e:
                logger.warning(f"Could not get feature importance: {e}")
                status["top_features"] = {}
        
        return status
    
    except Exception as e:
        logger.error(f"Failed to get model status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get model status: {str(e)}")


@router.post("/evaluate")
async def evaluate_model(
    start_date: date = Query(..., description="Start date for evaluation period"),
    end_date: date = Query(..., description="End date for evaluation period"),
    season: Optional[int] = Query(None, description="Season year"),
    predictor: NFLPredictor = Depends(get_predictor),
    db: Session = Depends(get_db_session)
):
    """Evaluate model performance on historical games."""
    if not predictor.is_trained:
        raise HTTPException(
            status_code=400, 
            detail="Model has not been trained yet. Please train the model first."
        )
    
    try:
        current_season = season or start_date.year
        
        # Get completed games in the evaluation period
        completed_games = db.query(GameModel).filter(
            GameModel.season == current_season,
            GameModel.game_date >= start_date,
            GameModel.game_date <= end_date,
            GameModel.home_score.isnot(None),
            GameModel.away_score.isnot(None)
        ).all()
        
        if not completed_games:
            return {
                "message": "No completed games found in the specified period",
                "evaluation": None,
                "total_games": 0
            }
        
        # Make predictions for each game
        predictions = []
        actual_results = []
        
        for game in completed_games:
            try:
                prediction = predictor.predict_game(
                    home_team=game.home_team,
                    away_team=game.away_team,
                    game_date=game.game_date,
                    season=current_season
                )
                
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
                
                predictions.append(prediction)
                actual_results.append((actual_winner, actual_loser))
                
            except Exception as e:
                logger.warning(f"Failed to predict {game.game_id} for evaluation: {e}")
                continue
        
        if not predictions:
            return {
                "message": "No valid predictions could be made for evaluation",
                "evaluation": None,
                "total_games": 0
            }
        
        # Evaluate predictions
        evaluation_metrics = predictor.evaluate_predictions(predictions, actual_results)
        
        return {
            "message": f"Evaluated model on {len(predictions)} games",
            "evaluation": evaluation_metrics,
            "total_games": len(predictions),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "season": current_season
            }
        }
    
    except Exception as e:
        logger.error(f"Model evaluation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Model evaluation failed: {str(e)}")