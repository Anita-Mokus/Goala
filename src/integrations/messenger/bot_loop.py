"""
Messenger bot main loop.
Handles continuous monitoring and message processing cycle.
"""
import time
import random
from datetime import datetime


def run_main_loop(bot):
    """
    Main bot loop - continuously monitor and respond to messages.
    
    Args:
        bot: MessengerBot instance
    """
    while bot.running:
        try:
            # Check if paused
            if bot.paused:
                time.sleep(1)
                continue
            
            # Check for "process unread now" trigger (from API)
            with bot._lock:
                if bot._process_unread_now_requested:
                    bot._process_unread_now_requested = False
            
            # Poll for unread messages
            from src.integrations.messenger.bot_messages import get_unread_messages
            unread_messages = get_unread_messages(bot)
            
            if unread_messages:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(unread_messages)} unread message(s) to process")
            
            # Process each unread message
            for message in unread_messages:
                if not bot.running or bot.paused:
                    break
                
                from src.integrations.messenger.bot_actions import process_message
                process_message(bot, message)
            
            # Interruptible delay so "process unread now" can wake us
            delay = random.uniform(
                bot.config.CHECK_INTERVAL_MIN,
                bot.config.CHECK_INTERVAL_MAX
            )
            bot._sleep_event.clear()
            bot._sleep_event.wait(timeout=delay)
            
        except KeyboardInterrupt:
            print("\n\nKeyboard interrupt received. Stopping bot...")
            bot.stop()
            break
        except Exception as e:
            print(f"ERROR in main loop: {e}")
            print("Continuing operation...")
            time.sleep(5)
