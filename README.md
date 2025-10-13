# Telegram Publisher Bot

A simple script for periodically publishing photo albums with descriptions to Telegram groups (e.g. for classified ads, marketplaces, etc.).

## 🚀 Quick Start

### 1. Clone the repo and install dependencies

```bash
pip install -r requirements.txt
````

### 2. Configure the bot

Copy the config template and fill in your credentials:

```
cp config.sample.py config.py
```

Edit `config.py`:

* Set your Telegram API ID and hash from [my.telegram.org](https://my.telegram.org)
* Add your target group usernames and posting delays (in days)

---

## 📁 Item Folder Structure

Each item you want to publish should be placed in the `items/` directory in its own subfolder:

```
items/
└── item1/
    ├── 1.jpg
    ├── 2.jpg
    ├── description.txt      # Text caption (optional)
    └── delay.txt            # Optional: delay in days before reposting (default: 7)
```

* You can include multiple `.jpg`, `.jpeg`, or `.png` images — they will be sent as an album.
* `delay.txt` should contain a number like `1`, `0.5`, or `7`. If missing, defaults to 7 days.

When the folder is deleted, the bot will automatically clean up its last posted message(s) in all groups.

---

## ⚡ Priority Function

A priority mechanism controls which items are preferred for publishing when multiple candidates are available for a group.

- Per-item priority:
  - Each item folder may contain a `priority.txt` file with a numeric value (integer or float).
  - Higher numbers mean higher priority. Default priority is `1` when the file is missing or invalid.
  - Example: `priority.txt` containing `2` makes this item more likely to be chosen before items with lower priorities.

---

## 🕒 Cron Job

The script is designed to be run every hour via `cron`:

```bash
0 * * * * sleep $((RANDOM % 300)); cd /home/user/telegram-publisher; python main.py
```

* It will publish **one item per group per run**, only if both:

  * the group delay has passed, and
  * the item's cooldown has passed.

Old posts are deleted before new ones are published if needed.

---

## 📦 State Tracking

Publication history is stored in `state.json` (automatically managed). It tracks:

* When each item was last posted to each group
* Message IDs to delete previous albums

---

## 🗂 state.json Structure

The `state.json` file tracks what was posted, when, and to which groups. It's automatically managed by the script.

```json
{
  "yourgroup": {
    "last_group_post": 1717000000,
    "items": {
      "item1": {
        "last_post_time": 1716900000,
        "post_ids": [12345, 12346, 12347]
      },
      "item2": {
        "last_post_time": 1716800000,
        "post_ids": [12300]
      }
    }
  }
```

* `last_group_post`: Unix timestamp of the last post in this group.
* `items`: Maps item folders to their last posting time and the Telegram message_ids sent as an album (used for cleanup before reposting).

---

## 🛠 Logging

Logs are written to `logs/main.log` and `logs/debug.log`, rotated weekly. You can check the log to see what was posted.

---

## ⚠️ Group Posting Restrictions

Sometimes a group may block the ability to post (for example, due to group rules violations or admin restrictions).  
If this happens, you will see errors like:

```
You can't write in this chat (caused by UploadMediaRequest)
```

When such an error occurs, the group name is automatically added to the `blocked_groups` variable (see `config.py`).  
No further attempts to post will be made to this group until the script is restarted or the group is unblocked.

You can also manually add group names to `blocked_groups` in `config.py` to temporarily disable posting to them and wait for the restriction to be lifted.

---

## ❌ Exclusions (EXCLUDES)

- `EXCLUDES` is expected to be a dictionary mapping group name -> list/tuple/set of item folder names to skip.
- `get_excludes()` reads `config.EXCLUDES` and returns a `dict` where each key is a group name and the value is a `set` of item names.
- When selecting candidates for posting, items listed in `EXCLUDES` for the given group are skipped and a `[SKIP] Item '...' excluded for group ...` log entry is written.

Example `config.py`:

```python
EXCLUDES = {
    "group_username_1": ["item1", "item2"],
    "group_username_2": ("old_item",),
    "group_username_3": None,  # empty exclusions
}

---

## ☁️ Optional: Sentry Integration

If enabled in `config.py`, errors are reported to your [Sentry](https://sentry.io) project.

```python
USE_SENTRY = True
SENTRY_DNS = 'https://...'
```
