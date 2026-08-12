# WRF Code Atlas — Continuation Prompt

## Project Overview

You are continuing development on the **WRF Code Atlas**, an interactive educational web application that lets researchers understand the Weather Research and Forecasting (WRF) atmospheric model by exploring its source code, namelist configuration, physics dispatch, and execution flow interactively.

**Philosophy**: *This is not a source-code browser. It is an interactive executable mental model of WRF.* Every displayed relationship must be traced to actual source evidence.

---

## Directory Layout (CRITICAL — do not mix these)

```
E:\QWRF\WRF          ← WRF v4.7.1 source code. READ-ONLY. Never modify this.
E:\QWRF\WRF_Atlas    ← The WRF Code Atlas application. All your work goes here.
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend Framework | Vue 3 + TypeScript + Vite |
| State Management | Pinia |
| Graph Visualization | Cytoscape.js |
| Source Indexer | Python 3 |
| Styling | Vanilla CSS with CSS custom properties (NO Tailwind) |
| Fonts | Inter (sans), Fira Code (mono) — from Google Fonts |

---

## Project File Layout

```
E:\QWRF\WRF_Atlas\
├── indexer/                     ← Python static analysis pipeline
│   ├── main.py                  ← Entry point, orchestrates indexing
│   ├── fortran_parser.py        ← Continuation-aware Fortran AST parser
│   ├── registry_parser.py       ← Parses WRF Registry/* files
│   ├── graph_builder.py         ← Assembles the knowledge graph JSON
│   ├── config.py                ← WRF_SOURCE_ROOT = E:\QWRF\WRF
│   └── requirements.txt
├── public/
│   └── data/
│       └── wrf-knowledge-graph.json   ← Generated graph (11,758 nodes, 36,774 edges)
├── src/
│   ├── App.vue                  ← Root layout (sidebar + header + router-view)
│   ├── main.ts
│   ├── router/index.ts          ← Vue Router routes
│   ├── stores/
│   │   ├── graphStore.ts        ← Loads graph JSON, fast-lookup indexes, getExecutionPath()
│   │   ├── configStore.ts       ← Reactive namelist.input configuration values
│   │   └── uiStore.ts           ← Theme (dark/light), mode (learning/researcher), sidebar
│   ├── types/graph.ts           ← GraphNode, GraphEdge, PHYSICS_CATEGORIES, SourceEvidence
│   ├── components/
│   │   ├── layout/AppSidebar.vue
│   │   ├── layout/AppHeader.vue
│   │   ├── graph/GraphView.vue       ← Cytoscape.js node tree with layout switcher, legend
│   │   ├── evidence/EvidencePanel.vue ← Activation chain + "View in Source" button
│   │   ├── search/SearchPalette.vue  ← Ctrl+K global fuzzy search
│   │   └── source/SourceViewer.vue   ← Fortran code viewer with line highlights & jump
│   ├── views/
│   │   ├── OverviewView.vue          ← Home screen with stats and use case banner
│   │   ├── GuidedToursView.vue       ← 3-tab guide: Scenarios / Workflow / Compilation
│   │   ├── NamelistLabView.vue       ← Flagship: namelist editor + execution graph + evidence
│   │   ├── ExecutionMapView.vue      ← WRF lifecycle flow visualization
│   │   ├── PhysicsView.vue           ← Physics scheme explorer by category
│   │   ├── VariablesView.vue         ← State variable search (3,244 vars) with journey view
│   │   └── SourceView.vue            ← Source browser (388 files) with live file streaming
│   └── styles/
│       ├── index.css             ← Global design system tokens, glassmorphism utilities
│       └── fortran-highlight.css
├── vite.config.ts               ← Has /api/source middleware to stream live WRF source files
├── package.json
└── docs/
    └── source-survey.md         ← WRF repo analysis (entry points, Registry, physics drivers)
```

---

## Knowledge Graph Schema (wrf-knowledge-graph.json)

**Stats**: 11,758 nodes, 36,774 edges, 388 Fortran files parsed, 339 Registry packages, 2,273 namelist options, 3,244 state variables.

**Node types**: `program`, `module`, `subroutine`, `function`, `driver`, `namelist_option`, `registry_package`, `state_variable`, `source_file`, `physical_process`, `phase`

**Edge types**: `CALLS`, `USES`, `INCLUDES`, `DEFINED_IN`, `SELECTED_BY`, `ACTIVE_WHEN`, `READS_CONFIG`, `READS_VARIABLE`, `WRITES_VARIABLE`, `PASSES_VARIABLE`, `BELONGS_TO`, `EXECUTES_DURING`, `INITIALIZES`, `PROVIDES_TO`, `DEPENDS_ON`

**Node ID conventions**:
```
namelist_option   →  "namelist:sf_surface_physics"
registry_package  →  "package:lsmscheme"
subroutine        →  "subroutine:surface_driver"
program           →  "program:wrf"
state_variable    →  "state_var:HFX"
source_file       →  "file:phys/module_surface_driver.F"
```

**Edge metadata**:
```json
{
  "source": "subroutine:surface_driver",
  "target": "namelist:sf_surface_physics",
  "type": "ACTIVE_WHEN",
  "data": {
    "value": "2",
    "condition": "sf_surface_physics == 2",
    "evidence": [{ "path": "phys/module_surface_driver.F", "startLine": 2820, "endLine": 2824 }],
    "confidence": "exact"
  }
}
```

---

## Key Store APIs (graphStore.ts)

```typescript
// Load the graph
await graphStore.loadGraph()
graphStore.isLoaded          // boolean
graphStore.graph             // { nodes, edges, metadata, stats }

// Fast lookup indexes (built on load)
graphStore.getNodeById(id)                        // GraphNode | undefined
graphStore.getNodesByType(type)                   // GraphNode[]
graphStore.getEdgesFrom(nodeId)                   // GraphEdge[]
graphStore.getEdgesTo(nodeId)                     // GraphEdge[]
graphStore.searchNodes(query, limit?)             // GraphNode[] fuzzy search

// Physics-specific
graphStore.getPackagesForNamelist(namelistVar)     // { value, description, packageName, node }[]
graphStore.getActiveSubroutines(namelistVar, value) // { node, edge, condition, evidence }[]
graphStore.getExecutionPath(namelistVar, value)   // { nodes: GraphNode[], edges: GraphEdge[] }
```

---

## Key Store APIs (configStore.ts)

```typescript
configStore.config                          // Record<string, number> reactive config
configStore.getConfig(namelistVar)          // number
configStore.setConfig(namelistVar, value)   // sets reactive value
configStore.activePhysicsOptions            // computed Map<string, number>
```

---

## Key Store APIs (uiStore.ts)

```typescript
uiStore.mode           // 'learning' | 'researcher' — global display density toggle
uiStore.theme          // 'dark' | 'light'
uiStore.setMode(mode)  // 'learning' = friendly explanations; 'researcher' = file paths + line numbers
uiStore.toggleTheme()
uiStore.toggleSidebar()
```

---

## PHYSICS_CATEGORIES (types/graph.ts)

```typescript
const PHYSICS_CATEGORIES = {
  'land-surface': { label: 'Land Surface', namelist: 'sf_surface_physics', icon: '🌱', color: '#10b981' },
  'surface-layer': { label: 'Surface Layer', namelist: 'sf_sfclay_physics', icon: '🌬️', color: '#06b6d4' },
  'pbl':           { label: 'PBL',           namelist: 'bl_pbl_physics',    icon: '🌫️', color: '#8b5cf6' },
  'microphysics':  { label: 'Microphysics',  namelist: 'mp_physics',        icon: '💧', color: '#3b82f6' },
  'radiation-lw':  { label: 'LW Radiation',  namelist: 'ra_lw_physics',     icon: '🌡️', color: '#f59e0b' },
  'radiation-sw':  { label: 'SW Radiation',  namelist: 'ra_sw_physics',     icon: '☀️', color: '#fbbf24' },
  'cumulus':       { label: 'Cumulus',        namelist: 'cu_physics',        icon: '⛅', color: '#ec4899' },
}
```

---

## CSS Design System (index.css)

```css
/* Theme tokens */
--bg-base: #0a0e27;
--bg-surface: rgba(22, 30, 67, 0.7);
--bg-surface-hover: rgba(30, 41, 89, 0.8);
--bg-panel: rgba(15, 20, 48, 0.85);
--text-primary: #f8fafc;
--text-secondary: #94a3b8;
--text-muted: #64748b;
--border-subtle: rgba(255,255,255,0.1);
--accent-blue: #3b82f6;
--accent-amber: #f59e0b;
--accent-emerald: #10b981;
--accent-purple: #8b5cf6;
--accent-rose: #f43f5e;
--font-sans: 'Inter', sans-serif;
--font-mono: 'Fira Code', monospace;
--sidebar-width: 260px;
--header-height: 64px;

/* Glass utility classes */
.glass        { background: var(--bg-surface); backdrop-filter: blur(12px); border: 1px solid var(--border-subtle); border-radius: 12px; }
.glass-panel  { background: var(--bg-panel);   backdrop-filter: blur(16px); border: 1px solid var(--border-subtle); border-radius: 12px; }
```

---

## Navigation Routes

| Path | View | Purpose |
|---|---|---|
| `/` | OverviewView | Home screen with stats, lifecycle, CTA cards |
| `/tours` | GuidedToursView | 3-tab guide: research scenarios / operational workflow / compilation |
| `/namelist` | NamelistLabView | Namelist editor + live execution graph + node evidence inspector |
| `/execution` | ExecutionMapView | WRF lifecycle flow (wrf.exe → solve_em → physics drivers) |
| `/physics/:category` | PhysicsView | Physics scheme explorer by category |
| `/variables` | VariablesView | State variable search (HFX, TSK, SMOIS, PBLH, etc.) |
| `/source` | SourceView | Live Fortran source browser (388 files from E:\QWRF\WRF) |

---

## Live Source Code API

The Vite dev server has a custom middleware (in `vite.config.ts`) that streams real Fortran source files:

```
GET /api/source?file=phys/module_surface_driver.F
GET /api/source?file=Registry/Registry.EM_COMMON
GET /api/source?file=dyn_em/solve_em.F
```

Files are read directly from `E:\QWRF\WRF`. The `SourceView.vue` and `SourceViewer.vue` components use this endpoint to show live source code with line numbers and syntax highlighting.

The `SourceView.vue` also accepts URL query params:
```
/source?file=phys/module_surface_driver.F&line=2820
```
This opens the file and auto-scrolls to + highlights line 2820.

---

## WRF Source Structure (read-only, for analysis only)

```
E:\QWRF\WRF\
├── main/wrf.F            ← Program entry: CALL wrf_init, wrf_run, wrf_finalize
├── main/module_wrf_top.F
├── dyn_em/solve_em.F     ← ARW solver timestep integration loop
├── phys/
│   ├── module_physics_init.F
│   ├── module_surface_driver.F   ← sf_surface_physics dispatch
│   ├── module_pbl_driver.F       ← bl_pbl_physics dispatch
│   ├── module_microphysics_driver.F
│   ├── module_ra_driver.F
│   ├── module_cu_driver.F
│   ├── module_sf_noahlsm.F       ← Noah LSM (sf_surface_physics=2)
│   ├── module_bl_ysu.F           ← YSU PBL (bl_pbl_physics=1)
│   ├── module_mp_thompson.F      ← Thompson MP (mp_physics=8)
│   └── module_sf_bep_bem.F       ← BEP/BEM Urban (sf_urban_physics=2/3)
├── Registry/
│   ├── Registry.EM_COMMON        ← state var declarations, rconfig, package
│   └── *.EM_*
└── run/README.namelist            ← Namelist documentation
```

---

## Development Commands

```bash
# Run indexer (re-scans E:\QWRF\WRF, regenerates public/data/wrf-knowledge-graph.json)
cd E:\QWRF\WRF_Atlas
npm run index

# Start Vite dev server
npm run dev      # → http://localhost:5173/

# Run both (index then dev)
npm run atlas

# Type check
npx vue-tsc --noEmit
```

---

## What Has Been Built

### ✅ Complete & Working
- **Python Indexer** — Fortran continuation-aware parser, Registry parser, graph builder
- **Knowledge Graph** — 11,758 nodes, 36,774 edges, indexed 388 Fortran files
- **Overview Page** — Home with stats, guided tours banner, lifecycle chain
- **Guided Tours** — 3 tabs: Research Scenarios (4 use cases with 1-click apply), Operational Workflow (WPS→real.exe→wrf.exe), Compilation Guide (gcc, NetCDF, MPICH, configure, compile em_real)
- **Namelist Lab** — Physics config dropdowns (data from graph), live Cytoscape.js execution tree, node inspector, evidence chain with working "View in Source" button, scenario presets
- **Physics Explorer** — Category sidebar, scheme cards, active highlighting, researcher/learning mode
- **Variables View** — Searchable list, variable journey (definition, packages, subroutines), pagination
- **Execution Map** — WRF lifecycle flow cards
- **Source Browser** — 388-file searchable tree, live Fortran streaming via /api/source, syntax highlighting, line jumping, evidence-linked navigation
- **Graph View Component** — Layout switcher (tree top-down, tree left-right, cose, circle, grid), zoom/fit/reset controls, node type legend, in-graph filter, node icons, evidence-grade edge styling
- **Search Palette** — Ctrl+K global fuzzy search across all 11,758 nodes
- **Learning/Researcher Mode Toggle** — Wired globally via uiStore.mode
- **Dark/Light Theme Toggle**

### 🔧 Known Issues / Incomplete Features
- **Source browser**: May show fewer files than expected if some nodes lack `data.path`; verify source_file node data fields
- **ExecutionMapView**: Currently shows static lifecycle steps rather than deriving them from the live graph
- **VariablesView**: Journey tab may not always find all cross-references for a variable; depends on indexer coverage
- **EvidencePanel "View in Source"**: Works when edges have `evidence[0].path`; edges without evidence (inferred `CALLS`) will not show the button

---

## Highest-Priority Next Features

### 1. ComparisonView (`/compare`) — AGENTS.md §12
Allow side-by-side config diff:
- User pastes two namelist configs (Config A and Config B)
- Show graph diff: shared paths (grey), A-only (red dashed), B-only (green solid)
- Summarize: changed options, activated/deactivated packages, different subroutines reachable
- Implementation hint: call `getExecutionPath()` for both, compute symmetric difference of node IDs and edge IDs

### 2. Timestep Storyboard / Animation (`/execution` enhancement) — AGENTS.md §14
- Timeline view of ONE WRF timestep: dynamics → radiation → surface → PBL → microphysics → output
- Play/Pause/Step/Speed controls
- Highlights active code modules as animation progresses
- Derives stage ordering from actual source (solve_em → first_rk_step → physics_driver)

### 3. "Why Active?" Inspector (WHY button on every node) — AGENTS.md §17
- Every graph node should have a "WHY ACTIVE?" expand button
- Shows the full reasoning chain: namelist value → Registry mapping → driver dispatch → CALL
- Each step links to source evidence

### 4. Improve Indexer: Deeper CALLS Graph
Currently `CALLS` edges are sparse because many calls are generated by WRF's preprocessor macros (`WRFU_TraceEnter`, `CALL_TIMING`). Improve `fortran_parser.py` to:
- Expand macro call patterns (`CALL_*`, `#define`d shortcuts)
- Better track `config_flags%sf_surface_physics` reads to link them to dispatch SELECT CASE blocks
- Extract INTENT(IN)/INTENT(OUT) argument names from SUBROUTINE signatures and map them to `state_variable` nodes

### 5. Runtime Log Import (`/source` or new `/runs` view) — AGENTS.md §24
- Allow drag-and-drop of `rsl.out.0000` / `rsl.error.0000`
- Parse known routine names from log messages
- Highlight which graph nodes were "observed" during the run vs. merely "reachable"

### 6. Physics Interaction Map — AGENTS.md §16
- Circular/orbital diagram showing inter-scheme coupling (Surface Layer → LSM → PBL → Radiation feedback)
- Different edge styles for: physical coupling vs. shared state variable vs. explicit CALL
- Driven by actual PASSES_VARIABLE / PROVIDES_TO edges in graph

---

## Important Constraints

1. **Never modify files in `E:\QWRF\WRF\`** — that is a read-only scientific source tree
2. **All Atlas code goes in `E:\QWRF\WRF_Atlas\`**
3. **Source-ground everything** — do not invent call relationships; only display edges with evidence
4. **No external LLM/AI API calls** — the app must work offline after indexing
5. **No Tailwind CSS** — use vanilla CSS with the established design tokens
6. **Dark, scientific, atmospheric aesthetic** — think interactive atlas + code debugger + educational sim
7. **Performance** — never render all 11,758 nodes at once; use lazy expansion, filters, depth limits

---

## Running State Right Now

- Vite dev server is running at `http://localhost:5173/`
- Knowledge graph is indexed and loaded at `public/data/wrf-knowledge-graph.json`
- TypeScript compiles with zero errors (`npx vue-tsc --noEmit` passes)
- All 7 views are functional with real data from the graph

---

## How to Start

1. `cd E:\QWRF\WRF_Atlas`
2. `npm run dev` (if not already running)
3. Open `http://localhost:5173/` in browser
4. To re-index after any WRF source changes: `npm run index`

Start by reading the AGENTS.md spec at `E:\QWRF\WRF_Atlas\AGENTS.md` and then continue implementing whichever feature from the "Highest-Priority Next Features" list makes most sense.
