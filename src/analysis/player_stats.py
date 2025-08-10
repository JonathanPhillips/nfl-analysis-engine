"""
Player statistics calculator for league leaders and rankings.

This module calculates comprehensive player statistics from play-by-play data
for quarterbacks, running backs, wide receivers, and defensive players.
"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_, text
from datetime import date, datetime
import pandas as pd

from ..models.play import PlayModel
from ..models.player import PlayerModel
from ..models.game import GameModel


class PlayerStatsCalculator:
    """Calculate player statistics from play-by-play data."""
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        
    def get_qb_stats(self, season: int = 2024, min_attempts: int = 50) -> List[Dict]:
        """
        Get quarterback statistics with passer rating calculation.
        
        Args:
            season: NFL season year
            min_attempts: Minimum pass attempts to qualify
            
        Returns:
            List of QB stats dictionaries sorted by passer rating
        """
        # Query to aggregate QB stats from plays
        qb_stats_query = self.db.query(
            PlayModel.passer_player_id.label('player_id'),
            func.count(PlayModel.id).label('attempts'),
            func.sum(case((PlayModel.desc.like('%COMPLETE%'), 1), else_=0)).label('completions'),
            func.sum(PlayModel.yards_gained).label('passing_yards'),
            func.sum(case((PlayModel.pass_touchdown == True, 1), else_=0)).label('passing_tds'),
            func.sum(case((PlayModel.interception == True, 1), else_=0)).label('interceptions'),
            func.avg(PlayModel.epa).label('avg_epa'),
            func.avg(PlayModel.yards_gained).label('yards_per_attempt')
        ).filter(
            PlayModel.play_type == 'pass',
            PlayModel.season == season,
            PlayModel.passer_player_id.isnot(None)
        ).group_by(
            PlayModel.passer_player_id
        ).having(
            func.count(PlayModel.id) >= min_attempts
        ).all()
        
        # Calculate passer rating and format results
        qb_results = []
        for stat in qb_stats_query:
            # Get player info
            player = self.db.query(PlayerModel).filter(
                PlayerModel.player_id == stat.player_id
            ).first()
            
            if not player:
                continue
                
            # Calculate passer rating components
            attempts = stat.attempts or 1  # Avoid division by zero
            completions = stat.completions or 0
            yards = stat.passing_yards or 0
            tds = stat.passing_tds or 0
            ints = stat.interceptions or 0
            
            # NFL passer rating formula
            comp_pct = (completions / attempts) * 100 if attempts > 0 else 0
            
            # Calculate the four components
            a = max(0, min(2.375, ((comp_pct / 100 - 0.3) * 5)))
            b = max(0, min(2.375, ((yards / attempts - 3) * 0.25))) if attempts > 0 else 0
            c = max(0, min(2.375, ((tds / attempts) * 20))) if attempts > 0 else 0
            d = max(0, min(2.375, (2.375 - ((ints / attempts) * 25)))) if attempts > 0 else 0
            
            passer_rating = ((a + b + c + d) / 6) * 100
            
            qb_results.append({
                'player_id': stat.player_id,
                'player_name': player.full_name,
                'team': player.team_abbr,
                'position': 'QB',
                'attempts': attempts,
                'completions': completions,
                'completion_pct': round(comp_pct, 1),
                'passing_yards': yards,
                'passing_tds': tds,
                'interceptions': ints,
                'passer_rating': round(passer_rating, 1),
                'avg_epa': round(stat.avg_epa, 3) if stat.avg_epa else 0,
                'yards_per_attempt': round(stat.yards_per_attempt, 1) if stat.yards_per_attempt else 0
            })
        
        # Sort by passer rating
        return sorted(qb_results, key=lambda x: x['passer_rating'], reverse=True)
    
    def get_rb_stats(self, season: int = 2024, min_carries: int = 25) -> List[Dict]:
        """
        Get running back statistics.
        
        Args:
            season: NFL season year
            min_carries: Minimum carries to qualify
            
        Returns:
            List of RB stats dictionaries sorted by rushing yards
        """
        # Query to aggregate RB stats from plays
        rb_stats_query = self.db.query(
            PlayModel.rusher_player_id.label('player_id'),
            func.count(PlayModel.id).label('carries'),
            func.sum(PlayModel.yards_gained).label('rushing_yards'),
            func.sum(case((PlayModel.rush_touchdown == True, 1), else_=0)).label('rushing_tds'),
            func.avg(PlayModel.yards_gained).label('yards_per_carry'),
            func.avg(PlayModel.epa).label('avg_epa'),
            func.max(PlayModel.yards_gained).label('longest_run'),
            func.sum(case((PlayModel.yards_gained >= 10, 1), else_=0)).label('runs_10plus'),
            func.sum(case((PlayModel.yards_gained >= 20, 1), else_=0)).label('runs_20plus')
        ).filter(
            PlayModel.play_type == 'run',
            PlayModel.season == season,
            PlayModel.rusher_player_id.isnot(None)
        ).group_by(
            PlayModel.rusher_player_id
        ).having(
            func.count(PlayModel.id) >= min_carries
        ).all()
        
        # Format results
        rb_results = []
        for stat in rb_stats_query:
            # Get player info
            player = self.db.query(PlayerModel).filter(
                PlayerModel.player_id == stat.player_id
            ).first()
            
            if not player:
                continue
            
            rb_results.append({
                'player_id': stat.player_id,
                'player_name': player.full_name,
                'team': player.team_abbr,
                'position': 'RB',
                'carries': stat.carries or 0,
                'rushing_yards': stat.rushing_yards or 0,
                'rushing_tds': stat.rushing_tds or 0,
                'yards_per_carry': round(stat.yards_per_carry, 1) if stat.yards_per_carry else 0,
                'longest_run': stat.longest_run or 0,
                'runs_10plus': stat.runs_10plus or 0,
                'runs_20plus': stat.runs_20plus or 0,
                'avg_epa': round(stat.avg_epa, 3) if stat.avg_epa else 0
            })
        
        # Sort by rushing yards
        return sorted(rb_results, key=lambda x: x['rushing_yards'], reverse=True)
    
    def get_wr_stats(self, season: int = 2024, min_targets: int = 20) -> List[Dict]:
        """
        Get wide receiver statistics.
        
        Args:
            season: NFL season year
            min_targets: Minimum targets to qualify
            
        Returns:
            List of WR stats dictionaries sorted by receiving yards
        """
        # Query to aggregate WR stats from plays
        wr_stats_query = self.db.query(
            PlayModel.receiver_player_id.label('player_id'),
            func.count(PlayModel.id).label('targets'),
            func.sum(case((PlayModel.desc.like('%COMPLETE%'), 1), else_=0)).label('receptions'),
            func.sum(PlayModel.yards_gained).label('receiving_yards'),
            func.sum(case((PlayModel.pass_touchdown == True, 1), else_=0)).label('receiving_tds'),
            func.avg(PlayModel.yards_gained).label('yards_per_reception'),
            func.avg(PlayModel.epa).label('avg_epa'),
            func.avg(PlayModel.air_yards).label('avg_air_yards'),
            func.avg(PlayModel.yards_after_catch).label('avg_yac')
        ).filter(
            PlayModel.play_type == 'pass',
            PlayModel.season == season,
            PlayModel.receiver_player_id.isnot(None)
        ).group_by(
            PlayModel.receiver_player_id
        ).having(
            func.count(PlayModel.id) >= min_targets
        ).all()
        
        # Format results
        wr_results = []
        for stat in wr_stats_query:
            # Get player info
            player = self.db.query(PlayerModel).filter(
                PlayerModel.player_id == stat.player_id
            ).first()
            
            if not player:
                continue
                
            targets = stat.targets or 1
            receptions = stat.receptions or 0
            catch_rate = (receptions / targets * 100) if targets > 0 else 0
            
            wr_results.append({
                'player_id': stat.player_id,
                'player_name': player.full_name,
                'team': player.team_abbr,
                'position': player.position or 'WR',
                'targets': targets,
                'receptions': receptions,
                'catch_rate': round(catch_rate, 1),
                'receiving_yards': stat.receiving_yards or 0,
                'receiving_tds': stat.receiving_tds or 0,
                'yards_per_reception': round(stat.yards_per_reception, 1) if stat.yards_per_reception else 0,
                'avg_air_yards': round(stat.avg_air_yards, 1) if stat.avg_air_yards else 0,
                'avg_yac': round(stat.avg_yac, 1) if stat.avg_yac else 0,
                'avg_epa': round(stat.avg_epa, 3) if stat.avg_epa else 0
            })
        
        # Sort by receiving yards
        return sorted(wr_results, key=lambda x: x['receiving_yards'], reverse=True)
    
    def get_team_offense_stats(self, season: int = 2024) -> List[Dict]:
        """
        Get team offensive statistics.
        
        Args:
            season: NFL season year
            
        Returns:
            List of team offensive stats sorted by total EPA
        """
        # Query to aggregate team offensive stats
        team_stats_query = self.db.query(
            PlayModel.posteam.label('team'),
            func.count(PlayModel.id).label('total_plays'),
            func.sum(PlayModel.yards_gained).label('total_yards'),
            func.avg(PlayModel.yards_gained).label('yards_per_play'),
            func.sum(case((PlayModel.touchdown == True, 1), else_=0)).label('total_tds'),
            func.sum(PlayModel.epa).label('total_epa'),
            func.avg(PlayModel.epa).label('avg_epa'),
            func.sum(case((PlayModel.play_type == 'pass', 1), else_=0)).label('pass_plays'),
            func.sum(case((PlayModel.play_type == 'run', 1), else_=0)).label('run_plays'),
            func.sum(case((or_(PlayModel.interception == True, PlayModel.fumble == True), 1), else_=0)).label('turnovers')
        ).filter(
            PlayModel.season == season,
            PlayModel.posteam.isnot(None),
            PlayModel.play_type.in_(['pass', 'run'])
        ).group_by(
            PlayModel.posteam
        ).all()
        
        # Format results
        team_results = []
        for stat in team_stats_query:
            total_plays = stat.total_plays or 1
            pass_plays = stat.pass_plays or 0
            run_plays = stat.run_plays or 0
            
            team_results.append({
                'team': stat.team,
                'total_plays': total_plays,
                'total_yards': stat.total_yards or 0,
                'yards_per_play': round(stat.yards_per_play, 1) if stat.yards_per_play else 0,
                'total_tds': stat.total_tds or 0,
                'total_epa': round(stat.total_epa, 1) if stat.total_epa else 0,
                'avg_epa': round(stat.avg_epa, 3) if stat.avg_epa else 0,
                'pass_plays': pass_plays,
                'run_plays': run_plays,
                'pass_rate': round((pass_plays / total_plays) * 100, 1) if total_plays > 0 else 0,
                'turnovers': stat.turnovers or 0
            })
        
        # Sort by total EPA
        return sorted(team_results, key=lambda x: x['total_epa'], reverse=True)
    
    def get_all_leaders(self, season: int = 2024) -> Dict:
        """
        Get all league leaders in one call.
        
        Args:
            season: NFL season year
            
        Returns:
            Dictionary with all leader categories
        """
        return {
            'quarterbacks': self.get_qb_stats(season)[:10],  # Top 10
            'running_backs': self.get_rb_stats(season)[:10],
            'receivers': self.get_wr_stats(season)[:10],
            'team_offense': self.get_team_offense_stats(season),
            'season': season,
            'last_updated': datetime.now().isoformat()
        }


def calculate_turnover_differential(db: Session, team_abbr: str, season: int) -> int:
    """Calculate turnover differential for a team."""
    # This would need to track both offensive and defensive turnovers
    # Simplified for now
    return 0


def calculate_red_zone_efficiency(db: Session, team_abbr: str, season: int) -> float:
    """Calculate red zone touchdown percentage."""
    red_zone_plays = db.query(PlayModel).filter(
        PlayModel.posteam == team_abbr,
        PlayModel.season == season,
        PlayModel.yardline_100 <= 20  # In red zone
    ).all()
    
    if not red_zone_plays:
        return 0.0
        
    red_zone_tds = sum(1 for play in red_zone_plays if play.touchdown)
    # Approximate drives by unique game_id + quarter combinations
    red_zone_drives = len(set(f"{play.game_id}_{play.qtr}" for play in red_zone_plays))
    
    return (red_zone_tds / red_zone_drives * 100) if red_zone_drives > 0 else 0.0