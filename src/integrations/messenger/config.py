"""
Configuration for Messenger bot integration.
Loads settings from environment variables.
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class MessengerConfig:
    """Configuration class for Messenger bot."""
    
    # Enable/disable bot
    ENABLED: bool = os.getenv("MESSENGER_ENABLED", "false").lower() == "true"
    
    # Chrome profile path (required for stealth)
    CHROME_PROFILE_PATH: Optional[str] = os.getenv("MESSENGER_CHROME_PROFILE_PATH")
    
    # Polling interval (randomized between min and max)
    CHECK_INTERVAL_MIN: int = int(os.getenv("MESSENGER_CHECK_INTERVAL_MIN", "10"))
    CHECK_INTERVAL_MAX: int = int(os.getenv("MESSENGER_CHECK_INTERVAL_MAX", "15"))
    
    # Response delay (randomized between min and max)
    RESPONSE_DELAY_MIN: int = int(os.getenv("MESSENGER_RESPONSE_DELAY_MIN", "2"))
    RESPONSE_DELAY_MAX: int = int(os.getenv("MESSENGER_RESPONSE_DELAY_MAX", "5"))
    
    # Goala RAG API endpoint
    API_URL: str = os.getenv("MESSENGER_API_URL", "http://localhost:8000/chat")
    
    # Status file for cross-process status (API vs standalone bot)
    STATUS_FILE: str = os.getenv("MESSENGER_STATUS_FILE", "/tmp/goala_messenger_status.json")

    # Conversation history window
    HISTORY_WINDOW_TURNS: int = int(os.getenv("MESSENGER_HISTORY_WINDOW_TURNS", "15"))
    HISTORY_MAX_CHARS: int = int(os.getenv("MESSENGER_HISTORY_MAX_CHARS", "12000"))

    # Group chat policy (group chats are disabled by default)
    ALLOW_GROUP_CHATS: bool = os.getenv("MESSENGER_ALLOW_GROUP_CHATS", "false").lower() == "true"
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        if not cls.ENABLED:
            return True
        
        if not cls.CHROME_PROFILE_PATH:
            print("ERROR: MESSENGER_CHROME_PROFILE_PATH is required when bot is enabled")
            return False
        
        # Skip file system validation in Docker (Chrome profile is on host)
        # The bot will run on the host machine, not inside Docker
        in_docker = os.path.exists('/.dockerenv')
        if not in_docker and not os.path.exists(cls.CHROME_PROFILE_PATH):
            print(f"ERROR: Chrome profile path does not exist: {cls.CHROME_PROFILE_PATH}")
            return False
        
        if cls.CHECK_INTERVAL_MIN > cls.CHECK_INTERVAL_MAX:
            print("ERROR: CHECK_INTERVAL_MIN must be <= CHECK_INTERVAL_MAX")
            return False
        
        if cls.RESPONSE_DELAY_MIN > cls.RESPONSE_DELAY_MAX:
            print("ERROR: RESPONSE_DELAY_MIN must be <= RESPONSE_DELAY_MAX")
            return False

        if cls.HISTORY_WINDOW_TURNS <= 0:
            print("ERROR: HISTORY_WINDOW_TURNS must be > 0")
            return False

        if cls.HISTORY_MAX_CHARS <= 0:
            print("ERROR: HISTORY_MAX_CHARS must be > 0")
            return False
        
        return True


# Chrome profile path hints for different platforms
CHROME_PROFILE_HINTS = {
    "Windows": r"C:\Users\{username}\AppData\Local\Google\Chrome\User Data",
    "Darwin": "~/Library/Application Support/Google/Chrome",
    "Linux": "~/.config/google-chrome"
}
