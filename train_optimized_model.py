#!/usr/bin/env python3
"""Train and evaluate the optimized NFL prediction model."""

import sys
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.database.config import get_session
from src.analysis.ml_optimizer import OptimizedNFLPredictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def train_optimized_model():
    """Train the optimized NFL prediction model."""
    logger.info("Starting optimized model training...")
    
    # Get database session
    db = get_session()()
    
    try:
        # Initialize optimized predictor
        predictor = OptimizedNFLPredictor(db)
        
        # Train on 2024 season data (we have play-by-play data for this)
        seasons = [2024]
        logger.info(f"Training on seasons: {seasons}")
        
        # Train with optimization
        metrics = predictor.train_optimized(seasons=seasons, test_size=0.25)
        
        # Display results
        print("\n" + "="*60)
        print("OPTIMIZED MODEL TRAINING RESULTS")
        print("="*60)
        print(f"Accuracy: {metrics.accuracy:.4f} ({metrics.accuracy*100:.2f}%)")
        print(f"Precision: {metrics.precision:.4f}")
        print(f"Recall: {metrics.recall:.4f}")
        print(f"F1 Score: {metrics.f1_score:.4f}")
        print(f"ROC AUC: {metrics.roc_auc:.4f}")
        print(f"Samples: {metrics.samples}")
        
        if hasattr(metrics, 'cross_val_scores'):
            cv_mean = sum(metrics.cross_val_scores) / len(metrics.cross_val_scores)
            print(f"\nCross-Validation Scores: {[f'{s:.4f}' for s in metrics.cross_val_scores]}")
            print(f"Mean CV Score: {cv_mean:.4f}")
        
        if hasattr(metrics, 'calibration_score'):
            print(f"Calibration Score: {metrics.calibration_score:.4f}")
        
        # Feature importance
        if hasattr(metrics, 'feature_importance') and metrics.feature_importance:
            print("\nTop 10 Most Important Features:")
            sorted_features = sorted(metrics.feature_importance.items(), 
                                   key=lambda x: x[1], reverse=True)[:10]
            for i, (feature, importance) in enumerate(sorted_features, 1):
                print(f"{i}. {feature}: {importance:.4f}")
        
        # Save the model
        predictor.save_optimized_model("nfl_predictor_optimized")
        print(f"\nModel saved to models/nfl_predictor_optimized.pkl")
        
        # Comparison with baseline
        print("\n" + "="*60)
        print("IMPROVEMENT ANALYSIS")
        print("="*60)
        baseline_accuracy = 0.6695  # Original accuracy
        improvement = metrics.accuracy - baseline_accuracy
        improvement_pct = (improvement / baseline_accuracy) * 100
        
        print(f"Baseline Accuracy: {baseline_accuracy:.4f} ({baseline_accuracy*100:.2f}%)")
        print(f"Optimized Accuracy: {metrics.accuracy:.4f} ({metrics.accuracy*100:.2f}%)")
        print(f"Improvement: {improvement:.4f} ({improvement_pct:+.2f}%)")
        
        if metrics.accuracy > 0.70:
            print("\n✅ SUCCESS: Achieved >70% accuracy!")
        elif metrics.accuracy > baseline_accuracy:
            print(f"\n✅ IMPROVED: Better than baseline by {improvement_pct:.2f}%")
        else:
            print("\n⚠️ No improvement over baseline")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error training model: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        db.close()


def test_predictions():
    """Test the optimized model with sample predictions."""
    logger.info("Testing optimized model predictions...")
    
    db = get_session()()
    
    try:
        predictor = OptimizedNFLPredictor(db)
        
        # Load the saved model
        model_path = Path("models/nfl_predictor_optimized.pkl")
        if not model_path.exists():
            print("Model not found. Please train first.")
            return
        
        # Test predictions for upcoming games
        test_games = [
            ("KC", "BUF", datetime(2025, 1, 26).date()),  # AFC Championship example
            ("SF", "PHI", datetime(2025, 1, 26).date()),  # NFC Championship example
            ("DAL", "GB", datetime(2025, 1, 19).date()),   # Playoff example
        ]
        
        print("\n" + "="*60)
        print("SAMPLE PREDICTIONS")
        print("="*60)
        
        for home_team, away_team, game_date in test_games:
            try:
                prediction = predictor.predict_game(
                    home_team, away_team, game_date, 2024
                )
                
                print(f"\n{away_team} @ {home_team} ({game_date})")
                print(f"Predicted Winner: {prediction.predicted_winner}")
                print(f"Win Probability: {prediction.win_probability:.2%}")
                print(f"Home Win Prob: {prediction.home_win_prob:.2%}")
                print(f"Away Win Prob: {prediction.away_win_prob:.2%}")
                print(f"Confidence: {prediction.confidence:.2%}")
                
            except Exception as e:
                print(f"Could not predict {away_team} @ {home_team}: {e}")
        
    except Exception as e:
        logger.error(f"Error testing predictions: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train optimized NFL prediction model")
    parser.add_argument("--test-only", action="store_true", 
                       help="Only test predictions without training")
    
    args = parser.parse_args()
    
    if args.test_only:
        test_predictions()
    else:
        metrics = train_optimized_model()
        if metrics and metrics.accuracy > 0.6695:
            print("\nTesting predictions with optimized model...")
            test_predictions()