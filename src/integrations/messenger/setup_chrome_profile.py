"""
Chrome Profile Setup Helper for Messenger Bot.
Helps users find their Chrome profile path and set up a dedicated profile.
"""
import os
import sys
import platform
from pathlib import Path


def get_chrome_user_data_dir():
    """Get the default Chrome user data directory for the current platform."""
    system = platform.system()
    
    if system == "Windows":
        username = os.getenv("USERNAME", "User")
        return Path(f"C:/Users/{username}/AppData/Local/Google/Chrome/User Data")
    elif system == "Darwin":  # macOS
        home = Path.home()
        return home / "Library/Application Support/Google/Chrome"
    elif system == "Linux":
        home = Path.home()
        return home / ".config/google-chrome"
    else:
        return None


def list_chrome_profiles():
    """List all Chrome profiles found in the user data directory."""
    user_data_dir = get_chrome_user_data_dir()
    
    if not user_data_dir or not user_data_dir.exists():
        print(f"❌ Chrome user data directory not found: {user_data_dir}")
        return []
    
    print(f"✓ Chrome user data directory: {user_data_dir}\n")
    
    profiles = []
    
    # Check Default profile
    default_profile = user_data_dir / "Default"
    if default_profile.exists():
        profiles.append(("Default", default_profile))
    
    # Check numbered profiles (Profile 1, Profile 2, etc.)
    for item in user_data_dir.iterdir():
        if item.is_dir() and item.name.startswith("Profile "):
            profiles.append((item.name, item))
    
    return profiles


def print_setup_instructions():
    """Print comprehensive setup instructions."""
    print("\n" + "="*80)
    print("MESSENGER BOT - CHROME PROFILE SETUP")
    print("="*80 + "\n")
    
    # Step 1: Find existing profiles
    print("STEP 1: Available Chrome Profiles")
    print("-" * 80)
    
    profiles = list_chrome_profiles()
    
    if profiles:
        print(f"Found {len(profiles)} Chrome profile(s):\n")
        for i, (name, path) in enumerate(profiles, 1):
            print(f"  {i}. {name}")
            print(f"     Path: {path}\n")
    else:
        print("No Chrome profiles found.\n")
    
    # Step 2: Create dedicated profile
    print("\nSTEP 2: Create a Dedicated Profile (Recommended)")
    print("-" * 80)
    print("It's recommended to create a new Chrome profile specifically for the bot.")
    print("This keeps bot activity separate from your personal browsing.\n")
    print("To create a new profile:")
    print("  1. Open Google Chrome")
    print("  2. Click your profile icon in the top-right corner")
    print("  3. Click 'Add' to create a new profile")
    print("  4. Name it 'Goala Bot' or similar")
    print("  5. A new Chrome window will open with the new profile")
    print("  6. The new profile will appear as 'Profile X' in the list above\n")
    
    # Step 3: Log in to Messenger
    print("STEP 3: Log In to Messenger")
    print("-" * 80)
    print("In the new Chrome profile:")
    print("  1. Go to https://messenger.com")
    print("  2. Log in with your Facebook account")
    print("  3. Make sure 'Stay logged in' is checked")
    print("  4. Close Chrome completely\n")
    
    # Step 4: Update .env
    print("STEP 4: Update .env File")
    print("-" * 80)
    print("Set the following environment variable in your .env file:\n")
    
    if profiles:
        print("Example (using one of your profiles):\n")
        example_profile = profiles[-1][1]  # Use the last profile as example
        print(f"MESSENGER_CHROME_PROFILE_PATH={example_profile}\n")
    else:
        user_data_dir = get_chrome_user_data_dir()
        if user_data_dir:
            print(f"MESSENGER_CHROME_PROFILE_PATH={user_data_dir}/Profile 1\n")
    
    print("Also make sure to enable the bot:\n")
    print("MESSENGER_ENABLED=true\n")
    
    # Step 5: Test
    print("STEP 5: Test the Bot")
    print("-" * 80)
    print("Run the bot to test your configuration:")
    print("  python -m src.integrations.messenger.run\n")
    print("The bot should:")
    print("  ✓ Open Chrome with your profile")
    print("  ✓ Navigate to messenger.com")
    print("  ✓ Detect that you're logged in")
    print("  ✓ Start monitoring for messages\n")
    
    print("="*80 + "\n")


def validate_profile_path(path_str):
    """Validate a Chrome profile path."""
    path = Path(path_str)
    
    print(f"\nValidating profile path: {path}")
    
    if not path.exists():
        print(f"❌ Path does not exist: {path}")
        return False
    
    if not path.is_dir():
        print(f"❌ Path is not a directory: {path}")
        return False
    
    # Check for Chrome profile indicators
    preferences_file = path / "Preferences"
    if not preferences_file.exists():
        print(f"⚠️  Warning: Preferences file not found. This may not be a valid Chrome profile.")
        print(f"   Expected: {preferences_file}")
        return False
    
    print("✓ Valid Chrome profile path!")
    return True


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--validate":
            if len(sys.argv) < 3:
                print("Usage: python setup_chrome_profile.py --validate <path>")
                sys.exit(1)
            
            path = sys.argv[2]
            valid = validate_profile_path(path)
            sys.exit(0 if valid else 1)
        elif sys.argv[1] == "--help":
            print("\nUsage: python setup_chrome_profile.py [OPTIONS]\n")
            print("Options:")
            print("  --help              Show this help message")
            print("  --validate <path>   Validate a Chrome profile path")
            print("\nDefault: Show setup instructions and list available profiles\n")
            sys.exit(0)
    
    # Default: show instructions
    print_setup_instructions()


if __name__ == "__main__":
    main()
