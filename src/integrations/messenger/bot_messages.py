"""
Messenger bot message detection and extraction.
Handles unread message detection and content extraction.
"""
import time
import hashlib
from typing import List, Dict, Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


def get_unread_messages(bot) -> List[Dict]:
    """
    Get all unread messages from Messenger.
    
    Args:
        bot: MessengerBot instance
    
    Returns:
        List of message dictionaries with 'sender', 'text', and 'element' keys
    """
    unread_messages = []
    
    try:
        conv_links = bot.driver.find_elements(
            By.CSS_SELECTOR,
            'a[href*="/t/"], a[href*="/e2ee/t/"]'
        )
        
        # Skip first 4 fixed Facebook nav buttons
        conversation_links = conv_links[4:]
        print(f"[DEBUG] Found {len(conversation_links)} conversation link(s) in sidebar:")
        for i, link in enumerate(conversation_links):
            label = (link.get_attribute("aria-label") or link.text or "").strip().replace("\n", " | ")
            href = link.get_attribute("href") or ""
            print(f"[DEBUG]   [{i}] {label[:70]}  →  {href}")
        
        unread_hrefs: List[str] = []
        
        def _sanitize_href(raw_href: str) -> str:
            """Remove invisible/control characters from URLs."""
            if not raw_href:
                return ""
            cleaned = "".join(ch for ch in raw_href if ch.isprintable() and ord(ch) not in {0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF})
            return cleaned.strip()
        
        for link in conversation_links:
            try:
                is_unread = bot.driver.execute_script("""
                    var el = arguments[0];
                    var children = el.querySelectorAll('*');
                    for (var i = 0; i < children.length; i++) {
                        var fw = window.getComputedStyle(children[i]).fontWeight;
                        if (fw === '700' || fw === 'bold') { return true; }
                    }
                    return false;
                """, link)
                
                if is_unread:
                    href = _sanitize_href(link.get_attribute("href") or "")
                    if href and href not in unread_hrefs:
                        unread_hrefs.append(href)
                        label = link.get_attribute("aria-label") or href
                        print(f"[DEBUG] Unread: {label[:70]}")
            except Exception:
                continue
        
        print(f"[DEBUG] {len(unread_hrefs)} unread conversation(s) detected")
        
        for href in unread_hrefs:
            try:
                print(f"[DEBUG] Opening unread conversation: {href}")
                bot.driver.get(href)
                time.sleep(1.5)
                
                conv_id = bot.driver.current_url
                
                # Extract all unanswered client messages (combined into one)
                message = extract_unanswered_client_messages(bot, conv_id)
                
                if message:
                    # Hash the combined text for deduplication
                    msg_hash = hashlib.sha256(message['text'].encode(errors='replace')).hexdigest()[:16]
                    message_key = (conv_id, msg_hash)
                    
                    # Skip if we've already processed this exact set of messages
                    if message_key in bot._processed_messages:
                        print(f"  [DEBUG] Skipping already processed message set in {conv_id}")
                        continue
                    
                    # Skip if this hash matches our last sent message (avoid replying to ourselves)
                    if bot._last_sent.get(conv_id) == msg_hash:
                        print(f"  [DEBUG] Skipping our own last message in {conv_id}")
                        continue
                    
                    message['conversation_id'] = conv_id
                    message['_msg_hash'] = msg_hash
                    unread_messages.append(message)
                    print(f"[DEBUG] Queued combined message from conversation: {conv_id}")
                else:
                    print(f"[DEBUG] No extractable client messages in conversation: {conv_id}")
            
            except Exception as e:
                print(f"Warning: Could not process conversation {href}: {type(e).__name__}: {e}")
                continue
        
        if not unread_messages:
            print("[DEBUG] No new unread messages found")
    
    except Exception as e:
        print(f"ERROR getting unread messages: {e}")
    
    return unread_messages


def extract_latest_message(bot) -> Optional[Dict]:
    """
    Extract the latest message from the currently open conversation.
    
    Args:
        bot: MessengerBot instance
    
    Returns:
        Dictionary with 'sender', 'text', and 'element' keys, or None
    """
    try:
        time.sleep(1)
        
        message_selectors = [
            'div[dir="auto"]',
            'span.x1lliihq',
            'div[role="row"] div[dir="auto"]',
        ]
        
        for selector in message_selectors:
            try:
                messages = bot.driver.find_elements(By.CSS_SELECTOR, selector)
                
                if messages:
                    latest = messages[-1]
                    text = latest.text.strip()
                    
                    if text:
                        sender = extract_sender_name(bot)
                        
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


def extract_sender_name(bot) -> str:
    """
    Extract sender name from the current conversation.
    
    Args:
        bot: MessengerBot instance
    
    Returns:
        Sender name or 'Unknown'
    """
    try:
        title = (bot.driver.title or "").strip()
        if " | " in title:
            return title.split(" | ")[0].strip()
        
        header_selectors = [
            'h1[dir="auto"]',
            'span[dir="auto"]',
            '[role="heading"]',
        ]
        
        for selector in header_selectors:
            try:
                element = bot.driver.find_element(By.CSS_SELECTOR, selector)
                name = element.text.strip()
                if name:
                    return name
            except NoSuchElementException:
                continue
    
    except Exception as e:
        print(f"Warning: Could not extract sender name: {e}")
    
    return "Unknown"


def is_message_from_us(bot, message_element) -> bool:
    """
    Determine if a message element is from us (the bot) or from the client.
    
    Messenger: sent bubbles have no solid background in the first 6 ancestors
    (they use a gradient from a CSS variable on a deeper wrapper). Received
    bubbles have a solid backgroundColor. So: background found → received;
    no background in 6 ancestors → sent by me.
    
    Args:
        bot: MessengerBot instance
        message_element: Selenium WebElement of the message (e.g. div[dir="auto"])
    
    Returns:
        True if the message is from us (sent by me), False if from client (received)
    """
    try:
        is_ours = bot.driver.execute_script("""
            function isSentByMe(msgEl) {
                var el = msgEl;
                for (var d = 0; d < 6; d++) {
                    if (!el) break;
                    var bg = getComputedStyle(el).backgroundColor;
                    var bgImg = getComputedStyle(el).backgroundImage;
                    if ((bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') ||
                        (bgImg && bgImg !== 'none')) {
                        return false;
                    }
                    el = el.parentElement;
                }
                return true;
            }
            return isSentByMe(arguments[0]);
        """, message_element)
        return is_ours
    except Exception as e:
        print(f"  Warning: Could not determine message ownership: {e}")
        return False


def extract_unanswered_client_messages(bot, conv_id: str = "") -> Optional[Dict]:
    """
    Extract all unanswered client messages since our last reply and combine them.
    
    This function:
    1. Gets all message elements in the conversation
    2. Identifies which are ours vs theirs
    3. Finds the last message from us
    4. Collects all client messages after our last message
    5. Combines them into a single text
    
    Args:
        bot: MessengerBot instance
        conv_id: Conversation ID for logging
    
    Returns:
        Dictionary with 'sender', 'text', and 'element' keys, or None if no client messages
    """
    try:
        time.sleep(1)
        
        # Try to find all message elements in the conversation
        message_selectors = [
            'div[role="row"] div[dir="auto"]',
            'div[dir="auto"]',
        ]
        
        all_messages: List[Tuple[object, str, bool]] = []  # (element, text, is_ours)
        
        for selector in message_selectors:
            try:
                message_elements = bot.driver.find_elements(By.CSS_SELECTOR, selector)
                
                if not message_elements:
                    continue
                
                print(f"  [DEBUG] Found {len(message_elements)} message elements with selector '{selector}'")
                
                # Extract text and determine ownership for each message
                for elem in message_elements:
                    text = elem.text.strip()
                    if not text:  # Skip empty messages
                        continue
                    
                    is_ours = is_message_from_us(bot, elem)
                    all_messages.append((elem, text, is_ours))
                
                # If we found messages with this selector, use them
                if all_messages:
                    break
                    
            except NoSuchElementException:
                continue
        
        if not all_messages:
            print(f"  [DEBUG] No messages found in conversation {conv_id}")
            return None
        
        print(f"  [DEBUG] Total messages in conversation: {len(all_messages)}")
        for i, (_, text, is_ours) in enumerate(all_messages):
            owner = "us" if is_ours else "client"
            print(f"  [DEBUG]   [{i}] {owner}: {text[:50]}...")
        
        # Find the index of the last message from us
        last_our_message_index = -1
        for i in range(len(all_messages) - 1, -1, -1):
            if all_messages[i][2]:  # is_ours
                last_our_message_index = i
                print(f"  [DEBUG] Last message from us at index {i}")
                break
        
        # Collect all client messages after our last message
        client_messages = []
        start_index = last_our_message_index + 1 if last_our_message_index >= 0 else 0
        
        for i in range(start_index, len(all_messages)):
            elem, text, is_ours = all_messages[i]
            if not is_ours:  # Client message
                client_messages.append(text)
        
        if not client_messages:
            print(f"  [DEBUG] No new client messages found after our last reply in {conv_id}")
            return None
        
        # Combine all client messages with newlines
        combined_text = "\n".join(client_messages)
        print(f"  [DEBUG] Combined {len(client_messages)} client message(s) into one: {combined_text[:100]}...")
        
        # Get sender name
        sender = extract_sender_name(bot)
        
        # Use the last client message element as reference
        last_client_element = all_messages[len(all_messages) - 1][0]
        
        return {
            'sender': sender,
            'text': combined_text,
            'element': last_client_element
        }
    
    except Exception as e:
        print(f"  ERROR extracting unanswered messages: {e}")
        import traceback
        traceback.print_exc()
        return None
