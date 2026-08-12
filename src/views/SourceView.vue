<template>
  <div class="source-view-container">
    <!-- Sidebar: Source File Directory & Filter -->
    <div class="source-sidebar glass">
      <div class="sidebar-header">
        <h3>WRF Source Files</h3>
        <span class="file-count" v-if="allFiles.length">{{ allFiles.length }} files</span>
      </div>

      <div class="search-box">
        <input 
          v-model="fileQuery" 
          type="text" 
          placeholder="Filter files (e.g. surface_driver)..." 
          class="search-input" 
        />
      </div>

      <div class="file-list" v-if="filteredFiles.length">
        <div 
          v-for="file in filteredFiles" 
          :key="file.id"
          class="file-item"
          :class="{ active: currentFilePath === file.data?.path }"
          @click="selectFile(file.data?.path)"
        >
          <span class="file-icon">📄</span>
          <div class="file-info">
            <span class="file-name">{{ getBasename(file.label) }}</span>
            <span class="file-dir">{{ getDirname(file.data?.path) }}</span>
          </div>
        </div>
      </div>

      <div v-else-if="graphStore.isLoaded" class="no-files">
        No files match "{{ fileQuery }}"
      </div>

      <div v-else class="loading-files">
        Loading source directory...
      </div>
    </div>

    <!-- Main View: Source Code Viewer -->
    <div class="source-main">
      <SourceViewer 
        :filePath="currentFilePath"
        :sourceCode="currentSourceCode"
        :loading="loadingSource"
        :initialLine="targetLine"
        :highlightLines="highlightLines"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/graphStore'
import SourceViewer from '@/components/source/SourceViewer.vue'

const route = useRoute()
const router = useRouter()
const graphStore = useGraphStore()

const fileQuery = ref('')
const currentFilePath = ref<string>('phys/module_surface_driver.F')
const currentSourceCode = ref<string>('')
const loadingSource = ref(false)
const targetLine = ref<number | undefined>(undefined)
const highlightLines = ref<number[]>([])

const allFiles = computed(() => {
  if (!graphStore.isLoaded) return []
  return graphStore.getNodesByType('source_file')
})

const filteredFiles = computed(() => {
  if (!fileQuery.value.trim()) return allFiles.value
  const q = fileQuery.value.toLowerCase()
  return allFiles.value.filter(f => 
    f.label.toLowerCase().includes(q) || 
    (f.data?.path && f.data.path.toLowerCase().includes(q))
  )
})

const getBasename = (path: string) => {
  if (!path) return ''
  const parts = path.split(/[/\\]/)
  return parts[parts.length - 1]
}

const getDirname = (path: string) => {
  if (!path) return ''
  const parts = path.split(/[/\\]/)
  if (parts.length <= 1) return ''
  return parts.slice(0, -1).join('/')
}

const fetchSourceFile = async (filePath: string) => {
  if (!filePath) return
  loadingSource.value = true
  currentSourceCode.value = ''
  try {
    const res = await fetch(`/api/source?file=${encodeURIComponent(filePath)}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const text = await res.text()
    currentSourceCode.value = text
  } catch (e: any) {
    currentSourceCode.value = `! Failed to load source file: ${filePath}\n! Error: ${e.message}\n! Verify file exists at WRF source root.`
  } finally {
    loadingSource.value = false
  }
}

const selectFile = (filePath?: string) => {
  if (!filePath) return
  currentFilePath.value = filePath
  router.replace({ query: { file: filePath } })
  fetchSourceFile(filePath)
}

watch(() => route.query, (query) => {
  if (query.file && typeof query.file === 'string') {
    currentFilePath.value = query.file
    if (query.line) {
      targetLine.value = parseInt(query.line as string)
      highlightLines.value = [targetLine.value]
    }
    fetchSourceFile(query.file)
  }
}, { immediate: true })

onMounted(async () => {
  if (!graphStore.isLoaded && !graphStore.loading) {
    await graphStore.loadGraph()
  }
  const queryFile = route.query.file as string
  if (queryFile) {
    currentFilePath.value = queryFile
  } else {
    currentFilePath.value = 'phys/module_surface_driver.F'
  }
  fetchSourceFile(currentFilePath.value)
})
</script>

<style scoped>
.source-view-container {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 1.25rem;
  height: calc(100vh - var(--header-height) - 3rem);
}

.source-sidebar {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 10px;
}

.sidebar-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(0, 0, 0, 0.15);
}

.sidebar-header h3 {
  font-size: 1rem;
  margin: 0;
}

.file-count {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.08);
  padding: 0.15rem 0.5rem;
  border-radius: 10px;
}

.search-box {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-subtle);
}

.search-input {
  width: 100%;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 0.4rem 0.75rem;
  color: var(--text-primary);
  font-size: 0.8rem;
  outline: none;
}

.search-input:focus {
  border-color: var(--accent-blue);
}

.file-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.file-item:hover {
  background: rgba(255, 255, 255, 0.06);
}

.file-item.active {
  background: rgba(59, 130, 246, 0.2);
  border-left: 3px solid var(--accent-blue);
}

.file-icon {
  font-size: 1rem;
}

.file-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-name {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.file-dir {
  font-size: 0.7rem;
  color: var(--text-muted);
  font-family: var(--font-mono);
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
}

.source-main {
  height: 100%;
  overflow: hidden;
}

.no-files, .loading-files {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.85rem;
}
</style>
