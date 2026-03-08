"""
Stealth Chrome WebDriver configuration for Messenger bot.
Implements manual stealth techniques without external packages.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from typing import Optional
import platform
import os


def create_stealth_driver(profile_path: str, chrome_driver_path: Optional[str] = None) -> webdriver.Chrome:
    """
    Create a Chrome WebDriver with stealth configuration.
    
    Key stealth features:
    - Persistent Chrome profile (real browser history/cookies)
    - Remove navigator.webdriver flag via CDP
    - Disable automation flags
    - Visible mode (NOT headless)
    - Default user agent (no override)
    
    Args:
        profile_path: Path to Chrome user data directory
        chrome_driver_path: Optional path to chromedriver executable
        
    Returns:
        Configured Chrome WebDriver instance
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Ensure profile directory exists and has a minimal structure
    if not os.path.exists(profile_path):
        os.makedirs(profile_path, mode=0o777)
        logger.info(f"Created Chrome profile directory: {profile_path}")
    
    # Create First Run file to prevent Chrome first-run setup
    first_run_file = os.path.join(profile_path, "First Run")
    if not os.path.exists(first_run_file):
        with open(first_run_file, 'w') as f:
            f.write("")
        logger.info("Created First Run file to skip Chrome setup")
    
    options = Options()
    
    # Use persistent Chrome profile (MOST IMPORTANT for stealth)
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")
    
    # Disable automation flags
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Window configuration
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    
    # Critical Docker/Linux flags
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Additional stability flags
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-setuid-sandbox")
    
    # Prevent crashes
    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-in-process-stack-traces")
    options.add_argument("--log-level=3")
    
    # Skip first-run prompts
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    
    # Disable infobars and notifications
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2
    })
    
    # Ensure DISPLAY is set for X11
    if not os.getenv("DISPLAY"):
        os.environ["DISPLAY"] = ":99"
        logger.info("Set DISPLAY environment variable to :99")
    
    # Set binary location if in Docker
    if os.path.exists("/usr/bin/google-chrome"):
        options.binary_location = "/usr/bin/google-chrome"
        logger.info(f"Using Chrome binary: {options.binary_location}")
    
    # Log configuration
    logger.info(f"Chrome profile path: {profile_path}")
    logger.info(f"DISPLAY: {os.getenv('DISPLAY')}")
    
    # Create service with verbose logging
    try:
        if chrome_driver_path:
            service = Service(chrome_driver_path, log_output="/tmp/chromedriver.log")
            service.service_args = ['--verbose']
            logger.info(f"Using ChromeDriver: {chrome_driver_path}")
            driver = webdriver.Chrome(service=service, options=options)
        else:
            service = Service(log_output="/tmp/chromedriver.log")
            service.service_args = ['--verbose']
            driver = webdriver.Chrome(service=service, options=options)
        
        logger.info("Chrome WebDriver created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create Chrome WebDriver: {e}")
        # Try to read chromedriver log for more details
        try:
            with open("/tmp/chromedriver.log", "r") as f:
                log_content = f.read()
                logger.error(f"ChromeDriver log:\n{log_content}")
        except:
            pass
        raise
    
    # Remove navigator.webdriver flag using CDP (Chrome DevTools Protocol)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })
    
    return driver


def get_default_chrome_profile_path() -> str:
    """
    Get the default Chrome profile path for the current platform.
    
    Returns:
        Path to Chrome user data directory
        
    Note:
        This returns the main Chrome profile directory.
        Create a dedicated profile for the bot to avoid conflicts.
    """
    system = platform.system()
    
    if system == "Windows":
        import os
        username = os.getenv("USERNAME", "User")
        return f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data"
    elif system == "Darwin":  # macOS
        import os
        home = os.path.expanduser("~")
        return f"{home}/Library/Application Support/Google/Chrome"
    elif system == "Linux":
        import os
        home = os.path.expanduser("~")
        return f"{home}/.config/google-chrome"
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


def print_chrome_profile_instructions():
    """Print instructions for setting up Chrome profile."""
    print("\n" + "="*80)
    print("CHROME PROFILE SETUP INSTRUCTIONS")
    print("="*80)
    print()
    print("To use the Messenger bot, you need a Chrome profile with Messenger logged in.")
    print()
    print("STEP 1: Find or create a Chrome profile")
    print("-" * 80)
    
    system = platform.system()
    if system == "Windows":
        print("  Default location: C:\\Users\\{your_username}\\AppData\\Local\\Google\\Chrome\\User Data")
    elif system == "Darwin":
        print("  Default location: ~/Library/Application Support/Google/Chrome")
    elif system == "Linux":
        print("  Default location: ~/.config/google-chrome")
    
    print()
    print("STEP 2: Create a dedicated profile (recommended)")
    print("-" * 80)
    print("  1. Open Chrome")
    print("  2. Click your profile icon (top right)")
    print("  3. Click 'Add' to create a new profile")
    print("  4. Name it 'Goala Bot' or similar")
    print("  5. The profile will be saved in a subfolder like 'Profile 1', 'Profile 2', etc.")
    print()
    print("STEP 3: Log in to Messenger")
    print("-" * 80)
    print("  1. In the new profile, go to https://messenger.com")
    print("  2. Log in with your Facebook account")
    print("  3. Make sure 'Stay logged in' is checked")
    print("  4. Close Chrome")
    print()
    print("STEP 4: Update .env file")
    print("-" * 80)
    print("  Set MESSENGER_CHROME_PROFILE_PATH to the full path, including profile folder:")
    
    if system == "Windows":
        print("  Example: C:\\Users\\YourName\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1")
    elif system == "Darwin":
        print("  Example: /Users/YourName/Library/Application Support/Google/Chrome/Profile 1")
    elif system == "Linux":
        print("  Example: /home/yourname/.config/google-chrome/Profile 1")
    
    print()
    print("="*80)
    print()
