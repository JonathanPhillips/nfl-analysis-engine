"""Tests for base service functionality."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.services.base import BaseService, ServiceException, NotFoundError, DatabaseError, ValidationException
from src.models.team import TeamModel, TeamCreate, TeamUpdate


class TestBaseService:
    """Test base service functionality."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture  
    def service(self, mock_db_session):
        """Create base service instance."""
        return BaseService[TeamModel, TeamCreate, TeamUpdate](mock_db_session, TeamModel)
    
    def test_init(self, mock_db_session):
        """Test service initialization."""
        service = BaseService(mock_db_session, TeamModel)
        assert service.db == mock_db_session
        assert service.model_class == TeamModel
        assert service._logger is not None
    
    def test_get_by_id_success(self, service, mock_db_session):
        """Test successful get by ID."""
        # Setup mock
        mock_team = Mock(spec=TeamModel)
        mock_team.id = 1
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_team
        
        # Execute
        result = service.get_by_id(1)
        
        # Assert
        assert result == mock_team
        mock_db_session.query.assert_called_once_with(TeamModel)
    
    def test_get_by_id_not_found(self, service, mock_db_session):
        """Test get by ID when entity not found."""
        # Setup mock
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = service.get_by_id(1)
        
        # Assert
        assert result is None
    
    def test_get_by_id_database_error(self, service, mock_db_session):
        """Test get by ID with database error."""
        # Setup mock to raise SQLAlchemy error
        mock_db_session.query.side_effect = SQLAlchemyError("Database error")
        
        # Execute and assert
        with pytest.raises(DatabaseError, match="Failed to get TeamModel by ID"):
            service.get_by_id(1)
    
    def test_get_by_id_or_404_success(self, service, mock_db_session):
        """Test successful get by ID or 404."""
        # Setup mock
        mock_team = Mock(spec=TeamModel)
        mock_team.id = 1
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_team
        
        # Execute
        result = service.get_by_id_or_404(1)
        
        # Assert
        assert result == mock_team
    
    def test_get_by_id_or_404_not_found(self, service, mock_db_session):
        """Test get by ID or 404 when entity not found."""
        # Setup mock
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Execute and assert
        with pytest.raises(NotFoundError, match="TeamModel with ID 1 not found"):
            service.get_by_id_or_404(1)
    
    def test_list_success(self, service, mock_db_session):
        """Test successful list operation."""
        # Setup mock
        mock_teams = [Mock(spec=TeamModel), Mock(spec=TeamModel)]
        mock_query = Mock()
        mock_query.offset.return_value.limit.return_value.all.return_value = mock_teams
        mock_db_session.query.return_value = mock_query
        
        # Execute
        result = service.list(limit=10, offset=5)
        
        # Assert
        assert result == mock_teams
        mock_query.offset.assert_called_once_with(5)
        mock_query.offset.return_value.limit.assert_called_once_with(10)
    
    def test_list_with_filters(self, service, mock_db_session):
        """Test list with filters."""
        # Setup mock
        mock_teams = [Mock(spec=TeamModel)]
        mock_query = Mock()
        mock_query.filter.return_value.offset.return_value.limit.return_value.all.return_value = mock_teams
        mock_db_session.query.return_value = mock_query
        
        # Mock hasattr to return True for our filter field
        with patch('builtins.hasattr', return_value=True):
            # Execute
            result = service.list(filters={"team_abbr": "SF"})
            
            # Assert
            assert result == mock_teams
            mock_query.filter.assert_called_once()
    
    def test_count_success(self, service, mock_db_session):
        """Test successful count operation."""
        # Setup mock
        mock_db_session.query.return_value.count.return_value = 32
        
        # Execute
        result = service.count()
        
        # Assert
        assert result == 32
        mock_db_session.query.assert_called_once_with(TeamModel)
    
    def test_count_database_error(self, service, mock_db_session):
        """Test count with database error."""
        # Setup mock to raise error
        mock_db_session.query.side_effect = SQLAlchemyError("Database error")
        
        # Execute and assert
        with pytest.raises(DatabaseError, match="Failed to count TeamModel entities"):
            service.count()
    
    def test_create_success(self, service, mock_db_session):
        """Test successful create operation."""
        # Setup mock
        mock_create_data = Mock()
        mock_create_data.model_dump.return_value = {"team_abbr": "SF", "team_name": "San Francisco"}
        
        mock_team = Mock(spec=TeamModel)
        mock_team.id = 1
        
        # Execute
        with patch.object(service.model_class, '__init__', return_value=None) as mock_init:
            with patch.object(service, 'model_class', return_value=mock_team) as mock_class:
                mock_class.return_value = mock_team
                result = service.create(mock_create_data)
                
                # Assert
                mock_db_session.add.assert_called_once()
                mock_db_session.commit.assert_called_once()
                mock_db_session.refresh.assert_called_once()
    
    def test_create_database_error(self, service, mock_db_session):
        """Test create with database error."""
        # Setup mock
        mock_create_data = Mock()
        mock_create_data.model_dump.return_value = {"team_abbr": "SF"}
        mock_db_session.add.side_effect = SQLAlchemyError("Database error")
        
        # Execute and assert
        with pytest.raises(DatabaseError, match="Failed to create TeamModel"):
            service.create(mock_create_data)
        
        mock_db_session.rollback.assert_called_once()
    
    def test_exists_true(self, service, mock_db_session):
        """Test exists when entity exists."""
        # Setup mock
        mock_db_session.query.return_value.filter.return_value.first.return_value = Mock()
        
        # Execute
        result = service.exists(1)
        
        # Assert
        assert result is True
    
    def test_exists_false(self, service, mock_db_session):
        """Test exists when entity does not exist."""
        # Setup mock
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = service.exists(1)
        
        # Assert
        assert result is False