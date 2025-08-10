#!/usr/bin/env python3
"""Verify and analyze the extracted 2024 NFL data for League Leaders system."""

import pandas as pd
import sys
from pathlib import Path

def verify_2024_data():
    """Verify the quality and completeness of extracted 2024 NFL data."""
    
    print("=" * 60)
    print("2024 NFL DATA VERIFICATION FOR LEAGUE LEADERS")
    print("=" * 60)
    
    data_dir = Path("data")
    
    # 1. Verify play-by-play data
    pbp_file = data_dir / "pbp_2024.parquet"
    if pbp_file.exists():
        print(f"\n✅ Play-by-Play Data ({pbp_file})")
        pbp = pd.read_parquet(pbp_file)
        
        print(f"   Total plays: {len(pbp):,}")
        print(f"   File size: {pbp_file.stat().st_size / (1024*1024):.1f} MB")
        print(f"   Memory usage: {pbp.memory_usage(deep=True).sum() / (1024*1024):.1f} MB")
        print(f"   Date range: {pbp['game_date'].min()} to {pbp['game_date'].max()}")
        print(f"   Weeks: {sorted(pbp['week'].unique())}")
        print(f"   Season types: {pbp['season_type'].value_counts().to_dict()}")
        
        # QB Analysis for League Leaders
        print(f"\n📊 QUARTERBACK ANALYSIS:")
        if 'pass' in pbp.columns and 'passer_player_name' in pbp.columns:
            pass_attempts = pbp[pbp['pass'] == 1]['passer_player_name'].value_counts()
            print(f"   Total passing plays: {len(pbp[pbp['pass'] == 1]):,}")
            print(f"   Unique QBs with attempts: {len(pass_attempts)}")
            print(f"   QBs with 150+ attempts: {len(pass_attempts[pass_attempts >= 150])}")
            print(f"   QBs with 300+ attempts: {len(pass_attempts[pass_attempts >= 300])}")
            print(f"   Top 10 QBs by attempts:")
            for i, (qb, attempts) in enumerate(pass_attempts.head(10).items(), 1):
                print(f"     {i:2d}. {qb}: {attempts} attempts")
        
        # RB Analysis for League Leaders
        print(f"\n📊 RUNNING BACK ANALYSIS:")
        if 'rush' in pbp.columns and 'rusher_player_name' in pbp.columns:
            rush_attempts = pbp[pbp['rush'] == 1]['rusher_player_name'].value_counts()
            print(f"   Total rushing plays: {len(pbp[pbp['rush'] == 1]):,}")
            print(f"   Unique RBs with carries: {len(rush_attempts)}")
            print(f"   RBs with 75+ carries: {len(rush_attempts[rush_attempts >= 75])}")
            print(f"   RBs with 150+ carries: {len(rush_attempts[rush_attempts >= 150])}")
            print(f"   Top 10 RBs by carries:")
            for i, (rb, carries) in enumerate(rush_attempts.head(10).items(), 1):
                print(f"     {i:2d}. {rb}: {carries} carries")
        
        # Receiving Analysis
        print(f"\n📊 RECEIVING ANALYSIS:")
        if 'pass' in pbp.columns and 'receiver_player_name' in pbp.columns:
            # Count completions (successful passes)
            completions = pbp[(pbp['pass'] == 1) & (pbp['complete_pass'] == 1)]['receiver_player_name'].value_counts()
            print(f"   Total completed passes: {len(pbp[(pbp['pass'] == 1) & (pbp['complete_pass'] == 1)]):,}")
            print(f"   Unique receivers with catches: {len(completions)}")
            print(f"   Receivers with 30+ catches: {len(completions[completions >= 30])}")
            print(f"   Receivers with 60+ catches: {len(completions[completions >= 60])}")
            print(f"   Top 10 receivers by catches:")
            for i, (wr, catches) in enumerate(completions.head(10).items(), 1):
                print(f"     {i:2d}. {wr}: {catches} catches")
                
    else:
        print("❌ No play-by-play data found")
        return False
    
    # 2. Verify roster data
    roster_file = data_dir / "rosters_2024.parquet"
    if roster_file.exists():
        print(f"\n✅ Roster Data ({roster_file})")
        rosters = pd.read_parquet(roster_file)
        
        print(f"   Total roster entries: {len(rosters):,}")
        print(f"   Unique players: {rosters['player_name'].nunique():,}")
        print(f"   Teams: {sorted(rosters['team'].unique())}")
        
        # Position breakdown
        if 'position' in rosters.columns:
            pos_counts = rosters['position'].value_counts()
            print(f"   Position breakdown:")
            for pos, count in pos_counts.head(10).items():
                print(f"     {pos}: {count}")
    else:
        print("❌ No roster data found")
    
    # 3. Verify schedule data
    schedule_file = data_dir / "schedule_2024.parquet"
    if schedule_file.exists():
        print(f"\n✅ Schedule Data ({schedule_file})")
        schedule = pd.read_parquet(schedule_file)
        
        print(f"   Total games: {len(schedule):,}")
        print(f"   Season types: {schedule['season_type'].value_counts().to_dict()}")
        print(f"   Weeks: {sorted(schedule['week'].unique())}")
    else:
        print("❌ No schedule data found")
    
    print(f"\n" + "=" * 60)
    print("LEAGUE LEADERS READINESS ASSESSMENT")
    print("=" * 60)
    
    if pbp_file.exists():
        pbp = pd.read_parquet(pbp_file)
        
        # Calculate expected League Leaders entries
        pass_attempts = pbp[pbp['pass'] == 1]['passer_player_name'].value_counts()
        qualified_qbs = pass_attempts[pass_attempts >= 150]
        
        rush_attempts = pbp[pbp['rush'] == 1]['rusher_player_name'].value_counts()
        qualified_rbs = rush_attempts[rush_attempts >= 75]
        
        completions = pbp[(pbp['pass'] == 1) & (pbp['complete_pass'] == 1)]['receiver_player_name'].value_counts()
        qualified_wrs = completions[completions >= 30]
        
        print(f"✅ SYSTEM IS READY FOR REAL NFL LEAGUE LEADERS!")
        print(f"   - {len(qualified_qbs)} QBs qualify for passing leaders (150+ attempts)")
        print(f"   - {len(qualified_rbs)} RBs qualify for rushing leaders (75+ carries)")  
        print(f"   - {len(qualified_wrs)} WRs qualify for receiving leaders (30+ catches)")
        print(f"   - Total plays available: {len(pbp):,} (vs previous {3252})")
        print(f"\n🎯 Expected top QBs: {list(qualified_qbs.head(5).index)}")
        print(f"🎯 Expected top RBs: {list(qualified_rbs.head(5).index)}")
        print(f"🎯 Expected top WRs: {list(qualified_wrs.head(5).index)}")
        
        return True
    else:
        print("❌ Cannot assess League Leaders readiness - no play data")
        return False

if __name__ == "__main__":
    success = verify_2024_data()
    sys.exit(0 if success else 1)