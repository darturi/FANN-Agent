"""Differential filesystem and scoped-binding proofs against the pinned original."""

import ast
import hashlib
import random
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import fast_paths as F

ROOT = Path("/Users/danielarturi/Developer/JinyangLiWork")
SOURCE = ROOT / "agent/experiments/startup-exact-vector-startup-integration-v1"


def original():
    path = SOURCE / "legacy_common.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == F.PIN
    function = next(
        n
        for n in ast.parse(path.read_text()).body
        if isinstance(n, ast.FunctionDef) and n.name == "safe_file"
    )
    scope = {"Path": Path}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), scope)
    return scope["safe_file"]


class DifferentialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / "nested").mkdir()
        (self.root / "nested/file").write_bytes(b"exact bytes")
        self.old = original()
        self.stats = F.stats()
        self.new = F.make_checker(self.old, self.stats)

    def compare(self, name, root=None):
        values = []
        for fn in (self.old, self.new):
            try:
                values.append(("return", fn(root or self.root, name)))
            except Exception as exc:
                values.append((type(exc).__name__, str(exc)))
        self.assertEqual(*values)
        return values[0]

    def test_valid_nested_bytes_and_absolute_result(self):
        self.assertEqual(self.compare("nested/file"), ("return", self.root / "nested/file"))

    def test_missing_leaf_remains_a_path_not_a_cached_success(self):
        self.assertEqual(self.compare("nested/missing")[0], "return")

    def test_missing_parent_same_semantics(self):
        self.assertEqual(self.compare("missing/file")[0], "return")

    def test_absolute_rejected(self):
        self.assertEqual(self.compare(str(self.root / "nested/file"))[0], "ValueError")

    def test_empty_and_dot_rejected(self):
        for name in ("", ".", Path(".")):
            with self.subTest(name=name):
                self.assertEqual(self.compare(name)[0], "ValueError")

    def test_parent_traversal_rejected(self):
        for name in ("..", "../file", "nested/../file", "nested/../../file"):
            with self.subTest(name=name):
                self.assertEqual(self.compare(name)[0], "ValueError")

    def test_path_normalization_matches_original(self):
        for name in ("nested/./file", "nested//file", "nested/file/", Path("nested/file")):
            self.compare(name)

    def test_leaf_symlink_rejected(self):
        (self.root / "link").symlink_to(self.root / "nested/file")
        self.assertEqual(self.compare("link")[0], "ValueError")

    def test_parent_symlink_rejected(self):
        (self.root / "link").symlink_to(self.root / "nested", target_is_directory=True)
        self.assertEqual(self.compare("link/file")[0], "ValueError")

    def test_broken_symlink_rejected(self):
        (self.root / "broken").symlink_to(self.root / "no-file")
        self.assertEqual(self.compare("broken")[0], "ValueError")

    def test_symlink_root_resolves_exactly_as_original(self):
        (self.root / "alias").symlink_to(self.root / "nested", target_is_directory=True)
        self.compare("file", self.root / "alias")

    def test_filesystem_root_uses_single_separator(self):
        self.compare(str(self.root / "nested/file").lstrip("/"), Path("/"))

    def test_sibling_prefix_and_root_itself_rejected(self):
        resolve = Path.resolve
        for target in (self.root, Path(str(self.root) + "-sibling/file")):

            def changed(path, *a, **kw):
                return target if path == self.root / "nested/file" else resolve(path, *a, **kw)

            with patch.object(Path, "resolve", changed):
                self.assertEqual(self.compare("nested/file")[0], "ValueError")

    def test_fresh_symlink_tamper_visible_on_next_call(self):
        self.compare("nested/file")
        (self.root / "nested/file").unlink()
        (self.root / "nested/file").symlink_to(self.root / "outside")
        self.assertEqual(self.compare("nested/file")[0], "ValueError")

    def test_same_ordered_resolve_and_symlink_observations(self):
        traces = []
        resolve, is_symlink = Path.resolve, Path.is_symlink
        for fn in (self.old, self.new):
            trace = []

            def resolved(path, *a, **kw):
                trace.append(("resolve", str(path)))
                return resolve(path, *a, **kw)

            def linked(path):
                trace.append(("is_symlink", str(path)))
                return is_symlink(path)

            with patch.object(Path, "resolve", resolved), patch.object(Path, "is_symlink", linked):
                fn(self.root, "nested/file")
            traces.append(trace)
        self.assertEqual(*traces)
        self.assertEqual(len(traces[0]), 4)

    def test_rejected_symlink_has_same_observations(self):
        (self.root / "link").symlink_to(self.root / "nested")
        observed = []
        old = Path.is_symlink
        for fn in (self.old, self.new):
            checks = []

            def linked(path):
                checks.append(str(path))
                return old(path)

            with patch.object(Path, "is_symlink", linked), self.assertRaises(ValueError):
                fn(self.root, "link/file")
            observed.append(checks)
        self.assertEqual(*observed)

    def test_seeded_valid_and_unsafe_paths(self):
        rng = random.Random(20261101)
        for _ in range(128):
            parts = [
                rng.choice(("nested", "missing", "file", "..", ".", "λ"))
                for _ in range(rng.randrange(1, 7))
            ]
            self.compare("/".join(parts))

    def test_filesystem_error_propagates_same_type_and_message(self):
        with patch.object(Path, "is_symlink", side_effect=PermissionError("denied")):
            self.assertEqual(self.compare("nested/file"), ("PermissionError", "denied"))

    def test_file_hashes_are_fresh_and_not_patched(self):
        path = self.new(self.root, "nested/file")
        first = hashlib.sha256(path.read_bytes()).hexdigest()
        path.write_bytes(b"changed")
        self.assertNotEqual(
            first, hashlib.sha256(self.new(self.root, "nested/file").read_bytes()).hexdigest()
        )

    def test_non_posix_delegates_original(self):
        with patch.object(F.os, "name", "nt"):
            marker = object()
            checker = F.make_checker(lambda *a: marker, F.stats())
            self.assertIs(checker("root", "name"), marker)


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.old = original()
        self.module = types.ModuleType("offline_path_test_common")
        self.module.__file__ = str(SOURCE / "pc_common.py")
        self.module.safe_file = self.old
        self.key = "offline_path_test_common"
        self.assertNotIn(self.key, sys.modules)
        sys.modules[self.key] = self.module
        self.addCleanup(sys.modules.pop, self.key, None)

    def scope(self, counters):
        return F.scoped(self.module, ROOT, SOURCE, counters)

    def test_normal_scope_restores_exact_original(self):
        s = F.stats()
        with self.scope(s):
            self.assertIsNot(self.module.safe_file, self.old)
        self.assertIs(self.module.safe_file, self.old)
        self.assertTrue(s["restored"])

    def test_exception_restores_exact_original(self):
        with self.assertRaisesRegex(ValueError, "fixture"), self.scope(F.stats()):
            raise ValueError("fixture")
        self.assertIs(self.module.safe_file, self.old)

    def test_nested_scope_rejected_without_losing_outer(self):
        with self.scope(F.stats()):
            checker = self.module.safe_file
            with self.assertRaisesRegex(RuntimeError, "Nested"), self.scope(F.stats()):
                pass
            self.assertIs(self.module.safe_file, checker)
        self.assertFalse(F.ACTIVE)

    def test_binding_loss_rejected_and_restored(self):
        with self.assertRaisesRegex(RuntimeError, "binding lost"), self.scope(F.stats()):
            self.module.safe_file = lambda *a: None
        self.assertIs(self.module.safe_file, self.old)

    def test_new_alias_restored(self):
        alias = types.ModuleType("offline_path_new_alias")
        alias.__file__ = str(SOURCE / "example.py")
        s = F.stats()
        with self.scope(s):
            alias.safe_file = self.module.safe_file
            sys.modules[alias.__name__] = alias
            self.addCleanup(sys.modules.pop, alias.__name__, None)
        self.assertIs(alias.safe_file, self.old)
        self.assertEqual(s["new_aliases_restored"], 1)

    def test_wrong_original_rejected(self):
        self.module.safe_file = lambda *a: None
        with self.assertRaisesRegex(RuntimeError, "Pinned original"), self.scope(F.stats()):
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
