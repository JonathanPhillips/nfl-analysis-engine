"""Feature engineering for NFL prediction models."""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, date, timedelta
import logging
from sqlalchemy.orm import Session

from ..models.team import TeamModel
from ..models.game import GameModel
from ..models.play import PlayModel
from ..models.player import PlayerModel

logger = logging.getLogger(__name__)


@dataclass
class TeamStats:
    """Container for team statistics."""
    team_abbr: str
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    points_for: float = 0.0
    points_against: float = 0.0
    yards_for: float = 0.0
    yards_against: float = 0.0
    turnovers_for: float = 0.0
    turnovers_against: float = 0.0
    penalties_for: float = 0.0
    penalties_against: float = 0.0
    time_of_possession: float = 0.0
    third_down_pct: float = 0.0
    red_zone_pct: float = 0.0
    
    @property
    def win_percentage(self) -> float:
        """Calculate win percentage."""
        if self.games_played == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / self.games_played
    
    @property
    def points_per_game(self) -> float:
        """Calculate points per game."""
        return self.points_for / max(1, self.games_played)
    
    @property
    def points_allowed_per_game(self) -> float:
        """Calculate points allowed per game."""
        return self.points_against / max(1, self.games_played)
    
    @property
    def point_differential(self) -> float:
        """Calculate point differential per game."""
        return self.points_per_game - self.points_allowed_per_game


class FeatureEngineer:
    """Feature engineering for NFL prediction models."""
    
    def __init__(self, db_session: Session):
        """Initialize feature engineer with database session."""
        self.db_session = db_session
        self.team_stats_cache: Dict[str, Dict[int, TeamStats]] = {}
    
    def get_team_stats(self, team_abbr: str, season: int, 
                      end_date: Optional[date] = None) -> TeamStats:
        """Get team statistics for a given season up to a specific date.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year
            end_date: Calculate stats only up to this date (exclusive)
            
        Returns:
            TeamStats object with calculated statistics
        """
        cache_key = f"{team_abbr}_{season}_{end_date}"
        
        # Check cache first
        if season in self.team_stats_cache.get(team_abbr, {}):
            if end_date is None:  # Full season stats
                return self.team_stats_cache[team_abbr][season]
        
        stats = TeamStats(team_abbr=team_abbr)
        
        # Query games for this team and season
        query = self.db_session.query(GameModel).filter(
            GameModel.season == season,
            (GameModel.home_team == team_abbr) | (GameModel.away_team == team_abbr)
        )
        
        if end_date:
            query = query.filter(GameModel.game_date < end_date)
        
        games = query.all()
        
        if not games:
            return stats
        
        stats.games_played = len(games)
        
        # Calculate basic stats
        for game in games:
            is_home = game.home_team == team_abbr
            team_score = game.home_score if is_home else game.away_score
            opp_score = game.away_score if is_home else game.home_score
            
            # Handle None scores
            if team_score is None or opp_score is None:
                continue
            
            stats.points_for += team_score
            stats.points_against += opp_score
            
            # Determine win/loss/tie
            if team_score > opp_score:
                stats.wins += 1
            elif team_score < opp_score:
                stats.losses += 1
            else:
                stats.ties += 1
        
        # Cache full season stats
        if end_date is None:
            if team_abbr not in self.team_stats_cache:
                self.team_stats_cache[team_abbr] = {}
            self.team_stats_cache[team_abbr][season] = stats
        
        return stats
    
    def get_head_to_head_stats(self, team1: str, team2: str, 
                              seasons: int = 3) -> Dict[str, float]:
        """Get head-to-head statistics between two teams.
        
        Args:
            team1: First team abbreviation
            team2: Second team abbreviation
            seasons: Number of recent seasons to consider
            
        Returns:
            Dictionary with head-to-head statistics
        """
        current_year = datetime.now().year
        start_year = current_year - seasons
        
        games = self.db_session.query(GameModel).filter(
            GameModel.season >= start_year,
            (
                (GameModel.home_team == team1) & (GameModel.away_team == team2)
            ) | (
                (GameModel.home_team == team2) & (GameModel.away_team == team1)
            )
        ).all()
        
        if not games:
            return {
                'h2h_games': 0,
                'team1_wins': 0,
                'team2_wins': 0,
                'ties': 0,
                'avg_total_points': 0.0,
                'avg_point_diff': 0.0
            }
        
        team1_wins = 0
        team2_wins = 0
        ties = 0
        total_points = 0
        point_diffs = []
        
        for game in games:
            if game.home_score is None or game.away_score is None:
                continue
                
            total_points += game.home_score + game.away_score
            
            # Determine winner from team1's perspective
            if game.home_team == team1:
                team1_score = game.home_score
                team2_score = game.away_score
            else:
                team1_score = game.away_score
                team2_score = game.home_score
            
            point_diff = team1_score - team2_score
            point_diffs.append(point_diff)
            
            if team1_score > team2_score:
                team1_wins += 1
            elif team1_score < team2_score:
                team2_wins += 1
            else:
                ties += 1
        
        return {
            'h2h_games': len(games),
            'team1_wins': team1_wins,
            'team2_wins': team2_wins,
            'ties': ties,
            'avg_total_points': total_points / max(1, len(games)),
            'avg_point_diff': np.mean(point_diffs) if point_diffs else 0.0
        }
    
    def get_recent_form(self, team_abbr: str, season: int, 
                       end_date: date, games: int = 5) -> Dict[str, float]:
        """Get recent form statistics for a team.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year
            end_date: Get form before this date
            games: Number of recent games to consider
            
        Returns:
            Dictionary with recent form statistics
        """
        query = self.db_session.query(GameModel).filter(
            GameModel.season == season,
            GameModel.game_date < end_date,
            (GameModel.home_team == team_abbr) | (GameModel.away_team == team_abbr)
        ).order_by(GameModel.game_date.desc()).limit(games)
        
        recent_games = query.all()
        
        if not recent_games:
            return {
                'recent_games': 0,
                'recent_wins': 0,
                'recent_losses': 0,
                'recent_win_pct': 0.0,
                'recent_ppg': 0.0,
                'recent_papg': 0.0,
                'recent_form': 0.0
            }
        
        wins = 0
        total_points_for = 0
        total_points_against = 0
        
        for game in recent_games:
            if game.home_score is None or game.away_score is None:
                continue
                
            is_home = game.home_team == team_abbr
            team_score = game.home_score if is_home else game.away_score
            opp_score = game.away_score if is_home else game.home_score
            
            total_points_for += team_score
            total_points_against += opp_score
            
            if team_score > opp_score:
                wins += 1
        
        games_played = len(recent_games)
        win_pct = wins / games_played if games_played > 0 else 0.0
        
        return {
            'recent_games': games_played,
            'recent_wins': wins,
            'recent_losses': games_played - wins,
            'recent_win_pct': win_pct,
            'recent_ppg': total_points_for / max(1, games_played),
            'recent_papg': total_points_against / max(1, games_played),
            'recent_form': win_pct * 2 - 1  # Scale from -1 to 1
        }
    
    def calculate_strength_of_schedule(self, team_abbr: str, season: int,
                                     end_date: Optional[date] = None) -> float:
        """Calculate strength of schedule for a team.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year
            end_date: Calculate only up to this date
            
        Returns:
            Strength of schedule (opponent win percentage)
        """
        query = self.db_session.query(GameModel).filter(
            GameModel.season == season,
            (GameModel.home_team == team_abbr) | (GameModel.away_team == team_abbr)
        )
        
        if end_date:
            query = query.filter(GameModel.game_date < end_date)
        
        games = query.all()
        
        if not games:
            return 0.5  # Neutral strength if no games
        
        opponent_win_percentages = []
        
        for game in games:
            opponent = game.away_team if game.home_team == team_abbr else game.home_team
            opp_stats = self.get_team_stats(opponent, season, end_date)
            opponent_win_percentages.append(opp_stats.win_percentage)
        
        return np.mean(opponent_win_percentages) if opponent_win_percentages else 0.5
    
    def create_game_features(self, home_team: str, away_team: str, 
                           game_date: date, season: int) -> Dict[str, float]:
        """Create feature set for a specific game.
        
        Args:
            home_team: Home team abbreviation
            away_team: Away team abbreviation
            game_date: Game date
            season: Season year
            
        Returns:
            Dictionary of features for the game
        """
        features = {}
        
        # Get team statistics up to game date
        home_stats = self.get_team_stats(home_team, season, game_date)
        away_stats = self.get_team_stats(away_team, season, game_date)
        
        # Basic team statistics
        features.update({
            'home_win_pct': home_stats.win_percentage,
            'away_win_pct': away_stats.win_percentage,
            'home_ppg': home_stats.points_per_game,
            'away_ppg': away_stats.points_per_game,
            'home_papg': home_stats.points_allowed_per_game,
            'away_papg': away_stats.points_allowed_per_game,
            'home_point_diff': home_stats.point_differential,
            'away_point_diff': away_stats.point_differential,
            'home_games_played': home_stats.games_played,
            'away_games_played': away_stats.games_played,
        })
        
        # Head-to-head statistics
        h2h_stats = self.get_head_to_head_stats(home_team, away_team)
        features.update({
            f'h2h_{k}': v for k, v in h2h_stats.items()
        })
        
        # Recent form
        home_form = self.get_recent_form(home_team, season, game_date)
        away_form = self.get_recent_form(away_team, season, game_date)
        
        features.update({
            f'home_{k}': v for k, v in home_form.items()
        })
        features.update({
            f'away_{k}': v for k, v in away_form.items()
        })
        
        # Strength of schedule
        features['home_sos'] = self.calculate_strength_of_schedule(home_team, season, game_date)
        features['away_sos'] = self.calculate_strength_of_schedule(away_team, season, game_date)
        
        # Matchup features
        features.update({
            'win_pct_diff': home_stats.win_percentage - away_stats.win_percentage,
            'ppg_diff': home_stats.points_per_game - away_stats.points_per_game,
            'papg_diff': away_stats.points_allowed_per_game - home_stats.points_allowed_per_game,
            'point_diff_advantage': home_stats.point_differential - away_stats.point_differential,
            'form_diff': home_form['recent_form'] - away_form['recent_form'],
            'sos_diff': features['away_sos'] - features['home_sos'],  # Higher opponent SOS is better
        })
        
        # Game context features
        features.update({
            'is_divisional': self._is_divisional_game(home_team, away_team),
            'is_conference': self._is_conference_game(home_team, away_team),
            'home_advantage': 1.0,  # Always 1 for home team
        })
        
        # Time-based features
        features.update({
            'week_of_season': self._get_week_of_season(game_date, season),
            'days_since_season_start': self._days_since_season_start(game_date, season),
        })
        
        return features
    
    def _is_divisional_game(self, team1: str, team2: str) -> float:
        """Check if game is divisional matchup."""
        try:
            from ..models.team import get_team_division
            team1_conf, team1_div = get_team_division(team1)
            team2_conf, team2_div = get_team_division(team2)
            return 1.0 if (team1_conf == team2_conf and team1_div == team2_div) else 0.0
        except ValueError:
            return 0.0
    
    def _is_conference_game(self, team1: str, team2: str) -> float:
        """Check if game is conference matchup."""
        try:
            from ..models.team import get_team_division
            team1_conf, _ = get_team_division(team1)
            team2_conf, _ = get_team_division(team2)
            return 1.0 if team1_conf == team2_conf else 0.0
        except ValueError:
            return 0.5
    
    def _get_week_of_season(self, game_date: date, season: int) -> float:
        """Get approximate week of NFL season."""
        # NFL season typically starts first week of September
        season_start = date(season, 9, 1)
        # Find first Thursday of September (approximate start)
        while season_start.weekday() != 3:  # 3 = Thursday
            season_start += timedelta(days=1)
        
        days_elapsed = (game_date - season_start).days
        week = max(1, (days_elapsed // 7) + 1)
        return min(22, week)  # Cap at 22 weeks (including playoffs)
    
    def _days_since_season_start(self, game_date: date, season: int) -> float:
        """Get days since season start."""
        season_start = date(season, 9, 1)
        return max(0, (game_date - season_start).days)