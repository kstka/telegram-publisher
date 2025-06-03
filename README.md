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

---

## 🕒 Cron Job

The script is designed to be run regularly (e.g. every 15 minutes) via `cron`:

```bash
*/15 * * * * /usr/bin/python3 /path/to/main.py
```

* It will publish **one item per group per run**, only if both:

  * the group delay has passed, and
  * the item's cooldown has passed.

Old posts are deleted before new ones are published.

---

## 📦 State Tracking

Publication history is stored in `state.json` (automatically managed). It tracks:

* When each item was last posted to each group
* Message IDs to delete previous albums

---

## 🛠 Logging

Logs are written to `logs/publisher.log`, rotated weekly. You can check the log to see what was posted or skipped.

---

## ☁️ Optional: Sentry Integration

If enabled in `config.py`, errors are reported to your [Sentry](https://sentry.io) project.

```python
USE_SENTRY = True
SENTRY_DNS = 'https://...'
```
