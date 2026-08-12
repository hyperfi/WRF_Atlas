"""
Tolerant WRF-aware Fortran parser.

This parser processes Fortran source files used in the WRF model, extracting:
- PROGRAM, MODULE, SUBROUTINE, FUNCTION definitions
- USE, CALL, INCLUDE relationships
- SELECT CASE dispatch patterns (critical for physics driver tracing)
- config_flags%, model_config_rec%, nl_get_ references
- Preprocessor directives

Design: operates on logical lines (after continuation joining) with
original line number tracking. All matching is case-insensitive.
Designed to survive syntax it doesn't understand.
"""

import re
import os
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── Regex patterns (all case-insensitive) ───

# Comment detection
RE_COMMENT_FREE = re.compile(r'^\s*!')
RE_COMMENT_FIXED = re.compile(r'^[cC\*]')
RE_PREPROC = re.compile(r'^\s*#')

# Definitions
RE_PROGRAM = re.compile(r'^\s*PROGRAM\s+(\w+)', re.I)
RE_MODULE = re.compile(r'^\s*MODULE\s+(\w+)', re.I)
RE_MODULE_PROC = re.compile(r'^\s*MODULE\s+PROCEDURE', re.I)
RE_SUBROUTINE = re.compile(
    r'^\s*(?:RECURSIVE\s+)?SUBROUTINE\s+(\w+)\s*(?:\(([^)]*)\))?', re.I)
RE_FUNCTION = re.compile(
    r'^\s*(?:\w+\s+)*(?:RECURSIVE\s+)?FUNCTION\s+(\w+)\s*\(', re.I)
RE_END = re.compile(
    r'^\s*END\s*(?:PROGRAM|MODULE|SUBROUTINE|FUNCTION|SELECT|DO|IF)\b', re.I)
RE_END_SELECT = re.compile(r'^\s*END\s+SELECT\b', re.I)
RE_END_SCOPE = re.compile(
    r'^\s*END\s+(PROGRAM|MODULE|SUBROUTINE|FUNCTION)\b\s*(\w+)?', re.I)

# Relationships
RE_USE = re.compile(r'^\s*USE\s+(\w+)', re.I)
RE_CALL = re.compile(r'\bCALL\s+(\w+)', re.I)
RE_INCLUDE_F = re.compile(r"^\s*INCLUDE\s+['\"]([^'\"]+)['\"]", re.I)
RE_INCLUDE_C = re.compile(r'^\s*#\s*include\s+[<"\']([^>"\']+)[>"\']', re.I)

# SELECT CASE / CASE / END SELECT
RE_SELECT_CASE = re.compile(
    r'(?:(\w+)\s*:\s*)?SELECT\s+CASE\s*\(\s*(.+?)\s*\)', re.I)
RE_CASE = re.compile(
    r'^\s*CASE\s*\(\s*(.+?)\s*\)', re.I)
RE_CASE_DEFAULT = re.compile(r'^\s*CASE\s+DEFAULT\b', re.I)

# Config references
RE_CONFIG_FLAGS = re.compile(r'config_flags\s*%\s*(\w+)', re.I)
RE_MODEL_CONFIG = re.compile(r'model_config_rec\s*%\s*(\w+)', re.I)
RE_NL_GET = re.compile(r'nl_get_(\w+)', re.I)

# Named label on SELECT CASE
RE_NAMED_END_SELECT = re.compile(r'^\s*END\s+SELECT\s+(\w+)', re.I)


@dataclass
class LogicalLine:
    """A logical Fortran line after continuation joining, with original line mapping."""
    text: str
    start_line: int  # 1-indexed first physical line
    end_line: int     # 1-indexed last physical line


@dataclass
class SelectCaseBlock:
    """Tracks a SELECT CASE block during parsing."""
    expression: str           # The expression being switched on
    config_var: Optional[str] # Extracted config variable name if recognized
    label: Optional[str]      # Named label (e.g., sfc_select:)
    start_line: int
    scope: Optional[str]      # Containing subroutine/function
    current_case_value: Optional[str] = None
    current_case_line: int = 0
    cases: List[Dict] = field(default_factory=list)


def preprocess_lines(raw_lines: List[str], filename: str) -> List[LogicalLine]:
    """
    Join continuation lines into logical Fortran statements.
    Preserves original line number mapping.
    Handles both free-form (&) and fixed-form continuations.
    """
    logical_lines = []
    current_text = ""
    start_line = 0
    in_continuation = False
    
    is_fixed = filename.lower().endswith(('.f', '.for', '.fpp'))
    
    for i, raw_line in enumerate(raw_lines):
        line_num = i + 1
        line = raw_line.rstrip('\r\n')
        
        # Skip blank lines (but finalize any pending continuation first)
        stripped = line.strip()
        
        # Handle preprocessor directives as single logical lines
        if RE_PREPROC.match(line):
            if current_text and not in_continuation:
                logical_lines.append(LogicalLine(current_text.strip(), start_line, line_num - 1))
                current_text = ""
            logical_lines.append(LogicalLine(stripped, line_num, line_num))
            continue
        
        # Skip comment-only lines
        if is_fixed and RE_COMMENT_FIXED.match(line):
            continue
        if RE_COMMENT_FREE.match(stripped):
            continue
        if not stripped:
            continue
            
        # Strip inline comments (simplistic - doesn't handle ! in strings)
        comment_pos = _find_inline_comment(stripped)
        if comment_pos >= 0:
            stripped = stripped[:comment_pos].rstrip()
        if not stripped:
            continue
        
        # Handle continuation lines
        if in_continuation:
            # If this line starts with &, it's a continuation indicator
            if stripped.startswith('&'):
                stripped = stripped[1:].strip()
            current_text += " " + stripped
            
            # Check if this line also continues
            if stripped.endswith('&'):
                current_text = current_text[:-1].rstrip()  # Remove trailing &
                in_continuation = True
            else:
                in_continuation = False
                logical_lines.append(LogicalLine(current_text.strip(), start_line, line_num))
                current_text = ""
        else:
            # New statement
            if stripped.endswith('&'):
                start_line = line_num
                current_text = stripped[:-1].rstrip()
                in_continuation = True
            else:
                logical_lines.append(LogicalLine(stripped, line_num, line_num))
    
    # Flush remaining
    if current_text:
        logical_lines.append(LogicalLine(current_text.strip(), start_line, len(raw_lines)))
    
    return logical_lines


def _find_inline_comment(line: str) -> int:
    """Find position of inline comment (!) not inside a string literal."""
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == '!' and not in_single and not in_double:
            return i
    return -1


def _mask_string_literals(line: str) -> str:
    """Replace string contents with spaces so keywords inside messages are ignored."""
    chars = list(line)
    quote = None
    i = 0
    while i < len(chars):
        ch = chars[i]
        if quote is None and ch in ("'", '"'):
            quote = ch
            chars[i] = ' '
        elif quote is not None:
            chars[i] = ' '
            if ch == quote:
                # Fortran escapes a quote by doubling it inside the literal.
                if i + 1 < len(chars) and chars[i + 1] == quote:
                    chars[i + 1] = ' '
                    i += 1
                else:
                    quote = None
        i += 1
    return ''.join(chars)


def _extract_config_var(expression: str) -> Optional[str]:
    """
    Extract the config variable name from a SELECT CASE expression.
    Handles: config_flags%var, just var (if it's a known physics selector pattern).
    """
    expr_lower = expression.lower().strip()
    
    # Direct config_flags% reference
    m = RE_CONFIG_FLAGS.search(expression)
    if m:
        return m.group(1).lower()
    
    # model_config_rec% reference  
    m = RE_MODEL_CONFIG.search(expression)
    if m:
        return m.group(1).lower()
    
    # Common WRF driver pattern: the SELECT CASE uses a local variable 
    # that was extracted from config_flags. Known physics selectors:
    KNOWN_SELECTORS = {
        'sf_surface_physics', 'sf_sfclay_physics', 'mp_physics',
        'ra_lw_physics', 'ra_sw_physics', 'bl_pbl_physics', 'cu_physics',
        'shcu_physics', 'lw_physics', 'sw_physics', 'sf_urban_physics',
        'sf_lake_physics', 'sf_ocean_physics', 'gwd_opt',
        'lightning_option', 'tracer_opt', 'scalar_pblmix',
        'dfi_opt', 'ideal_case', 'grid_fdda', 'grid_sfdda',
        'obs_nudge_opt', 'topo_wind', 'seaice_albedo_opt',
        'fractional_seaice', 'progn', 'naer', 'aer_opt',
    }
    
    # Remove any whitespace from expression for matching
    clean = expr_lower.replace(' ', '')
    if clean in KNOWN_SELECTORS:
        return clean
    
    return None


def parse_fortran_file(filepath: str) -> Dict[str, Any]:
    """
    Parse a single Fortran file and extract structural information.
    
    Returns a dict with keys:
      programs, modules, subroutines, functions,
      use_stmts, calls, includes,
      select_cases, config_refs
    """
    result = {
        'filepath': filepath,
        'programs': [],
        'modules': [],
        'subroutines': [],
        'functions': [],
        'use_stmts': [],
        'calls': [],
        'includes': [],
        'select_cases': [],
        'config_refs': []
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            raw_lines = f.readlines()
    except Exception as e:
        logger.error(f"Failed to read {filepath}: {e}")
        return result
    
    logical_lines = preprocess_lines(raw_lines, filepath)
    
    # Scope tracking
    scope_stack = []  # Stack of (type, name) for nested scopes
    current_scope = None
    
    # SELECT CASE tracking
    select_stack: List[SelectCaseBlock] = []
    
    for ll in logical_lines:
        text = ll.text
        start = ll.start_line
        end = ll.end_line
        
        try:
            # ─── END statements (must check first) ───
            
            end_sel = RE_END_SELECT.match(text)
            if end_sel:
                if select_stack:
                    finished = select_stack.pop()
                    # Finalize the last CASE block
                    if finished.current_case_value is not None:
                        # already recorded
                        pass
                    result['select_cases'].append({
                        'expression': finished.expression,
                        'config_var': finished.config_var,
                        'label': finished.label,
                        'scope': finished.scope,
                        'start_line': finished.start_line,
                        'end_line': start,
                        'cases': finished.cases
                    })
                continue
            
            end_scope = RE_END_SCOPE.match(text)
            if end_scope:
                if scope_stack:
                    scope_stack.pop()
                current_scope = scope_stack[-1][1] if scope_stack else None
                continue
            
            # ─── PROGRAM ───
            if RE_MODULE_PROC.match(text):
                continue  # Skip MODULE PROCEDURE
                
            m = RE_PROGRAM.match(text)
            if m:
                name = m.group(1).lower()
                scope_stack.append(('program', name))
                current_scope = name
                result['programs'].append({
                    'name': name,
                    'line': start,
                    'end_line': end
                })
                continue
            
            # ─── MODULE ───
            m = RE_MODULE.match(text)
            if m:
                name = m.group(1).lower()
                if name.lower() == 'procedure':
                    continue
                scope_stack.append(('module', name))
                current_scope = name
                result['modules'].append({
                    'name': name,
                    'line': start,
                    'end_line': end
                })
                continue
            
            # ─── SUBROUTINE ───
            m = RE_SUBROUTINE.match(text)
            if m:
                name = m.group(1).lower()
                args_str = m.group(2) or ''
                args = [a.strip().lower() for a in args_str.split(',') if a.strip()]
                scope_stack.append(('subroutine', name))
                current_scope = name
                result['subroutines'].append({
                    'name': name,
                    'line': start,
                    'end_line': end,
                    'args': args
                })
                continue
            
            # ─── FUNCTION ───
            m = RE_FUNCTION.match(text)
            if m:
                name = m.group(1).lower()
                scope_stack.append(('function', name))
                current_scope = name
                result['functions'].append({
                    'name': name,
                    'line': start,
                    'end_line': end
                })
                continue
            
            # ─── USE ───
            m = RE_USE.match(text)
            if m:
                result['use_stmts'].append({
                    'module': m.group(1).lower(),
                    'scope': current_scope,
                    'line': start
                })
                continue
            
            # ─── INCLUDE / #include ───
            m = RE_INCLUDE_F.match(text) or RE_INCLUDE_C.match(text)
            if m:
                result['includes'].append({
                    'file': m.group(1),
                    'scope': current_scope,
                    'line': start
                })
            
            # ─── SELECT CASE ───
            m = RE_SELECT_CASE.search(text)
            if m:
                label = m.group(1)
                expr = m.group(2).strip()
                config_var = _extract_config_var(expr)
                
                block = SelectCaseBlock(
                    expression=expr,
                    config_var=config_var,
                    label=label,
                    start_line=start,
                    scope=current_scope
                )
                select_stack.append(block)
                continue
            
            # ─── CASE ───
            m = RE_CASE.match(text)
            if m and select_stack:
                val = m.group(1).strip()
                block = select_stack[-1]
                # Record previous case's calls
                block.current_case_value = val
                block.current_case_line = start
                block.cases.append({
                    'value': val,
                    'line': start,
                    'calls': []
                })
                continue
            
            m = RE_CASE_DEFAULT.match(text)
            if m and select_stack:
                block = select_stack[-1]
                block.current_case_value = 'DEFAULT'
                block.current_case_line = start
                block.cases.append({
                    'value': 'DEFAULT',
                    'line': start,
                    'calls': []
                })
                continue
            
            # ─── CALL (must come after CASE to be recorded within case blocks) ───
            structural_text = _mask_string_literals(text)
            for call_match in RE_CALL.finditer(structural_text):
                sub_name = call_match.group(1).lower()
                
                call_info = {
                    'subroutine': sub_name,
                    'caller': current_scope,
                    'caller_type': scope_stack[-1][0] if scope_stack else None,
                    'line': start,
                    'end_line': end,
                }
                
                # If inside a SELECT CASE, attach dispatch context
                if select_stack:
                    block = select_stack[-1]
                    if block.config_var and block.cases:
                        call_info['dispatch_var'] = block.config_var
                        call_info['dispatch_value'] = block.current_case_value
                        call_info['dispatch_expression'] = block.expression
                        # Also add to the current case's calls
                        block.cases[-1]['calls'].append({
                            'name': sub_name,
                            'line': start
                        })
                
                result['calls'].append(call_info)
            
            # ─── Config references ───
            for m in RE_CONFIG_FLAGS.finditer(structural_text):
                result['config_refs'].append({
                    'var': m.group(1).lower(),
                    'type': 'config_flags',
                    'scope': current_scope,
                    'line': start
                })
            for m in RE_MODEL_CONFIG.finditer(structural_text):
                result['config_refs'].append({
                    'var': m.group(1).lower(),
                    'type': 'model_config_rec',
                    'scope': current_scope,
                    'line': start
                })
            for m in RE_NL_GET.finditer(structural_text):
                result['config_refs'].append({
                    'var': m.group(1).lower(),
                    'type': 'nl_get',
                    'scope': current_scope,
                    'line': start
                })
                
        except Exception as e:
            logger.warning(f"Error parsing line {start} in {filepath}: {e}")
            continue
    
    # Flush any remaining SELECT CASE blocks (unclosed)
    for block in select_stack:
        result['select_cases'].append({
            'expression': block.expression,
            'config_var': block.config_var,
            'label': block.label,
            'scope': block.scope,
            'start_line': block.start_line,
            'end_line': -1,  # unclosed
            'cases': block.cases
        })
    
    return result
