"""Enhanced position-specific analytics for NFL players."""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, case, text
from dataclasses import dataclass
import logging

from ..models.play import PlayModel
from ..models.player import PlayerModel

logger = logging.getLogger(__name__)


@dataclass
class QuarterbackStats:
    """Comprehensive quarterback statistics."""
    player_name: str
    team: str
    attempts: int
    completions: int
    completion_pct: float
    passing_yards: int
    passing_tds: int
    interceptions: int
    passer_rating: float
    qbr: float
    yards_per_attempt: float
    yards_per_completion: float
    avg_epa: float
    success_rate: float  # % of plays with positive EPA
    deep_ball_pct: float  # % of passes 20+ yards
    red_zone_td_pct: float  # TD % in red zone


@dataclass
class RunningBackStats:
    """Comprehensive running back statistics."""
    player_name: str
    team: str
    carries: int
    rushing_yards: int
    rushing_tds: int
    yards_per_carry: float
    longest_run: int
    first_downs: int
    # Receiving stats for RBs
    targets: int
    receptions: int
    receiving_yards: int
    receiving_tds: int
    catch_rate: float
    avg_epa_rushing: float
    avg_epa_receiving: float
    total_touchdowns: int
    total_yards: int


@dataclass
class WideReceiverStats:
    """Comprehensive wide receiver statistics."""
    player_name: str
    team: str
    targets: int
    receptions: int
    receiving_yards: int
    receiving_tds: int
    catch_rate: float
    yards_per_catch: float
    yards_per_target: float
    yards_after_catch: float
    first_downs: int
    longest_reception: int
    deep_targets: int  # 20+ yard targets
    red_zone_targets: int
    avg_epa: float
    drop_rate: float


class PositionAnalytics:
    """Enhanced position-specific analytics calculator."""
    
    def __init__(self, db_session: Session):
        """Initialize with database session."""
        self.db_session = db_session
    
    def calculate_quarterback_stats(self, season: int, min_attempts: int = 150) -> List[QuarterbackStats]:
        """Calculate comprehensive quarterback statistics."""
        logger.info(f"Calculating QB stats for season {season}")
        
        # Main QB query with enhanced metrics
        qb_query = self.db_session.query(
            PlayModel.passer_player_id,
            PlayerModel.full_name,
            PlayerModel.team_abbr,
            func.count(PlayModel.id).label('attempts'),
            func.sum(case((PlayModel.yards_gained >= 0, PlayModel.yards_gained), else_=0)).label('total_yards'),
            func.sum(case((
                (PlayModel.play_type == 'pass') & 
                (PlayModel.interception.is_(False)) & 
                (PlayModel.yards_gained >= 0), 1
            ), else_=0)).label('completions'),
            func.sum(case((PlayModel.pass_touchdown.is_(True), 1), else_=0)).label('touchdowns'),
            func.sum(case((PlayModel.interception.is_(True), 1), else_=0)).label('interceptions'),
            func.avg(PlayModel.epa).label('avg_epa'),
            func.sum(case((PlayModel.epa > 0, 1), else_=0)).label('successful_plays'),
            func.sum(case((PlayModel.air_yards >= 20, 1), else_=0)).label('deep_attempts'),
            func.max(PlayModel.yards_gained).label('longest_pass')
        ).join(
            PlayerModel, PlayModel.passer_player_id == PlayerModel.player_id
        ).filter(
            PlayModel.play_type == 'pass',
            PlayModel.season == season,
            PlayModel.passer_player_id.isnot(None)
        ).group_by(
            PlayModel.passer_player_id,
            PlayerModel.full_name,
            PlayerModel.team_abbr
        ).having(func.count(PlayModel.id) >= min_attempts).all()
        
        # Calculate red zone stats separately
        red_zone_stats = {}
        for qb in qb_query:
            red_zone_query = self.db_session.query(
                func.count(PlayModel.id).label('rz_attempts'),
                func.sum(case((PlayModel.pass_touchdown.is_(True), 1), else_=0)).label('rz_tds')
            ).filter(
                PlayModel.play_type == 'pass',
                PlayModel.season == season,
                PlayModel.passer_player_id == qb.passer_player_id,
                PlayModel.yardline_100 <= 20
            ).first()
            
            red_zone_stats[qb.passer_player_id] = {
                'attempts': red_zone_query.rz_attempts or 0,
                'tds': red_zone_query.rz_tds or 0
            }
        
        qb_stats = []
        for stat in qb_query:
            attempts = stat.attempts or 1
            completions = stat.completions or 0
            yards = stat.total_yards or 0
            tds = stat.touchdowns or 0
            ints = stat.interceptions or 0
            successful_plays = stat.successful_plays or 0
            deep_attempts = stat.deep_attempts or 0
            
            # Calculate percentages
            comp_pct = (completions / attempts) * 100
            ypa = yards / attempts
            ypc = yards / completions if completions > 0 else 0
            td_pct = (tds / attempts) * 100
            int_pct = (ints / attempts) * 100
            success_rate = (successful_plays / attempts) * 100
            deep_ball_pct = (deep_attempts / attempts) * 100
            
            # NFL passer rating formula
            a = max(0, min(2.375, ((comp_pct - 30) * 0.05)))
            b = max(0, min(2.375, ((ypa - 3) * 0.25)))
            c = max(0, min(2.375, (td_pct * 0.2)))
            d = max(0, min(2.375, (2.375 - (int_pct * 0.25))))
            passer_rating = ((a + b + c + d) / 6) * 100
            
            # Simplified QBR (EPA-based approximation)
            qbr = min(100, max(0, 50 + (stat.avg_epa or 0) * 25))
            
            # Red zone TD percentage
            rz_data = red_zone_stats.get(stat.passer_player_id, {'attempts': 0, 'tds': 0})
            red_zone_td_pct = (rz_data['tds'] / rz_data['attempts'] * 100) if rz_data['attempts'] > 0 else 0
            
            qb_stats.append(QuarterbackStats(
                player_name=stat.full_name,
                team=stat.team_abbr,
                attempts=attempts,
                completions=completions,
                completion_pct=round(comp_pct, 1),
                passing_yards=int(yards),
                passing_tds=tds,
                interceptions=ints,
                passer_rating=round(passer_rating, 1),
                qbr=round(qbr, 1),
                yards_per_attempt=round(ypa, 1),
                yards_per_completion=round(ypc, 1),
                avg_epa=round(stat.avg_epa or 0, 3),
                success_rate=round(success_rate, 1),
                deep_ball_pct=round(deep_ball_pct, 1),
                red_zone_td_pct=round(red_zone_td_pct, 1)
            ))
        
        # Sort by passer rating
        return sorted(qb_stats, key=lambda x: x.passer_rating, reverse=True)
    
    def calculate_running_back_stats(self, season: int, min_carries: int = 75) -> List[RunningBackStats]:
        """Calculate comprehensive running back statistics."""
        logger.info(f"Calculating RB stats for season {season}")
        
        # Rushing stats
        rushing_query = self.db_session.query(
            PlayModel.rusher_player_id,
            PlayerModel.full_name,
            PlayerModel.team_abbr,
            func.count(PlayModel.id).label('carries'),
            func.sum(PlayModel.yards_gained).label('total_yards'),
            func.avg(PlayModel.yards_gained).label('avg_per_carry'),
            func.sum(case((PlayModel.rush_touchdown.is_(True), 1), else_=0)).label('touchdowns'),
            func.max(PlayModel.yards_gained).label('longest'),
            func.sum(case((PlayModel.first_down.is_(True), 1), else_=0)).label('first_downs'),
            func.avg(PlayModel.epa).label('avg_epa')
        ).join(
            PlayerModel, PlayModel.rusher_player_id == PlayerModel.player_id
        ).filter(
            PlayModel.play_type == 'run',
            PlayModel.season == season,
            PlayModel.rusher_player_id.isnot(None)
        ).group_by(
            PlayModel.rusher_player_id,
            PlayerModel.full_name,
            PlayerModel.team_abbr
        ).having(func.count(PlayModel.id) >= min_carries).all()
        
        rb_stats = []
        
        for stat in rushing_query:
            # Get receiving stats for this RB
            receiving_query = self.db_session.query(
                func.count(case((PlayModel.receiver_player_id == stat.rusher_player_id, 1))).label('targets'),
                func.count(case((
                    (PlayModel.receiver_player_id == stat.rusher_player_id) &
                    (PlayModel.yards_gained >= 0) &
                    (PlayModel.interception.is_(False)), 1
                ))).label('receptions'),
                func.sum(case((
                    (PlayModel.receiver_player_id == stat.rusher_player_id) &
                    (PlayModel.yards_gained >= 0) &
                    (PlayModel.interception.is_(False)), PlayModel.yards_gained
                ), else_=0)).label('receiving_yards'),
                func.sum(case((
                    (PlayModel.receiver_player_id == stat.rusher_player_id) &
                    (PlayModel.pass_touchdown.is_(True)), 1
                ), else_=0)).label('receiving_tds'),
                func.avg(case((
                    PlayModel.receiver_player_id == stat.rusher_player_id, PlayModel.epa
                ))).label('receiving_epa')
            ).filter(
                PlayModel.play_type == 'pass',
                PlayModel.season == season
            ).first()
            
            targets = receiving_query.targets or 0
            receptions = receiving_query.receptions or 0
            receiving_yards = receiving_query.receiving_yards or 0
            receiving_tds = receiving_query.receiving_tds or 0
            
            catch_rate = (receptions / targets * 100) if targets > 0 else 0
            
            rb_stats.append(RunningBackStats(
                player_name=stat.full_name,
                team=stat.team_abbr,
                carries=stat.carries or 0,
                rushing_yards=int(stat.total_yards or 0),
                rushing_tds=stat.touchdowns or 0,
                yards_per_carry=round(stat.avg_per_carry or 0, 1),
                longest_run=stat.longest or 0,
                first_downs=stat.first_downs or 0,
                targets=targets,
                receptions=receptions,
                receiving_yards=int(receiving_yards),
                receiving_tds=receiving_tds,
                catch_rate=round(catch_rate, 1),
                avg_epa_rushing=round(stat.avg_epa or 0, 3),
                avg_epa_receiving=round(receiving_query.receiving_epa or 0, 3),
                total_touchdowns=(stat.touchdowns or 0) + receiving_tds,
                total_yards=int((stat.total_yards or 0) + receiving_yards)
            ))
        
        # Sort by total yards
        return sorted(rb_stats, key=lambda x: x.total_yards, reverse=True)
    
    def calculate_wide_receiver_stats(self, season: int, min_targets: int = 30) -> List[WideReceiverStats]:
        """Calculate comprehensive wide receiver statistics."""
        logger.info(f"Calculating WR stats for season {season}")
        
        # WR receiving stats with targets calculation
        wr_query = self.db_session.query(
            PlayModel.receiver_player_id,
            PlayerModel.full_name,
            PlayerModel.team_abbr,
            # Targets = all pass plays where this player was the intended receiver
            func.count(PlayModel.id).label('targets'),
            # Receptions = completed passes to this player
            func.sum(case((
                (PlayModel.interception.is_(False)) & 
                (PlayModel.yards_gained >= 0), 1
            ), else_=0)).label('receptions'),
            func.sum(case((
                (PlayModel.interception.is_(False)) & 
                (PlayModel.yards_gained >= 0), PlayModel.yards_gained
            ), else_=0)).label('total_yards'),
            func.sum(case((PlayModel.pass_touchdown.is_(True), 1), else_=0)).label('touchdowns'),
            func.sum(case((PlayModel.first_down.is_(True), 1), else_=0)).label('first_downs'),
            func.max(case((
                (PlayModel.interception.is_(False)) & 
                (PlayModel.yards_gained >= 0), PlayModel.yards_gained
            ))).label('longest'),
            func.sum(case((PlayModel.air_yards >= 20, 1), else_=0)).label('deep_targets'),
            func.avg(PlayModel.epa).label('avg_epa'),
            func.avg(PlayModel.yards_after_catch).label('avg_yac')
        ).join(
            PlayerModel, PlayModel.receiver_player_id == PlayerModel.player_id
        ).filter(
            PlayModel.play_type == 'pass',
            PlayModel.season == season,
            PlayModel.receiver_player_id.isnot(None)
        ).group_by(
            PlayModel.receiver_player_id,
            PlayerModel.full_name,
            PlayerModel.team_abbr
        ).having(func.count(PlayModel.id) >= min_targets).all()
        
        wr_stats = []
        
        for stat in wr_query:
            targets = stat.targets or 1
            receptions = stat.receptions or 0
            yards = stat.total_yards or 0
            tds = stat.touchdowns or 0
            
            # Calculate advanced metrics
            catch_rate = (receptions / targets * 100)
            yards_per_catch = yards / receptions if receptions > 0 else 0
            yards_per_target = yards / targets
            
            # Red zone targets
            red_zone_targets = self.db_session.query(
                func.count(PlayModel.id)
            ).filter(
                PlayModel.play_type == 'pass',
                PlayModel.season == season,
                PlayModel.receiver_player_id == stat.receiver_player_id,
                PlayModel.yardline_100 <= 20
            ).scalar() or 0
            
            # Estimate drop rate (incomplete passes that weren't INTs or throwaways)
            incomplete_passes = targets - receptions
            # Simple approximation: assume 70% of incomplete passes are drops
            estimated_drops = int(incomplete_passes * 0.3)  # Conservative estimate
            drop_rate = (estimated_drops / targets * 100) if targets > 0 else 0
            
            wr_stats.append(WideReceiverStats(
                player_name=stat.full_name,
                team=stat.team_abbr,
                targets=targets,
                receptions=receptions,
                receiving_yards=int(yards),
                receiving_tds=tds,
                catch_rate=round(catch_rate, 1),
                yards_per_catch=round(yards_per_catch, 1),
                yards_per_target=round(yards_per_target, 1),
                yards_after_catch=round(stat.avg_yac or 0, 1),
                first_downs=stat.first_downs or 0,
                longest_reception=stat.longest or 0,
                deep_targets=stat.deep_targets or 0,
                red_zone_targets=red_zone_targets,
                avg_epa=round(stat.avg_epa or 0, 3),
                drop_rate=round(drop_rate, 1)
            ))
        
        # Sort by receiving yards
        return sorted(wr_stats, key=lambda x: x.receiving_yards, reverse=True)
    
    def get_position_leaders(self, season: int, position: str = 'all') -> Dict[str, List[Any]]:
        """Get comprehensive position leaders for a season."""
        leaders = {}
        
        if position in ['all', 'qb', 'quarterback']:
            leaders['quarterbacks'] = [qb.__dict__ for qb in self.calculate_quarterback_stats(season)]
        
        if position in ['all', 'rb', 'running_back']:
            leaders['running_backs'] = [rb.__dict__ for rb in self.calculate_running_back_stats(season)]
        
        if position in ['all', 'wr', 'wide_receiver', 'receiver']:
            leaders['receivers'] = [wr.__dict__ for wr in self.calculate_wide_receiver_stats(season)]
        
        return leaders