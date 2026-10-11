import unittest
from pathlib import Path

from kpi_engine import load_config, run
from kpi_engine.alerts import classify
from kpi_engine.diagnosis import assign_tiers, score_health
from kpi_engine.metrics import ratio

ROOT = Path(__file__).resolve().parent.parent
CONFIG = load_config(ROOT / "config" / "metrics.toml")


def unit(**overrides) -> dict:
    base = {
        "store_id": "S001", "store_name": "测试店", "city": "测试", "model": "MPV", "tier": "一级",
        "traffic": 1000, "leads": 450, "test_drives": 170, "locks": 40,
        "month_target": 60, "achievement": 0.7, "data_issues": [],
        "z": {"lead_rate": 0.0, "td_rate": 0.0, "lock_rate": 0.0},
    }
    base.update(overrides)
    return base


class MetricsTest(unittest.TestCase):
    def test_ratio_handles_zero_denominator(self):
        self.assertIsNone(ratio(3, 0))
        self.assertEqual(ratio(1, 4), 0.25)


class DiagnosisTest(unittest.TestCase):
    def test_tiers_split_evenly_by_volume(self):
        stores = [{"store_id": f"S{i}", "locks": i} for i in range(9)]
        tiers = assign_tiers(stores, "locks", ["一级", "二级", "三级"])
        self.assertEqual(tiers["S8"], "一级")
        self.assertEqual(tiers["S0"], "三级")
        self.assertEqual(sorted(tiers.values()).count("二级"), 3)

    def test_dirty_rows_are_excluded_from_scoring(self):
        rows = [{"tier": "一级", "lock_rate": v, "data_issues": []} for v in (0.2, 0.25, 0.3)]
        rows.append({"tier": "一级", "lock_rate": 3.0, "data_issues": ["locks > test_drives"]})
        score_health(rows, {"lock_rate": 1.0}, center=50, scale=15)
        self.assertIsNone(rows[3]["health"])
        self.assertAlmostEqual(rows[0]["tier_mean"]["lock_rate"], 0.25)
        self.assertAlmostEqual(rows[1]["health"], 50)


class AlertsTest(unittest.TestCase):
    cfg = CONFIG["alerts"]

    def test_data_issue_takes_precedence(self):
        alert = classify(unit(data_issues=["x"], achievement=1.5), self.cfg)
        self.assertEqual((alert["cause"], alert["priority"]), ("数据类", "P2"))

    def test_low_lock_rate_is_efficiency_issue(self):
        alert = classify(unit(z={"lead_rate": 0, "td_rate": 0, "lock_rate": -1.8}), self.cfg)
        self.assertEqual((alert["cause"], alert["priority"]), ("效率类", "P2"))

    def test_small_test_drive_sample_does_not_trigger_efficiency(self):
        u = unit(test_drives=3, achievement=0.9, z={"lead_rate": 0, "td_rate": 0, "lock_rate": -2.5})
        self.assertIsNone(classify(u, self.cfg))

    def test_multiple_weak_stages_become_composite(self):
        u = unit(achievement=0.5, z={"lead_rate": -1.5, "td_rate": -1.2, "lock_rate": 0})
        alert = classify(u, self.cfg)
        self.assertEqual((alert["cause"], alert["priority"]), ("综合类", "P1"))

    def test_on_track_and_tiny_targets_are_skipped(self):
        self.assertIsNone(classify(unit(achievement=1.02), self.cfg))
        self.assertIsNone(classify(unit(month_target=3, achievement=0.2), self.cfg))


class EndToEndTest(unittest.TestCase):
    def test_injected_glitch_is_caught(self):
        ctx = run(load_config(ROOT / "config" / "metrics.toml"), ROOT / "data")
        data_alerts = [a for a in ctx["alerts"] if a["cause"] == "数据类"]
        self.assertEqual([(a["store_id"], a["model"]) for a in data_alerts], [("S011", "家庭SUV")])
        self.assertTrue(all(s["health"] is not None for s in ctx["stores"] if not s["data_issues"]))


if __name__ == "__main__":
    unittest.main()
