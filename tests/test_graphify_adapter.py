import json
import tempfile
import unittest
from pathlib import Path

from tools.graphify_adapter import GraphifyInput, build_search_index


class GraphifyAdapterTests(unittest.TestCase):
    def test_adapts_extracted_symbols_without_promoting_execution_evidence(self):
        fixture = {
            "nodes": [
                {
                    "id": "wrf",
                    "label": "wrf.F",
                    "file_type": "code",
                    "source_file": "wrf.F",
                    "source_location": "L1",
                    "_origin": "ast",
                },
                {
                    "id": "wrf_wrf",
                    "label": "wrf",
                    "file_type": "code",
                    "source_file": "wrf.F",
                    "source_location": "L3",
                    "_origin": "ast",
                },
            ],
            "edges": [
                {
                    "source": "wrf",
                    "target": "wrf_wrf",
                    "relation": "defines",
                    "confidence": "EXTRACTED",
                    "source_file": "wrf.F",
                    "source_location": "L3",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph.json"
            graph_path.write_text(json.dumps(fixture), encoding="utf-8")
            result = build_search_index(
                [GraphifyInput(graph_path, "main")],
                source_label="WRF fixture",
                source_commit="abc123",
                graphify_version="test",
            )

        symbol = next(entry for entry in result["entries"] if entry["label"] == "wrf")
        self.assertEqual(symbol["path"], "main/wrf.F")
        self.assertEqual(symbol["line"], 3)
        self.assertEqual(symbol["kind"], "symbol")
        self.assertEqual(symbol["origin"], "graphify")
        self.assertEqual(result["metadata"]["role"], "supplementary-code-search")
        self.assertNotIn("edges", result)

    def test_rejects_duplicate_entries_from_the_same_source_location(self):
        fixture = {
            "nodes": [
                {"id": "a", "label": "driver", "source_file": "driver.F", "source_location": "L8", "_origin": "ast"},
                {"id": "b", "label": "driver", "source_file": "driver.F", "source_location": "L8", "_origin": "ast"},
            ],
            "edges": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph.json"
            graph_path.write_text(json.dumps(fixture), encoding="utf-8")
            result = build_search_index(
                [GraphifyInput(graph_path, "phys")],
                source_label="fixture",
                source_commit="abc",
                graphify_version="test",
            )
        self.assertEqual(len(result["entries"]), 1)


if __name__ == "__main__":
    unittest.main()
