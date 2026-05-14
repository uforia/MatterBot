#!/usr/bin/env python3

BINDS = ["@unfurl"]
CHANS = ["debug"]

# Whether unfurl should reach out to remote services for enrichment
# (e.g. shortener expansion, threat-intel lookups). Defaults to False
# so the bot stays self-contained and doesn't leak the queried URL
# to third parties without explicit opt-in.
REMOTE_LOOKUPS = False

# Soft cap on the text tree returned to the channel. Mattermost will
# reject very large messages; anything above this is truncated with
# a footer note instead of being silently dropped.
MAX_OUTPUT_CHARS = 8000

HELP = {
    "DEFAULT": {
        "args": "<URL>",
        "desc": "Parses a URL with Unfurl (https://github.com/obsidianforensics/unfurl) "
        "and returns its components as a tree: decoded tracking params, "
        "embedded base64, JWT contents, timestamps, UUIDs, and more. "
        "Useful for triaging suspicious URLs without visiting them. "
        "Example: `@unfurl https://example.com/path?utm_source=foo&id=eyJhbGciOi...`",
    },
}
