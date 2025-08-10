"""NFL data client for integrating with nfl_data_py."""

import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from pathlib import Path
import pandas as pd
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import nfl_data_py conditionally for testing
try:
    import nfl_data_py as nfl
    NFL_DATA_PY_AVAILABLE = True
except ImportError:
    # Create a stub nfl module for testing when nfl_data_py is not available
    class MockNFLModule:
        def import_team_desc(self):
            raise ImportError("nfl_data_py not available")
        def import_schedules(self, seasons):
            raise ImportError("nfl_data_py not available")
        def import_pbp_data(self, seasons, downcast=True):
            raise ImportError("nfl_data_py not available")
        def import_rosters(self, seasons):
            raise ImportError("nfl_data_py not available")
    
    nfl = MockNFLModule()
    NFL_DATA_PY_AVAILABLE = False
    logger.warning("nfl_data_py not available. Some functionality will be limited.")


@dataclass
class DataFetchConfig:
    """Configuration for data fetching operations."""
    max_retries: int = 3
    timeout_seconds: int = 300
    cache_enabled: bool = True
    batch_size: int = 1000
    rate_limit_delay: float = 0.1


class NFLDataClient:
    """Client for fetching NFL data using nfl_data_py library.
    
    This class provides a unified interface for accessing various NFL datasets
    including games, plays, players, and team information.
    """
    
    def __init__(self, config: Optional[DataFetchConfig] = None):
        """Initialize NFL data client.
        
        Args:
            config: Configuration for data fetching
        """
        self.config = config or DataFetchConfig()
        self._cache: Dict[str, Any] = {} if self.config.cache_enabled else {}
        logger.info(f"Initialized NFLDataClient with config: {self.config}")
    
    def fetch_teams(self) -> pd.DataFrame:
        """Fetch NFL teams data.
        
        Returns:
            DataFrame with team information
        """
        if not NFL_DATA_PY_AVAILABLE:
            raise ImportError("nfl_data_py is not available. Please install it to use this functionality.")
        
        cache_key = "teams"
        if self.config.cache_enabled and cache_key in self._cache:
            logger.info("Returning cached teams data")
            return self._cache[cache_key]
        
        try:
            logger.info("Fetching teams data from nfl_data_py")
            teams_df = nfl.import_team_desc()
            
            if self.config.cache_enabled:
                self._cache[cache_key] = teams_df
            
            logger.info(f"Successfully fetched {len(teams_df)} teams")
            return teams_df
            
        except Exception as e:
            logger.error(f"Failed to fetch teams data: {e}")
            raise
    
    def fetch_games(self, seasons: List[int]) -> pd.DataFrame:
        """Fetch NFL games data for specified seasons.
        
        Args:
            seasons: List of seasons to fetch (e.g., [2023, 2024])
            
        Returns:
            DataFrame with game information
        """
        if not NFL_DATA_PY_AVAILABLE:
            raise ImportError("nfl_data_py is not available. Please install it to use this functionality.")
        cache_key = f"games_{'-'.join(map(str, sorted(seasons)))}"
        if self.config.cache_enabled and cache_key in self._cache:
            logger.info("Returning cached games data")
            return self._cache[cache_key]
        
        try:
            logger.info(f"Fetching games data for seasons: {seasons}")
            games_df = nfl.import_schedules(seasons)
            
            if self.config.cache_enabled:
                self._cache[cache_key] = games_df
            
            logger.info(f"Successfully fetched {len(games_df)} games")
            return games_df
            
        except Exception as e:
            logger.error(f"Failed to fetch games data for seasons {seasons}: {e}")
            raise
    
    def fetch_plays(self, seasons: List[int], weeks: Optional[List[int]] = None) -> pd.DataFrame:
        """Fetch NFL play-by-play data for specified seasons and weeks.
        
        Args:
            seasons: List of seasons to fetch
            weeks: Optional list of weeks to fetch (if None, fetches all weeks)
            
        Returns:
            DataFrame with play-by-play data
        """
        # First try to load from extracted parquet files
        data_dir = Path("data")
        combined_data = []
        
        for season in seasons:
            parquet_file = data_dir / f"pbp_{season}.parquet"
            if parquet_file.exists():
                logger.info(f"Loading play-by-play data from {parquet_file}")
                season_data = pd.read_parquet(parquet_file)
                
                # Filter by weeks if specified
                if weeks:
                    season_data = season_data[season_data['week'].isin(weeks)]
                    logger.info(f"Filtered to weeks {weeks}: {len(season_data)} plays")
                
                combined_data.append(season_data)
                continue
        
        # If we got data from parquet files, return it
        if combined_data:
            result = pd.concat(combined_data, ignore_index=True)
            logger.info(f"Loaded {len(result)} plays from parquet files")
            return result
        
        # Fall back to nfl_data_py if available
        if not NFL_DATA_PY_AVAILABLE:
            logger.error("No parquet files found and nfl_data_py not available")
            logger.info("Try running: docker-compose -f docker-compose.nfl-data.yml --profile extract up")
            raise ImportError("No data source available. Please extract data using Docker or install nfl_data_py.")
        cache_key = f"plays_{'-'.join(map(str, sorted(seasons)))}_{weeks or 'all'}"
        if self.config.cache_enabled and cache_key in self._cache:
            logger.info("Returning cached plays data")
            return self._cache[cache_key]
        
        try:
            logger.info(f"Fetching play-by-play data for seasons: {seasons}, weeks: {weeks}")
            
            # Fetch play-by-play data
            if weeks:
                # Fetch specific weeks
                plays_df = pd.DataFrame()
                for season in seasons:
                    for week in weeks:
                        try:
                            week_data = nfl.import_pbp_data([season], downcast=False)
                            if not week_data.empty:
                                week_plays = week_data[week_data['week'] == week]
                                plays_df = pd.concat([plays_df, week_plays], ignore_index=True)
                        except Exception as e:
                            logger.warning(f"Failed to fetch week {week} of season {season}: {e}")
                            continue
            else:
                plays_df = nfl.import_pbp_data(seasons, downcast=False)
            
            if self.config.cache_enabled:
                self._cache[cache_key] = plays_df
            
            logger.info(f"Successfully fetched {len(plays_df)} plays")
            return plays_df
            
        except Exception as e:
            logger.error(f"Failed to fetch plays data for seasons {seasons}: {e}")
            raise
    
    def fetch_players(self, seasons: Optional[List[int]] = None) -> pd.DataFrame:
        """Fetch NFL players data with comprehensive position information.
        
        Args:
            seasons: Optional list of seasons (if None, fetches current roster)
            
        Returns:
            DataFrame with player information including positions
        """
        if not NFL_DATA_PY_AVAILABLE:
            raise ImportError("nfl_data_py is not available. Please install it to use this functionality.")
        cache_key = f"players_{seasons or 'current'}"
        if self.config.cache_enabled and cache_key in self._cache:
            logger.info("Returning cached players data")
            return self._cache[cache_key]
        
        try:
            # Strategy: Use seasonal rosters as primary source for position data
            # This provides the most complete and accurate position information
            logger.info("Fetching comprehensive player data with positions...")
            
            if seasons is None:
                seasons = [2024]  # Default to current season for roster data
            
            # Start with seasonal rosters (has position data)
            all_rosters = pd.DataFrame()
            for season in seasons:
                try:
                    logger.info(f"Fetching roster data for season {season}...")
                    season_rosters = nfl.import_seasonal_rosters([season])
                    if not season_rosters.empty:
                        season_rosters['season'] = season
                        all_rosters = pd.concat([all_rosters, season_rosters], ignore_index=True)
                        logger.info(f"Added {len(season_rosters)} roster records for season {season}")
                except Exception as e:
                    logger.warning(f"Failed to fetch roster for season {season}: {e}")
                    continue
            
            if all_rosters.empty:
                logger.warning("No roster data available, falling back to basic player data")
                # Fallback to basic player data
                players_df = nfl.import_players()
                logger.info(f"Fetched {len(players_df)} players from import_players()")
                
                if self.config.cache_enabled:
                    self._cache[cache_key] = players_df
                return players_df
            
            # Get most recent roster info for each player (latest season)
            logger.info("Processing roster data to get latest player information...")
            latest_rosters = (all_rosters
                            .sort_values(['season'], ascending=False)
                            .groupby('player_name')
                            .first()
                            .reset_index())
            
            logger.info(f"Processed roster data: {len(latest_rosters)} unique players")
            
            # Get base player information for additional fields
            try:
                logger.info("Fetching base player information...")
                players_df = nfl.import_players()
                logger.info(f"Fetched {len(players_df)} base player records")
                
                # Merge roster data (with positions) with player data (with additional info)
                # Use outer join to keep all players with position data
                merged_df = latest_rosters.merge(
                    players_df,
                    left_on='player_name',
                    right_on='display_name',
                    how='left',
                    suffixes=('_roster', '_player')
                )
                
                # Prioritize roster data for key fields
                merged_df['position'] = merged_df.get('position_roster', merged_df.get('position_player'))
                merged_df['team'] = merged_df.get('team_roster', merged_df.get('team_player'))
                merged_df['jersey_number'] = merged_df.get('jersey_number_roster', merged_df.get('jersey_number_player'))
                
                # Use player data for extended info
                for col in ['gsis_id', 'height', 'weight', 'birth_date', 'college', 'draft_year', 'draft_round', 'draft_pick']:
                    if col in players_df.columns:
                        merged_df[col] = merged_df.get(f'{col}_player', merged_df.get(col))
                
                # Use display_name as the canonical full name
                merged_df['display_name'] = merged_df.get('display_name', merged_df.get('player_name'))
                
                position_count = merged_df['position'].notna().sum()
                logger.info(f"Successfully merged data: {len(merged_df)} players, {position_count} with positions")
                
                final_df = merged_df
                
            except Exception as e:
                logger.warning(f"Failed to merge with base player data: {e}")
                logger.info("Using roster data only")
                final_df = latest_rosters
            
            if self.config.cache_enabled:
                self._cache[cache_key] = final_df
            
            logger.info(f"Successfully fetched {len(final_df)} players with comprehensive data")
            return final_df
            
        except Exception as e:
            logger.error(f"Failed to fetch players data: {e}")
            raise
    
    def fetch_season_games(self, season: int, season_type: str = "REG") -> pd.DataFrame:
        """Fetch games for a specific season and season type.
        
        Args:
            season: Season year
            season_type: Season type ('REG', 'POST', 'PRE')
            
        Returns:
            DataFrame with games for the specified season/type
        """
        try:
            logger.info(f"Fetching {season_type} games for season {season}")
            all_games = self.fetch_games([season])
            
            if not all_games.empty:
                season_games = all_games[all_games['season_type'] == season_type]
                logger.info(f"Filtered to {len(season_games)} {season_type} games")
                return season_games
            else:
                logger.warning(f"No games found for season {season}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Failed to fetch {season_type} games for season {season}: {e}")
            raise
    
    def fetch_recent_games(self, days: int = 7) -> pd.DataFrame:
        """Fetch games from recent days.
        
        Args:
            days: Number of recent days to fetch
            
        Returns:
            DataFrame with recent games
        """
        try:
            current_year = datetime.now().year
            logger.info(f"Fetching games from last {days} days")
            
            # Get current season games
            current_games = self.fetch_games([current_year])
            
            if not current_games.empty and 'gameday' in current_games.columns:
                # Filter to recent games
                current_games['gameday'] = pd.to_datetime(current_games['gameday'])
                cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days)
                recent_games = current_games[current_games['gameday'] >= cutoff_date]
                
                logger.info(f"Found {len(recent_games)} games in last {days} days")
                return recent_games
            else:
                logger.warning("No gameday column found or no games available")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Failed to fetch recent games: {e}")
            raise
    
    def fetch_team_games(self, team: str, season: int) -> pd.DataFrame:
        """Fetch games for a specific team and season.
        
        Args:
            team: Team abbreviation (e.g., 'SF', 'KC')
            season: Season year
            
        Returns:
            DataFrame with team's games
        """
        try:
            logger.info(f"Fetching games for team {team} in season {season}")
            all_games = self.fetch_games([season])
            
            if not all_games.empty:
                team_games = all_games[
                    (all_games['home_team'] == team) | 
                    (all_games['away_team'] == team)
                ]
                logger.info(f"Found {len(team_games)} games for team {team}")
                return team_games
            else:
                logger.warning(f"No games found for season {season}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Failed to fetch games for team {team}: {e}")
            raise
    
    def get_available_seasons(self) -> List[int]:
        """Get list of available seasons in nfl_data_py.
        
        Returns:
            List of available season years
        """
        try:
            # nfl_data_py typically supports 1999-current
            current_year = datetime.now().year
            # Check if we're in the season (starts around September)
            if datetime.now().month >= 9:
                latest_season = current_year
            else:
                latest_season = current_year - 1
            
            # NFL data typically goes back to 1999
            seasons = list(range(1999, latest_season + 1))
            logger.info(f"Available seasons: {seasons[0]}-{seasons[-1]}")
            return seasons
            
        except Exception as e:
            logger.error(f"Failed to get available seasons: {e}")
            return []
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        if self.config.cache_enabled:
            self._cache.clear()
            logger.info("Cleared data cache")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached data.
        
        Returns:
            Dictionary with cache information
        """
        if not self.config.cache_enabled:
            return {"cache_enabled": False, "cached_items": 0}
        
        cache_info = {
            "cache_enabled": True,
            "cached_items": len(self._cache),
            "cache_keys": list(self._cache.keys())
        }
        
        # Add memory usage estimate if possible
        try:
            total_size = 0
            for key, df in self._cache.items():
                if isinstance(df, pd.DataFrame):
                    total_size += df.memory_usage(deep=True).sum()
            cache_info["estimated_memory_mb"] = total_size / (1024 * 1024)
        except Exception:
            cache_info["estimated_memory_mb"] = "unknown"
        
        return cache_info