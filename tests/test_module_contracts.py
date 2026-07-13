import ast
import unittest
from pathlib import Path


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
    """A module exposed to the AI must declare the indicator types it accepts."""

    @staticmethod
    def _module_assignments(path):
        tree = ast.parse(path.read_text())
        out = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        try:
                            out[target.id] = ast.literal_eval(node.value)
                        except ValueError:
                            out[target.id] = None
        return out

    def test_aitool_modules_declare_accepts(self):
        offenders = []
        root = Path(__file__).resolve().parent.parent
        for defaults in sorted(root.glob("commands/*/defaults.py")):
            values = self._module_assignments(defaults)
            if values.get("AITOOL") and not values.get("ACCEPTS"):
                offenders.append(defaults.parent.name)
        self.assertEqual(
            offenders, [],
            "these modules opt into the AI toolbox but declare no ACCEPTS, so the model "
            f"would be told they take any indicator type: {offenders}",
        )

    def test_the_starter_set_is_opted_in_and_covers_every_type(self):
        expected = {"abuseipdb", "circlpdns", "crtsh", "ipinfo",
                    "malwarebazaar", "threatfox", "urlhaus"}
        root = Path(__file__).resolve().parent.parent
        opted_in, covered = set(), set()
        for defaults in sorted(root.glob("commands/*/defaults.py")):
            values = self._module_assignments(defaults)
            if values.get("AITOOL") is True:
                opted_in.add(defaults.parent.name)
                covered |= set(values.get("ACCEPTS") or [])
        self.assertTrue(expected.issubset(opted_in),
                        f"starter AI modules not opted in: {sorted(expected - opted_in)}")
        every_type = {"ip", "ipv6", "cidr", "domain", "url", "md5", "sha1", "sha256"}
        self.assertEqual(every_type - covered, set(),
                         "the AI toolbox cannot look up every indicator type the "
                         "classifier can produce")


if __name__ == "__main__":
    unittest.main()
