#!/usr/bin/env python3

# `@ioc` is the generic indicator-of-compromise dispatch — by including it we
# get fanned out alongside virustotal, malwarebazaar, threatfox, urlhaus etc.
# when a user runs `@ioc <hash>`. `@yaraify` and `@yi` are the direct binds.
BINDS = ["@yaraify", "@yi", "@ioc"]
CHANS = ["debug"]

APIURL = {
    "yaraify": {
        "url": "https://yaraify-api.abuse.ch/api/v1/",
        # Auth-Key is OPTIONAL — yaraify gives anonymous callers a working but
        # rate-limited tier. Operators with an abuse.ch auth-key can drop it
        # here (or in settings.py); empty string = anonymous tier.
        "key": "",
    },
}

# Request timeout in seconds. Yaraify's hash-lookup endpoint is fast on hit
# but can be slow when the file is large enough to require a scan. The
# bot's own 30s command timeout caps this further regardless.
TIMEOUT = 30

# Soft cap on the rendered message body. Mattermost rejects very large
# messages; anything above this is truncated with a footer note.
MAX_OUTPUT_CHARS = 6000

# Cap the number of YARA-rule hits we render. A single sample can match
# dozens of rules; channel readers want the triage view, not the full
# rule fan-out.
MAX_RULES = 20

CONTENTTYPE = "application/json"

HELP = {
    "DEFAULT": {
        "args": "<MD5|SHA1|SHA256>",
        "desc": "Query abuse.ch Yaraify (https://yaraify.abuse.ch) for a file "
        "hash and display matched YARA rules, signature/family, tags, and "
        "first-seen timestamp. Anonymous tier works without auth; set "
        "`APIURL['yaraify']['key']` in settings.py for higher rate limits. "
        "Example: `@yaraify 44d88612fea8a8f36de82e1278abb02f`",
    },
}
