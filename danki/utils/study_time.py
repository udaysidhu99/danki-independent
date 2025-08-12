"""Utilities for handling study time and day rollover in Anki-style scheduling."""

import time
from datetime import datetime, timedelta
from typing import Tuple


class StudyTime:
    """Utility class for handling study dates and day rollover."""
    
    def __init__(self, rollover_hour: int = 4):
        """
        Initialize study time utilities.
        
        Args:
            rollover_hour: Hour of day when study day rolls over (default 4 AM)
        """
        self.rollover_hour = rollover_hour
    
    def get_study_date(self, timestamp: int = None) -> str:
        """
        Get the current study date (YYYY-MM-DD format).
        
        Study day starts at rollover hour (4 AM by default), so:
        - 2 AM → yesterday's study date
        - 6 AM → today's study date
        
        Args:
            timestamp: Unix timestamp (defaults to current time)
            
        Returns:
            Study date string in YYYY-MM-DD format
        """
        if timestamp is None:
            timestamp = int(time.time())
            
        dt = datetime.fromtimestamp(timestamp)
        
        # If before rollover hour, count as previous day
        if dt.hour < self.rollover_hour:
            dt = dt - timedelta(days=1)
            
        return dt.strftime("%Y-%m-%d")
    
    def get_next_rollover_timestamp(self, timestamp: int = None) -> int:
        """
        Get the timestamp of the next rollover time.
        
        Args:
            timestamp: Unix timestamp (defaults to current time)
            
        Returns:
            Unix timestamp of next rollover
        """
        if timestamp is None:
            timestamp = int(time.time())
            
        dt = datetime.fromtimestamp(timestamp)
        
        # Get today's rollover time
        rollover_today = dt.replace(hour=self.rollover_hour, minute=0, second=0, microsecond=0)
        
        # If we're past today's rollover, get tomorrow's
        if dt >= rollover_today:
            rollover_next = rollover_today + timedelta(days=1)
        else:
            rollover_next = rollover_today
            
        return int(rollover_next.timestamp())
    
    def is_same_study_day(self, timestamp1: int, timestamp2: int) -> bool:
        """
        Check if two timestamps are in the same study day.
        
        Args:
            timestamp1: First timestamp
            timestamp2: Second timestamp
            
        Returns:
            True if both timestamps are in the same study day
        """
        return self.get_study_date(timestamp1) == self.get_study_date(timestamp2)
    
    def get_day_progress(self, rollover_timestamp: int) -> Tuple[int, int]:
        """
        Get progress through current study day.
        
        Args:
            rollover_timestamp: Next rollover timestamp
            
        Returns:
            Tuple of (seconds_elapsed, total_seconds_in_day)
        """
        current_time = int(time.time())
        total_seconds = 24 * 60 * 60  # 24 hours
        
        # Calculate seconds since last rollover
        seconds_since_rollover = current_time - (rollover_timestamp - total_seconds)
        
        return (seconds_since_rollover, total_seconds)
    
    def time_until_rollover(self, timestamp: int = None) -> int:
        """
        Get seconds until next rollover.
        
        Args:
            timestamp: Unix timestamp (defaults to current time)
            
        Returns:
            Seconds until next rollover
        """
        if timestamp is None:
            timestamp = int(time.time())
            
        next_rollover = self.get_next_rollover_timestamp(timestamp)
        return max(0, next_rollover - timestamp)


# Global instance with default settings
study_time = StudyTime()