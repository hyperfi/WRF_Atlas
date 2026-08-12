<template>
  <header class="app-header">
    <div class="header-left">
      <button class="icon-button" type="button" title="Toggle navigation" @click="uiStore.toggleSidebar">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5.5h14M3 10h14M3 14.5h14" /></svg>
      </button>
      <div class="location">
        <span class="location-root">Atlas</span>
        <span class="location-separator">/</span>
        <span class="location-page">{{ currentSection }}</span>
      </div>
    </div>

    <div class="header-center">
      <button class="search-trigger" type="button" @click="$emit('open-search')">
        <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="4.5"/><path d="m12 12 4 4"/></svg>
        <span>Search symbols, options, fields</span>
        <kbd>Ctrl K</kbd>
      </button>
    </div>

    <div class="header-right">
      <div class="local-source-control" :class="{ connected: localSource.connected }">
        <button
          type="button"
          :title="localSource.connected
            ? `Reading source directly from ${localSource.folderName}; click to disconnect`
            : localSource.supported
              ? 'Choose a local WRF source folder for faster browsing'
              : 'Direct folder access requires Chrome or Edge on localhost or HTTPS'"
          @click="toggleLocalSource"
        >
          <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M2.5 5.5h5l1.5 2h8.5v7.5h-15z"/><path d="M2.5 7.5h15"/></svg>
          <span>{{ localSource.connected ? localSource.folderName : 'Local folder' }}</span>
          <i v-if="localSource.connected"></i>
        </button>
        <p v-if="localSource.error" role="status">{{ localSource.error }}</p>
      </div>
      <label class="snapshot-picker" title="Indexed WRF source snapshot">
        <span>Source</span>
        <select :value="graphStore.activeSnapshotId || ''" :disabled="graphStore.loading" @change="changeSnapshot">
          <option v-for="snapshot in graphStore.snapshots" :key="snapshot.id" :value="snapshot.id">{{ snapshot.label }}</option>
        </select>
      </label>
      <div class="mode-toggle" aria-label="Information density">
        <button :class="{ active: uiStore.mode === 'learning' }" @click="uiStore.setMode('learning')">Learning</button>
        <button :class="{ active: uiStore.mode === 'researcher' }" @click="uiStore.setMode('researcher')">Researcher</button>
      </div>
      <button class="icon-button" type="button" :title="`Use ${uiStore.theme === 'dark' ? 'light' : 'dark'} theme`" @click="uiStore.toggleTheme">
        <svg v-if="uiStore.theme === 'dark'" viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="3"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.3 4.3l1.4 1.4M14.3 14.3l1.4 1.4M15.7 4.3l-1.4 1.4M5.7 14.3l-1.4 1.4"/></svg>
        <svg v-else viewBox="0 0 20 20" aria-hidden="true"><path d="M16.5 12.4A6.8 6.8 0 0 1 7.6 3.5 6.8 6.8 0 1 0 16.5 12.4Z"/></svg>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUiStore } from '@/stores/uiStore'
import { useGraphStore } from '@/stores/graphStore'
import { useLocalSourceStore } from '@/stores/localSourceStore'

const uiStore = useUiStore()
const graphStore = useGraphStore()
const localSource = useLocalSourceStore()
const route = useRoute()
defineEmits(['open-search'])

localSource.restore()

const toggleLocalSource = async () => {
  if (localSource.connected) await localSource.disconnect()
  else await localSource.chooseFolder()
}

const changeSnapshot = async (event: Event) => {
  await graphStore.switchSnapshot((event.target as HTMLSelectElement).value)
}

const labels: Record<string, string> = {
  '/': 'Overview',
  '/namelist': 'Namelist Lab',
  '/execution': 'Execution Map',
  '/physics': 'Physics',
  '/variables': 'Variables',
  '/compare': 'Compare releases',
  '/source': 'Source',
  '/tours': 'Guided Tours',
}

const currentSection = computed(() => {
  const base = '/' + route.path.split('/').filter(Boolean)[0]
  return labels[route.path] || labels[base] || 'Explore'
})
</script>

<style scoped>
.app-header {
  position: relative;
  z-index: 90;
  display: grid;
  height: var(--header-height);
  flex: 0 0 auto;
  grid-template-columns: 1fr minmax(280px, 440px) 1fr;
  align-items: center;
  padding: 0 18px;
  background: color-mix(in srgb, var(--bg-raised) 94%, transparent);
  border-bottom: 1px solid var(--border-subtle);
}

.header-left,
.header-right { display: flex; align-items: center; gap: 10px; }
.header-right { justify-content: flex-end; }
.header-center { display: flex; justify-content: center; }

.icon-button {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  color: var(--text-secondary);
  cursor: pointer;
}
.icon-button:hover { background: var(--bg-surface-hover); border-color: var(--border-subtle); color: var(--text-primary); }
.icon-button svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.5; }

.location { display: flex; align-items: center; gap: 8px; font-size: 0.78rem; }
.location-root { color: var(--text-muted); }
.location-separator { color: var(--border-strong); }
.location-page { color: var(--text-secondary); font-weight: 560; }

.search-trigger {
  display: flex;
  width: 100%;
  height: 34px;
  align-items: center;
  gap: 9px;
  padding: 0 9px 0 11px;
  background: var(--bg-inset);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.76rem;
  text-align: left;
}
.search-trigger:hover { border-color: var(--border-strong); color: var(--text-secondary); }
.search-trigger svg { width: 15px; height: 15px; fill: none; stroke: currentColor; stroke-width: 1.5; }
.search-trigger span { flex: 1; }
kbd { padding: 2px 6px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-muted); font-family: var(--font-mono); font-size: 0.62rem; }
.snapshot-picker { display: flex; align-items: center; gap: 6px; color: var(--text-muted); font-size: .6rem; text-transform: uppercase; letter-spacing: .06em; }.snapshot-picker select { max-width: 170px; height: 30px; padding: 0 24px 0 8px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 5px; color: var(--text-secondary); font-size: .66rem; text-transform: none; letter-spacing: 0; }
.local-source-control { position: relative; }.local-source-control button { display: flex; max-width: 150px; height: 30px; align-items: center; gap: 6px; padding: 0 8px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 5px; color: var(--text-muted); cursor: pointer; font-size: .66rem; }.local-source-control button:hover { border-color: var(--border-strong); color: var(--text-secondary); }.local-source-control svg { width: 14px; flex: 0 0 auto; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.3; }.local-source-control span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.local-source-control i { width: 6px; height: 6px; flex: 0 0 auto; background: var(--accent-emerald); border-radius: 50%; box-shadow: 0 0 8px color-mix(in srgb, var(--accent-emerald) 65%, transparent); }.local-source-control.connected button { border-color: color-mix(in srgb, var(--accent-emerald) 40%, var(--border-subtle)); color: var(--text-secondary); }.local-source-control p { position: absolute; top: 34px; right: 0; width: 280px; margin: 0; padding: 8px 10px; background: var(--bg-raised); border: 1px solid var(--border-strong); border-radius: 6px; box-shadow: var(--shadow-lg); color: var(--text-secondary); font-size: .68rem; line-height: 1.45; text-transform: none; }

.mode-toggle { display: flex; padding: 2px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 6px; }
.mode-toggle button { padding: 4px 9px; background: transparent; border: 0; border-radius: 4px; color: var(--text-muted); cursor: pointer; font-size: 0.7rem; }
.mode-toggle button.active { background: var(--bg-surface-hover); color: var(--text-primary); box-shadow: inset 0 0 0 1px var(--border-subtle); }

@media (max-width: 950px) {
  .app-header { grid-template-columns: auto 1fr auto; }
  .location { display: none; }
  .header-center { padding: 0 12px; }
  .search-trigger span { display: none; }
  .mode-toggle button { padding-inline: 7px; }
  .snapshot-picker span { display: none; }
  .snapshot-picker select { max-width: 125px; }
  .local-source-control span { display: none; }
}
</style>
