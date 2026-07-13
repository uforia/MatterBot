"""Wiring tests for the AI analyst's integration with matterbot.py.

matterbot.py imports mattermostdriver and relies on a module-level `options`
global that only exists under __main__, so it cannot be imported under the
dependency-free CI runner. Structural claims are therefore asserted against its
AST (as tests/test_module_contracts.py does for the command modules).

AST tests alone are too weak for this feature -- they can pass while the real bot
breaks -- so the callback CONTRACTS (thread shape, post shape) are additionally
tested for real in tests/test_ai_analyst.py against pure functions that
ai_analyst.py owns. Keep it that way: any logic worth testing belongs in
ai_analyst.py, not in matterbot.py.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATTERBOT = ROOT / "matterbot.py"


def _tree():
    return ast.parse(MATTERBOT.read_text())


def _method(name):
    for node in ast.walk(_tree()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _argnames(node):
    args = node.args
    return [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]


class SendMessageTests(unittest.TestCase):
    def test_send_message_accepts_props(self):
        node = _method("send_message")
        self.assertIsNotNone(node, "send_message not found in matterbot.py")
        self.assertIn(
            "props", _argnames(node),
            "send_message must accept props so AI posts can be tagged as narrative "
            "or evidence and reconstructed correctly",
        )

    def test_send_message_stamps_a_part_index_on_split_posts(self):
        # send_message splits long text across several posts. Without a part index,
        # a long AI narrative is replayed to the model as N separate assistant
        # turns AND its tool budget is counted N times.
        source = MATTERBOT.read_text()
        self.assertIn(
            "ai_part", source,
            "send_message must stamp a part index onto the props of each block of "
            "a split message",
        )


class RunModuleTests(unittest.TestCase):
    def test_run_module_exists_and_is_async(self):
        node = _method("run_module")
        self.assertIsNotNone(node, "run_module not found in matterbot.py")
        self.assertIsInstance(node, ast.AsyncFunctionDef, "run_module must be a coroutine")

    def test_run_module_returns_the_module_result(self):
        node = _method("run_module")
        returns = [n for n in ast.walk(node) if isinstance(n, ast.Return) and n.value is not None]
        self.assertTrue(
            returns,
            "run_module must RETURN the module result dict -- the AI executor feeds "
            "it back to the model rather than posting it",
        )

    def test_call_module_delegates_to_run_module(self):
        node = _method("call_module")
        self.assertIsNotNone(node)
        called = {
            n.func.attr for n in ast.walk(node)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        self.assertIn(
            "run_module", called,
            "call_module must delegate execution to run_module so the posting path "
            "and the AI path share one executor",
        )


class PackagingTests(unittest.TestCase):
    def test_ai_analyst_is_shipped_as_a_py_module(self):
        pyproject = (ROOT / "pyproject.toml").read_text()
        self.assertIn(
            '"ai_analyst"', pyproject,
            "py-modules lists only matterbot and matterfeed, so a top-level "
            "ai_analyst.py would be silently dropped on install",
        )

    def test_python_floor_matches_reality(self):
        # main already calls asyncio.timeout (3.11+), so >=3.9 is a lie today.
        pyproject = (ROOT / "pyproject.toml").read_text()
        self.assertIn("requires-python = \">=3.11\"", pyproject)


if __name__ == "__main__":
    unittest.main()
