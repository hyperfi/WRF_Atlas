"""Run Graphify over selected WRF source areas and build the Atlas sidecar index."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from graphify_adapter import GraphifyInput, build_search_index, write_search_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WRF_ROOT = Path(os.environ.get("WRF_SOURCE_ROOT", r"E:\QWRF\WRF"))
DEFAULT_SCOPES = ("main", "share", "frame", "dyn_em", "phys")
GRAPHIFY_VERSION = "0.9.63"


def _graphify_command() -> list[str]:
    uv = shutil.which("uv")
    if uv:
        return [uv, "tool", "run", "--from", f"graphifyy=={GRAPHIFY_VERSION}", "graphify"]
    executable = shutil.which("graphify")
    if executable:
        version = subprocess.run(
            [executable, "--version"], capture_output=True, text=True, check=False
        )
        if version.returncode == 0 and version.stdout.strip() == f"graphify {GRAPHIFY_VERSION}":
            return [executable]
        raise RuntimeError(
            f"Graphify {GRAPHIFY_VERSION} is required, but {version.stdout.strip() or executable} "
            "is installed. Install uv for the pinned release or install that Graphify version."
        )
    raise RuntimeError(
        "Graphify is not available. Install uv, then run: "
        f"uv tool install graphifyy=={GRAPHIFY_VERSION}"
    )


def _git_value(root: Path, *args: str, default: str = "unknown") -> str:
    try:
        value = subprocess.check_output(
            ["git", *args], cwd=root, text=True, stderr=subprocess.DEVNULL
        ).strip()
        return value or default
    except (OSError, subprocess.CalledProcessError):
        return default


def run_pipeline(args: argparse.Namespace) -> Path:
    wrf_root = args.wrf_root.resolve()
    if not wrf_root.is_dir():
        raise FileNotFoundError(f"WRF source root does not exist: {wrf_root}")

    command = _graphify_command()
    graph_inputs: list[GraphifyInput] = []
    for scope in args.scope:
        relative_scope = Path(scope)
        if relative_scope.is_absolute() or ".." in relative_scope.parts:
            raise ValueError(f"Scope must stay inside the WRF checkout: {scope}")
        source_dir = wrf_root / relative_scope
        if not source_dir.is_dir():
            print(f"[graphify] skipping missing scope: {scope}", file=sys.stderr)
            continue
        scope_key = scope.replace("\\", "_").replace("/", "_")
        scope_output = args.work_dir / scope_key
        graph_path = scope_output / "graphify-out" / "graph.json"
        if not args.adapt_only:
            scope_output.mkdir(parents=True, exist_ok=True)
            run_command = [
                *command, "extract", str(source_dir), "--code-only", "--no-cluster",
                "--out", str(scope_output),
            ]
            print(f"[graphify] indexing {source_dir}")
            try:
                subprocess.run(run_command, cwd=PROJECT_ROOT, check=True)
            except subprocess.CalledProcessError as error:
                detail = (
                    " (Windows access violation; check the Graphify version and try again)"
                    if error.returncode in (3221225477, -1073741819) else ""
                )
                raise RuntimeError(
                    f"Graphify failed while indexing {scope} (exit {error.returncode}){detail}. "
                    f"The previous Atlas search index was kept."
                ) from error
        if not graph_path.is_file():
            raise FileNotFoundError(f"Graphify did not produce {graph_path}")
        graph_inputs.append(GraphifyInput(graph_path=graph_path, path_prefix=scope))

    if not graph_inputs:
        raise RuntimeError("No Graphify scopes were indexed")

    commit = _git_value(wrf_root, "rev-parse", "HEAD")
    label = args.source_label or f"WRF checkout {wrf_root.name}"
    index = build_search_index(
        graph_inputs,
        source_label=label,
        source_commit=commit,
        graphify_version=GRAPHIFY_VERSION,
    )
    write_search_index(index, args.output)
    print(
        f"[graphify] Atlas search index: {args.output} "
        f"({len(index['entries'])} entries, {len(index['connections'])} connections)"
    )
    return args.output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrf-root", type=Path, default=DEFAULT_WRF_ROOT)
    parser.add_argument(
        "--output", type=Path,
        default=PROJECT_ROOT / "public" / "data" / "local" / "graphify-search.json",
    )
    parser.add_argument(
        "--work-dir", type=Path,
        default=PROJECT_ROOT / ".graphify-work",
    )
    parser.add_argument("--scope", action="append", default=[])
    parser.add_argument("--source-label", default="")
    parser.add_argument(
        "--adapt-only", action="store_true",
        help="Reuse graphs already present under --work-dir.",
    )
    args = parser.parse_args()
    args.scope = args.scope or list(DEFAULT_SCOPES)
    args.output = args.output.resolve()
    args.work_dir = args.work_dir.resolve()
    return args


if __name__ == "__main__":
    run_pipeline(parse_args())
