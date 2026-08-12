"""
WRF Registry Parser

Parses WRF Registry files to extract:
- rconfig entries (namelist configuration variables)
- package entries (namelist value → physics package → state variables)
- state entries (model state variable definitions)
- dimspec entries (dimension specifications)

Handles include directives to follow Registry file chains.
"""

import re
import os
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)

# Regex for extracting quoted strings from Registry lines
RE_QUOTED = re.compile(r'"([^"]*)"')


def parse_registry(root_dir: str,
                   start_files: List[str] = None) -> Dict[str, Any]:
    """
    Parse WRF Registry files starting from the given entry points.
    
    Returns dict with keys: rconfig, packages, states, dimspecs,
    packages_by_namelist (convenience lookup).
    """
    if start_files is None:
        # Try Registry.EM first (it includes Registry.EM_COMMON),
        # fall back to Registry.EM_COMMON directly
        start_files = [
            "Registry/Registry.EM",
            "Registry/Registry.EM_COMMON",
            "Registry/registry.dimspec",
        ]
    
    result = {
        'rconfig': [],
        'packages': [],
        'states': [],
        'dimspecs': [],
        'packages_by_namelist': {},
    }
    
    parsed_files: Set[str] = set()
    
    def process_file(filepath: str, line_offset: int = 0):
        if not os.path.exists(filepath):
            logger.debug(f"Registry file not found: {filepath}")
            return
        
        real_path = os.path.normpath(os.path.realpath(filepath))
        if real_path in parsed_files:
            return
        parsed_files.add(real_path)
        
        rel_path = os.path.relpath(filepath, root_dir)
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, raw_line in enumerate(f, 1):
                    line = raw_line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Split on whitespace, but preserve quoted strings
                    parts = _smart_split(line)
                    if not parts:
                        continue
                    
                    cmd = parts[0].lower()
                    
                    if cmd == 'include':
                        if len(parts) >= 2:
                            inc_file = parts[1].strip('"\'')
                            # Try relative to Registry/ directory
                            inc_path = os.path.join(root_dir, "Registry", inc_file)
                            if not os.path.exists(inc_path):
                                inc_path = os.path.join(os.path.dirname(filepath), inc_file)
                            process_file(inc_path)
                    
                    elif cmd == 'rconfig':
                        entry = _parse_rconfig(parts, rel_path, line_num)
                        if entry:
                            result['rconfig'].append(entry)
                    
                    elif cmd == 'package':
                        entry = _parse_package(parts, rel_path, line_num)
                        if entry:
                            result['packages'].append(entry)
                    
                    elif cmd == 'state':
                        entry = _parse_state(parts, raw_line, rel_path, line_num)
                        if entry:
                            result['states'].append(entry)
                    
                    elif cmd == 'dimspec':
                        entry = _parse_dimspec(parts, rel_path, line_num)
                        if entry:
                            result['dimspecs'].append(entry)
                            
        except Exception as e:
            logger.error(f"Error parsing registry file {filepath}: {e}")
    
    # Process all start files
    for sf in start_files:
        start_path = os.path.join(root_dir, sf)
        process_file(start_path)
    
    # Build convenience lookup: namelist_var -> list of packages
    for pkg in result['packages']:
        nl_var = pkg['namelist_var']
        if nl_var not in result['packages_by_namelist']:
            result['packages_by_namelist'][nl_var] = []
        result['packages_by_namelist'][nl_var].append(pkg)
    
    logger.info(f"Registry: {len(result['rconfig'])} rconfigs, "
                f"{len(result['packages'])} packages, "
                f"{len(result['states'])} states, "
                f"{len(result['dimspecs'])} dimspecs")
    
    return result


def _smart_split(line: str) -> List[str]:
    """Split a line on whitespace, but keep quoted strings together."""
    parts = []
    current = ''
    in_quote = False
    quote_char = ''
    
    for ch in line:
        if in_quote:
            current += ch
            if ch == quote_char:
                in_quote = False
        elif ch in ('"', "'"):
            in_quote = True
            quote_char = ch
            current += ch
        elif ch in (' ', '\t'):
            if current:
                parts.append(current)
                current = ''
        else:
            current += ch
    
    if current:
        parts.append(current)
    
    return parts


def _parse_rconfig(parts: List[str], file: str, line: int) -> Dict[str, Any]:
    """Parse an rconfig entry."""
    # rconfig <type> <name> <namelist_group> <dims> <default> <io_flags> "description" "units" "stagger"
    if len(parts) < 6:
        return None
    
    # Extract quoted strings for description/units
    raw = ' '.join(parts)
    quoted = RE_QUOTED.findall(raw)
    
    entry = {
        'type': parts[1],
        'name': parts[2].lower(),
        'group': parts[3],
        'dims': parts[4],
        'default': parts[5],
        'io_flags': parts[6] if len(parts) > 6 else '',
        'description': quoted[0] if len(quoted) > 0 else parts[2],
        'units': quoted[2] if len(quoted) > 2 else '',
        'source_file': file,
        'source_line': line,
    }
    return entry


def _parse_package(parts: List[str], file: str, line: int) -> Dict[str, Any]:
    """Parse a package entry."""
    # package <pkg_name> <namelist_var>==<value> - <state_list>
    if len(parts) < 3:
        return None
    
    pkg_name = parts[1]
    cond = parts[2]
    
    if '==' not in cond:
        return None
    
    var, val = cond.split('==', 1)
    
    # State vars come after the '-' separator
    state_vars = []
    found_dash = False
    for p in parts[3:]:
        if p == '-':
            found_dash = True
            continue
        if found_dash and p != '-':
            state_vars.append(p.lower())
    
    return {
        'package_name': pkg_name.lower(),
        'namelist_var': var.lower(),
        'value': val,
        'state_vars': state_vars,
        'source_file': file,
        'source_line': line,
    }


def _parse_state(parts: List[str], raw_line: str, file: str, line: int) -> Dict[str, Any]:
    """Parse a state entry."""
    # state <type> <name> <dims> <group> <num_time_levels> <stagger> <io_flags> "VAR_NAME" "DESCRIPTION" "UNITS"
    if len(parts) < 3:
        return None
    
    quoted = RE_QUOTED.findall(raw_line)
    
    entry = {
        'type': parts[1],
        'name': parts[2].lower(),
        'dims': parts[3] if len(parts) > 3 else '',
        'group': parts[4] if len(parts) > 4 else '',
        'num_time_levels': parts[5] if len(parts) > 5 else '',
        'stagger': parts[6] if len(parts) > 6 else '',
        'short_name': quoted[0] if len(quoted) > 0 else parts[2],
        'description': quoted[1] if len(quoted) > 1 else '',
        'units': quoted[2] if len(quoted) > 2 else '',
        'source_file': file,
        'source_line': line,
    }
    return entry


def _parse_dimspec(parts: List[str], file: str, line: int) -> Dict[str, Any]:
    """Parse a dimspec entry."""
    if len(parts) < 3:
        return None
    return {
        'name': parts[1],
        'order': parts[2],
        'source_file': file,
        'source_line': line,
    }
