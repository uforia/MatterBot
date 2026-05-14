#!/usr/bin/env python3

BINDS = ["@waybacklister", "@wbl"]
CHANS = ["debug"]

# Wayback CDX endpoint. The bot only ever talks to web.archive.org with a
# domain it has already validated against a strict RFC-1123 regex, so the
# outbound surface here is just "a query string built from a known hostname".
CDX_URL = "https://web.archive.org/cdx/search/cdx"

# CDX request timeout in seconds. The Internet Archive is occasionally slow;
# this gives it ~30s before we return a clean timeout message instead of
# blocking the user's command worker.
TIMEOUT = 30

# Per-query CDX row cap. The collapse=urlkey filter already deduplicates by
# canonical URL, so 1000 is enough to cover most domains worth listing
# without producing a multi-megabyte response.
CDX_LIMIT = 1000

# Soft cap on the rendered directory list. Mattermost rejects very large
# messages; anything above this is truncated with a footer note.
MAX_OUTPUT_CHARS = 6000

# Cap the number of URLs we render to the channel after filtering. The CDX
# limit above bounds the upstream payload; this bounds the user-facing list.
MAX_RESULTS = 200

# User-Agent for the CDX call. Some Wayback edges return 403 for the default
# python-requests UA; pinning an identifying string keeps the query routable
# and makes Internet Archive abuse-handlers able to reach the operator.
USER_AGENT = "MatterBot-waybacklister/1.0 (+https://github.com/uforia/MatterBot)"

HELP = {
    "DEFAULT": {
        "args": "<domain>",
        "desc": "Enumerates paths the Wayback Machine has archived for a "
        "domain and filters for directory-shaped URLs (paths ending in `/`). "
        "Inspired by wayBackLister (https://github.com/anmolksachan/wayBackLister) "
        "— useful as a first-pass open-directory hunt without sending traffic "
        "to the live domain. "
        "Example: `@waybacklister example.com`",
    },
}
