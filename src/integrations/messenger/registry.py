"""
Bot instance registry.
Manages global bot instance and thread state.
"""
from typing import Optional, Tuple
import threading

# Global bot state
_bot_instance = None
_bot_thread = None


def set_bot(bot, thread: Optional[threading.Thread] = None):
    """
    Set the global bot instance and optional thread.
    
    Args:
        bot: MessengerBot instance
        thread: Optional thread running the bot
    """
    global _bot_instance, _bot_thread
    _bot_instance = bot
    _bot_thread = thread


def get_bot():
    """
    Get the global bot instance.
    
    Returns:
        MessengerBot instance or None
    """
    return _bot_instance


def get_bot_thread() -> Optional[threading.Thread]:
    """
    Get the bot thread.
    
    Returns:
        Thread instance or None
    """
    return _bot_thread


def clear_bot():
    """Clear the global bot instance and thread."""
    global _bot_instance, _bot_thread
    _bot_instance = None
    _bot_thread = None
