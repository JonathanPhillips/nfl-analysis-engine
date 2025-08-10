"""Direct nflfastR data client - bypasses nfl_data_py installation issues."""

import logging
import pandas as pd
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NFLFastRConfig:
    """Configuration for nflfastR data client."""
    base_url: str = "https://github.com/nflverse/nflverse-data/releases/download"
    cache_dir: str = "data/cache"
    timeout_seconds: int = 300
    max_retries: int = 3
    
    # Alternative base URLs to try
    alt_urls: List[str] = None
    
    def __post_init__(self):
        if self.alt_urls is None:
            self.alt_urls = [
                "https://github.com/nflverse/nfldata/releases/download",
                "https://raw.githubusercontent.com/nflverse/nflverse-data/master/data",
                "https://github.com/nflverse/nflverse-data/raw/master/data"
            ]


class NFLFastRClient:
    """Direct client for nflfastR data without nfl_data_py dependency.
    
    This client downloads parquet files directly from the nflfastR GitHub releases,
    providing the same data as nfl_data_py but without Python compilation issues.
    """
    
    def __init__(self, config: Optional[NFLFastRConfig] = None):
        """Initialize nflfastR client.
        
        Args:
            config: Configuration for data fetching
        """
        self.config = config or NFLFastRConfig()
        self.cache_dir = Path(self.config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized NFLFastRClient with cache: {self.cache_dir}")
    
    def _download_file(self, url: str, local_path: Path) -> bool:
        """Download file with retry logic.
        
        Args:
            url: URL to download
            local_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.config.max_retries):
            try:
                logger.info(f"Downloading {url} (attempt {attempt + 1})")
                response = requests.get(url, timeout=self.config.timeout_seconds)
                response.raise_for_status()
                
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Successfully downloaded {local_path}")
                return True
                
            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if attempt == self.config.max_retries - 1:
                    logger.error(f"Failed to download {url} after {self.config.max_retries} attempts")
                    return False
        
        return False
    
    def fetch_play_by_play(self, seasons: List[int], force_download: bool = False) -> pd.DataFrame:
        """Fetch play-by-play data for specified seasons.
        
        Args:
            seasons: List of seasons to fetch (e.g., [2023, 2024])
            force_download: Force re-download even if cached
            
        Returns:
            DataFrame with play-by-play data
        """
        all_data = []
        
        for season in seasons:
            cache_file = self.cache_dir / f"play_by_play_{season}.parquet"
            
            # Check if we need to download
            if not cache_file.exists() or force_download:
                url = f"{self.config.base_url}/pbp/play_by_play_{season}.parquet"
                if not self._download_file(url, cache_file):
                    logger.error(f"Failed to download play-by-play data for {season}")
                    continue
            
            # Load the data
            try:
                season_data = pd.read_parquet(cache_file)
                logger.info(f"Loaded {len(season_data)} plays for season {season}")
                all_data.append(season_data)
            except Exception as e:
                logger.error(f"Failed to load play-by-play data for {season}: {e}")
                continue
        
        if not all_data:
            logger.warning("No play-by-play data loaded")
            return pd.DataFrame()
        
        combined_data = pd.concat(all_data, ignore_index=True)
        logger.info(f"Combined data: {len(combined_data)} total plays")
        
        return combined_data
    
    def fetch_games(self, seasons: List[int], force_download: bool = False) -> pd.DataFrame:
        """Fetch schedule/games data for specified seasons.
        
        Args:
            seasons: List of seasons to fetch
            force_download: Force re-download even if cached
            
        Returns:
            DataFrame with games data
        """
        all_data = []
        
        for season in seasons:
            cache_file = self.cache_dir / f"schedules_{season}.parquet"
            
            if not cache_file.exists() or force_download:
                url = f"{self.config.base_url}/schedules/schedules_{season}.parquet"
                if not self._download_file(url, cache_file):
                    logger.error(f"Failed to download schedule data for {season}")
                    continue
            
            try:
                season_data = pd.read_parquet(cache_file)
                logger.info(f"Loaded {len(season_data)} games for season {season}")
                all_data.append(season_data)
            except Exception as e:
                logger.error(f"Failed to load schedule data for {season}: {e}")
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        combined_data = pd.concat(all_data, ignore_index=True)
        logger.info(f"Combined games data: {len(combined_data)} total games")
        
        return combined_data
    
    def fetch_rosters(self, seasons: List[int], force_download: bool = False) -> pd.DataFrame:
        """Fetch roster data for specified seasons.
        
        Args:
            seasons: List of seasons to fetch
            force_download: Force re-download even if cached
            
        Returns:
            DataFrame with roster data
        """
        all_data = []
        
        for season in seasons:
            cache_file = self.cache_dir / f"rosters_{season}.parquet"
            
            if not cache_file.exists() or force_download:
                url = f"{self.config.base_url}/rosters/rosters_{season}.parquet"
                if not self._download_file(url, cache_file):
                    logger.error(f"Failed to download roster data for {season}")
                    continue
            
            try:
                season_data = pd.read_parquet(cache_file)
                logger.info(f"Loaded {len(season_data)} roster entries for season {season}")
                all_data.append(season_data)
            except Exception as e:
                logger.error(f"Failed to load roster data for {season}: {e}")
                continue
        
        if not all_data:
            return pd.DataFrame()
        
        combined_data = pd.concat(all_data, ignore_index=True)
        logger.info(f"Combined roster data: {len(combined_data)} total entries")
        
        return combined_data
    
    def get_sample_data(self, season: int = 2024, weeks: List[int] = [1, 2]) -> pd.DataFrame:
        """Get sample play-by-play data for testing.
        
        Args:
            season: Season to fetch
            weeks: List of weeks to include in sample
            
        Returns:
            DataFrame with sample play-by-play data
        """
        full_data = self.fetch_play_by_play([season])
        
        if full_data.empty:
            return pd.DataFrame()
        
        # Filter to specific weeks
        sample_data = full_data[full_data['week'].isin(weeks)]
        logger.info(f"Sample data: {len(sample_data)} plays from weeks {weeks}")
        
        return sample_data
    
    def analyze_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data quality for League Leaders validation.
        
        Args:
            data: Play-by-play DataFrame to analyze
            
        Returns:
            Dictionary with data quality metrics
        """
        if data.empty:
            return {"error": "No data to analyze"}
        
        analysis = {
            "total_plays": len(data),
            "date_range": {
                "min": data['game_date'].min() if 'game_date' in data.columns else None,
                "max": data['game_date'].max() if 'game_date' in data.columns else None
            },
            "unique_games": data['game_id'].nunique() if 'game_id' in data.columns else 0,
            "unique_teams": set(),
            "play_types": {},
            "key_players": {}
        }
        
        # Team analysis
        if 'posteam' in data.columns:
            analysis["unique_teams"] = sorted(data['posteam'].dropna().unique())
        
        # Play type breakdown
        if 'play_type' in data.columns:
            analysis["play_types"] = data['play_type'].value_counts().to_dict()
        
        # Key player analysis for League Leaders validation
        key_stats = {}
        
        # QB passing attempts
        if 'passer_player_name' in data.columns:
            qb_attempts = data[data['pass'] == 1]['passer_player_name'].value_counts()
            key_stats['qb_attempts'] = qb_attempts.head(10).to_dict()
        
        # RB carries
        if 'rusher_player_name' in data.columns:
            rb_carries = data[data['rush'] == 1]['rusher_player_name'].value_counts()
            key_stats['rb_carries'] = rb_carries.head(10).to_dict()
        
        # WR targets
        if 'receiver_player_name' in data.columns:
            wr_targets = data[data['pass'] == 1]['receiver_player_name'].value_counts()
            key_stats['wr_targets'] = wr_targets.head(10).to_dict()
        
        analysis["key_players"] = key_stats
        
        return analysis
    
    def validate_league_leaders_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate data contains legitimate starters for League Leaders system.
        
        Args:
            data: Play-by-play DataFrame
            
        Returns:
            Validation results with recommendations
        """
        validation = {
            "meets_minimum_thresholds": False,
            "legitimate_starters_found": [],
            "data_quality_score": 0.0,
            "recommendations": []
        }
        
        if data.empty:
            validation["recommendations"].append("No data available - download required")
            return validation
        
        # Known legitimate starters for validation
        expected_qbs = {"J.Allen", "L.Jackson", "P.Mahomes", "J.Burrow", "A.Rodgers"}
        expected_rbs = {"D.Henry", "C.McCaffrey", "S.Barkley", "J.Jacobs", "A.Jones"}
        expected_wrs = {"T.Hill", "D.Adams", "C.Kupp", "S.Diggs", "M.Evans"}
        
        # Check QB data
        if 'passer_player_name' in data.columns:
            qb_attempts = data[data['pass'] == 1]['passer_player_name'].value_counts()
            top_qbs = set(qb_attempts.head(10).index)
            qb_matches = top_qbs.intersection(expected_qbs)
            validation["legitimate_starters_found"].extend([f"QB: {qb}" for qb in qb_matches])
            
            # Check minimum threshold (150+ attempts)
            qualified_qbs = qb_attempts[qb_attempts >= 150]
            if len(qualified_qbs) >= 20:  # Expect ~32 starting QBs
                validation["meets_minimum_thresholds"] = True
        
        # Check RB data
        if 'rusher_player_name' in data.columns:
            rb_carries = data[data['rush'] == 1]['rusher_player_name'].value_counts()
            top_rbs = set(rb_carries.head(20).index)
            rb_matches = top_rbs.intersection(expected_rbs)
            validation["legitimate_starters_found"].extend([f"RB: {rb}" for rb in rb_matches])
        
        # Check WR data
        if 'receiver_player_name' in data.columns:
            wr_targets = data[data['pass'] == 1]['receiver_player_name'].value_counts()
            top_wrs = set(wr_targets.head(30).index)
            wr_matches = top_wrs.intersection(expected_wrs)
            validation["legitimate_starters_found"].extend([f"WR: {wr}" for wr in wr_matches])
        
        # Calculate quality score
        total_matches = len(validation["legitimate_starters_found"])
        max_possible = len(expected_qbs) + len(expected_rbs) + len(expected_wrs)
        validation["data_quality_score"] = total_matches / max_possible
        
        # Generate recommendations
        if validation["data_quality_score"] > 0.7:
            validation["recommendations"].append("Data quality is excellent for League Leaders")
        elif validation["data_quality_score"] > 0.4:
            validation["recommendations"].append("Data quality is good - minor gaps in coverage")
        else:
            validation["recommendations"].append("Data quality is poor - consider alternative source")
        
        if not validation["meets_minimum_thresholds"]:
            validation["recommendations"].append("Insufficient data for minimum thresholds - need full season")
        
        return validation
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached files.
        
        Returns:
            Dictionary with cache information
        """
        cache_files = list(self.cache_dir.glob("*.parquet"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            "cache_dir": str(self.cache_dir),
            "cached_files": len(cache_files),
            "total_size_mb": total_size / (1024 * 1024),
            "files": [f.name for f in cache_files]
        }