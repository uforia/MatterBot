#!/usr/bin/env python3

BINDS = ["@ghunt"]
CHANS = ["debug"]

# Ghunt requires an authenticated Google session to call the internal
# endpoints it scrapes. The bot host operator must run `ghunt login` once
# (interactive) and have the resulting `creds.m` cookie file persisted on
# disk before this command will return anything useful. See
# https://github.com/mxrch/GHunt for the auth bootstrap flow.
#
# Ghunt subcommand to invoke. Currently only `email` is wired; switching this
# to `gaia` or another subcommand would also need a different positional-arg
# validator below.
SUBCOMMAND = "email"

# Subprocess timeout in seconds. Ghunt makes a fan-out of Google API calls;
# 90s is generous for a cold path while still bounding worst-case latency.
TIMEOUT = 90

# Soft cap on the rendered message body. Mattermost rejects very large
# messages; anything above this is truncated with a footer note instead of
# being silently dropped.
MAX_OUTPUT_CHARS = 6000

HELP = {
    "DEFAULT": {
        "args": "<email>",
        "desc": "Looks up a Google account using Ghunt "
        "(https://github.com/mxrch/GHunt) — surfaces the Gaia ID, profile "
        "picture, public reviews/maps activity, and linked services. "
        "Requires the bot host operator to have run `ghunt login` first; "
        "without persistent Google credentials this command will return "
        "an authentication error. "
        "Example: `@ghunt target@gmail.com`",
    },
}
