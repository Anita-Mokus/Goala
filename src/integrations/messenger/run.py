"""
Standalone runner script for Messenger bot.
Can be run directly or as a background service.
"""
import sys
import time
import signal
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.integrations.messenger.bot import MessengerBot
from src.integrations.messenger.config import MessengerConfig
from src.integrations.messenger.stealth_driver import print_chrome_profile_instructions


# Global bot instance
bot = None


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    print("\n\nShutdown signal received...")
    if bot:
        bot.stop()
    sys.exit(0)


def run_bot_standalone():
    """Run the bot in standalone mode (foreground)."""
    global bot
    
    print("\n" + "="*80)
    print("GOALA MESSENGER BOT - STANDALONE MODE")
    print("="*80 + "\n")
    
    # Validate configuration
    if not MessengerConfig.ENABLED:
        print("ERROR: Messenger bot is disabled in configuration.")
        print("Set MESSENGER_ENABLED=true in .env to enable the bot.\n")
        return
    
    if not MessengerConfig.validate():
        print("\nERROR: Invalid configuration. Please check your .env file.\n")
        print_chrome_profile_instructions()
        return
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start bot
    try:
        bot = MessengerBot()
        bot.start()  # This will block until bot is stopped
    except KeyboardInterrupt:
        print("\n\nKeyboard interrupt...")
        if bot:
            bot.stop()
    except Exception as e:
        print(f"\n\nERROR: {e}")
        if bot:
            bot.stop()
        raise


def run_bot_background():
    """Run the bot in background mode (daemon thread)."""
    global bot
    
    print("Starting Messenger bot in background mode...")
    
    # Validate configuration
    if not MessengerConfig.ENABLED:
        print("ERROR: Messenger bot is disabled in configuration.")
        return None
    
    if not MessengerConfig.validate():
        print("ERROR: Invalid configuration.")
        return None
    
    # Create bot
    bot = MessengerBot()
    
    # Start bot in daemon thread
    bot_thread = threading.Thread(target=bot.start, daemon=True)
    bot_thread.start()
    
    # Wait a moment for startup
    time.sleep(3)
    
    if bot.running:
        print("✓ Messenger bot started successfully in background")
        return bot
    else:
        print("✗ Failed to start Messenger bot")
        return None


def get_bot_instance():
    """Get the global bot instance (for integration with FastAPI)."""
    return bot


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--background":
            print("Background mode not supported in standalone script.")
            print("Use run_bot_background() function from Python code instead.")
            sys.exit(1)
        elif sys.argv[1] == "--help":
            print("\nUsage: python run.py [OPTIONS]\n")
            print("Options:")
            print("  --help         Show this help message")
            print("  --instructions Show Chrome profile setup instructions")
            print("\nDefault: Run bot in foreground mode (press Ctrl+C to stop)\n")
            sys.exit(0)
        elif sys.argv[1] == "--instructions":
            print_chrome_profile_instructions()
            sys.exit(0)
    
    # Run in standalone mode
    run_bot_standalone()
