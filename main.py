import os
import json
import time
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import DeleteMessagesRequest as ChannelDeleteMessagesRequest
from loguru import logger
import config
from config import blocked_groups

ITEMS_DIR = 'items'
SESSIONS_DIR = 'sessions'
STATE_FILE = 'state.json'
DEFAULT_POST_DELAY_DAYS = 7
SECONDS_IN_DAY = 86400

logger.add("logs/main.log", level="INFO", encoding="utf8", rotation="1 week", retention="4 weeks")
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
                return int(days * SECONDS_IN_DAY)
        except Exception as e:
            logger.warning(f"Failed to read delay.txt in {item_path}: {e}")
    logger.debug(f"No delay.txt found for '{item_path}', using default: {default_delay} days")
    return default_delay * SECONDS_IN_DAY

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

def get_groups_settings():
    logger.debug("Reading group settings from config...")
    return [
        (group,
         settings.get('delay', 1) * SECONDS_IN_DAY,
         settings.get('keep_old', False),
         settings.get('max_per_week', 100))
        for group, settings in config.GROUPS.items()
    ]

def cleanup_item(client, group, old_post_ids, keep_old):
    # delete old album messages, if keep_old is false
    if old_post_ids and not keep_old:
        try:
            logger.info(f"Deleting previous messages in {group}: {old_post_ids}")
            client(ChannelDeleteMessagesRequest(group, old_post_ids))
            return old_post_ids
        except Exception as e:
            logger.error(f"Failed to delete previous messages in {group}: {e}")
            return None
    return None

def post_item(client, group, item_path):
    description, photos = get_description_and_photos(item_path)

    # Skip if no photos found
    if not photos:
        logger.warning(f"[SKIP] No photos found in {item_path}.")
        return None

    # Skip if no description found
    if not description:
        logger.warning(f"[SKIP] No description found in {item_path}.")
        return None

    # Check if the group is blocked due to a previous error
    if group in blocked_groups:
        logger.warning(f"[SKIP] Group {group} blocked because of previous error.")
        return None

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
        # Block the group if the error indicates we can't write in the chat
        if "can't write in this chat" in str(e).lower():
            blocked_groups.append(group)
            logger.warning(f"[BLOCK] Group {group} blocked due to error: {e}")
        return None

def main():
    use_sentry()

    now = int(time.time())
    state = load_state()
    previous_state_json = json.dumps(state, sort_keys=True)

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
        for group_name, group_delay, keep_old, max_per_week in get_groups_settings():

            # skip blocked groups
            if group_name in blocked_groups:
                logger.warning(f"[SKIP] Group {group_name} blocked, skipping.")
                continue

            # get group state
            group_state = state.get(group_name, {})

            # enforce max posts per week
            week_ago = now - 7 * SECONDS_IN_DAY
            items_state = group_state.get('items', {})
            posts_last_week = 0
            for item in items_state.values():
                if item.get('last_post_time', 0) >= week_ago:
                    posts_last_week += 1
            if max_per_week is not None and posts_last_week >= max_per_week:
                logger.info(f"[SKIP] Group {group_name}: weekly post limit reached ({max_per_week})")
                continue

            # enforce group delay
            last_group_post = group_state.get('last_group_post', 0)
            logger.debug(f"Checking group {group_name}, last post was {now - last_group_post} sec ago")

            if now - last_group_post < group_delay:
                logger.debug(f"[SKIP] Group {group_name}: delay not reached yet.")
                continue

            # find candidate items
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
                    candidates.append((cooldown, item_name, item_path, item_state.get('post_ids')))
                else:
                    logger.debug(f"[SKIP] Item '{item_name}' not ready (cooldown: {cooldown}s)")

            if not candidates:
                logger.debug(f"[SKIP] No suitable items found for group {group_name}")
                continue

            # find item with the longest cooldown
            candidates.sort(reverse=True)
            _, item_name, item_path, old_post_ids = candidates[0]

            # post new item
            new_post_ids = post_item(client, group_name, item_path)
            if new_post_ids:
                logger.success(f"[OK] Published '{item_name}' to {group_name}, msg_ids={new_post_ids}")

                item_entry = group_state.setdefault('items', {}). \
                    setdefault(item_name, {'last_post_time': now, 'post_ids': []})
                item_entry['last_post_time'] = now
                item_entry.setdefault('post_ids', [])
                item_entry['post_ids'].extend(new_post_ids)

                group_state['last_group_post'] = now
                state[group_name] = group_state

            # cleanup old posts if needed
            deleted_post_ids = cleanup_item(client, group_name, old_post_ids, keep_old)
            if deleted_post_ids:
                logger.info(f"[CLEANUP] Deleted old posts for '{item_name}' in {group_name}")
                item_entry = group_state.setdefault('items', {}). \
                    setdefault(item_name, {'last_post_time': now, 'post_ids': []})
                item_entry['post_ids'] = [pid for pid in item_entry.get('post_ids', []) if pid not in deleted_post_ids]

        # Cleanup: remove state entries for deleted items
        existing_items = set(os.listdir(ITEMS_DIR))

        for group_name, group_state in state.items():
            items_state = group_state.get("items", {})
            to_remove = []

            for item_name, item_data in items_state.items():
                if item_name not in existing_items:
                    logger.info(f"[CLEANUP] '{item_name}' no longer exists in {ITEMS_DIR}, removing from state")
                    old_post_ids = item_data.get("post_ids")
                    if old_post_ids:
                        try:
                            client(ChannelDeleteMessagesRequest(group_name, old_post_ids))
                            logger.success(f"[CLEANUP] Deleted old messages for '{item_name}' in {group_name}")
                        except Exception as e:
                            logger.error(f"[CLEANUP] Failed to delete messages for '{item_name}': {e}")
                    to_remove.append(item_name)

            # Apply deletions
            for item_name in to_remove:
                del group_state["items"][item_name]

    updated_state_json = json.dumps(state, sort_keys=True)
    if updated_state_json != previous_state_json:
        save_state(state)
        logger.debug("State has changed — file updated.")
    else:
        logger.debug("State unchanged — skipping save.")

    logger.debug("Script execution completed.")

if __name__ == '__main__':
    main()
