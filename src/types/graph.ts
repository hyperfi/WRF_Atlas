export interface GraphNode {
  id: string
  type: string
  label: string
  data: Record<string, any>
}

export interface SourceEvidence {
  path: string
  startLine?: number
  endLine?: number
  description?: string
  snippet?: string
}

export interface GraphEdge {
  source: string
  target: string
  type: string
  data: {
    condition?: string
    value?: string
    evidence?: SourceEvidence[]
    confidence?: 'exact' | 'inferred' | 'documentation'
    dispatch_var?: string
    dispatch_value?: string
    [key: string]: any
  }
}

export interface KnowledgeGraph {
  metadata: {
    wrf_version: string
    commit: string
    branch?: string
    indexed_at: string
    source_root: string
    stats?: {
      total_nodes: number
      total_edges: number
      fortran_files_parsed?: number
      registry_packages?: number
      namelist_options?: number
      state_variables?: number
    }
  }
  nodes: GraphNode[]
  edges: GraphEdge[]
}

// Physics categories for the UI
export const PHYSICS_CATEGORIES = {
  land_surface: { label: 'Land Surface', namelist: 'sf_surface_physics', icon: '🌲', color: '#10b981' },
  surface_layer: { label: 'Surface Layer', namelist: 'sf_sfclay_physics', icon: '🌬️', color: '#06b6d4' },
  pbl: { label: 'Planetary Boundary Layer', namelist: 'bl_pbl_physics', icon: '☁️', color: '#8b5cf6' },
  microphysics: { label: 'Microphysics', namelist: 'mp_physics', icon: '🌧️', color: '#3b82f6' },
  longwave_radiation: { label: 'Longwave Radiation', namelist: 'ra_lw_physics', icon: '🌡️', color: '#ef4444' },
  shortwave_radiation: { label: 'Shortwave Radiation', namelist: 'ra_sw_physics', icon: '☀️', color: '#f59e0b' },
  cumulus: { label: 'Cumulus', namelist: 'cu_physics', icon: '⛈️', color: '#6366f1' },
  urban_canopy: { label: 'Urban Canopy', namelist: 'sf_urban_physics', icon: 'URB', color: '#b98b5f' },
} as const

export type PhysicsCategory = keyof typeof PHYSICS_CATEGORIES
