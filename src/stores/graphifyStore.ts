import { computed, ref, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import type { GraphifySearchEntry, GraphifySearchIndex } from '@/types/graph'

export const useGraphifyStore = defineStore('graphify', () => {
  const index = shallowRef<GraphifySearchIndex | null>(null)
  const loading = ref(false)
  const attempted = ref(false)
  const error = ref<string | null>(null)
  let loadPromise: Promise<void> | null = null

  const publicAsset = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\//, '')}`

  const loadIndex = async (refresh = false) => {
    if (refresh) index.value = null
    if (index.value || loadPromise) return loadPromise
    loadPromise = (async () => {
      loading.value = true
      error.value = null
      const candidates = import.meta.env.DEV
        ? ['data/local/graphify-search.json', 'data/graphify/search.json']
        : ['data/graphify/search.json']
      try {
        for (const candidate of candidates) {
          const response = await fetch(`${publicAsset(candidate)}${refresh ? `?updated=${Date.now()}` : ''}`, { cache: refresh ? 'no-store' : 'default' })
          if (response.status === 404) continue
          if (!response.ok) throw new Error(`HTTP ${response.status} loading ${candidate}`)
          const data: GraphifySearchIndex = await response.json()
          if (data.schemaVersion !== 1 || data.metadata?.provider !== 'graphify') {
            throw new Error('Unsupported Graphify search-index format')
          }
          index.value = data
          return
        }
      } catch (reason: any) {
        error.value = reason?.message || 'Unable to load the Graphify search index'
      } finally {
        attempted.value = true
        loading.value = false
        loadPromise = null
      }
    })()
    return loadPromise
  }

  const search = (query: string, limit = 20): GraphifySearchEntry[] => {
    const cleaned = query.trim().toLowerCase()
    if (!cleaned || !index.value) return []
    const tokens = cleaned.split(/\s+/).filter(Boolean)
    return index.value.entries
      .map(entry => {
        const label = entry.label.toLowerCase()
        const path = entry.path.toLowerCase()
        const relations = entry.relations.join(' ').toLowerCase()
        if (!tokens.every(token => label.includes(token) || path.includes(token) || relations.includes(token))) {
          return { entry, score: -1 }
        }
        let score = label === cleaned ? 120 : label.startsWith(cleaned) ? 90 : label.includes(cleaned) ? 65 : 0
        if (path.includes(cleaned)) score += 30
        if (relations.includes(cleaned)) score += 16
        if (entry.confidence === 'extracted') score += 4
        return { entry, score }
      })
      .filter(result => result.score >= 0)
      .sort((a, b) => b.score - a.score || a.entry.label.localeCompare(b.entry.label))
      .slice(0, limit)
      .map(result => result.entry)
  }

  const available = computed(() => Boolean(index.value))
  const metadata = computed(() => index.value?.metadata || null)

  return { index, loading, attempted, error, available, metadata, loadIndex, search }
})
