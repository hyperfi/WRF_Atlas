<template>
  <div class="layout-container" :class="uiStore.theme + '-theme'">
    <AppSidebar />
    
    <main class="main-content">
      <AppHeader @open-search="isSearchOpen = true" />
      
      <div class="view-container">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <SearchPalette :is-open="isSearchOpen" @close="isSearchOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import SearchPalette from '@/components/search/SearchPalette.vue'
import { useUiStore } from '@/stores/uiStore'
import { useGraphStore } from '@/stores/graphStore'

const uiStore = useUiStore()
const graphStore = useGraphStore()
const isSearchOpen = ref(false)

onMounted(() => {
  graphStore.loadGraph()
  
  // Listen for global search shortcut
  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault()
      isSearchOpen.value = !isSearchOpen.value
    }
  })
})
</script>

<style>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
