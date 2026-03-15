"""
Facebook Messenger Bot for Goala RAG.
Monitors Messenger conversations and responds automatically using the RAG API.
"""
import time
import os
import json
import threading
from datetime import datetime
from typing import Optional, Dict

from src.integrations.messenger.config import MessengerConfig
from src.integrations.messenger.stealth_driver import create_stealth_driver


class MessengerBot:
    """
    Facebook Messenger bot that monitors conversations and responds using Goala RAG.
    """
    
    def __init__(self, config: Optional[MessengerConfig] = None):
        """
        Initialize the Messenger bot.
        
        Args:
            config: Optional configuration object (uses MessengerConfig by default)
        """
        self.config = config or MessengerConfig
        
        if not self.config.validate():
            raise ValueError("Invalid Messenger bot configuration")
        
        # State tracking
        self.running = False
        self.paused = False
        self.message_count = 0
        self.last_message_timestamp: Optional[datetime] = None
        self.start_time: Optional[datetime] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Driver (initialized on start)
        self.driver = None
        
        # Processed message tracking
        self._processed_messages: set = set()
        self._last_sent: Dict[str, str] = {}
        
        # Sleep event for interruptible delay
        self._process_unread_now_requested = False
        self._sleep_event = threading.Event()
    
    def start(self):
        """Start the bot and begin monitoring Messenger."""
        if self.running:
            print("Bot is already running")
            return
        
        # Mark as running immediately
        with self._lock:
            self.running = True
            self.paused = False
            self.start_time = datetime.now()
        
        print("\n" + "="*80)
        print("STARTING MESSENGER BOT")
        print("="*80)
        print(f"API URL: {self.config.API_URL}")
        print(f"Check interval: {self.config.CHECK_INTERVAL_MIN}-{self.config.CHECK_INTERVAL_MAX}s")
        print(f"Response delay: {self.config.RESPONSE_DELAY_MIN}-{self.config.RESPONSE_DELAY_MAX}s")
        print("="*80 + "\n")
        
        try:
            print("Initializing Chrome driver with stealth configuration...")
            self.driver = create_stealth_driver(self.config.CHROME_PROFILE_PATH)
            
            print("Navigating to Messenger...")
            self.driver.get("https://www.messenger.com")
            
            if not self._wait_for_login():
                print("ERROR: Failed to detect login. Please log in manually and restart the bot.")
                self.stop()
                return
            
            print("✓ Logged in successfully")
            
            self._write_status_file()
            print("✓ Bot started. Monitoring for messages...\n")
            
            # Start main loop
            from src.integrations.messenger.bot_loop import run_main_loop
            run_main_loop(self)
        except Exception as e:
            print(f"ERROR in bot startup: {e}")
            with self._lock:
                self.running = False
            raise
    
    def _wait_for_login(self, timeout: int = 300) -> bool:
        """
        Wait for user to log in to Messenger.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if login detected, False otherwise
        """
        from selenium.webdriver.common.by import By
        from selenium.common.exceptions import NoSuchElementException
        
        print(f"Waiting for login (timeout: {timeout}s)...")
        print("If not logged in, please log in manually in the Chrome window.")
        
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                selectors = [
                    '[aria-label*="Chats"]',
                    '[aria-label*="Conversations"]',
                    '[role="navigation"]',
                    'div[data-pagelet="LeftRail"]'
                ]
                
                for selector in selectors:
                    try:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if element:
                            return True
                    except NoSuchElementException:
                        continue
                
                time.sleep(2)
            except Exception as e:
                print(f"Error checking login status: {e}")
                time.sleep(2)
        
        return False
    
    def pause(self):
        """Pause message processing (but keep bot running)."""
        with self._lock:
            self.paused = True
        self._write_status_file()
        print("Bot paused")
    
    def resume(self):
        """Resume message processing."""
        with self._lock:
            self.paused = False
        self._write_status_file()
        print("Bot resumed")
    
    def request_process_unread_now(self):
        """Request one immediate cycle of unread message processing."""
        with self._lock:
            self._process_unread_now_requested = True
        self._sleep_event.set()
        print("Process unread now requested")
    
    def stop(self):
        """Stop the bot and cleanup resources."""
        print("\nStopping bot...")
        
        with self._lock:
            self.running = False
        
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Warning: Error closing driver: {e}")
        
        self._write_status_file()
        print("Bot stopped")
    
    def get_status(self) -> Dict:
        """
        Get current bot status.
        
        Returns:
            Dictionary with status information
        """
        with self._lock:
            uptime_seconds = 0
            if self.start_time:
                uptime_seconds = int((datetime.now() - self.start_time).total_seconds())
            
            return {
                'running': self.running,
                'paused': self.paused,
                'message_count': self.message_count,
                'last_message_timestamp': self.last_message_timestamp.isoformat() if self.last_message_timestamp else None,
                'uptime_seconds': uptime_seconds
            }
    
    def _write_status_file(self) -> None:
        """Write current status to shared file."""
        try:
            data = self.get_status()
            data['pid'] = os.getpid()
            path = self.config.STATUS_FILE
            with open(path, 'w') as f:
                json.dump(data, f, indent=0)
        except Exception as e:
            print(f"Warning: Could not write status file: {e}")
