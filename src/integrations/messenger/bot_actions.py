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

from src.integrations.messenger.history_bootstrap import bootstrap_thread_from_dom
from src.integrations.messenger.history_context import (
    select_history_window,
    build_contextual_user_input,
)
from src.integrations.messenger.history_repository import (
    get_or_create_thread,
    count_thread_messages,
    mark_thread_bootstrapped,
    save_message,
    get_recent_messages,
    extract_conversation_id,
)
from src.integrations.messenger.thread_policy import is_likely_group_chat


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
        
        if not bot.config.ALLOW_GROUP_CHATS and is_likely_group_chat(sender):
            print(f"  [INFO] Group chat detected for '{sender}'. Skipping per policy.")
            _mark_processed(bot, message)
            return

        # Ensure thread exists and bootstrap from DOM once for first-time users
        thread = get_or_create_thread(
            conversation_url=conv_id or bot.driver.current_url,
            display_name=sender,
            metadata={"source": "messenger_bot"},
        )
        thread_id = int(thread["id"])
        conversation_id = str(thread.get("conversation_id") or extract_conversation_id(conv_id or ""))

        message_count_before = count_thread_messages(thread_id)
        if message_count_before == 0 and not thread.get("bootstrapped_from_dom"):
            bootstrapped_count = bootstrap_thread_from_dom(bot, thread_id, conversation_id)
            mark_thread_bootstrapped(thread_id)
            print(f"  [DEBUG] DOM bootstrap saved {bootstrapped_count} message(s) for conversation {conversation_id}")

        save_message(
            thread_id=thread_id,
            role="user",
            direction="inbound",
            content=text,
            source="live_poll",
            metadata={
                "sender": sender,
                "conversation_url": conv_id,
                "conversation_id": conversation_id,
            },
        )

        recent_messages = get_recent_messages(thread_id, limit=max(bot.config.HISTORY_WINDOW_TURNS * 4, 40))
        history_window = select_history_window(
            messages=recent_messages,
            max_turns=bot.config.HISTORY_WINDOW_TURNS,
            max_chars=bot.config.HISTORY_MAX_CHARS,
        )
        contextual_input = build_contextual_user_input(history_window, text)

        # Get response from RAG API using contextualized input
        response = get_rag_response(bot, contextual_input, sender)
        
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

            save_message(
                thread_id=thread_id,
                role="assistant",
                direction="outbound",
                content=response,
                source="live_send",
                metadata={
                    "sender": sender,
                    "conversation_url": conv_id,
                    "conversation_id": conversation_id,
                },
            )
            
            # Mark as processed
            _mark_processed(bot, message, response)
            
            # Update stats
            with bot._lock:
                bot.message_count += 1
                bot.last_message_timestamp = datetime.now()
            bot._write_status_file()
        else:
            print("  ✗ Failed to send response")
    
    except Exception as e:
        print(f"ERROR processing message: {e}")


def _mark_processed(bot, message: Dict, response: Optional[str] = None) -> None:
    """Track processed message hashes to avoid duplicate handling in-memory."""
    conv_id = message.get('conversation_id')
    msg_hash = message.get('_msg_hash')

    if conv_id and msg_hash:
        bot._processed_messages.add((conv_id, msg_hash))

    if conv_id and response:
        resp_hash = hashlib.sha256(response.encode(errors='replace')).hexdigest()[:16]
        bot._last_sent[conv_id] = resp_hash


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
