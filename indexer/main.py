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
    
    args = parser.parse_args()
    
    setup_logging()
    logger = logging.getLogger('indexer.main')
    
    wrf_root = args.wrf_root
    
    if args.output_dir:
        import os
        output_file = os.path.join(args.output_dir, "wrf-knowledge-graph.json")
    else:
        output_file = DEFAULT_OUTPUT_FILE
        
    logger.info("Starting WRF Code Atlas Indexer...")
    logger.info(f"WRF Source Root: {wrf_root}")
    logger.info(f"Output File: {output_file}")
    
    start_time = time.time()
    
    try:
        build_graph(wrf_root, output_file)
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return 1
        
    elapsed = time.time() - start_time
    logger.info(f"Indexing completed successfully in {elapsed:.2f} seconds.")
    
    return 0

if __name__ == "__main__":
    exit(main())
