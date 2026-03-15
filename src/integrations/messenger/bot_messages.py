"""
Messenger bot message detection and extraction.
Handles unread message detection and content extraction.
"""
import time
import hashlib
from typing import List, Dict, Optional
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
                message = extract_latest_message(bot)
                
                if message:
                    msg_hash = hashlib.sha256(message['text'].encode(errors='replace')).hexdigest()[:16]
                    message_key = (conv_id, msg_hash)
                    
                    if message_key in bot._processed_messages:
                        continue
                    if bot._last_sent.get(conv_id) == msg_hash:
                        continue
                    
                    message['conversation_id'] = conv_id
                    message['_msg_hash'] = msg_hash
                    unread_messages.append(message)
                    print(f"[DEBUG] Queued message from conversation: {conv_id}")
                else:
                    print(f"[DEBUG] No extractable message in conversation: {conv_id}")
            
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
