import copy
import unittest

from sa_observe import CATALOG
from sa_report import interpret


class InterpretationTests(unittest.TestCase):
    def setUp(self):
        sample = dict(
            process=dict(rss="1000000 kB", hwm="2000000 kB"),
            scopes=dict(task=dict(stat=dict(anon=1024**3)), job=dict(stat=dict(file=2 * 1024**3))),
            arrow=dict(live_bytes=0),
        )
        self.points = {name: dict(sample=copy.deepcopy(sample)) for name in CATALOG}

    def test_stable_context_does_not_inform(self):
        self.assertEqual(interpret(self.points)[0], [])

    def test_retention_only_does_not_inform(self):
        self.points["E0.hold_begin"]["sample"]["process"]["rss"] = "3000000 kB"
        self.assertEqual(interpret(self.points)[0], [])

    def test_cursor_drop_is_descriptive(self):
        self.points["S04.cursor_closed"]["sample"]["process"]["rss"] = "500000 kB"
        findings, _ = interpret(self.points)
        self.assertIn("cursor_close_descriptive_bracket", findings)

    def test_norm_hwm_growth_is_descriptive(self):
        self.points["S08.norm_complete"]["sample"]["process"]["hwm"] = "3000000 kB"
        self.assertIn("norm_descriptive_bracket", interpret(self.points)[0])

    def test_default_pool_variation_can_inform(self):
        self.points["V.initial.native640.fetch_return.1237"]["sample"]["arrow"]["live_bytes"] = (
            256 * 1024**2
        )
        self.assertIn("V.initial.native640_default_pool_variation", interpret(self.points)[0])

    def test_file_charge_coincidence_without_ownership(self):
        self.points["R01.source_inventory.after"]["sample"]["scopes"]["job"]["stat"]["file"] += (
            256 * 1024**2
        )
        self.assertIn(
            "R01.source_inventory.before_file_charge_coincidence_no_ownership_claim",
            interpret(self.points)[0],
        )

    def test_file_and_anon_growth_does_not_isolate_file_context(self):
        self.points["R01.source_inventory.after"]["sample"]["scopes"]["job"]["stat"]["file"] += (
            256 * 1024**2
        )
        self.points["R01.source_inventory.after"]["sample"]["scopes"]["task"]["stat"]["anon"] += (
            256 * 1024**2
        )
        self.assertEqual(interpret(self.points)[0], [])
