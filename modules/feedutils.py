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


def result(items=None, errors=None):
    """Build a FeedResult from collected posts and (source, message) errors."""
    return FeedResult(list(items) if items else [], list(errors) if errors else [])


def split_result(value):
    """Normalise a query() return value into a (items, errors) pair.

    Accepts the legacy contract (a plain list, or None) -- for which errors is
    always empty -- as well as a FeedResult. This is what the main loop calls
    so that both old and migrated modules go through one code path.
    """
    if isinstance(value, FeedResult):
        return list(value.items) if value.items else [], list(value.errors) if value.errors else []
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
