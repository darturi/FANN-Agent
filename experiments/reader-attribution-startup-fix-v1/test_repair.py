"""The repair changes namespacing only, including every host analysis consumer."""

import ast
import hashlib
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[2] / "trials/fannagent-benchmark-evaluation-v1/reviews-small"
OLD = STUDY / "kits/reader-attribution-v1"
NEW = STUDY / "kits/reader-attribution-v1-startup-fix"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Repair(unittest.TestCase):
    def test_only_import_names_change_in_executable_code(self):
        for name in ("experiment.py", "verify_return.py", "analyse.py"):
            before = ast.parse((OLD / name).read_text())
            for node in ast.walk(before):
                if isinstance(node, ast.ImportFrom) and node.module == "design":
                    node.module = "reader_attribution_design"
            self.assertEqual(ast.dump(before), ast.dump(ast.parse((NEW / name).read_text())))

    def test_schedule_module_is_exact_rename(self):
        self.assertEqual(
            (OLD / "design.py").read_bytes(), (NEW / "reader_attribution_design.py").read_bytes()
        )
        self.assertFalse((NEW / "design.py").exists())

    def test_no_other_old_artifact_changes(self):
        changed = {
            "experiment.py",
            "verify_return.py",
            "analyse.py",
            "design.py",
            "SHA256SUMS",
            "submit.sh",
        }
        for source in OLD.iterdir():
            if source.is_file() and source.name not in changed:
                self.assertEqual(source.read_bytes(), (NEW / source.name).read_bytes(), source.name)

    def test_native_preflight_is_required_before_submission(self):
        original = (OLD / "submit.sh").read_text()
        marker = '/opt/slurm/bin/sbatch --test-only "${args[@]}"'
        self.assertEqual(
            (NEW / "submit.sh").read_text(),
            original.replace(marker, "bash ./startup-preflight.sh\n" + marker),
        )
        script = (NEW / "startup-preflight.sh").read_text()
        self.assertNotIn("--loader-only", script)
        self.assertIn("for phase in timing work", script)

    def test_schedule_and_all_role_assignments_are_identical(self):
        old = load(OLD / "design.py", "old_schedule_probe")
        new = load(NEW / "reader_attribution_design.py", "new_schedule_probe")
        self.assertEqual(old.BLOCKS, new.BLOCKS)
        self.assertEqual(old.FAMILIES, new.FAMILIES)
        self.assertEqual(old.ARMS, new.ARMS)
        self.assertEqual(new.TOTAL_ATTEMPTS, 684950)
        for ti in range(7):
            for cycle, rotation in old.BLOCKS:
                for reader in range(20):
                    self.assertEqual(old.role(reader, rotation), new.role(reader, rotation))
                    self.assertEqual(
                        old.cpu_for(reader, ti, [1, 3, 5, 7]), new.cpu_for(reader, ti, [1, 3, 5, 7])
                    )
                for position in range(450):
                    self.assertEqual(
                        old.order_for(position, cycle, rotation, ti),
                        new.order_for(position, cycle, rotation, ti),
                    )

    def test_original_archive_and_freeze_preserved(self):
        def sha(path):
            with path.open("rb") as handle:
                return hashlib.file_digest(handle, "sha256").hexdigest()

        self.assertEqual(
            sha(OLD.with_suffix(".tar.gz")),
            "5ea46c974ea9e6e2a6d367ab72e025528e08eda9b63834e4cd1b6128d4de826f",
        )
        self.assertEqual(
            sha(STUDY / "freeze/reader-attribution-v1.json"),
            "c8e4079c62a22e22c0e831152b82c2756fd3c2e4e502e2fb20a76dd933648d73",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
