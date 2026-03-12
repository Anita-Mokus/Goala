"""
Facebook Messenger Bot for Goala RAG.
Monitors Messenger conversations and responds automatically using the RAG API.
"""
import time
import random
import requests
import threading
import hashlib
import os
import json
from datetime import datetime
from typing import Optional, Dict, List
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
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
        
        # Processed message tracking: (conv_id, message_hash) so we only skip
        # the exact same message, not the whole conversation (new messages get replied).
        self._processed_messages: set = set()

        # Track the hash of the last response we sent per conversation to avoid
        # replying to our own messages on the next poll cycle.
        self._last_sent: Dict[str, str] = {}

        # Trigger for "process unread now" (wake main loop)
        self._process_unread_now_requested = False
        self._sleep_event = threading.Event()
    
    def start(self):
        """Start the bot and begin monitoring Messenger."""
        if self.running:
            print("Bot is already running")
            return

        # Mark as running immediately so the API /start route can confirm startup
        # within its 2-second window (Chrome launch + login detection takes longer).
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

            self._write_status_file()
            print("✓ Bot started. Monitoring for messages...\n")

            # Start main loop
            self._main_loop()
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
                
                # Check for "process unread now" trigger (from API)
                with self._lock:
                    if self._process_unread_now_requested:
                        self._process_unread_now_requested = False
                
                # Poll for unread messages
                unread_messages = self._get_unread_messages()
                if unread_messages:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(unread_messages)} unread message(s) to process")
                
                # Process each unread message
                for message in unread_messages:
                    if not self.running or self.paused:
                        break
                    
                    self._process_message(message)
                
                # Interruptible delay so "process unread now" can wake us
                delay = random.uniform(
                    self.config.CHECK_INTERVAL_MIN,
                    self.config.CHECK_INTERVAL_MAX
                )
                self._sleep_event.clear()
                self._sleep_event.wait(timeout=delay)
                
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
            # Selector strategies for unread conversations on modern Messenger (2025-2026).
            # Ordered from most specific to least specific.
            # Note: leading space in " unread" avoids partial-word false matches on
            # elements whose aria-label merely starts with "unread".
            unread_selectors = [
                '[aria-label*=" unread"]',           # e.g. "John Doe, 2 unread messages"
                '[aria-label*="unread message"]',    # e.g. "1 unread message"
                '[aria-label*=" Unread"]',
                '[aria-label*="Unread message"]',
                '[aria-label*="unread"]',             # broader fallback
                '[aria-label*="Unread"]',
            ]

            for selector in unread_selectors:
                try:
                    conversations = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"[DEBUG] Selector '{selector}' → {len(conversations)} element(s)")

                    for conv in conversations:
                        try:
                            # Click to open conversation
                            conv.click()
                            time.sleep(1.2)

                            # Use the URL after navigation as a stable conversation ID.
                            # It contains Facebook's thread ID, unlike element id/text which are
                            # unstable across DOM re-renders.
                            conv_id = self.driver.current_url

                            # Extract latest message
                            message = self._extract_latest_message()

                            if message:
                                msg_hash = hashlib.sha256(message['text'].encode(errors='replace')).hexdigest()[:16]
                                message_key = (conv_id, msg_hash)

                                # Skip if already processed
                                if message_key in self._processed_messages:
                                    continue

                                # Skip if this is the last message we ourselves sent
                                # (prevents replying to our own replies on the next cycle)
                                if self._last_sent.get(conv_id) == msg_hash:
                                    continue

                                message['conversation_id'] = conv_id
                                message['_msg_hash'] = msg_hash
                                unread_messages.append(message)

                        except (StaleElementReferenceException, NoSuchElementException) as e:
                            print(f"Warning: Could not process conversation: {e}")
                            continue

                    if unread_messages:
                        break  # Found new messages, no need to try other selectors

                except NoSuchElementException:
                    continue

            if not unread_messages:
                print("[DEBUG] No new unread messages found")

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
                
                # Mark this message as processed only after successful send (so we retry if send failed)
                msg_hash = message.get('_msg_hash')
                conv_id = message.get('conversation_id')
                if conv_id and msg_hash:
                    self._processed_messages.add((conv_id, msg_hash))
                    # Record the hash of the response we just sent so the next poll cycle
                    # can skip it and avoid the bot replying to its own messages.
                    resp_hash = hashlib.sha256(response.encode(errors='replace')).hexdigest()[:16]
                    self._last_sent[conv_id] = resp_hash

                # Update stats
                with self._lock:
                    self.message_count += 1
                    self.last_message_timestamp = datetime.now()
                self._write_status_file()
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
                    data = response.json()
                    result = data.get("response") if isinstance(data, dict) else None
                    if result:
                        return result
                    print("  Warning: API returned 200 but no 'response' key in JSON")
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
            
            # Focus and clear any existing content
            input_box.click()
            time.sleep(0.3)

            # Clear with Ctrl+A → Delete, then type with send_keys.
            # JS textContent mutation is silently ignored by React's synthetic event
            # system, so send_keys is the only reliable method for Messenger's
            # contenteditable input.
            try:
                ActionChains(self.driver) \
                    .key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL) \
                    .send_keys(Keys.DELETE) \
                    .perform()
                time.sleep(0.1)
                input_box.send_keys(text)
            except Exception:
                try:
                    input_box.send_keys(text)
                except Exception:
                    pass

            time.sleep(0.5)
            
            # Find and click send button
            send_selectors = [
                '[aria-label*="Send"]',
                '[aria-label*="Press enter"]',
                'div[aria-label="Send"]',
                '[data-icon="send"]',
            ]
            
            for selector in send_selectors:
                try:
                    send_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    send_button.click()
                    time.sleep(0.3)
                    return True
                except NoSuchElementException:
                    continue
            
            # Fallback: press Enter (Messenger often sends on Enter)
            try:
                input_box.send_keys(Keys.ENTER)
                return True
            except Exception:
                pass
            
            print("  ERROR: Could not find send button or send via Enter")
            return False
        
        except Exception as e:
            print(f"  ERROR sending message: {e}")
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
        """
        Request one immediate cycle of unread message processing.
        Wakes the main loop so it runs get unread + process without waiting for the next interval.
        Safe to call from another thread (e.g. API).
        """
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
        """Write current status to shared file so API can report status when bot runs in another process."""
        try:
            data = self.get_status()
            data['pid'] = os.getpid()
            path = self.config.STATUS_FILE
            with open(path, 'w') as f:
                json.dump(data, f, indent=0)
        except Exception as e:
            print(f"Warning: Could not write status file: {e}")
