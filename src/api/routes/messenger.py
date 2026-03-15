"""
FastAPI routes for Messenger bot control and monitoring.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import threading
import subprocess
import os

from src.integrations.messenger.registry import set_bot, get_bot, get_bot_thread, clear_bot
from src.integrations.messenger.status_file import read_status_file

router = APIRouter(prefix="/api/messenger", tags=["messenger"])


class MessengerStatusResponse(BaseModel):
    """Response model for bot status."""
    running: bool
    paused: bool
    message_count: int
    last_message_timestamp: Optional[str]
    uptime_seconds: int
    config_valid: bool


class MessengerActionResponse(BaseModel):
    """Response model for bot actions."""
    status: str
    message: str


@router.get("/status", response_model=MessengerStatusResponse)
def get_messenger_status():
    """
    Get current Messenger bot status.
    
    Returns:
        Bot status including running state, message count, and uptime
    """
    from src.integrations.messenger.config import MessengerConfig
    
    bot = get_bot()
    config_valid = MessengerConfig.validate()
    
    if not bot:
        # Bot may be running in another process (e.g. standalone); check status file
        file_status = read_status_file()
        if file_status is not None and file_status.get("running"):
            return MessengerStatusResponse(
                running=True,
                paused=file_status.get("paused", False),
                message_count=file_status.get("message_count", 0),
                last_message_timestamp=file_status.get("last_message_timestamp"),
                uptime_seconds=file_status.get("uptime_seconds", 0),
                config_valid=config_valid
            )
        return MessengerStatusResponse(
            running=False,
            paused=False,
            message_count=0,
            last_message_timestamp=None,
            uptime_seconds=0,
            config_valid=config_valid
        )
    
    status = bot.get_status()
    status['config_valid'] = config_valid
    return MessengerStatusResponse(**status)


@router.post("/start", response_model=MessengerActionResponse)
def start_messenger_bot():
    """
    Start the Messenger bot in background mode.
    
    Returns:
        Status confirmation
    """
    from src.integrations.messenger.config import MessengerConfig
    from src.integrations.messenger.bot import MessengerBot
    
    # Check if already running
    if get_bot() and get_bot().running:
        return MessengerActionResponse(
            status="already_running",
            message="Messenger bot is already running"
        )
    
    # Validate configuration
    if not MessengerConfig.ENABLED:
        raise HTTPException(
            status_code=400, 
            detail="Messenger bot is disabled. Set MESSENGER_ENABLED=true in .env"
        )
    
    if not MessengerConfig.validate():
        raise HTTPException(
            status_code=400,
            detail="Invalid configuration. Please check MESSENGER_CHROME_PROFILE_PATH in .env"
        )
    
    try:
        # Create bot instance
        bot_instance = MessengerBot()
        
        # Start bot in background thread
        bot_thread = threading.Thread(target=bot_instance.start, daemon=True)
        bot_thread.start()
        
        # Register bot
        set_bot(bot_instance, bot_thread)
        
        # Give the thread a moment to confirm it has started
        import time
        time.sleep(2)
        
        if bot_thread.is_alive():
            return MessengerActionResponse(
                status="started",
                message="Messenger bot has been started successfully"
            )
        else:
            raise Exception("Bot thread exited immediately — check server logs for errors")
    
    except Exception as e:
        clear_bot()
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")


@router.post("/stop", response_model=MessengerActionResponse)
def stop_messenger_bot():
    """
    Stop the Messenger bot.
    
    Returns:
        Status confirmation
    """
    bot = get_bot()
    
    if not bot:
        return MessengerActionResponse(
            status="not_running",
            message="Bot is not running"
        )
    
    if not bot.running:
        return MessengerActionResponse(
            status="not_running",
            message="Bot is not running"
        )
    
    try:
        bot.stop()
        clear_bot()
        
        return MessengerActionResponse(
            status="stopped",
            message="Messenger bot has been stopped"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop bot: {str(e)}")


@router.post("/pause", response_model=MessengerActionResponse)
def pause_messenger_bot():
    """
    Pause the Messenger bot.
    
    Stops processing messages but keeps the bot running.
    
    Returns:
        Status confirmation
    """
    bot = get_bot()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Messenger bot is not running")
    
    if not bot.running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    if bot.paused:
        return MessengerActionResponse(
            status="already_paused",
            message="Bot is already paused"
        )
    
    bot.pause()
    
    return MessengerActionResponse(
        status="paused",
        message="Messenger bot has been paused"
    )


@router.post("/resume", response_model=MessengerActionResponse)
def resume_messenger_bot():
    """
    Resume the Messenger bot.
    
    Continues processing messages if bot was paused.
    
    Returns:
        Status confirmation
    """
    bot = get_bot()
    
    if not bot:
        raise HTTPException(status_code=404, detail="Messenger bot is not running")
    
    if not bot.running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    if not bot.paused:
        return MessengerActionResponse(
            status="already_running",
            message="Bot is already running"
        )
    
    bot.resume()
    
    return MessengerActionResponse(
        status="resumed",
        message="Messenger bot has been resumed"
    )


@router.get("/login-redirect")
def messenger_login_redirect():
    """
    Redirect to Messenger login page.
    
    This allows users to log in to Messenger from the frontend.
    """
    return RedirectResponse(url="https://www.messenger.com")


@router.get("/debug")
def debug_messenger_bot():
    """
    Debug endpoint: inspects the live Messenger page and reports conversation links
    found in the sidebar along with their bold (unread) detection result.
    """
    from selenium.webdriver.common.by import By

    bot = get_bot()
    if not bot:
        return {"error": "Bot is not running"}
    if not bot.driver:
        return {"error": "Chrome driver not initialised yet"}

    result: dict = {
        "page_title": bot.driver.title,
        "current_url": bot.driver.current_url,
        "conversation_links": [],
        "selectors": {},
    }

    # Check all conversation links in the sidebar
    try:
        conv_links = bot.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/t/"], a[href*="/e2ee/t/"]')
        # Skip the first 4 fixed Facebook nav buttons (Chatek, Marketplace, Kérések, Archiválás)
        conversation_links = conv_links[4:]
        result["conversation_links_total"] = len(conversation_links)
        for link in conversation_links[:20]:  # cap at 20 to avoid huge responses
            try:
                is_bold = bot.driver.execute_script("""
                    var el = arguments[0];
                    var children = el.querySelectorAll('*');
                    for (var i = 0; i < children.length; i++) {
                        var fw = window.getComputedStyle(children[i]).fontWeight;
                        if (fw === '700' || fw === 'bold') { return true; }
                    }
                    return false;
                """, link)
                result["conversation_links"].append({
                    "href": link.get_attribute("href"),
                    "aria_label": (link.get_attribute("aria-label") or "")[:80],
                    "text": (link.text or "")[:80],
                    "is_unread_bold": is_bold,
                })
            except Exception as exc:
                result["conversation_links"].append({"error": str(exc)})
    except Exception as exc:
        result["conversation_links_error"] = str(exc)

    # Also probe a few extra selectors for reference
    extra_selectors = [
        'div[contenteditable="true"][role="textbox"]',
        'div[dir="auto"]',
        '[aria-label*="olvasatlan"]',
        '[aria-label*="unread"]',
    ]
    for selector in extra_selectors:
        try:
            elements = bot.driver.find_elements(By.CSS_SELECTOR, selector)
            result["selectors"][selector] = {
                "count": len(elements),
                "samples": [(el.get_attribute("aria-label") or el.text or "")[:80] for el in elements[:5]],
            }
        except Exception as exc:
            result["selectors"][selector] = {"error": str(exc)}

    return result


@router.get("/diagnostics")
def get_chrome_diagnostics():
    """
    Get Chrome environment diagnostics.
    
    Returns information about Chrome, ChromeDriver, X11, and system setup.
    """
    import subprocess
    import os
    
    diagnostics = {}
    
    # Check Chrome version
    try:
        chrome_version = subprocess.check_output(
            ["google-chrome", "--version"],
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
        diagnostics["chrome_version"] = chrome_version
    except Exception as e:
        diagnostics["chrome_version"] = f"Error: {str(e)}"
    
    # Check ChromeDriver version
    try:
        chromedriver_version = subprocess.check_output(
            ["chromedriver", "--version"],
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
        diagnostics["chromedriver_version"] = chromedriver_version
    except Exception as e:
        diagnostics["chromedriver_version"] = f"Error: {str(e)}"
    
    # Check DISPLAY environment variable
    diagnostics["display"] = os.getenv("DISPLAY", "Not set")
    
    # Check if X11 is running
    try:
        xdpyinfo_output = subprocess.check_output(
            ["xdpyinfo", "-display", ":99"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5
        )
        diagnostics["x11_running"] = "Yes"
        diagnostics["x11_info"] = xdpyinfo_output.split('\n')[0:3]
    except Exception as e:
        diagnostics["x11_running"] = "No"
        diagnostics["x11_error"] = str(e)
    
    # Check Chrome profile directory
    profile_path = os.getenv("MESSENGER_CHROME_PROFILE_PATH", "/app/chrome_profile")
    diagnostics["chrome_profile_path"] = profile_path
    diagnostics["chrome_profile_exists"] = os.path.exists(profile_path)
    diagnostics["chrome_profile_writable"] = os.access(profile_path, os.W_OK) if os.path.exists(profile_path) else False
    
    # Check ChromeDriver log
    if os.path.exists("/tmp/chromedriver.log"):
        try:
            with open("/tmp/chromedriver.log", "r") as f:
                log_lines = f.readlines()
                diagnostics["chromedriver_log"] = log_lines[-20:]  # Last 20 lines
        except Exception as e:
            diagnostics["chromedriver_log"] = f"Error reading log: {str(e)}"
    else:
        diagnostics["chromedriver_log"] = "Log file not found"
    
    return diagnostics
