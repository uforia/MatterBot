"""Guard tests for how modules put their own directory on sys.path (issue #282).

`modules/socket/` has an `__init__.py`, which makes it a *regular package* --
not a namespace portion. A regular package wins the import scan outright, so it
shadows the stdlib `socket` for any `sys.path` entry that precedes the stdlib:

    >>> sys.path.insert(0, 'modules'); import socket
    >>> socket.__file__
    '.../modules/socket/__init__.py'
    >>> hasattr(socket, 'socket')
    False

Anything importing `socket` fresh after that dies -- `multiprocessing.reduction`
does exactly that, on `socket.socket`.

Feed modules legitimately need `modules/` on the path (for `feedutils`, and for
`from opencve.defaults import ...`). Appending finds those just as well while
leaving the stdlib ahead of `modules/`, so the collision cannot happen. Placing
it at position 0 is what arms the bug.

These checks are static (AST only), so they need none of the feeds' third-party
dependencies.
"""

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = REPO_ROOT / "modules"


def _sys_path_inserts_at_front(source, filename="<unknown>"):
    """Yield lineno for every `sys.path.insert(0, ...)` call in `source`."""
    tree = ast.parse(source, filename=filename)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # match sys.path.insert(...)
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "insert"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "path"
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == "sys"
        ):
            continue
        if not node.args:
            continue
        index = node.args[0]
        if isinstance(index, ast.Constant) and index.value == 0:
            yield node.lineno


class ImportPathSafetyTests(unittest.TestCase):
    def test_the_shadowing_hazard_is_real(self):
        # If this ever fails, modules/socket stopped being a regular package and
        # the guard below is no longer load-bearing -- worth knowing either way.
        self.assertTrue(
            (MODULES_DIR / "socket" / "__init__.py").exists(),
            "modules/socket/__init__.py is gone; re-evaluate test_no_module_puts_itself_ahead_of_the_stdlib",
        )

    def test_no_module_puts_itself_ahead_of_the_stdlib(self):
        offenders = []
        for path in sorted(MODULES_DIR.rglob("*.py")):
            source = path.read_text(encoding="utf-8", errors="replace")
            for lineno in _sys_path_inserts_at_front(source):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}")
        self.assertEqual(
            [],
            offenders,
            "sys.path.insert(0, ...) puts modules/ ahead of the stdlib, where "
            "modules/socket shadows the stdlib socket. Use sys.path.append(...) "
            "instead -- it finds feedutils/opencve just as well. Offenders: "
            + ", ".join(offenders),
        )


class DetectorTests(unittest.TestCase):
    """The guard is only worth having if it actually detects the pattern."""

    def test_detects_insert_at_zero(self):
        src = "import sys\nsys.path.insert(0, 'modules')\n"
        self.assertEqual([2], list(_sys_path_inserts_at_front(src, "<test>")))

    def test_ignores_append(self):
        src = "import sys\nsys.path.append('modules')\n"
        self.assertEqual([], list(_sys_path_inserts_at_front(src, "<test>")))

    def test_ignores_insert_at_a_later_index(self):
        # Only position 0 puts the dir ahead of the stdlib entries.
        src = "import sys\nsys.path.insert(1, 'modules')\n"
        self.assertEqual([], list(_sys_path_inserts_at_front(src, "<test>")))


if __name__ == "__main__":
    unittest.main()
