"""
Stealth Chrome WebDriver configuration for Messenger bot.
Implements manual stealth techniques without external packages.
"""
import logging
import os
import platform
import shutil
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)


def _build_chrome_options(profile_path: str) -> Options:
    """Build Chrome options with stealth and Docker stability flags."""
    options = Options()

    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--profile-directory=Default")

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.add_argument("--window-size=1920,1080")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-crash-reporter")
    options.add_argument("--disable-in-process-stack-traces")
    options.add_argument("--log-level=3")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")

    options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2
    })

    if os.path.exists("/usr/bin/google-chrome"):
        options.binary_location = "/usr/bin/google-chrome"

    return options


def _launch_driver(options: Options, chrome_driver_path: Optional[str]) -> webdriver.Chrome:
    """Attempt a single Chrome WebDriver launch, logging the chromedriver output on failure."""
    log_path = "/tmp/chromedriver.log"
    kwargs = {"executable_path": chrome_driver_path} if chrome_driver_path else {}
    service = Service(**kwargs)
    # Pass log path directly to the chromedriver binary so the file is always created
    service.service_args = [f"--log-path={log_path}", "--verbose"]

    try:
        return webdriver.Chrome(service=service, options=options)
    except Exception:
        try:
            with open(log_path, "r") as f:
                logger.error("ChromeDriver verbose log:\n%s", f.read()[-4000:])
        except OSError:
            logger.warning("ChromeDriver log not found at %s", log_path)
        raise


def _reset_profile(profile_path: str) -> None:
    """Delete profile contents so Chrome starts fresh (Messenger login will be lost)."""
    logger.warning("Clearing Chrome profile at %s — login session will be lost", profile_path)
    if os.path.exists(profile_path):
        shutil.rmtree(profile_path)
    os.makedirs(profile_path, mode=0o777)
    open(os.path.join(profile_path, "First Run"), "w").close()
    logger.warning("Chrome profile cleared — please log in to Messenger again after the bot starts")


def create_stealth_driver(profile_path: str, chrome_driver_path: Optional[str] = None) -> webdriver.Chrome:
    """
    Create a Chrome WebDriver with stealth configuration.

    Key stealth features:
    - Persistent Chrome profile (real browser history/cookies)
    - Remove navigator.webdriver flag via CDP
    - Disable automation flags
    - Visible mode (NOT headless)
    - Default user agent (no override)

    If Chrome fails to start with the existing profile (e.g. after a Chrome
    version upgrade), the profile is automatically cleared and one retry is
    attempted so the bot recovers without manual intervention.

    Args:
        profile_path: Path to Chrome user data directory
        chrome_driver_path: Optional path to chromedriver executable

    Returns:
        Configured Chrome WebDriver instance
    """
    if not os.path.exists(profile_path):
        os.makedirs(profile_path, mode=0o777)
    first_run = os.path.join(profile_path, "First Run")
    if not os.path.exists(first_run):
        open(first_run, "w").close()

    if not os.getenv("DISPLAY"):
        os.environ["DISPLAY"] = ":99"

    logger.info("Initializing Chrome (profile=%s, DISPLAY=%s)", profile_path, os.getenv("DISPLAY"))

    options = _build_chrome_options(profile_path)
    try:
        driver = _launch_driver(options, chrome_driver_path)
        logger.info("Chrome WebDriver created successfully (visible mode)")
    except Exception as first_err:
        logger.warning("Chrome startup failed in visible mode: %s", first_err)

        # Retry 1: profile may be incompatible with an updated Chrome version
        logger.warning("Retry 1: clearing profile and retrying in visible mode...")
        _reset_profile(profile_path)
        options = _build_chrome_options(profile_path)
        try:
            driver = _launch_driver(options, chrome_driver_path)
            logger.info("Chrome WebDriver created successfully (visible mode, fresh profile)")
        except Exception as second_err:
            # Retry 2: bypass X11/Xvfb entirely with headless=new
            logger.warning("Retry 1 failed: %s", second_err)
            logger.warning("Retry 2: switching to --headless=new to bypass display dependency...")
            options = _build_chrome_options(profile_path)
            options.add_argument("--headless=new")
            driver = _launch_driver(options, chrome_driver_path)
            logger.info("Chrome WebDriver created successfully (headless=new fallback)")
    
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
