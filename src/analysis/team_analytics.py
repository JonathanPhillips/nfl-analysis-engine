"""Advanced team-level analytics for NFL teams."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, func, case
from src.models.team import TeamModel
from src.models.play import PlayModel
from src.models.game import GameModel
import logging

logger = logging.getLogger(__name__)


@dataclass
class RedZoneStats:
    """Red zone performance statistics."""
    attempts: int
    touchdowns: int
    field_goals: int
    td_percentage: float
    fg_percentage: float
    success_percentage: float  # (TDs + FGs) / attempts


@dataclass
class ThirdDownStats:
    """Third down conversion statistics."""
    attempts: int
    conversions: int
    conversion_rate: float
    avg_yards_to_go: float
    success_by_distance: Dict[str, float]  # short/medium/long


@dataclass
class TurnoverStats:
    """Turnover differential statistics."""
    giveaways: int
    takeaways: int
    differential: int
    fumbles_lost: int
    fumbles_recovered: int
    interceptions_thrown: int
    interceptions_caught: int


@dataclass
class OffensiveEfficiency:
    """Offensive efficiency metrics."""
    total_plays: int
    total_yards: int
    yards_per_play: float
    first_downs: int
    first_down_rate: float
    explosive_plays: int  # 20+ yard gains
    explosive_play_rate: float
    avg_epa: float
    success_rate: float  # % plays with positive EPA


@dataclass
class DefensiveEfficiency:
    """Defensive efficiency metrics."""
    total_plays: int
    total_yards_allowed: int
    yards_per_play_allowed: float
    first_downs_allowed: int
    explosive_plays_allowed: int
    avg_epa_allowed: float
    success_rate_allowed: float
    sacks: int
    sack_rate: float


@dataclass
class TeamAnalytics:
    """Comprehensive team analytics."""
    team: str
    team_name: str
    season: int
    games_played: int
    
    # Efficiency metrics
    offensive_efficiency: OffensiveEfficiency
    defensive_efficiency: DefensiveEfficiency
    
    # Situational metrics
    red_zone_offense: RedZoneStats
    red_zone_defense: RedZoneStats
    third_down_offense: ThirdDownStats
    third_down_defense: ThirdDownStats
    
    # Turnover metrics
    turnover_stats: TurnoverStats
    
    # Overall performance
    points_per_game: float
    points_allowed_per_game: float
    point_differential: float


class TeamAnalyticsCalculator:
    """Calculator for advanced team analytics."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_team_analytics(self, season: int, team_abbr: Optional[str] = None) -> List[TeamAnalytics]:
        """Calculate comprehensive team analytics for all teams or specific team."""
        logger.info(f"Calculating team analytics for season {season}")
        
        # Get teams to analyze
        team_query = self.db.query(TeamModel)
        if team_abbr:
            team_query = team_query.filter(TeamModel.team_abbr == team_abbr)
        teams = team_query.all()
        
        team_analytics = []
        
        for team in teams:
            try:
                analytics = self._calculate_single_team_analytics(season, team.team_abbr, team.team_name)
                if analytics:
                    team_analytics.append(analytics)
            except Exception as e:
                logger.error(f"Error calculating analytics for {team.team_abbr}: {e}")
                continue
        
        return team_analytics
    
    def _calculate_single_team_analytics(self, season: int, team_abbr: str, team_name: str) -> Optional[TeamAnalytics]:
        """Calculate analytics for a single team."""
        
        # Get games played
        games_played = self.db.query(func.count(GameModel.game_id)).filter(
            ((GameModel.home_team == team_abbr) | (GameModel.away_team == team_abbr)),
            GameModel.season == season,
            GameModel.home_score.isnot(None)
        ).scalar() or 0
        
        if games_played == 0:
            return None
        
        # Calculate all metrics
        offensive_efficiency = self._calculate_offensive_efficiency(season, team_abbr)
        defensive_efficiency = self._calculate_defensive_efficiency(season, team_abbr)
        red_zone_offense = self._calculate_red_zone_stats(season, team_abbr, 'offense')
        red_zone_defense = self._calculate_red_zone_stats(season, team_abbr, 'defense')
        third_down_offense = self._calculate_third_down_stats(season, team_abbr, 'offense')
        third_down_defense = self._calculate_third_down_stats(season, team_abbr, 'defense')
        turnover_stats = self._calculate_turnover_stats(season, team_abbr)
        
        # Calculate scoring metrics
        scoring_stats = self._calculate_scoring_stats(season, team_abbr, games_played)
        
        return TeamAnalytics(
            team=team_abbr,
            team_name=team_name,
            season=season,
            games_played=games_played,
            offensive_efficiency=offensive_efficiency,
            defensive_efficiency=defensive_efficiency,
            red_zone_offense=red_zone_offense,
            red_zone_defense=red_zone_defense,
            third_down_offense=third_down_offense,
            third_down_defense=third_down_defense,
            turnover_stats=turnover_stats,
            points_per_game=scoring_stats['ppg'],
            points_allowed_per_game=scoring_stats['papg'],
            point_differential=scoring_stats['diff']
        )
    
    def _calculate_offensive_efficiency(self, season: int, team_abbr: str) -> OffensiveEfficiency:
        """Calculate offensive efficiency metrics."""
        query = text("""
            SELECT 
                COUNT(*) as total_plays,
                SUM(yards_gained) as total_yards,
                AVG(yards_gained) as yards_per_play,
                SUM(CASE WHEN first_down = true THEN 1 ELSE 0 END) as first_downs,
                SUM(CASE WHEN yards_gained >= 20 AND play_type = 'pass' THEN 1 
                         WHEN yards_gained >= 15 AND play_type = 'run' THEN 1 
                         ELSE 0 END) as explosive_plays,
                AVG(epa) as avg_epa,
                SUM(CASE WHEN epa > 0 THEN 1 ELSE 0 END) as successful_plays
            FROM plays 
            WHERE season = :season 
                AND posteam = :team
                AND play_type IN ('pass', 'run')
                AND yards_gained IS NOT NULL
        """)
        
        result = self.db.execute(query, {'season': season, 'team': team_abbr}).first()
        
        if not result or result.total_plays == 0:
            return OffensiveEfficiency(0, 0, 0.0, 0, 0.0, 0, 0.0, 0.0, 0.0)
        
        return OffensiveEfficiency(
            total_plays=result.total_plays,
            total_yards=result.total_yards or 0,
            yards_per_play=round(result.yards_per_play or 0, 2),
            first_downs=result.first_downs or 0,
            first_down_rate=round((result.first_downs or 0) / result.total_plays * 100, 1),
            explosive_plays=result.explosive_plays or 0,
            explosive_play_rate=round((result.explosive_plays or 0) / result.total_plays * 100, 1),
            avg_epa=round(result.avg_epa or 0, 3),
            success_rate=round((result.successful_plays or 0) / result.total_plays * 100, 1)
        )
    
    def _calculate_defensive_efficiency(self, season: int, team_abbr: str) -> DefensiveEfficiency:
        """Calculate defensive efficiency metrics."""
        query = text("""
            SELECT 
                COUNT(*) as total_plays,
                SUM(yards_gained) as total_yards,
                AVG(yards_gained) as yards_per_play,
                SUM(CASE WHEN first_down = true THEN 1 ELSE 0 END) as first_downs,
                SUM(CASE WHEN yards_gained >= 20 AND play_type = 'pass' THEN 1 
                         WHEN yards_gained >= 15 AND play_type = 'run' THEN 1 
                         ELSE 0 END) as explosive_plays,
                AVG(epa) as avg_epa,
                SUM(CASE WHEN epa > 0 THEN 1 ELSE 0 END) as successful_plays,
                SUM(CASE WHEN yards_gained < 0 THEN 1 ELSE 0 END) as sacks
            FROM plays 
            WHERE season = :season 
                AND defteam = :team
                AND play_type IN ('pass', 'run')
                AND yards_gained IS NOT NULL
        """)
        
        result = self.db.execute(query, {'season': season, 'team': team_abbr}).first()
        
        if not result or result.total_plays == 0:
            return DefensiveEfficiency(0, 0, 0.0, 0, 0, 0.0, 0.0, 0, 0.0)
        
        return DefensiveEfficiency(
            total_plays=result.total_plays,
            total_yards_allowed=result.total_yards or 0,
            yards_per_play_allowed=round(result.yards_per_play or 0, 2),
            first_downs_allowed=result.first_downs or 0,
            explosive_plays_allowed=result.explosive_plays or 0,
            avg_epa_allowed=round(result.avg_epa or 0, 3),
            success_rate_allowed=round((result.successful_plays or 0) / result.total_plays * 100, 1),
            sacks=result.sacks or 0,
            sack_rate=round((result.sacks or 0) / result.total_plays * 100, 1)
        )
    
    def _calculate_red_zone_stats(self, season: int, team_abbr: str, side: str) -> RedZoneStats:
        """Calculate red zone statistics."""
        team_filter = 'posteam' if side == 'offense' else 'defteam'
        
        query = text(f"""
            SELECT 
                COUNT(CASE WHEN yardline_100 <= 20 AND down = 1 THEN 1 END) as attempts,
                SUM(CASE WHEN touchdown = true THEN 1 ELSE 0 END) as touchdowns,
                SUM(CASE WHEN play_type = 'field_goal' AND yards_gained > 0 THEN 1 ELSE 0 END) as field_goals
            FROM plays 
            WHERE season = :season 
                AND {team_filter} = :team
                AND yardline_100 <= 20
                AND play_type IN ('pass', 'run', 'field_goal')
        """)
        
        result = self.db.execute(query, {'season': season, 'team': team_abbr}).first()
        
        attempts = result.attempts or 0
        touchdowns = result.touchdowns or 0
        field_goals = result.field_goals or 0
        
        if attempts == 0:
            return RedZoneStats(0, 0, 0, 0.0, 0.0, 0.0)
        
        return RedZoneStats(
            attempts=attempts,
            touchdowns=touchdowns,
            field_goals=field_goals,
            td_percentage=round(touchdowns / attempts * 100, 1),
            fg_percentage=round(field_goals / attempts * 100, 1),
            success_percentage=round((touchdowns + field_goals) / attempts * 100, 1)
        )
    
    def _calculate_third_down_stats(self, season: int, team_abbr: str, side: str) -> ThirdDownStats:
        """Calculate third down conversion statistics."""
        team_filter = 'posteam' if side == 'offense' else 'defteam'
        
        query = text(f"""
            SELECT 
                COUNT(*) as attempts,
                SUM(CASE WHEN first_down = true OR touchdown = true THEN 1 ELSE 0 END) as conversions,
                AVG(ydstogo) as avg_yards_to_go,
                SUM(CASE WHEN ydstogo <= 3 AND (first_down = true OR touchdown = true) THEN 1 ELSE 0 END) as short_conversions,
                SUM(CASE WHEN ydstogo <= 3 THEN 1 ELSE 0 END) as short_attempts,
                SUM(CASE WHEN ydstogo BETWEEN 4 AND 7 AND (first_down = true OR touchdown = true) THEN 1 ELSE 0 END) as medium_conversions,
                SUM(CASE WHEN ydstogo BETWEEN 4 AND 7 THEN 1 ELSE 0 END) as medium_attempts,
                SUM(CASE WHEN ydstogo >= 8 AND (first_down = true OR touchdown = true) THEN 1 ELSE 0 END) as long_conversions,
                SUM(CASE WHEN ydstogo >= 8 THEN 1 ELSE 0 END) as long_attempts
            FROM plays 
            WHERE season = :season 
                AND {team_filter} = :team
                AND down = 3
                AND play_type IN ('pass', 'run')
        """)
        
        result = self.db.execute(query, {'season': season, 'team': team_abbr}).first()
        
        attempts = result.attempts or 0
        conversions = result.conversions or 0
        
        if attempts == 0:
            return ThirdDownStats(0, 0, 0.0, 0.0, {})
        
        # Calculate success by distance
        success_by_distance = {
            'short': round((result.short_conversions or 0) / max(1, result.short_attempts or 1) * 100, 1),
            'medium': round((result.medium_conversions or 0) / max(1, result.medium_attempts or 1) * 100, 1),
            'long': round((result.long_conversions or 0) / max(1, result.long_attempts or 1) * 100, 1)
        }
        
        return ThirdDownStats(
            attempts=attempts,
            conversions=conversions,
            conversion_rate=round(conversions / attempts * 100, 1),
            avg_yards_to_go=round(result.avg_yards_to_go or 0, 1),
            success_by_distance=success_by_distance
        )
    
    def _calculate_turnover_stats(self, season: int, team_abbr: str) -> TurnoverStats:
        """Calculate turnover differential statistics."""
        query = text("""
            SELECT 
                -- Giveaways (when team is on offense)
                SUM(CASE WHEN posteam = :team AND interception = true THEN 1 ELSE 0 END) as ints_thrown,
                SUM(CASE WHEN posteam = :team AND fumble = true THEN 1 ELSE 0 END) as fumbles_lost,
                -- Takeaways (when team is on defense)  
                SUM(CASE WHEN defteam = :team AND interception = true THEN 1 ELSE 0 END) as ints_caught,
                SUM(CASE WHEN defteam = :team AND fumble = true THEN 1 ELSE 0 END) as fumbles_recovered
            FROM plays 
            WHERE season = :season 
                AND (posteam = :team OR defteam = :team)
                AND (interception = true OR fumble = true)
        """)
        
        result = self.db.execute(query, {'season': season, 'team': team_abbr}).first()
        
        ints_thrown = result.ints_thrown or 0
        fumbles_lost = result.fumbles_lost or 0
        ints_caught = result.ints_caught or 0
        fumbles_recovered = result.fumbles_recovered or 0
        
        giveaways = ints_thrown + fumbles_lost
        takeaways = ints_caught + fumbles_recovered
        
        return TurnoverStats(
            giveaways=giveaways,
            takeaways=takeaways,
            differential=takeaways - giveaways,
            fumbles_lost=fumbles_lost,
            fumbles_recovered=fumbles_recovered,
            interceptions_thrown=ints_thrown,
            interceptions_caught=ints_caught
        )
    
    def _calculate_scoring_stats(self, season: int, team_abbr: str, games_played: int) -> Dict[str, float]:
        """Calculate points per game statistics."""
        query = text("""
            SELECT 
                AVG(CASE WHEN home_team = :team THEN home_score 
                         WHEN away_team = :team THEN away_score END) as ppg,
                AVG(CASE WHEN home_team = :team THEN away_score 
                         WHEN away_team = :team THEN home_score END) as papg
            FROM games 
            WHERE season = :season 
                AND (home_team = :team OR away_team = :team)
                AND home_score IS NOT NULL
        """)
        
        result = self.db.execute(query, {'season': season, 'team': team_abbr}).first()
        
        ppg = result.ppg or 0
        papg = result.papg or 0
        
        return {
            'ppg': round(ppg, 1),
            'papg': round(papg, 1),
            'diff': round(ppg - papg, 1)
        }
    
    def get_team_rankings(self, season: int) -> Dict[str, List[Dict[str, Any]]]:
        """Get team rankings across key metrics."""
        teams = self.calculate_team_analytics(season)
        
        # Create rankings for different categories
        rankings = {
            'offensive_efficiency': sorted(teams, key=lambda x: x.offensive_efficiency.avg_epa, reverse=True),
            'defensive_efficiency': sorted(teams, key=lambda x: x.defensive_efficiency.avg_epa_allowed),
            'red_zone_offense': sorted(teams, key=lambda x: x.red_zone_offense.td_percentage, reverse=True),
            'red_zone_defense': sorted(teams, key=lambda x: x.red_zone_defense.td_percentage),
            'third_down_offense': sorted(teams, key=lambda x: x.third_down_offense.conversion_rate, reverse=True),
            'third_down_defense': sorted(teams, key=lambda x: x.third_down_defense.conversion_rate),
            'turnover_differential': sorted(teams, key=lambda x: x.turnover_stats.differential, reverse=True),
            'point_differential': sorted(teams, key=lambda x: x.point_differential, reverse=True)
        }
        
        return rankings