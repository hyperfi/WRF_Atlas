import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { useGraphStore } from './graphStore'
import { matchingParallelIndex, type ParallelIndex } from '@/lib/parallel'

export const useParallelStore = defineStore('parallel', () => {
  const graph = useGraphStore()
  const index = shallowRef<ParallelIndex | null>(null)
  const loading = ref(false)
  const error = ref('')
  let generation = 0
  const load = async () => {
    const request = ++generation
    index.value = null
    error.value = ''
    const snapshot = graph.activeSnapshot, metadata = graph.metadata
    if (!snapshot || !metadata || !graph.isLoaded) { loading.value = false; return }
    loading.value = true
    try {
      const file = snapshot.file.replace(/\.json$/, '.parallel.json')
      const response = await fetch(`${import.meta.env.BASE_URL}${file}`, { cache: 'no-cache' })
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('No parallel index is available for this snapshot. Regenerate its index, then retry.')
      const data = await response.json() as ParallelIndex
      if (!matchingParallelIndex(data, metadata)) throw new Error('Parallel evidence does not match the selected graph identity. Reindex this snapshot before exploring it.')
      if (request === generation) index.value = data
    } catch (cause) {
      if (request === generation) error.value = cause instanceof Error ? cause.message : 'Parallel index could not be loaded.'
    } finally { if (request === generation) loading.value = false }
  }
  return { index, loading, error, load }
})
