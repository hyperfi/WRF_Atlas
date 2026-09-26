import test from 'node:test'
import assert from 'node:assert/strict'
import { sourceExcerpt, uniqueTargets } from '../src/lib/presentation.ts'

test('source excerpt preserves original line numbers and highlights the evidence range', () => {
  const source = Array.from({ length: 50 }, (_, i) => `line ${i + 1}`).join('\r\n')
  const result = sourceExcerpt(source, 20, 23)
  assert.equal(result.lines[0].number, 14)
  assert.equal(result.lines[0].text, 'line 14')
  assert.deepEqual(result.lines.filter(line => line.highlighted).map(line => line.number), [20, 21, 22, 23])
  assert.equal(result.truncated, false)
})
test('source excerpt bounds large ranges and handles out-of-range anchors', () => {
  const source = Array.from({ length: 500 }, (_, i) => String(i + 1)).join('\n')
  assert.equal(sourceExcerpt(source, 50, 450).truncated, true)
  assert.ok(sourceExcerpt(source, 50, 450).lines.length < 120)
  assert.equal(sourceExcerpt(source, 800).lines.at(-1)?.number, 500)
  assert.equal(sourceExcerpt(source, 800).outOfRange, true)
  assert.equal(sourceExcerpt(source, 800).lines.some(line => line.highlighted), false)
  assert.equal(sourceExcerpt(source, -5).lines[0].number, 1)
})
test('compact target display deduplicates routines without changing first evidence', () => {
  const edges = [{ target: 'lsm', line: 20 }, { target: 'lsm', line: 40 }, { target: 'sflx', line: 80 }]
  assert.deepEqual(uniqueTargets(edges), [edges[0], edges[2]])
  assert.equal(edges.length, 3)
})
