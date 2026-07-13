#!/usr/bin/env python3

import importlib
import re
from collections import namedtuple
from types import SimpleNamespace

_STRIPCHARS = '`\\[\\]\'\"'
_DESCRIPTION_RX = re.compile('[%s]' % _STRIPCHARS)


# A feed module's query() may return either the original plain list of posts,
# or a FeedResult carrying BOTH the posts it collected AND the per-source
# errors it hit. The second form lets a module report partial failures (e.g.
# "one of my five feeds returned a 403") to the main loop, which logs them
# centrally, instead of the module having to choose between swallowing the
# error silently or raising and discarding every post it already collected.
#
# `errors` is a list of (source, message) pairs -- source is whatever
# identifies the failing input (a feed URL, a section name), message a short
# human-readable string.
FeedResult = namedtuple('FeedResult', ['items', 'errors'])


UNKNOWN_SOURCE = '<unknown source>'

# How a module's run turned out, given what it returned.
OK = 'ok'            # nothing went wrong
PARTIAL = 'partial'  # some sources failed, but posts were still collected
FAILED = 'failed'    # every source failed and nothing was collected


class AllSourcesFailed(Exception):
    """Raised when a module reported errors and collected nothing at all.

    A module that returns FeedResult([], errors) has not "run successfully with
    no news" -- it is dark. Without this, the empty list is indistinguishable
    from a quiet feed, the run is counted as a success, and a module whose every
    source is 403ing reports "16/16 modules ran successfully" indefinitely.
    """


def classify(items, errors):
    """Decide whether a module's run was OK, PARTIAL, or FAILED.

    The distinction that matters: errors *with* posts is a partial failure worth
    a warning, errors *without* any posts is a dead module worth an error and a
    failed count. No errors at all is fine, however few posts came back -- a
    quiet feed is not a broken one.
    """
    if not errors:
        return OK
    return PARTIAL if items else FAILED


def normalise_errors(errors):
    """Coerce a module's `errors` into a list of (source, message) string pairs.

    Every module hand-builds its own error list, so one of them will eventually
    append a bare string, or a 3-tuple, or None. The main loop unpacks these
    entries -- and it does so *after* the module's posts have already been
    collected, so an unpackable entry used to take the whole run down with it
    and discard every post the module had gathered.

    Reporting an error must never be able to destroy the posts that the same
    run succeeded in fetching. So a malformed entry is repaired here rather than
    raised on: whatever it holds is kept as the message, under an unknown source,
    where an operator will still see it.
    """
    if not errors:
        return []
    normalised = []
    for entry in errors:
        if isinstance(entry, (tuple, list)) and len(entry) == 2:
            source, message = entry
        elif isinstance(entry, (tuple, list)):
            # Wrong arity: keep everything, rather than silently dropping a field.
            source, message = UNKNOWN_SOURCE, ', '.join(str(part) for part in entry)
        else:
            source, message = UNKNOWN_SOURCE, entry
        normalised.append((str(source), str(message)))
    return normalised


def result(items=None, errors=None):
    """Build a FeedResult from collected posts and (source, message) errors."""
    return FeedResult(list(items) if items else [], normalise_errors(errors))


def split_result(value):
    """Normalise a query() return value into a (items, errors) pair.

    Accepts the legacy contract (a plain list, or None) -- for which errors is
    always empty -- as well as a FeedResult. This is what the main loop calls
    so that both old and migrated modules go through one code path.

    Errors are normalised here too, not only in result(): a module can build a
    FeedResult directly, and the caller unpacks these pairs, so the guarantee
    has to hold at the boundary the caller actually reads from.
    """
    if isinstance(value, FeedResult):
        items = list(value.items) if value.items else []
        return items, normalise_errors(value.errors)
    if value is None:
        return [], []
    return list(value), []


def load_settings(settings=None, defaults_module='defaults', overrides_module='settings'):
    if settings:
        return SimpleNamespace(**settings)

    defaults = importlib.import_module(defaults_module)
    try:
        overrides = importlib.import_module(overrides_module)
    except ImportError:
        return defaults

    defaults.__dict__.update({k: v for k, v in vars(overrides).items() if not k.startswith('__')})
    return defaults


def clean_description(description, max_length=400):
    import bs4  # imported lazily so feedutils stays importable without bs4 (e.g. under the stdlib-only test runner)
    text = _DESCRIPTION_RX.sub('', bs4.BeautifulSoup(description, 'lxml').get_text("\n"))
    text = text.strip().replace('\n', '. ')
    if len(text) > max_length:
        return text[:max_length - 4] + ' ...'
    return text
