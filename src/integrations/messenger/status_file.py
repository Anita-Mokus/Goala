"""
Status file utilities.
Reads bot status from shared file (for standalone bot processes).
"""
import os
import json
from typing import Optional, Dict


def read_status_file() -> Optional[Dict]:
    """
    Read bot status from shared file (used when bot runs in another process).
    
    Returns:
        Dict with running, paused, message_count, last_message_timestamp, uptime_seconds,
        or None if file missing/invalid or process no longer alive.
    """
    from src.integrations.messenger.config import MessengerConfig
    path = MessengerConfig.STATUS_FILE
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    if not data.get("running"):
        return data
    pid = data.get("pid")
    if pid is not None:
        try:
            os.kill(pid, 0)
        except (OSError, TypeError):
            return {**data, "running": False}
    return data
