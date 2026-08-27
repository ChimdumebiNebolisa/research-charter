from __future__ import annotations

import json
import math
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FoundationTests(unittest.TestCase):
    def run_check(self, script: str, *args: str) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

    def test_registry_has_exactly_three_frozen_questions(self) -> None:
        registry = json.loads((ROOT / "problems" / "PROBLEM_REGISTRY.json").read_text(encoding="utf-8"))
        expected = {"dts_7_5", "heilbronn_n12", "kserver_k4_circle"}
        self.assertEqual(set(registry["allowed_problem_ids"]), expected)
        self.assertEqual({item["problem_id"] for item in registry["problems"]}, expected)
        self.assertEqual(len(registry["problems"]), 3)

    def test_frozen_numeric_sanity(self) -> None:
        registry = json.loads((ROOT / "problems" / "PROBLEM_REGISTRY.json").read_text(encoding="utf-8"))
        by_id = {item["problem_id"]: item for item in registry["problems"]}
        self.assertEqual(by_id["dts_7_5"]["baseline"]["value"], 112)
        self.assertEqual(by_id["dts_7_5"]["target"]["value"], 111)
        self.assertEqual(by_id["kserver_k4_circle"]["baseline"]["value"], 3)
        self.assertEqual(by_id["kserver_k4_circle"]["target"]["value"], 3)
        self.assertEqual(by_id["kserver_k4_circle"]["target"]["operator"], "<")
        A = 27 + 3 * math.sqrt(57)
        x = 1 - (A ** (2 / 3) + 6) / (6 * A ** (1 / 3))
        y = 2 * x * x - 3 * x + 0.5
        baseline = x / 4 + x * y / 2 - x * x / 2
        self.assertAlmostEqual(x, 0.115353822881, places=10)
        self.assertAlmostEqual(y, 0.180551540264, places=10)
        self.assertAlmostEqual(baseline, 0.032598858692, places=11)

    def test_upstream_lock_has_pinned_code_revisions(self) -> None:
        lock = json.loads((ROOT / "upstreams.lock.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(lock["sources"]), 8)
        pinned = [item for item in lock["sources"] if item["kind"] == "upstream_repository"]
        self.assertTrue(pinned)
        for item in pinned:
            self.assertRegex(item["commit_sha"], r"^[0-9a-f]{40}$")
            self.assertTrue(item["url"].startswith("https://"))

    def test_record_checks_accept_valid_fixtures(self) -> None:
        fixture_dir = str(ROOT / "tests" / "fixtures")
        self.run_check("validate_experiment.py", "--path", fixture_dir)
        self.run_check("validate_candidate.py", "--path", fixture_dir)
        self.run_check("check_drift.py", "--path", fixture_dir)
        self.run_check("validate_decision.py")

    def test_phase_status_matches_authorization(self) -> None:
        status = json.loads((ROOT / "state" / "RESEARCH_STATUS.json").read_text(encoding="utf-8"))
        if status["phase_2_authorized"]:
            self.assertEqual(status["phase"], "phase2")
            self.assertGreater(status["experiments_run"], 0)
            self.assertTrue(status["novel_research_started"])
        else:
            self.assertEqual(status["phase"], "foundation")
            self.assertEqual(status["experiments_run"], 0)
            self.assertFalse(status["novel_research_started"])


if __name__ == "__main__":
    unittest.main()
