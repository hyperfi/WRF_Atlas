import type { SourceEvidence } from '../types/graph'

export type BuildMode = 'serial' | 'dmpar' | 'smpar' | 'hybrid'
export type Availability = 'active' | 'inactive' | 'conditional'
export interface ParallelEvent {
  id: string; scopeId: string; scope: string; operation: string; kind: string
  evidence: SourceEvidence[]; guards: string[]; conditions: string[]; threadContext: string
  arguments?: string[]; directive?: string; construct?: string; regionId?: string
  endEvidence?: SourceEvidence; semantics?: string; communicationId?: string
}
export interface Communication {
  id: string; name: string; kind: string
  groups: Array<{ pattern: string; fields: string[] }>; evidence: SourceEvidence[]
}
export interface ParallelIndex {
  schemaVersion: number
  metadata: { commit: string; source_id?: string; indexed_at: string; dirty?: boolean | null; parallel_indexed_at?: string }
  scopes: Array<{ id: string; name: string; path: string }>
  events: ParallelEvent[]; communications: Communication[]; generatorEvidence: SourceEvidence[]
  diagnostics: Array<{ path: string; line: number; message: string }>; limitations: string[]
  configuration: Array<{ name: string; default_value?: string; source_file: string; source_line: number }>
}
export const BUILD_MODES: Array<{ id: BuildMode; label: string; mpi: boolean; omp: boolean }> = [
  { id: 'serial', label: 'Serial', mpi: false, omp: false },
  { id: 'dmpar', label: 'dmpar · MPI', mpi: true, omp: false },
  { id: 'smpar', label: 'smpar · OpenMP', mpi: false, omp: true },
  { id: 'hybrid', label: 'dm+sm · Hybrid', mpi: true, omp: true },
]
export const modeSettings = (mode: BuildMode) => BUILD_MODES.find(item => item.id === mode) || BUILD_MODES[0]!
type Truth = boolean | null
const and = (a: Truth, b: Truth): Truth => a === false || b === false ? false : a === null || b === null ? null : true
const or = (a: Truth, b: Truth): Truth => a === true || b === true ? true : a === null || b === null ? null : false

export function evaluateBuildGuard(expression: string, mode: BuildMode): Truth {
  const settings = modeSettings(mode)
  const known: Record<string, boolean> = { DM_PARALLEL: settings.mpi, STUBMPI: !settings.mpi, _OPENMP: settings.omp }
  const tokens = expression.match(/defined|[A-Za-z_]\w*|\d+|&&|\|\||[!()]/g) || []
  // Do not silently drop arithmetic, comparisons, or macro-expansion syntax.
  if (tokens.join('') !== expression.replace(/\s/g, '')) return null
  let cursor = 0
  const atom = (): Truth => {
    const token = tokens[cursor++]
    if (token === '!') { const value = atom(); return value === null ? null : !value }
    if (token === '(') { const value = disjunction(); if (tokens[cursor++] !== ')') throw new Error('Unbalanced'); return value }
    if (token === 'defined') {
      const parenthesis = tokens[cursor] === '('
      if (parenthesis) cursor++
      const name = tokens[cursor++] || ''
      if (parenthesis && tokens[cursor++] !== ')') throw new Error('Unbalanced')
      return name in known ? known[name]! : null
    }
    if (token === '0' || token === '1') return token === '1'
    return null
  }
  const conjunction = (): Truth => { let value = atom(); while (tokens[cursor] === '&&') { cursor++; value = and(value, atom()) }; return value }
  const disjunction = (): Truth => { let value = conjunction(); while (tokens[cursor] === '||') { cursor++; value = or(value, conjunction()) }; return value }
  try { const value = disjunction(); return cursor === tokens.length ? value : null } catch { return null }
}

export function eventAvailability(event: ParallelEvent, mode: BuildMode): Availability {
  const settings = modeSettings(mode)
  if (event.kind.startsWith('mpi_') && !settings.mpi) return 'inactive'
  if (event.kind.startsWith('omp_') && !settings.omp) return 'inactive'
  const values = event.guards.map(guard => evaluateBuildGuard(guard, mode))
  if (values.includes(false)) return 'inactive'
  return values.includes(null) || event.conditions.length > 0 ? 'conditional' : 'active'
}

export function illustrativeDimensions(mode: BuildMode, x: number, y: number, threads: number) {
  const settings = modeSettings(mode)
  const bounded = (value: number, max: number) => Number.isFinite(value) ? Math.min(max, Math.max(1, Math.floor(value))) : 1
  return { x: settings.mpi ? bounded(x, 3) : 1, y: settings.mpi ? bounded(y, 3) : 1, threads: settings.omp ? bounded(threads, 4) : 1 }
}

export function rankNeighbors(rank: number, x: number, y: number, axis: 'x' | 'y' | 'both' = 'both') {
  if (rank < 0 || rank >= x * y) return []
  const row = Math.floor(rank / x), column = rank % x
  const result: number[] = []
  if (axis !== 'y') { if (column > 0) result.push(rank - 1); if (column + 1 < x) result.push(rank + 1) }
  if (axis !== 'x') { if (row > 0) result.push(rank - x); if (row + 1 < y) result.push(rank + x) }
  return result
}

export function communicationTopology(event: ParallelEvent | undefined, scopeEvents: ParallelEvent[]) {
  if (!event) return null
  if (event.kind === 'mpi_barrier' || event.kind === 'mpi_collective') return 'communicator' as const
  // Do not assign neighbor topology to arbitrary requests or MPI setup calls.
  if (!['exchange', 'mpi_post', 'mpi_wait', 'mpi_transfer'].includes(event.kind)) return null
  if (event.kind === 'exchange') return event.operation.toUpperCase().startsWith('HALO_') ? 'both' as const : null
  const shifts = scopeEvents.filter(item => item.operation.toLowerCase() === 'mpi_cart_shift')
  if (shifts.length !== 1) return null
  return shifts[0]?.arguments?.[1] === '0' ? 'y' as const : shifts[0]?.arguments?.[1] === '1' ? 'x' as const : null
}

export function communicationNeighbors(event: ParallelEvent | undefined, scopeEvents: ParallelEvent[], mode: BuildMode, rank: number, x: number, y: number) {
  if (!event || !modeSettings(mode).mpi || eventAvailability(event, mode) === 'inactive') return []
  const topology = communicationTopology(event, scopeEvents)
  return !topology || topology === 'communicator' ? [] : rankNeighbors(rank, x, y, topology)
}

export function eventMeaning(event: ParallelEvent, mode: BuildMode) {
  const availability = eventAvailability(event, mode)
  const settings = modeSettings(mode)
  if (availability === 'inactive') {
    if (event.kind.startsWith('omp_') && !settings.omp) return { label: 'OpenMP directive ignored', detail: 'Without OpenMP, the Fortran body remains sequential within each participating rank; this thread-team synchronization does not apply.' }
    return { label: 'Excluded in this mode', detail: 'The selected build assumptions exclude this communication mechanism or preprocessor branch. No wait is implied here.' }
  }
  if (event.kind === 'omp_region') {
    const construct = event.construct
    if (construct === 'master') return { label: 'Primary-thread region', detail: 'Only the primary thread executes this region. MASTER has no implied entry or exit barrier; other threads do not wait merely because this directive exists.' }
    if (construct === 'single') return { label: 'One-thread region', detail: 'One thread in the team executes this region; the selected thread is not necessarily the primary thread. The end has an implied barrier unless NOWAIT is present.' }
    if (construct === 'critical') return { label: 'Serialized critical region', detail: 'Threads enter the same critical region one at a time. Mutual exclusion can delay entry, but the end is not a thread-team barrier.' }
  }
  const meanings: Record<string, { label: string; detail: string }> = {
    exchange: { label: 'Boundary exchange', detail: 'The source includes generated communication. Registry field membership is direct evidence; the generator-to-MPI link is inferred until generated code is available.' },
    mpi_post: { label: 'Post communication', detail: 'A nonblocking operation is posted. Posting does not prove communication/computation overlap or that the operation has completed.' },
    mpi_wait: { label: 'Request completion', detail: 'This rank may wait for the specified outstanding request(s). It is not a barrier across every rank; completed requests can return immediately.' },
    mpi_barrier: { label: 'Communicator barrier', detail: 'Participating ranks cannot complete this barrier until all members of this communicator have entered. It is not necessarily MPI_COMM_WORLD.' },
    mpi_collective: { label: 'Collective communication', detail: 'This operation involves the indicated communicator. Collective data dependencies are not interchangeable with an explicit barrier.' },
    mpi_transfer: { label: 'Blocking communication', detail: 'Completion obeys this MPI operation’s semantics; a blocking send does not necessarily wait for the receiver to finish its work.' },
    mpi_test: { label: 'Test completion', detail: 'Checks whether a request has completed. A test is not itself a blocking wait.' },
    mpi_other: { label: 'MPI service', detail: 'An MPI API call is present. Its rank participation and effects require inspection; no wait is inferred.' },
    monitor: { label: 'Monitor-rank guard', detail: 'The WRF monitor predicate guards this branch. Do not assume global rank zero or that other ranks wait here.' },
    omp_region: { label: 'OpenMP region', detail: 'This directive defines a thread region or worksharing construct within a rank. Clauses, nesting, runtime conditions, and the actual team size govern participation.' },
    omp_join: { label: 'Thread-team synchronization', detail: 'An explicit or standard-implied OpenMP barrier joins the relevant thread team within this rank, not MPI ranks. Source conditions still apply.' },
    omp_end: { label: 'Region ends without a join', detail: 'This end directive does not imply a team barrier here, for example a NOWAIT worksharing region, MASTER, or CRITICAL.' },
    call: { label: settings.omp && event.threadContext ? 'Call inside a thread region' : 'Call in the selected scope', detail: 'This call site is exact. Its participating ranks and transitive thread behavior are unresolved; absence of MPI is not evidence of globally serial work.' },
  }
  return meanings[event.kind] || { label: 'Unresolved', detail: 'Inspect the source to establish execution scope.' }
}

export function matchingParallelIndex(index: ParallelIndex, metadata: { commit: string; indexed_at: string; source_id?: string; dirty?: boolean | null }) {
  return index.schemaVersion === 1 && index.metadata.commit === metadata.commit &&
    index.metadata.indexed_at === metadata.indexed_at && index.metadata.source_id === metadata.source_id && index.metadata.dirty === metadata.dirty
}

export function sourceWindow(events: ParallelEvent[], selectedId: string, size = 10) {
  const index = Math.max(0, events.findIndex(event => event.id === selectedId))
  const start = Math.floor(index / size) * size
  return { start, events: events.slice(start, start + size) }
}

export function retainedSelection(previous: ParallelEvent[], next: ParallelEvent[], selectedId: string) {
  if (next.some(event => event.id === selectedId)) return selectedId
  const oldIndex = previous.findIndex(event => event.id === selectedId)
  const positions = new Map(previous.map((event, index) => [event.id, index]))
  return next.reduce<ParallelEvent | undefined>((nearest, event) => {
    const distance = Math.abs((positions.get(event.id) ?? Infinity) - oldIndex)
    const best = Math.abs((positions.get(nearest?.id || '') ?? Infinity) - oldIndex)
    return !nearest || distance < best ? event : nearest
  }, undefined)?.id || ''
}

export function enclosingThreadRegion(event: ParallelEvent, scopeEvents: ParallelEvent[], mode: BuildMode) {
  if (!modeSettings(mode).omp || eventAvailability(event, mode) === 'inactive') return undefined
  const anchor = event.evidence[0]
  if (!anchor) return undefined
  return scopeEvents.filter(region => region.kind === 'omp_region' && region.construct?.startsWith('parallel') &&
    region.scopeId === event.scopeId && region.evidence[0]?.path === anchor.path && region.endEvidence &&
    region.evidence[0].startLine <= anchor.startLine && region.endEvidence.startLine >= anchor.startLine &&
    eventAvailability(region, mode) !== 'inactive')
    .sort((a, b) => b.evidence[0]!.startLine - a.evidence[0]!.startLine)[0]
}

export interface RequestAssociation { post: ParallelEvent; wait: ParallelEvent; request: string }

// Lexical association only: neither object identity nor control-flow reachability is proven.
export function requestAssociations(events: ParallelEvent[], mode: BuildMode): RequestAssociation[] {
  if (!modeSettings(mode).mpi) return []
  const signature = (event: ParallelEvent) => JSON.stringify([event.guards, event.conditions].map(items => items.map(value => value.replace(/\s+/g, ' ').trim())))
  const request = (event: ParallelEvent, post: boolean) => {
    const args = event.arguments || []
    const isC = event.evidence[0]?.path.endsWith('.c')
    const value = args[post ? args.length - (isC ? 1 : 2) : 0]?.trim() || ''
    if (!/^&?[A-Za-z_]\w*$/.test(value)) return ''
    return isC ? value.replace(/^&/, '') : value.toLowerCase()
  }
  return events.filter(event => event.kind === 'mpi_wait' && event.operation.toLowerCase() === 'mpi_wait' && eventAvailability(event, mode) !== 'inactive')
    .flatMap(wait => {
      const name = request(wait, false)
      if (!name || wait.conditions.some(condition => condition.includes('unresolved'))) return []
      const posts = events.filter(post => post.kind === 'mpi_post' && ['mpi_isend', 'mpi_irecv'].includes(post.operation.toLowerCase()) &&
        eventAvailability(post, mode) !== 'inactive' && post.scopeId === wait.scopeId && post.evidence[0]?.path === wait.evidence[0]?.path &&
        post.evidence[0]!.startLine < wait.evidence[0]!.startLine && request(post, true) === name && signature(post) === signature(wait))
      return posts.length === 1 ? [{ post: posts[0]!, wait, request: name }] : []
    })
}
