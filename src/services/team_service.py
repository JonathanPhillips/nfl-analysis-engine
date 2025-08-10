"""Team service for business logic."""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_, or_

from .base import BaseService, DatabaseError, NotFoundError
from ..models.team import TeamModel, TeamCreate, TeamUpdate
from ..models.game import GameModel


class TeamService(BaseService[TeamModel, TeamCreate, TeamUpdate]):
    """Service class for team operations."""
    
    def __init__(self, db_session: Session):
        """Initialize team service."""
        super().__init__(db_session, TeamModel)
    
    def get_by_abbreviation(self, team_abbr: str) -> Optional[TeamModel]:
        """Get team by abbreviation.
        
        Args:
            team_abbr: Team abbreviation (e.g., 'SF', 'KC')
            
        Returns:
            Team if found, None otherwise
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            return self.db.query(TeamModel).filter(
                TeamModel.team_abbr == team_abbr.upper()
            ).first()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_by_abbreviation: {e}")
            raise DatabaseError(f"Failed to get team by abbreviation {team_abbr}") from e
    
    def get_by_abbreviation_or_404(self, team_abbr: str) -> TeamModel:
        """Get team by abbreviation or raise NotFoundError.
        
        Args:
            team_abbr: Team abbreviation
            
        Returns:
            Team if found
            
        Raises:
            NotFoundError: If team not found
        """
        team = self.get_by_abbreviation(team_abbr)
        if team is None:
            raise NotFoundError(f"Team {team_abbr} not found")
        return team
    
    def get_by_conference(self, conference: str) -> List[TeamModel]:
        """Get teams by conference.
        
        Args:
            conference: Conference ('AFC' or 'NFC')
            
        Returns:
            List of teams in the conference
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            return self.db.query(TeamModel).filter(
                TeamModel.team_conf == conference.upper()
            ).order_by(TeamModel.team_division, TeamModel.team_name).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_by_conference: {e}")
            raise DatabaseError(f"Failed to get teams by conference {conference}") from e
    
    def get_by_division(self, conference: str, division: str) -> List[TeamModel]:
        """Get teams by division.
        
        Args:
            conference: Conference ('AFC' or 'NFC')  
            division: Division ('North', 'South', 'East', 'West')
            
        Returns:
            List of teams in the division
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            return self.db.query(TeamModel).filter(
                and_(
                    TeamModel.team_conf == conference.upper(),
                    TeamModel.team_division == division.title()
                )
            ).order_by(TeamModel.team_name).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_by_division: {e}")
            raise DatabaseError(f"Failed to get teams by division {conference} {division}") from e
    
    def search_teams(self, query: str) -> List[TeamModel]:
        """Search teams by name, nickname, or abbreviation.
        
        Args:
            query: Search query
            
        Returns:
            List of matching teams
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            search_term = f"%{query}%"
            return self.db.query(TeamModel).filter(
                or_(
                    TeamModel.team_name.ilike(search_term),
                    TeamModel.team_nick.ilike(search_term),
                    TeamModel.team_abbr.ilike(search_term)
                )
            ).order_by(TeamModel.team_name).all()
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in search_teams: {e}")
            raise DatabaseError(f"Failed to search teams with query '{query}'") from e
    
    def get_team_stats(self, team_abbr: str, season: Optional[int] = None) -> Dict[str, Any]:
        """Get team statistics for a season.
        
        Args:
            team_abbr: Team abbreviation
            season: Season year (current season if None)
            
        Returns:
            Dictionary with team statistics
            
        Raises:
            NotFoundError: If team not found
            DatabaseError: If database error occurs
        """
        try:
            # Verify team exists
            team = self.get_by_abbreviation_or_404(team_abbr)
            
            # Build query for team games
            query = self.db.query(GameModel).filter(
                or_(
                    GameModel.home_team == team_abbr.upper(),
                    GameModel.away_team == team_abbr.upper()
                )
            )
            
            # Filter by season if provided
            if season:
                query = query.filter(GameModel.season == season)
            
            # Only completed games
            query = query.filter(GameModel.home_score.isnot(None))
            
            games = query.all()
            
            # Calculate statistics
            stats = {
                "team": team,
                "season": season,
                "games_played": len(games),
                "wins": 0,
                "losses": 0,
                "ties": 0,
                "points_for": 0,
                "points_against": 0,
                "home_games": 0,
                "away_games": 0,
                "home_wins": 0,
                "away_wins": 0
            }
            
            for game in games:
                is_home = game.home_team == team_abbr.upper()
                team_score = game.home_score if is_home else game.away_score
                opp_score = game.away_score if is_home else game.home_score
                
                # Update scores
                stats["points_for"] += team_score
                stats["points_against"] += opp_score
                
                # Update game counts
                if is_home:
                    stats["home_games"] += 1
                else:
                    stats["away_games"] += 1
                
                # Update win/loss record
                if team_score > opp_score:
                    stats["wins"] += 1
                    if is_home:
                        stats["home_wins"] += 1
                    else:
                        stats["away_wins"] += 1
                elif team_score < opp_score:
                    stats["losses"] += 1
                else:
                    stats["ties"] += 1
            
            # Calculate derived statistics
            if stats["games_played"] > 0:
                stats["win_percentage"] = stats["wins"] / stats["games_played"]
                stats["points_per_game"] = stats["points_for"] / stats["games_played"]
                stats["points_allowed_per_game"] = stats["points_against"] / stats["games_played"]
                stats["point_differential"] = stats["points_for"] - stats["points_against"]
            else:
                stats["win_percentage"] = 0.0
                stats["points_per_game"] = 0.0
                stats["points_allowed_per_game"] = 0.0
                stats["point_differential"] = 0
            
            return stats
            
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_team_stats: {e}")
            raise DatabaseError(f"Failed to get stats for team {team_abbr}") from e
    
    def get_division_standings(self, conference: str, division: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get division standings.
        
        Args:
            conference: Conference ('AFC' or 'NFC')
            division: Division ('North', 'South', 'East', 'West')
            season: Season year (current season if None)
            
        Returns:
            List of team standings in the division
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            # Get teams in division
            teams = self.get_by_division(conference, division)
            
            standings = []
            for team in teams:
                stats = self.get_team_stats(team.team_abbr, season)
                standings.append(stats)
            
            # Sort by win percentage (descending), then by point differential (descending)
            standings.sort(key=lambda x: (x["win_percentage"], x["point_differential"]), reverse=True)
            
            return standings
            
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_division_standings: {e}")
            raise DatabaseError(f"Failed to get standings for {conference} {division}") from e
    
    def get_conference_standings(self, conference: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conference standings.
        
        Args:
            conference: Conference ('AFC' or 'NFC')
            season: Season year (current season if None)
            
        Returns:
            List of team standings in the conference
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            # Get teams in conference
            teams = self.get_by_conference(conference)
            
            standings = []
            for team in teams:
                stats = self.get_team_stats(team.team_abbr, season)
                standings.append(stats)
            
            # Sort by win percentage (descending), then by point differential (descending)
            standings.sort(key=lambda x: (x["win_percentage"], x["point_differential"]), reverse=True)
            
            return standings
            
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_conference_standings: {e}")
            raise DatabaseError(f"Failed to get standings for {conference}") from e
    
    def get_all_teams_grouped(self) -> Dict[str, Dict[str, List[TeamModel]]]:
        """Get all teams grouped by conference and division.
        
        Returns:
            Dictionary with structure: {conference: {division: [teams]}}
            
        Raises:
            DatabaseError: If database error occurs
        """
        try:
            teams = self.list(limit=32, order_by="team_name")
            
            grouped = {
                "AFC": {"North": [], "South": [], "East": [], "West": []},
                "NFC": {"North": [], "South": [], "East": [], "West": []}
            }
            
            for team in teams:
                if team.team_conf in grouped and team.team_division in grouped[team.team_conf]:
                    grouped[team.team_conf][team.team_division].append(team)
            
            return grouped
            
        except SQLAlchemyError as e:
            self._logger.error(f"Database error in get_all_teams_grouped: {e}")
            raise DatabaseError("Failed to get teams grouped by division") from e