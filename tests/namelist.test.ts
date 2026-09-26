import assert from 'node:assert/strict'
import { test } from 'node:test'
import { getNamelistValue, parseNamelist, unquoteNamelist, updateNamelistValue } from '../src/lib/namelist.ts'

const example = `&domains
 max_dom = 2,
/
&physics
 physics_suite = 'CONUS', ! suite values fill only unset (-1) options
 mp_physics = 8, 10,
 sf_surface_physics = 2*2,
 ra_lw_physics(2) = 4,
 note = 'rain, snow',
 message = 'rain! snow',
/
`

test('parses groups, per-domain values, repeat counts, and quoted commas', () => {
  const parsed = parseNamelist(example)
  assert.equal(parsed.maxDomain, 2)
  assert.equal(getNamelistValue(parsed, 'physics', 'mp_physics', 2), '10')
  assert.equal(getNamelistValue(parsed, 'physics', 'sf_surface_physics', 2), '2')
  assert.equal(getNamelistValue(parsed, 'physics', 'ra_lw_physics', 1), undefined)
  assert.equal(getNamelistValue(parsed, 'physics', 'ra_lw_physics', 2), '4')
  assert.equal(unquoteNamelist(getNamelistValue(parsed, 'physics', 'physics_suite')), 'CONUS')
  assert.equal(getNamelistValue(parsed, 'physics', 'note'), "'rain, snow'")
  assert.equal(getNamelistValue(parsed, 'physics', 'message'), "'rain! snow'")
})

test('edits the selected domain while preserving unrelated groups', () => {
  const updated = updateNamelistValue(example, 'physics', 'mp_physics', 2, '6')
  const parsed = parseNamelist(updated)
  assert.equal(getNamelistValue(parsed, 'physics', 'mp_physics', 1), '8')
  assert.equal(getNamelistValue(parsed, 'physics', 'mp_physics', 2), '6')
  assert.equal(getNamelistValue(parsed, 'domains', 'max_dom'), '2')
})

test('adds an indexed assignment without fabricating other domains', () => {
  const updated = updateNamelistValue(example, 'physics', 'cu_physics', 2, '0')
  const parsed = parseNamelist(updated)
  assert.equal(getNamelistValue(parsed, 'physics', 'cu_physics', 1), undefined)
  assert.equal(getNamelistValue(parsed, 'physics', 'cu_physics', 2), '0')
})

test('changing one domain preserves comments and other assignments', () => {
  const source = "&physics\n mp_physics = 8, 10, ! separate domains\n cu_physics = 0, 1,\n/\n"
  const updated = updateNamelistValue(source, 'physics', 'mp_physics', 2, '6')
  assert.match(updated, /mp_physics = 8, 6, ! separate domains/)
  assert.match(updated, /cu_physics = 0, 1/)
})
