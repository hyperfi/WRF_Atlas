"""Bounded MPI/OpenMP evidence index; never infers rank ownership from absent MPI."""

import hashlib
import json
import re
from pathlib import Path

from .fortran_parser import preprocess_lines, _mask_string_literals, _call_arguments
from .registry_parser import parse_registry


MPI_KINDS = {
    'mpi_barrier': 'mpi_barrier', 'mpi_wait': 'mpi_wait',
    'mpi_waitall': 'mpi_wait', 'mpi_waitany': 'mpi_wait',
    'mpi_waitsome': 'mpi_wait', 'mpi_test': 'mpi_test',
    'mpi_testall': 'mpi_test', 'mpi_isend': 'mpi_post',
    'mpi_irecv': 'mpi_post', 'mpi_send': 'mpi_transfer',
    'mpi_recv': 'mpi_transfer', 'mpi_sendrecv': 'mpi_transfer',
    'mpi_allreduce': 'mpi_collective', 'mpi_reduce': 'mpi_collective',
    'mpi_bcast': 'mpi_collective', 'mpi_gather': 'mpi_collective',
    'mpi_gatherv': 'mpi_collective', 'mpi_scatter': 'mpi_collective',
    'mpi_alltoall': 'mpi_collective', 'mpi_allgather': 'mpi_collective',
}
OMP_CONSTRUCTS = ('parallel do', 'parallel sections', 'parallel', 'do',
                  'sections', 'single', 'master', 'critical', 'workshare')
MPI_DOC = 'https://docs.open-mpi.org/en/main/man-openmpi/man3/'
OMP_DOC = 'https://www.openmp.org/spec-html/5.2/openmpse3.html'


def evidence(path, start, end=None):
    return {'path': path, 'startLine': start, 'endLine': end or start}


class Guards:
    """Retain mutually exclusive CPP alternatives rather than evaluating a build."""

    def __init__(self):
        self.stack = []

    def update(self, statement):
        match = re.match(r'#\s*(ifdef|ifndef|if|elif|else|endif)\b\s*(.*)', statement, re.I)
        if not match:
            return False
        command, value = match.groups()
        command = command.lower()
        if command in ('if', 'ifdef', 'ifndef'):
            expression = value.strip()
            if command != 'if':
                expression = ('!' if command == 'ifndef' else '') + f'defined({expression})'
            self.stack.append({'seen': [expression], 'current': expression})
        elif command == 'endif' and self.stack:
            self.stack.pop()
        elif command in ('elif', 'else') and self.stack:
            frame = self.stack[-1]
            excluded = ' || '.join(f'({item})' for item in frame['seen'])
            frame['current'] = f'!({excluded})'
            if command == 'elif':
                frame['current'] += f' && ({value})'
                frame['seen'].append(value)
        return True

    def values(self):
        return [frame['current'] for frame in self.stack]


def _event(path, scope, start, end, operation, kind, guards, conditions, thread='', **extra):
    return {
        'id': f'{path}:{start}:{operation}', 'scopeId': f'{path}::{scope}',
        'scope': scope, 'operation': operation, 'kind': kind,
        'evidence': [evidence(path, start, end)], 'guards': list(guards),
        'conditions': list(conditions), 'threadContext': thread,
        **extra,
    }


def scan_fortran(text, path):
    events, diagnostics = [], []
    # Preserve directive sentinels before the ordinary Fortran normalizer drops comments.
    prepared = []
    continuing_omp = False
    for line in text.splitlines(keepends=True):
        directive = re.match(r'^\s*(?:!|[cC*])\$[oO][mM][pP]\s*(.*)', line)
        if directive:
            body = directive.group(1).lstrip('&').strip()
            prepared.append((' ' if continuing_omp else ' @OMP ') + body + '\n')
            continuing_omp = body.endswith('&')
        else:
            prepared.append(line)
    # WRF's uppercase .F sources use free-form statements, including column-one CALL.
    normalization_path = path + '.f90' if path.endswith('.F') else path
    statements = preprocess_lines(prepared, normalization_path)
    guards, scopes, conditions, omp = Guards(), [], [], []
    for item in statements:
        raw = item.text
        masked = _mask_string_literals(raw)
        if guards.update(raw):
            continue
        definition = re.match(r'^\s*(?:recursive\s+)?(?:[\w()=*]+\s+)*?(subroutine|function|program)\s+(\w+)', masked, re.I)
        if definition and not re.match(r'^\s*end\b', masked, re.I):
            scopes.append(definition.group(2).lower())
            conditions.clear()
        scope = scopes[-1] if scopes else '<file>'
        if re.match(r'^\s*end\s*(subroutine|function|program)\b', masked, re.I):
            if omp:
                diagnostics.append({'path': path, 'line': item.start_line, 'message': 'Unclosed OpenMP construct; extent unresolved.'})
                omp.clear()
            if scopes:
                scopes.pop()
            conditions.clear()
            continue
        if re.match(r'^\s*end\s*if\b|^\s*endif\b', masked, re.I):
            if conditions:
                conditions.pop()
        elif re.match(r'^\s*else\b|^\s*elseif\b|^\s*else\s+if\b', masked, re.I):
            if conditions:
                conditions[-1] = 'alternative branch (predicate unresolved)'
        elif re.match(r'^\s*if\s*\(', masked, re.I) and re.search(r'\bthen\s*$', masked, re.I):
            conditions.append(raw.strip())
        if re.match(r'^\s*@OMP\b', raw, re.I):
            directive = re.sub(r'^\s*@OMP\s*', '', raw, flags=re.I).strip()
            lower = directive.lower()
            if lower.startswith('end '):
                construct = next((name for name in OMP_CONSTRUCTS if lower[4:].startswith(name)), None)
                if construct and omp and omp[-1]['construct'] == construct:
                    region = omp.pop()
                    joins = construct.startswith('parallel') or (construct in ('do', 'sections', 'single', 'workshare') and 'nowait' not in lower)
                    events.append(_event(path, scope, item.start_line, item.end_line,
                                         'END ' + construct.upper(), 'omp_join' if joins else 'omp_end',
                                         guards.values(), conditions, construct,
                                         regionId=region['id'], directive=directive, semantics=OMP_DOC))
                    region['endEvidence'] = evidence(path, item.start_line, item.end_line)
                else:
                    diagnostics.append({'path': path, 'line': item.start_line, 'message': 'Unmatched OpenMP end; join unresolved.'})
                continue
            construct = next((name for name in OMP_CONSTRUCTS if re.match(r'^' + name + r'\b', lower)), None)
            if construct:
                event = _event(path, scope, item.start_line, item.end_line,
                               construct.upper(), 'omp_region', guards.values(), conditions,
                               omp[-1]['construct'] if omp else '', directive=directive,
                               construct=construct, semantics=OMP_DOC)
                events.append(event)
                omp.append(event)
            elif lower.startswith('barrier'):
                events.append(_event(path, scope, item.start_line, item.end_line, 'BARRIER', 'omp_join',
                                     guards.values(), conditions, omp[-1]['construct'] if omp else '',
                                     directive=directive, semantics=OMP_DOC))
            elif not lower.startswith(('private', 'shared', 'firstprivate', 'reduction', 'schedule', 'default', 'atomic', 'flush', 'threadprivate')):
                diagnostics.append({'path': path, 'line': item.start_line, 'message': f'OpenMP directive not modeled: {directive}'})
            continue
        thread = omp[-1]['construct'] if omp else ''
        include = re.match(r'^\s*#?\s*include\s+["\']([^"\']+)', raw, re.I)
        if include and re.match(r'(HALO_|PERIOD_|SWAP_|CYCLE_)', Path(include.group(1)).name, re.I):
            events.append(_event(path, scope, item.start_line, item.end_line, include.group(1),
                                 'exchange', guards.values(), conditions, thread))
        call = re.search(r'\bcall\s+(\w+)', masked, re.I)
        if call:
            name = call.group(1)
            kind = MPI_KINDS.get(name.lower(), 'mpi_other' if name.lower().startswith('mpi_') else 'call')
            # Keep ordinary calls for the ARW walkthrough, not every call in the repository.
            if kind != 'call' or path.startswith('dyn_em/'):
                inline = [raw[:call.start()].strip()] if raw[:call.start()].strip() else []
                events.append(_event(path, scope, item.start_line, item.end_line, name, kind,
                                     guards.values(), conditions + inline, thread,
                                     arguments=_call_arguments(raw, call.end()),
                                     **({'semantics': MPI_DOC + 'MPI_' + name[4:].capitalize() + '.3.html'} if kind.startswith('mpi_') else {})))
        monitor = re.search(r'\bif\s*\(\s*wrf_dm_on_monitor\s*\(\s*\)\s*\)', masked, re.I)
        if monitor:
            events.append(_event(path, scope, item.start_line, item.end_line, 'wrf_dm_on_monitor()',
                                 'monitor', guards.values(), conditions, thread))
    return events, diagnostics


def _c_mask(text):
    """Lexically remove C comments/strings while preserving offsets and lines."""
    token = re.compile(r'/\*[\s\S]*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
    return token.sub(lambda match: ''.join('\n' if char == '\n' else ' ' for char in match.group()), text)


def scan_c(text, path):
    masked = _c_mask(text)
    lines = masked.splitlines()
    guards = Guards()
    guard_lines = {}
    for number, line in enumerate(lines, 1):
        guards.update(line)
        guard_lines[number] = guards.values()
    # Balanced token pairs avoid matching calls inside comments or multiline signatures.
    tokens = list(re.finditer(r'\w+|[^\s]', masked))
    pairs, opened = {}, []
    for index, token in enumerate(tokens):
        if token.group() in ('(', '{', '['):
            opened.append(index)
        elif token.group() in (')', '}', ']') and opened:
            opening = opened.pop()
            if tokens[opening].group() == {')': '(', '}': '{', ']': '['}[token.group()]:
                pairs[opening] = index
                pairs[index] = opening
    events, contexts = [], []
    scope = '<file>'
    for index, token in enumerate(tokens):
        value = token.group()
        if value == '{':
            context = {'scope': scope, 'condition': ''}
            previous = index - 1
            if previous >= 0 and tokens[previous].group() == ')' and previous in pairs:
                paren = pairs[previous]
                name = tokens[paren - 1].group() if paren else ''
                if name in ('if', 'for', 'while', 'switch'):
                    context['condition'] = masked[tokens[paren - 1].start():tokens[previous].end()].strip()
                elif re.match(r'^\w+$', name):
                    scope = name.lower()
            contexts.append(context)
        elif value == '}' and contexts:
            scope = contexts.pop()['scope']
        if not value.startswith('MPI_') or index + 1 >= len(tokens) or tokens[index + 1].group() != '(':
            continue
        opening = index + 1
        if opening not in pairs:
            continue
        close = pairs[opening]
        if close + 1 < len(tokens) and tokens[close + 1].group() == '{':
            continue
        start = masked.count('\n', 0, token.start()) + 1
        end = masked.count('\n', 0, tokens[close].end()) + 1
        statement = masked[token.start():tokens[close].end()]
        conditions = [context['condition'] for context in contexts if context['condition']]
        # A brace-free if on the same line still guards the call.
        prefix = masked[masked.rfind('\n', 0, token.start()) + 1:token.start()]
        if re.search(r'\bif\s*\(', prefix) and '{' not in prefix:
            conditions.append(prefix.strip())
        events.append(_event(path, scope, start, end, value,
                             MPI_KINDS.get(value.lower(), 'mpi_other'), guard_lines.get(start, []),
                             conditions, arguments=_call_arguments(statement, len(value)),
                             semantics=MPI_DOC + value + '.3.html'))
    return events, []


def registry_communications(root):
    return parse_registry(str(root))['communications']


def analyze_parallel(root, metadata=None):
    root = Path(root)
    events, diagnostics = [], []
    digest = hashlib.sha256()
    directories = ('dyn_em', 'frame', 'share', 'main', 'phys', 'external/RSL_LITE')
    for directory in directories:
        for path in sorted((root / directory).rglob('*')):
            if not path.is_file() or path.suffix.lower() not in ('.f', '.f90', '.c'):
                continue
            relative = path.relative_to(root).as_posix()
            text = path.read_text(encoding='utf-8', errors='replace')
            digest.update(relative.encode() + b'\0' + text.encode())
            parsed, issues = scan_c(text, relative) if path.suffix == '.c' else scan_fortran(text, relative)
            events.extend(parsed)
            diagnostics.extend(issues)
    communications = registry_communications(root)
    digest.update(json.dumps(communications, sort_keys=True).encode())
    declarations = {item['id']: item for item in communications}
    for event in events:
        if event['kind'] == 'exchange':
            name = Path(event['operation']).stem.upper()
            if name in declarations:
                event['communicationId'] = name
            else:
                diagnostics.append({'path': event['evidence'][0]['path'], 'line': event['evidence'][0]['startLine'],
                                    'message': f'No Registry declaration resolved for {name}.'})
    scopes = {}
    for event in events:
        scopes.setdefault(event['scopeId'], {'id': event['scopeId'], 'name': event['scope'],
                                            'path': event['evidence'][0]['path']})
    registry = parse_registry(str(root))
    options = [item for item in registry['rconfig'] if item['name'] in ('nproc_x', 'nproc_y', 'numtiles', 'tile_sz_x', 'tile_sz_y', 'nio_tasks_per_group', 'nio_groups')]
    generator = root / 'external/RSL_LITE/gen_comms.c'
    generator_evidence = []
    if generator.exists():
        for number, line in enumerate(generator.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
            if 'fprintf' in line and ('CALL RSL_LITE_EXCH_Y' in line or 'CALL RSL_LITE_EXCH_X' in line):
                anchor = evidence('external/RSL_LITE/gen_comms.c', number)
                anchor['description'] = re.search(r'CALL (RSL_LITE_EXCH_[XY])', line).group(1)
                generator_evidence.append(anchor)
    events.sort(key=lambda item: (item['evidence'][0]['path'], item['evidence'][0]['startLine'], item['id']))
    return {'schemaVersion': 1, 'metadata': {**(metadata or {}), 'parallel_index_version': 1,
                                            'parallel_source_digest': digest.hexdigest()},
            'scopes': sorted(scopes.values(), key=lambda item: (item['name'], item['path'])),
            'events': events, 'communications': communications, 'configuration': options,
            'generatorEvidence': generator_evidence, 'diagnostics': diagnostics,
            'limitations': [
                'Source order is not a runtime trace; loops, branches, and call reachability are not executed.',
                'Build modes resolve only DM_PARALLEL, STUBMPI, and _OPENMP assumptions; other macros remain conditional.',
                'Absent MPI calls do not prove serial or monitor-only work. Thread context is lexical, not interprocedural.',
                'Registry-to-include matching is exact by name; generated exchange implementation joins remain inferred.',
                'Rank numbering, partition sizes, thread assignments, message durations, and waiting times are illustrative.',
                'MPI thread-support level, I/O quilting ranks, and complete communicator membership are not modeled.',
            ]}


def write_parallel_index(root, output_path, metadata):
    target = Path(output_path).with_suffix('.parallel.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(analyze_parallel(root, metadata), separators=(',', ':')), encoding='utf-8')
    return target
