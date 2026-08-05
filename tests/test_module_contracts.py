import ast
import sys
import unittest
from pathlib import Path

# cmdutils lives in commands/, which is not on the path under the test runner.
# It is stdlib-only, so importing it keeps this file dependency-free.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "commands"))

import cmdutils  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS_DIR = REPO_ROOT / "commands"
FEEDS_DIR = REPO_ROOT / "modules"


def _python_dirs(parent):
    return sorted(
        path for path in parent.iterdir()
        if path.is_dir() and not path.name.startswith(".") and not path.name.startswith("__")
    )


def _parse(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _defined_functions(tree):
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def _assigned_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


class CommandModuleContractTests(unittest.TestCase):
    def test_commands_directory_exists(self):
        self.assertTrue(COMMANDS_DIR.is_dir(), "commands directory is missing")

    def test_command_modules_have_required_files(self):
        missing = []
        for module_dir in _python_dirs(COMMANDS_DIR):
            for filename in ("command.py", "defaults.py"):
                if not (module_dir / filename).is_file():
                    missing.append(f"{module_dir.name}/{filename}")
        self.assertEqual([], missing)

    def test_command_modules_define_process(self):
        missing = []
        for module_dir in _python_dirs(COMMANDS_DIR):
            tree = _parse(module_dir / "command.py")
            if "process" not in _defined_functions(tree):
                missing.append(module_dir.name)
        self.assertEqual([], missing)

    def test_command_defaults_define_help_binds_and_channels(self):
        missing = []
        required = {"HELP", "BINDS", "CHANS"}
        for module_dir in _python_dirs(COMMANDS_DIR):
            tree = _parse(module_dir / "defaults.py")
            absent = sorted(required - _assigned_names(tree))
            if absent:
                missing.append(f"{module_dir.name}: {', '.join(absent)}")
        self.assertEqual([], missing)


class FeedModuleContractTests(unittest.TestCase):
    def test_modules_directory_exists(self):
        self.assertTrue(FEEDS_DIR.is_dir(), "modules directory is missing")

    def test_feed_modules_have_required_files(self):
        missing = []
        for module_dir in _python_dirs(FEEDS_DIR):
            for filename in ("feed.py", "defaults.py"):
                if not (module_dir / filename).is_file():
                    missing.append(f"{module_dir.name}/{filename}")
        self.assertEqual([], missing)

    def test_feed_modules_define_query(self):
        missing = []
        for module_dir in _python_dirs(FEEDS_DIR):
            tree = _parse(module_dir / "feed.py")
            if "query" not in _defined_functions(tree):
                missing.append(module_dir.name)
        self.assertEqual([], missing)

    def test_feed_defaults_define_name(self):
        missing = []
        for module_dir in _python_dirs(FEEDS_DIR):
            tree = _parse(module_dir / "defaults.py")
            if "NAME" not in _assigned_names(tree):
                missing.append(module_dir.name)
        self.assertEqual([], missing)


class AIToolContractTests(unittest.TestCase):
    """A module exposed to the AI must declare the indicator types it accepts.

    Both declarations live on process() -- @cmdutils.handles(...) and
    @cmdutils.aitool -- so this reads the decorators straight off the real
    modules via AST. Importing command.py would drag in requests and friends the
    dependency-free runner does not have.
    """

    @staticmethod
    def _process_decorators(path):
        """{decorator name: [arg attribute names]} for the module's process()."""
        out = {}
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not (isinstance(node, ast.FunctionDef) and node.name == "process"):
                continue
            for dec in node.decorator_list:
                func = dec.func if isinstance(dec, ast.Call) else dec
                name = getattr(func, "attr", getattr(func, "id", None))
                if name is None:
                    continue
                args = dec.args if isinstance(dec, ast.Call) else []
                out[name] = [getattr(a, "attr", getattr(a, "id", None)) for a in args]
        return out

    @staticmethod
    def _type_values(const_names):
        # Decorator args are the cmdutils.<NAME> constants; resolve to their
        # canonical string values so a rename in cmdutils cannot pass silently.
        return {getattr(cmdutils, n) for n in const_names if hasattr(cmdutils, n)}

    def _commands(self):
        root = Path(__file__).resolve().parent.parent
        return sorted(root.glob("commands/*/command.py"))

    def test_aitool_modules_declare_accepts(self):
        offenders = []
        for command in self._commands():
            decorators = self._process_decorators(command)
            if "aitool" in decorators and not decorators.get("handles"):
                offenders.append(command.parent.name)
        self.assertEqual(
            offenders, [],
            "these modules opt into the AI toolbox with @cmdutils.aitool but declare no "
            "@cmdutils.handles(...), so the model would be told they take any indicator "
            f"type: {offenders}",
        )

    def test_the_starter_set_is_opted_in_and_covers_every_type(self):
        expected = {"abuseipdb", "circlpdns", "crtsh", "ipinfo",
                    "malwarebazaar", "threatfox", "urlhaus"}
        opted_in, covered = set(), set()
        for command in self._commands():
            decorators = self._process_decorators(command)
            if "aitool" in decorators:
                opted_in.add(command.parent.name)
                covered |= self._type_values(decorators.get("handles") or [])
        self.assertTrue(expected.issubset(opted_in),
                        f"starter AI modules not opted in: {sorted(expected - opted_in)}")
        every_type = {"ip", "ipv6", "cidr", "domain", "url", "md5", "sha1", "sha256"}
        self.assertEqual(every_type - covered, set(),
                         "the AI toolbox cannot look up every indicator type the "
                         "classifier can produce")

    def test_the_ai_optin_is_not_settable_from_config(self):
        # The developer's half of the gate must not be reachable from
        # defaults.py/settings.py: a config file that could set it would be able
        # to widen exposure past what a developer marked safe. Operators narrow
        # via AI.modules / AI.blocked_modules, which can only subtract.
        root = Path(__file__).resolve().parent.parent
        offenders = [p.parent.name for p in sorted(root.glob("commands/*/defaults.py"))
                     if "AITOOL" in p.read_text(encoding="utf-8")]
        self.assertEqual(
            offenders, [],
            f"AITOOL must be declared with @cmdutils.aitool on process(): {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
