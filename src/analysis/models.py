"""Machine learning models for NFL prediction."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
import pickle
import json
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sqlalchemy.orm import Session

from .features import FeatureEngineer
from ..models.game import GameModel

logger = logging.getLogger(__name__)


@dataclass
class ModelMetrics:
    """Container for model performance metrics."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    samples: int
    
    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to dictionary."""
        return {
            'accuracy': self.accuracy,
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'roc_auc': self.roc_auc,
            'samples': self.samples
        }


@dataclass
class Prediction:
    """Container for game prediction."""
    home_team: str
    away_team: str
    game_date: date
    predicted_winner: str
    win_probability: float
    home_win_prob: float
    away_win_prob: float
    confidence: float
    features: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prediction to dictionary."""
        return {
            'home_team': self.home_team,
            'away_team': self.away_team,
            'game_date': self.game_date.isoformat(),
            'predicted_winner': self.predicted_winner,
            'win_probability': self.win_probability,
            'home_win_prob': self.home_win_prob,
            'away_win_prob': self.away_win_prob,
            'confidence': self.confidence,
            'features': self.features
        }


class NFLPredictor:
    """Random Forest model for NFL game prediction."""
    
    def __init__(self, db_session: Session, model_dir: Optional[str] = None):
        """Initialize NFL predictor.
        
        Args:
            db_session: Database session
            model_dir: Directory to save/load models
        """
        self.db_session = db_session
        self.feature_engineer = FeatureEngineer(db_session)
        self.model_dir = Path(model_dir) if model_dir else Path("models")
        self.model_dir.mkdir(exist_ok=True)
        
        # Model components
        self.model: Optional[RandomForestClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: List[str] = []
        self.is_trained = False
        self.training_metrics: Optional[ModelMetrics] = None
        self.validation_metrics: Optional[ModelMetrics] = None
    
    def prepare_training_data(self, seasons: List[int], 
                            min_games_played: int = 4) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data from historical games.
        
        Args:
            seasons: List of seasons to include
            min_games_played: Minimum games played before including in training
            
        Returns:
            Tuple of features DataFrame and target Series
        """
        logger.info(f"Preparing training data for seasons {seasons}")
        
        training_data = []
        
        for season in seasons:
            logger.info(f"Processing season {season}")
            
            # Get all games for the season
            games = self.db_session.query(GameModel).filter(
                GameModel.season == season,
                GameModel.home_score.isnot(None),
                GameModel.away_score.isnot(None)
            ).order_by(GameModel.game_date).all()
            
            logger.info(f"Found {len(games)} games in {season}")
            
            for game in games:
                # Skip games early in season if both teams haven't played enough
                home_stats = self.feature_engineer.get_team_stats(
                    game.home_team, season, game.game_date
                )
                away_stats = self.feature_engineer.get_team_stats(
                    game.away_team, season, game.game_date
                )
                
                if (home_stats.games_played < min_games_played or 
                    away_stats.games_played < min_games_played):
                    continue
                
                # Create features
                try:
                    features = self.feature_engineer.create_game_features(
                        game.home_team, game.away_team, game.game_date, season
                    )
                    
                    # Determine target (1 if home team wins, 0 if away team wins)
                    if game.home_score > game.away_score:
                        target = 1  # Home win
                    elif game.home_score < game.away_score:
                        target = 0  # Away win
                    else:
                        # Skip ties for binary classification
                        continue
                    
                    # Add game metadata
                    features.update({
                        'game_id': game.game_id,
                        'season': season,
                        'home_team': game.home_team,
                        'away_team': game.away_team,
                        'target': target
                    })
                    
                    training_data.append(features)
                    
                except Exception as e:
                    logger.warning(f"Failed to create features for {game.game_id}: {e}")
                    continue
        
        if not training_data:
            raise ValueError("No training data could be generated")
        
        df = pd.DataFrame(training_data)
        logger.info(f"Created training dataset with {len(df)} samples")
        
        # Separate features and targets
        feature_cols = [col for col in df.columns if col not in 
                       ['game_id', 'season', 'home_team', 'away_team', 'target']]
        
        X = df[feature_cols]
        y = df['target']
        
        # Store feature names
        self.feature_names = feature_cols
        
        # Handle missing values
        X = X.fillna(0)
        
        logger.info(f"Feature matrix shape: {X.shape}")
        logger.info(f"Target distribution: {y.value_counts().to_dict()}")
        
        return X, y
    
    def train(self, seasons: List[int], test_size: float = 0.2, 
              optimize_hyperparameters: bool = True, **kwargs) -> None:
        """Train the Random Forest model.
        
        Args:
            seasons: Seasons to use for training
            test_size: Fraction of data to use for testing
            optimize_hyperparameters: Whether to perform grid search
            **kwargs: Additional arguments for RandomForestClassifier
        """
        logger.info("Starting model training")
        
        # Prepare training data
        X, y = self.prepare_training_data(seasons)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Set default parameters
        default_params = {
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'random_state': 42,
            'n_jobs': -1
        }
        default_params.update(kwargs)
        
        if optimize_hyperparameters:
            logger.info("Optimizing hyperparameters with grid search")
            
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [5, 10, 15, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
            
            rf = RandomForestClassifier(random_state=42, n_jobs=-1)
            grid_search = GridSearchCV(
                rf, param_grid, cv=5, scoring='accuracy', n_jobs=-1, verbose=1
            )
            
            grid_search.fit(X_train_scaled, y_train)
            self.model = grid_search.best_estimator_
            
            logger.info(f"Best parameters: {grid_search.best_params_}")
            logger.info(f"Best cross-validation score: {grid_search.best_score_:.3f}")
        else:
            # Train with default/provided parameters
            self.model = RandomForestClassifier(**default_params)
            self.model.fit(X_train_scaled, y_train)
        
        # Calculate training metrics
        train_pred = self.model.predict(X_train_scaled)
        train_pred_proba = self.model.predict_proba(X_train_scaled)[:, 1]
        
        self.training_metrics = ModelMetrics(
            accuracy=accuracy_score(y_train, train_pred),
            precision=precision_score(y_train, train_pred),
            recall=recall_score(y_train, train_pred),
            f1_score=f1_score(y_train, train_pred),
            roc_auc=roc_auc_score(y_train, train_pred_proba),
            samples=len(y_train)
        )
        
        # Calculate validation metrics
        test_pred = self.model.predict(X_test_scaled)
        test_pred_proba = self.model.predict_proba(X_test_scaled)[:, 1]
        
        self.validation_metrics = ModelMetrics(
            accuracy=accuracy_score(y_test, test_pred),
            precision=precision_score(y_test, test_pred),
            recall=recall_score(y_test, test_pred),
            f1_score=f1_score(y_test, test_pred),
            roc_auc=roc_auc_score(y_test, test_pred_proba),
            samples=len(y_test)
        )
        
        self.is_trained = True
        
        logger.info("Model training completed")
        logger.info(f"Training accuracy: {self.training_metrics.accuracy:.3f}")
        logger.info(f"Validation accuracy: {self.validation_metrics.accuracy:.3f}")
        logger.info(f"Validation ROC AUC: {self.validation_metrics.roc_auc:.3f}")
    
    def predict_game(self, home_team: str, away_team: str, 
                    game_date: date, season: int) -> Prediction:
        """Predict the outcome of a single game.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            game_date: Game date
            season: Season year
            
        Returns:
            Prediction object with results
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Create features
        features = self.feature_engineer.create_game_features(
            home_team, away_team, game_date, season
        )
        
        # Convert to DataFrame and align with training features
        feature_df = pd.DataFrame([features])
        
        # Ensure all training features are present
        for feature_name in self.feature_names:
            if feature_name not in feature_df.columns:
                feature_df[feature_name] = 0
        
        # Select and order features to match training
        feature_df = feature_df[self.feature_names].fillna(0)
        
        # Scale features
        feature_scaled = self.scaler.transform(feature_df)
        
        # Make prediction
        prediction_proba = self.model.predict_proba(feature_scaled)[0]
        home_win_prob = prediction_proba[1]
        away_win_prob = prediction_proba[0]
        
        # Determine predicted winner
        predicted_winner = home_team if home_win_prob > away_win_prob else away_team
        win_probability = max(home_win_prob, away_win_prob)
        
        # Calculate confidence (how far from 50/50 the prediction is)
        confidence = abs(home_win_prob - 0.5) * 2
        
        return Prediction(
            home_team=home_team,
            away_team=away_team,
            game_date=game_date,
            predicted_winner=predicted_winner,
            win_probability=win_probability,
            home_win_prob=home_win_prob,
            away_win_prob=away_win_prob,
            confidence=confidence,
            features=features
        )
    
    def predict_games(self, games: List[Tuple[str, str, date, int]]) -> List[Prediction]:
        """Predict outcomes for multiple games.
        
        Args:
            games: List of (home_team, away_team, game_date, season) tuples
            
        Returns:
            List of Prediction objects
        """
        predictions = []
        
        for home_team, away_team, game_date, season in games:
            try:
                prediction = self.predict_game(home_team, away_team, game_date, season)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"Failed to predict {home_team} vs {away_team}: {e}")
        
        return predictions
    
    def get_feature_importance(self, top_n: int = 20) -> Dict[str, float]:
        """Get feature importance from trained model.
        
        Args:
            top_n: Number of top features to return
            
        Returns:
            Dictionary of feature names and importance scores
        """
        if not self.is_trained:
            raise ValueError("Model must be trained first")
        
        importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))
        
        # Sort by importance and return top N
        sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_features[:top_n])
    
    def save_model(self, name: str = "nfl_predictor") -> None:
        """Save trained model to disk.
        
        Args:
            name: Model name for saving
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        model_path = self.model_dir / f"{name}.pkl"
        metadata_path = self.model_dir / f"{name}_metadata.json"
        
        # Save model and scaler
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        # Save metadata
        metadata = {
            'trained_at': datetime.now().isoformat(),
            'feature_count': len(self.feature_names),
            'training_metrics': self.training_metrics.to_dict() if self.training_metrics else None,
            'validation_metrics': self.validation_metrics.to_dict() if self.validation_metrics else None
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
    
    def load_model(self, name: str = "nfl_predictor") -> None:
        """Load trained model from disk.
        
        Args:
            name: Model name to load
        """
        model_path = self.model_dir / f"{name}.pkl"
        metadata_path = self.model_dir / f"{name}_metadata.json"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file {model_path} not found")
        
        # Load model components
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.is_trained = True
        
        # Load metadata if available
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            if metadata.get('training_metrics'):
                metrics_data = metadata['training_metrics']
                self.training_metrics = ModelMetrics(**metrics_data)
            
            if metadata.get('validation_metrics'):
                metrics_data = metadata['validation_metrics']
                self.validation_metrics = ModelMetrics(**metrics_data)
        
        logger.info(f"Model loaded from {model_path}")
    
    def evaluate_predictions(self, predictions: List[Prediction], 
                           actual_results: List[Tuple[str, str]]) -> Dict[str, float]:
        """Evaluate prediction accuracy against actual results.
        
        Args:
            predictions: List of predictions
            actual_results: List of (winner, loser) tuples
            
        Returns:
            Dictionary of evaluation metrics
        """
        if len(predictions) != len(actual_results):
            raise ValueError("Predictions and actual results must have same length")
        
        correct = 0
        total_confidence = 0
        total_calibration_error = 0
        
        for pred, (actual_winner, actual_loser) in zip(predictions, actual_results):
            # Check if prediction is correct
            if pred.predicted_winner == actual_winner:
                correct += 1
            
            total_confidence += pred.confidence
            
            # Calculate calibration error (how well probabilities match outcomes)
            if pred.predicted_winner == actual_winner:
                calibration_error = abs(pred.win_probability - 1.0)
            else:
                calibration_error = abs(pred.win_probability - 0.0)
            
            total_calibration_error += calibration_error
        
        n = len(predictions)
        return {
            'accuracy': correct / n,
            'avg_confidence': total_confidence / n,
            'avg_calibration_error': total_calibration_error / n,
            'correct_predictions': correct,
            'total_predictions': n
        }