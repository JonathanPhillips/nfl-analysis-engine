#!/usr/bin/env python3
"""
Script to diagnose and fix position data issues in NFL analysis engine.

This script will:
1. Analyze the current state of position data in the database
2. Test nfl_data_py data sources to identify position availability
3. Fix the data loading pipeline to properly capture positions
4. Backfill missing position data for existing players
"""

import os
import sys
import logging
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data.nfl_data_client import NFLDataClient
from data.data_mapper import DataMapper
from models.player import PlayerModel, PlayerCreate
from database.config import get_database_url

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def analyze_current_position_data(session) -> Dict[str, any]:
    """Analyze the current state of position data in the database."""
    logger.info("Analyzing current position data in database...")
    
    try:
        # Get total player count
        total_players = session.execute(text("SELECT COUNT(*) FROM players")).scalar()
        
        # Get count of players with positions
        players_with_position = session.execute(
            text("SELECT COUNT(*) FROM players WHERE position IS NOT NULL AND position != ''")
        ).scalar()
        
        # Get count of players without positions
        players_without_position = total_players - players_with_position
        
        # Get position distribution
        position_counts = session.execute(
            text("""
                SELECT position, COUNT(*) as count 
                FROM players 
                WHERE position IS NOT NULL AND position != ''
                GROUP BY position 
                ORDER BY count DESC
            """)
        ).fetchall()
        
        # Get sample of players missing positions
        missing_position_sample = session.execute(
            text("""
                SELECT player_id, full_name, team_abbr 
                FROM players 
                WHERE position IS NULL OR position = ''
                LIMIT 10
            """)
        ).fetchall()
        
        stats = {
            'total_players': total_players,
            'players_with_position': players_with_position,
            'players_without_position': players_without_position,
            'percentage_missing': (players_without_position / total_players * 100) if total_players > 0 else 0,
            'position_distribution': position_counts,
            'missing_position_sample': missing_position_sample
        }
        
        logger.info(f"Database Analysis Results:")
        logger.info(f"  Total players: {stats['total_players']}")
        logger.info(f"  Players with position: {stats['players_with_position']}")
        logger.info(f"  Players without position: {stats['players_without_position']}")
        logger.info(f"  Percentage missing positions: {stats['percentage_missing']:.1f}%")
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to analyze position data: {e}")
        raise


def test_nfl_data_sources():
    """Test various nfl_data_py sources to identify where position data is available."""
    logger.info("Testing nfl_data_py data sources for position information...")
    
    client = NFLDataClient()
    
    try:
        # Test 1: import_players() - basic player info
        logger.info("Testing nfl.import_players()...")
        import nfl_data_py as nfl
        
        players_df = nfl.import_players()
        logger.info(f"import_players() returned {len(players_df)} players")
        logger.info(f"Columns: {list(players_df.columns)}")
        
        # Check if position data exists
        if 'position' in players_df.columns:
            position_count = players_df['position'].notna().sum()
            logger.info(f"Players with position data: {position_count} out of {len(players_df)}")
        else:
            logger.warning("No 'position' column in import_players()")
        
        # Test 2: import_seasonal_rosters() - roster data with positions
        logger.info("\nTesting nfl.import_seasonal_rosters() for 2024...")
        rosters_df = nfl.import_seasonal_rosters([2024])
        logger.info(f"import_seasonal_rosters([2024]) returned {len(rosters_df)} records")
        logger.info(f"Columns: {list(rosters_df.columns)}")
        
        if 'position' in rosters_df.columns:
            position_count = rosters_df['position'].notna().sum()
            unique_positions = rosters_df['position'].dropna().unique()
            logger.info(f"Roster records with position: {position_count} out of {len(rosters_df)}")
            logger.info(f"Unique positions: {sorted(unique_positions)}")
            
            # Sample data
            sample = rosters_df[['player_name', 'team', 'position']].head(10)
            logger.info(f"Sample roster data:\n{sample}")
        
        # Test 3: import_rosters() - current rosters
        logger.info("\nTesting nfl.import_rosters()...")
        current_rosters = nfl.import_rosters()
        logger.info(f"import_rosters() returned {len(current_rosters)} records")
        logger.info(f"Columns: {list(current_rosters.columns)}")
        
        if 'position' in current_rosters.columns:
            position_count = current_rosters['position'].notna().sum()
            unique_positions = current_rosters['position'].dropna().unique()
            logger.info(f"Current roster records with position: {position_count} out of {len(current_rosters)}")
            logger.info(f"Unique positions: {sorted(unique_positions)}")
        
        return {
            'players_df': players_df,
            'rosters_df': rosters_df,
            'current_rosters': current_rosters
        }
        
    except Exception as e:
        logger.error(f"Failed to test nfl_data_py sources: {e}")
        raise


def create_improved_player_mapper():
    """Create an improved player data mapping strategy."""
    logger.info("Creating improved player data mapping strategy...")
    
    try:
        import nfl_data_py as nfl
        
        # Strategy 1: Use seasonal rosters as primary source for position data
        # This typically has the most complete and accurate position information
        def fetch_players_with_positions(seasons: List[int] = None) -> pd.DataFrame:
            if seasons is None:
                seasons = [2024]  # Default to current season
            
            logger.info(f"Fetching comprehensive player data for seasons: {seasons}")
            
            # Get basic player info
            players_df = nfl.import_players()
            logger.info(f"Base player data: {len(players_df)} players")
            
            # Get seasonal rosters for position data
            all_rosters = pd.DataFrame()
            for season in seasons:
                try:
                    season_rosters = nfl.import_seasonal_rosters([season])
                    season_rosters['season'] = season
                    all_rosters = pd.concat([all_rosters, season_rosters], ignore_index=True)
                    logger.info(f"Added {len(season_rosters)} roster records for season {season}")
                except Exception as e:
                    logger.warning(f"Failed to fetch rosters for season {season}: {e}")
            
            if all_rosters.empty:
                logger.warning("No roster data available, using player data only")
                return players_df
            
            # Get the most recent roster entry for each player
            # Sort by season descending to get latest information
            latest_rosters = (all_rosters
                            .sort_values(['season'], ascending=False)
                            .groupby('player_name')
                            .first()
                            .reset_index())
            
            logger.info(f"Latest roster data: {len(latest_rosters)} unique players")
            
            # Merge player data with roster data
            # Use multiple join strategies to maximize matches
            merged_df = players_df.copy()
            
            # Strategy A: Join on display_name = player_name
            merge1 = merged_df.merge(
                latest_rosters[['player_name', 'team', 'position', 'jersey_number']],
                left_on='display_name',
                right_on='player_name',
                how='left',
                suffixes=('', '_roster')
            )
            
            # Strategy B: For unmatched players, try fuzzy matching or alternate name formats
            unmatched = merge1[merge1['position'].isna()]
            if len(unmatched) > 0:
                logger.info(f"Attempting to match {len(unmatched)} unmatched players...")
                
                # Try matching on first_name + last_name
                if 'first_name' in merged_df.columns and 'last_name' in merged_df.columns:
                    unmatched_with_names = unmatched[
                        unmatched['first_name'].notna() & unmatched['last_name'].notna()
                    ].copy()
                    
                    if len(unmatched_with_names) > 0:
                        unmatched_with_names['constructed_name'] = (
                            unmatched_with_names['first_name'] + ' ' + unmatched_with_names['last_name']
                        )
                        
                        additional_matches = unmatched_with_names.merge(
                            latest_rosters[['player_name', 'team', 'position', 'jersey_number']],
                            left_on='constructed_name',
                            right_on='player_name',
                            how='inner',
                            suffixes=('', '_roster2')
                        )
                        
                        logger.info(f"Found {len(additional_matches)} additional matches using name construction")
            
            # Count successful matches
            position_matches = merge1['position'].notna().sum()
            logger.info(f"Successfully matched position data for {position_matches} out of {len(merge1)} players")
            
            return merge1
        
        return fetch_players_with_positions
        
    except Exception as e:
        logger.error(f"Failed to create improved mapper: {e}")
        raise


def update_data_mapper():
    """Update the data_mapper.py to use improved position data loading."""
    logger.info("Updating data mapper for better position data handling...")
    
    # The fix involves modifying the map_players_data method to prioritize roster data
    updated_mapping_code = '''
    def map_players_data_improved(self, players_df: pd.DataFrame) -> List[PlayerCreate]:
        """Map nfl_data_py players data to PlayerCreate models with improved position handling.
        
        Args:
            players_df: DataFrame from improved player fetching (includes roster data)
            
        Returns:
            List of PlayerCreate models
        """
        players = []
        
        for _, row in players_df.iterrows():
            try:
                # Use gsis_id as player_id (primary identifier)
                player_id = str(row.get('gsis_id', '')).strip()
                if not player_id:
                    continue
                
                # Get display_name as full_name
                full_name = str(row.get('display_name', '')).strip()
                if not full_name:
                    continue
                
                player_data = {
                    'player_id': player_id,
                    'full_name': full_name
                }
                
                # IMPROVED POSITION MAPPING
                # Priority order: roster position > player position > NGS position
                position = None
                
                # Try roster position first (most reliable)
                if 'position' in row and pd.notna(row['position']):
                    position = str(row['position']).strip().upper()
                
                # Fallback to other position columns if needed
                if not position:
                    for pos_col in ['position_x', 'position_y', 'ngs_position']:
                        if pos_col in row and pd.notna(row[pos_col]):
                            position = str(row[pos_col]).strip().upper()
                            break
                
                if position:
                    player_data['position'] = position
                
                # IMPROVED TEAM MAPPING
                team_abbr = None
                # Try roster team first
                if 'team' in row and pd.notna(row['team']):
                    team_abbr = str(row['team']).strip().upper()
                
                # Fallback to other team columns
                if not team_abbr:
                    for team_col in ['latest_team', 'team_roster']:
                        if team_col in row and pd.notna(row[team_col]):
                            team_abbr = str(row[team_col]).strip().upper()
                            break
                
                # Apply team mapping for old abbreviations
                team_mapping = {
                    'LA': 'LAR', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'
                }
                
                if team_abbr and team_abbr not in ['UNK', 'NA']:
                    if team_abbr in team_mapping:
                        team_abbr = team_mapping[team_abbr]
                    player_data['team_abbr'] = team_abbr
                
                # IMPROVED JERSEY NUMBER MAPPING
                jersey_number = None
                if 'jersey_number' in row and pd.notna(row['jersey_number']):
                    try:
                        jersey = int(row['jersey_number'])
                        if 0 <= jersey <= 99:
                            player_data['jersey_number'] = jersey
                    except (ValueError, TypeError):
                        pass
                
                # ... rest of the mapping logic remains the same ...
                
                player = PlayerCreate(**player_data)
                players.append(player)
                
            except Exception as e:
                logger.warning(f"Failed to map player row: {e}")
                continue
        
        logger.info(f"Mapped {len(players)} players with improved position data")
        return players
    '''
    
    logger.info("Improved mapping strategy defined")
    return updated_mapping_code


def fix_position_data(session):
    """Execute the position data fix."""
    logger.info("Starting position data fix process...")
    
    try:
        # Step 1: Test data sources
        data_sources = test_nfl_data_sources()
        
        # Step 2: Create improved fetcher
        improved_fetcher = create_improved_player_mapper()
        
        # Step 3: Fetch improved player data
        logger.info("Fetching improved player data...")
        seasons = [2024, 2023]  # Get recent seasons for best data coverage
        improved_players_df = improved_fetcher(seasons)
        
        # Step 4: Map to our models
        mapper = DataMapper()
        
        # Create a temporary improved mapping method
        def map_players_improved(df):
            players = []
            success_count = 0
            position_count = 0
            
            for _, row in df.iterrows():
                try:
                    player_id = str(row.get('gsis_id', '')).strip()
                    if not player_id:
                        continue
                    
                    full_name = str(row.get('display_name', '')).strip()
                    if not full_name:
                        continue
                    
                    player_data = {
                        'player_id': player_id,
                        'full_name': full_name
                    }
                    
                    # Improved position mapping
                    position = None
                    if 'position' in row and pd.notna(row['position']):
                        position = str(row['position']).strip().upper()
                        position_count += 1
                    
                    if position:
                        player_data['position'] = position
                    
                    # Team mapping (with roster data preference)
                    team_abbr = None
                    if 'team' in row and pd.notna(row['team']):
                        team_abbr = str(row['team']).strip().upper()
                    elif 'latest_team' in row and pd.notna(row['latest_team']):
                        team_abbr = str(row['latest_team']).strip().upper()
                    
                    if team_abbr and team_abbr not in ['UNK', 'NA']:
                        # Apply team mapping
                        team_mapping = {'LA': 'LAR', 'OAK': 'LV', 'SD': 'LAC', 'STL': 'LAR'}
                        if team_abbr in team_mapping:
                            team_abbr = team_mapping[team_abbr]
                        player_data['team_abbr'] = team_abbr
                    
                    # Jersey number
                    if 'jersey_number' in row and pd.notna(row['jersey_number']):
                        try:
                            jersey = int(row['jersey_number'])
                            if 0 <= jersey <= 99:
                                player_data['jersey_number'] = jersey
                        except (ValueError, TypeError):
                            pass
                    
                    # Add other fields as available
                    optional_fields = {
                        'height': lambda x: int(x) if pd.notna(x) and 60 <= int(x) <= 84 else None,
                        'weight': lambda x: int(x) if pd.notna(x) and 150 <= int(x) <= 400 else None,
                        'rookie_year': lambda x: int(x) if pd.notna(x) and 1920 <= int(x) <= datetime.now().year else None,
                        'college': lambda x: str(x).strip() if pd.notna(x) else None,
                    }
                    
                    for field, validator in optional_fields.items():
                        if field in row:
                            try:
                                value = validator(row[field])
                                if value is not None:
                                    player_data[field] = value
                            except (ValueError, TypeError):
                                pass
                    
                    player = PlayerCreate(**player_data)
                    players.append(player)
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to map player row: {e}")
                    continue
            
            logger.info(f"Successfully mapped {success_count} players, {position_count} with positions")
            return players
        
        # Apply improved mapping
        improved_players = map_players_improved(improved_players_df)
        
        # Step 5: Update database with improved data
        logger.info(f"Updating database with {len(improved_players)} players...")
        
        updated_count = 0
        for player_data in improved_players:
            try:
                # Check if player exists
                existing_player = session.query(PlayerModel).filter(
                    PlayerModel.player_id == player_data.player_id
                ).first()
                
                if existing_player:
                    # Update existing player with new data
                    updated = False
                    
                    # Update position if we have better data
                    if player_data.position and (not existing_player.position or existing_player.position != player_data.position):
                        existing_player.position = player_data.position
                        updated = True
                    
                    # Update team if we have data
                    if player_data.team_abbr and (not existing_player.team_abbr or existing_player.team_abbr != player_data.team_abbr):
                        existing_player.team_abbr = player_data.team_abbr
                        updated = True
                    
                    # Update other fields as needed
                    for field in ['jersey_number', 'height', 'weight', 'rookie_year', 'college']:
                        new_value = getattr(player_data, field, None)
                        existing_value = getattr(existing_player, field, None)
                        
                        if new_value is not None and (existing_value is None or existing_value != new_value):
                            setattr(existing_player, field, new_value)
                            updated = True
                    
                    if updated:
                        updated_count += 1
                else:
                    # Create new player
                    new_player = PlayerModel(
                        player_id=player_data.player_id,
                        full_name=player_data.full_name,
                        position=player_data.position,
                        team_abbr=player_data.team_abbr,
                        jersey_number=getattr(player_data, 'jersey_number', None),
                        height=getattr(player_data, 'height', None),
                        weight=getattr(player_data, 'weight', None),
                        rookie_year=getattr(player_data, 'rookie_year', None),
                        college=getattr(player_data, 'college', None),
                    )
                    session.add(new_player)
                    updated_count += 1
            
            except Exception as e:
                logger.warning(f"Failed to update player {player_data.player_id}: {e}")
                continue
        
        # Commit changes
        session.commit()
        logger.info(f"Successfully updated {updated_count} players")
        
        return {
            'total_processed': len(improved_players),
            'updated_count': updated_count,
            'improved_players_df': improved_players_df
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to fix position data: {e}")
        raise


def main():
    """Main execution function."""
    logger.info("Starting NFL Position Data Fix Script")
    
    try:
        # Setup database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Step 1: Analyze current state
        logger.info("\n" + "="*50)
        logger.info("STEP 1: ANALYZING CURRENT POSITION DATA")
        logger.info("="*50)
        current_stats = analyze_current_position_data(session)
        
        # Step 2: Test data sources
        logger.info("\n" + "="*50)
        logger.info("STEP 2: TESTING NFL DATA SOURCES")
        logger.info("="*50)
        data_sources = test_nfl_data_sources()
        
        # Step 3: Fix position data
        logger.info("\n" + "="*50)
        logger.info("STEP 3: EXECUTING POSITION DATA FIX")
        logger.info("="*50)
        fix_results = fix_position_data(session)
        
        # Step 4: Analyze results
        logger.info("\n" + "="*50)
        logger.info("STEP 4: ANALYZING RESULTS")
        logger.info("="*50)
        final_stats = analyze_current_position_data(session)
        
        # Summary
        logger.info("\n" + "="*50)
        logger.info("POSITION DATA FIX SUMMARY")
        logger.info("="*50)
        logger.info(f"Before fix:")
        logger.info(f"  Total players: {current_stats['total_players']}")
        logger.info(f"  Players with positions: {current_stats['players_with_position']}")
        logger.info(f"  Missing positions: {current_stats['percentage_missing']:.1f}%")
        
        logger.info(f"\nAfter fix:")
        logger.info(f"  Total players: {final_stats['total_players']}")
        logger.info(f"  Players with positions: {final_stats['players_with_position']}")
        logger.info(f"  Missing positions: {final_stats['percentage_missing']:.1f}%")
        
        improvement = current_stats['percentage_missing'] - final_stats['percentage_missing']
        logger.info(f"\nImprovement: {improvement:.1f} percentage points reduction in missing positions")
        
        session.close()
        logger.info("\nPosition data fix completed successfully!")
        
    except Exception as e:
        logger.error(f"Position data fix failed: {e}")
        if 'session' in locals():
            session.close()
        sys.exit(1)


if __name__ == "__main__":
    main()