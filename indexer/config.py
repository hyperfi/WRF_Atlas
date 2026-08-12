import os
from pathlib import Path

# Default Paths
DEFAULT_WRF_SOURCE_ROOT = r"E:\QWRF\WRF"
ATLAS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUTPUT_DIR = os.path.join(ATLAS_ROOT, "public", "data")
DEFAULT_OUTPUT_FILE = os.path.join(DEFAULT_OUTPUT_DIR, "wrf-knowledge-graph.json")

# File patterns
FORTRAN_EXTENSIONS = {".F", ".f", ".F90", ".f90", ".inc"}

# Important files to prioritize
PRIORITY_FILES = [
    "phys/module_surface_driver.F",
    "phys/module_radiation_driver.F",
    "phys/module_pbl_driver.F",
    "phys/module_microphysics_driver.F",
    "phys/module_cumulus_driver.F",
    "dyn_em/solve_em.F",
    "dyn_em/module_first_rk_step_part1.F",
    "main/wrf.F",
    "main/module_wrf_top.F",
    "frame/module_configure.F"
]

REGISTRY_MAIN_FILES = [
    "Registry/Registry.EM_COMMON",
    "Registry/registry.dimspec"
]
