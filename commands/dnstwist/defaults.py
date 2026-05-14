#!/usr/bin/env python3

BINDS = ["@dnstwist"]
CHANS = ["debug"]

# Whether DNSTwist should perform DNS lookups against the generated permutations
# and return only registered ones. This is the killer feature of the tool —
# without DNS resolution you only get a permutation list with no signal about
# which ones are actually live. Unlike `unfurl` (which leaks the queried URL to
# shorteners and threat-intel services on remote_lookups=True), the privacy
# cost here is just public DNS queries for typosquat candidates of the
# user-supplied domain, so this defaults to True.
# Set to False if you want a pure offline permutation enumeration.
REMOTE_LOOKUPS = True

# Per-run DNS resolution thread count. dnstwist's own default is 10.
THREADS = 10

# Soft cap on the number of result rows kept after fuzzing. dnstwist can
# produce thousands of permutations; truncating here keeps the channel
# message tractable and well under Mattermost's message ceiling.
MAX_RESULTS = 200

# Soft cap on the rendered message body. Mattermost rejects very large
# messages; anything above this is truncated with a footer note.
MAX_OUTPUT_CHARS = 8000

HELP = {
    "DEFAULT": {
        "args": "<domain>",
        "desc": "Generates typosquatting and lookalike permutations of a domain "
        "using DNSTwist (https://github.com/elceef/dnstwist) and resolves them "
        "against public DNS to find registered ones. Useful for brand-protection "
        "monitoring and phishing triage. "
        "Example: `@dnstwist paypal.com`",
    },
}
