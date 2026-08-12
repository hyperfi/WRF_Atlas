<template>
  <aside class="app-sidebar" :class="{ collapsed: uiStore.sidebarCollapsed }">
    <div class="sidebar-header">
      <router-link to="/" class="brand" aria-label="WRF Code Atlas home">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 32 32" role="img">
            <path d="M5 20c3.3-7.6 9.2-11.5 18-11.8-4.8 2.3-7.8 5-9.1 8.1 3.4-1.9 7-2.4 10.8-1.7-4.5 1.4-7.7 3.8-9.7 7.2-2.3 3.9-5.6 4.5-10 1.8 2.2-.2 3.9-1.4 5.1-3.5-1.6.6-3.3.6-5.1-.1Z" />
          </svg>
        </span>
        <span v-if="!uiStore.sidebarCollapsed" class="brand-copy">
          <strong>WRF Atlas</strong>
          <small>Source intelligence</small>
        </span>
      </router-link>
    </div>

    <div v-if="!uiStore.sidebarCollapsed" class="nav-section-label">Explore</div>
    <nav class="sidebar-nav" aria-label="Primary navigation">
      <router-link v-for="item in navigation" :key="item.to" :to="item.to" class="nav-item" :title="item.label">
        <span class="nav-glyph" aria-hidden="true">{{ item.glyph }}</span>
        <span v-if="!uiStore.sidebarCollapsed" class="label">{{ item.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <div class="source-status" :title="graphStore.metadata?.source_label || graphStore.metadata?.repository_url || 'Source not loaded'">
        <span class="status-dot" :class="{ ready: graphStore.isLoaded }"></span>
        <span v-if="!uiStore.sidebarCollapsed" class="status-copy">
          <span>{{ graphStore.isLoaded ? `WRF ${graphStore.metadata?.wrf_version}` : 'Loading index' }}</span>
          <small>{{ graphStore.isLoaded ? shortCommit : 'Local source' }}</small>
        </span>
      </div>
      <a
        class="creator-credit"
        href="https://www.dr-abhishek.com"
        target="_blank"
        rel="noopener noreferrer"
        title="Created by Dr. Abhishek"
      >
        <span class="credit-mark" aria-hidden="true">A</span>
        <span v-if="!uiStore.sidebarCollapsed" class="credit-copy">
          <small>Created by</small>
          <strong>Dr. Abhishek</strong>
        </span>
        <svg v-if="!uiStore.sidebarCollapsed" viewBox="0 0 20 20" aria-hidden="true"><path d="M8 5h7v7M15 5 7 13"/><path d="M13 11v4H5V7h4"/></svg>
      </a>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useUiStore } from '@/stores/uiStore'
import { useGraphStore } from '@/stores/graphStore'

const uiStore = useUiStore()
const graphStore = useGraphStore()

const navigation = [
  { to: '/', label: 'Overview', glyph: 'OV' },
  { to: '/namelist', label: 'Namelist Lab', glyph: 'NL' },
  { to: '/execution', label: 'Execution Map', glyph: 'EX' },
  { to: '/physics', label: 'Physics', glyph: 'PH' },
  { to: '/variables', label: 'Variables', glyph: 'VR' },
  { to: '/compare', label: 'Compare', glyph: 'CP' },
  { to: '/source', label: 'Source', glyph: 'SC' },
  { to: '/tours', label: 'Guided Tours', glyph: 'GT' },
]

const shortCommit = computed(() => {
  const commit = graphStore.metadata?.commit
  return commit ? `commit ${commit.slice(0, 7)}` : 'provenance pending'
})
</script>

<style scoped>
.app-sidebar {
  position: relative;
  z-index: 100;
  display: flex;
  width: var(--sidebar-width);
  height: 100vh;
  flex: 0 0 auto;
  flex-direction: column;
  overflow: hidden;
  background: color-mix(in srgb, var(--bg-raised) 96%, transparent);
  border-right: 1px solid var(--border-subtle);
  transition: width 180ms ease;
}

.app-sidebar.collapsed { width: var(--sidebar-collapsed); }

.sidebar-header {
  display: flex;
  height: var(--header-height);
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
}

.brand {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 11px;
  padding: 0 16px;
  color: var(--text-primary);
}

.brand-mark {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  background: var(--accent-soft);
  border: 1px solid color-mix(in srgb, var(--accent-emerald) 40%, var(--border-subtle));
  border-radius: 7px;
}

.brand-mark svg { width: 24px; height: 24px; fill: var(--accent-emerald); }
.brand-copy { display: flex; min-width: 0; flex-direction: column; line-height: 1.15; }
.brand-copy strong { font-size: 0.93rem; letter-spacing: -0.01em; }
.brand-copy small { margin-top: 3px; color: var(--text-muted); font-size: 0.66rem; letter-spacing: 0.04em; }

.nav-section-label {
  padding: 23px 18px 8px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.64rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.sidebar-nav { display: flex; flex: 1; flex-direction: column; gap: 3px; padding: 4px 10px; }
.nav-item {
  position: relative;
  display: flex;
  height: 40px;
  align-items: center;
  gap: 11px;
  padding: 0 10px;
  overflow: hidden;
  color: var(--text-secondary);
  border: 1px solid transparent;
  border-radius: 6px;
  font-size: 0.84rem;
  font-weight: 520;
  white-space: nowrap;
  transition: background 140ms ease, color 140ms ease, border-color 140ms ease;
}

.nav-item:hover { background: var(--bg-surface-hover); color: var(--text-primary); }
.nav-item.router-link-exact-active,
.nav-item.router-link-active {
  background: var(--accent-soft);
  border-color: color-mix(in srgb, var(--accent-emerald) 26%, var(--border-subtle));
  color: var(--text-primary);
}

.nav-item.router-link-active::before {
  position: absolute;
  top: 9px;
  bottom: 9px;
  left: -1px;
  width: 2px;
  background: var(--accent-emerald);
  border-radius: 2px;
  content: '';
}

.nav-glyph {
  width: 25px;
  flex: 0 0 25px;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 0.64rem;
  font-weight: 650;
  letter-spacing: -0.03em;
  text-align: center;
}

.router-link-active .nav-glyph { color: var(--accent-emerald); }

.sidebar-footer { padding: 10px 12px 12px; border-top: 1px solid var(--border-subtle); }
.source-status { display: flex; min-height: 42px; align-items: center; gap: 10px; padding: 6px 8px; }
.status-dot { width: 7px; height: 7px; flex: 0 0 auto; background: var(--text-muted); border-radius: 50%; }
.status-dot.ready { background: var(--accent-emerald); box-shadow: 0 0 0 4px var(--accent-soft); }
.status-copy { display: flex; min-width: 0; flex-direction: column; font-size: 0.75rem; }
.status-copy small { color: var(--text-muted); font-family: var(--font-mono); font-size: 0.64rem; }
.creator-credit { display: flex; min-height: 39px; align-items: center; gap: 9px; padding: 5px 8px; color: var(--text-muted); border: 1px solid transparent; border-radius: 6px; transition: background 140ms ease, border-color 140ms ease, color 140ms ease; }.creator-credit:hover { background: var(--bg-surface-hover); border-color: var(--border-subtle); color: var(--text-primary); }.credit-mark { display: grid; width: 22px; height: 22px; flex: 0 0 auto; place-items: center; border: 1px solid var(--border-strong); border-radius: 50%; color: var(--accent-emerald); font-family: var(--font-mono); font-size: .65rem; font-weight: 700; }.credit-copy { display: flex; min-width: 0; flex: 1; flex-direction: column; line-height: 1.2; }.credit-copy small { color: var(--text-muted); font-size: .56rem; letter-spacing: .07em; text-transform: uppercase; }.credit-copy strong { margin-top: 2px; color: var(--text-secondary); font-size: .7rem; font-weight: 570; }.creator-credit svg { width: 13px; height: 13px; flex: 0 0 auto; fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.3; }
.collapsed .creator-credit { justify-content: center; padding-inline: 0; }
</style>
