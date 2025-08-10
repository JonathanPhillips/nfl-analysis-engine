"""Game service for business logic."""

from typing import Optional, List, Dict, Any
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_, desc, asc

from .base import BaseService, DatabaseError, NotFoundError
from ..models.game import GameModel, GameCreate, GameUpdate


class GameService(BaseService[GameModel, GameCreate, GameUpdate]):
    """Service class for game operations."""
    
    def __init__(self, db_session: Session):
        """Initialize game service."""
        super().__init__(db_session, GameModel)
    
    def get_by_game_id(self, game_id: str) -> Optional[GameModel]:
        """Get game by game ID.
        
        Args:
            game_id: Unique game identifier
            
        Returns:
            Game if found, None otherwise
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            return self.db.query(GameModel).filter(GameModel.game_id == game_id).first()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_by_game_id: {e}")
            raise DatabaseError(f"Failed to get game by ID {game_id}") from e
    
    def get_by_game_id_or_404(self, game_id: str) -> GameModel:
        """Get game by game ID or raise NotFoundError.
        
        Args:
            game_id: Unique game identifier
            
        Returns:
            Game if found
            
        Raises:
            NotFoundError: If game not found
        """
        game = self.get_by_game_id(game_id)
        if game is None:
            raise NotFoundError(f"Game {game_id} not found")
        return game
    
    def get_games_by_season(self, season: int, 
                           season_type: Optional[str] = None,
                           week: Optional[int] = None,
                           limit: int = 100,
                           offset: int = 0) -> List[GameModel]:
        """Get games by season with optional filtering.
        
        Args:
            season: Season year
            season_type: Season type ('REG', 'POST', 'PRE')
            week: Week number
            limit: Maximum number of games to return
            offset: Number of games to skip
            
        Returns:
            List of games matching criteria
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(GameModel).filter(GameModel.season == season)
            
            # Apply optional filters
            if season_type:
                query = query.filter(GameModel.season_type == season_type.upper())
            
            if week is not None:
                query = query.filter(GameModel.week == week)
            
            # Order by game date descending
            query = query.order_by(desc(GameModel.game_date))
            
            # Apply pagination
            return query.offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_games_by_season: {e}")
            raise DatabaseError(f"Failed to get games for season {season}") from e
    
    def get_team_games(self, team_abbr: str,
                       season: Optional[int] = None,
                       season_type: Optional[str] = None,
                       home_only: bool = False,
                       away_only: bool = False,
                       limit: int = 100,
                       offset: int = 0) -> List[GameModel]:
        """Get games for a specific team.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year (all seasons if None)
            season_type: Season type ('REG', 'POST', 'PRE')
            home_only: Only return home games
            away_only: Only return away games
            limit: Maximum number of games to return
            offset: Number of games to skip
            
        Returns:
            List of team's games
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            team_abbr = team_abbr.upper()
            
            # Build team filter
            if home_only:
                team_filter = GameModel.home_team == team_abbr
            elif away_only:
                team_filter = GameModel.away_team == team_abbr
            else:
                team_filter = or_(
                    GameModel.home_team == team_abbr,
                    GameModel.away_team == team_abbr
                )
            
            query = self.db.query(GameModel).filter(team_filter)
            
            # Apply optional filters
            if season:
                query = query.filter(GameModel.season == season)
            
            if season_type:
                query = query.filter(GameModel.season_type == season_type.upper())
            
            # Order by game date descending
            query = query.order_by(desc(GameModel.game_date))
            
            # Apply pagination
            return query.offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_team_games: {e}")
            raise DatabaseError(f"Failed to get games for team {team_abbr}") from e
    
    def get_matchup_history(self, team1: str, team2: str,
                           season: Optional[int] = None,
                           limit: int = 10) -> List[GameModel]:
        """Get head-to-head matchup history between two teams.
        
        Args:
            team1: First team abbreviation
            team2: Second team abbreviation  
            season: Season year (all seasons if None)
            limit: Maximum number of games to return
            
        Returns:
            List of games between the teams
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            team1 = team1.upper()
            team2 = team2.upper()
            
            query = self.db.query(GameModel).filter(
                or_(
                    and_(GameModel.home_team == team1, GameModel.away_team == team2),
                    and_(GameModel.home_team == team2, GameModel.away_team == team1)
                )
            )
            
            # Apply season filter if provided
            if season:
                query = query.filter(GameModel.season == season)
            
            # Order by game date descending
            query = query.order_by(desc(GameModel.game_date))
            
            return query.limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_matchup_history: {e}")
            raise DatabaseError(f"Failed to get matchup history for {team1} vs {team2}") from e
    
    def get_games_by_date_range(self, start_date: date, end_date: date,
                               limit: int = 100, offset: int = 0) -> List[GameModel]:
        """Get games within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            limit: Maximum number of games to return
            offset: Number of games to skip
            
        Returns:
            List of games in the date range
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(GameModel).filter(
                and_(
                    GameModel.game_date >= start_date,
                    GameModel.game_date <= end_date
                )
            ).order_by(desc(GameModel.game_date))
            
            return query.offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_games_by_date_range: {e}")
            raise DatabaseError(f"Failed to get games between {start_date} and {end_date}") from e
    
    def get_upcoming_games(self, days_ahead: int = 7, limit: int = 100) -> List[GameModel]:
        """Get upcoming games.
        
        Args:
            days_ahead: Number of days ahead to look
            limit: Maximum number of games to return
            
        Returns:
            List of upcoming games
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            today = date.today()
            future_date = date.fromordinal(today.toordinal() + days_ahead)
            
            query = self.db.query(GameModel).filter(
                and_(
                    GameModel.game_date >= today,
                    GameModel.game_date <= future_date,
                    GameModel.home_score.is_(None)  # Games not yet played
                )
            ).order_by(asc(GameModel.game_date))
            
            return query.limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_upcoming_games: {e}")
            raise DatabaseError("Failed to get upcoming games") from e
    
    def get_completed_games(self, season: Optional[int] = None,
                           limit: int = 100, offset: int = 0) -> List[GameModel]:
        """Get completed games with scores.
        
        Args:
            season: Season year (all seasons if None)
            limit: Maximum number of games to return
            offset: Number of games to skip
            
        Returns:
            List of completed games
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(GameModel).filter(GameModel.home_score.isnot(None))
            
            if season:
                query = query.filter(GameModel.season == season)
            
            query = query.order_by(desc(GameModel.game_date))
            
            return query.offset(offset).limit(limit).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_completed_games: {e}")
            raise DatabaseError("Failed to get completed games") from e
    
    def get_games_by_week(self, season: int, week: int,
                         season_type: str = 'REG') -> List[GameModel]:
        """Get games for a specific week.
        
        Args:
            season: Season year
            week: Week number
            season_type: Season type ('REG', 'POST', 'PRE')
            
        Returns:
            List of games for the week
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            query = self.db.query(GameModel).filter(
                and_(
                    GameModel.season == season,
                    GameModel.week == week,
                    GameModel.season_type == season_type.upper()
                )
            ).order_by(GameModel.game_date)
            
            return query.all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_games_by_week: {e}")
            raise DatabaseError(f"Failed to get games for season {season} week {week}") from e
    
    def get_game_summary(self, game_id: str) -> Dict[str, Any]:
        """Get comprehensive game summary with statistics.
        
        Args:
            game_id: Unique game identifier
            
        Returns:
            Dictionary with game summary and statistics
            
        Raises:
            NotFoundError: If game not found
            DatabaseError: If database error occurs
        """
        try:
            game = self.get_by_game_id_or_404(game_id)
            
            summary = {
                "game": game,
                "is_completed": game.home_score is not None,
                "winner": None,
                "margin": None,
                "total_points": None,
                "game_info": {
                    "season": game.season,
                    "week": game.week,
                    "season_type": game.season_type,
                    "date": game.game_date,
                    "home_team": game.home_team,
                    "away_team": game.away_team
                }
            }
            
            # Add completed game statistics
            if game.home_score is not None and game.away_score is not None:
                summary["total_points"] = game.home_score + game.away_score
                summary["margin"] = abs(game.home_score - game.away_score)
                
                if game.home_score > game.away_score:
                    summary["winner"] = game.home_team
                elif game.away_score > game.home_score:
                    summary["winner"] = game.away_team
                else:
                    summary["winner"] = "TIE"
                
                summary["final_score"] = {
                    "home": game.home_score,
                    "away": game.away_score
                }
            
            return summary
            
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_game_summary: {e}")
            raise DatabaseError(f"Failed to get summary for game {game_id}") from e
    
    def update_game_score(self, game_id: str, home_score: int, away_score: int) -> GameModel:
        """Update game score.
        
        Args:
            game_id: Unique game identifier
            home_score: Home team score
            away_score: Away team score
            
        Returns:
            Updated game
            
        Raises:
            NotFoundError: If game not found
            DatabaseError: If database error occurs
        """
        try:
            game = self.get_by_game_id_or_404(game_id)
            
            game.home_score = home_score
            game.away_score = away_score
            
            self.db.commit()
            self.db.refresh(game)
            
            self._logger.info(f"Updated score for game {game_id}: {home_score}-{away_score}")
            return game
            
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            self._logger.error(f"Database error in update_game_score: {e}")
            raise DatabaseError(f"Failed to update score for game {game_id}") from e