"""Prediction service for ML model operations."""

from typing import Optional, Dict, Any, List
from datetime import date
from sqlalchemy.orm import Session
from pathlib import Path
import logging

from .base import ServiceException, DatabaseError
from ..analysis.models import NFLPredictor, Prediction
from ..analysis.ml_optimizer import OptimizedNFLPredictor


class PredictionService:
    """Service class for prediction operations."""
    
    def __init__(self, db_session: Session, model_dir: Optional[str] = None):
        """Initialize prediction service.
        
        Args:
            db_session: Database session
            model_dir: Directory containing trained models
        """
        self.db = db_session
        self.model_dir = Path(model_dir) if model_dir else Path("models")
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize predictors
        self._basic_predictor: Optional[NFLPredictor] = None
        self._optimized_predictor: Optional[OptimizedNFLPredictor] = None
    
    @property
    def basic_predictor(self) -> NFLPredictor:
        """Get or initialize basic predictor."""
        if self._basic_predictor is None:
            self._basic_predictor = NFLPredictor(self.db, str(self.model_dir))
            
            # Try to load existing model
            try:
                self._basic_predictor.load_model("nfl_predictor")
            except Exception as e:
                self._logger.warning(f"Could not load basic model: {e}")
        
        return self._basic_predictor
    
    @property
    def optimized_predictor(self) -> OptimizedNFLPredictor:
        """Get or initialize optimized predictor."""
        if self._optimized_predictor is None:
            self._optimized_predictor = OptimizedNFLPredictor(self.db, str(self.model_dir))
            
            # Try to load existing optimized model
            try:
                model_path = self.model_dir / "nfl_predictor_optimized.pkl"
                if model_path.exists():
                    # Load the optimized model components
                    import pickle
                    with open(model_path, 'rb') as f:
                        model_data = pickle.load(f)
                    
                    self._optimized_predictor.model = model_data['model']
                    self._optimized_predictor.scaler = model_data['scaler']
                    self._optimized_predictor.feature_selector = model_data.get('feature_selector')
                    self._optimized_predictor.polynomial_features = model_data.get('polynomial_features')
                    self._optimized_predictor.ensemble_model = model_data.get('ensemble_model')
                    self._optimized_predictor.feature_names = model_data.get('feature_names')
                    self._optimized_predictor.is_trained = True
                    
                    self._logger.info("Loaded optimized model successfully")
            except Exception as e:
                self._logger.warning(f"Could not load optimized model: {e}")
        
        return self._optimized_predictor
    
    def predict_game(self, home_team: str, away_team: str, game_date: date,
                    season: int, use_optimized: bool = True) -> Prediction:
        """Predict game outcome.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            game_date: Game date
            season: Season year
            use_optimized: Use optimized model if available
            
        Returns:
            Prediction object with probabilities and metadata
            
        Raises:
            ServiceException: If prediction fails
        """
        try:
            # Try optimized model first if requested and available
            if use_optimized and self.has_optimized_model():
                predictor = self.optimized_predictor
                model_type = "optimized"
            else:
                predictor = self.basic_predictor
                model_type = "basic"
            
            # Check if model is trained
            if not predictor.is_trained:
                raise ServiceException(f"No trained {model_type} model available")
            
            # Make prediction
            prediction = predictor.predict_game(home_team, away_team, game_date, season)
            
            # Add metadata about which model was used
            prediction.model_type = model_type
            prediction.model_version = "1.0"
            
            self._logger.info(f"Predicted {away_team} @ {home_team} using {model_type} model: "
                            f"{prediction.predicted_winner} ({prediction.win_probability:.1%})")
            
            return prediction
            
        except Exception as e:
            self._logger.error(f"Error predicting game {away_team} @ {home_team}: {e}")
            raise ServiceException(f"Failed to predict game") from e
    
    def batch_predict(self, games: List[Dict[str, Any]], 
                     use_optimized: bool = True) -> List[Prediction]:
        """Predict multiple games in batch.
        
        Args:
            games: List of game dictionaries with keys: home_team, away_team, game_date, season
            use_optimized: Use optimized model if available
            
        Returns:
            List of predictions
            
        Raises:
            ServiceException: If batch prediction fails
        """
        try:
            predictions = []
            
            for game in games:
                try:
                    prediction = self.predict_game(
                        home_team=game['home_team'],
                        away_team=game['away_team'],
                        game_date=game['game_date'],
                        season=game['season'],
                        use_optimized=use_optimized
                    )
                    predictions.append(prediction)
                except Exception as e:
                    self._logger.warning(f"Failed to predict game {game}: {e}")
                    continue
            
            self._logger.info(f"Completed batch prediction for {len(predictions)}/{len(games)} games")
            return predictions
            
        except Exception as e:
            self._logger.error(f"Error in batch prediction: {e}")
            raise ServiceException("Failed to complete batch prediction") from e
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of available models.
        
        Returns:
            Dictionary with model status information
        """
        try:
            status = {
                "basic_model": {
                    "available": False,
                    "trained": False,
                    "accuracy": None,
                    "last_trained": None
                },
                "optimized_model": {
                    "available": False,
                    "trained": False,
                    "accuracy": None,
                    "last_trained": None
                }
            }
            
            # Check basic model
            try:
                basic_path = self.model_dir / "nfl_predictor.pkl"
                if basic_path.exists():
                    status["basic_model"]["available"] = True
                    if self._basic_predictor and self._basic_predictor.is_trained:
                        status["basic_model"]["trained"] = True
                        if self._basic_predictor.training_metrics:
                            status["basic_model"]["accuracy"] = self._basic_predictor.training_metrics.accuracy
            except Exception as e:
                self._logger.warning(f"Error checking basic model status: {e}")
            
            # Check optimized model
            try:
                optimized_path = self.model_dir / "nfl_predictor_optimized.pkl"
                if optimized_path.exists():
                    status["optimized_model"]["available"] = True
                    if self._optimized_predictor and self._optimized_predictor.is_trained:
                        status["optimized_model"]["trained"] = True
                        if self._optimized_predictor.training_metrics:
                            status["optimized_model"]["accuracy"] = self._optimized_predictor.training_metrics.accuracy
            except Exception as e:
                self._logger.warning(f"Error checking optimized model status: {e}")
            
            return status
            
        except Exception as e:
            self._logger.error(f"Error getting model status: {e}")
            raise ServiceException("Failed to get model status") from e
    
    def has_basic_model(self) -> bool:
        """Check if basic model is available and trained."""
        try:
            return (self.model_dir / "nfl_predictor.pkl").exists() and self.basic_predictor.is_trained
        except:
            return False
    
    def has_optimized_model(self) -> bool:
        """Check if optimized model is available and trained."""
        try:
            return (self.model_dir / "nfl_predictor_optimized.pkl").exists() and self.optimized_predictor.is_trained
        except:
            return False
    
    def train_basic_model(self, seasons: List[int], test_size: float = 0.2) -> Dict[str, Any]:
        """Train basic prediction model.
        
        Args:
            seasons: List of seasons to train on
            test_size: Proportion of data for testing
            
        Returns:
            Dictionary with training results
            
        Raises:
            ServiceException: If training fails
        """
        try:
            self._logger.info(f"Starting basic model training for seasons {seasons}")
            
            predictor = self.basic_predictor
            metrics = predictor.train(seasons, test_size)
            
            # Save trained model
            predictor.save_model("nfl_predictor")
            
            result = {
                "model_type": "basic",
                "seasons": seasons,
                "test_size": test_size,
                "accuracy": metrics.accuracy,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1_score,
                "samples": metrics.samples,
                "success": True
            }
            
            self._logger.info(f"Basic model training completed. Accuracy: {metrics.accuracy:.4f}")
            return result
            
        except Exception as e:
            self._logger.error(f"Error training basic model: {e}")
            raise ServiceException("Failed to train basic model") from e
    
    def train_optimized_model(self, seasons: List[int], test_size: float = 0.2) -> Dict[str, Any]:
        """Train optimized prediction model.
        
        Args:
            seasons: List of seasons to train on
            test_size: Proportion of data for testing
            
        Returns:
            Dictionary with training results
            
        Raises:
            ServiceException: If training fails
        """
        try:
            self._logger.info(f"Starting optimized model training for seasons {seasons}")
            
            predictor = self.optimized_predictor
            metrics = predictor.train_optimized(seasons, test_size)
            
            # Save trained model
            predictor.save_optimized_model("nfl_predictor_optimized")
            
            result = {
                "model_type": "optimized",
                "seasons": seasons,
                "test_size": test_size,
                "accuracy": metrics.accuracy,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1_score": metrics.f1_score,
                "roc_auc": metrics.roc_auc,
                "samples": metrics.samples,
                "cross_val_scores": metrics.cross_val_scores,
                "calibration_score": metrics.calibration_score,
                "feature_importance": dict(list(metrics.feature_importance.items())[:10]),  # Top 10 features
                "success": True
            }
            
            self._logger.info(f"Optimized model training completed. Accuracy: {metrics.accuracy:.4f}")
            return result
            
        except Exception as e:
            self._logger.error(f"Error training optimized model: {e}")
            raise ServiceException("Failed to train optimized model") from e
    
    def compare_models(self, test_games: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare basic and optimized model performance on test games.
        
        Args:
            test_games: List of test games with actual results
            
        Returns:
            Dictionary with comparison results
            
        Raises:
            ServiceException: If comparison fails
        """
        try:
            if not self.has_basic_model() or not self.has_optimized_model():
                raise ServiceException("Both models must be available for comparison")
            
            basic_correct = 0
            optimized_correct = 0
            total_games = 0
            
            for game in test_games:
                try:
                    # Get actual result
                    actual_winner = game.get('actual_winner')
                    if not actual_winner:
                        continue
                    
                    # Basic model prediction
                    basic_pred = self.predict_game(
                        game['home_team'], game['away_team'], 
                        game['game_date'], game['season'], use_optimized=False
                    )
                    
                    # Optimized model prediction
                    optimized_pred = self.predict_game(
                        game['home_team'], game['away_team'],
                        game['game_date'], game['season'], use_optimized=True
                    )
                    
                    # Check accuracy
                    if basic_pred.predicted_winner == actual_winner:
                        basic_correct += 1
                    
                    if optimized_pred.predicted_winner == actual_winner:
                        optimized_correct += 1
                    
                    total_games += 1
                    
                except Exception as e:
                    self._logger.warning(f"Failed to compare models on game {game}: {e}")
                    continue
            
            if total_games == 0:
                raise ServiceException("No valid test games for comparison")
            
            basic_accuracy = basic_correct / total_games
            optimized_accuracy = optimized_correct / total_games
            
            result = {
                "total_games": total_games,
                "basic_model": {
                    "correct_predictions": basic_correct,
                    "accuracy": basic_accuracy
                },
                "optimized_model": {
                    "correct_predictions": optimized_correct,
                    "accuracy": optimized_accuracy
                },
                "improvement": optimized_accuracy - basic_accuracy,
                "improvement_percentage": ((optimized_accuracy - basic_accuracy) / basic_accuracy) * 100 if basic_accuracy > 0 else 0
            }
            
            self._logger.info(f"Model comparison completed. Basic: {basic_accuracy:.1%}, "
                            f"Optimized: {optimized_accuracy:.1%}, "
                            f"Improvement: {result['improvement_percentage']:+.1f}%")
            
            return result
            
        except Exception as e:
            self._logger.error(f"Error comparing models: {e}")
            raise ServiceException("Failed to compare models") from e