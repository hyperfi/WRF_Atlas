import test from 'node:test'
import assert from 'node:assert/strict'
import { communicationTopology, enclosingThreadRegion, evaluateBuildGuard, eventAvailability, eventMeaning, illustrativeDimensions, matchingParallelIndex, rankNeighbors, requestAssociations, retainedSelection, sourceWindow, type ParallelEvent, type ParallelIndex } from '../src/lib/parallel.ts'
import { readFileSync } from 'node:fs'

const event = (changes: Partial<ParallelEvent> = {}): ParallelEvent => ({ id: 'test', scopeId: 'test::step', scope: 'step', operation: 'MPI_Wait', kind: 'mpi_wait', evidence: [{ path: 'test.F', startLine: 1 }], guards: [], conditions: [], threadContext: '', ...changes })

test('all build modes independently control MPI ranks and OpenMP teams', () => {
  assert.deepEqual(illustrativeDimensions('serial', 2, 3, 4), { x: 1, y: 1, threads: 1 })
  assert.deepEqual(illustrativeDimensions('dmpar', 2, 3, 4), { x: 2, y: 3, threads: 1 })
  assert.deepEqual(illustrativeDimensions('smpar', 2, 3, 4), { x: 1, y: 1, threads: 4 })
  assert.deepEqual(illustrativeDimensions('hybrid', 2, 3, 4), { x: 2, y: 3, threads: 4 })
  assert.deepEqual(illustrativeDimensions('hybrid', Infinity, -2, 80), { x: 1, y: 1, threads: 4 })
})

test('macro alternatives and unresolved macros do not create false active paths', () => {
  const guard = 'defined(DM_PARALLEL) && !defined(STUBMPI)'
  assert.equal(evaluateBuildGuard(guard, 'dmpar'), true)
  assert.equal(evaluateBuildGuard(guard, 'smpar'), false)
  assert.equal(evaluateBuildGuard('!((defined(DM_PARALLEL)))', 'serial'), true)
  assert.equal(evaluateBuildGuard('defined(WRF_CHEM)', 'hybrid'), null)
  assert.equal(evaluateBuildGuard('0 && defined(WRF_CHEM)', 'hybrid'), false)
  assert.equal(evaluateBuildGuard('1 || defined(WRF_CHEM)', 'hybrid'), true)
  assert.equal(evaluateBuildGuard('DM_PARALLEL == 1', 'hybrid'), null)
  assert.equal(evaluateBuildGuard('defined(_OPENMP)', 'smpar'), true)
  assert.equal(evaluateBuildGuard('defined(_OPENMP)', 'dmpar'), false)
})

test('MPI mechanisms disappear without MPI while OpenMP bodies are not deleted', () => {
  assert.equal(eventAvailability(event(), 'smpar'), 'inactive')
  assert.equal(eventAvailability(event({ conditions: ['if (peer != MPI_PROC_NULL)'] }), 'dmpar'), 'conditional')
  const omp = event({ kind: 'omp_join', operation: 'END PARALLEL DO' })
  assert.equal(eventAvailability(omp, 'hybrid'), 'active')
  assert.match(eventMeaning(omp, 'dmpar').detail, /body remains sequential/)
  assert.equal(eventAvailability(event({ kind: 'call', operation: 'work', threadContext: 'parallel do' }), 'dmpar'), 'active')
})

test('master, single and critical explain restricted participation rather than team-wide work', () => {
  assert.equal(eventMeaning(event({ kind: 'omp_region', construct: 'master' }), 'hybrid').label, 'Primary-thread region')
  assert.match(eventMeaning(event({ kind: 'omp_region', construct: 'single' }), 'smpar').detail, /not necessarily the primary/)
  assert.match(eventMeaning(event({ kind: 'omp_region', construct: 'critical' }), 'smpar').detail, /not a thread-team barrier/)
})

test('illustrative topology has no wraparound and never invents peers for arbitrary MPI calls', () => {
  assert.deepEqual(rankNeighbors(0, 2, 2), [1, 2])
  assert.deepEqual(rankNeighbors(1, 2, 2, 'x'), [0])
  assert.deepEqual(rankNeighbors(0, 2, 2, 'y'), [2])
  assert.deepEqual(rankNeighbors(9, 2, 2), [])
  const shift = event({ operation: 'MPI_Cart_shift', kind: 'mpi_other', arguments: ['comm', '0', '1'] })
  assert.equal(communicationTopology(shift, [shift]), null)
  assert.equal(communicationTopology(event(), []), null)
  assert.equal(communicationTopology(event(), [shift]), 'y')
  assert.equal(communicationTopology(event({ kind: 'mpi_barrier' }), []), 'communicator')
  assert.equal(communicationTopology(event({ kind: 'exchange', operation: 'PERIOD_TEST.inc' }), []), null)
})

test('parallel evidence cannot silently mix snapshots or graph generations', () => {
  const metadata = { commit: 'abc', indexed_at: '2026-10-06', source_id: 'official', dirty: false }
  const index = { schemaVersion: 1, metadata } as ParallelIndex
  assert.equal(matchingParallelIndex(index, metadata), true)
  assert.equal(matchingParallelIndex(index, { ...metadata, commit: 'def' }), false)
  assert.equal(matchingParallelIndex(index, { ...metadata, indexed_at: 'older' }), false)
  assert.equal(matchingParallelIndex(index, { ...metadata, source_id: 'local' }), false)
  assert.equal(matchingParallelIndex(index, { ...metadata, dirty: true }), false)
})

test('mode filtering preserves source identity, otherwise selects a nearby source stop', () => {
  const before = Array.from({ length: 6 }, (_, i) => event({ id: String(i) }))
  assert.equal(retainedSelection(before, before.filter(item => item.id !== '1'), '4'), '4')
  assert.equal(retainedSelection(before, before.filter(item => item.id !== '4'), '4'), '3')
  assert.equal(retainedSelection(before, [], '4'), '')
  assert.equal(retainedSelection([], before, ''), '0')
})

test('source pages stay stable while stepping and contain the selected stop', () => {
  const events = Array.from({ length: 23 }, (_, i) => event({ id: String(i) }))
  assert.equal(sourceWindow(events, '14').start, 10)
  assert.equal(sourceWindow(events, '18').start, 10)
  assert.equal(sourceWindow(events, '20').start, 20)
  assert.equal(sourceWindow(events, '22').events.length, 3)
})

test('thread forks require a proven lexical parallel extent, not a thread-context label alone', () => {
  const region = event({ id: 'region', kind: 'omp_region', construct: 'parallel do', evidence: [{ path: 'test.F', startLine: 10 }], endEvidence: { path: 'test.F', startLine: 30 } })
  const body = event({ kind: 'call', evidence: [{ path: 'test.F', startLine: 20 }], threadContext: 'parallel do' })
  assert.equal(enclosingThreadRegion(body, [region, body], 'hybrid')?.id, 'region')
  assert.equal(enclosingThreadRegion(body, [region, body], 'dmpar'), undefined)
  assert.equal(enclosingThreadRegion(body, [{ ...region, endEvidence: undefined }, body], 'hybrid'), undefined)
  assert.equal(enclosingThreadRegion({ ...body, evidence: [{ path: 'other.F', startLine: 20 }] }, [region], 'hybrid'), undefined)
  assert.equal(enclosingThreadRegion(body, [{ ...region, scopeId: 'other' }], 'hybrid'), undefined)
  assert.equal(enclosingThreadRegion(body, [{ ...region, construct: 'do' }], 'hybrid'), undefined)
})

test('request association refuses mismatched guards, duplicate posts and unsupported arrays', () => {
  const post = event({ id: 'post', operation: 'MPI_Irecv', kind: 'mpi_post', evidence: [{ path: 'test.c', startLine: 10 }], arguments: ['buf', 'count', 'type', 'peer', 'tag', 'comm', '&req'], conditions: ['if (peer > 0)'] })
  const wait = event({ id: 'wait', evidence: [{ path: 'test.c', startLine: 20 }], arguments: ['&req', '&status'], conditions: post.conditions })
  assert.equal(requestAssociations([post, wait], 'hybrid')[0]?.request, 'req')
  assert.equal(requestAssociations([post, wait], 'serial').length, 0)
  assert.equal(requestAssociations([post, { ...wait, conditions: [] }], 'hybrid').length, 0)
  assert.equal(requestAssociations([post, { ...post, id: 'another' }, wait], 'hybrid').length, 0)
  assert.equal(requestAssociations([post, { ...wait, operation: 'MPI_Waitall' }], 'hybrid').length, 0)
  assert.equal(requestAssociations([post, { ...wait, arguments: ['req[0]'] }], 'hybrid').length, 0)
  const fpost = { ...post, evidence: [{ path: 'test.F', startLine: 10 }], arguments: ['buf', 'n', 'type', 'peer', 'tag', 'comm', 'REQ', 'ierr'] }
  const fwait = { ...wait, evidence: [{ path: 'test.F', startLine: 20 }], arguments: ['req', 'status', 'ierr'] }
  assert.equal(requestAssociations([fpost, fwait], 'dmpar')[0]?.request, 'req')
})

test('official checkout evidence connects the local OpenMP extent and RSL request pair', () => {
  const index = JSON.parse(readFileSync(new URL('../public/data/snapshots/wrf-v4.8.0.parallel.json', import.meta.url), 'utf8')) as ParallelIndex
  const solver = index.events.filter(item => item.scopeId === 'dyn_em/solve_em.F::solve_em')
  const body = solver.find(item => item.operation === 'zero_bdytend')!
  const region = enclosingThreadRegion(body, solver, 'hybrid')!
  assert.equal(region.evidence[0]?.startLine, 491)
  assert.equal(region.endEvidence?.startLine, 533)
  assert.ok(solver.some(item => item.regionId === region.id && item.kind === 'omp_join'))
  const pairs = requestAssociations(index.events.filter(item => item.scope === 'rsl_lite_exch_y'), 'dmpar')
  const pair = pairs.find(item => item.request === 'yp_recv')!
  assert.equal(pair.post.evidence[0]?.startLine, 1016)
  assert.equal(pair.wait.evidence[0]?.startLine, 1027)
})
