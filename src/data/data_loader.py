"""Data loading service that orchestrates fetching and storing NFL data."""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.database.manager import DatabaseManager
from src.database.config import get_db_session
from src.models.team import TeamModel, TeamCreate
from src.models.player import PlayerModel, PlayerCreate
from src.models.game import GameModel, GameCreate
from src.models.play import PlayModel, PlayCreate
from .nfl_data_client import NFLDataClient, DataFetchConfig
from .data_mapper import DataMapper

logger = logging.getLogger(__name__)


class DataLoadResult:
    """Result of a data loading operation."""
    
    def __init__(self):
        self.success = False
        self.records_processed = 0
        self.records_inserted = 0
        self.records_updated = 0
        self.records_skipped = 0
        self.errors: List[str] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get operation duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'success': self.success,
            'records_processed': self.records_processed,
            'records_inserted': self.records_inserted,
            'records_updated': self.records_updated,
            'records_skipped': self.records_skipped,
            'error_count': len(self.errors),
            'errors': self.errors[:10],  # Limit errors shown
            'duration_seconds': self.duration,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


class DataLoader:
    """Service for loading NFL data into the database."""
    
    def __init__(self, 
                 db_manager: Optional[DatabaseManager] = None,
                 nfl_client: Optional[NFLDataClient] = None,
                 data_mapper: Optional[DataMapper] = None):
        """Initialize data loader.
        
        Args:
            db_manager: Database manager instance
            nfl_client: NFL data client instance
            data_mapper: Data mapper instance
        """
        self.db_manager = db_manager or DatabaseManager()
        self.nfl_client = nfl_client or NFLDataClient()
        self.data_mapper = data_mapper or DataMapper()
        logger.info("Initialized DataLoader")
    
    def load_teams(self) -> DataLoadResult:
        """Load NFL teams data into the database.
        
        Returns:
            DataLoadResult with operation details
        """
        result = DataLoadResult()
        result.start_time = datetime.now()
        
        try:
            logger.info("Starting teams data load")
            
            # Fetch teams data
            teams_df = self.nfl_client.fetch_teams()
            if teams_df.empty:
                logger.warning("No teams data received")
                result.success = True  # Not an error, just no data
                return result
            
            # Map to our models
            team_creates = self.data_mapper.map_teams_data(teams_df)
            result.records_processed = len(team_creates)
            
            # Load into database
            session = self.db_manager.get_session()
            try:
                for team_create in team_creates:
                    try:
                        # Check if team exists
                        existing_team = session.query(TeamModel).filter(
                            TeamModel.team_abbr == team_create.team_abbr
                        ).first()
                        
                        if existing_team:
                            # Update existing team
                            for field, value in team_create.model_dump(exclude_unset=True).items():
                                setattr(existing_team, field, value)
                            result.records_updated += 1
                        else:
                            # Create new team
                            team_model = TeamModel(**team_create.model_dump())
                            session.add(team_model)
                            result.records_inserted += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to process team {team_create.team_abbr}: {e}")
                        result.errors.append(str(e))
                        result.records_skipped += 1
                        continue
                
                session.commit()
                result.success = True
                logger.info(f"Teams load completed: {result.records_inserted} inserted, "
                          f"{result.records_updated} updated, {result.records_skipped} skipped")
                
            except Exception as e:
                session.rollback()
                raise
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Teams data load failed: {e}")
            result.errors.append(str(e))
            result.success = False
        
        finally:
            result.end_time = datetime.now()
        
        return result
    
    def load_players(self, seasons: Optional[List[int]] = None) -> DataLoadResult:
        """Load NFL players data into the database.
        
        Args:
            seasons: Optional list of seasons to load
            
        Returns:
            DataLoadResult with operation details
        """
        result = DataLoadResult()
        result.start_time = datetime.now()
        
        try:
            logger.info(f"Starting players data load for seasons: {seasons}")
            
            # Fetch players data
            players_df = self.nfl_client.fetch_players(seasons)
            if players_df.empty:
                logger.warning("No players data received")
                result.success = True
                return result
            
            # Map to our models
            player_creates = self.data_mapper.map_players_data(players_df)
            result.records_processed = len(player_creates)
            
            # Load into database
            session = self.db_manager.get_session()
            try:
                for player_create in player_creates:
                    try:
                        # Check if player exists
                        existing_player = session.query(PlayerModel).filter(
                            PlayerModel.player_id == player_create.player_id
                        ).first()
                        
                        if existing_player:
                            # Update existing player
                            for field, value in player_create.model_dump(exclude_unset=True).items():
                                setattr(existing_player, field, value)
                            result.records_updated += 1
                        else:
                            # Create new player
                            player_model = PlayerModel(**player_create.model_dump())
                            session.add(player_model)
                            result.records_inserted += 1
                        
                    except IntegrityError as e:
                        session.rollback()
                        logger.warning(f"Integrity error for player {player_create.player_id}: {e}")
                        result.errors.append(str(e))
                        result.records_skipped += 1
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to process player {player_create.player_id}: {e}")
                        result.errors.append(str(e))
                        result.records_skipped += 1
                        continue
                
                session.commit()
                result.success = True
                logger.info(f"Players load completed: {result.records_inserted} inserted, "
                          f"{result.records_updated} updated, {result.records_skipped} skipped")
                
            except Exception as e:
                session.rollback()
                raise
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Players data load failed: {e}")
            result.errors.append(str(e))
            result.success = False
        
        finally:
            result.end_time = datetime.now()
        
        return result
    
    def load_games(self, seasons: List[int]) -> DataLoadResult:
        """Load NFL games data into the database.
        
        Args:
            seasons: List of seasons to load
            
        Returns:
            DataLoadResult with operation details
        """
        result = DataLoadResult()
        result.start_time = datetime.now()
        
        try:
            logger.info(f"Starting games data load for seasons: {seasons}")
            
            # Fetch games data
            games_df = self.nfl_client.fetch_games(seasons)
            if games_df.empty:
                logger.warning("No games data received")
                result.success = True
                return result
            
            # Map to our models
            game_creates = self.data_mapper.map_games_data(games_df)
            result.records_processed = len(game_creates)
            
            # Load into database
            session = self.db_manager.get_session()
            try:
                for game_create in game_creates:
                    try:
                        # Check if game exists
                        existing_game = session.query(GameModel).filter(
                            GameModel.game_id == game_create.game_id
                        ).first()
                        
                        if existing_game:
                            # Update existing game
                            for field, value in game_create.model_dump(exclude_unset=True).items():
                                setattr(existing_game, field, value)
                            result.records_updated += 1
                        else:
                            # Create new game
                            game_model = GameModel(**game_create.model_dump())
                            session.add(game_model)
                            result.records_inserted += 1
                        
                    except IntegrityError as e:
                        session.rollback()
                        logger.warning(f"Integrity error for game {game_create.game_id}: {e}")
                        result.errors.append(str(e))
                        result.records_skipped += 1
                        continue
                    except Exception as e:
                        logger.warning(f"Failed to process game {game_create.game_id}: {e}")
                        result.errors.append(str(e))
                        result.records_skipped += 1
                        continue
                
                session.commit()
                result.success = True
                logger.info(f"Games load completed: {result.records_inserted} inserted, "
                          f"{result.records_updated} updated, {result.records_skipped} skipped")
                
            except Exception as e:
                session.rollback()
                raise
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Games data load failed: {e}")
            result.errors.append(str(e))
            result.success = False
        
        finally:
            result.end_time = datetime.now()
        
        return result
    
    def load_plays(self, seasons: List[int], weeks: Optional[List[int]] = None,
                  batch_size: int = 1000) -> DataLoadResult:
        """Load NFL plays data into the database.
        
        Args:
            seasons: List of seasons to load
            weeks: Optional list of weeks to load
            batch_size: Batch size for processing
            
        Returns:
            DataLoadResult with operation details
        """
        result = DataLoadResult()
        result.start_time = datetime.now()
        
        try:
            logger.info(f"Starting plays data load for seasons: {seasons}, weeks: {weeks}")
            
            # Fetch plays data
            plays_df = self.nfl_client.fetch_plays(seasons, weeks)
            if plays_df.empty:
                logger.warning("No plays data received")
                result.success = True
                return result
            
            # Map to our models in batches
            play_batches = self.data_mapper.map_plays_data(plays_df, batch_size)
            total_plays = sum(len(batch) for batch in play_batches)
            result.records_processed = total_plays
            
            logger.info(f"Processing {total_plays} plays in {len(play_batches)} batches")
            
            # Load into database batch by batch
            session = self.db_manager.get_session()
            try:
                for batch_num, play_batch in enumerate(play_batches):
                    logger.info(f"Processing batch {batch_num + 1}/{len(play_batches)} "
                              f"({len(play_batch)} plays)")
                    
                    for play_create in play_batch:
                        try:
                            # Check if play exists
                            existing_play = session.query(PlayModel).filter(
                                PlayModel.play_id == play_create.play_id
                            ).first()
                            
                            if existing_play:
                                # Update existing play
                                for field, value in play_create.model_dump(exclude_unset=True).items():
                                    setattr(existing_play, field, value)
                                result.records_updated += 1
                            else:
                                # Create new play
                                play_model = PlayModel(**play_create.model_dump())
                                session.add(play_model)
                                result.records_inserted += 1
                            
                        except IntegrityError as e:
                            session.rollback()
                            logger.warning(f"Integrity error for play {play_create.play_id}: {e}")
                            result.errors.append(str(e))
                            result.records_skipped += 1
                            continue
                        except Exception as e:
                            logger.warning(f"Failed to process play {play_create.play_id}: {e}")
                            result.errors.append(str(e))
                            result.records_skipped += 1
                            continue
                    
                    # Commit each batch
                    session.commit()
                    logger.info(f"Committed batch {batch_num + 1}")
                
                result.success = True
                logger.info(f"Plays load completed: {result.records_inserted} inserted, "
                          f"{result.records_updated} updated, {result.records_skipped} skipped")
                
            except Exception as e:
                session.rollback()
                raise
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Plays data load failed: {e}")
            result.errors.append(str(e))
            result.success = False
        
        finally:
            result.end_time = datetime.now()
        
        return result
    
    def load_full_dataset(self, seasons: List[int], 
                         include_plays: bool = True,
                         weeks: Optional[List[int]] = None) -> Dict[str, DataLoadResult]:
        """Load complete NFL dataset for specified seasons.
        
        Args:
            seasons: List of seasons to load
            include_plays: Whether to load play-by-play data
            weeks: Optional list of weeks to load (for plays)
            
        Returns:
            Dictionary mapping data type to DataLoadResult
        """
        logger.info(f"Starting full dataset load for seasons: {seasons}")
        results = {}
        
        # Load teams first (required for foreign keys)
        logger.info("Loading teams data...")
        results['teams'] = self.load_teams()
        
        # Load games
        logger.info("Loading games data...")
        results['games'] = self.load_games(seasons)
        
        # Load players
        logger.info("Loading players data...")
        results['players'] = self.load_players(seasons)
        
        # Load plays if requested
        if include_plays:
            logger.info("Loading plays data...")
            results['plays'] = self.load_plays(seasons, weeks)
        
        # Summary
        total_inserted = sum(r.records_inserted for r in results.values())
        total_updated = sum(r.records_updated for r in results.values())
        total_errors = sum(len(r.errors) for r in results.values())
        
        logger.info(f"Full dataset load completed: {total_inserted} inserted, "
                   f"{total_updated} updated, {total_errors} errors")
        
        return results
    
    def get_load_status(self) -> Dict[str, Any]:
        """Get current database load status.
        
        Returns:
            Dictionary with database status information
        """
        try:
            session = self.db_manager.get_session()
            try:
                status = {
                    'teams_count': session.query(TeamModel).count(),
                    'players_count': session.query(PlayerModel).count(),
                    'games_count': session.query(GameModel).count(),
                    'plays_count': session.query(PlayModel).count(),
                }
                
                # Get latest data timestamps
                latest_game = session.query(GameModel).order_by(
                    GameModel.game_date.desc()
                ).first()
                
                if latest_game:
                    status['latest_game_date'] = latest_game.game_date.isoformat()
                    status['latest_season'] = latest_game.season
                
                # Get seasons available
                seasons = session.query(GameModel.season).distinct().all()
                status['available_seasons'] = sorted([s[0] for s in seasons])
                
                return status
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to get load status: {e}")
            return {'error': str(e)}