#!/usr/bin/env python3

import importlib
import re
from types import SimpleNamespace

import bs4

_STRIPCHARS = '`\\[\\]\'\"'
_DESCRIPTION_RX = re.compile('[%s]' % _STRIPCHARS)


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
    text = _DESCRIPTION_RX.sub('', bs4.BeautifulSoup(description, 'lxml').get_text("\n"))
    text = text.strip().replace('\n', '. ')
    if len(text) > max_length:
        return text[:max_length - 4] + ' ...'
    return text
