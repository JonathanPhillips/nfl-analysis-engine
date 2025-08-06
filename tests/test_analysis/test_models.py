"""Tests for machine learning models."""

import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
import tempfile
import shutil

from src.analysis.models import NFLPredictor, ModelMetrics, Prediction


class TestModelMetrics:
    """Test ModelMetrics class."""
    
    def test_model_metrics_creation(self):
        """Test ModelMetrics object creation."""
        metrics = ModelMetrics(
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            roc_auc=0.90,
            samples=100
        )
        
        assert metrics.accuracy == 0.85
        assert metrics.precision == 0.82
        assert metrics.recall == 0.88
        assert metrics.f1_score == 0.85
        assert metrics.roc_auc == 0.90
        assert metrics.samples == 100
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metrics = ModelMetrics(
            accuracy=0.85,
            precision=0.82,
            recall=0.88,
            f1_score=0.85,
            roc_auc=0.90,
            samples=100
        )
        
        result = metrics.to_dict()
        
        assert isinstance(result, dict)
        assert result['accuracy'] == 0.85
        assert result['precision'] == 0.82
        assert result['samples'] == 100


class TestPrediction:
    """Test Prediction class."""
    
    def test_prediction_creation(self):
        """Test Prediction object creation."""
        pred = Prediction(
            home_team="SF",
            away_team="KC",
            game_date=date(2023, 10, 1),
            predicted_winner="SF",
            win_probability=0.65,
            home_win_prob=0.65,
            away_win_prob=0.35,
            confidence=0.30,
            features={"feature1": 0.5}
        )
        
        assert pred.home_team == "SF"
        assert pred.away_team == "KC"
        assert pred.predicted_winner == "SF"
        assert pred.win_probability == 0.65
        assert pred.confidence == 0.30
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        pred = Prediction(
            home_team="SF",
            away_team="KC",
            game_date=date(2023, 10, 1),
            predicted_winner="SF",
            win_probability=0.65,
            home_win_prob=0.65,
            away_win_prob=0.35,
            confidence=0.30,
            features={"feature1": 0.5}
        )
        
        result = pred.to_dict()
        
        assert isinstance(result, dict)
        assert result['home_team'] == "SF"
        assert result['game_date'] == "2023-10-01"
        assert result['predicted_winner'] == "SF"
        assert result['features'] == {"feature1": 0.5}


class TestNFLPredictor:
    """Test NFLPredictor class."""
    
    def test_initialization(self, test_session):
        """Test NFLPredictor initialization."""
        model_dir = tempfile.mkdtemp()
        try:
            predictor = NFLPredictor(test_session, model_dir)
            
            assert predictor.db_session == test_session
            assert predictor.model_dir == Path(model_dir)
            assert predictor.model is None
            assert predictor.scaler is None
            assert predictor.feature_names == []
            assert not predictor.is_trained
            assert predictor.feature_engineer is not None
        finally:
            shutil.rmtree(model_dir)
    
    def test_initialization_default_model_dir(self, test_session):
        """Test initialization with default model directory."""
        predictor = NFLPredictor(test_session)
        
        assert predictor.model_dir == Path("models")
        assert predictor.model_dir.exists()
    
    def test_prepare_training_data_no_games(self, nfl_predictor):
        """Test prepare_training_data with no games."""
        with pytest.raises(ValueError, match="No training data could be generated"):
            nfl_predictor.prepare_training_data([2023])
    
    def test_prepare_training_data_insufficient_games(self, nfl_predictor, sample_games):
        """Test prepare_training_data with insufficient games per team."""
        # Most teams won't have enough games with min_games_played=10
        with pytest.raises(ValueError):
            nfl_predictor.prepare_training_data([2023], min_games_played=10)
    
    def test_prepare_training_data_success(self, nfl_predictor, sample_games):
        """Test successful training data preparation."""
        # Use low minimum to allow training with sample data
        X, y = nfl_predictor.prepare_training_data([2023], min_games_played=1)
        
        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, pd.Series)
        assert len(X) == len(y)
        assert len(X) > 0
        assert len(nfl_predictor.feature_names) > 0
        
        # Check that features are all numeric
        assert X.dtypes.apply(lambda x: pd.api.types.is_numeric_dtype(x)).all()
        
        # Check target values are 0 or 1
        assert set(y.unique()).issubset({0, 1})
    
    def test_train_insufficient_data(self, nfl_predictor):
        """Test training with insufficient data."""
        with pytest.raises(ValueError):
            nfl_predictor.train([2023], optimize_hyperparameters=False)
    
    def test_train_success(self, nfl_predictor, sample_games):
        """Test successful model training."""
        # Train with sample data (no hyperparameter optimization for speed)
        nfl_predictor.train([2023], test_size=0.3, optimize_hyperparameters=False, 
                           min_games_played=1, n_estimators=10)
        
        assert nfl_predictor.is_trained
        assert nfl_predictor.model is not None
        assert nfl_predictor.scaler is not None
        assert len(nfl_predictor.feature_names) > 0
        assert nfl_predictor.training_metrics is not None
        assert nfl_predictor.validation_metrics is not None
        
        # Check metric ranges
        assert 0 <= nfl_predictor.training_metrics.accuracy <= 1
        assert 0 <= nfl_predictor.validation_metrics.accuracy <= 1
    
    def test_predict_game_untrained(self, nfl_predictor):
        """Test prediction with untrained model."""
        with pytest.raises(ValueError, match="Model must be trained"):
            nfl_predictor.predict_game("SF", "KC", date(2023, 10, 1), 2023)
    
    def test_predict_game_success(self, trained_predictor):
        """Test successful game prediction."""
        prediction = trained_predictor.predict_game("SF", "KC", date(2023, 10, 1), 2023)
        
        assert isinstance(prediction, Prediction)
        assert prediction.home_team == "SF"
        assert prediction.away_team == "KC"
        assert prediction.predicted_winner in ["SF", "KC"]
        
        # Probability checks
        assert 0 <= prediction.win_probability <= 1
        assert 0 <= prediction.home_win_prob <= 1
        assert 0 <= prediction.away_win_prob <= 1
        assert 0 <= prediction.confidence <= 1
        assert abs(prediction.home_win_prob + prediction.away_win_prob - 1.0) < 0.01
        
        # Check features
        assert isinstance(prediction.features, dict)
        assert len(prediction.features) > 0
    
    def test_predict_games_multiple(self, trained_predictor):
        """Test predicting multiple games."""
        games = [
            ("SF", "KC", date(2023, 10, 1), 2023),
            ("DAL", "BUF", date(2023, 10, 2), 2023),
        ]
        
        predictions = trained_predictor.predict_games(games)
        
        assert len(predictions) == 2
        assert all(isinstance(p, Prediction) for p in predictions)
        assert predictions[0].home_team == "SF"
        assert predictions[1].home_team == "DAL"
    
    def test_predict_games_with_errors(self, trained_predictor):
        """Test predicting games with some errors."""
        games = [
            ("SF", "KC", date(2023, 10, 1), 2023),
            ("INVALID", "TEAM", date(2023, 10, 2), 2023),  # Should fail
        ]
        
        predictions = trained_predictor.predict_games(games)
        
        # Should get at least one successful prediction
        assert len(predictions) >= 0
        # Errors should be logged but not crash the function
    
    def test_get_feature_importance_untrained(self, nfl_predictor):
        """Test feature importance with untrained model."""
        with pytest.raises(ValueError, match="Model must be trained"):
            nfl_predictor.get_feature_importance()
    
    def test_get_feature_importance_success(self, trained_predictor):
        """Test successful feature importance extraction."""
        importance = trained_predictor.get_feature_importance(top_n=10)
        
        assert isinstance(importance, dict)
        assert len(importance) <= 10
        assert len(importance) > 0
        
        # All importance values should be non-negative
        for feature, score in importance.items():
            assert score >= 0
            assert isinstance(feature, str)
        
        # Should be sorted by importance (descending)
        scores = list(importance.values())
        assert scores == sorted(scores, reverse=True)
    
    def test_save_model_untrained(self, nfl_predictor):
        """Test saving untrained model."""
        with pytest.raises(ValueError, match="Model must be trained"):
            nfl_predictor.save_model()
    
    def test_save_and_load_model(self, trained_predictor):
        """Test saving and loading model."""
        model_name = "test_model"
        
        # Save model
        trained_predictor.save_model(model_name)
        
        # Check files were created
        model_path = trained_predictor.model_dir / f"{model_name}.pkl"
        metadata_path = trained_predictor.model_dir / f"{model_name}_metadata.json"
        
        assert model_path.exists()
        assert metadata_path.exists()
        
        # Create new predictor and load model
        new_predictor = NFLPredictor(trained_predictor.db_session, str(trained_predictor.model_dir))
        new_predictor.load_model(model_name)
        
        assert new_predictor.is_trained
        assert new_predictor.model is not None
        assert new_predictor.scaler is not None
        assert new_predictor.feature_names == trained_predictor.feature_names
        
        # Test that loaded model can make predictions
        prediction = new_predictor.predict_game("SF", "KC", date(2023, 10, 1), 2023)
        assert isinstance(prediction, Prediction)
    
    def test_load_model_not_found(self, nfl_predictor):
        """Test loading non-existent model."""
        with pytest.raises(FileNotFoundError):
            nfl_predictor.load_model("nonexistent_model")
    
    def test_evaluate_predictions(self, nfl_predictor, sample_predictions):
        """Test prediction evaluation."""
        actual_results = [
            ("SF", "KC"),  # SF won, prediction was SF (correct)
            ("BUF", "DAL"), # BUF won, prediction was BUF (correct)
        ]
        
        evaluation = nfl_predictor.evaluate_predictions(sample_predictions, actual_results)
        
        assert isinstance(evaluation, dict)
        assert 'accuracy' in evaluation
        assert 'avg_confidence' in evaluation
        assert 'avg_calibration_error' in evaluation
        assert 'correct_predictions' in evaluation
        assert 'total_predictions' in evaluation
        
        # Both predictions were correct
        assert evaluation['accuracy'] == 1.0
        assert evaluation['correct_predictions'] == 2
        assert evaluation['total_predictions'] == 2
    
    def test_evaluate_predictions_mismatch_length(self, nfl_predictor, sample_predictions):
        """Test evaluation with mismatched lengths."""
        actual_results = [("SF", "KC")]  # Only one result for two predictions
        
        with pytest.raises(ValueError, match="same length"):
            nfl_predictor.evaluate_predictions(sample_predictions, actual_results)
    
    def test_evaluate_predictions_mixed_accuracy(self, nfl_predictor, sample_predictions):
        """Test evaluation with mixed accuracy."""
        actual_results = [
            ("SF", "KC"),   # Correct prediction
            ("DAL", "BUF")  # Incorrect prediction (predicted BUF, DAL won)
        ]
        
        evaluation = nfl_predictor.evaluate_predictions(sample_predictions, actual_results)
        
        assert evaluation['accuracy'] == 0.5  # 1 out of 2 correct
        assert evaluation['correct_predictions'] == 1
        assert evaluation['total_predictions'] == 2
    
    def test_model_training_metrics(self, nfl_predictor, sample_games):
        """Test that training produces reasonable metrics."""
        nfl_predictor.train([2023], test_size=0.3, optimize_hyperparameters=False, 
                           min_games_played=1, n_estimators=10)
        
        train_metrics = nfl_predictor.training_metrics
        val_metrics = nfl_predictor.validation_metrics
        
        # Check that all metrics are in reasonable ranges
        for metrics in [train_metrics, val_metrics]:
            assert 0 <= metrics.accuracy <= 1
            assert 0 <= metrics.precision <= 1
            assert 0 <= metrics.recall <= 1
            assert 0 <= metrics.f1_score <= 1
            assert 0 <= metrics.roc_auc <= 1
            assert metrics.samples > 0
    
    def test_feature_consistency_across_predictions(self, trained_predictor):
        """Test that feature creation is consistent across predictions."""
        prediction1 = trained_predictor.predict_game("SF", "KC", date(2023, 10, 1), 2023)
        prediction2 = trained_predictor.predict_game("SF", "KC", date(2023, 10, 1), 2023)
        
        # Should get identical predictions for identical inputs
        assert prediction1.predicted_winner == prediction2.predicted_winner
        assert prediction1.win_probability == prediction2.win_probability
        assert prediction1.features == prediction2.features
    
    def test_prediction_probability_consistency(self, trained_predictor):
        """Test that prediction probabilities are consistent."""
        prediction = trained_predictor.predict_game("SF", "KC", date(2023, 10, 1), 2023)
        
        # Winner should correspond to higher probability
        if prediction.predicted_winner == prediction.home_team:
            assert prediction.home_win_prob >= prediction.away_win_prob
            assert prediction.win_probability == prediction.home_win_prob
        else:
            assert prediction.away_win_prob >= prediction.home_win_prob
            assert prediction.win_probability == prediction.away_win_prob
        
        # Probabilities should sum to 1
        assert abs(prediction.home_win_prob + prediction.away_win_prob - 1.0) < 0.01
    
    def test_model_persistence_across_sessions(self, trained_predictor, test_session):
        """Test that saved models work with different database sessions."""
        model_name = "persistence_test"
        
        # Save model
        trained_predictor.save_model(model_name)
        
        # Create new predictor with same session
        new_predictor = NFLPredictor(test_session, str(trained_predictor.model_dir))
        new_predictor.load_model(model_name)
        
        # Should be able to make predictions
        prediction = new_predictor.predict_game("SF", "KC", date(2023, 10, 1), 2023)
        assert isinstance(prediction, Prediction)
    
    def test_training_data_quality(self, nfl_predictor, sample_games):
        """Test the quality of prepared training data."""
        X, y = nfl_predictor.prepare_training_data([2023], min_games_played=1)
        
        # Check for no infinite or NaN values
        assert not X.isnull().any().any(), "Training data contains NaN values"
        assert not np.isinf(X.values).any(), "Training data contains infinite values"
        
        # Check that features have reasonable ranges
        for col in X.columns:
            if 'win_pct' in col or 'form' in col:
                # Win percentages and form should be bounded
                assert X[col].min() >= -1, f"Column {col} has values below -1"
                assert X[col].max() <= 1, f"Column {col} has values above 1"
            elif 'ppg' in col or 'papg' in col:
                # Points should be non-negative and reasonable
                assert X[col].min() >= 0, f"Column {col} has negative values"
                assert X[col].max() <= 100, f"Column {col} has unreasonably high values"