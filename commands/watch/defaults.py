#!/usr/bin/env python3

BINDS = ["@watch"]
# Watch is intentionally lenient on CHANS — the actual privacy boundary is
# the DM that matterbot sends when a keyword fires, not where the user
# configures their list. Most installs will want to add @watch to the
# debug channel and to whatever general channel users hang out in.
CHANS = ["debug"]

# Minimum keyword length. Sub-3-character substrings produce too much noise
# (every "is", "to", "a") to be useful as alerts.
MIN_KEYWORD_LEN = 3

# Maximum keyword length. Anything longer is almost certainly a paste of a
# whole sentence and not a useful watch.
MAX_KEYWORD_LEN = 64

# Maximum watches per user. Caps the per-message scan cost (we walk every
# active watch on every message) and bounds the JSON file size.
MAX_WATCHES_PER_USER = 50

# Default expiry when the user does not pass a duration. `None` = never
# expires. Set to a duration string like "30d" in settings.py if you want
# the bot to auto-prune stale watches.
DEFAULT_DURATION = None

# Maximum allowed expiry duration in seconds (default: 365 days). Prevents
# accidental year-long watches set with typos like "10000d".
MAX_DURATION_SECONDS = 365 * 24 * 60 * 60

# Length of the message snippet included in the alert DM. Long enough to
# give context, short enough that the alert stays scannable.
SNIPPET_CHARS = 240

HELP = {
    "DEFAULT": {
        "args": "[list|add|del|clear] ...",
        "desc": "Watch channel messages for keywords and get DM'd when they "
        "match. Like Mattermost's built-in keyword notifications, but "
        "with per-keyword expiry. Without args, lists your active watches.",
    },
    "add": {
        "args": "<keyword> [duration]",
        "desc": "Add a keyword to watch. Optional duration like `7d`, `24h`, "
        "`30m`. No duration = never expires. "
        "Example: `@watch add ransomware 7d`",
    },
    "del": {
        "args": "<keyword>",
        "desc": "Stop watching a keyword. "
        "Example: `@watch del ransomware`",
    },
    "list": {
        "args": None,
        "desc": "List your active watches and their expiry times.",
    },
    "clear": {
        "args": None,
        "desc": "Remove all of your active watches.",
    },
}
