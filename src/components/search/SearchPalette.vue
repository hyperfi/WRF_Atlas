<template>
  <div v-if="isOpen" class="search-backdrop" @click.self="close">
    <div class="search-palette glass-panel">
      <div class="search-input-wrapper">
        <span class="search-icon">🔍</span>
        <input 
          ref="searchInput"
          v-model="query"
          type="text" 
          class="search-input" 
          placeholder="Search physics schemes, variables, subroutines..."
          @keydown.esc="close"
          @keydown.down.prevent="moveSelection(1)"
          @keydown.up.prevent="moveSelection(-1)"
          @keydown.enter="selectCurrent"
        />
        <span class="search-hint">ESC to close</span>
      </div>
      
      <div class="search-results">
        <div v-if="filteredResults.length === 0" class="no-results">
          No results found for "{{ query }}"
        </div>
        
        <div 
          v-for="(result, index) in filteredResults" 
          :key="result.id"
          class="result-item"
          :class="{ 'selected': selectedIndex === index }"
          @click="selectResult(result)"
          @mouseenter="selectedIndex = index"
        >
          <div class="result-icon">
            {{ getIconForType(result.type) }}
          </div>
          <div class="result-info">
            <div class="result-label" :class="`text-${result.type}`">{{ result.label }}</div>
            <div class="result-type">{{ formatType(result.type) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useGraphStore } from '@/stores/graphStore'
import { useRouter } from 'vue-router'
import type { GraphNode } from '@/types/graph'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits(['close'])

const graphStore = useGraphStore()
const router = useRouter()

const query = ref('')
const searchInput = ref<HTMLInputElement | null>(null)
const selectedIndex = ref(0)

const close = () => {
  emit('close')
  query.value = ''
}

const filteredResults = computed(() => {
  if (!query.value.trim() || !graphStore.isLoaded) return []
  return graphStore.searchNodes(query.value, 15)
})

watch(query, () => {
  selectedIndex.value = 0
})

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    nextTick(() => {
      searchInput.value?.focus()
    })
  }
})

const moveSelection = (dir: number) => {
  selectedIndex.value = (selectedIndex.value + dir + filteredResults.value.length) % filteredResults.value.length
}

const selectCurrent = () => {
  if (filteredResults.value[selectedIndex.value]) {
    selectResult(filteredResults.value[selectedIndex.value])
  }
}

const selectResult = (result: GraphNode) => {
  // Navigate based on type
  if (result.type === 'physics_scheme' || result.type === 'namelist_option') {
    router.push('/physics')
  } else if (result.type === 'state_variable') {
    router.push('/variables')
  } else {
    router.push('/source')
  }
  close()
}

const getIconForType = (type: string) => {
  const map: Record<string, string> = {
    namelist_option: '⚙️',
    physics_scheme: '☁️',
    state_variable: '📦',
    subroutine: 'f()',
    module: '📦'
  }
  return map[type] || '📄'
}

const formatType = (type: string) => {
  return type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
}

const handleGlobalKeydown = (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    if (props.isOpen) close()
    else emit('close') // we need a way to open it, parent handles this
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>

<style scoped>
.search-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  justify-content: center;
  padding-top: 10vh;
}

.search-palette {
  width: 100%;
  max-width: 600px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--border-subtle);
  gap: 1rem;
}

.search-icon {
  font-size: 1.25rem;
  color: var(--text-muted);
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 1.25rem;
  outline: none;
  font-family: var(--font-sans);
}

.search-input::placeholder {
  color: var(--text-muted);
}

.search-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.1);
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}

.search-results {
  overflow-y: auto;
  padding: 0.5rem;
}

.no-results {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}

.result-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.1s;
}

.result-item.selected, .result-item:hover {
  background: rgba(59, 130, 246, 0.15);
}

.result-icon {
  width: 2.5rem;
  height: 2.5rem;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-family: var(--font-mono);
  color: var(--text-secondary);
}

.result-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.result-label {
  font-weight: 500;
  font-size: 1.1rem;
}

.result-type {
  font-size: 0.8rem;
  color: var(--text-muted);
}
</style>
