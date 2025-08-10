"""Play service for business logic."""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_, or_, desc

from .base import BaseService, DatabaseError, NotFoundError
from ..models.play import PlayModel, PlayCreate, PlayUpdate


class PlayService(BaseService[PlayModel, PlayCreate, PlayUpdate]):
    """Service class for play operations."""
    
    def __init__(self, db_session: Session):
        """Initialize play service."""
        super().__init__(db_session, PlayModel)
    
    def get_plays_by_game(self, game_id: str, limit: int = 1000, offset: int = 0) -> List[PlayModel]:
        """Get plays for a specific game.
        
        Args:
            game_id: Game identifier
            limit: Maximum number of plays to return
            offset: Number of plays to skip
            
        Returns:
            List of plays in the game
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayModel).filter(
                PlayModel.game_id == game_id
            ).order_by(PlayModel.play_id)
            
            return query.offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_plays_by_game: {e}")
            raise DatabaseError(f"Failed to get plays for game {game_id}") from e
    
    def get_plays_by_team(self, team_abbr: str, season: Optional[int] = None,
                         play_type: Optional[str] = None, limit: int = 1000,
                         offset: int = 0) -> List[PlayModel]:
        """Get plays for a specific team.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year (all seasons if None)
            play_type: Type of play ('pass', 'run', etc.)
            limit: Maximum number of plays to return
            offset: Number of plays to skip
            
        Returns:
            List of team's plays
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            team_abbr = team_abbr.upper()
            query = self.db.query(PlayModel).filter(
                or_(
                    PlayModel.posteam == team_abbr,
                    PlayModel.defteam == team_abbr
                )
            )
            
            if season:
                query = query.filter(PlayModel.season == season)
            
            if play_type:
                query = query.filter(PlayModel.play_type == play_type)
            
            query = query.order_by(desc(PlayModel.game_date))
            
            return query.offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_plays_by_team: {e}")
            raise DatabaseError(f"Failed to get plays for team {team_abbr}") from e
    
    def get_plays_by_player(self, player_id: str, season: Optional[int] = None,
                           play_type: Optional[str] = None, limit: int = 1000,
                           offset: int = 0) -> List[PlayModel]:
        """Get plays involving a specific player.
        
        Args:
            player_id: Player identifier
            season: Season year (all seasons if None)
            play_type: Type of play ('pass', 'run', etc.)
            limit: Maximum number of plays to return
            offset: Number of plays to skip
            
        Returns:
            List of player's plays
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayModel).filter(
                or_(
                    PlayModel.passer_player_id == player_id,
                    PlayModel.rusher_player_id == player_id,
                    PlayModel.receiver_player_id == player_id
                )
            )
            
            if season:
                query = query.filter(PlayModel.season == season)
            
            if play_type:
                query = query.filter(PlayModel.play_type == play_type)
            
            query = query.order_by(desc(PlayModel.game_date))
            
            return query.offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_plays_by_player: {e}")
            raise DatabaseError(f"Failed to get plays for player {player_id}") from e
    
    def get_explosive_plays(self, season: Optional[int] = None, team_abbr: Optional[str] = None,
                           rushing_threshold: int = 20, passing_threshold: int = 25,
                           limit: int = 100) -> List[PlayModel]:
        """Get explosive plays (long runs/passes).
        
        Args:
            season: Season year (all seasons if None)
            team_abbr: Team abbreviation (all teams if None)
            rushing_threshold: Minimum rushing yards for explosive run
            passing_threshold: Minimum passing yards for explosive pass
            limit: Maximum number of plays to return
            
        Returns:
            List of explosive plays
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayModel).filter(
                or_(
                    and_(
                        PlayModel.play_type == 'run',
                        PlayModel.rushing_yards >= rushing_threshold
                    ),
                    and_(
                        PlayModel.play_type == 'pass',
                        PlayModel.passing_yards >= passing_threshold
                    )
                )
            )
            
            if season:
                query = query.filter(PlayModel.season == season)
            
            if team_abbr:
                query = query.filter(PlayModel.posteam == team_abbr.upper())
            
            query = query.order_by(desc(PlayModel.passing_yards + PlayModel.rushing_yards))
            
            return query.limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_explosive_plays: {e}")
            raise DatabaseError("Failed to get explosive plays") from e
    
    def get_red_zone_plays(self, season: Optional[int] = None, 
                          team_abbr: Optional[str] = None,
                          limit: int = 1000) -> List[PlayModel]:
        """Get red zone plays (within 20 yards of goal line).
        
        Args:
            season: Season year (all seasons if None)
            team_abbr: Team abbreviation (all teams if None)
            limit: Maximum number of plays to return
            
        Returns:
            List of red zone plays
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayModel).filter(
                and_(
                    PlayModel.yardline_100 <= 20,
                    PlayModel.yardline_100 > 0
                )
            )
            
            if season:
                query = query.filter(PlayModel.season == season)
            
            if team_abbr:
                query = query.filter(PlayModel.posteam == team_abbr.upper())
            
            query = query.order_by(desc(PlayModel.game_date))
            
            return query.limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_red_zone_plays: {e}")
            raise DatabaseError("Failed to get red zone plays") from e
    
    def get_scoring_plays(self, season: Optional[int] = None,
                         team_abbr: Optional[str] = None,
                         limit: int = 1000) -> List[PlayModel]:
        """Get scoring plays (touchdowns and field goals).
        
        Args:
            season: Season year (all seasons if None)
            team_abbr: Team abbreviation (all teams if None)
            limit: Maximum number of plays to return
            
        Returns:
            List of scoring plays
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayModel).filter(
                or_(
                    PlayModel.touchdown == 1,
                    PlayModel.field_goal_result == 'made'
                )
            )
            
            if season:
                query = query.filter(PlayModel.season == season)
            
            if team_abbr:
                query = query.filter(PlayModel.posteam == team_abbr.upper())
            
            query = query.order_by(desc(PlayModel.game_date))
            
            return query.limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_scoring_plays: {e}")
            raise DatabaseError("Failed to get scoring plays") from e
    
    def get_turnover_plays(self, season: Optional[int] = None,
                          team_abbr: Optional[str] = None,
                          limit: int = 1000) -> List[PlayModel]:
        """Get turnover plays (interceptions and fumbles).
        
        Args:
            season: Season year (all seasons if None)
            team_abbr: Team abbreviation (all teams if None)
            limit: Maximum number of plays to return
            
        Returns:
            List of turnover plays
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayModel).filter(
                or_(
                    PlayModel.interception == 1,
                    PlayModel.fumble_lost == 1
                )
            )
            
            if season:
                query = query.filter(PlayModel.season == season)
            
            if team_abbr:
                query = query.filter(
                    or_(
                        PlayModel.posteam == team_abbr.upper(),
                        PlayModel.defteam == team_abbr.upper()
                    )
                )
            
            query = query.order_by(desc(PlayModel.game_date))
            
            return query.limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_turnover_plays: {e}")
            raise DatabaseError("Failed to get turnover plays") from e
    
    def get_play_summary_stats(self, season: Optional[int] = None,
                              team_abbr: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for plays.
        
        Args:
            season: Season year (all seasons if None)
            team_abbr: Team abbreviation (all teams if None)
            
        Returns:
            Dictionary with play summary statistics
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayModel)
            
            if season:
                query = query.filter(PlayModel.season == season)
            
            if team_abbr:
                query = query.filter(PlayModel.posteam == team_abbr.upper())
            
            plays = query.all()
            
            # Calculate summary statistics
            total_plays = len(plays)
            passing_plays = [p for p in plays if p.play_type == 'pass']
            rushing_plays = [p for p in plays if p.play_type == 'run']
            
            stats = {
                "total_plays": total_plays,
                "passing_plays": len(passing_plays),
                "rushing_plays": len(rushing_plays),
                "other_plays": total_plays - len(passing_plays) - len(rushing_plays),
                "total_yards": sum((p.passing_yards or 0) + (p.rushing_yards or 0) for p in plays),
                "passing_yards": sum(p.passing_yards or 0 for p in passing_plays),
                "rushing_yards": sum(p.rushing_yards or 0 for p in rushing_plays),
                "touchdowns": sum(p.touchdown or 0 for p in plays),
                "turnovers": sum((p.interception or 0) + (p.fumble_lost or 0) for p in plays),
                "explosive_plays": len([p for p in plays if 
                                      (p.play_type == 'run' and (p.rushing_yards or 0) >= 20) or
                                      (p.play_type == 'pass' and (p.passing_yards or 0) >= 25)])
            }
            
            # Calculate averages
            if total_plays > 0:
                stats["yards_per_play"] = stats["total_yards"] / total_plays
            else:
                stats["yards_per_play"] = 0
                
            if len(passing_plays) > 0:
                stats["yards_per_pass"] = stats["passing_yards"] / len(passing_plays)
                stats["completion_percentage"] = sum(p.complete_pass or 0 for p in passing_plays) / len(passing_plays) * 100
            else:
                stats["yards_per_pass"] = 0
                stats["completion_percentage"] = 0
                
            if len(rushing_plays) > 0:
                stats["yards_per_rush"] = stats["rushing_yards"] / len(rushing_plays)
            else:
                stats["yards_per_rush"] = 0
            
            return stats
            
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_play_summary_stats: {e}")
            raise DatabaseError("Failed to get play summary statistics") from e
    
    def get_situational_plays(self, down: Optional[int] = None,
                             distance: Optional[int] = None,
                             field_position: Optional[str] = None,
                             season: Optional[int] = None,
                             team_abbr: Optional[str] = None,
                             limit: int = 1000) -> List[PlayModel]:
        """Get plays by situational criteria.
        
        Args:
            down: Down number (1-4)
            distance: Yards to go for first down
            field_position: Field position zone ('red_zone', 'goal_line', etc.)
            season: Season year (all seasons if None)
            team_abbr: Team abbreviation (all teams if None)
            limit: Maximum number of plays to return
            
        Returns:
            List of plays matching criteria
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayModel)
            
            if down:
                query = query.filter(PlayModel.down == down)
            
            if distance:
                query = query.filter(PlayModel.ydstogo == distance)
            
            if field_position == 'red_zone':
                query = query.filter(PlayModel.yardline_100 <= 20)
            elif field_position == 'goal_line':
                query = query.filter(PlayModel.yardline_100 <= 5)
            
            if season:
                query = query.filter(PlayModel.season == season)
            
            if team_abbr:
                query = query.filter(PlayModel.posteam == team_abbr.upper())
            
            query = query.order_by(desc(PlayModel.game_date))
            
            return query.limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_situational_plays: {e}")
            raise DatabaseError("Failed to get situational plays") from e