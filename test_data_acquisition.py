#!/usr/bin/env python3
"""Test script for NFL data acquisition approaches."""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from data.nflfastr_client import NFLFastRClient, NFLFastRConfig

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_sample_data_acquisition():
    """Test acquiring sample 2024 NFL data for League Leaders validation."""
    
    print("=" * 60)
    print("NFL DATA ACQUISITION TEST")
    print("=" * 60)
    
    # Initialize client
    config = NFLFastRConfig(cache_dir="data/test_cache")
    client = NFLFastRClient(config)
    
    print("\n1. Testing Sample Data Download (Weeks 1-2)")
    print("-" * 50)
    
    try:
        # Get sample data for testing
        sample_data = client.get_sample_data(season=2024, weeks=[1, 2])
        
        if sample_data.empty:
            print("❌ No sample data retrieved")
            return False
        
        print(f"✅ Retrieved {len(sample_data)} plays from sample weeks")
        print(f"   Date range: {sample_data['game_date'].min()} to {sample_data['game_date'].max()}")
        print(f"   Unique games: {sample_data['game_id'].nunique()}")
        
    except Exception as e:
        print(f"❌ Sample data download failed: {e}")
        return False
    
    print("\n2. Data Quality Analysis")
    print("-" * 50)
    
    try:
        quality_analysis = client.analyze_data_quality(sample_data)
        
        print(f"   Total plays: {quality_analysis['total_plays']}")
        print(f"   Unique teams: {len(quality_analysis['unique_teams'])}")
        print(f"   Play types: {list(quality_analysis['play_types'].keys())[:5]}...")
        
        # Show top QBs
        if 'qb_attempts' in quality_analysis['key_players']:
            top_qbs = list(quality_analysis['key_players']['qb_attempts'].keys())[:5]
            print(f"   Top QBs: {top_qbs}")
        
        # Show top RBs
        if 'rb_carries' in quality_analysis['key_players']:
            top_rbs = list(quality_analysis['key_players']['rb_carries'].keys())[:5]
            print(f"   Top RBs: {top_rbs}")
        
    except Exception as e:
        print(f"❌ Data quality analysis failed: {e}")
        return False
    
    print("\n3. League Leaders Validation")
    print("-" * 50)
    
    try:
        validation = client.validate_league_leaders_data(sample_data)
        
        print(f"   Meets thresholds: {validation['meets_minimum_thresholds']}")
        print(f"   Quality score: {validation['data_quality_score']:.2f}")
        print(f"   Legitimate starters found: {len(validation['legitimate_starters_found'])}")
        
        if validation['legitimate_starters_found']:
            print("   ✅ Found legitimate starters:")
            for starter in validation['legitimate_starters_found'][:10]:
                print(f"      - {starter}")
        
        print("   Recommendations:")
        for rec in validation['recommendations']:
            print(f"      • {rec}")
        
    except Exception as e:
        print(f"❌ League Leaders validation failed: {e}")
        return False
    
    print("\n4. Full Season Data Test")
    print("-" * 50)
    
    try:
        print("   Attempting full 2024 season download...")
        full_data = client.fetch_play_by_play([2024])
        
        if full_data.empty:
            print("   ❌ Full season data not available yet")
        else:
            print(f"   ✅ Full season: {len(full_data)} total plays")
            
            # Validate full season for League Leaders
            full_validation = client.validate_league_leaders_data(full_data)
            print(f"   Full season quality score: {full_validation['data_quality_score']:.2f}")
            print(f"   Meets minimum thresholds: {full_validation['meets_minimum_thresholds']}")
            
    except Exception as e:
        print(f"   ⚠️  Full season download issue (expected for 2024): {e}")
    
    print("\n5. Cache Information")
    print("-" * 50)
    
    cache_info = client.get_cache_info()
    print(f"   Cache directory: {cache_info['cache_dir']}")
    print(f"   Cached files: {cache_info['cached_files']}")
    print(f"   Total size: {cache_info['total_size_mb']:.2f} MB")
    
    if cache_info['files']:
        print("   Files:")
        for file in cache_info['files']:
            print(f"      - {file}")
    
    print("\n" + "=" * 60)
    print("CONCLUSION & RECOMMENDATIONS")
    print("=" * 60)
    
    if sample_data.empty:
        print("❌ Data acquisition failed - try alternative approach")
    else:
        print("✅ Data acquisition successful!")
        print(f"\nFor League Leaders system with {len(sample_data)} sample plays:")
        
        # Practical recommendations
        if len(sample_data) > 5000:
            print("✅ Sufficient data volume for testing")
        else:
            print("⚠️  Low data volume - consider more weeks")
        
        print(f"\nNext steps:")
        print("1. Use this approach for development testing")
        print("2. Scale to full season when 2024 data is complete")
        print("3. Consider 2023 full season data for immediate production needs")
        print("4. Implement this client as primary data source")
    
    return True


def test_alternative_approaches():
    """Test alternative data acquisition approaches."""
    
    print("\n" + "=" * 60)
    print("ALTERNATIVE APPROACHES TEST")
    print("=" * 60)
    
    print("\n1. Direct URL Access Test")
    print("-" * 50)
    
    import requests
    
    try:
        # Test 2023 data availability (known to be complete)
        test_url = "https://github.com/nflverse/nfldata/releases/download/pbp/play_by_play_2023.parquet"
        response = requests.head(test_url, timeout=10)
        
        if response.status_code == 200:
            print("✅ 2023 data available via direct download")
            size_mb = int(response.headers.get('content-length', 0)) / (1024 * 1024)
            print(f"   File size: {size_mb:.1f} MB")
        else:
            print(f"❌ 2023 data access failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Direct URL test failed: {e}")
    
    print("\n2. Python Environment Assessment")
    print("-" * 50)
    
    try:
        import pandas as pd
        print(f"✅ pandas available: {pd.__version__}")
    except ImportError:
        print("❌ pandas not available")
    
    try:
        import requests
        print(f"✅ requests available: {requests.__version__}")
    except ImportError:
        print("❌ requests not available")
    
    try:
        # Test if we can import the original nfl_data_py
        import nfl_data_py as nfl
        print("✅ nfl_data_py available (compilation succeeded)")
    except ImportError:
        print("❌ nfl_data_py not available (expected - compilation issues)")
    
    print("\n3. Docker Environment Assessment")
    print("-" * 50)
    
    import subprocess
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Docker available for containerized approach")
        else:
            print("❌ Docker not properly configured")
    except Exception:
        print("❌ Docker not available")


if __name__ == "__main__":
    print("Starting NFL Data Acquisition Tests...")
    
    success = test_sample_data_acquisition()
    test_alternative_approaches()
    
    if success:
        print("\n✅ Testing completed successfully!")
        print("Ready to implement League Leaders data pipeline.")
    else:
        print("\n❌ Testing revealed issues - see recommendations above.")