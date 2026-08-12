import argparse
import logging
import os
import sys
import time

# Support running as both `python main.py` and `python -m indexer.main`
try:
    from .config import DEFAULT_WRF_SOURCE_ROOT, DEFAULT_OUTPUT_FILE
    from .graph_builder import build_graph
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from indexer.config import DEFAULT_WRF_SOURCE_ROOT, DEFAULT_OUTPUT_FILE
    from indexer.graph_builder import build_graph

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

def main():
    parser = argparse.ArgumentParser(description="WRF Code Atlas Indexer")
    parser.add_argument('--wrf-root', type=str, default=DEFAULT_WRF_SOURCE_ROOT,
                        help=f"Path to WRF source root (default: {DEFAULT_WRF_SOURCE_ROOT})")
    parser.add_argument('--output-dir', type=str, default=None,
                        help="Path to output directory. If set, overrides the default output file.")
    parser.add_argument('--output', type=str, default=None,
                        help="Exact output JSON path. Takes precedence over --output-dir.")
    parser.add_argument('--source-id', type=str, default='local-wrf',
                        help="Stable source/snapshot identifier stored in provenance.")
    parser.add_argument('--source-label', type=str, default='Local WRF checkout',
                        help="Human-readable source label.")
    parser.add_argument('--source-mode', choices=('local', 'upstream', 'fork'), default='local',
                        help="How the indexed source is made available to the Atlas.")
    parser.add_argument('--repository-url', type=str, default=None,
                        help="Public Git repository used for source links.")
    parser.add_argument('--tag', type=str, default=None,
                        help="Release tag or source label, for example v4.8.0.")
    parser.add_argument('--include-local-path', action='store_true',
                        help="Include the absolute source root in generated metadata.")
    
    args = parser.parse_args()
    
    setup_logging()
    logger = logging.getLogger('indexer.main')
    
    wrf_root = args.wrf_root
    
    if args.output:
        output_file = os.path.abspath(args.output)
    elif args.output_dir:
        output_file = os.path.join(args.output_dir, "wrf-knowledge-graph.json")
    else:
        output_file = DEFAULT_OUTPUT_FILE
        
    logger.info("Starting WRF Code Atlas Indexer...")
    logger.info(f"WRF Source Root: {wrf_root}")
    logger.info(f"Output File: {output_file}")
    
    start_time = time.time()
    
    try:
        build_graph(wrf_root, output_file, {
            'source_id': args.source_id,
            'source_label': args.source_label,
            'source_mode': args.source_mode,
            'repository_url': args.repository_url,
            'tag': args.tag,
            'include_local_path': args.include_local_path,
        })
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return 1
        
    elapsed = time.time() - start_time
    logger.info(f"Indexing completed successfully in {elapsed:.2f} seconds.")
    
    return 0

if __name__ == "__main__":
    exit(main())
