"""Guard against command modules leaking secrets through error messages.

Some command modules build their request URL with the API key in the query
string (e.g. `...?key=<APIKEY>`). A `requests` HTTPError stringifies to include
the offending URL, so interpolating `str(e)` of such an error into a channel
message posts the API key into Mattermost -- a credential leak into a widely
readable, long-lived chat log. The single most common trigger is a wrong or
expired key, which returns 401.

These modules put the key in the URL *and* used to post `str(e)`:
botscout, proxycheck, mwdb. This test pins them shut: their exception handler
must not interpolate the caught exception into a `messages.append(...)`.

The check is static (AST only), so it needs none of the modules' third-party
dependencies.
"""

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Modules that place the API key in the request URL: for these, any exception
# string reaching the channel is a credential leak. Regression-locked here.
KEY_IN_URL_MODULES = ("botscout", "proxycheck", "mwdb")


def _names_bound_to_caught_exceptions(tree):
    """Return the set of identifiers bound as `except ... as <name>`."""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
    return names


def _messages_append_calls(tree):
    """Yield ast.Call nodes that look like `<something>.append(...)`."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "append"
        ):
            yield node


def _references_any_name(node, names):
    return any(
        isinstance(child, ast.Name) and child.id in names
        for child in ast.walk(node)
    )


class CommandErrorDisclosureTests(unittest.TestCase):
    def test_key_in_url_modules_do_not_post_exception_text(self):
        offenders = []
        for module in KEY_IN_URL_MODULES:
            path = REPO_ROOT / "commands" / module / "command.py"
            self.assertTrue(path.exists(), f"missing {path}")
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            caught = _names_bound_to_caught_exceptions(tree)
            if not caught:
                continue
            for call in _messages_append_calls(tree):
                if _references_any_name(call, caught):
                    offenders.append(f"{module}/command.py:{call.lineno}")
        self.assertEqual(
            [],
            offenders,
            "A caught exception is interpolated into a channel message. For these "
            "modules the API key is in the request URL, so the exception string "
            "leaks it into the channel. Log it instead and post a flat, "
            "credential-free line. Offenders: " + ", ".join(offenders),
        )


class DetectorTests(unittest.TestCase):
    """The guard is only worth having if it detects the pattern it targets."""

    def test_detects_exception_in_append(self):
        src = (
            "msgs = []\n"
            "try:\n"
            "    pass\n"
            "except Exception as e:\n"
            "    msgs.append({'text': 'boom %s' % str(e)})\n"
        )
        tree = ast.parse(src)
        caught = _names_bound_to_caught_exceptions(tree)
        hits = [c for c in _messages_append_calls(tree) if _references_any_name(c, caught)]
        self.assertEqual(1, len(hits))

    def test_ignores_flat_message(self):
        src = (
            "msgs = []\n"
            "try:\n"
            "    pass\n"
            "except Exception:\n"
            "    msgs.append({'text': 'the lookup failed'})\n"
        )
        tree = ast.parse(src)
        caught = _names_bound_to_caught_exceptions(tree)
        hits = [c for c in _messages_append_calls(tree) if _references_any_name(c, caught)]
        self.assertEqual([], hits)


if __name__ == "__main__":
    unittest.main()
