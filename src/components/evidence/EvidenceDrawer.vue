<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useEvidenceStore } from '@/stores/evidenceStore'
import { useGraphStore } from '@/stores/graphStore'
import { useLocalSourceStore } from '@/stores/localSourceStore'
import { sourceExcerpt } from '@/lib/presentation'

const store = useEvidenceStore()
const graph = useGraphStore()
const local = useLocalSourceStore()
const router = useRouter()
const dialog = ref<HTMLDialogElement>()
const text = ref('')
const loading = ref(false)
const error = ref('')
let request = 0
const excerpt = computed(() => sourceExcerpt(text.value, store.selection?.evidence.startLine, store.selection?.evidence.endLine || store.selection?.evidence.startLine))
const sourceLabel = computed(() => local.connected ? `Local folder: ${local.folderName} · graph: ${graph.metadata?.source_label}` : graph.metadata?.source_label || 'Indexed checkout')
const githubUrl = computed(() => {
  const meta = graph.metadata
  if (local.connected || meta?.source_mode === 'local' || !meta?.repository_url || !meta.commit || meta.commit === 'unknown') return ''
  return `${meta.repository_url.replace(/\/$/, '')}/blob/${meta.commit}/${store.selection?.evidence.path.replaceAll('\\', '/')}#L${store.selection?.evidence.startLine || 1}`
})
watch(() => [store.selection, graph.activeSnapshotId, local.connected], async () => {
  const selection = store.selection
  const version = ++request
  if (!selection) { dialog.value?.close(); return }
  await nextTick()
  if (!dialog.value?.open) dialog.value?.showModal()
  text.value = ''; error.value = ''; loading.value = true
  try {
    let source: string
    if (local.connected) source = await local.readTextFile(selection.evidence.path)
    else {
      const meta = graph.metadata
      const path = selection.evidence.path.replaceAll('\\', '/')
      const isLocal = import.meta.env.DEV && meta?.source_mode === 'local'
      if (!isLocal && (!meta?.repository_url || !meta.commit || meta.commit === 'unknown')) throw new Error('No public source repository is configured for this snapshot. Select a local WRF folder.')
      const url = isLocal ? `/api/source?file=${encodeURIComponent(path)}` : `${meta!.repository_url!.replace('https://github.com/', 'https://raw.githubusercontent.com/').replace(/\/$/, '')}/${meta!.commit}/${path}`
      const response = await fetch(url)
      if (!response.ok) throw new Error(`Source request failed (HTTP ${response.status})`)
      source = await response.text()
    }
    if (version === request) text.value = source
  } catch (e) { if (version === request) error.value = e instanceof Error ? e.message : String(e) }
  finally { if (version === request) loading.value = false }
}, { immediate: true })
const openFullSource = () => {
  const evidence = store.selection?.evidence
  if (!evidence) return
  const returnTo = store.selection?.returnTo || router.currentRoute.value.fullPath
  store.close()
  router.push({ path: '/source', query: { file: evidence.path, line: String(evidence.startLine || 1), returnTo } })
}
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="evidence-drawer" aria-labelledby="evidence-title" @cancel.prevent="store.close()" @click="($event.target === dialog) && store.close()">
      <section v-if="store.selection" class="drawer-sheet">
        <header><div><p class="eyebrow">Inspect evidence</p><h2 id="evidence-title">{{ store.selection.title }}</h2></div><button class="close-drawer" autofocus @click="store.close()" aria-label="Close evidence">✕</button></header>
        <div class="drawer-context"><span :class="['confidence', store.selection.confidence]">{{ store.selection.confidence }}</span><span>{{ sourceLabel }}</span></div>
        <p v-if="local.connected" class="source-warning">Files come from your selected folder. Line references belong to the indexed snapshot; they may differ if the folder has been modified.</p>
        <p v-if="store.selection.explanation" class="explanation">{{ store.selection.explanation }}</p>
        <div class="source-location"><code>{{ store.selection.evidence.path }}</code><span>Lines {{ store.selection.evidence.startLine || 1 }}<template v-if="store.selection.evidence.endLine && store.selection.evidence.endLine !== store.selection.evidence.startLine">–{{ store.selection.evidence.endLine }}</template></span></div>
        <div class="excerpt-scroll">
          <p v-if="loading" class="drawer-message" role="status">Loading source…</p>
          <p v-else-if="error" class="drawer-message source-warning" role="alert">{{ error }}</p>
          <div v-else>
          <p v-if="excerpt.outOfRange" class="drawer-message source-warning">The indexed line is beyond this file's length. Check that your source folder matches the selected snapshot.</p>
          <div class="source-excerpt" aria-label="Source excerpt">
            <div v-for="line in excerpt.lines" :key="line.number" :class="{ highlighted: line.highlighted }"><span>{{ line.number }}</span><pre>{{ line.text || ' ' }}</pre></div>
          </div>
          </div>
        </div>
        <footer><p>Exact lines support this source fact, not unconditional runtime execution.</p><div><button @click="openFullSource">Open full source ↗</button><a v-if="githubUrl" :href="githubUrl" target="_blank" rel="noreferrer">Exact commit on GitHub ↗</a></div><small v-if="excerpt.truncated">Excerpt shortened; open full source for the complete range.</small></footer>
      </section>
    </dialog>
  </Teleport>
</template>

<style scoped>
.evidence-drawer { position: fixed; inset: 0 0 0 auto; margin: 0; width: min(740px, 95vw); height: 100dvh; max-height: none; max-width: none; padding: 0; border: 0; border-left: 1px solid var(--border-strong); background: var(--bg-panel); color: var(--text-primary); box-shadow: -18px 0 70px #0005; }
.evidence-drawer::backdrop { background: #0008; }
.drawer-sheet { display: flex; height: 100%; flex-direction: column; min-height: 0; }
header { display: flex; justify-content: space-between; gap: 20px; padding: 24px; border-bottom: 1px solid var(--border-subtle); }
header h2 { margin-top: 4px; font-size: 1.2rem; overflow-wrap: anywhere; }
.close-drawer { align-self: start; background: var(--bg-inset); border: 1px solid var(--border-strong); color: var(--text-primary); border-radius: 4px; padding: 5px 10px; cursor: pointer; }
.drawer-context { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; padding: 16px 24px 8px; color: var(--text-secondary); font-size: .74rem; }
.confidence { border: 1px solid var(--border-strong); border-radius: 3px; padding: 2px 7px; color: var(--accent-emerald); font: .68rem var(--font-mono); }.confidence.inferred { color: var(--accent-amber); }
.explanation,.source-warning { padding: 8px 24px; color: var(--text-secondary); font-size: .8rem; line-height: 1.6; }.source-warning { color: var(--accent-amber); }
.source-location { display: flex; flex-direction: column; gap: 5px; padding: 15px 24px; border-bottom: 1px solid var(--border-subtle); font-size: .74rem; }.source-location code { overflow-wrap: anywhere; }.source-location span { color: var(--text-secondary); }
.excerpt-scroll { flex: 1; overflow: auto; min-height: 120px; background: var(--bg-inset); }.source-excerpt { min-width: max-content; padding: 12px 0; font: .74rem/1.85 var(--font-mono); }.source-excerpt > div { display: flex; padding-right: 20px; }.source-excerpt span { flex-shrink: 0; width: 64px; padding-right: 16px; text-align: right; color: var(--text-muted); user-select: none; }.source-excerpt pre { margin: 0; font: inherit; white-space: pre; }.source-excerpt .highlighted { background: var(--accent-soft); box-shadow: inset 3px 0 var(--accent-emerald); }
.drawer-message { padding: 24px; font-size: .85rem; }
footer { padding: 17px 24px; border-top: 1px solid var(--border-subtle); }footer p,footer small { color: var(--text-secondary); font-size: .72rem; }footer > div { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }footer button,footer a { border: 1px solid var(--border-strong); border-radius: 4px; background: var(--bg-inset); padding: 8px 11px; color: var(--text-primary); cursor: pointer; font-size: .76rem; }
@media (prefers-reduced-motion: no-preference) { .evidence-drawer[open] { animation: drawer-in .18s ease-out; }@keyframes drawer-in { from { transform: translateX(30px); opacity: .6; }to { transform: translateX(0); opacity: 1; } } }
</style>
