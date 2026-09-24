import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import graphify_pipeline


class GraphifyCommandTests(unittest.TestCase):
    def test_prefers_pinned_uv_release_over_installed_graphify(self):
        with patch.object(graphify_pipeline.shutil, "which", side_effect=lambda name: {"uv": "uv.exe", "graphify": "graphify.exe"}.get(name)):
            self.assertEqual(
                graphify_pipeline._graphify_command(),
                ["uv.exe", "tool", "run", "--from", "graphifyy==0.9.63", "graphify"],
            )

    def test_rejects_unpinned_installed_release_without_uv(self):
        with patch.object(graphify_pipeline.shutil, "which", side_effect=lambda name: "graphify.exe" if name == "graphify" else None):
            with patch.object(graphify_pipeline.subprocess, "run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "graphify 0.9.66\n"
                with self.assertRaisesRegex(RuntimeError, "0.9.63 is required"):
                    graphify_pipeline._graphify_command()


if __name__ == "__main__":
    unittest.main()
