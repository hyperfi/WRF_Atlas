import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_ROOT = PROJECT_ROOT / "public" / "data" / "snapshots"


class PublicSnapshotTests(unittest.TestCase):
    def test_manifest_defaults_to_latest_pinned_release(self):
        manifest = json.loads((SNAPSHOT_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["defaultSnapshot"], "wrf-v4.8.0")
        self.assertEqual(
            [item["id"] for item in manifest["snapshots"]],
            ["wrf-v4.8.0", "wrf-v4.7.1"],
        )

    def test_public_snapshots_have_exact_provenance_without_local_paths(self):
        expected = {
            "wrf-v4.7.1.json": ("4.7.1", "f52c197ed39d12e087d02c50f412d90d418f6186", 3),
            "wrf-v4.8.0.json": ("4.8.0", "06d4240ae989cc3e50af412bb472df3d9048783c", 8),
        }

        for filename, (version, commit, submodule_count) in expected.items():
            with self.subTest(filename=filename):
                graph = json.loads((SNAPSHOT_ROOT / filename).read_text(encoding="utf-8"))
                metadata = graph["metadata"]
                self.assertEqual(metadata["wrf_version"], version)
                self.assertEqual(metadata["commit"], commit)
                self.assertEqual(metadata["source_mode"], "upstream")
                self.assertFalse(metadata["dirty"])
                self.assertIsNone(metadata["source_root"])
                self.assertEqual(len(metadata["submodules"]), submodule_count)


if __name__ == "__main__":
    unittest.main()
