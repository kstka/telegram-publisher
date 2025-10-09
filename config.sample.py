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

# List of blocked groups
blocked_groups = []

# --- Group delay, message retention, and weekly post limit settings ---
# Use group usernames (e.g., '@mygroup') or numeric IDs (e.g., -1001234567890)
GROUPS = {
    'examplegroup1': {'delay': 0.5, 'keep_old': False, 'max_per_week': 5},  # 12 hours, old messages will be deleted, max 5 posts per week
    'examplegroup2': {'delay': 1, 'keep_old': True, 'max_per_week': 10},    # 1 day, old messages will be kept, max 10 posts per week
}

# --- Excludes items from being reposted in specific groups ---
EXCLUDES = {
    "group_username_1": ["item1", "item2"],
    "group_username_2": ("old_item",),
    "group_username_3": None,  # empty exclusions
}

# --- Optional: Sentry error reporting ---
USE_SENTRY = False
SENTRY_DNS = 'https://examplePublicKey@o0.ingest.sentry.io/0'
