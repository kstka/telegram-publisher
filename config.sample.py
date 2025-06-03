# config.sample.py

# Rename this file to config.py and fill in your actual values before running the script.

# --- Telegram API credentials ---
TELEGRAM_API_ID = 123456               # Replace with your Telegram API ID
TELEGRAM_API_HASH = 'your_api_hash'    # Replace with your Telegram API hash

# Session name (the session file will be saved to ./sessions/)
TELEGRAM_SESSION_NAME = 'publisher_session'

# --- Optional: Telegram client app identity ---
DEVICE_MODEL = "Desktop"
SYSTEM_VERSION = "Windows 10"
APP_VERSION = "4.12.2 x64"
LANG_CODE = "en"
SYSTEM_LANG_CODE = "en-US"

# --- Group delay settings (in days) ---
# Use group usernames (e.g., '@mygroup') or numeric IDs (e.g., -1001234567890)
GROUPS = {
    'examplegroup1': 0.5,   # 12 hours
    'examplegroup2': 1,     # 1 day
}

# --- Optional: Sentry error reporting ---
USE_SENTRY = False
SENTRY_DNS = 'https://examplePublicKey@o0.ingest.sentry.io/0'
