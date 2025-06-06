import os
import json
import time
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import DeleteMessagesRequest as ChannelDeleteMessagesRequest
from loguru import logger
import config

ITEMS_DIR = 'items'
SESSIONS_DIR = 'sessions'
STATE_FILE = 'state.json'
DEFAULT_POST_DELAY_DAYS = 7

logger.add("logs/main.log", encoding="utf8", rotation="1 week", retention="4 weeks")
logger.add("logs/debug.log", level='DEBUG', encoding="utf8", rotation="1 week", retention="4 weeks")

def use_sentry():
    try:
        if config.USE_SENTRY:
            import sentry_sdk
            sentry_sdk.init(dsn=config.SENTRY_DNS)
    except NameError:
        pass

def load_state():
    logger.debug("Loading state from file...")
    return json.load(open(STATE_FILE)) if os.path.exists(STATE_FILE) else {}

def save_state(state):
    logger.debug("Saving updated state to file...")
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def get_item_post_delay(item_path, default_delay=DEFAULT_POST_DELAY_DAYS):
    delay_path = os.path.join(item_path, 'delay.txt')
    if os.path.exists(delay_path):
        try:
            with open(delay_path) as f:
                days = float(f.read().strip())
                logger.debug(f"Found delay.txt for '{item_path}': {days} days")
                return int(days * 86400)
        except Exception as e:
            logger.warning(f"Failed to read delay.txt in {item_path}: {e}")
    logger.debug(f"No delay.txt found for '{item_path}', using default: {default_delay} days")
    return default_delay * 86400

def get_description_and_photos(item_path):
    description_path = os.path.join(item_path, 'description.txt')
    photos = sorted(
        os.path.join(item_path, f)
        for f in os.listdir(item_path)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    )
    description = ""
    if os.path.exists(description_path):
        try:
            with open(description_path, encoding='utf-8') as f:
                description = f.read().strip()
        except Exception as e:
            logger.warning(f"Failed to read description.txt in {item_path}: {e}")
    return description, photos

def get_groups_and_delays():
    logger.debug("Reading group delays from config...")
    return [(group, delay * 86400) for group, delay in config.GROUPS.items()]

def post_item(client, group, item_path, old_post_ids):
    description, photos = get_description_and_photos(item_path)
    if not photos:
        logger.warning(f"[SKIP] No photos found in {item_path}.")
        return None

    # delete old album messages
    if old_post_ids:
        try:
            logger.info(f"Deleting previous messages in {group}: {old_post_ids}")
            client(ChannelDeleteMessagesRequest(group, old_post_ids))
        except Exception as e:
            logger.error(f"Failed to delete previous messages in {group}: {e}")

    # send new album
    try:
        logger.info(f"Sending new post to {group} from {item_path}")
        result = client.send_file(group, photos, caption=description, force_document=False)
        if not isinstance(result, list):
            return [result.id]
        else:
            return [msg.id for msg in result]
    except Exception as e:
        logger.error(f"Failed to send post to {group} from {item_path}: {e}")
        return None

def main():
    use_sentry()

    now = int(time.time())
    state = load_state()

    with TelegramClient(
        os.path.join(SESSIONS_DIR, config.TELEGRAM_SESSION_NAME),
        config.TELEGRAM_API_ID,
        config.TELEGRAM_API_HASH,
        device_model=config.DEVICE_MODEL,
        system_version=config.SYSTEM_VERSION,
        app_version=config.APP_VERSION,
        system_lang_code=config.SYSTEM_LANG_CODE,
        lang_code=config.LANG_CODE
    ) as client:
        for group_name, group_delay in get_groups_and_delays():
            group_state = state.get(group_name, {})
            last_group_post = group_state.get('last_group_post', 0)
            logger.debug(f"Checking group {group_name}, last post was {now - last_group_post} sec ago")

            if now - last_group_post < group_delay:
                logger.debug(f"[SKIP] Group {group_name}: delay not reached yet.")
                continue

            candidates = []
            for item_name in os.listdir(ITEMS_DIR):
                item_path = os.path.join(ITEMS_DIR, item_name)
                if not os.path.isdir(item_path):
                    continue
                cooldown = get_item_post_delay(item_path)
                item_state = group_state.get('items', {}).get(item_name, {})
                last_post_time = item_state.get('last_post_time', 0)
                if now - last_post_time >= cooldown:
                    logger.debug(f"Item '{item_name}' is ready for posting to {group_name}")
                    candidates.append((cooldown, item_name, item_path, item_state.get('last_post_ids')))
                else:
                    logger.debug(f"[SKIP] Item '{item_name}' not ready (cooldown: {cooldown}s)")

            if not candidates:
                logger.debug(f"[SKIP] No suitable items found for group {group_name}")
                continue

            candidates.sort(reverse=True)
            _, item_name, item_path, old_post_ids = candidates[0]
            new_post_ids = post_item(client, group_name, item_path, old_post_ids)

            if new_post_ids:
                logger.success(f"[OK] Published '{item_name}' to {group_name}, msg_ids={new_post_ids}")
                group_state.setdefault('items', {})[item_name] = {
                    'last_post_time': now,
                    'last_post_ids': new_post_ids
                }
                group_state['last_group_post'] = now
                state[group_name] = group_state

    save_state(state)
    logger.debug("Script execution completed.")

if __name__ == '__main__':
    main()
