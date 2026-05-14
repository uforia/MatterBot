#!/usr/bin/env python3

BINDS = ["@phishstats", "@ps"]
CHANS = ["debug"]

# PhishStats public API. No authentication required.
# Reference: https://phishstats.info/#apidoc
APIURL = "https://phishstats.info:2096/api/phishing"

# Soft cap on results returned by the API (PhishStats default is 200; cap
# to the most recent N so we don't render a 10-page wall of URLs).
MAX_RESULTS = 20

# Request timeout in seconds.
TIMEOUT = 30

# Soft cap on the rendered message body. Mattermost rejects very large
# messages; anything above this is truncated with a footer note.
MAX_OUTPUT_CHARS = 6000

# User-Agent — PhishStats does not require one but identifying ourselves
# makes the operator reachable to PhishStats abuse handlers if a deploy
# generates anomalous query volume.
USER_AGENT = "MatterBot-phishstats/1.0 (+https://github.com/uforia/MatterBot)"

HELP = {
    "DEFAULT": {
        "args": "<domain|host>",
        "desc": "Query PhishStats (https://phishstats.info) for recent phishing "
        "reports matching a domain or hostname substring. Returns date, URL, "
        "score, and page title for each hit. No API key required. "
        "Example: `@phishstats example.com`",
    },
}
