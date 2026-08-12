import { defineStore } from 'pinia'
import { ref } from 'vue'

export type AppMode = 'learning' | 'researcher'

export const useUiStore = defineStore('ui', () => {
  const theme = ref<'dark' | 'light'>('dark')
  const mode = ref<AppMode>('learning')
  const sidebarCollapsed = ref(false)
  const activePanels = ref<string[]>([])
  
  const toggleTheme = () => {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    document.documentElement.classList.toggle('light-theme', theme.value === 'light')
  }

  const setMode = (newMode: AppMode) => {
    mode.value = newMode
  }

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return {
    theme,
    mode,
    sidebarCollapsed,
    activePanels,
    toggleTheme,
    setMode,
    toggleSidebar
  }
})
