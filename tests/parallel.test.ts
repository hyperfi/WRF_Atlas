import test from 'node:test'
import assert from 'node:assert/strict'
import { communicationTopology, evaluateBuildGuard, eventAvailability, eventMeaning, illustrativeDimensions, matchingParallelIndex, rankNeighbors, type ParallelEvent, type ParallelIndex } from '../src/lib/parallel.ts'

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
