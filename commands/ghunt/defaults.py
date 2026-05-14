#!/usr/bin/env python3

BINDS = ["@ghunt"]
CHANS = ["debug"]

# Ghunt is intentionally NOT in the top-level requirements.txt. Reasons:
#   1. It pins `pillow==9.3.0`, which fails to build on Python 3.12+
#      (Pillow 9.x predates the newer setuptools metadata format and
#      raises `KeyError: '__version__'` during get_requires_for_build_wheel).
#      Forcing every operator's `pip install -r` to hit this is hostile.
#   2. Ghunt needs an authenticated Google session to do anything useful —
#      the operator MUST run `ghunt login` (interactive) and persist the
#      resulting `creds.m` cookie file before this command returns
#      anything. There is no "just install and go" path.
#
# This command shells out to the `ghunt` binary via subprocess; it does NOT
# import ghunt as a Python library. The bot can therefore run on any Python
# version — only the environment that *installs* ghunt is constrained by
# Pillow 9.3.0. The cleanest install pattern is pipx, which isolates ghunt
# in its own venv:
#
#     pipx install ghunt --python python3.11   # any Python where Pillow 9 builds
#     ghunt login                               # interactive cookie/OAuth bootstrap
#
# A system package manager install, a separate venv, or anything else that
# puts the `ghunt` binary on the bot's PATH works equally well.
#
# See https://github.com/mxrch/GHunt for the upstream README.
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
