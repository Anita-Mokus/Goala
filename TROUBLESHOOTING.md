# Troubleshooting Guide

## Chrome Crashes / "session not created: Chrome instance exited"

### Symptoms
- Error message: `selenium.common.exceptions.SessionNotCreatedException: Message: session not created: Chrome instance exited`
- Bot fails to start even though it worked before
- Zombie Chrome processes (`<defunct>`) visible in container

### Root Cause
Chrome crashes leave behind:
1. **Zombie processes** that hold locks on the profile
2. **Lock files** (`Singleton*`, `.com.google.Chrome.*`) that prevent new Chrome instances
3. **Accumulated failures** from multiple restart attempts

### Quick Fix

Run these commands to clean up and restart:

```bash
# Clean Chrome profile lock files
docker compose exec api bash -c "rm -rf /app/chrome_profile/Singleton* /app/chrome_profile/Default/Singleton* /app/chrome_profile/.com.google.Chrome.* /app/chrome_profile/Default/.com.google.Chrome.*"

# Restart the API container to clear zombie processes
docker compose restart api
```