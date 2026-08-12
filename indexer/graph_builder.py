"""
WRF Code Atlas — Knowledge Graph Builder

Assembles a normalized knowledge graph from:
  1. Registry parsed data (namelist options, packages, state variables)
  2. Fortran parsed data (subroutines, calls, dispatch patterns)

Produces a JSON knowledge graph with nodes and edges that the Vue frontend
can load and visualize interactively.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
import subprocess
import re

try:
    from .config import FORTRAN_EXTENSIONS, PRIORITY_FILES, REGISTRY_MAIN_FILES
    from .fortran_parser import parse_fortran_file
    from .registry_parser import parse_registry
except ImportError:
    from config import FORTRAN_EXTENSIONS, PRIORITY_FILES, REGISTRY_MAIN_FILES
    from fortran_parser import parse_fortran_file
    from registry_parser import parse_registry

logger = logging.getLogger(__name__)


# ─── Human-readable names for physics schemes ───
SCHEME_DESCRIPTIONS = {
    # Land surface
    'slabscheme': 'Slab (Thermal Diffusion)',
    'lsmscheme': 'Noah LSM',
    'ruclsmscheme': 'RUC LSM',
    'noahmpscheme': 'Noah-MP LSM',
    'clmscheme': 'CLM (Community Land Model)',
    'ctsmscheme': 'CTSM',
    'pxlsmscheme': 'Pleim-Xiu LSM',
    'ssibscheme': 'SSiB LSM',
    'nolsmscheme': 'No Land Surface',
    # Urban canopy
    'noahucmscheme': 'Single-layer Urban Canopy Model',
    'bepscheme': 'BEP (Building Effect Parameterization)',
    'bep_bemscheme': 'BEP + BEM (Building Energy Model)',
    # Surface layer
    'sfclayrevscheme': 'Revised MM5 Surface Layer',
    'sfclayscheme': 'MM5 Surface Layer',
    'myjsfcscheme': 'MYJ Surface Layer',
    'qnsesfcscheme': 'QNSE Surface Layer',
    'mynnsfcscheme': 'MYNN Surface Layer',
    'pxsfcscheme': 'Pleim-Xiu Surface Layer',
    'temfsfcscheme': 'TEMF Surface Layer',
    'gfssfcscheme': 'GFS Surface Layer',
    'idealscmsfcscheme': 'Ideal SCM Surface Layer',
    # PBL
    'ysuscheme': 'YSU PBL',
    'myjpblscheme': 'MYJ PBL',
    'qnseblpblscheme': 'QNSE PBL',
    'mynnpblscheme2': 'MYNN 2.5-level PBL',
    'mynnpblscheme3': 'MYNN 3.0-level PBL',
    'mynnpblscheme': 'MYNN PBL',
    'acmpblscheme': 'ACM2 PBL',
    'baborepblscheme': 'BouLac PBL',
    'uwpblscheme': 'UW PBL',
    'temfpblscheme': 'TEMF PBL',
    'shinpblscheme': 'Shin-Hong PBL',
    'gbmpblscheme': 'GBM PBL',
    'kaborepblscheme': 'K-Epsilon PBL',
    'eblscheme': 'E-BL PBL',
    # Microphysics
    'kesslerscheme': 'Kessler',
    'linscheme': 'Lin (Purdue)',
    'wsm3scheme': 'WSM3',
    'wsm5scheme': 'WSM5',
    'wsm6scheme': 'WSM6',
    'etampnew': 'Ferrier (new Eta)',
    'thompson': 'Thompson',
    'morr_two_moment': 'Morrison 2-Moment',
    'wdm5scheme': 'WDM5',
    'wdm6scheme': 'WDM6',
    'p3_1cat': 'P3 1-Category',
    'p3_2cat': 'P3 2-Category',
    'p3_1catice2mom': 'P3 1-Cat + 2-Mom Ice',
    'naborscheme': 'NSSL 2-Moment',
    # Radiation
    'rrtmscheme': 'RRTM LW',
    'rrtmg_lwscheme': 'RRTMG LW',
    'camlwscheme': 'CAM LW',
    'newgoddardlwscheme': 'New Goddard LW',
    'flglwscheme': 'FLG LW',
    'haborlwscheme': 'Held-Suarez LW',
    'swradscheme': 'Dudhia SW',
    'gaborswscheme': 'Goddard SW',
    'camswscheme': 'CAM SW',
    'rrtmg_swscheme': 'RRTMG SW',
    'newgoddardswscheme': 'New Goddard SW',
    'flgswscheme': 'FLG SW',
    # Cumulus
    'kfetascheme': 'Kain-Fritsch',
    'bmjscheme': 'BMJ (Betts-Miller-Janjic)',
    'gdscheme': 'Grell-Devenyi',
    'sasscheme': 'SAS (Simplified Arakawa-Schubert)',
    'g3scheme': 'Grell-3',
    'taborechscheme': 'Tiedtke',
    'ntiedtkescheme': 'New Tiedtke',
    'nsas2dscheme': 'New SAS (NSAS)',
    'camzmscheme': 'CAM Zhang-McFarlane',
    'mushroomscheme': 'Mushroom',
    'kaborescheme': 'KFCUP',
}

# Map namelist variables to physics categories
NAMELIST_TO_CATEGORY = {
    'sf_surface_physics': 'land_surface',
    'sf_sfclay_physics': 'surface_layer',
    'bl_pbl_physics': 'pbl',
    'mp_physics': 'microphysics',
    'ra_lw_physics': 'longwave_radiation',
    'ra_sw_physics': 'shortwave_radiation',
    'cu_physics': 'cumulus',
    'shcu_physics': 'shallow_cumulus',
    'sf_urban_physics': 'urban_canopy',
}

# Map namelist variables to their driver subroutine names
NAMELIST_TO_DRIVER = {
    'sf_surface_physics': 'surface_driver',
    'sf_sfclay_physics': 'surface_driver',
    'bl_pbl_physics': 'pbl_driver',
    'mp_physics': 'microphysics_driver',
    'ra_lw_physics': 'radiation_driver',
    'ra_sw_physics': 'radiation_driver',
    'cu_physics': 'cumulus_driver',
    'shcu_physics': 'shallowcu_driver',
}

# Physics execution order in WRF timestep
PHYSICS_TIMESTEP_ORDER = {
    'radiation_driver': {'phase': 'first_rk_step_part1', 'order': 1,
                         'description': 'Radiation (conditional on radiation interval)'},
    'surface_driver': {'phase': 'first_rk_step_part1', 'order': 2,
                       'description': 'Surface layer + Land surface'},
    'pbl_driver': {'phase': 'first_rk_step_part1', 'order': 3,
                   'description': 'Planetary boundary layer'},
    'cumulus_driver': {'phase': 'first_rk_step_part1', 'order': 4,
                       'description': 'Cumulus convection (conditional on cumulus interval)'},
    'shallowcu_driver': {'phase': 'first_rk_step_part1', 'order': 5,
                          'description': 'Shallow convection'},
    'microphysics_driver': {'phase': 'post_rk_loop', 'order': 6,
                            'description': 'Microphysics (after RK dynamics loop)'},
}


class KnowledgeGraph:
    """Normalized graph with typed nodes and edges."""
    
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[Dict] = []
        self._edge_set: Set[str] = set()  # Dedup key
    
    def add_node(self, id: str, type: str, label: str, data: Dict[str, Any] = None):
        if id not in self.nodes:
            self.nodes[id] = {
                'id': id,
                'type': type,
                'label': label,
                'data': data or {}
            }
        else:
            # Merge data into existing node
            if data:
                self.nodes[id]['data'].update(data)
    
    def add_edge(self, source: str, target: str, type: str, data: Dict[str, Any] = None):
        key = f"{source}|{target}|{type}|{json.dumps(data or {}, sort_keys=True)}"
        if key not in self._edge_set:
            self._edge_set.add(key)
            self.edges.append({
                'source': source,
                'target': target,
                'type': type,
                'data': data or {}
            })
    
    def to_dict(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'metadata': metadata,
            'nodes': list(self.nodes.values()),
            'edges': self.edges
        }


def build_graph(wrf_root: str, output_path: str, source_config: Optional[Dict[str, Any]] = None):
    """Build the complete knowledge graph from WRF source."""
    kg = KnowledgeGraph()
    
    # ════════════════════════════════════════════
    # 1. Parse Registry
    # ════════════════════════════════════════════
    logger.info("Parsing Registry...")
    registry_data = parse_registry(wrf_root)
    
    # Create namelist option nodes
    for rconf in registry_data['rconfig']:
        node_id = f"namelist:{rconf['name']}"
        category = NAMELIST_TO_CATEGORY.get(rconf['name'])
        driver = NAMELIST_TO_DRIVER.get(rconf['name'])
        kg.add_node(node_id, 'namelist_option', rconf['name'], {
            **rconf,
            'category': category,
            'driver': driver,
        })
    
    # Create package nodes and SELECTED_BY edges
    for pkg in registry_data['packages']:
        pkg_id = f"package:{pkg['package_name']}"
        description = SCHEME_DESCRIPTIONS.get(pkg['package_name'], pkg['package_name'])
        nl_var = pkg['namelist_var']
        category = NAMELIST_TO_CATEGORY.get(nl_var)
        
        # Parse state vars from the package
        state_vars = []
        for sv_group in pkg.get('state_vars', []):
            if sv_group and ':' in sv_group:
                prefix, vars_str = sv_group.split(':', 1)
                state_vars.extend([v.strip() for v in vars_str.split(',') if v.strip()])
            elif sv_group and sv_group != '-':
                state_vars.extend([v.strip() for v in sv_group.split(',') if v.strip()])
        
        kg.add_node(pkg_id, 'registry_package', description, {
            'package_name': pkg['package_name'],
            'namelist_var': nl_var,
            'value': pkg['value'],
            'state_vars': state_vars,
            'category': category,
            'description': description,
            'source_file': pkg.get('source_file'),
            'source_line': pkg.get('source_line'),
        })
        
        # Link package to namelist option
        nl_id = f"namelist:{nl_var}"
        kg.add_edge(pkg_id, nl_id, 'SELECTED_BY', {
            'condition': f"{nl_var}=={pkg['value']}",
            'value': pkg['value'],
            'confidence': 'exact',
            'evidence': [{
                'path': pkg.get('source_file', 'Registry/Registry.EM_COMMON').replace('\\', '/'),
                'startLine': pkg.get('source_line'),
                'endLine': pkg.get('source_line'),
                'description': f"package {pkg['package_name']} {nl_var}=={pkg['value']}"
            }]
        })
    
    # Create state variable nodes
    for state in registry_data['states']:
        sv_id = f"state:{state['name']}"
        kg.add_node(sv_id, 'state_variable', state['name'], state)
    
    # ════════════════════════════════════════════
    # 2. Create physical process category nodes
    # ════════════════════════════════════════════
    process_meta = {
        'microphysics': 'Cloud & precipitation formation processes',
        'longwave_radiation': 'Longwave (infrared) radiation transfer',
        'shortwave_radiation': 'Shortwave (solar) radiation transfer',
        'surface_layer': 'Surface-atmosphere exchange coefficients',
        'land_surface': 'Land-surface energy/moisture balance',
        'pbl': 'Planetary boundary layer mixing',
        'cumulus': 'Sub-grid cumulus convection',
        'shallow_cumulus': 'Shallow convection',
        'dynamics': 'Atmospheric dynamics (RK integration)',
    }
    for proc, desc in process_meta.items():
        kg.add_node(f"process:{proc}", 'physical_process', proc, {
            'description': desc
        })
    
    # Create timestep phase nodes
    phases = {
        'initialization': 'Model initialization and configuration',
        'first_rk_step_part1': 'Physics (radiation, surface, PBL, cumulus)',
        'rk_dynamics_loop': 'Runge-Kutta dynamics integration',
        'post_rk_loop': 'Post-RK physics (microphysics)',
        'output_nesting': 'Output and nesting operations',
    }
    for phase, desc in phases.items():
        kg.add_node(f"phase:{phase}", 'phase', phase, {'description': desc})
    
    # ════════════════════════════════════════════
    # 3. Parse Fortran files
    # ════════════════════════════════════════════
    logger.info("Parsing Fortran files...")
    
    fortran_files = _collect_fortran_files(wrf_root)
    logger.info(f"Found {len(fortran_files)} Fortran files to parse.")
    
    # Parse all files and collect results
    all_parsed = {}
    for filepath in fortran_files:
        try:
            f_data = parse_fortran_file(filepath)
            rel_path = os.path.relpath(filepath, wrf_root)
            all_parsed[rel_path] = f_data
            
            # Source file node
            file_id = f"file:{rel_path}"
            kg.add_node(file_id, 'source_file', os.path.basename(filepath), {
                'path': rel_path,
                'full_path': filepath
            })
            
            # Programs
            for prog in f_data['programs']:
                pid = f"program:{prog['name']}"
                kg.add_node(pid, 'program', prog['name'], {
                    'file': rel_path, 'line': prog['line']
                })
                kg.add_edge(pid, file_id, 'DEFINED_IN', {
                    'evidence': [{'path': rel_path, 'startLine': prog['line']}],
                    'confidence': 'exact'
                })
            
            # Modules
            for mod in f_data['modules']:
                mid = f"module:{mod['name']}"
                kg.add_node(mid, 'module', mod['name'], {
                    'file': rel_path, 'line': mod['line']
                })
                kg.add_edge(mid, file_id, 'DEFINED_IN', {
                    'evidence': [{'path': rel_path, 'startLine': mod['line']}],
                    'confidence': 'exact'
                })
            
            # Subroutines
            for sub in f_data['subroutines']:
                sid = f"subroutine:{sub['name']}"
                is_driver = sub['name'].endswith('_driver')
                node_type = 'driver' if is_driver else 'subroutine'
                kg.add_node(sid, node_type, sub['name'], {
                    'file': rel_path,
                    'line': sub['line'],
                    'args': sub.get('args', [])
                })
                kg.add_edge(sid, file_id, 'DEFINED_IN', {
                    'evidence': [{'path': rel_path, 'startLine': sub['line']}],
                    'confidence': 'exact'
                })
                
                # Link drivers to physical processes. Timestep phase edges are
                # added later from real CALL edges and their source locations.
                if is_driver:
                    # Link to process categories
                    for nl_var, driver_name in NAMELIST_TO_DRIVER.items():
                        if sub['name'] == driver_name:
                            cat = NAMELIST_TO_CATEGORY[nl_var]
                            kg.add_edge(sid, f"process:{cat}", 'BELONGS_TO', {
                                'confidence': 'exact'
                            })
            
            # Functions
            for func in f_data.get('functions', []):
                fid = f"function:{func['name']}"
                kg.add_node(fid, 'function', func['name'], {
                    'file': rel_path, 'line': func['line']
                })
                kg.add_edge(fid, file_id, 'DEFINED_IN', {
                    'evidence': [{'path': rel_path, 'startLine': func['line']}],
                    'confidence': 'exact'
                })
            
            # CALL edges (with dispatch context)
            for call in f_data['calls']:
                caller_kind = call.get('caller_type') or 'subroutine'
                caller_prefix = {
                    'program': 'program',
                    'module': 'module',
                    'function': 'function',
                    'subroutine': 'subroutine',
                }.get(caller_kind, 'subroutine')
                caller_id = f"{caller_prefix}:{call['caller']}" if call['caller'] else file_id
                target_id = f"subroutine:{call['subroutine']}"
                
                # Ensure target node exists
                kg.add_node(target_id, 'subroutine', call['subroutine'])
                
                call_data = {
                    'evidence': [{
                        'path': rel_path,
                        'startLine': call['line'],
                        'endLine': call.get('end_line', call['line'])
                    }],
                    'confidence': 'exact'
                }
                
                # If this call is inside a physics dispatch SELECT CASE
                dispatch_var = call.get('dispatch_var')
                dispatch_value = call.get('dispatch_value')
                if dispatch_var and dispatch_value:
                    call_data['dispatch_var'] = dispatch_var
                    call_data['dispatch_value'] = dispatch_value
                    
                    # Create ACTIVE_WHEN edge
                    nl_id = f"namelist:{dispatch_var}"
                    if nl_id in kg.nodes or dispatch_var in NAMELIST_TO_CATEGORY:
                        kg.add_edge(target_id, nl_id, 'ACTIVE_WHEN', {
                            'condition': f"{dispatch_var}=={dispatch_value}",
                            'value': dispatch_value,
                            'evidence': [{
                                'path': rel_path,
                                'startLine': call['line'],
                                'endLine': call.get('end_line', call['line'])
                            }],
                            'confidence': 'exact'
                        })
                
                kg.add_edge(caller_id, target_id, 'CALLS', call_data)
            
            # USE edges
            for use in f_data['use_stmts']:
                scope_id = f"subroutine:{use['scope']}" if use['scope'] else file_id
                mod_id = f"module:{use['module']}"
                kg.add_node(mod_id, 'module', use['module'])
                kg.add_edge(scope_id, mod_id, 'USES', {
                    'evidence': [{'path': rel_path, 'startLine': use['line']}],
                    'confidence': 'exact'
                })
            
            # Config refs (READS_CONFIG edges)
            for ref in f_data['config_refs']:
                scope_id = f"subroutine:{ref['scope']}" if ref['scope'] else file_id
                nl_id = f"namelist:{ref['var']}"
                kg.add_edge(scope_id, nl_id, 'READS_CONFIG', {
                    'evidence': [{'path': rel_path, 'startLine': ref['line']}],
                    'ref_type': ref.get('type', 'unknown'),
                    'confidence': 'exact'
                })
            
            # SELECT CASE blocks (enrich with structured dispatch info)
            for sc in f_data['select_cases']:
                if sc.get('config_var'):
                    var = sc['config_var']
                    for case in sc.get('cases', []):
                        case_val = case.get('value', '')
                        for case_call in case.get('calls', []):
                            target_id = f"subroutine:{case_call['name']}"
                            nl_id = f"namelist:{var}"
                            kg.add_edge(target_id, nl_id, 'ACTIVE_WHEN', {
                                'condition': f"{var}=={case_val}",
                                'value': case_val,
                                'evidence': [{
                                    'path': rel_path,
                                    'startLine': case_call.get('line', case.get('line', 0)),
                                }],
                                'confidence': 'exact'
                            })
                            
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
    
    # ════════════════════════════════════════════
    # 4. Build conceptual timestep phases from exact, indexed call sites.
    _link_execution_phases_from_calls(kg)

    # 5. Link packages to implementation subroutines
    # ════════════════════════════════════════════
    _link_packages_to_implementations(kg)
    
    # ════════════════════════════════════════════
    # 6. Save output
    # ════════════════════════════════════════════
    source_config = source_config or {}

    def git_output(*args: str, default: str = "unknown") -> str:
        try:
            return subprocess.check_output(
                ['git', *args], cwd=wrf_root, text=True,
                stderr=subprocess.DEVNULL
            ).strip() or default
        except Exception:
            return default

    commit = git_output('rev-parse', 'HEAD')
    branch = git_output('rev-parse', '--abbrev-ref', 'HEAD')
    tag = source_config.get('tag') or git_output('describe', '--tags', '--exact-match', default='')
    repository_url = source_config.get('repository_url') or git_output('remote', 'get-url', 'origin', default='')
    if repository_url.endswith('.git'):
        repository_url = repository_url[:-4]

    version = tag.lstrip('v') if tag else ''
    if not version:
        readme_path = os.path.join(wrf_root, 'README')
        try:
            with open(readme_path, 'r', encoding='utf-8', errors='replace') as readme:
                match = re.search(r'WRF Model Version\s+([0-9]+(?:\.[0-9]+)+)', readme.read(4096), re.I)
                version = match.group(1) if match else 'unknown'
        except OSError:
            version = 'unknown'

    try:
        dirty = bool(subprocess.check_output(
            ['git', 'status', '--porcelain=v1', '--untracked-files=no'],
            cwd=wrf_root, text=True, stderr=subprocess.DEVNULL
        ).strip())
    except Exception:
        dirty = None

    submodules = []
    try:
        for line in subprocess.check_output(
            ['git', 'submodule', 'status', '--recursive'], cwd=wrf_root,
            text=True, stderr=subprocess.DEVNULL
        ).splitlines():
            match = re.match(r'^[ +\-U]?([0-9a-f]+)\s+([^\s]+)', line.strip())
            if match:
                submodules.append({'path': match.group(2), 'commit': match.group(1)})
    except Exception:
        pass
    
    metadata = {
        'wrf_version': version,
        'commit': commit,
        'branch': branch,
        'tag': tag or None,
        'dirty': dirty,
        'source_id': source_config.get('source_id', 'local-wrf'),
        'source_label': source_config.get('source_label', 'Local WRF checkout'),
        'source_mode': source_config.get('source_mode', 'local'),
        'repository_url': repository_url or None,
        'submodules': submodules,
        'indexed_at': datetime.now().isoformat(),
        'source_root': wrf_root if source_config.get('include_local_path') else None,
        'stats': {
            'total_nodes': len(kg.nodes),
            'total_edges': len(kg.edges),
            'fortran_files_parsed': len(all_parsed),
            'registry_packages': len(registry_data['packages']),
            'namelist_options': len(registry_data['rconfig']),
            'state_variables': len(registry_data['states']),
        }
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(kg.to_dict(metadata), f)
    
    logger.info(f"Graph built: {len(kg.nodes)} nodes, {len(kg.edges)} edges.")
    logger.info(f"Output: {output_path}")


def _collect_fortran_files(wrf_root: str) -> List[str]:
    """Collect all Fortran files to parse, prioritizing driver files."""
    fortran_files = []
    seen = set()
    
    # Priority files first
    for pf in PRIORITY_FILES:
        full_path = os.path.join(wrf_root, pf)
        if os.path.exists(full_path):
            fortran_files.append(full_path)
            seen.add(os.path.normpath(full_path))
    
    # Then scan directories
    for search_dir in ['phys', 'dyn_em', 'main', 'frame', 'share']:
        dir_path = os.path.join(wrf_root, search_dir)
        if not os.path.isdir(dir_path):
            continue
        for root, _, files in os.walk(dir_path):
            for file in sorted(files):
                if any(file.endswith(ext) for ext in FORTRAN_EXTENSIONS):
                    full_path = os.path.join(root, file)
                    norm = os.path.normpath(full_path)
                    if norm not in seen:
                        seen.add(norm)
                        fortran_files.append(full_path)
    
    return fortran_files


def _link_packages_to_implementations(kg: KnowledgeGraph):
    """
    For each registry package, try to find the implementation subroutine
    it's linked to via ACTIVE_WHEN edges, and create BELONGS_TO edges
    from the subroutine to the package's physical process category.
    """
    for node in list(kg.nodes.values()):
        if node['type'] == 'registry_package':
            pkg_name = node['data'].get('package_name', '')
            nl_var = node['data'].get('namelist_var', '')
            value = node['data'].get('value', '')
            category = node['data'].get('category')
            
            if not category:
                continue
            
            # Find all subroutines that are ACTIVE_WHEN this specific value
            nl_id = f"namelist:{nl_var}"
            for edge in kg.edges:
                if (edge['type'] == 'ACTIVE_WHEN' and
                    edge['target'] == nl_id and
                    edge['data'].get('value') == value):
                    # This subroutine activates for this package
                    sub_id = edge['source']
                    kg.add_edge(sub_id, f"process:{category}", 'BELONGS_TO', {
                        'via_package': pkg_name,
                        'confidence': 'inferred'
                    })
                    # Link package to its implementation
                    kg.add_edge(node['id'], sub_id, 'ACTIVATES', {
                        'condition': f"{nl_var}=={value}",
                        'confidence': 'inferred'
                    })


def _link_execution_phases_from_calls(kg: KnowledgeGraph):
    """Attach driver phase/order metadata only when an exact parent CALL exists."""
    phase_bindings = {
        'first_rk_step_part1': {
            'phase': 'first_rk_step_part1',
            'drivers': {
                'radiation_driver', 'surface_driver', 'pbl_driver',
                'cumulus_driver', 'shallowcu_driver',
            },
        },
        'solve_em': {
            'phase': 'post_rk_loop',
            'drivers': {'microphysics_driver'},
        },
    }

    for parent_name, binding in phase_bindings.items():
        parent_id = f"subroutine:{parent_name}"
        matching_calls = [
            edge for edge in kg.edges
            if edge['type'] == 'CALLS'
            and edge['source'] == parent_id
            and edge['target'].removeprefix('subroutine:') in binding['drivers']
            and edge.get('data', {}).get('evidence')
        ]
        matching_calls.sort(
            key=lambda edge: edge['data']['evidence'][0].get('startLine', 0)
        )

        seen_targets = set()
        ordered_unique_calls = []
        for edge in matching_calls:
            if edge['target'] in seen_targets:
                continue
            seen_targets.add(edge['target'])
            ordered_unique_calls.append(edge)

        for order, call_edge in enumerate(ordered_unique_calls, 1):
            kg.add_edge(call_edge['target'], f"phase:{binding['phase']}", 'EXECUTES_DURING', {
                'order': order,
                'parent': parent_id,
                'evidence': call_edge['data']['evidence'],
                'confidence': 'exact',
            })
