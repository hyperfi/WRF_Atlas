<script setup lang="ts">
import { ref, computed } from 'vue'
import { useGraphStore } from '@/stores/graphStore'
import type { GraphNode } from '@/types/graph'

const graphStore = useGraphStore()

const searchQuery = ref('')
const displayCount = ref(50)
const selectedVar = ref<GraphNode | null>(null)

const stateVariables = computed(() => {
  return graphStore.getNodesByType('state_variable').sort((a, b) => a.label.localeCompare(b.label))
})

const filteredVariables = computed(() => {
  const query = searchQuery.value.toLowerCase()
  if (!query) return stateVariables.value
  
  return stateVariables.value.filter(v => 
    v.label.toLowerCase().includes(query) || 
    (v.data.description && v.data.description.toLowerCase().includes(query))
  )
})

const displayedVariables = computed(() => {
  return filteredVariables.value.slice(0, displayCount.value)
})

const loadMore = () => {
  displayCount.value += 50
}

const selectVariable = (v: GraphNode) => {
  selectedVar.value = v
}

// Compute details for selected variable
const relatedPackages = computed(() => {
  if (!selectedVar.value) return []
  const varName = selectedVar.value.data.name || selectedVar.value.label
  return graphStore.getNodesByType('registry_package').filter(p => 
    p.data.state_vars && p.data.state_vars.includes(varName)
  )
})

const referencingSubroutines = computed(() => {
  if (!selectedVar.value) return []
  const varName = selectedVar.value.data.name || selectedVar.value.label
  return graphStore.getNodesByType('subroutine').filter(s => 
    s.data.args && (s.data.args.includes(varName) || s.data.args.includes(selectedVar.value!.label))
  )
})
</script>

<template>
  <div class="variables-view">
    <div class="sidebar glass-panel">
      <div class="search-box">
        <input 
          type="text" 
          v-model="searchQuery" 
          placeholder="Search variables by name or description..." 
          class="search-input"
          @input="displayCount = 50"
        />
        <div class="var-count">{{ filteredVariables.length }} variables found</div>
      </div>
      
      <div class="var-list">
        <div 
          v-for="v in displayedVariables" 
          :key="v.id"
          class="var-card"
          :class="{ active: selectedVar?.id === v.id }"
          @click="selectVariable(v)"
        >
          <div class="var-header">
            <span class="var-name">{{ v.label }}</span>
            <span class="var-type" v-if="v.data.type">{{ v.data.type }}</span>
          </div>
          <div class="var-desc" v-if="v.data.description">{{ v.data.description }}</div>
        </div>
        
        <button 
          v-if="displayCount < filteredVariables.length" 
          @click="loadMore"
          class="load-more-btn"
        >
          Load More
        </button>
      </div>
    </div>
    
    <div class="detail-panel glass-panel">
      <div v-if="selectedVar" class="detail-content">
        <div class="detail-header">
          <h2>{{ selectedVar.label }}</h2>
          <div class="tags">
            <span class="tag" v-if="selectedVar.data.type">Type: {{ selectedVar.data.type }}</span>
            <span class="tag" v-if="selectedVar.data.dims">Dims: {{ selectedVar.data.dims }}</span>
            <span class="tag" v-if="selectedVar.data.units">Units: {{ selectedVar.data.units }}</span>
          </div>
        </div>
        
        <div class="detail-section">
          <h3>Description</h3>
          <p class="desc-text">{{ selectedVar.data.description || 'No description available.' }}</p>
        </div>
        
        <div class="detail-section" v-if="selectedVar.data.source_file">
          <h3>Definition</h3>
          <div class="source-info">
            <code>{{ selectedVar.data.source_file }}</code> : {{ selectedVar.data.source_line }}
          </div>
        </div>
        
        <div class="detail-section">
          <h3>Registry Packages ({{ relatedPackages.length }})</h3>
          <div v-if="relatedPackages.length > 0" class="chip-container">
            <div v-for="pkg in relatedPackages" :key="pkg.id" class="chip package-chip">
              {{ pkg.label }}
            </div>
          </div>
          <p v-else class="text-muted">Not explicitly part of any package state_vars.</p>
        </div>
        
        <div class="detail-section">
          <h3>Referencing Subroutines ({{ referencingSubroutines.length }})</h3>
          <div v-if="referencingSubroutines.length > 0" class="chip-container">
            <div v-for="sub in referencingSubroutines" :key="sub.id" class="chip sub-chip">
              {{ sub.label }}
            </div>
          </div>
          <p v-else class="text-muted">No subroutines found directly referencing this variable in their arguments.</p>
        </div>
      </div>
      
      <div v-else class="empty-state">
        <div class="icon">🔍</div>
        <h3>Select a variable</h3>
        <p>Choose a state variable from the list to view its journey through the model.</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.variables-view {
  height: 100%;
  display: flex;
  gap: 1.5rem;
  padding: 1.5rem;
  box-sizing: border-box;
}

.sidebar {
  width: 400px;
  display: flex;
  flex-direction: column;
  background: var(--bg-panel, rgba(15, 23, 42, 0.6));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 8px;
  overflow: hidden;
}

.search-box {
  padding: 1.25rem;
  border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  background: var(--bg-panel-header, rgba(15, 23, 42, 0.8));
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem;
  background: var(--bg-darker, rgba(0, 0, 0, 0.2));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 6px;
  color: var(--text-primary, #e2e8f0);
  font-size: 0.95rem;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.search-input:focus {
  border-color: var(--accent-blue, #3b82f6);
}

.var-count {
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: var(--text-muted, #64748b);
}

.var-list {
  flex: 1;
  overflow-y: auto;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.var-list::-webkit-scrollbar {
  width: 6px;
}
.var-list::-webkit-scrollbar-thumb {
  background: var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 3px;
}

.var-card {
  padding: 1rem;
  background: var(--bg-card, rgba(30, 41, 59, 0.5));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.var-card:hover {
  border-color: var(--accent-blue, #3b82f6);
  background: var(--bg-card-hover, rgba(30, 41, 59, 0.8));
}

.var-card.active {
  border-color: var(--accent-blue, #3b82f6);
  background: rgba(59, 130, 246, 0.1);
}

.var-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.var-name {
  font-weight: 600;
  color: var(--text-primary, #e2e8f0);
  font-size: 1.05rem;
}

.var-type {
  font-size: 0.75rem;
  padding: 0.2rem 0.5rem;
  background: var(--bg-darker, rgba(0, 0, 0, 0.2));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 4px;
  color: var(--accent-cyan, #06b6d4);
  text-transform: uppercase;
}

.var-desc {
  font-size: 0.85rem;
  color: var(--text-secondary, #94a3b8);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.load-more-btn {
  margin: 1rem 0;
  padding: 0.75rem;
  background: var(--bg-darker, rgba(0, 0, 0, 0.2));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  color: var(--text-primary, #e2e8f0);
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background 0.2s;
}

.load-more-btn:hover {
  background: var(--bg-card-hover, rgba(30, 41, 59, 0.8));
}

.detail-panel {
  flex: 1;
  background: var(--bg-panel, rgba(15, 23, 42, 0.6));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 8px;
  overflow-y: auto;
}

.detail-content {
  padding: 2rem;
}

.detail-header {
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
}

.detail-header h2 {
  font-size: 1.8rem;
  margin: 0 0 1rem 0;
  color: var(--text-primary, #e2e8f0);
}

.tags {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.tag {
  font-size: 0.85rem;
  padding: 0.35rem 0.75rem;
  background: var(--bg-darker, rgba(0, 0, 0, 0.2));
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  border-radius: 4px;
  color: var(--text-secondary, #94a3b8);
}

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h3 {
  font-size: 1.1rem;
  color: var(--text-primary, #e2e8f0);
  margin: 0 0 1rem 0;
  font-weight: 600;
}

.desc-text {
  color: var(--text-secondary, #94a3b8);
  line-height: 1.6;
  font-size: 1.05rem;
  margin: 0;
}

.source-info {
  background: var(--bg-darker, rgba(0, 0, 0, 0.2));
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  color: var(--text-secondary, #94a3b8);
  font-family: monospace;
  font-size: 0.95rem;
}

.source-info code {
  color: var(--accent-purple, #8b5cf6);
}

.chip-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.chip {
  padding: 0.4rem 0.8rem;
  border-radius: 16px;
  font-size: 0.85rem;
  font-weight: 500;
}

.package-chip {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.sub-chip {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.text-muted {
  color: var(--text-muted, #64748b);
  font-style: italic;
  margin: 0;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted, #64748b);
  text-align: center;
  padding: 2rem;
}

.empty-state .icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state h3 {
  color: var(--text-secondary, #94a3b8);
  margin: 0 0 0.5rem 0;
}

.empty-state p {
  max-width: 300px;
  margin: 0;
}
</style>
