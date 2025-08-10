"""Player service for business logic."""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_, or_, desc

from .base import BaseService, DatabaseError, NotFoundError
from ..models.player import PlayerModel, PlayerCreate, PlayerUpdate
from ..models.play import PlayModel


class PlayerService(BaseService[PlayerModel, PlayerCreate, PlayerUpdate]):
    """Service class for player operations."""
    
    def __init__(self, db_session: Session):
        """Initialize player service."""
        super().__init__(db_session, PlayerModel)
    
    def get_by_player_id(self, player_id: str) -> Optional[PlayerModel]:
        """Get player by player ID.
        
        Args:
            player_id: Unique player identifier
            
        Returns:
            Player if found, None otherwise
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            return self.db.query(PlayerModel).filter(PlayerModel.player_id == player_id).first()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_by_player_id: {e}")
            raise DatabaseError(f"Failed to get player by ID {player_id}") from e
    
    def get_by_player_id_or_404(self, player_id: str) -> PlayerModel:
        """Get player by player ID or raise NotFoundError.
        
        Args:
            player_id: Unique player identifier
            
        Returns:
            Player if found
            
        Raises:
            NotFoundError: If player not found
        """
        player = self.get_by_player_id(player_id)
        if player is None:
            raise NotFoundError(f"Player {player_id} not found")
        return player
    
    def get_by_team(self, team_abbr: str, season: Optional[int] = None) -> List[PlayerModel]:
        """Get players by team.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year (current roster if None)
            
        Returns:
            List of players on the team
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayerModel).filter(
                PlayerModel.team_abbr == team_abbr.upper()
            )
            
            # Filter by season if provided
            if season:
                query = query.filter(PlayerModel.season == season)
            
            return query.order_by(PlayerModel.player_name).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_by_team: {e}")
            raise DatabaseError(f"Failed to get players for team {team_abbr}") from e
    
    def get_by_position(self, position: str, team_abbr: Optional[str] = None,
                       season: Optional[int] = None) -> List[PlayerModel]:
        """Get players by position.
        
        Args:
            position: Player position (e.g., 'QB', 'RB', 'WR')
            team_abbr: Team abbreviation (all teams if None)
            season: Season year (current season if None)
            
        Returns:
            List of players at the position
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(PlayerModel).filter(
                PlayerModel.position == position.upper()
            )
            
            if team_abbr:
                query = query.filter(PlayerModel.team_abbr == team_abbr.upper())
            
            if season:
                query = query.filter(PlayerModel.season == season)
            
            return query.order_by(PlayerModel.player_name).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_by_position: {e}")
            raise DatabaseError(f"Failed to get players by position {position}") from e
    
    def search_players(self, query: str, position: Optional[str] = None,
                      team_abbr: Optional[str] = None) -> List[PlayerModel]:
        """Search players by name.
        
        Args:
            query: Search query for player name
            position: Filter by position
            team_abbr: Filter by team
            
        Returns:
            List of matching players
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            search_term = f"%{query}%"
            db_query = self.db.query(PlayerModel).filter(
                PlayerModel.player_name.ilike(search_term)
            )
            
            if position:
                db_query = db_query.filter(PlayerModel.position == position.upper())
            
            if team_abbr:
                db_query = db_query.filter(PlayerModel.team_abbr == team_abbr.upper())
            
            return db_query.order_by(PlayerModel.player_name).limit(50).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in search_players: {e}")
            raise DatabaseError(f"Failed to search players with query '{query}'") from e
    
    def get_player_stats(self, player_id: str, season: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive player statistics.
        
        Args:
            player_id: Unique player identifier
            season: Season year (all seasons if None)
            
        Returns:
            Dictionary with player statistics
            
        Raises:
            NotFoundError: If player not found
            DatabaseError: If database error occurs
        """
        try:
            player = self.get_by_player_id_or_404(player_id)
            
            # Base query for player's plays
            plays_query = self.db.query(PlayModel)
            
            if season:
                plays_query = plays_query.filter(PlayModel.season == season)
            
            # Position-specific statistics
            stats = {
                "player": player,
                "season": season,
                "position": player.position,
                "team": player.team_abbr,
                "games_played": 0,
                "total_plays": 0
            }
            
            if player.position == 'QB':
                stats.update(self._get_qb_stats(player_id, plays_query))
            elif player.position in ['RB', 'FB']:
                stats.update(self._get_rb_stats(player_id, plays_query))
            elif player.position in ['WR', 'TE']:
                stats.update(self._get_receiver_stats(player_id, plays_query))
            elif player.position in ['K']:
                stats.update(self._get_kicker_stats(player_id, plays_query))
            else:
                # Generic stats for other positions
                stats.update(self._get_generic_stats(player_id, plays_query))
            
            return stats
            
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_player_stats: {e}")
            raise DatabaseError(f"Failed to get stats for player {player_id}") from e
    
    def _get_qb_stats(self, player_id: str, plays_query) -> Dict[str, Any]:
        """Get quarterback-specific statistics."""
        passing_plays = plays_query.filter(
            and_(
                PlayModel.passer_player_id == player_id,
                PlayModel.play_type == 'pass'
            )
        ).all()
        
        rushing_plays = plays_query.filter(
            and_(
                PlayModel.rusher_player_id == player_id,
                PlayModel.play_type == 'run'
            )
        ).all()
        
        # Passing stats
        attempts = len(passing_plays)
        completions = sum(1 for p in passing_plays if p.complete_pass == 1)
        passing_yards = sum(p.passing_yards or 0 for p in passing_plays)
        passing_tds = sum(p.pass_touchdown or 0 for p in passing_plays)
        interceptions = sum(p.interception or 0 for p in passing_plays)
        
        # Rushing stats
        rushing_attempts = len(rushing_plays)
        rushing_yards = sum(p.rushing_yards or 0 for p in rushing_plays)
        rushing_tds = sum(p.rush_touchdown or 0 for p in rushing_plays)
        
        # Calculate derived stats
        completion_percentage = (completions / attempts * 100) if attempts > 0 else 0
        yards_per_attempt = (passing_yards / attempts) if attempts > 0 else 0
        yards_per_carry = (rushing_yards / rushing_attempts) if rushing_attempts > 0 else 0
        
        # Passer rating calculation (simplified)
        passer_rating = 85.0  # Placeholder - would need full calculation
        
        return {
            "passing_attempts": attempts,
            "passing_completions": completions,
            "completion_percentage": completion_percentage,
            "passing_yards": passing_yards,
            "yards_per_attempt": yards_per_attempt,
            "passing_touchdowns": passing_tds,
            "interceptions": interceptions,
            "passer_rating": passer_rating,
            "rushing_attempts": rushing_attempts,
            "rushing_yards": rushing_yards,
            "yards_per_carry": yards_per_carry,
            "rushing_touchdowns": rushing_tds,
            "total_touchdowns": passing_tds + rushing_tds,
            "total_plays": attempts + rushing_attempts
        }
    
    def _get_rb_stats(self, player_id: str, plays_query) -> Dict[str, Any]:
        """Get running back-specific statistics."""
        rushing_plays = plays_query.filter(
            and_(
                PlayModel.rusher_player_id == player_id,
                PlayModel.play_type == 'run'
            )
        ).all()
        
        receiving_plays = plays_query.filter(
            and_(
                PlayModel.receiver_player_id == player_id,
                PlayModel.play_type == 'pass',
                PlayModel.complete_pass == 1
            )
        ).all()
        
        # Rushing stats
        carries = len(rushing_plays)
        rushing_yards = sum(p.rushing_yards or 0 for p in rushing_plays)
        rushing_tds = sum(p.rush_touchdown or 0 for p in rushing_plays)
        
        # Receiving stats
        receptions = len(receiving_plays)
        receiving_yards = sum(p.receiving_yards or 0 for p in receiving_plays)
        receiving_tds = sum(p.pass_touchdown or 0 for p in receiving_plays)
        
        # Calculate derived stats
        yards_per_carry = (rushing_yards / carries) if carries > 0 else 0
        yards_per_reception = (receiving_yards / receptions) if receptions > 0 else 0
        
        return {
            "carries": carries,
            "rushing_yards": rushing_yards,
            "yards_per_carry": yards_per_carry,
            "rushing_touchdowns": rushing_tds,
            "receptions": receptions,
            "receiving_yards": receiving_yards,
            "yards_per_reception": yards_per_reception,
            "receiving_touchdowns": receiving_tds,
            "total_yards": rushing_yards + receiving_yards,
            "total_touchdowns": rushing_tds + receiving_tds,
            "total_plays": carries + receptions
        }
    
    def _get_receiver_stats(self, player_id: str, plays_query) -> Dict[str, Any]:
        """Get receiver-specific statistics."""
        targets = plays_query.filter(
            and_(
                PlayModel.receiver_player_id == player_id,
                PlayModel.play_type == 'pass'
            )
        ).all()
        
        receptions = [p for p in targets if p.complete_pass == 1]
        
        # Receiving stats
        target_count = len(targets)
        reception_count = len(receptions)
        receiving_yards = sum(p.receiving_yards or 0 for p in receptions)
        receiving_tds = sum(p.pass_touchdown or 0 for p in receptions)
        
        # Calculate derived stats
        catch_percentage = (reception_count / target_count * 100) if target_count > 0 else 0
        yards_per_reception = (receiving_yards / reception_count) if reception_count > 0 else 0
        yards_per_target = (receiving_yards / target_count) if target_count > 0 else 0
        
        return {
            "targets": target_count,
            "receptions": reception_count,
            "catch_percentage": catch_percentage,
            "receiving_yards": receiving_yards,
            "yards_per_reception": yards_per_reception,
            "yards_per_target": yards_per_target,
            "receiving_touchdowns": receiving_tds,
            "total_plays": target_count
        }
    
    def _get_kicker_stats(self, player_id: str, plays_query) -> Dict[str, Any]:
        """Get kicker-specific statistics."""
        # Placeholder - would need field goal and extra point data
        return {
            "field_goal_attempts": 0,
            "field_goals_made": 0,
            "field_goal_percentage": 0,
            "extra_point_attempts": 0,
            "extra_points_made": 0,
            "extra_point_percentage": 0,
            "total_points": 0
        }
    
    def _get_generic_stats(self, player_id: str, plays_query) -> Dict[str, Any]:
        """Get generic statistics for other positions."""
        return {
            "tackles": 0,
            "assists": 0,
            "sacks": 0,
            "interceptions": 0,
            "fumbles_recovered": 0,
            "defensive_touchdowns": 0
        }
    
    def get_position_leaders(self, position: str, season: Optional[int] = None,
                           stat_category: str = 'yards', limit: int = 10) -> List[Dict[str, Any]]:
        """Get statistical leaders for a position.
        
        Args:
            position: Player position
            season: Season year (current season if None)
            stat_category: Statistical category to rank by
            limit: Number of leaders to return
            
        Returns:
            List of players with statistics, ranked by category
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            players = self.get_by_position(position, season=season)
            
            # Get stats for each player and rank them
            player_stats = []
            for player in players:
                stats = self.get_player_stats(player.player_id, season)
                if stats.get('total_plays', 0) > 0:  # Only include active players
                    player_stats.append(stats)
            
            # Sort by the requested stat category
            if stat_category in ['yards', 'passing_yards', 'rushing_yards', 'receiving_yards']:
                key_func = lambda x: x.get(stat_category, 0)
            elif stat_category in ['touchdowns', 'total_touchdowns']:
                key_func = lambda x: x.get(stat_category, 0)
            elif stat_category == 'completion_percentage':
                key_func = lambda x: x.get(stat_category, 0)
            else:
                key_func = lambda x: x.get(stat_category, 0)
            
            player_stats.sort(key=key_func, reverse=True)
            
            return player_stats[:limit]
            
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_position_leaders: {e}")
            raise DatabaseError(f"Failed to get {position} leaders for {stat_category}") from e