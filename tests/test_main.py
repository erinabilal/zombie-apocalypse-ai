"""Unit tests for the headless CLI entry point."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import main as main_mod

ROOT = Path(__file__).resolve().parents[1]


class TestMain(unittest.TestCase):
    """CLI exit codes and repeatable quiet runs."""

    def test_quiet_seed_7_repeatable(self) -> None:
        """Two quiet runs with --seed 7 produce the same printed result line."""
        argv = [
            "--map",
            str(ROOT / "maps" / "small.txt"),
            "--seed",
            "7",
            "--quiet",
            "--zombie-ai",
            "random",
            "--human-ai",
            "random",
            "--healer-ai",
            "random",
        ]
        out1 = io.StringIO()
        out2 = io.StringIO()
        with redirect_stdout(out1):
            code1 = main_mod.main(argv)
        with redirect_stdout(out2):
            code2 = main_mod.main(argv)
        self.assertEqual(code1, 0)
        self.assertEqual(code2, 0)
        self.assertEqual(out1.getvalue(), out2.getvalue())
        self.assertIn("winner=", out1.getvalue())

    def test_invalid_ai_exit_2(self) -> None:
        """Unimplemented AI names exit with code 2 and a clear message."""
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = main_mod.main(
                ["--map", str(ROOT / "maps" / "small.txt"), "--zombie-ai", "qlearning", "--quiet"]
            )
        self.assertEqual(code, 2)
        self.assertIn("not implemented", err.getvalue())

    def test_compare_exit_2(self) -> None:
        """--compare is not available yet and exits 2."""
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = main_mod.main(["--compare"])
        self.assertEqual(code, 2)

    def test_bad_map_exit_2(self) -> None:
        """Missing map file exits 2."""
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = main_mod.main(["--map", "maps/nope.txt", "--quiet"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
