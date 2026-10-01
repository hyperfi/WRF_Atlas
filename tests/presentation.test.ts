import test from 'node:test'
import assert from 'node:assert/strict'
import { sourceExcerpt, uniqueTargets } from '../src/lib/presentation.ts'
import { rankedSearch, entityDestination, registryFieldGroups } from '../src/lib/exploration.ts'

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

test('exact entities outrank substring matches before the result limit is applied', () => {
  const nodes = Array.from({ length: 40 }, (_, i) => ({ id: `state:hfx_${i}`, label: `hfx_${i}`, type: 'state_variable', data: {} }))
  const exact = { id: 'state:hfx', label: 'hfx', type: 'state_variable', data: {} }
  nodes.push(exact)
  assert.equal(rankedSearch(nodes, ' HFX ', 2)[0], exact)
  assert.deepEqual(rankedSearch(nodes, '   '), [])
  assert.equal(nodes.at(-1), exact)
})

test('search destinations preserve the selected field, package, and configuration option', () => {
  assert.deepEqual(entityDestination({ id: 'state:hfx', label: 'hfx', type: 'state_variable', data: {} }), { path: '/variables', query: { field: 'hfx' } })
  assert.deepEqual(entityDestination({ id: 'package:lsmscheme', label: 'Noah', type: 'registry_package', data: { category: 'land_surface', value: '2' } }), { path: '/physics/land_surface', query: { scheme: '2' } })
  assert.deepEqual(entityDestination({ id: 'namelist:sf_surface_physics', label: 'sf_surface_physics', type: 'namelist_option', data: { category: 'land_surface' } }), { path: '/namelist', query: { focus: 'sf_surface_physics' } })
})

test('learning field groups retain source descriptions and unknown fields without inventing semantics', () => {
  const flux = { id: 'state:hfx', label: 'hfx', type: 'state_variable', data: { description: 'UPWARD HEAT FLUX AT THE SURFACE', units: 'W m-2' } }
  const unknown = { id: 'state:experimental', label: 'experimental', type: 'state_variable', data: {} }
  const groups = registryFieldGroups([unknown, flux])
  assert.equal(groups[0]?.fields[0], flux)
  assert.equal(groups[1]?.title, 'Other model state')
  assert.equal(groups[1]?.fields[0], unknown)
  assert.equal(flux.data.units, 'W m-2')
})
