"""Convert one or more Graphify graphs into a compact Atlas search index.

Graphify remains a supplementary discovery source.  This adapter deliberately
does not merge Graphify edges into the Atlas execution graph: WRF-specific
Registry and dispatch relationships continue to come from the Atlas indexer.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


LINE_RE = re.compile(r"L(?P<start>\d+)(?:-L?(?P<end>\d+))?", re.IGNORECASE)
SOURCE_SUFFIXES = {
    ".f", ".f90", ".f95", ".f03", ".f08", ".inc",
    ".c", ".h", ".cpp", ".hpp", ".py", ".sh",
}


@dataclass(frozen=True)
class GraphifyInput:
    graph_path: Path
    path_prefix: str = ""


def _line_number(location: Any) -> int | None:
    match = LINE_RE.search(str(location or ""))
    return int(match.group("start")) if match else None


def _normalise_path(path: Any, prefix: str) -> str:
    value = str(path or "").replace("\\", "/").lstrip("./")
    clean_prefix = prefix.replace("\\", "/").strip("/")
    if not value:
        return clean_prefix
    if clean_prefix and not value.lower().startswith(f"{clean_prefix.lower()}/"):
        return f"{clean_prefix}/{value}"
    return value


def _node_kind(node: dict[str, Any], defined_ids: set[str]) -> str:
    if node.get("_callable_class"):
        return "class"
    if node.get("_callable"):
        return "routine"
    label = str(node.get("label") or "")
    if Path(label).suffix.lower() in SOURCE_SUFFIXES:
        return "source_file"
    if str(node.get("id")) in defined_ids:
        return "symbol"
    return str(node.get("file_type") or "concept")


def build_search_index(
    inputs: Iterable[GraphifyInput],
    *,
    source_label: str,
    source_commit: str,
    graphify_version: str,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    connections: list[dict[str, Any]] = []
    seen_entries: set[tuple[str, str, int | None, str]] = set()
    scopes: list[str] = []

    for graph_input in inputs:
        raw = json.loads(graph_input.graph_path.read_text(encoding="utf-8"))
        nodes = raw.get("nodes") or []
        edges = raw.get("edges") or []
        prefix = graph_input.path_prefix.strip("/\\")
        scopes.append(prefix or ".")
        namespace = prefix.replace("/", ":").replace("\\", ":") or "root"

        node_by_id = {str(node.get("id")): node for node in nodes if node.get("id") is not None}
        defined_ids = {
            str(edge.get("target"))
            for edge in edges
            if str(edge.get("relation", "")).lower() == "defines"
        }
        relation_map: dict[str, list[str]] = {node_id: [] for node_id in node_by_id}

        for edge in edges:
            source = str(edge.get("source") or "")
            target = str(edge.get("target") or "")
            relation = str(edge.get("relation") or "related_to")
            target_label = str(node_by_id.get(target, {}).get("label") or target)
            source_label_value = str(node_by_id.get(source, {}).get("label") or source)
            if source in relation_map:
                relation_map[source].append(f"{relation} {target_label}")
            if target in relation_map:
                relation_map[target].append(f"{relation} from {source_label_value}")

            if source and target:
                connections.append({
                    "source": f"graphify:{namespace}:{source}",
                    "target": f"graphify:{namespace}:{target}",
                    "relation": relation,
                    "confidence": str(edge.get("confidence") or "INFERRED").lower(),
                    "path": _normalise_path(edge.get("source_file"), prefix),
                    "line": _line_number(edge.get("source_location")),
                })

        for node_id, node in node_by_id.items():
            path = _normalise_path(node.get("source_file"), prefix)
            if not path:
                continue
            label = str(node.get("label") or node_id)
            line = _line_number(node.get("source_location"))
            kind = _node_kind(node, defined_ids)
            identity = (label.lower(), path.lower(), line, kind)
            if identity in seen_entries:
                continue
            seen_entries.add(identity)
            relations = list(dict.fromkeys(relation_map.get(node_id, [])))[:8]
            entries.append({
                "id": f"graphify:{namespace}:{node_id}",
                "label": label,
                "kind": kind,
                "path": path,
                "line": line,
                "confidence": "extracted" if node.get("_origin") == "ast" else "inferred",
                "origin": "graphify",
                "relations": relations,
            })

    entries.sort(key=lambda item: (item["label"].lower(), item["path"].lower(), item["line"] or 0))
    connections.sort(key=lambda item: (item["source"], item["target"], item["relation"]))
    return {
        "schemaVersion": 1,
        "metadata": {
            "provider": "graphify",
            "role": "supplementary-code-search",
            "graphifyVersion": graphify_version,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "sourceLabel": source_label,
            "sourceCommit": source_commit,
            "scopes": scopes,
            "stats": {
                "entries": len(entries),
                "connections": len(connections),
            },
        },
        "entries": entries,
        "connections": connections,
    }


def write_search_index(index: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
