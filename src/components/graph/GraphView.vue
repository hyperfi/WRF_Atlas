<template>
  <div class="graph-wrapper">
    <!-- Graph Control Bar -->
    <div class="graph-toolbar glass">
      <div class="toolbar-group">
        <span class="toolbar-label">Layout:</span>
        <button 
          v-for="l in layoutOptions" 
          :key="l.id"
          class="tool-btn"
          :class="{ active: currentLayout === l.id }"
          :title="l.description"
          @click="changeLayout(l.id)"
        >
          <span class="btn-text">{{ l.label }}</span>
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <div class="toolbar-group">
        <button class="tool-btn icon-only" title="Zoom in" @click="zoomIn">+</button>
        <button class="tool-btn icon-only" title="Zoom out" @click="zoomOut">−</button>
        <button class="tool-btn icon-only" title="Fit view" @click="fitView">Fit</button>
        <button class="tool-btn icon-only" title="Reset view" @click="resetView">Reset</button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- Quick Search inside Graph -->
      <div class="graph-search">
        <input 
          v-model="graphFilter" 
          type="text" 
          placeholder="Filter nodes..." 
          class="graph-search-input" 
        />
        <span v-if="graphFilter" class="clear-btn" @click="graphFilter = ''">✕</span>
      </div>
    </div>

    <!-- Node Type Legend Bar -->
    <div class="legend-bar glass">
      <div 
        v-for="(color, type) in activeLegendTypes" 
        :key="type"
        class="legend-item"
        :class="{ dimmed: activeTypeFilter && activeTypeFilter !== type }"
        @click="toggleTypeFilter(type)"
      >
        <span class="legend-dot" :style="{ backgroundColor: color }"></span>
        <span class="legend-label">{{ formatTypeName(type) }}</span>
        <span class="legend-count">{{ getNodeCountByType(type) }}</span>
      </div>
      <button v-if="activeTypeFilter" class="reset-filter-btn" @click="activeTypeFilter = null">
        Show All
      </button>
    </div>

    <!-- Cytoscape Container -->
    <div class="graph-container" ref="container"></div>

    <!-- Graph Stats Footer -->
    <div class="graph-footer">
      <span>Nodes: <strong>{{ visibleNodeCount }}</strong></span>
      <span class="footer-dot">•</span>
      <span>Edges: <strong>{{ visibleEdgeCount }}</strong></span>
      <span class="footer-dot" v-if="selectedNodeLabel">•</span>
      <span v-if="selectedNodeLabel" class="selected-label">Selected: <strong>{{ selectedNodeLabel }}</strong></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted, computed } from 'vue'
import cytoscape from 'cytoscape'
import type { GraphNode, GraphEdge } from '@/types/graph'

const props = withDefaults(defineProps<{
  nodes: GraphNode[]
  edges: GraphEdge[]
  layout?: string
}>(), {
  layout: 'tree-tb'
})

const emit = defineEmits<{
  (e: 'node-click', node: GraphNode): void
}>()

const container = ref<HTMLElement | null>(null)
let cy: cytoscape.Core | null = null

const currentLayout = ref(props.layout)
const graphFilter = ref('')
const activeTypeFilter = ref<string | null>(null)
const selectedNodeLabel = ref<string | null>(null)

const layoutOptions = [
  { id: 'tree-tb', label: 'Vertical', description: 'Hierarchical vertical tree layout' },
  { id: 'tree-lr', label: 'Horizontal', description: 'Hierarchical horizontal tree layout' },
  { id: 'cose', label: 'Force', description: 'Force-directed layout' },
  { id: 'circle', label: 'Circle', description: 'Circular layout' },
  { id: 'grid', label: 'Grid', description: 'Grid matrix layout' },
]

const nodeColors: Record<string, string> = {
  program: '#b96f6f',
  module: '#887ba8',
  subroutine: '#5f91ad',
  function: '#5e9b98',
  driver: '#8c82b0',
  namelist_option: '#b58c4b',
  registry_package: '#4f9778',
  state_variable: '#8a74a6',
  source_file: '#66766f',
  physical_process: '#5b9185',
  phase: '#81719a',
}

const nodeIcons: Record<string, string> = {
  program: 'PROGRAM',
  module: 'MODULE',
  subroutine: 'ROUTINE',
  function: 'FUNCTION',
  driver: 'DRIVER',
  namelist_option: 'NAMELIST',
  registry_package: 'PACKAGE',
  state_variable: 'FIELD',
  source_file: 'SOURCE',
  physical_process: 'PROCESS',
  phase: 'PHASE',
}

const edgeLabels: Record<string, string> = {
  SELECTS: 'selects',
  DISPATCHES_THROUGH: 'symbolic join',
  CALLS: 'calls',
  SELECTED_BY: 'selected by',
  ACTIVE_WHEN: 'active when',
  DEFINED_IN: 'defined in',
}

const formatTypeName = (type: string) => {
  return type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())
}

const getNodeCountByType = (type: string) => {
  return props.nodes.filter(n => n.type === type).length
}

const activeLegendTypes = computed(() => {
  const presentTypes = new Set(props.nodes.map(n => n.type))
  const result: Record<string, string> = {}
  for (const [type, color] of Object.entries(nodeColors)) {
    if (presentTypes.has(type)) {
      result[type] = color
    }
  }
  return result
})

const visibleNodeCount = computed(() => {
  if (!cy) return props.nodes.length
  return cy.nodes(':visible').length
})

const visibleEdgeCount = computed(() => {
  if (!cy) return props.edges.length
  return cy.edges(':visible').length
})

// Build Cytoscape Stylesheet with enhanced visibility
const style: cytoscape.Stylesheet[] = [
  {
    selector: 'node',
    style: {
      'label': 'data(displayLabel)',
      'color': '#ffffff',
      'text-valign': 'center',
      'text-halign': 'center',
      'font-size': '13px',
      'font-weight': '600' as any,
      'font-family': 'Cascadia Code, Consolas, monospace',
      'text-outline-width': 0,
      'width': 'label',
      'height': 'label',
      'padding': '16px',
      'shape': 'round-rectangle',
      'background-color': '#3b82f6',
      'border-width': 2,
      'border-color': '#8ba096',
      'text-max-width': '220px',
      'text-wrap': 'wrap',
      'transition-property': 'background-color, border-color, border-width, opacity',
      'transition-duration': 250,
      'shadow-opacity': 0,
    }
  },
  ...Object.entries(nodeColors).map(([type, color]) => ({
    selector: `node[type="${type}"]`,
    style: {
      'background-color': color,
      'border-color': color,
      'border-opacity': 0.4,
    } as any
  })),
  {
    selector: 'node[type="driver"]',
    style: {
      'shape': 'round-rectangle',
      'padding': '15px',
      'border-width': 2,
      'border-color': '#a897c4',
    } as any
  },
  {
    selector: 'node[type="namelist_option"]',
    style: {
      'shape': 'round-rectangle',
      'border-width': 2,
      'border-color': '#d4a85f',
    } as any
  },
  {
    selector: 'node[type="registry_package"]',
    style: {
      'shape': 'round-rectangle',
      'border-width': 2,
      'border-color': '#62ad8c',
    } as any
  },
  {
    selector: 'node[type="physical_process"]',
    style: {
      'shape': 'ellipse',
      'padding': '20px',
      'border-width': 3,
      'border-color': '#2dd4bf',
    } as any
  },
  {
    selector: 'edge',
    style: {
      'width': 1.5,
      'line-color': '#52655c',
      'target-arrow-color': '#71867c',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 0.8,
      'curve-style': 'bezier',
      'label': 'data(label)',
      'font-size': '10px',
      'font-weight': '600' as any,
      'color': '#b9c8c0',
      'text-background-opacity': 1,
      'text-background-color': '#0a1311',
      'text-background-padding': '4px',
      'text-background-shape': 'round-rectangle',
      'text-rotation': 'autorotate',
      'transition-property': 'line-color, target-arrow-color, width, opacity',
      'transition-duration': 250,
    }
  },
  {
    selector: 'edge[type="CALLS"]',
    style: {
      'line-color': '#5f91ad',
      'target-arrow-color': '#5f91ad',
      'width': 2.5,
    } as any
  },
  {
    selector: 'edge[type="SELECTS"]',
    style: {
      'line-color': '#b58c4b',
      'target-arrow-color': '#b58c4b',
    } as any
  },
  {
    selector: 'edge[type="DISPATCHES_THROUGH"]',
    style: {
      'line-color': '#b58c4b',
      'target-arrow-color': '#b58c4b',
      'line-style': 'dotted',
    } as any
  },
  {
    selector: 'edge[type="SELECTED_BY"]',
    style: {
      'line-color': 'rgba(245, 158, 11, 0.8)',
      'target-arrow-color': '#f59e0b',
      'line-style': 'dashed',
    } as any
  },
  {
    selector: 'edge[type="ACTIVE_WHEN"]',
    style: {
      'line-color': 'rgba(16, 185, 129, 0.8)',
      'target-arrow-color': '#10b981',
      'width': 3.5,
    } as any
  },
  {
    selector: 'edge[type="DEFINED_IN"]',
    style: {
      'line-color': 'rgba(100, 116, 139, 0.4)',
      'target-arrow-color': '#64748b',
      'line-style': 'dotted',
    } as any
  },
  {
    selector: 'node:selected',
    style: {
      'border-width': 5,
      'border-color': '#ffffff',
      'border-opacity': 1,
      'shadow-blur': 25,
      'shadow-color': '#ffffff',
      'shadow-opacity': 0.8,
    }
  },
  {
    selector: '.dimmed',
    style: {
      'opacity': 0.15,
    }
  },
  {
    selector: '.highlighted',
    style: {
      'border-width': 4,
      'border-color': '#fbbf24',
      'opacity': 1,
    }
  }
]

onMounted(() => {
  if (!container.value) return

  cy = cytoscape({
    container: container.value,
    elements: [],
    style,
    layout: { name: 'preset' },
    wheelSensitivity: 0.25,
    minZoom: 0.15,
    maxZoom: 3.5,
  })

  cy.on('tap', 'node', (evt) => {
    const nodeData = evt.target.data()
    selectedNodeLabel.value = nodeData.label
    const node = props.nodes.find(n => n.id === nodeData.id)
    if (node) emit('node-click', node)
  })

  cy.on('tap', (evt) => {
    if (evt.target === cy) {
      selectedNodeLabel.value = null
    }
  })

  updateGraph()
})

const changeLayout = (layoutId: string) => {
  currentLayout.value = layoutId
  runLayout()
}

const runLayout = () => {
  if (!cy) return

  const layoutId = currentLayout.value || 'tree-tb'
  let layoutOpts: any = {
    name: 'breadthfirst',
    animate: true,
    animationDuration: 400,
    padding: 40,
  }

  if (layoutId === 'tree-tb') {
    layoutOpts = {
      name: 'breadthfirst',
      directed: true,
      circle: false,
      grid: false,
      maximal: true,
      spacingFactor: 1.2,
      padding: 70,
      animate: true,
      animationDuration: 400,
    }
  } else if (layoutId === 'tree-lr') {
    // For horizontal tree, calculate breadthfirst and transpose x/y
    layoutOpts = {
      name: 'breadthfirst',
      directed: true,
      circle: false,
      grid: false,
      maximal: true,
      spacingFactor: 1.3,
      padding: 70,
      animate: true,
      animationDuration: 400,
      transform: (node: any, pos: { x: number; y: number }) => ({
        x: pos.y * 1.25,
        y: pos.x
      })
    }
  } else if (layoutId === 'cose') {
    layoutOpts = {
      name: 'cose',
      animate: true,
      animationDuration: 500,
      nodeRepulsion: () => 12000,
      idealEdgeLength: () => 140,
      edgeElasticity: () => 100,
      nestingFactor: 1.2,
      gravity: 0.2,
      numIter: 1000,
      padding: 50,
    }
  } else if (layoutId === 'circle') {
    layoutOpts = {
      name: 'circle',
      animate: true,
      animationDuration: 400,
      padding: 50,
    }
  } else if (layoutId === 'grid') {
    layoutOpts = {
      name: 'grid',
      animate: true,
      animationDuration: 400,
      padding: 50,
    }
  }

  // Fit only after Cytoscape has committed the final animated positions.
  // Fitting immediately after layout.run() used the transient starting
  // positions and left small Namelist Lab paths almost unreadably zoomed out.
  cy.one('layoutstop', () => {
    requestAnimationFrame(() => {
      cy?.resize()
      cy?.fit(undefined, 70)
      if (cy && cy.zoom() > 1.35) {
        cy.zoom(1.35)
        cy.center()
      }
    })
  })
  cy.layout(layoutOpts).run()
}

const updateGraph = () => {
  if (!cy || !props.nodes.length) return

  const nodeIds = new Set(props.nodes.map(n => n.id))
  const validEdges = props.edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))

  const elements: cytoscape.ElementDefinition[] = [
    ...props.nodes.map(n => {
      const icon = nodeIcons[n.type] || ''
      return {
        data: {
          id: n.id,
          label: n.label,
          displayLabel: `${icon}\n${n.label}`,
          type: n.type,
          ...n.data
        },
        group: 'nodes' as const,
      }
    }),
    ...validEdges.map((e, i) => ({
      data: {
        id: `e-${e.source}-${e.target}-${e.type}-${i}`,
        source: e.source,
        target: e.target,
        label: edgeLabels[e.type] || e.type.toLowerCase().replaceAll('_', ' '),
        type: e.type,
        confidence: e.data?.confidence,
      },
      group: 'edges' as const,
    }))
  ]

  cy.elements().remove()

  if (elements.length === 0) return

  cy.add(elements)
  runLayout()
  applyFilters()
}

const applyFilters = () => {
  if (!cy) return

  const filterText = graphFilter.value.trim().toLowerCase()
  const typeFilter = activeTypeFilter.value

  cy.batch(() => {
    cy?.nodes().forEach(node => {
      const nodeData = node.data()
      const matchesText = !filterText || nodeData.label.toLowerCase().includes(filterText) || nodeData.id.toLowerCase().includes(filterText)
      const matchesType = !typeFilter || nodeData.type === typeFilter

      if (matchesText && matchesType) {
        node.removeClass('dimmed')
      } else {
        node.addClass('dimmed')
      }
    })

    cy?.edges().forEach(edge => {
      const source = edge.source()
      const target = edge.target()
      if (source.hasClass('dimmed') || target.hasClass('dimmed')) {
        edge.addClass('dimmed')
      } else {
        edge.removeClass('dimmed')
      }
    })
  })
}

const toggleTypeFilter = (type: string) => {
  activeTypeFilter.value = activeTypeFilter.value === type ? null : type
  applyFilters()
}

const zoomIn = () => {
  if (!cy) return
  cy.zoom({
    level: cy.zoom() * 1.25,
    renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 }
  })
}

const zoomOut = () => {
  if (!cy) return
  cy.zoom({
    level: cy.zoom() * 0.8,
    renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 }
  })
}

const fitView = () => {
  if (!cy) return
  cy.resize()
  cy.fit(undefined, 70)
  if (cy.zoom() > 1.35) {
    cy.zoom(1.35)
    cy.center()
  }
}

const resetView = () => {
  if (!cy) return
  graphFilter.value = ''
  activeTypeFilter.value = null
  selectedNodeLabel.value = null
  runLayout()
}

watch([graphFilter, activeTypeFilter], applyFilters)
watch(() => [props.nodes, props.edges], updateGraph, { deep: true })
watch(() => props.layout, (newVal) => {
  if (newVal) {
    currentLayout.value = newVal
    runLayout()
  }
})

onUnmounted(() => {
  if (cy) cy.destroy()
})
</script>

<style scoped>
.graph-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Toolbar */
.graph-toolbar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem;
  margin: 0.75rem;
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 10;
  border-radius: 6px;
  flex-wrap: wrap;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.toolbar-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-right: 0.25rem;
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.28rem 0.5rem;
  background: var(--bg-inset);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 0.65rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tool-btn:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.tool-btn.active {
  background: var(--accent-soft);
  color: var(--accent-emerald);
  border-color: var(--border-focus);
  font-weight: 600;
}

.tool-btn.icon-only {
  padding: 0.35rem 0.5rem;
  font-family: var(--font-mono);
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: var(--border-subtle);
}

.graph-search {
  margin-left: auto;
  position: relative;
  display: flex;
  align-items: center;
}

.graph-search-input {
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 0.3rem 1.8rem 0.3rem 0.6rem;
  color: var(--text-primary);
  font-size: 0.75rem;
  outline: none;
  width: 150px;
  transition: width 0.2s, border-color 0.2s;
}

.graph-search-input:focus {
  width: 200px;
  border-color: var(--accent-blue);
}

.clear-btn {
  position: absolute;
  right: 0.5rem;
  font-size: 0.7rem;
  color: var(--text-muted);
  cursor: pointer;
}

/* Legend bar */
.legend-bar {
  position: absolute;
  bottom: 2.25rem;
  left: 0.75rem;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.4rem 0.85rem;
  border-radius: 5px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.62rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: opacity 0.2s;
}

.legend-item.dimmed {
  opacity: 0.3;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-label {
  font-weight: 500;
}

.legend-count {
  font-size: 0.65rem;
  opacity: 0.6;
  background: rgba(255, 255, 255, 0.1);
  padding: 0.05rem 0.3rem;
  border-radius: 4px;
}

.reset-filter-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  color: var(--text-muted);
  font-size: 0.7rem;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  cursor: pointer;
}

.reset-filter-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.2);
}

/* Container */
.graph-container {
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 450px;
  background-color: var(--bg-inset);
  background-image: radial-gradient(circle, var(--border-subtle) 1px, transparent 1px);
  background-size: 22px 22px;
}

/* Footer */
.graph-footer {
  position: absolute;
  bottom: 0.5rem;
  right: 0.75rem;
  z-index: 10;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.7rem;
  color: var(--text-muted);
  background: var(--bg-inset);
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  backdrop-filter: blur(8px);
}

.footer-dot {
  opacity: 0.4;
}

.selected-label {
  color: var(--accent-amber);
}
</style>
