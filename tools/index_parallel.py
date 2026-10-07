"""Refresh a parallel sidecar without regenerating the existing large graph."""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from indexer.parallel_analysis import write_parallel_index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wrf-root', required=True)
    parser.add_argument('--graph', required=True)
    args = parser.parse_args()
    metadata = json.loads(Path(args.graph).read_text(encoding='utf-8'))['metadata']
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.wrf_root, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain=v1', '--untracked-files=no'], cwd=args.wrf_root, text=True).strip())
    if commit != metadata['commit'] or dirty != metadata.get('dirty'):
        raise SystemExit('Source identity differs from graph. Regenerate the graph with npm run index first.')
    metadata = {**metadata, 'parallel_indexed_at': datetime.now(timezone.utc).isoformat()}
    print(write_parallel_index(args.wrf_root, args.graph, metadata))


if __name__ == '__main__':
    main()
