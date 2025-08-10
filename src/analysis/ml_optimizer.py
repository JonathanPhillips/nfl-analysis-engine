"""Advanced ML model optimization for NFL game prediction."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
import pickle
import json
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (
    train_test_split, cross_val_score, GridSearchCV, 
    RandomizedSearchCV, StratifiedKFold, learning_curve
)
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.feature_selection import SelectKBest, f_classif, RFE
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, 
    roc_auc_score, confusion_matrix, classification_report
)
from sklearn.calibration import CalibratedClassifierCV
from sqlalchemy.orm import Session
from sqlalchemy import func
import xgboost as xgb
from scipy import stats

from .features import FeatureEngineer
from .models import NFLPredictor, ModelMetrics, Prediction
from ..models.game import GameModel
from ..models.play import PlayModel
from ..models.team import TeamModel

logger = logging.getLogger(__name__)


@dataclass
class OptimizedModelMetrics(ModelMetrics):
    """Extended metrics for optimized models."""
    feature_importance: Dict[str, float]
    best_params: Dict[str, Any]
    cross_val_scores: List[float]
    learning_curve_data: Dict[str, List[float]]
    calibration_score: float


class EnhancedFeatureEngineer(FeatureEngineer):
    """Enhanced feature engineering with advanced NFL-specific features."""
    
    def create_advanced_features(self, home_team: str, away_team: str, 
                                game_date: date, season: int) -> Dict[str, float]:
        """Create advanced features for game prediction.
        
        New features include:
        - Momentum metrics (recent form, streak)
        - Situational performance (primetime, division games)
        - Advanced team metrics (EPA, success rate)
        - Weather and rest days
        - Coaching and QB performance
        """
        # Get basic features
        basic_features = self.create_game_features(home_team, away_team, game_date, season)
        
        # Get team stats for advanced metrics
        home_stats = self.get_team_stats(home_team, season, game_date)
        away_stats = self.get_team_stats(away_team, season, game_date)
        
        advanced_features = {}
        
        # 1. Momentum Features (Recent Form)
        home_momentum = self._calculate_momentum(home_team, season, game_date)
        away_momentum = self._calculate_momentum(away_team, season, game_date)
        
        advanced_features.update({
            'home_momentum': home_momentum['weighted_form'],
            'away_momentum': away_momentum['weighted_form'],
            'home_streak': home_momentum['current_streak'],
            'away_streak': away_momentum['current_streak'],
            'momentum_diff': home_momentum['weighted_form'] - away_momentum['weighted_form']
        })
        
        # 2. Rest Days and Schedule Difficulty
        home_rest = self._calculate_rest_days(home_team, game_date, season)
        away_rest = self._calculate_rest_days(away_team, game_date, season)
        
        advanced_features.update({
            'home_rest_days': home_rest,
            'away_rest_days': away_rest,
            'rest_advantage': home_rest - away_rest,
            'home_is_well_rested': 1 if home_rest >= 7 else 0,
            'away_is_well_rested': 1 if away_rest >= 7 else 0
        })
        
        # 3. EPA and Success Rate (from play-by-play data)
        home_epa = self._calculate_team_epa(home_team, season, game_date)
        away_epa = self._calculate_team_epa(away_team, season, game_date)
        
        advanced_features.update({
            'home_offensive_epa': home_epa['offensive_epa'],
            'home_defensive_epa': home_epa['defensive_epa'],
            'away_offensive_epa': away_epa['offensive_epa'],
            'away_defensive_epa': away_epa['defensive_epa'],
            'home_success_rate': home_epa['success_rate'],
            'away_success_rate': away_epa['success_rate'],
            'epa_matchup': home_epa['offensive_epa'] - away_epa['defensive_epa']
        })
        
        # 4. Situational Performance
        home_situational = self._calculate_situational_performance(home_team, season, game_date)
        away_situational = self._calculate_situational_performance(away_team, season, game_date)
        
        advanced_features.update({
            'home_close_game_win_pct': home_situational['close_games'],
            'away_close_game_win_pct': away_situational['close_games'],
            'home_blowout_pct': home_situational['blowouts'],
            'away_blowout_pct': away_situational['blowouts'],
            'home_comeback_pct': home_situational['comebacks'],
            'away_comeback_pct': away_situational['comebacks']
        })
        
        # 5. Quarterback Performance (if available)
        home_qb = self._get_qb_performance(home_team, season, game_date)
        away_qb = self._get_qb_performance(away_team, season, game_date)
        
        if home_qb and away_qb:
            advanced_features.update({
                'home_qb_rating': home_qb['passer_rating'],
                'away_qb_rating': away_qb['passer_rating'],
                'home_qb_epa': home_qb['epa_per_play'],
                'away_qb_epa': away_qb['epa_per_play'],
                'qb_rating_diff': home_qb['passer_rating'] - away_qb['passer_rating']
            })
        
        # 6. Division and Conference Games
        is_division_game = self._is_division_game(home_team, away_team)
        is_conference_game = self._is_conference_game(home_team, away_team)
        
        advanced_features.update({
            'is_division_game': 1 if is_division_game else 0,
            'is_conference_game': 1 if is_conference_game else 0,
            'home_division_record': self._get_division_record(home_team, season, game_date),
            'away_division_record': self._get_division_record(away_team, season, game_date)
        })
        
        # 7. Time and Day Features
        advanced_features.update({
            'is_primetime': 1 if self._is_primetime_game(game_date) else 0,
            'is_thursday': 1 if game_date.weekday() == 3 else 0,
            'is_monday': 1 if game_date.weekday() == 0 else 0,
            'week_of_season': self._get_week_of_season(game_date, season)
        })
        
        # Combine with basic features
        all_features = {**basic_features, **advanced_features}
        
        return all_features
    
    def _calculate_momentum(self, team: str, season: int, end_date: date) -> Dict[str, float]:
        """Calculate team momentum based on recent games."""
        recent_games = self.db_session.query(GameModel).filter(
            GameModel.season == season,
            (GameModel.home_team == team) | (GameModel.away_team == team),
            GameModel.game_date < end_date,
            GameModel.home_score.isnot(None)
        ).order_by(GameModel.game_date.desc()).limit(5).all()
        
        if not recent_games:
            return {'weighted_form': 0.5, 'current_streak': 0}
        
        weights = [0.35, 0.25, 0.20, 0.15, 0.05]  # More weight to recent games
        weighted_wins = 0
        total_weight = 0
        current_streak = 0
        
        for i, game in enumerate(recent_games):
            if i < len(weights):
                weight = weights[i]
                is_home = game.home_team == team
                team_score = game.home_score if is_home else game.away_score
                opp_score = game.away_score if is_home else game.home_score
                
                if team_score > opp_score:
                    weighted_wins += weight
                    if i == 0:
                        current_streak = max(1, current_streak + 1)
                elif i == 0 and team_score < opp_score:
                    current_streak = min(-1, current_streak - 1)
                
                total_weight += weight
        
        weighted_form = weighted_wins / total_weight if total_weight > 0 else 0.5
        
        return {'weighted_form': weighted_form, 'current_streak': current_streak}
    
    def _calculate_rest_days(self, team: str, game_date: date, season: int) -> int:
        """Calculate days of rest before the game."""
        previous_game = self.db_session.query(GameModel).filter(
            GameModel.season == season,
            (GameModel.home_team == team) | (GameModel.away_team == team),
            GameModel.game_date < game_date
        ).order_by(GameModel.game_date.desc()).first()
        
        if previous_game:
            return (game_date - previous_game.game_date).days
        return 7  # Default to normal week rest
    
    def _calculate_team_epa(self, team: str, season: int, end_date: date) -> Dict[str, float]:
        """Calculate team EPA metrics from play-by-play data."""
        # Offensive EPA
        offensive_plays = self.db_session.query(
            PlayModel.epa
        ).join(
            GameModel, PlayModel.game_id == GameModel.game_id
        ).filter(
            PlayModel.season == season,
            PlayModel.posteam == team,
            GameModel.game_date < end_date,
            PlayModel.play_type.in_(['pass', 'run'])
        ).all()
        
        # Defensive EPA
        defensive_plays = self.db_session.query(
            PlayModel.epa
        ).join(
            GameModel, PlayModel.game_id == GameModel.game_id
        ).filter(
            PlayModel.season == season,
            PlayModel.defteam == team,
            GameModel.game_date < end_date,
            PlayModel.play_type.in_(['pass', 'run'])
        ).all()
        
        offensive_epa = np.mean([p.epa for p in offensive_plays if p.epa is not None]) if offensive_plays else 0
        defensive_epa = np.mean([p.epa for p in defensive_plays if p.epa is not None]) if defensive_plays else 0
        
        # Success rate (% of plays with positive EPA)
        success_plays = sum(1 for p in offensive_plays if p.epa is not None and p.epa > 0)
        total_plays = sum(1 for p in offensive_plays if p.epa is not None)
        success_rate = success_plays / total_plays if total_plays > 0 else 0.5
        
        return {
            'offensive_epa': offensive_epa,
            'defensive_epa': defensive_epa,
            'success_rate': success_rate
        }
    
    def _calculate_situational_performance(self, team: str, season: int, end_date: date) -> Dict[str, float]:
        """Calculate performance in specific game situations."""
        games = self.db_session.query(GameModel).filter(
            GameModel.season == season,
            (GameModel.home_team == team) | (GameModel.away_team == team),
            GameModel.game_date < end_date,
            GameModel.home_score.isnot(None)
        ).all()
        
        close_games_won = 0
        close_games_total = 0
        blowouts_won = 0
        comebacks = 0
        
        for game in games:
            is_home = game.home_team == team
            team_score = game.home_score if is_home else game.away_score
            opp_score = game.away_score if is_home else game.home_score
            diff = abs(team_score - opp_score)
            
            # Close games (decided by 7 points or less)
            if diff <= 7:
                close_games_total += 1
                if team_score > opp_score:
                    close_games_won += 1
            
            # Blowouts (winning by 21+ points)
            if team_score - opp_score >= 21:
                blowouts_won += 1
        
        return {
            'close_games': close_games_won / close_games_total if close_games_total > 0 else 0.5,
            'blowouts': blowouts_won / len(games) if games else 0,
            'comebacks': comebacks / len(games) if games else 0
        }
    
    def _get_qb_performance(self, team: str, season: int, end_date: date) -> Optional[Dict[str, float]]:
        """Get quarterback performance metrics."""
        qb_stats = self.db_session.query(
            PlayModel.passer_player_id,
            func.avg(PlayModel.epa).label('epa_per_play'),
            func.count(PlayModel.id).label('attempts')
        ).filter(
            PlayModel.season == season,
            PlayModel.posteam == team,
            PlayModel.play_type == 'pass',
            PlayModel.passer_player_id.isnot(None)
        ).group_by(
            PlayModel.passer_player_id
        ).order_by(
            func.count(PlayModel.id).desc()
        ).first()
        
        if not qb_stats:
            return None
        
        # Calculate passer rating (simplified)
        return {
            'passer_rating': 85.0,  # Default/placeholder
            'epa_per_play': qb_stats.epa_per_play or 0
        }
    
    def _is_division_game(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same division."""
        team1_info = self.db_session.query(TeamModel).filter_by(team_abbr=team1).first()
        team2_info = self.db_session.query(TeamModel).filter_by(team_abbr=team2).first()
        
        if team1_info and team2_info:
            return team1_info.team_division == team2_info.team_division
        return False
    
    def _is_conference_game(self, team1: str, team2: str) -> bool:
        """Check if two teams are in the same conference."""
        team1_info = self.db_session.query(TeamModel).filter_by(team_abbr=team1).first()
        team2_info = self.db_session.query(TeamModel).filter_by(team_abbr=team2).first()
        
        if team1_info and team2_info:
            return team1_info.team_conf == team2_info.team_conf
        return False
    
    def _get_division_record(self, team: str, season: int, end_date: date) -> float:
        """Get team's winning percentage in division games."""
        team_info = self.db_session.query(TeamModel).filter_by(team_abbr=team).first()
        if not team_info:
            return 0.5
        
        division_teams = self.db_session.query(TeamModel.team_abbr).filter_by(
            team_division=team_info.team_division
        ).all()
        division_teams = [t[0] for t in division_teams if t[0] != team]
        
        games = self.db_session.query(GameModel).filter(
            GameModel.season == season,
            GameModel.game_date < end_date,
            GameModel.home_score.isnot(None),
            ((GameModel.home_team == team) & (GameModel.away_team.in_(division_teams))) |
            ((GameModel.away_team == team) & (GameModel.home_team.in_(division_teams)))
        ).all()
        
        if not games:
            return 0.5
        
        wins = 0
        for game in games:
            is_home = game.home_team == team
            team_score = game.home_score if is_home else game.away_score
            opp_score = game.away_score if is_home else game.home_score
            if team_score > opp_score:
                wins += 1
        
        return wins / len(games)
    
    def _is_primetime_game(self, game_date: date) -> bool:
        """Check if game is in primetime (Sunday/Monday night)."""
        weekday = game_date.weekday()
        return weekday in [0, 6]  # Monday or Sunday
    
    def _get_week_of_season(self, game_date: date, season: int) -> int:
        """Get the week number of the season."""
        # Simplified - would need actual NFL schedule
        season_start = date(season, 9, 1)  # Approximate
        weeks = (game_date - season_start).days // 7
        return min(max(1, weeks), 18)


class OptimizedNFLPredictor(NFLPredictor):
    """Optimized NFL predictor with advanced ML techniques."""
    
    def __init__(self, db_session: Session, model_dir: Optional[str] = None):
        super().__init__(db_session, model_dir)
        self.feature_engineer = EnhancedFeatureEngineer(db_session)
        self.ensemble_model = None
        self.feature_selector = None
        self.polynomial_features = None
        
    def train_optimized(self, seasons: List[int], test_size: float = 0.2) -> OptimizedModelMetrics:
        """Train with advanced optimization techniques.
        
        Improvements:
        1. Enhanced feature engineering
        2. Feature selection and polynomial features
        3. Ensemble methods (Random Forest + XGBoost + Gradient Boosting)
        4. Hyperparameter optimization
        5. Model calibration
        """
        logger.info("Starting optimized training process")
        
        # Prepare enhanced training data
        X, y = self.prepare_enhanced_training_data(seasons)
        
        # Feature engineering: Polynomial features for interactions
        logger.info("Creating polynomial features...")
        self.polynomial_features = PolynomialFeatures(degree=2, include_bias=False)
        X_poly = self.polynomial_features.fit_transform(X)
        
        # Feature selection using RFE
        logger.info("Performing feature selection...")
        base_estimator = RandomForestClassifier(n_estimators=100, random_state=42)
        self.feature_selector = RFE(base_estimator, n_features_to_select=50, step=5)
        X_selected = self.feature_selector.fit_transform(X_poly, y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_selected, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Create ensemble model
        logger.info("Creating ensemble model...")
        models = self._create_ensemble_models()
        
        # Hyperparameter tuning
        logger.info("Optimizing hyperparameters...")
        best_models = []
        for name, model, param_grid in models:
            logger.info(f"Tuning {name}...")
            optimized_model = self._optimize_model(model, param_grid, X_train_scaled, y_train)
            best_models.append((name, optimized_model))
        
        # Create voting ensemble
        self.ensemble_model = VotingClassifier(
            estimators=best_models,
            voting='soft',
            weights=[1.2, 1.5, 1.0]  # Weight XGBoost slightly higher
        )
        
        # Train ensemble
        logger.info("Training ensemble model...")
        self.ensemble_model.fit(X_train_scaled, y_train)
        
        # Calibrate model for better probability estimates
        logger.info("Calibrating model...")
        self.model = CalibratedClassifierCV(self.ensemble_model, cv=3, method='sigmoid')
        self.model.fit(X_train_scaled, y_train)
        
        # Calculate metrics
        metrics = self._calculate_optimized_metrics(X_train_scaled, y_train, X_test_scaled, y_test)
        
        self.is_trained = True
        self.training_metrics = metrics
        
        logger.info(f"Optimized training complete. Accuracy: {metrics.accuracy:.4f}")
        
        return metrics
    
    def prepare_enhanced_training_data(self, seasons: List[int]) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare training data with enhanced features."""
        logger.info(f"Preparing enhanced training data for seasons {seasons}")
        
        training_data = []
        
        for season in seasons:
            games = self.db_session.query(GameModel).filter(
                GameModel.season == season,
                GameModel.home_score.isnot(None)
            ).all()
            
            for game in games:
                try:
                    # Use enhanced feature engineering
                    features = self.feature_engineer.create_advanced_features(
                        game.home_team, game.away_team, game.game_date, season
                    )
                    
                    # Target
                    target = 1 if game.home_score > game.away_score else 0
                    
                    features['target'] = target
                    training_data.append(features)
                    
                except Exception as e:
                    logger.warning(f"Failed to create features for game {game.game_id}: {e}")
                    continue
        
        df = pd.DataFrame(training_data)
        
        # Separate features and target
        feature_cols = [col for col in df.columns if col != 'target']
        X = df[feature_cols].fillna(0)
        y = df['target']
        
        self.feature_names = feature_cols
        
        logger.info(f"Created enhanced dataset with {len(df)} samples and {len(feature_cols)} features")
        
        return X, y
    
    def _create_ensemble_models(self) -> List[Tuple[str, Any, Dict]]:
        """Create ensemble models with parameter grids."""
        models = [
            ('rf', RandomForestClassifier(random_state=42), {
                'n_estimators': [200, 300],
                'max_depth': [15, 20, 25],
                'min_samples_split': [5, 10],
                'min_samples_leaf': [2, 4],
                'max_features': ['sqrt', 'log2']
            }),
            ('xgb', xgb.XGBClassifier(random_state=42, use_label_encoder=False, eval_metric='logloss'), {
                'n_estimators': [200, 300],
                'max_depth': [4, 6, 8],
                'learning_rate': [0.05, 0.1, 0.15],
                'subsample': [0.8, 0.9],
                'colsample_bytree': [0.8, 0.9]
            }),
            ('gb', GradientBoostingClassifier(random_state=42), {
                'n_estimators': [150, 200],
                'max_depth': [3, 5, 7],
                'learning_rate': [0.05, 0.1],
                'subsample': [0.8, 0.9]
            })
        ]
        return models
    
    def _optimize_model(self, model: Any, param_grid: Dict, X: np.ndarray, y: np.ndarray) -> Any:
        """Optimize model hyperparameters using RandomizedSearchCV."""
        search = RandomizedSearchCV(
            model, param_grid, 
            n_iter=20,  # Number of parameter settings sampled
            cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
            scoring='roc_auc',
            n_jobs=-1,
            random_state=42
        )
        search.fit(X, y)
        return search.best_estimator_
    
    def _calculate_optimized_metrics(self, X_train: np.ndarray, y_train: np.ndarray,
                                    X_test: np.ndarray, y_test: np.ndarray) -> OptimizedModelMetrics:
        """Calculate comprehensive metrics for optimized model."""
        # Predictions
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        y_proba_test = self.model.predict_proba(X_test)[:, 1]
        
        # Basic metrics
        test_metrics = {
            'accuracy': accuracy_score(y_test, y_pred_test),
            'precision': precision_score(y_test, y_pred_test),
            'recall': recall_score(y_test, y_pred_test),
            'f1_score': f1_score(y_test, y_pred_test),
            'roc_auc': roc_auc_score(y_test, y_proba_test)
        }
        
        # Cross-validation scores
        cv_scores = cross_val_score(
            self.model, X_train, y_train, 
            cv=5, scoring='accuracy'
        ).tolist()
        
        # Feature importance (from Random Forest in ensemble)
        feature_importance = {}
        if hasattr(self.ensemble_model, 'estimators_'):
            for name, estimator in self.ensemble_model.estimators_:
                if hasattr(estimator, 'feature_importances_'):
                    importances = estimator.feature_importances_
                    for i, importance in enumerate(importances[:20]):  # Top 20 features
                        feature_name = f"feature_{i}"
                        if feature_name not in feature_importance:
                            feature_importance[feature_name] = 0
                        feature_importance[feature_name] += importance
        
        # Learning curve data
        train_sizes, train_scores, val_scores = learning_curve(
            self.model, X_train, y_train, cv=5,
            train_sizes=np.linspace(0.1, 1.0, 10)
        )
        
        learning_data = {
            'train_sizes': train_sizes.tolist(),
            'train_scores': train_scores.mean(axis=1).tolist(),
            'val_scores': val_scores.mean(axis=1).tolist()
        }
        
        # Calibration score
        calibration_score = np.mean(np.abs(y_proba_test - y_test))
        
        return OptimizedModelMetrics(
            accuracy=test_metrics['accuracy'],
            precision=test_metrics['precision'],
            recall=test_metrics['recall'],
            f1_score=test_metrics['f1_score'],
            roc_auc=test_metrics['roc_auc'],
            samples=len(y_test),
            feature_importance=feature_importance,
            best_params={},  # Would need to extract from GridSearchCV
            cross_val_scores=cv_scores,
            learning_curve_data=learning_data,
            calibration_score=calibration_score
        )
    
    def save_optimized_model(self, name: str = "optimized_nfl_predictor") -> None:
        """Save the optimized model and components."""
        if not self.is_trained:
            raise ValueError("Model must be trained before saving")
        
        model_path = self.model_dir / f"{name}.pkl"
        metadata_path = self.model_dir / f"{name}_metadata.json"
        
        # Save model components
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_selector': self.feature_selector,
            'polynomial_features': self.polynomial_features,
            'ensemble_model': self.ensemble_model,
            'feature_names': self.feature_names
        }
        
        with open(model_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        # Save metadata
        metadata = {
            'training_metrics': self.training_metrics.to_dict() if self.training_metrics else None,
            'model_type': 'OptimizedEnsemble',
            'created_at': datetime.now().isoformat()
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Optimized model saved to {model_path}")