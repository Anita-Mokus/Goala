"""
Messenger bot actions.
Handles message processing, RAG responses, and sending messages.
"""
import time
import random
import hashlib
import requests
from typing import Dict, Optional
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException


def process_message(bot, message: Dict):
    """
    Process a single message: get RAG response and send reply.
    
    Note: message['text'] may contain multiple client messages combined with newlines.
    
    Args:
        bot: MessengerBot instance
        message: Message dictionary with 'sender', 'text', and 'conversation_id'
    """
    try:
        sender = message['sender']
        text = message['text']
        conv_id = message.get('conversation_id')
        
        # Check if this is a combined message (contains newlines indicating multiple bubbles)
        message_count = text.count('\n') + 1
        if message_count > 1:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] New combined message ({message_count} parts) from {sender}:")
        else:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] New message from {sender}:")
        
        print(f"  > {text[:100]}{'...' if len(text) > 100 else ''}")
        
        # Ensure we are in the target conversation before sending
        if conv_id and bot.driver.current_url != conv_id:
            print(f"  [DEBUG] Switching to target conversation: {conv_id}")
            bot.driver.get(conv_id)
            time.sleep(1.2)
        
        # Get response from RAG API
        response = get_rag_response(bot, text, sender)
        
        if not response:
            print("  ✗ Failed to get response from RAG API")
            return
        
        print(f"  < {response[:100]}{'...' if len(response) > 100 else ''}")
        
        # Random delay before responding
        delay = random.uniform(
            bot.config.RESPONSE_DELAY_MIN,
            bot.config.RESPONSE_DELAY_MAX
        )
        time.sleep(delay)
        
        # Send response
        if send_message(bot, response):
            print("  ✓ Response sent successfully")
            
            # Mark as processed
            msg_hash = message.get('_msg_hash')
            if conv_id and msg_hash:
                bot._processed_messages.add((conv_id, msg_hash))
                resp_hash = hashlib.sha256(response.encode(errors='replace')).hexdigest()[:16]
                bot._last_sent[conv_id] = resp_hash
            
            # Update stats
            with bot._lock:
                bot.message_count += 1
                bot.last_message_timestamp = datetime.now()
            bot._write_status_file()
        else:
            print("  ✗ Failed to send response")
    
    except Exception as e:
        print(f"ERROR processing message: {e}")


def get_rag_response(bot, message: str, sender: str, max_retries: int = 3) -> Optional[str]:
    """
    Get response from Goala RAG API with retry logic.
    
    Args:
        bot: MessengerBot instance
        message: User message
        sender: Sender name
        max_retries: Maximum number of retry attempts
        
    Returns:
        AI response or None on failure
    """
    for attempt in range(max_retries):
        try:
            response = requests.post(
                bot.config.API_URL,
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
                wait_time = 2 ** attempt
                time.sleep(wait_time)
    
    return "I apologize, but I'm having trouble processing your request right now. Please try again later."


def send_message(bot, text: str) -> bool:
    """
    Send a message in the currently open conversation.
    
    Args:
        bot: MessengerBot instance
        text: Message text to send
        
    Returns:
        True if successful, False otherwise
    """
    try:
        input_selectors = [
            'div[contenteditable="true"][role="textbox"]',
            '[aria-label*="Message"]',
            '[aria-label*="Aa"]',
            'div[contenteditable="true"]',
        ]
        
        input_box = None
        for selector in input_selectors:
            try:
                input_box = bot.driver.find_element(By.CSS_SELECTOR, selector)
                if input_box:
                    break
            except NoSuchElementException:
                continue
        
        if not input_box:
            print("  ERROR: Could not find message input box")
            return False
        
        # Focus and clear
        input_box.click()
        time.sleep(0.3)
        
        try:
            ActionChains(bot.driver) \
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
                send_button = bot.driver.find_element(By.CSS_SELECTOR, selector)
                send_button.click()
                time.sleep(0.3)
                return True
            except NoSuchElementException:
                continue
        
        # Fallback: press Enter
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
