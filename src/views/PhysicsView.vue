<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/graphStore'
import { useConfigStore } from '@/stores/configStore'
import { useUiStore } from '@/stores/uiStore'
import { PHYSICS_CATEGORIES, type PhysicsCategory } from '@/types/graph'

const route = useRoute()
const router = useRouter()
const graphStore = useGraphStore()
const configStore = useConfigStore()
const uiStore = useUiStore()

const categories = Object.entries(PHYSICS_CATEGORIES).map(([key, value]) => ({
  id: key as PhysicsCategory,
  ...value
}))

const selectedCategoryId = ref<PhysicsCategory | null>(null)
const selectedSchemeValue = ref<string | null>(null)

onMounted(() => {
  const cat = route.params.category as PhysicsCategory
  if (cat && categories.find(c => c.id === cat)) {
    selectedCategoryId.value = cat
  } else {
    selectedCategoryId.value = categories[0].id
  }
})

watch(() => selectedCategoryId.value, (newVal) => {
  if (newVal && newVal !== route.params.category) {
    router.push(`/physics/${newVal}`)
  }
  selectedSchemeValue.value = null
})

watch(() => route.params.category, (newCat) => {
  if (newCat && newCat !== selectedCategoryId.value) {
    const cat = newCat as PhysicsCategory
    if (categories.find(c => c.id === cat)) {
      selectedCategoryId.value = cat
    }
  }
})

const currentCategory = computed(() => {
  return categories.find(c => c.id === selectedCategoryId.value)
})

const availableSchemes = computed(() => {
  if (!currentCategory.value || !graphStore.isLoaded) return []
  return graphStore.getPackagesForNamelist(currentCategory.value.namelist)
})

const activeSchemeValue = computed(() => {
  if (!currentCategory.value) return null
  return String(configStore.getConfig(currentCategory.value.namelist))
})

const selectScheme = (value: string) => {
  selectedSchemeValue.value = value === selectedSchemeValue.value ? null : value
}

const activateScheme = (value: string) => {
  if (currentCategory.value) {
    configStore.setConfig(currentCategory.value.namelist, parseInt(value))
  }
}

const selectedSchemeDetails = computed(() => {
  if (!selectedSchemeValue.value || !currentCategory.value) return null
  const subroutines = graphStore.getActiveSubroutines(currentCategory.value.namelist, selectedSchemeValue.value)
  return { subroutines }
})
</script>

<template>
  <div class="physics-view glass-panel">
    <div class="header">
      <div class="header-main">
        <div>
          <h2>Physics Explorer</h2>
          <p class="subtitle">Browse physical parameterization schemes by category</p>
        </div>
        <div class="mode-badge-wrapper">
          <span class="mode-badge" :class="uiStore.mode">
            {{ uiStore.mode === 'learning' ? '🌱 Learning Mode' : '🔬 Researcher Mode' }}
          </span>
        </div>
      </div>
    </div>

    <div class="layout" v-if="graphStore.isLoaded">
      <!-- Categories Sidebar -->
      <div class="categories-list">
        <button 
          v-for="cat in categories" 
          :key="cat.id"
          class="category-btn"
          :class="{ active: cat.id === selectedCategoryId }"
          :style="{ '--cat-color': cat.color }"
          @click="selectedCategoryId = cat.id"
        >
          <span class="icon">{{ cat.icon }}</span>
          <span class="label">{{ cat.label }}</span>
        </button>
      </div>

      <!-- Schemes Grid -->
      <div class="schemes-content" v-if="currentCategory">
        <div class="category-header">
          <span class="icon" style="font-size: 2rem;">{{ currentCategory.icon }}</span>
          <div>
            <h3 style="margin: 0 0 0.25rem 0; font-size: 1.5rem;">{{ currentCategory.label }} Schemes</h3>
            <span class="namelist-badge" v-if="uiStore.mode === 'researcher'">{{ currentCategory.namelist }}</span>
            <span class="namelist-badge learning" v-else>Namelist Selector: {{ currentCategory.namelist }}</span>
          </div>
        </div>

        <div class="schemes-grid">
          <div 
            v-for="scheme in availableSchemes" 
            :key="scheme.value"
            class="scheme-card"
            :class="{ 
              active: scheme.value === activeSchemeValue,
              expanded: scheme.value === selectedSchemeValue
            }"
            @click="selectScheme(scheme.value)"
          >
            <div class="scheme-header">
              <span class="value-badge">{{ scheme.value }}</span>
              <h4>{{ scheme.packageName }}</h4>
            </div>
            
            <p class="description">{{ scheme.description || 'No description available' }}</p>

            <!-- Learning Mode Metadata -->
            <div v-if="uiStore.mode === 'learning'" class="learning-box">
              <div class="meta-item">
                <span class="meta-lbl">Role:</span> {{ currentCategory.label }} parameterization
              </div>
            </div>

            <!-- Researcher Mode Metadata -->
            <div v-else-if="scheme.node?.data?.state_vars?.length" class="scheme-meta">
               <strong>State Variables:</strong> {{ scheme.node.data.state_vars.join(', ') }}
            </div>

            <div class="actions">
              <button 
                class="activate-btn" 
                v-if="scheme.value !== activeSchemeValue"
                @click.stop="activateScheme(scheme.value)"
              >
                Set Active
              </button>
              <span class="active-label" v-else>Currently Active</span>
            </div>

            <!-- Details when selected -->
            <div class="scheme-details" v-if="scheme.value === selectedSchemeValue" @click.stop>
              <h5>{{ uiStore.mode === 'learning' ? '🌱 How This Scheme Executes' : '🔬 Subroutines & Source Files' }}</h5>
              <div v-if="selectedSchemeDetails && selectedSchemeDetails.subroutines.length > 0">
                 <div v-for="(sub, i) in selectedSchemeDetails.subroutines" :key="i" class="sub-item">
                    <div style="margin-bottom: 0.25rem;">
                      <span class="text-muted">Source:</span> 
                      <span class="source-file" v-if="sub.evidence && sub.evidence.length > 0">{{ sub.evidence[0].path }}</span>
                      <span class="source-file" v-else-if="sub.node?.data?.file">{{ sub.node.data.file }}</span>
                      <span v-else>Unknown</span>
                    </div>
                    <div>
                      <span class="text-muted">Subroutine:</span> <span class="sub-name">{{ sub.node?.label }}</span>
                    </div>
                 </div>
              </div>
              <div v-else class="text-muted" style="font-size: 0.9rem;">No implementation details found.</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="loading-state">
      <div class="spinner"></div>
      Loading graph data...
    </div>
  </div>
</template>

<style scoped>
.physics-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.header { 
  padding: 1.5rem 2rem; 
  border-bottom: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
}
.header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header h2 {
  margin: 0 0 0.25rem 0;
  color: #e2e8f0;
}
.subtitle { 
  color: #94a3b8; 
  margin: 0; 
  font-size: 0.95rem;
}
.mode-badge {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
}
.mode-badge.learning {
  background: rgba(52, 211, 153, 0.2);
  color: #34d399;
}
.mode-badge.researcher {
  background: rgba(96, 165, 250, 0.2);
  color: #60a5fa;
}

.layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.categories-list {
  width: 280px;
  border-right: 1px solid var(--border-subtle, rgba(255,255,255,0.1));
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  gap: 0.75rem;
  overflow-y: auto;
  background: rgba(10, 14, 39, 0.3);
}

.category-btn {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1.25rem;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  color: #cbd5e1;
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: left;
  font-size: 1rem;
  font-weight: 500;
}
.category-btn:hover {
  background: rgba(255,255,255,0.08);
  border-color: var(--cat-color);
  color: #f8fafc;
}
.category-btn.active {
  background: rgba(255,255,255,0.1);
  border-color: var(--cat-color);
  box-shadow: 0 0 12px var(--cat-color);
  color: #fff;
}
.category-btn .icon {
  font-size: 1.25rem;
}

.schemes-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  background: linear-gradient(to bottom, rgba(10, 14, 39, 0.1), transparent);
}

.category-header {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  margin-bottom: 2rem;
  color: #f8fafc;
}
.namelist-badge {
  background: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9rem;
  border: 1px solid rgba(59, 130, 246, 0.3);
}
.namelist-badge.learning {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border-color: rgba(16, 185, 129, 0.3);
  font-family: var(--font-sans);
}

.schemes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 1.5rem;
}

.scheme-card {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  gap: 1rem;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}
.scheme-card:hover {
  border-color: rgba(255, 255, 255, 0.3);
  transform: translateY(-2px);
  background: rgba(30, 41, 59, 0.7);
}
.scheme-card.active {
  border-color: #10b981;
  box-shadow: 0 0 15px rgba(16, 185, 129, 0.15), inset 0 0 0 1px #10b981;
}

.scheme-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.scheme-header h4 { 
  margin: 0; 
  font-size: 1.15rem; 
  color: #f8fafc;
}
.value-badge {
  background: rgba(255,255,255,0.1);
  color: #e2e8f0;
  font-family: monospace;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
  font-weight: bold;
  font-size: 0.9rem;
  min-width: 2.5rem;
  text-align: center;
}

.description {
  color: #94a3b8;
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0;
}

.learning-box {
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.2);
  padding: 0.6rem 0.8rem;
  border-radius: 6px;
  font-size: 0.85rem;
  color: #a7f3d0;
}

.meta-lbl {
  font-weight: bold;
  color: #34d399;
}

.scheme-meta {
  font-size: 0.9rem;
  color: #64748b;
  background: rgba(0,0,0,0.2);
  padding: 0.75rem;
  border-radius: 6px;
}

.actions {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding-top: 1rem;
  border-top: 1px dashed rgba(255,255,255,0.1);
}

.activate-btn {
  background: transparent;
  border: 1px solid #10b981;
  color: #10b981;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.9rem;
  font-weight: 500;
}
.activate-btn:hover {
  background: #10b981;
  color: #022c22;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
}

.active-label {
  color: #10b981;
  font-weight: 600;
  font-size: 0.95rem;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  text-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
}
.active-label::before {
  content: '✓';
  font-weight: bold;
}

.scheme-details {
  border-top: 1px solid rgba(255,255,255,0.1);
  padding-top: 1.25rem;
  margin-top: 0.5rem;
  animation: slideDown 0.3s ease;
}
.scheme-details h5 {
  margin: 0 0 1rem 0;
  color: #e2e8f0;
  font-size: 1rem;
}
.sub-item {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.05);
  padding: 0.85rem;
  border-radius: 6px;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}
.text-muted {
  color: #64748b;
}
.source-file {
  font-family: monospace;
  color: #60a5fa;
  background: rgba(96, 165, 250, 0.1);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}
.sub-name {
  font-weight: bold;
  color: #f8fafc;
}

.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  gap: 1rem;
  font-size: 1.1rem;
}
.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255,255,255,0.1);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
