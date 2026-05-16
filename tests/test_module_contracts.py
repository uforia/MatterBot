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


if __name__ == "__main__":
    unittest.main()
