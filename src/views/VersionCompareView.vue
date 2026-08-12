<template>
  <div class="compare-view">
    <header class="page-header">
      <div><p class="eyebrow">Source evolution</p><h1>Compare WRF releases</h1><p>See how the indexed configuration surface and executable architecture changed between pinned upstream commits.</p></div>
      <div class="compare-contract"><span>Structural comparison</span><small>Presence in the index does not by itself prove runtime activation.</small></div>
    </header>

    <section class="compare-controls surface-panel">
      <label><span>Baseline</span><select v-model="leftId"><option v-for="item in publicSnapshots" :key="item.id" :value="item.id">{{ item.label }}</option></select></label>
      <div class="compare-direction"><span>→</span><small>indexed change</small></div>
      <label><span>Target</span><select v-model="rightId"><option v-for="item in publicSnapshots" :key="item.id" :value="item.id">{{ item.label }}</option></select></label>
    </section>

    <div v-if="loading" class="loading-panel surface-panel">Loading pinned knowledge graphs…</div>
    <template v-else-if="comparison">
      <section class="release-identities">
        <article class="surface-panel"><p class="eyebrow">Baseline</p><h2>WRF {{ leftGraph?.metadata.wrf_version }}</h2><code>{{ leftGraph?.metadata.commit.slice(0, 12) }}</code><span>{{ leftGraph?.metadata.stats?.fortran_files_parsed }} indexed Fortran files</span></article>
        <article class="surface-panel target"><p class="eyebrow">Target</p><h2>WRF {{ rightGraph?.metadata.wrf_version }}</h2><code>{{ rightGraph?.metadata.commit.slice(0, 12) }}</code><span>{{ rightGraph?.metadata.stats?.fortran_files_parsed }} indexed Fortran files</span></article>
      </section>

      <section class="metric-grid">
        <article v-for="metric in comparison.metrics" :key="metric.label" class="surface-panel"><span>{{ metric.label }}</span><strong :class="metric.delta > 0 ? 'positive' : metric.delta < 0 ? 'negative' : ''">{{ signed(metric.delta) }}</strong><small>{{ metric.before.toLocaleString() }} → {{ metric.after.toLocaleString() }}</small></article>
      </section>

      <section class="change-grid">
        <article class="change-panel surface-panel"><div class="panel-title"><div><p class="eyebrow">Configuration surface</p><h2>New namelist controls</h2></div><span>{{ comparison.addedNamelists.length }}</span></div><div class="entity-list"><code v-for="name in comparison.addedNamelists.slice(0, 24)" :key="name">{{ name }}</code><p v-if="!comparison.addedNamelists.length">No additions resolved.</p></div></article>
        <article class="change-panel surface-panel"><div class="panel-title"><div><p class="eyebrow">Physics registry</p><h2>New package mappings</h2></div><span>{{ comparison.addedPackages.length }}</span></div><div class="mapping-list"><div v-for="item in comparison.addedPackages.slice(0, 18)" :key="item.key"><code>{{ item.selector }} = {{ item.value }}</code><strong>{{ item.label }}</strong></div><p v-if="!comparison.addedPackages.length">No additions resolved.</p></div></article>
        <article class="change-panel surface-panel"><div class="panel-title"><div><p class="eyebrow">Executable code</p><h2>New indexed routines</h2></div><span>{{ comparison.addedRoutines.length }}</span></div><div class="entity-list"><code v-for="name in comparison.addedRoutines.slice(0, 24)" :key="name">{{ name }}</code><p v-if="!comparison.addedRoutines.length">No additions resolved.</p></div></article>
        <article class="change-panel surface-panel"><div class="panel-title"><div><p class="eyebrow">Removed or moved</p><h2>Entities absent in target</h2></div><span>{{ comparison.removedNodes.length }}</span></div><div class="entity-list"><code v-for="name in comparison.removedNodes.slice(0, 24)" :key="name">{{ name }}</code><p v-if="!comparison.removedNodes.length">No removals resolved.</p></div></article>
      </section>

      <div class="comparison-warning"><strong>Interpretation boundary</strong><p>A removed symbol may have been renamed, moved into a submodule, generated at build time, or excluded by tolerant parsing. Open each release snapshot before treating a structural difference as a scientific behavior change.</p></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, shallowRef, watch } from 'vue'
import { useGraphStore } from '@/stores/graphStore'
import type { KnowledgeGraph } from '@/types/graph'

const graphStore = useGraphStore()
const leftId = ref('wrf-v4.7.1')
const rightId = ref('wrf-v4.8.0')
const leftGraph = shallowRef<KnowledgeGraph | null>(null)
const rightGraph = shallowRef<KnowledgeGraph | null>(null)
const loading = ref(false)
const publicSnapshots = computed(() => graphStore.snapshots.filter(item => item.public))
const asset = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\//, '')}`

const fetchGraph = async (id: string) => {
  const snapshot = graphStore.snapshots.find(item => item.id === id)
  if (!snapshot) return null
  const response = await fetch(asset(snapshot.file))
  if (!response.ok) throw new Error(`Unable to load ${snapshot.label}`)
  return response.json() as Promise<KnowledgeGraph>
}

const loadComparison = async () => {
  if (!leftId.value || !rightId.value) return
  loading.value = true
  try { [leftGraph.value, rightGraph.value] = await Promise.all([fetchGraph(leftId.value), fetchGraph(rightId.value)]) }
  finally { loading.value = false }
}

const comparison = computed(() => {
  if (!leftGraph.value || !rightGraph.value) return null
  const left = leftGraph.value
  const right = rightGraph.value
  const leftIds = new Set(left.nodes.map(node => node.id))
  const rightIds = new Set(right.nodes.map(node => node.id))
  const added = right.nodes.filter(node => !leftIds.has(node.id))
  const removed = left.nodes.filter(node => !rightIds.has(node.id))
  const leftPackages = new Set(left.nodes.filter(node => node.type === 'registry_package').map(node => `${node.data.namelist_var}:${node.data.value}:${node.data.package_name}`))
  const addedPackages = right.nodes.filter(node => node.type === 'registry_package' && !leftPackages.has(`${node.data.namelist_var}:${node.data.value}:${node.data.package_name}`)).map(node => ({ key: node.id, selector: node.data.namelist_var, value: node.data.value, label: node.label }))
  return {
    metrics: [
      { label: 'Graph nodes', before: left.nodes.length, after: right.nodes.length, delta: right.nodes.length - left.nodes.length },
      { label: 'Graph edges', before: left.edges.length, after: right.edges.length, delta: right.edges.length - left.edges.length },
      { label: 'Namelist controls', before: left.metadata.stats?.namelist_options || 0, after: right.metadata.stats?.namelist_options || 0, delta: (right.metadata.stats?.namelist_options || 0) - (left.metadata.stats?.namelist_options || 0) },
      { label: 'Registry state fields', before: left.metadata.stats?.state_variables || 0, after: right.metadata.stats?.state_variables || 0, delta: (right.metadata.stats?.state_variables || 0) - (left.metadata.stats?.state_variables || 0) },
    ],
    addedNamelists: added.filter(node => node.type === 'namelist_option').map(node => node.label).sort(),
    addedPackages,
    addedRoutines: added.filter(node => node.type === 'subroutine' || node.type === 'function').map(node => node.label).sort(),
    removedNodes: removed.filter(node => ['namelist_option', 'registry_package', 'subroutine', 'function'].includes(node.type)).map(node => node.label).sort(),
  }
})

const signed = (value: number) => value > 0 ? `+${value.toLocaleString()}` : value.toLocaleString()
watch([leftId, rightId], loadComparison)
onMounted(async () => { await graphStore.loadSnapshots(); await loadComparison() })
</script>

<style scoped>
.compare-view{display:flex;width:100%;max-width:1480px;margin:0 auto;flex-direction:column;gap:16px}.page-header{display:flex;align-items:flex-end;justify-content:space-between;gap:35px;padding:4px 2px 8px}.page-header h1{margin-top:6px;font-size:2rem}.page-header>div>p:last-child{max-width:760px;margin-top:7px;color:var(--text-secondary);font-size:.8rem}.compare-contract{max-width:300px;padding-left:18px;border-left:1px solid var(--border-subtle)}.compare-contract span{color:var(--accent-emerald);font-family:var(--font-mono);font-size:.58rem;text-transform:uppercase}.compare-contract small{display:block;margin-top:5px;color:var(--text-muted);font-size:.61rem;line-height:1.45}.compare-controls{display:grid;grid-template-columns:1fr 80px 1fr;align-items:end;gap:16px;padding:16px 18px}.compare-controls label{display:flex;flex-direction:column;gap:6px}.compare-controls label span{color:var(--text-muted);font-size:.6rem;text-transform:uppercase}.compare-controls select{height:38px;padding:0 10px;background:var(--bg-inset);border:1px solid var(--border-subtle);border-radius:5px;color:var(--text-primary)}.compare-direction{text-align:center}.compare-direction span{display:block;color:var(--accent-emerald);font-size:1.1rem}.compare-direction small{color:var(--text-muted);font-size:.55rem}.loading-panel{display:grid;min-height:400px;place-items:center;color:var(--text-muted)}.release-identities{display:grid;grid-template-columns:1fr 1fr;gap:14px}.release-identities article{padding:17px 20px;border-left:2px solid var(--text-muted)}.release-identities article.target{border-left-color:var(--accent-emerald)}.release-identities h2{margin:4px 0 7px;font-size:1rem}.release-identities code{color:var(--accent-amber);font-size:.63rem}.release-identities article>span{float:right;color:var(--text-muted);font-size:.61rem}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric-grid article{padding:15px 16px}.metric-grid article>span{display:block;color:var(--text-muted);font-size:.61rem}.metric-grid strong{display:block;margin:6px 0 3px;font-family:var(--font-mono);font-size:1.15rem}.metric-grid strong.positive{color:var(--accent-emerald)}.metric-grid strong.negative{color:var(--accent-amber)}.metric-grid small{color:var(--text-muted);font-size:.58rem}.change-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.change-panel{overflow:hidden}.panel-title{display:flex;align-items:center;justify-content:space-between;padding:15px 17px;border-bottom:1px solid var(--border-subtle)}.panel-title h2{margin-top:4px;font-size:.86rem}.panel-title>span{color:var(--accent-emerald);font-family:var(--font-mono)}.entity-list{display:flex;max-height:270px;flex-wrap:wrap;gap:6px;overflow:auto;padding:14px}.entity-list code{padding:5px 7px;background:var(--bg-inset);border:1px solid var(--border-subtle);border-radius:4px;color:var(--text-secondary);font-size:.59rem}.entity-list p,.mapping-list>p{color:var(--text-muted);font-size:.64rem}.mapping-list{max-height:270px;overflow:auto}.mapping-list>div{display:grid;grid-template-columns:180px 1fr;gap:10px;padding:9px 15px;border-bottom:1px solid var(--border-subtle)}.mapping-list code{color:var(--accent-amber);font-size:.59rem}.mapping-list strong{font-size:.64rem}.comparison-warning{display:grid;grid-template-columns:170px 1fr;gap:20px;padding:13px 16px;background:color-mix(in srgb,var(--accent-amber) 7%,var(--bg-panel));border:1px solid color-mix(in srgb,var(--accent-amber) 26%,var(--border-subtle));border-radius:6px}.comparison-warning strong{font-size:.66rem}.comparison-warning p{color:var(--text-secondary);font-size:.63rem;line-height:1.5}@media(max-width:900px){.page-header{align-items:flex-start;flex-direction:column}.metric-grid{grid-template-columns:1fr 1fr}.change-grid,.release-identities{grid-template-columns:1fr}.compare-controls{grid-template-columns:1fr}.compare-direction{display:none}}
</style>
