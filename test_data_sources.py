#!/usr/bin/env python3
"""Test script to find working NFL data sources."""

import requests
import time
from pathlib import Path

def test_data_sources():
    """Test various NFL data source URLs to find working endpoints."""
    
    print("=" * 70)
    print("NFL DATA SOURCE AVAILABILITY TEST")
    print("=" * 70)
    
    # Test various base URLs and data types
    base_urls = [
        "https://github.com/nflverse/nflverse-data/releases/download/pbp",
        "https://github.com/nflverse/nfldata/releases/download/pbp", 
        "https://raw.githubusercontent.com/nflverse/nflverse-data/master/data/pbp",
        "https://github.com/nflverse/nflverse-data/raw/master/data/pbp"
    ]
    
    seasons = [2024, 2023, 2022, 2021]
    file_types = ["play_by_play", "pbp"]
    
    working_urls = []
    
    for base_url in base_urls:
        print(f"\nTesting base URL: {base_url}")
        print("-" * 50)
        
        for season in seasons:
            for file_type in file_types:
                url = f"{base_url}/{file_type}_{season}.parquet"
                
                try:
                    response = requests.head(url, timeout=10)
                    if response.status_code == 200:
                        size_mb = int(response.headers.get('content-length', 0)) / (1024 * 1024)
                        print(f"✅ {file_type}_{season}.parquet - {size_mb:.1f} MB")
                        working_urls.append(url)
                    elif response.status_code == 404:
                        print(f"❌ {file_type}_{season}.parquet - Not Found")
                    else:
                        print(f"⚠️  {file_type}_{season}.parquet - Status {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ {file_type}_{season}.parquet - Error: {str(e)[:50]}")
                
                # Small delay to be respectful
                time.sleep(0.1)
    
    print("\n" + "=" * 70)
    print("WORKING DATA SOURCES SUMMARY")
    print("=" * 70)
    
    if working_urls:
        print(f"✅ Found {len(working_urls)} working data sources:")
        for url in working_urls:
            print(f"   - {url}")
    else:
        print("❌ No working data sources found")
    
    return working_urls


def test_alternative_sources():
    """Test alternative NFL data sources."""
    
    print("\n" + "=" * 70)
    print("ALTERNATIVE NFL DATA SOURCES TEST")
    print("=" * 70)
    
    # Test direct nflfastR data repository
    alternative_sources = [
        "https://raw.githubusercontent.com/nflverse/nflfastR-data/master/data/play_by_play_2023.rds",
        "https://github.com/nflverse/nflfastR-data/raw/master/data/play_by_play_2023.rds",
        "https://raw.githubusercontent.com/guga31bb/nflfastR-data/master/data/play_by_play_2023.csv.gz",
    ]
    
    for source in alternative_sources:
        try:
            response = requests.head(source, timeout=10)
            if response.status_code == 200:
                size_mb = int(response.headers.get('content-length', 0)) / (1024 * 1024)
                print(f"✅ Alternative source: {source}")
                print(f"   Size: {size_mb:.1f} MB")
            else:
                print(f"❌ {source} - Status {response.status_code}")
        except Exception as e:
            print(f"❌ {source} - Error: {str(e)[:60]}")


def recommend_data_strategy(working_urls):
    """Provide recommendations based on available data sources."""
    
    print("\n" + "=" * 70)
    print("DATA STRATEGY RECOMMENDATIONS")
    print("=" * 70)
    
    if not working_urls:
        print("Since no direct parquet files were found, here are your options:")
        print()
        print("1. USE ALTERNATIVE DATA FORMAT:")
        print("   - Try CSV.gz files from nflfastR-data repository")
        print("   - Use nflreadr R package to export data")
        print("   - Convert from RDS format if available")
        print()
        print("2. USE DOCKER APPROACH:")
        print("   - Set up R environment in Docker")
        print("   - Use nflfastR package directly")
        print("   - Export to parquet for Python consumption")
        print()
        print("3. USE PYTHON 3.11 ENVIRONMENT:")
        print("   - Create separate environment with Python 3.11")
        print("   - Install nfl_data_py successfully")
        print("   - Export data for Python 3.13 consumption")
        print()
        print("4. USE PAID DATA SERVICE:")
        print("   - ESPN API (rate limited)")
        print("   - SportRadar API (paid)")
        print("   - NFL Official API (expensive)")
        
    else:
        print("EXCELLENT! Found working data sources.")
        print()
        
        # Categorize by year
        years_available = set()
        for url in working_urls:
            if "2024" in url:
                years_available.add("2024")
            elif "2023" in url:
                years_available.add("2023")
            elif "2022" in url:
                years_available.add("2022")
        
        if "2024" in years_available:
            print("✅ IMMEDIATE SOLUTION AVAILABLE:")
            print("   - 2024 data is accessible")
            print("   - Can implement League Leaders immediately")
            print("   - Use NFLFastRClient with working URLs")
        elif "2023" in years_available:
            print("✅ DEVELOPMENT SOLUTION AVAILABLE:")
            print("   - Use 2023 data for development/testing")
            print("   - Validate League Leaders system")
            print("   - Wait for 2024 data completion")
        else:
            print("⚠️  LIMITED SOLUTION:")
            print("   - Only older data available")
            print("   - Good for system testing")
            print("   - Need alternative for current season")
    
    print("\nNEXT STEPS:")
    if working_urls:
        print("1. Update NFLFastRClient with working base URLs")
        print("2. Test data download and validation")
        print("3. Implement League Leaders data pipeline")
        print("4. Set up automated data refresh")
    else:
        print("1. Try R-based approach with Docker")
        print("2. Set up Python 3.11 environment")
        print("3. Consider paid data services for production")
        print("4. Implement fallback data strategies")


if __name__ == "__main__":
    print("Starting comprehensive NFL data source testing...")
    print("This may take a few minutes to test all endpoints...")
    
    working_urls = test_data_sources()
    test_alternative_sources()
    recommend_data_strategy(working_urls)
    
    print("\n✅ Data source analysis complete!")