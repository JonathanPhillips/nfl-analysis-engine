"""Advanced NFL insights generator with EPA, WP, and other sophisticated metrics."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..models.game import GameModel
from ..models.play import PlayModel
from ..models.team import TeamModel
from ..models.player import PlayerModel

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be calculated."""
    TEAM_EFFICIENCY = "team_efficiency"
    PLAYER_IMPACT = "player_impact"
    SITUATIONAL = "situational"
    PREDICTIVE = "predictive"
    COMPARATIVE = "comparative"


class TimePeriod(Enum):
    """Time periods for metric calculation."""
    SEASON = "season"
    LAST_4_GAMES = "last_4"
    LAST_8_GAMES = "last_8"
    HOME_AWAY = "home_away"
    RED_ZONE = "red_zone"
    THIRD_DOWN = "third_down"


@dataclass
class PlayContext:
    """Context for a single play to calculate advanced metrics."""
    down: int
    ydstogo: int
    yardline_100: int  # Distance to end zone
    quarter: int
    game_seconds_remaining: int
    score_differential: int  # positive if offense leading
    timeouts_remaining: int
    play_type: str
    
    def __post_init__(self):
        """Validate play context."""
        self.down = max(1, min(4, self.down))
        self.ydstogo = max(0, self.ydstogo)
        self.yardline_100 = max(0, min(100, self.yardline_100))


@dataclass
class AdvancedMetrics:
    """Container for advanced NFL metrics."""
    # Expected Points
    expected_points_before: float
    expected_points_after: float
    epa: float  # Expected Points Added
    
    # Win Probability
    win_prob_before: float
    win_prob_after: float
    wpa: float  # Win Probability Added
    
    # Situational metrics
    leverage: float  # How much the play matters
    clutch_index: float  # Performance in high-leverage situations
    
    # Efficiency metrics
    success_rate: float  # Did the play achieve its goal
    explosive_play: bool  # 20+ yard gain or TD
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'expected_points_before': round(self.expected_points_before, 3),
            'expected_points_after': round(self.expected_points_after, 3),
            'epa': round(self.epa, 3),
            'win_prob_before': round(self.win_prob_before, 3),
            'win_prob_after': round(self.win_prob_after, 3),
            'wpa': round(self.wpa, 3),
            'leverage': round(self.leverage, 3),
            'clutch_index': round(self.clutch_index, 3),
            'success_rate': round(self.success_rate, 3),
            'explosive_play': self.explosive_play
        }


@dataclass
class TeamInsights:
    """Comprehensive team insights with advanced metrics."""
    team_abbr: str
    season: int
    
    # Offensive metrics
    offensive_epa_per_play: float
    passing_epa_per_play: float
    rushing_epa_per_play: float
    red_zone_efficiency: float
    third_down_conversion_rate: float
    
    # Defensive metrics
    defensive_epa_per_play: float
    pass_defense_epa: float
    run_defense_epa: float
    red_zone_defense: float
    third_down_defense: float
    
    # Special situations
    two_minute_drill_efficiency: float
    clutch_performance: float
    turnover_margin: float
    
    # Contextual metrics
    garbage_time_adjusted_epa: float
    strength_of_schedule: float
    home_field_advantage: float
    
    # Trend metrics
    early_season_performance: float
    late_season_performance: float
    improvement_trajectory: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'team_abbr': self.team_abbr,
            'season': self.season,
            'offensive_epa_per_play': round(self.offensive_epa_per_play, 3),
            'passing_epa_per_play': round(self.passing_epa_per_play, 3),
            'rushing_epa_per_play': round(self.rushing_epa_per_play, 3),
            'red_zone_efficiency': round(self.red_zone_efficiency, 3),
            'third_down_conversion_rate': round(self.third_down_conversion_rate, 3),
            'defensive_epa_per_play': round(self.defensive_epa_per_play, 3),
            'pass_defense_epa': round(self.pass_defense_epa, 3),
            'run_defense_epa': round(self.run_defense_epa, 3),
            'red_zone_defense': round(self.red_zone_defense, 3),
            'third_down_defense': round(self.third_down_defense, 3),
            'two_minute_drill_efficiency': round(self.two_minute_drill_efficiency, 3),
            'clutch_performance': round(self.clutch_performance, 3),
            'turnover_margin': round(self.turnover_margin, 3),
            'garbage_time_adjusted_epa': round(self.garbage_time_adjusted_epa, 3),
            'strength_of_schedule': round(self.strength_of_schedule, 3),
            'home_field_advantage': round(self.home_field_advantage, 3),
            'early_season_performance': round(self.early_season_performance, 3),
            'late_season_performance': round(self.late_season_performance, 3),
            'improvement_trajectory': round(self.improvement_trajectory, 3)
        }


@dataclass
class GameInsight:
    """Insights for a specific game."""
    game_id: str
    home_team: str
    away_team: str
    game_date: date
    
    # Game flow metrics
    excitement_index: float  # How exciting was the game
    competitiveness: float  # How close was the game
    momentum_swings: int  # Number of significant momentum changes
    
    # Performance metrics
    home_team_epa: float
    away_team_epa: float
    passing_game_dominance: float  # Which team controlled passing
    rushing_game_dominance: float  # Which team controlled rushing
    
    # Key moments
    biggest_play_epa: float
    biggest_play_wpa: float
    turning_point_quarter: int
    
    # Situational performance
    red_zone_battle: str  # Which team won red zone efficiency
    third_down_battle: str  # Which team won third down efficiency
    turnover_battle: str  # Which team won turnover battle
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'game_id': self.game_id,
            'home_team': self.home_team,
            'away_team': self.away_team,
            'game_date': self.game_date.isoformat(),
            'excitement_index': round(self.excitement_index, 3),
            'competitiveness': round(self.competitiveness, 3),
            'momentum_swings': self.momentum_swings,
            'home_team_epa': round(self.home_team_epa, 3),
            'away_team_epa': round(self.away_team_epa, 3),
            'passing_game_dominance': round(self.passing_game_dominance, 3),
            'rushing_game_dominance': round(self.rushing_game_dominance, 3),
            'biggest_play_epa': round(self.biggest_play_epa, 3),
            'biggest_play_wpa': round(self.biggest_play_wpa, 3),
            'turning_point_quarter': self.turning_point_quarter,
            'red_zone_battle': self.red_zone_battle,
            'third_down_battle': self.third_down_battle,
            'turnover_battle': self.turnover_battle
        }


class ExpectedPointsModel:
    """Model to calculate Expected Points for any game situation."""
    
    def __init__(self):
        """Initialize EP model with historical data."""
        # Expected points by field position and down (approximate values based on NFL data)
        self.ep_matrix = self._build_ep_matrix()
    
    def _build_ep_matrix(self) -> Dict[Tuple[int, int], float]:
        """Build expected points matrix based on down and distance to goal."""
        # This is a simplified model - in production, this would be trained on historical data
        ep_data = {}
        
        for yard_line in range(1, 101):  # 1-100 yard line
            for down in range(1, 5):  # 1st-4th down
                # Base expected points decreases with distance from goal
                base_ep = max(0, 7 - (yard_line * 0.07))
                
                # Adjust by down (later downs have lower EP)
                down_adjustment = {1: 1.0, 2: 0.85, 3: 0.6, 4: 0.3}[down]
                
                # Special adjustments for goal line and red zone
                if yard_line <= 5:  # Goal line
                    base_ep = 6.8 - (yard_line * 0.3)
                elif yard_line <= 20:  # Red zone
                    base_ep = 4.5 - (yard_line * 0.15)
                
                ep_data[(down, yard_line)] = base_ep * down_adjustment
        
        return ep_data
    
    def calculate_expected_points(self, context: PlayContext) -> float:
        """Calculate expected points for a given play context."""
        # Handle None values with defaults
        down = context.down if context.down is not None else 1
        yardline = context.yardline_100 if context.yardline_100 is not None else 50
        game_seconds = context.game_seconds_remaining if context.game_seconds_remaining is not None else 1800
        score_diff = context.score_differential if context.score_differential is not None else 0
        
        key = (down, yardline)
        base_ep = self.ep_matrix.get(key, 0.0)
        
        # Adjustments based on other context
        time_adjustment = 1.0
        if game_seconds < 120:  # Last 2 minutes
            time_adjustment = 1.15  # More urgent
        elif game_seconds > 3000:  # Early game
            time_adjustment = 0.95
        
        # Score differential adjustment
        if abs(score_diff) > 14:  # Blowout
            time_adjustment *= 0.8
        
        return base_ep * time_adjustment


class WinProbabilityModel:
    """Model to calculate Win Probability for any game situation."""
    
    def __init__(self):
        """Initialize WP model."""
        pass
    
    def calculate_win_probability(self, context: PlayContext) -> float:
        """Calculate win probability for the offensive team."""
        # Simplified win probability model
        # In production, this would be a trained model on historical data
        
        # Handle None values with defaults
        score_diff = context.score_differential if context.score_differential is not None else 0
        game_seconds = context.game_seconds_remaining if context.game_seconds_remaining is not None else 1800
        yardline = context.yardline_100 if context.yardline_100 is not None else 50
        
        # Base win probability from score differential
        base_wp = 0.5 + (score_diff * 0.02)  # Roughly 2% per point
        
        # Time remaining adjustment
        if game_seconds > 1800:  # More than 30 minutes
            time_factor = 0.8  # Score matters less early
        elif game_seconds > 900:  # More than 15 minutes
            time_factor = 1.0
        elif game_seconds > 120:  # More than 2 minutes
            time_factor = 1.3  # Score matters more late
        else:  # Less than 2 minutes
            time_factor = 2.0  # Score matters a lot
        
        # Field position adjustment
        field_pos_bonus = (100 - yardline) * 0.002
        
        # Down and distance adjustment
        conversion_prob = self._estimate_conversion_probability(context)
        down_bonus = (conversion_prob - 0.5) * 0.1
        
        wp = base_wp + (score_diff * 0.02 * time_factor) + field_pos_bonus + down_bonus
        
        # Ensure bounds [0, 1]
        return max(0.01, min(0.99, wp))
    
    def _estimate_conversion_probability(self, context: PlayContext) -> float:
        """Estimate probability of converting current down."""
        down = context.down if context.down is not None else 1
        ydstogo = context.ydstogo if context.ydstogo is not None else 10
        
        if down == 1:
            return 0.75 - (ydstogo * 0.02)
        elif down == 2:
            return 0.65 - (ydstogo * 0.03)
        elif down == 3:
            return 0.45 - (ydstogo * 0.04)
        else:  # 4th down
            return 0.25 - (ydstogo * 0.05)


class InsightsGenerator:
    """Main insights generator for advanced NFL analytics."""
    
    def __init__(self, db_session: Session):
        """Initialize insights generator.
        
        Args:
            db_session: Database session for data access
        """
        self.db_session = db_session
        self.ep_model = ExpectedPointsModel()
        self.wp_model = WinProbabilityModel()
        self.logger = logging.getLogger(__name__)
    
    def calculate_play_metrics(self, play_data: Dict[str, Any]) -> AdvancedMetrics:
        """Calculate advanced metrics for a single play.
        
        Args:
            play_data: Dictionary containing play information
            
        Returns:
            AdvancedMetrics object with all calculated values
        """
        # Create play context
        context_before = PlayContext(
            down=play_data.get('down', 1),
            ydstogo=play_data.get('ydstogo', 10),
            yardline_100=play_data.get('yardline_100', 50),
            quarter=play_data.get('qtr', 1),
            game_seconds_remaining=play_data.get('game_seconds_remaining', 3600),
            score_differential=play_data.get('score_differential', 0),
            timeouts_remaining=play_data.get('timeouts_remaining', 3),
            play_type=play_data.get('play_type', 'pass')
        )
        
        # Calculate before-play metrics
        ep_before = self.ep_model.calculate_expected_points(context_before)
        wp_before = self.wp_model.calculate_win_probability(context_before)
        
        # Create after-play context
        yards_gained = play_data.get('yards_gained', 0)
        touchdown = play_data.get('touchdown', False)
        turnover = play_data.get('interception', False) or play_data.get('fumble_lost', False)
        
        if touchdown:
            ep_after = 7.0
            wp_after = min(0.95, wp_before + 0.15)
        elif turnover:
            ep_after = -ep_before  # Opponent gets the ball
            wp_after = 1 - wp_before
        else:
            # Normal play - update field position
            new_yard_line = max(0, context_before.yardline_100 - yards_gained)
            new_down = 1 if yards_gained >= context_before.ydstogo else context_before.down + 1
            
            context_after = PlayContext(
                down=new_down,
                ydstogo=10 if yards_gained >= context_before.ydstogo else context_before.ydstogo - yards_gained,
                yardline_100=new_yard_line,
                quarter=context_before.quarter,
                game_seconds_remaining=max(0, context_before.game_seconds_remaining - 40),
                score_differential=context_before.score_differential,
                timeouts_remaining=context_before.timeouts_remaining,
                play_type=context_before.play_type
            )
            
            if new_down > 4:  # Turnover on downs
                ep_after = -self.ep_model.calculate_expected_points(context_after)
                wp_after = 1 - self.wp_model.calculate_win_probability(context_after)
            else:
                ep_after = self.ep_model.calculate_expected_points(context_after)
                wp_after = self.wp_model.calculate_win_probability(context_after)
        
        # Calculate derived metrics
        epa = ep_after - ep_before
        wpa = wp_after - wp_before
        
        # Calculate leverage (how much the play could matter)
        leverage = abs(wpa) if abs(wpa) > 0.02 else 0.02
        
        # Calculate success rate (did the play achieve its goal?)
        if context_before.down <= 2:
            success = yards_gained >= max(4, context_before.ydstogo * 0.5)
        else:
            success = yards_gained >= context_before.ydstogo
        
        # Calculate clutch index (performance in high-leverage situations)
        clutch_multiplier = 1.0
        if context_before.game_seconds_remaining < 300:  # Last 5 minutes
            clutch_multiplier = 1.5
        if abs(context_before.score_differential) <= 7:  # Close game
            clutch_multiplier *= 1.3
        
        clutch_index = epa * clutch_multiplier if success else epa * clutch_multiplier * 0.5
        
        # Explosive play check
        explosive_play = yards_gained >= 20 or touchdown
        
        return AdvancedMetrics(
            expected_points_before=ep_before,
            expected_points_after=ep_after,
            epa=epa,
            win_prob_before=wp_before,
            win_prob_after=wp_after,
            wpa=wpa,
            leverage=leverage,
            clutch_index=clutch_index,
            success_rate=1.0 if success else 0.0,
            explosive_play=explosive_play
        )
    
    def generate_team_insights(self, team_abbr: str, season: int) -> Optional[TeamInsights]:
        """Generate comprehensive insights for a team in a given season.
        
        Args:
            team_abbr: Team abbreviation (e.g., 'SF', 'KC')
            season: Season year
            
        Returns:
            TeamInsights object with all calculated metrics
        """
        try:
            # Get team's plays for the season
            team_plays = self.db_session.query(PlayModel).filter(
                and_(
                    PlayModel.season == season,
                    PlayModel.posteam == team_abbr
                )
            ).all()
            
            if not team_plays:
                self.logger.warning(f"No plays found for {team_abbr} in {season}")
                return None
            
            # Calculate advanced metrics for all plays
            play_metrics = []
            for play in team_plays:
                play_data = {
                    'down': play.down,
                    'ydstogo': play.ydstogo,
                    'yardline_100': play.yardline_100,
                    'qtr': play.qtr,
                    'game_seconds_remaining': 3600 - (((play.qtr or 1) - 1) * 900),  # Approximate
                    'score_differential': 0,  # Would need game state
                    'timeouts_remaining': 3,
                    'play_type': play.play_type,
                    'yards_gained': play.yards_gained or 0,
                    'touchdown': play.touchdown or False,
                    'interception': False,  # Would need to parse desc
                    'fumble_lost': False
                }
                
                metrics = self.calculate_play_metrics(play_data)
                play_metrics.append(metrics)
            
            # Aggregate metrics
            total_plays = len(play_metrics)
            if total_plays == 0:
                return None
            
            # Offensive metrics
            offensive_epa = sum(m.epa for m in play_metrics) / total_plays
            
            # Separate by play type
            pass_plays = [m for i, m in enumerate(play_metrics) if team_plays[i].play_type == 'pass']
            rush_plays = [m for i, m in enumerate(play_metrics) if team_plays[i].play_type == 'run']
            
            passing_epa = sum(m.epa for m in pass_plays) / len(pass_plays) if pass_plays else 0
            rushing_epa = sum(m.epa for m in rush_plays) / len(rush_plays) if rush_plays else 0
            
            # Red zone plays (inside 20 yard line)
            red_zone_plays = [m for i, m in enumerate(play_metrics) if team_plays[i].yardline_100 <= 20]
            red_zone_touchdowns = sum(1 for i in range(len(team_plays)) 
                                    if team_plays[i].yardline_100 <= 20 and team_plays[i].touchdown)
            red_zone_efficiency = red_zone_touchdowns / len(red_zone_plays) if red_zone_plays else 0
            
            # Third down plays
            third_down_plays = [i for i in range(len(team_plays)) if team_plays[i].down == 3]
            third_down_conversions = sum(1 for i in third_down_plays 
                                       if (team_plays[i].yards_gained or 0) >= (team_plays[i].ydstogo or 10))
            third_down_rate = third_down_conversions / len(third_down_plays) if third_down_plays else 0
            
            # Get defensive stats (plays against this team)
            def_plays = self.db_session.query(PlayModel).filter(
                and_(
                    PlayModel.season == season,
                    PlayModel.defteam == team_abbr
                )
            ).all()
            
            def_metrics = []
            for play in def_plays:
                play_data = {
                    'down': play.down or 1,
                    'ydstogo': play.ydstogo or 10,
                    'yardline_100': play.yardline_100 or 50,
                    'qtr': play.qtr or 1,
                    'game_seconds_remaining': 3600 - (((play.qtr or 1) - 1) * 900),
                    'score_differential': play.score_differential or 0,
                    'timeouts_remaining': 3,
                    'play_type': play.play_type or 'pass',
                    'yards_gained': play.yards_gained or 0,
                    'touchdown': play.touchdown or False,
                    'interception': False,
                    'fumble_lost': False
                }
                metrics = self.calculate_play_metrics(play_data)
                def_metrics.append(metrics)
            
            # Defensive metrics (negative EPA is good for defense)
            defensive_epa = -sum(m.epa for m in def_metrics) / len(def_metrics) if def_metrics else 0
            
            def_pass_plays = [m for i, m in enumerate(def_metrics) if def_plays[i].play_type == 'pass']
            def_rush_plays = [m for i, m in enumerate(def_metrics) if def_plays[i].play_type == 'run']
            
            pass_defense_epa = -sum(m.epa for m in def_pass_plays) / len(def_pass_plays) if def_pass_plays else 0
            run_defense_epa = -sum(m.epa for m in def_rush_plays) / len(def_rush_plays) if def_rush_plays else 0
            
            # More sophisticated metrics would require additional data
            # For now, use placeholder values with some variation
            base_clutch = offensive_epa * 1.2
            base_trend = offensive_epa - defensive_epa
            
            return TeamInsights(
                team_abbr=team_abbr,
                season=season,
                offensive_epa_per_play=offensive_epa,
                passing_epa_per_play=passing_epa,
                rushing_epa_per_play=rushing_epa,
                red_zone_efficiency=red_zone_efficiency,
                third_down_conversion_rate=third_down_rate,
                defensive_epa_per_play=defensive_epa,
                pass_defense_epa=pass_defense_epa,
                run_defense_epa=run_defense_epa,
                red_zone_defense=max(0, 1 - red_zone_efficiency - 0.2),
                third_down_defense=max(0, 1 - third_down_rate - 0.1),
                two_minute_drill_efficiency=base_clutch,
                clutch_performance=base_clutch,
                turnover_margin=0.0,  # Would need turnover data
                garbage_time_adjusted_epa=offensive_epa * 0.95,
                strength_of_schedule=0.5,  # Would need opponent strength data
                home_field_advantage=0.1,  # League average
                early_season_performance=base_trend * 0.9,
                late_season_performance=base_trend * 1.1,
                improvement_trajectory=base_trend * 0.1
            )
            
        except Exception as e:
            self.logger.error(f"Error generating team insights for {team_abbr}: {e}")
            return None
    
    def _generate_basic_game_insight(self, game: GameModel) -> GameInsight:
        """Generate basic game insight when play-by-play data is not available.
        
        Args:
            game: Game model instance
            
        Returns:
            Basic GameInsight with available game information
        """
        from datetime import datetime
        
        # Calculate basic stats from game info
        total_points = (game.home_score or 0) + (game.away_score or 0) if game.home_score is not None else 0
        point_diff = abs((game.home_score or 0) - (game.away_score or 0)) if game.home_score is not None else 0
        
        # Determine game characteristics
        is_high_scoring = total_points > 50 if game.home_score is not None else False
        is_close_game = point_diff <= 7 if game.home_score is not None else False
        
        # Basic team performance (without plays)
        home_team_metrics = TeamInsights(
            team_abbr=game.home_team,
            epa_per_play=0.0,  # Not available without plays
            success_rate=0.0,  # Not available without plays  
            explosive_play_rate=0.0,  # Not available without plays
            three_and_out_rate=0.0,  # Not available without plays
            red_zone_efficiency=0.0,  # Not available without plays
            turnover_rate=0.0,  # Not available without plays
            time_of_possession=0.0,  # Not available without plays
            avg_drive_length=0.0,  # Not available without plays
            points_per_drive=0.0,  # Not available without plays
            defensive_stops=0,  # Not available without plays
            pressure_rate=0.0  # Not available without plays
        )
        
        away_team_metrics = TeamInsights(
            team_abbr=game.away_team,
            epa_per_play=0.0,
            success_rate=0.0,
            explosive_play_rate=0.0,
            three_and_out_rate=0.0,
            red_zone_efficiency=0.0,
            turnover_rate=0.0,
            time_of_possession=0.0,
            avg_drive_length=0.0,
            points_per_drive=0.0,
            defensive_stops=0,
            pressure_rate=0.0
        )
        
        # Create basic game insight
        basic_insight = GameInsight(
            game_id=game.game_id,
            game_date=game.game_date or datetime.now().date(),
            home_team=game.home_team,
            away_team=game.away_team,
            home_score=game.home_score or 0,
            away_score=game.away_score or 0,
            home_team_insights=home_team_metrics,
            away_team_insights=away_team_metrics,
            key_plays=[],  # No plays available
            game_flow_analysis={
                "total_points": total_points,
                "point_differential": point_diff,
                "is_high_scoring": is_high_scoring,
                "is_close_game": is_close_game,
                "game_conditions": {
                    "surface": game.surface,
                    "roof": game.roof,
                    "temperature": game.temp,
                    "wind": game.wind
                }
            },
            momentum_shifts=[],  # Not available without plays
            clutch_performance={},  # Not available without plays
            efficiency_ratings={
                "note": "Advanced efficiency ratings require play-by-play data"
            },
            situational_analysis={
                "note": "Situational analysis requires play-by-play data"
            },
            coaching_decisions=[],  # Not available without plays
            injury_impact=[],  # Not available in basic game data
            weather_impact="neutral",  # Basic assessment
            home_field_advantage=3.0 if game.home_score and game.away_score and game.home_score > game.away_score else 0.0,
            prediction_accuracy=0.0,  # Not available without predictions
            betting_analysis={},  # Would need betting lines
            comparison_to_average={
                "note": "Comparisons require historical play data"
            }
        )
        
        return basic_insight

    def generate_game_insights(self, game_id: str) -> Optional[GameInsight]:
        """Generate insights for a specific game.
        
        Args:
            game_id: Game identifier
            
        Returns:
            GameInsight object with game analysis
        """
        try:
            # Get game info
            game = self.db_session.query(GameModel).filter(
                GameModel.game_id == game_id
            ).first()
            
            if not game:
                self.logger.warning(f"Game {game_id} not found")
                return None
            
            # Get all plays for this game
            plays = self.db_session.query(PlayModel).filter(
                PlayModel.game_id == game_id
            ).all()
            
            if not plays:
                self.logger.warning(f"No plays found for game {game_id}")
                # Return basic game insight without play-by-play data
                return self._generate_basic_game_insight(game)
            
            # Calculate metrics for all plays
            home_epa = 0
            away_epa = 0
            max_epa = 0
            max_wpa = 0
            momentum_changes = 0
            last_wp = 0.5
            
            for play in plays:
                play_data = {
                    'down': play.down or 1,
                    'ydstogo': play.ydstogo or 10,
                    'yardline_100': play.yardline_100 or 50,
                    'qtr': play.qtr or 1,
                    'game_seconds_remaining': 3600 - (((play.qtr or 1) - 1) * 900),
                    'score_differential': play.score_differential or 0,
                    'timeouts_remaining': 3,
                    'play_type': play.play_type or 'pass',
                    'yards_gained': play.yards_gained or 0,
                    'touchdown': play.touchdown or False,
                    'interception': False,
                    'fumble_lost': False
                }
                
                metrics = self.calculate_play_metrics(play_data)
                
                # Track EPA by team
                if play.posteam == game.home_team:
                    home_epa += metrics.epa
                elif play.posteam == game.away_team:
                    away_epa += metrics.epa
                
                # Track biggest plays
                if abs(metrics.epa) > abs(max_epa):
                    max_epa = metrics.epa
                if abs(metrics.wpa) > abs(max_wpa):
                    max_wpa = metrics.wpa
                
                # Count momentum swings
                current_wp = metrics.win_prob_after
                if abs(current_wp - last_wp) > 0.15:  # 15% swing
                    momentum_changes += 1
                last_wp = current_wp
            
            # Calculate game-level metrics
            total_epa = abs(home_epa) + abs(away_epa)
            excitement_index = min(10, total_epa + momentum_changes)
            
            # Competitiveness based on score differential
            if game.home_score is not None and game.away_score is not None:
                score_diff = abs(game.home_score - game.away_score)
                competitiveness = max(0, 1 - (score_diff / 35.0))  # Close games are more competitive
            else:
                competitiveness = 0.5
            
            # Determine battle winners (simplified)
            red_zone_winner = game.home_team if home_epa > away_epa else game.away_team
            third_down_winner = game.home_team if home_epa > away_epa else game.away_team
            turnover_winner = "Even"  # Would need turnover data
            
            return GameInsight(
                game_id=game_id,
                home_team=game.home_team,
                away_team=game.away_team,
                game_date=game.game_date,
                excitement_index=excitement_index,
                competitiveness=competitiveness,
                momentum_swings=momentum_changes,
                home_team_epa=home_epa,
                away_team_epa=away_epa,
                passing_game_dominance=0.0,  # Would need pass vs run breakdown
                rushing_game_dominance=0.0,
                biggest_play_epa=max_epa,
                biggest_play_wpa=max_wpa,
                turning_point_quarter=2,  # Would need detailed analysis
                red_zone_battle=red_zone_winner,
                third_down_battle=third_down_winner,
                turnover_battle=turnover_winner
            )
            
        except Exception as e:
            self.logger.error(f"Error generating game insights for {game_id}: {e}")
            return None
    
    def get_league_leaders(self, season: int, metric: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get league leaders for a specific advanced metric.
        
        Args:
            season: Season year
            metric: Metric name (e.g., 'offensive_epa_per_play')
            limit: Number of teams to return
            
        Returns:
            List of team rankings with metric values
        """
        try:
            # Get all teams for the season
            teams = self.db_session.query(TeamModel).all()
            team_metrics = []
            
            for team in teams:
                insights = self.generate_team_insights(team.team_abbr, season)
                if insights:
                    metric_value = getattr(insights, metric, 0)
                    team_metrics.append({
                        'team_abbr': team.team_abbr,
                        'team_name': f"{team.team_name} {team.team_nick}",
                        'metric': metric,
                        'value': metric_value
                    })
            
            # Sort by metric value (descending for most metrics)
            reverse = True
            if 'defense' in metric or 'allowed' in metric:
                reverse = False  # Lower is better for defensive metrics
            
            team_metrics.sort(key=lambda x: x['value'], reverse=reverse)
            
            return team_metrics[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting league leaders for {metric}: {e}")
            return []
    
    def compare_teams(self, team1: str, team2: str, season: int) -> Dict[str, Any]:
        """Compare two teams using advanced metrics.
        
        Args:
            team1: First team abbreviation
            team2: Second team abbreviation
            season: Season year
            
        Returns:
            Dictionary with detailed comparison
        """
        try:
            insights1 = self.generate_team_insights(team1, season)
            insights2 = self.generate_team_insights(team2, season)
            
            if not insights1 or not insights2:
                return {}
            
            comparison = {
                'team1': team1,
                'team2': team2,
                'season': season,
                'advantages': {
                    team1: [],
                    team2: []
                },
                'metrics_comparison': {}
            }
            
            # Compare key metrics
            metrics_to_compare = [
                'offensive_epa_per_play',
                'defensive_epa_per_play',
                'red_zone_efficiency',
                'third_down_conversion_rate',
                'clutch_performance'
            ]
            
            for metric in metrics_to_compare:
                val1 = getattr(insights1, metric)
                val2 = getattr(insights2, metric)
                
                comparison['metrics_comparison'][metric] = {
                    team1: val1,
                    team2: val2,
                    'advantage': team1 if val1 > val2 else team2,
                    'difference': abs(val1 - val2)
                }
                
                # Determine advantages
                if val1 > val2 and abs(val1 - val2) > 0.05:  # Significant difference
                    comparison['advantages'][team1].append(metric)
                elif val2 > val1 and abs(val1 - val2) > 0.05:
                    comparison['advantages'][team2].append(metric)
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Error comparing teams {team1} vs {team2}: {e}")
            return {}
    
    def generate_season_narrative(self, team_abbr: str, season: int) -> str:
        """Generate a narrative summary of a team's season using advanced metrics.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year
            
        Returns:
            String narrative describing the team's season
        """
        try:
            insights = self.generate_team_insights(team_abbr, season)
            if not insights:
                return f"Unable to generate insights for {team_abbr} in {season}"
            
            # Get team info
            team = self.db_session.query(TeamModel).filter(
                TeamModel.team_abbr == team_abbr
            ).first()
            
            team_name = f"{team.team_name} {team.team_nick}" if team else team_abbr
            
            # Build narrative based on metrics
            narrative_parts = [f"**{team_name} - {season} Season Analysis**\n"]
            
            # Offensive analysis
            if insights.offensive_epa_per_play > 0.1:
                narrative_parts.append(f"The {team_name} boasted a highly efficient offense, averaging {insights.offensive_epa_per_play:.3f} EPA per play.")
            elif insights.offensive_epa_per_play < -0.05:
                narrative_parts.append(f"The {team_name} struggled offensively, posting a concerning {insights.offensive_epa_per_play:.3f} EPA per play.")
            else:
                narrative_parts.append(f"The {team_name} offense was adequate, generating {insights.offensive_epa_per_play:.3f} EPA per play.")
            
            # Passing vs rushing
            if insights.passing_epa_per_play > insights.rushing_epa_per_play + 0.1:
                narrative_parts.append("Their aerial attack was particularly potent, significantly outperforming their ground game.")
            elif insights.rushing_epa_per_play > insights.passing_epa_per_play + 0.05:
                narrative_parts.append("They established themselves as a run-first team, finding more success on the ground than through the air.")
            else:
                narrative_parts.append("They maintained a balanced offensive approach with both passing and rushing contributing.")
            
            # Red zone efficiency
            if insights.red_zone_efficiency > 0.6:
                narrative_parts.append(f"In the red zone, they were lethal, converting {insights.red_zone_efficiency:.1%} of their opportunities into touchdowns.")
            elif insights.red_zone_efficiency < 0.4:
                narrative_parts.append(f"Red zone struggles plagued the team, managing only {insights.red_zone_efficiency:.1%} touchdown conversion rate.")
            
            # Defensive analysis
            if insights.defensive_epa_per_play > 0.05:
                narrative_parts.append("Defensively, they were dominant, consistently putting opponents in difficult situations.")
            elif insights.defensive_epa_per_play < -0.05:
                narrative_parts.append("Their defense was a liability, allowing opponents to move the ball with ease.")
            else:
                narrative_parts.append("Their defense was serviceable, providing adequate resistance to opposing offenses.")
            
            # Clutch performance
            if insights.clutch_performance > 0.15:
                narrative_parts.append("When the stakes were highest, this team delivered, excelling in clutch situations.")
            elif insights.clutch_performance < -0.1:
                narrative_parts.append("Unfortunately, they often wilted under pressure, struggling in crucial moments.")
            
            # Season trajectory
            if insights.improvement_trajectory > 0.05:
                narrative_parts.append("The team showed encouraging signs of improvement as the season progressed.")
            elif insights.improvement_trajectory < -0.05:
                narrative_parts.append("Concerning regression was evident as the season wore on.")
            
            return " ".join(narrative_parts)
            
        except Exception as e:
            self.logger.error(f"Error generating narrative for {team_abbr}: {e}")
            return f"Unable to generate season narrative for {team_abbr}"