"""
Facebook Messenger Bot for Goala RAG.
Monitors Messenger conversations and responds automatically using the RAG API.
"""
import time
import random
import requests
import threading
from datetime import datetime
from typing import Optional, Dict, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from src.integrations.messenger.config import MessengerConfig
from src.integrations.messenger.stealth_driver import create_stealth_driver


class MessengerBot:
    """
    Facebook Messenger bot that monitors conversations and responds using Goala RAG.
    
    Features:
    - 24/7 operation with continuous monitoring
    - Randomized polling intervals (10-15s)
    - Randomized response delays (2-5s)
    - Stealth configuration to avoid detection
    - Error handling with retries
    - Pause/resume/stop controls
    """
    
    def __init__(self, config: Optional[MessengerConfig] = None):
        """
        Initialize the Messenger bot.
        
        Args:
            config: Optional configuration object (uses MessengerConfig by default)
        """
        self.config = config or MessengerConfig
        
        # Validate configuration
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
        
        # Processed message tracking (to avoid duplicates)
        self._processed_messages: set = set()
    
    def start(self):
        """Start the bot and begin monitoring Messenger."""
        if self.running:
            print("Bot is already running")
            return
        
        print("\n" + "="*80)
        print("STARTING MESSENGER BOT")
        print("="*80)
        print(f"API URL: {self.config.API_URL}")
        print(f"Check interval: {self.config.CHECK_INTERVAL_MIN}-{self.config.CHECK_INTERVAL_MAX}s")
        print(f"Response delay: {self.config.RESPONSE_DELAY_MIN}-{self.config.RESPONSE_DELAY_MAX}s")
        print("="*80 + "\n")
        
        # Create stealth driver
        print("Initializing Chrome driver with stealth configuration...")
        self.driver = create_stealth_driver(self.config.CHROME_PROFILE_PATH)
        
        # Navigate to Messenger
        print("Navigating to Messenger...")
        self.driver.get("https://www.messenger.com")
        
        # Wait for login if needed
        if not self._wait_for_login():
            print("ERROR: Failed to detect login. Please log in manually and restart the bot.")
            self.stop()
            return
        
        print("✓ Logged in successfully")
        
        # Set running state
        with self._lock:
            self.running = True
            self.paused = False
            self.start_time = datetime.now()
        
        print("✓ Bot started. Monitoring for messages...\n")
        
        # Start main loop
        self._main_loop()
    
    def _wait_for_login(self, timeout: int = 300) -> bool:
        """
        Wait for user to log in to Messenger.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if login detected, False otherwise
        """
        print(f"Waiting for login (timeout: {timeout}s)...")
        print("If not logged in, please log in manually in the Chrome window.")
        
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                # Check for chat interface elements (indicates logged in)
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
    
    def _main_loop(self):
        """Main bot loop - continuously monitor and respond to messages."""
        while self.running:
            try:
                # Check if paused
                if self.paused:
                    time.sleep(1)
                    continue
                
                # Poll for unread messages
                unread_messages = self._get_unread_messages()
                
                # Process each unread message
                for message in unread_messages:
                    if not self.running or self.paused:
                        break
                    
                    self._process_message(message)
                
                # Random delay before next check
                delay = random.uniform(
                    self.config.CHECK_INTERVAL_MIN,
                    self.config.CHECK_INTERVAL_MAX
                )
                time.sleep(delay)
                
            except KeyboardInterrupt:
                print("\n\nKeyboard interrupt received. Stopping bot...")
                self.stop()
                break
            except Exception as e:
                print(f"ERROR in main loop: {e}")
                print("Continuing operation...")
                time.sleep(5)
    
    def _get_unread_messages(self) -> List[Dict]:
        """
        Get all unread messages from Messenger.
        
        Returns:
            List of message dictionaries with 'sender', 'text', and 'element' keys
        """
        unread_messages = []
        
        try:
            # Multiple selector strategies for unread conversations
            unread_selectors = [
                '[aria-label*="unread"]',
                '[aria-label*="Unread"]',
                'div[role="button"][aria-label*="message"]',
            ]
            
            for selector in unread_selectors:
                try:
                    conversations = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for conv in conversations:
                        try:
                            # Get conversation identifier
                            conv_id = conv.get_attribute("id") or conv.text[:50]
                            
                            # Skip if already processed
                            if conv_id in self._processed_messages:
                                continue
                            
                            # Click to open conversation
                            conv.click()
                            time.sleep(1)
                            
                            # Extract latest message
                            message = self._extract_latest_message()
                            
                            if message:
                                message['conversation_id'] = conv_id
                                unread_messages.append(message)
                                self._processed_messages.add(conv_id)
                        
                        except (StaleElementReferenceException, NoSuchElementException) as e:
                            print(f"Warning: Could not process conversation: {e}")
                            continue
                    
                    if unread_messages:
                        break  # Found messages, no need to try other selectors
                
                except NoSuchElementException:
                    continue
        
        except Exception as e:
            print(f"ERROR getting unread messages: {e}")
        
        return unread_messages
    
    def _extract_latest_message(self) -> Optional[Dict]:
        """
        Extract the latest message from the currently open conversation.
        
        Returns:
            Dictionary with 'sender', 'text', and 'element' keys, or None
        """
        try:
            # Wait for messages to load
            time.sleep(1)
            
            # Multiple selector strategies for messages
            message_selectors = [
                'div[dir="auto"]',
                'span.x1lliihq',
                'div[role="row"] div[dir="auto"]',
            ]
            
            for selector in message_selectors:
                try:
                    messages = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if messages:
                        # Get the last message (most recent)
                        latest = messages[-1]
                        text = latest.text.strip()
                        
                        if text:
                            # Try to extract sender name
                            sender = self._extract_sender_name()
                            
                            return {
                                'sender': sender,
                                'text': text,
                                'element': latest
                            }
                
                except NoSuchElementException:
                    continue
        
        except Exception as e:
            print(f"ERROR extracting message: {e}")
        
        return None
    
    def _extract_sender_name(self) -> str:
        """
        Extract sender name from the current conversation.
        
        Returns:
            Sender name or 'Unknown'
        """
        try:
            # Try to find conversation header with name
            header_selectors = [
                'h1[dir="auto"]',
                'span[dir="auto"]',
                '[role="heading"]',
            ]
            
            for selector in header_selectors:
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    name = element.text.strip()
                    if name:
                        return name
                except NoSuchElementException:
                    continue
        
        except Exception as e:
            print(f"Warning: Could not extract sender name: {e}")
        
        return "Unknown"
    
    def _process_message(self, message: Dict):
        """
        Process a single message: get RAG response and send reply.
        
        Args:
            message: Message dictionary with 'sender', 'text', and 'conversation_id'
        """
        try:
            sender = message['sender']
            text = message['text']
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] New message from {sender}:")
            print(f"  > {text[:100]}{'...' if len(text) > 100 else ''}")
            
            # Get response from RAG API
            response = self._get_rag_response(text, sender)
            
            if not response:
                print("  ✗ Failed to get response from RAG API")
                return
            
            print(f"  < {response[:100]}{'...' if len(response) > 100 else ''}")
            
            # Random delay before responding
            delay = random.uniform(
                self.config.RESPONSE_DELAY_MIN,
                self.config.RESPONSE_DELAY_MAX
            )
            time.sleep(delay)
            
            # Send response
            if self._send_message(response):
                print("  ✓ Response sent successfully")
                
                # Update stats
                with self._lock:
                    self.message_count += 1
                    self.last_message_timestamp = datetime.now()
            else:
                print("  ✗ Failed to send response")
        
        except Exception as e:
            print(f"ERROR processing message: {e}")
    
    def _get_rag_response(self, message: str, sender: str, max_retries: int = 3) -> Optional[str]:
        """
        Get response from Goala RAG API with retry logic.
        
        Args:
            message: User message
            sender: Sender name
            max_retries: Maximum number of retry attempts
            
        Returns:
            AI response or None on failure
        """
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.config.API_URL,
                    json={"message": message},
                    timeout=30
                )
                
                if response.status_code == 200:
                    return response.json().get("response")
                else:
                    print(f"  Warning: API returned status {response.status_code}")
            
            except requests.exceptions.RequestException as e:
                print(f"  Warning: API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
        
        # All retries failed, return fallback message
        return "I apologize, but I'm having trouble processing your request right now. Please try again later."
    
    def _send_message(self, text: str) -> bool:
        """
        Send a message in the currently open conversation.
        
        Args:
            text: Message text to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find input box with multiple selector strategies
            input_selectors = [
                'div[contenteditable="true"][role="textbox"]',
                '[aria-label*="Message"]',
                '[aria-label*="Aa"]',
                'div[contenteditable="true"]',
            ]
            
            input_box = None
            for selector in input_selectors:
                try:
                    input_box = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if input_box:
                        break
                except NoSuchElementException:
                    continue
            
            if not input_box:
                print("  ERROR: Could not find message input box")
                return False
            
            # Paste text (no typing simulation)
            input_box.click()
            input_box.send_keys(text)
            
            # Wait a moment for text to be entered
            time.sleep(0.5)
            
            # Find and click send button
            send_selectors = [
                '[aria-label*="Send"]',
                '[aria-label*="Press enter"]',
                'div[aria-label="Send"]',
            ]
            
            for selector in send_selectors:
                try:
                    send_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    send_button.click()
                    return True
                except NoSuchElementException:
                    continue
            
            print("  ERROR: Could not find send button")
            return False
        
        except Exception as e:
            print(f"  ERROR sending message: {e}")
            return False
    
    def pause(self):
        """Pause message processing (but keep bot running)."""
        with self._lock:
            self.paused = True
        print("Bot paused")
    
    def resume(self):
        """Resume message processing."""
        with self._lock:
            self.paused = False
        print("Bot resumed")
    
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
