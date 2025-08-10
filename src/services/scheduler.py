"""Data refresh scheduler service for automated data pipeline."""

import logging
import schedule
import time
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import requests
from threading import Thread
import os

logger = logging.getLogger(__name__)


class DataRefreshScheduler:
    """Scheduler for automated NFL data refresh."""
    
    def __init__(self, 
                 api_base_url: str = "http://localhost:8000",
                 refresh_time: str = "06:00",
                 enabled: bool = False):
        """Initialize the data refresh scheduler.
        
        Args:
            api_base_url: Base URL for API calls
            refresh_time: Time of day to run refresh (HH:MM format)
            enabled: Whether automatic refresh is enabled
        """
        self.api_base_url = api_base_url.rstrip('/')
        self.refresh_time = refresh_time
        self.enabled = enabled
        self.running = False
        self.last_refresh: Optional[datetime] = None
        self.last_refresh_status: Optional[str] = None
        self.refresh_thread: Optional[Thread] = None
        
        logger.info(f"DataRefreshScheduler initialized - API: {api_base_url}, Time: {refresh_time}, Enabled: {enabled}")
    
    def schedule_daily_refresh(self):
        """Schedule daily data refresh."""
        schedule.every().day.at(self.refresh_time).do(self._run_data_refresh)
        logger.info(f"Scheduled daily data refresh at {self.refresh_time}")
    
    def schedule_weekly_full_refresh(self):
        """Schedule weekly full data refresh (includes more seasons)."""
        schedule.every().sunday.at("05:00").do(self._run_full_data_refresh)
        logger.info("Scheduled weekly full data refresh on Sundays at 05:00")
    
    def _run_data_refresh(self, current_season_only: bool = True) -> Dict[str, Any]:
        """Run data refresh via API call."""
        try:
            logger.info(f"Starting {'current season' if current_season_only else 'full'} data refresh...")
            
            # Call the refresh API endpoint
            response = requests.post(
                f"{self.api_base_url}/api/v1/data/refresh",
                params={"current_season_only": current_season_only},
                timeout=300  # 5 minute timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                self.last_refresh = datetime.now()
                self.last_refresh_status = "success"
                logger.info(f"Data refresh completed successfully: {result['message']}")
                return result
            else:
                error_msg = f"Data refresh failed with status {response.status_code}: {response.text}"
                logger.error(error_msg)
                self.last_refresh_status = "error"
                return {"status": "error", "message": error_msg}
                
        except Exception as e:
            error_msg = f"Data refresh failed with exception: {str(e)}"
            logger.error(error_msg)
            self.last_refresh_status = "error"
            return {"status": "error", "message": error_msg}
    
    def _run_full_data_refresh(self) -> Dict[str, Any]:
        """Run full data refresh (multiple seasons)."""
        return self._run_data_refresh(current_season_only=False)
    
    def start(self):
        """Start the scheduler in a background thread."""
        if self.running or not self.enabled:
            logger.warning("Scheduler already running or not enabled")
            return
        
        self.running = True
        
        # Schedule jobs
        self.schedule_daily_refresh()
        self.schedule_weekly_full_refresh()
        
        # Start scheduler thread
        self.refresh_thread = Thread(target=self._run_scheduler, daemon=True)
        self.refresh_thread.start()
        
        logger.info("Data refresh scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        schedule.clear()
        logger.info("Data refresh scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def trigger_immediate_refresh(self, current_season_only: bool = True) -> Dict[str, Any]:
        """Trigger an immediate data refresh."""
        logger.info("Triggering immediate data refresh...")
        return self._run_data_refresh(current_season_only)
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        next_jobs = []
        for job in schedule.jobs:
            next_jobs.append({
                "job": str(job.job_func.__name__),
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "interval": str(job.interval)
            })
        
        return {
            "enabled": self.enabled,
            "running": self.running,
            "refresh_time": self.refresh_time,
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
            "last_refresh_status": self.last_refresh_status,
            "next_jobs": next_jobs
        }


class NFLSeasonAwareScheduler(DataRefreshScheduler):
    """NFL season-aware scheduler that adjusts refresh frequency based on season."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.season_start_month = 9  # September
        self.season_end_month = 2   # February
    
    def is_nfl_season(self) -> bool:
        """Check if we're currently in NFL season."""
        now = datetime.now()
        month = now.month
        
        # NFL season runs September through February
        return month >= self.season_start_month or month <= self.season_end_month
    
    def get_refresh_frequency(self) -> str:
        """Get appropriate refresh frequency based on season."""
        if self.is_nfl_season():
            return "daily"  # More frequent during season
        else:
            return "weekly"  # Less frequent during off-season
    
    def schedule_season_aware_refresh(self):
        """Schedule refresh based on NFL season."""
        if self.is_nfl_season():
            # During season: daily refresh
            schedule.every().day.at(self.refresh_time).do(self._run_data_refresh)
            logger.info("NFL season active - scheduled daily refresh")
        else:
            # Off-season: weekly refresh
            schedule.every().week.at(self.refresh_time).do(self._run_data_refresh)
            logger.info("NFL off-season - scheduled weekly refresh")


def create_scheduler() -> DataRefreshScheduler:
    """Create and configure the data refresh scheduler."""
    # Get configuration from environment
    api_url = os.getenv("API_BASE_URL", "http://localhost:8004")
    refresh_time = os.getenv("REFRESH_TIME", "06:00")
    enabled = os.getenv("AUTO_REFRESH_ENABLED", "false").lower() == "true"
    season_aware = os.getenv("SEASON_AWARE_SCHEDULING", "true").lower() == "true"
    
    if season_aware:
        scheduler = NFLSeasonAwareScheduler(
            api_base_url=api_url,
            refresh_time=refresh_time,
            enabled=enabled
        )
    else:
        scheduler = DataRefreshScheduler(
            api_base_url=api_url,
            refresh_time=refresh_time,
            enabled=enabled
        )
    
    return scheduler


# Global scheduler instance
_global_scheduler: Optional[DataRefreshScheduler] = None


def get_global_scheduler() -> DataRefreshScheduler:
    """Get or create the global scheduler instance."""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = create_scheduler()
    return _global_scheduler


if __name__ == "__main__":
    # CLI tool for testing scheduler
    import argparse
    
    parser = argparse.ArgumentParser(description="NFL Data Refresh Scheduler")
    parser.add_argument("--start", action="store_true", help="Start the scheduler")
    parser.add_argument("--refresh", action="store_true", help="Trigger immediate refresh")
    parser.add_argument("--status", action="store_true", help="Show scheduler status")
    parser.add_argument("--api-url", default="http://localhost:8004", help="API base URL")
    
    args = parser.parse_args()
    
    scheduler = DataRefreshScheduler(
        api_base_url=args.api_url,
        enabled=True
    )
    
    if args.refresh:
        result = scheduler.trigger_immediate_refresh()
        print(f"Refresh result: {result}")
    
    if args.status:
        status = scheduler.get_status()
        print(f"Scheduler status: {status}")
    
    if args.start:
        print("Starting scheduler...")
        scheduler.start()
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("Stopping scheduler...")
            scheduler.stop()