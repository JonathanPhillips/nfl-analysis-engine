"""Tests for team service."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from src.services.team_service import TeamService
from src.services.base import NotFoundError, DatabaseError
from src.models.team import TeamModel


class TestTeamService:
    """Test team service functionality."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def service(self, mock_db_session):
        """Create team service instance."""
        return TeamService(mock_db_session)
    
    @pytest.fixture
    def mock_team(self):
        """Create mock team."""
        team = Mock(spec=TeamModel)
        team.id = 1
        team.team_abbr = "SF"
        team.team_name = "San Francisco"
        team.team_nick = "49ers"
        team.team_conf = "NFC"
        team.team_division = "West"
        return team
    
    def test_init(self, mock_db_session):
        """Test service initialization."""
        service = TeamService(mock_db_session)
        assert service.db == mock_db_session
        assert service.model_class == TeamModel
    
    def test_get_by_abbreviation_success(self, service, mock_db_session, mock_team):
        """Test successful get by abbreviation."""
        # Setup mock
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_team
        
        # Execute
        result = service.get_by_abbreviation("sf")
        
        # Assert
        assert result == mock_team
        mock_db_session.query.assert_called_once_with(TeamModel)
    
    def test_get_by_abbreviation_not_found(self, service, mock_db_session):
        """Test get by abbreviation when team not found."""
        # Setup mock
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = service.get_by_abbreviation("XX")
        
        # Assert
        assert result is None
    
    def test_get_by_abbreviation_or_404_success(self, service, mock_db_session, mock_team):
        """Test successful get by abbreviation or 404."""
        # Setup mock
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_team
        
        # Execute
        result = service.get_by_abbreviation_or_404("SF")
        
        # Assert
        assert result == mock_team
    
    def test_get_by_abbreviation_or_404_not_found(self, service, mock_db_session):
        """Test get by abbreviation or 404 when team not found."""
        # Setup mock
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Execute and assert
        with pytest.raises(NotFoundError, match="Team XX not found"):
            service.get_by_abbreviation_or_404("XX")
    
    def test_get_by_conference(self, service, mock_db_session, mock_team):
        """Test get teams by conference."""
        # Setup mock
        teams = [mock_team]
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = teams
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = service.get_by_conference("NFC")
        
        # Assert
        assert result == teams
        mock_query.filter.assert_called_once()
        mock_query.filter.return_value.order_by.assert_called_once()
    
    def test_get_by_division(self, service, mock_db_session, mock_team):
        """Test get teams by division."""
        # Setup mock
        teams = [mock_team]
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = teams
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = service.get_by_division("NFC", "West")
        
        # Assert
        assert result == teams
        mock_query.filter.assert_called_once()
    
    def test_search_teams(self, service, mock_db_session, mock_team):
        """Test search teams functionality."""
        # Setup mock
        teams = [mock_team]
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = teams
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = service.search_teams("49ers")
        
        # Assert
        assert result == teams
        mock_query.filter.assert_called_once()
    
    @patch('src.services.team_service.TeamService.get_by_abbreviation_or_404')
    def test_get_team_stats(self, mock_get_team, service, mock_db_session, mock_team):
        """Test get team statistics."""
        # Setup mocks
        mock_get_team.return_value = mock_team
        
        # Mock game data
        mock_game = Mock()
        mock_game.home_team = "SF"
        mock_game.away_team = "KC"
        mock_game.home_score = 24
        mock_game.away_score = 21
        
        mock_query = Mock()
        mock_query.filter.return_value.filter.return_value.filter.return_value.all.return_value = [mock_game]
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = service.get_team_stats("SF", 2024)
        
        # Assert
        assert result["team"] == mock_team
        assert result["season"] == 2024
        assert result["games_played"] == 1
        assert result["wins"] == 1
        assert result["losses"] == 0
        assert result["points_for"] == 24
        assert result["points_against"] == 21
    
    def test_get_team_stats_team_not_found(self, service, mock_db_session):
        """Test get team stats when team not found."""
        with patch.object(service, 'get_by_abbreviation_or_404', side_effect=NotFoundError("Team not found")):
            with pytest.raises(NotFoundError):
                service.get_team_stats("XX", 2024)
    
    def test_get_all_teams_grouped(self, service, mock_db_session):
        """Test get all teams grouped by conference and division."""
        # Setup mock teams
        teams = []
        for conf in ["AFC", "NFC"]:
            for div in ["North", "South", "East", "West"]:
                team = Mock(spec=TeamModel)
                team.team_conf = conf
                team.team_division = div
                team.team_abbr = f"{conf[0]}{div[0]}"
                teams.append(team)
        
        with patch.object(service, 'list', return_value=teams):
            # Execute
            result = service.get_all_teams_grouped()
            
            # Assert
            assert "AFC" in result
            assert "NFC" in result
            assert "North" in result["AFC"]
            assert "South" in result["AFC"]
            assert "East" in result["AFC"]
            assert "West" in result["AFC"]
            assert len(result["AFC"]["North"]) == 1
            assert len(result["NFC"]["West"]) == 1