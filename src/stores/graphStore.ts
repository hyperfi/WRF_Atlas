import { defineStore } from 'pinia'
import { ref, computed, shallowRef } from 'vue'
import type { KnowledgeGraph, GraphNode, GraphEdge, AtlasSnapshot, SnapshotManifest } from '@/types/graph'

export const useGraphStore = defineStore('graph', () => {
  const graph = shallowRef<KnowledgeGraph | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const snapshots = ref<AtlasSnapshot[]>([])
  const activeSnapshotId = ref<string | null>(null)

  // ── Indexed lookups (built on load) ──
  const nodesById = ref<Map<string, GraphNode>>(new Map())
  const nodesByType = ref<Map<string, GraphNode[]>>(new Map())
  const edgesBySource = ref<Map<string, GraphEdge[]>>(new Map())
  const edgesByTarget = ref<Map<string, GraphEdge[]>>(new Map())
  const edgesByType = ref<Map<string, GraphEdge[]>>(new Map())
  let loadPromise: Promise<void> | null = null
  let manifestPromise: Promise<void> | null = null

  const publicAsset = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\//, '')}`

  const loadSnapshots = async () => {
    if (snapshots.value.length) return
    if (manifestPromise) return manifestPromise
    manifestPromise = (async () => {
      try {
        const res = await fetch(publicAsset('data/snapshots/manifest.json'))
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const manifest: SnapshotManifest = await res.json()
        snapshots.value = manifest.snapshots
        if (import.meta.env.DEV) {
          const localFile = 'data/local/qwrf-v4.7.1.json'
          const localResponse = await fetch(publicAsset(localFile), { method: 'HEAD' })
          const localContentType = localResponse.headers.get('content-type') || ''
          if (localResponse.ok && localContentType.includes('application/json')) {
            snapshots.value = [{
              id: 'qwrf-v4.7.1-local', label: 'QWRF 4.7.1 local',
              description: 'Protected local research checkout with Morrison instrumentation.',
              file: localFile, version: '4.7.1', commit: 'local',
              sourceMode: 'local', repositoryUrl: 'https://github.com/wrf-model/WRF', public: false,
            }, ...snapshots.value]
          }
        }
        const saved = localStorage.getItem('wrf-atlas-snapshot')
        activeSnapshotId.value = manifest.snapshots.some(item => item.id === saved)
          ? saved
          : manifest.defaultSnapshot
      } catch {
        snapshots.value = [{
          id: 'legacy-local', label: 'Local WRF snapshot', description: 'Legacy generated graph',
          file: 'data/wrf-knowledge-graph.json', version: 'unknown', commit: 'unknown',
          sourceMode: 'local', public: false,
        }]
        activeSnapshotId.value = 'legacy-local'
      } finally {
        manifestPromise = null
      }
    })()
    return manifestPromise
  }

  const indexGraph = (data: KnowledgeGraph) => {
    graph.value = data

    const _byId = new Map<string, GraphNode>()
    const _byType = new Map<string, GraphNode[]>()
    for (const node of data.nodes) {
      _byId.set(node.id, node)
      const list = _byType.get(node.type) || []
      list.push(node)
      _byType.set(node.type, list)
    }
    nodesById.value = _byId
    nodesByType.value = _byType

    const _bySrc = new Map<string, GraphEdge[]>()
    const _byTgt = new Map<string, GraphEdge[]>()
    const _byEType = new Map<string, GraphEdge[]>()
    for (const edge of data.edges) {
      const slist = _bySrc.get(edge.source) || []
      slist.push(edge)
      _bySrc.set(edge.source, slist)
      const tlist = _byTgt.get(edge.target) || []
      tlist.push(edge)
      _byTgt.set(edge.target, tlist)
      const etlist = _byEType.get(edge.type) || []
      etlist.push(edge)
      _byEType.set(edge.type, etlist)
    }
    edgesBySource.value = _bySrc
    edgesByTarget.value = _byTgt
    edgesByType.value = _byEType
  }

  const loadGraph = async (requestedSnapshot?: string) => {
    await loadSnapshots()
    const targetId = requestedSnapshot || activeSnapshotId.value || snapshots.value[0]?.id
    if (!targetId) throw new Error('No Atlas snapshots are configured')
    if (graph.value && activeSnapshotId.value === targetId) return
    if (loadPromise) return loadPromise

    loadPromise = (async () => {
      loading.value = true
      error.value = null
      try {
        const snapshot = snapshots.value.find(item => item.id === targetId)
        if (!snapshot) throw new Error(`Unknown Atlas snapshot: ${targetId}`)
        const res = await fetch(publicAsset(snapshot.file))
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data: KnowledgeGraph = await res.json()
        indexGraph(data)
        activeSnapshotId.value = targetId
        localStorage.setItem('wrf-atlas-snapshot', targetId)

        console.log(`[WRF Atlas] Loaded ${data.nodes.length} nodes, ${data.edges.length} edges`)
      } catch (e: any) {
        error.value = e.message || 'Failed to load knowledge graph'
        console.error('[WRF Atlas] Load failed:', e)
      } finally {
        loading.value = false
        loadPromise = null
      }
    })()

    return loadPromise
  }

  const switchSnapshot = async (snapshotId: string) => {
    if (snapshotId === activeSnapshotId.value && graph.value) return
    if (loadPromise) await loadPromise
    graph.value = null
    await loadGraph(snapshotId)
  }

  // ── Fast getters ──

  const getNodeById = (id: string): GraphNode | undefined => {
    return nodesById.value.get(id)
  }

  const getNodesByType = (type: string): GraphNode[] => {
    return nodesByType.value.get(type) || []
  }

  const getEdgesFrom = (sourceId: string): GraphEdge[] => {
    return edgesBySource.value.get(sourceId) || []
  }

  const getEdgesTo = (targetId: string): GraphEdge[] => {
    return edgesByTarget.value.get(targetId) || []
  }

  const getEdgesOfType = (type: string): GraphEdge[] => {
    return edgesByType.value.get(type) || []
  }

  // ── Physics query helpers ──

  /**
   * Get all packages available for a given namelist variable.
   * Returns list of { package node, value, description }.
   */
  const getPackagesForNamelist = (namelistVar: string) => {
    const nlId = `namelist:${namelistVar}`
    const selectedByEdges = getEdgesTo(nlId).filter(e => e.type === 'SELECTED_BY')
    return selectedByEdges.map(e => {
      const pkgNode = getNodeById(e.source)
      return {
        node: pkgNode,
        value: e.data?.value || '',
        condition: e.data?.condition || '',
        packageName: pkgNode?.data?.package_name || pkgNode?.label || '',
        description: pkgNode?.label || '',
      }
    }).sort((a, b) => parseInt(a.value) - parseInt(b.value))
  }

  /**
   * Get all subroutines that are ACTIVE_WHEN a given namelist variable has a specific value.
   */
  const getActiveSubroutines = (namelistVar: string, value: string) => {
    const nlId = `namelist:${namelistVar}`
    const awEdges = getEdgesTo(nlId).filter(e => 
      e.type === 'ACTIVE_WHEN' && e.data?.value === value
    )
    return awEdges.map(e => ({
      node: getNodeById(e.source),
      edge: e,
      condition: e.data?.condition || '',
      evidence: e.data?.evidence || [],
    })).filter(r => r.node)
  }

  /**
   * Build an execution path for a namelist option setting:
   * namelist → Registry package constant → driver → dispatched calls.
   *
   * WRF dispatches on symbolic constants (for example LSMSCHEME), while the
   * Registry maps those constants to numeric namelist values. Keep that join
   * explicit here and never manufacture an "exact" call edge when the index
   * does not contain one.
   */
  const getExecutionPath = (namelistVar: string, value: string) => {
    const nlId = `namelist:${namelistVar}`
    const nlNode = getNodeById(nlId)
    if (!nlNode) return { nodes: [], edges: [] }

    const nodeMap = new Map<string, GraphNode>()
    const edgeMap = new Map<string, GraphEdge>()

    nodeMap.set(nlNode.id, nlNode)

    // 1. Registry packages whose predicate matches the selected value.
    const selectedBy = getEdgesTo(nlId).filter(e => 
      e.type === 'SELECTED_BY' && String(e.data?.value) === String(value)
    )
    const packageNodes: GraphNode[] = []
    for (const sb of selectedBy) {
      const pkgNode = getNodeById(sb.source)
      if (pkgNode) {
        packageNodes.push(pkgNode)
        nodeMap.set(pkgNode.id, pkgNode)
        // Reverse SELECTED_BY only for the explanatory left-to-right flow.
        // The evidence and confidence remain those of the indexed Registry edge.
        edgeMap.set(`${nlNode.id}->${pkgNode.id}:SELECTS`, {
          source: nlNode.id,
          target: pkgNode.id,
          type: 'SELECTS',
          data: { ...sb.data }
        })
      }
    }

    // 2. Associated Driver
    const driverName = nlNode.data?.driver
    let driverNode: GraphNode | undefined
    if (driverName) {
      driverNode = getNodeById(`subroutine:${driverName}`)
      if (driverNode) {
        nodeMap.set(driverNode.id, driverNode)
      }
    }

    // 3. Join the Registry package constant to CALLS edges recorded inside the
    // matching SELECT CASE branch in the driver.
    if (driverNode) {
      const dispatchConstants = new Set(
        packageNodes
          .map(pkg => String(pkg.data?.package_name || pkg.label).trim().toUpperCase())
          .filter(Boolean)
      )
      const dispatchCalls = getEdgesFrom(driverNode.id).filter(edge => {
        if (edge.type !== 'CALLS') return false
        if (String(edge.data?.dispatch_var || '').toLowerCase() !== namelistVar.toLowerCase()) return false
        const caseValues = String(edge.data?.dispatch_value || '')
          .split(',')
          .map(part => part.trim().toUpperCase())
        return caseValues.some(caseValue => dispatchConstants.has(caseValue))
      })

      for (const pkgNode of packageNodes) {
        const firstDispatchEvidence = dispatchCalls[0]?.data?.evidence || []
        edgeMap.set(`${pkgNode.id}->${driverNode.id}:DISPATCHES_THROUGH`, {
          source: pkgNode.id,
          target: driverNode.id,
          type: 'DISPATCHES_THROUGH',
          data: {
            condition: `${namelistVar} = ${value} selects ${pkgNode.data?.package_name || pkgNode.label}`,
            evidence: firstDispatchEvidence,
            confidence: 'inferred'
          }
        })
      }

      for (const callEdge of dispatchCalls) {
        const targetNode = getNodeById(callEdge.target)
        if (!targetNode) continue
        nodeMap.set(targetNode.id, targetNode)
        edgeMap.set(`${callEdge.source}->${callEdge.target}:${callEdge.data?.evidence?.[0]?.startLine || ''}`, callEdge)
      }
    }

    return { 
      nodes: Array.from(nodeMap.values()), 
      edges: Array.from(edgeMap.values()) 
    }
  }

  /**
   * Search nodes by label (fuzzy).
   */
  const searchNodes = (query: string, limit = 30): GraphNode[] => {
    if (!graph.value || !query) return []
    const q = query.toLowerCase()
    const results: GraphNode[] = []
    for (const node of graph.value.nodes) {
      if (results.length >= limit) break
      if (node.label.toLowerCase().includes(q) || node.id.toLowerCase().includes(q)) {
        results.push(node)
      }
    }
    return results
  }

  // ── Computed properties ──

  const metadata = computed(() => graph.value?.metadata || null)
  const activeSnapshot = computed(() => snapshots.value.find(item => item.id === activeSnapshotId.value) || null)

  const isLoaded = computed(() => graph.value !== null && !loading.value)

  const stats = computed(() => {
    if (!graph.value) return null
    return graph.value.metadata?.stats || {
      total_nodes: graph.value.nodes.length,
      total_edges: graph.value.edges.length,
    }
  })

  return {
    graph,
    loading,
    error,
    metadata,
    isLoaded,
    stats,
    snapshots,
    activeSnapshotId,
    activeSnapshot,
    loadSnapshots,
    switchSnapshot,
    loadGraph,
    getNodeById,
    getNodesByType,
    getEdgesFrom,
    getEdgesTo,
    getEdgesOfType,
    getPackagesForNamelist,
    getActiveSubroutines,
    getExecutionPath,
    searchNodes,
  }
})
