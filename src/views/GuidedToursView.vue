<template>
  <div class="guide-view">
    <header class="page-header">
      <div>
        <p class="eyebrow">Learn · configure · run</p>
        <h1>WRF field guide</h1>
        <p>Structured paths through this checkout, its input controls, and the practical workflow around a real-data WRF run.</p>
      </div>
      <div class="guide-scope">
        <span><i></i> Indexed: WRF {{ graphStore.metadata?.wrf_version || '4.7.1' }}</span>
        <small>WPS is not present in this checkout and is identified as external where relevant.</small>
      </div>
    </header>

    <nav class="guide-tabs surface-panel" aria-label="Field guide sections">
      <button v-for="tab in tabs" :key="tab.id" :class="{ active: activeTab === tab.id }" @click="activeTab = tab.id">
        <span>{{ tab.code }}</span>
        <div><strong>{{ tab.label }}</strong><small>{{ tab.description }}</small></div>
      </button>
    </nav>

    <section v-if="activeTab === 'learn'" class="learn-layout">
      <aside class="lesson-list surface-panel">
        <div class="section-heading"><p class="eyebrow">Source-led lessons</p><span>01</span></div>
        <button v-for="(lesson, index) in lessons" :key="lesson.id" :class="{ active: selectedLesson.id === lesson.id }" @click="selectedLesson = lesson">
          <span>{{ String(index + 1).padStart(2, '0') }}</span>
          <div><strong>{{ lesson.title }}</strong><small>{{ lesson.duration }}</small></div>
        </button>
      </aside>

      <main class="lesson-detail surface-panel">
        <div class="lesson-intro">
          <div>
            <p class="eyebrow">{{ selectedLesson.level }} · {{ selectedLesson.duration }}</p>
            <h2>{{ selectedLesson.title }}</h2>
            <p>{{ selectedLesson.summary }}</p>
          </div>
          <router-link v-if="selectedLesson.route" :to="selectedLesson.route" class="primary-action">Open interactive view <span>→</span></router-link>
        </div>

        <div class="lesson-objective">
          <strong>Question this lesson answers</strong>
          <p>{{ selectedLesson.question }}</p>
        </div>

        <div class="source-stops">
          <div class="stops-heading"><p class="eyebrow">Evidence stops</p><span>Open any stop beside the live checkout</span></div>
          <article v-for="(stop, index) in resolvedLessonStops" :key="`${selectedLesson.id}-${stop.label}`" class="source-stop">
            <span class="stop-number">{{ String(index + 1).padStart(2, '0') }}</span>
            <div class="stop-copy">
              <span class="confidence" :class="stop.confidence">{{ stop.confidence }}</span>
              <h3>{{ stop.label }}</h3>
              <p>{{ stop.explanation }}</p>
              <code v-if="stop.node">{{ stop.node.label }}</code>
            </div>
            <button v-if="stop.evidence" @click="openSource(stop.evidence.path, stop.evidence.line)">Source <span>↗</span></button>
          </article>
        </div>
      </main>
    </section>

    <section v-else-if="activeTab === 'workflows'" class="research-layout">
      <aside class="workflow-picker surface-panel">
        <div class="section-heading"><p class="eyebrow">Research questions</p><span>02</span></div>
        <button v-for="workflow in researchWorkflows" :key="workflow.id" :class="{ active: selectedWorkflow.id === workflow.id }" @click="selectedWorkflow = workflow">
          <span>{{ workflow.code }}</span>
          <div><strong>{{ workflow.title }}</strong><small>{{ workflow.scale }}</small></div>
        </button>
        <div class="template-contract"><strong>Exploration template</strong><p>These are checkout-valid starting points for tracing code, not universal scientific recommendations.</p></div>
      </aside>

      <main class="research-detail surface-panel">
        <div class="research-hero">
          <div><p class="eyebrow">{{ selectedWorkflow.code }} · {{ selectedWorkflow.scale }}</p><h2>{{ selectedWorkflow.title }}</h2><p>{{ selectedWorkflow.summary }}</p></div>
          <button class="primary-action" @click="applyWorkflow">Trace the defining choice <span>→</span></button>
        </div>
        <div class="research-question"><strong>Research lens</strong><p>{{ selectedWorkflow.question }}</p></div>
        <div class="workflow-config">
          <div class="config-heading"><p class="eyebrow">Source-resolved option set</p><span>Registry mappings from this checkout</span></div>
          <article v-for="item in resolvedWorkflowConfig" :key="item.name">
            <div><code>{{ item.name }}</code><span>= {{ item.value }}</span></div>
            <strong>{{ item.packageLabel }}</strong>
            <button v-if="item.evidence" @click="openSource(item.evidence.path, item.evidence.line)">Registry ↗</button>
            <span v-else class="unresolved">Unresolved</span>
          </article>
        </div>
        <div class="workflow-notes">
          <div><p class="eyebrow">Decisions to investigate</p><ul><li v-for="decision in selectedWorkflow.decisions" :key="decision">{{ decision }}</li></ul></div>
          <div><p class="eyebrow">Required beyond this index</p><ul><li v-for="input in selectedWorkflow.external" :key="input">{{ input }}</li></ul></div>
        </div>
        <div class="workflow-caution"><strong>Before using this in a study</strong><p>{{ selectedWorkflow.caution }}</p></div>
      </main>
    </section>

    <section v-else-if="activeTab === 'inputs'" class="input-layout">
      <aside class="input-groups surface-panel">
        <div class="section-heading"><p class="eyebrow">Input domains</p><span>02</span></div>
        <button v-for="group in parameterGroups" :key="group.id" :class="{ active: selectedParameterGroup.id === group.id }" @click="selectParameterGroup(group)">
          <span>{{ group.code }}</span><div><strong>{{ group.label }}</strong><small>{{ group.parameters.length }} key controls</small></div>
        </button>
      </aside>

      <main class="parameter-catalog surface-panel">
        <div class="catalog-header">
          <div><p class="eyebrow">{{ selectedParameterGroup.label }}</p><h2>Input parameter guide</h2></div>
          <label class="parameter-search"><span>Filter</span><input v-model="parameterQuery" placeholder="parameter name" /></label>
        </div>
        <div class="parameter-table">
          <button v-for="parameter in filteredParameters" :key="parameter.name" :class="{ active: selectedParameter?.name === parameter.name }" @click="selectedParameter = parameter">
            <code>{{ parameter.name }}</code><span>{{ parameter.role }}</span><small>{{ parameter.unit || 'configuration' }}</small>
          </button>
        </div>
      </main>

      <aside class="parameter-detail surface-panel" v-if="selectedParameter">
        <div class="detail-heading"><p class="eyebrow">Parameter evidence</p><span>03</span></div>
        <h2><code>{{ selectedParameter.name }}</code></h2>
        <p class="parameter-role">{{ selectedParameter.role }}</p>
        <dl>
          <div><dt>Registry type</dt><dd>{{ selectedParameterNode?.data?.type || 'not resolved' }}</dd></div>
          <div><dt>Dimensions</dt><dd><code>{{ selectedParameterNode?.data?.dims || 'not resolved' }}</code></dd></div>
          <div><dt>Registry default</dt><dd><code>{{ selectedParameterNode?.data?.default ?? 'not resolved' }}</code></dd></div>
          <div><dt>Namelist group</dt><dd><code>{{ selectedParameterNode?.data?.group || 'not resolved' }}</code></dd></div>
        </dl>
        <div class="interpretation-note">
          <strong>How to use this guide</strong>
          <p>{{ selectedParameter.guidance }}</p>
        </div>
        <button class="source-link" @click="openSource('run/README.namelist', selectedParameter.docLine)">Open local parameter documentation <span>↗</span></button>
        <button v-if="selectedParameterNode" class="source-link secondary" @click="openSource(selectedParameterNode.data.source_file, selectedParameterNode.data.source_line)">Open Registry definition <span>↗</span></button>
      </aside>
    </section>

    <section v-else-if="activeTab === 'run'" class="workflow-layout">
      <div class="workflow-intro surface-panel">
        <div><p class="eyebrow">Real-data workflow</p><h2>Inputs become an integrating atmosphere in four boundaries.</h2></div>
        <p>This is an operational orientation, not a guarantee that external datasets or WPS are installed locally.</p>
      </div>
      <div class="workflow-stages">
        <article v-for="(stage, index) in runStages" :key="stage.title" class="workflow-stage surface-panel">
          <div class="stage-index">{{ String(index + 1).padStart(2, '0') }}</div>
          <div class="stage-main"><span class="stage-scope" :class="stage.scope">{{ stage.scope }}</span><h3>{{ stage.title }}</h3><p>{{ stage.description }}</p></div>
          <div class="stage-io"><span>Consumes</span><code>{{ stage.input }}</code><span>Produces</span><code>{{ stage.output }}</code></div>
          <button v-if="stage.source" @click="openSource(stage.source.path, stage.source.line)">Evidence <span>↗</span></button>
        </article>
      </div>
      <div class="workflow-warning"><strong>Boundary of this Atlas:</strong> WPS source is not under <code>E:\QWRF\WRF</code>. The WPS stages are workflow documentation; WRF startup and integration stages link to indexed source.</div>
    </section>

    <section v-else class="build-layout">
      <div class="build-intro surface-panel">
        <div><p class="eyebrow">Local checkout build paths</p><h2>Use the build system this WRF tree actually ships.</h2></div>
        <p>The Atlas documents commands present in the checkout. Compiler and library installation remains platform-specific; the local documentation names netCDF as required.</p>
      </div>
      <div class="build-paths">
        <article v-for="path in buildPaths" :key="path.id" class="build-path surface-panel" :class="{ selected: selectedBuildPath === path.id }">
          <div class="build-path-header"><span>{{ path.code }}</span><div><h3>{{ path.title }}</h3><p>{{ path.subtitle }}</p></div><button @click="selectedBuildPath = path.id">{{ selectedBuildPath === path.id ? 'Selected' : 'Inspect' }}</button></div>
          <template v-if="selectedBuildPath === path.id">
            <ol><li v-for="step in path.steps" :key="step.command"><div><strong>{{ step.title }}</strong><p>{{ step.detail }}</p></div><code>{{ step.command }}</code></li></ol>
            <div class="build-proof"><span>Local authority</span><code>{{ path.evidence.path }}:{{ path.evidence.line }}</code><button @click="openSource(path.evidence.path, path.evidence.line)">Open documentation ↗</button></div>
          </template>
        </article>
      </div>
      <div class="prerequisite-panel surface-panel">
        <p class="eyebrow">Before configure</p>
        <div><strong>Compiler toolchain</strong><span>Supported compiler must be available on the target system.</span></div>
        <div><strong>netCDF</strong><span>The checkout documentation explicitly identifies netCDF as required.</span></div>
        <div><strong>Parallel mode</strong><span>Choose serial, shared-memory, or distributed-memory options appropriate to the machine.</span></div>
        <p>No universal package-manager command is presented because dependencies, MPI implementation, module environment, and ABI compatibility are platform-specific.</p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useGraphStore } from '@/stores/graphStore'
import { useConfigStore } from '@/stores/configStore'
import type { GraphNode } from '@/types/graph'

type TabId = 'learn' | 'workflows' | 'inputs' | 'run' | 'build'
interface ParameterGuide { name: string; role: string; guidance: string; docLine: number; unit?: string }

const router = useRouter()
const graphStore = useGraphStore()
const configStore = useConfigStore()
const activeTab = ref<TabId>('learn')
const tabs = [
  { id: 'learn' as const, code: '01', label: 'Learn the code', description: 'Source-led lessons' },
  { id: 'workflows' as const, code: '02', label: 'Research workflows', description: 'Real-world study lenses' },
  { id: 'inputs' as const, code: '03', label: 'Input guide', description: 'Understand namelist controls' },
  { id: 'run' as const, code: '04', label: 'Run workflow', description: 'WPS to wrf.exe' },
  { id: 'build' as const, code: '05', label: 'Build locally', description: 'Checkout-supported paths' },
]

const lessons = [
  { id: 'startup', title: 'How WRF starts', duration: '12 min', level: 'Foundation', question: 'How does the executable move from process startup into the model integration loop?', summary: 'Follow exact call sites from PROGRAM wrf through initialization, wrf_run, the domain integration mediator, and ARW solve_em.', route: '/execution', stops: [
    { id: 'program:wrf', explanation: 'The executable entry program and its ordered top-level calls.' },
    { id: 'subroutine:wrf_init', explanation: 'Initialization and configuration work begins here.' },
    { id: 'subroutine:wrf_run', explanation: 'The forward model run hands control to domain integration.' },
    { id: 'subroutine:integrate', explanation: 'The mediation layer manages domains, I/O, nesting, and solve calls.' },
    { id: 'subroutine:solve_em', explanation: 'The ARW solver advances the model state.' },
  ]},
  { id: 'timestep', title: 'Anatomy of one timestep', duration: '18 min', level: 'Core execution', question: 'Where do physics drivers sit relative to the RK dynamics work?', summary: 'Use exact call lines in solve_em and first_rk_step_part1 to orient one conceptual timestep.', route: '/execution?view=timestep', stops: [
    { id: 'subroutine:solve_em', explanation: 'The ARW integration routine contains RK work and physics call sites.' },
    { id: 'subroutine:first_rk_step_part1', explanation: 'Radiation, surface, PBL, and convection drivers are called here in source order.' },
    { id: 'subroutine:first_rk_step_part2', explanation: 'Physics tendencies and diffusion work continue in the second part.' },
    { id: 'subroutine:microphysics_driver', explanation: 'Microphysics is called later from solve_em in this checkout.' },
  ]},
  { id: 'land', title: 'Choosing a land-surface model', duration: '15 min', level: 'Configuration trace', question: 'Why does sf_surface_physics = 2 activate the Noah LSM branch?', summary: 'Join the exact Registry predicate to the symbolic surface_driver CASE and inspect its calls.', route: '/namelist?focus=sf_surface_physics&value=2', stops: [
    { id: 'namelist:sf_surface_physics', explanation: 'The Registry defines the user-facing option.' },
    { id: 'package:lsmscheme', explanation: 'The Registry maps value 2 to the LSMSCHEME constant.' },
    { id: 'subroutine:surface_driver', explanation: 'The runtime driver selects the matching symbolic CASE.' },
    { id: 'subroutine:lsm', explanation: 'An exact implementation call inside that branch.' },
  ]},
  { id: 'field', title: 'Follow a model field', duration: '10 min', level: 'State journey', question: 'Where is HFX declared and which indexed routines reference it?', summary: 'Begin at the Registry state definition, then inspect the currently available static cross-references without assuming read/write direction.', route: '/variables', stops: [
    { id: 'state:hfx', explanation: 'The Registry declaration anchors the field identity and I/O metadata.' },
    { id: 'subroutine:surface_driver', explanation: 'The surface driver carries HFX among its arguments.' },
    { id: 'subroutine:pbl_driver', explanation: 'The PBL interface also exchanges surface heat-flux state.' },
  ]},
]

const selectedLesson = ref(lessons[0])
const resolvedLessonStops = computed(() => selectedLesson.value.stops.map(stop => {
  const node = graphStore.getNodeById(stop.id)
  const path = node?.data?.file || node?.data?.source_file || node?.data?.path
  const line = node?.data?.line || node?.data?.source_line || 1
  return { ...stop, label: node?.label || stop.id.replace(/^\w+:/, ''), node, confidence: node && path ? 'exact' : 'unresolved', evidence: path ? { path, line } : undefined }
}))

interface ResearchWorkflow {
  id: string
  code: string
  title: string
  scale: string
  summary: string
  question: string
  focus: string
  config: Record<string, number>
  decisions: string[]
  external: string[]
  caution: string
}

const researchWorkflows: ResearchWorkflow[] = [
  {
    id: 'regional', code: 'REG', title: 'Regional weather forecast', scale: 'Synoptic to mesoscale',
    summary: 'Trace how a familiar regional forecast configuration connects land, boundary-layer, cloud, convection, and radiation code paths.',
    question: 'Which parameterized processes become reachable, and which assumptions should be revisited as domain spacing changes?',
    focus: 'sf_surface_physics',
    config: { sf_surface_physics: 2, sf_sfclay_physics: 1, bl_pbl_physics: 1, mp_physics: 8, cu_physics: 1, ra_lw_physics: 4, ra_sw_physics: 4 },
    decisions: ['Follow Noah LSM into the surface driver.', 'Inspect surface-layer and PBL coupling.', 'Compare explicit microphysics with parameterized deep convection.'],
    external: ['WPS geography and land-use data', 'Time-varying meteorological forcing', 'Domain, resolution, timestep, and boundary design'],
    caution: 'The option set is a code-exploration baseline. Forecast quality and suitability require case-specific validation, spin-up choices, observations, and sensitivity experiments.'
  },
  {
    id: 'urban', code: 'UHI', title: 'Urban heat-island study', scale: 'City to regional coupling',
    summary: 'Expose the urban canopy selector alongside Noah-MP and the near-surface schemes that exchange heat, moisture, momentum, and diagnostic fields.',
    question: 'Where does an urban option enter the land-surface path, and what urban morphology or land-use information must exist outside the namelist?',
    focus: 'sf_urban_physics',
    config: { sf_surface_physics: 4, sf_urban_physics: 2, sf_sfclay_physics: 5, bl_pbl_physics: 5, mp_physics: 8, ra_lw_physics: 4, ra_sw_physics: 4 },
    decisions: ['Resolve sf_urban_physics = 2 to the BEP Registry package.', 'Inspect its conditional handling inside land-surface routines.', 'Follow T2, U10, V10, HFX, QFX, and urban state fields.'],
    external: ['Urban land-use or LCZ classification', 'Urban morphology and building parameters', 'Observations suitable for urban and rural comparison'],
    caution: 'BEP is not activated meaningfully by the selector alone. Land-use categories, urban parameters, domain resolution, forcing, and compatible physics must be checked for the intended experiment.'
  },
  {
    id: 'convection', code: 'CONV', title: 'Severe-convection experiment', scale: 'Convection permitting',
    summary: 'Explore a configuration that turns off the cumulus package while retaining explicit microphysics and near-surface parameterizations.',
    question: 'What changes in the executable path when cu_physics is disabled and condensate processes remain represented by microphysics?',
    focus: 'cu_physics',
    config: { sf_surface_physics: 2, sf_sfclay_physics: 5, bl_pbl_physics: 5, mp_physics: 10, cu_physics: 0, ra_lw_physics: 4, ra_sw_physics: 4 },
    decisions: ['Compare the inactive cumulus branch with active alternatives.', 'Trace Morrison two-moment microphysics dispatch.', 'Inspect timestep and grid-spacing implications separately from scheme selection.'],
    external: ['High-resolution initial and boundary data', 'Radar or storm-scale verification data', 'Resolution, timestep, vertical grid, and diffusion design'],
    caution: 'Disabling cumulus physics is not automatically correct at every grid spacing. Grey-zone behavior, storm initiation, numerics, and microphysics sensitivity require deliberate experiment design.'
  },
  {
    id: 'cyclone', code: 'TC', title: 'Tropical-cyclone case', scale: 'Storm and environment',
    summary: 'Use a compact option set to investigate moisture processes, surface exchange, radiation, and parameterized convection around a rotating storm.',
    question: 'Which physics paths exchange the thermodynamic and surface-flux state that can influence storm structure and intensity?',
    focus: 'mp_physics',
    config: { sf_surface_physics: 2, sf_sfclay_physics: 1, bl_pbl_physics: 1, mp_physics: 6, cu_physics: 1, ra_lw_physics: 4, ra_sw_physics: 4 },
    decisions: ['Trace WSM6 through microphysics dispatch.', 'Inspect surface-flux and PBL interfaces.', 'Compare cumulus reachability across nested-domain resolutions.'],
    external: ['Storm-centered forcing and sea-surface state', 'Vortex initialization or data-assimilation choices', 'Track, intensity, rainfall, and structure observations'],
    caution: 'This is not a validated tropical-cyclone suite. Ocean coupling, nesting, SST evolution, initialization, resolution, and alternative physics can dominate the scientific result.'
  },
]

const selectedWorkflow = ref<ResearchWorkflow>(researchWorkflows[0])
const resolvedWorkflowConfig = computed(() => Object.entries(selectedWorkflow.value.config).map(([name, value]) => {
  const option = graphStore.getPackagesForNamelist(name).find(item => Number(item.value) === value)
  const edge = graphStore.getEdgesTo(`namelist:${name}`).find(item => item.type === 'SELECTED_BY' && Number(item.data?.value) === value)
  const proof = edge?.data?.evidence?.[0]
  return {
    name, value,
    packageLabel: option?.description || option?.packageName || 'No Registry package resolved',
    evidence: proof ? { path: proof.path, line: proof.startLine || 1 } : undefined,
  }
}))

const applyWorkflow = () => {
  for (const [name, value] of Object.entries(selectedWorkflow.value.config)) configStore.setConfig(name, value)
  router.push({ path: '/namelist', query: { focus: selectedWorkflow.value.focus, value: String(selectedWorkflow.value.config[selectedWorkflow.value.focus]) } })
}

const parameterGroups = [
  { id: 'time', code: 'TIME', label: 'Run time and dates', parameters: [
    { name: 'run_hours', role: 'Total simulated hours.', guidance: 'Keep the requested duration consistent with available boundary-condition times.', docLine: 10, unit: 'hours' },
    { name: 'start_year', role: 'Start date year for each domain.', guidance: 'Date components and interval_seconds must align with the incoming real-data sequence.', docLine: 16 },
    { name: 'interval_seconds', role: 'Spacing between incoming real-data times.', guidance: 'This describes the temporal spacing of external forcing, not the numerical integration timestep.', docLine: 39, unit: 'seconds' },
  ]},
  { id: 'domain', code: 'GRID', label: 'Domain and timestep', parameters: [
    { name: 'time_step', role: 'Model integration timestep.', guidance: 'Stability depends on grid spacing, dynamics, nesting, and physics; the Atlas does not prescribe a universal value.', docLine: 155, unit: 'seconds' },
    { name: 'max_dom', role: 'Number of WRF domains.', guidance: 'Values above one activate nested-domain configuration requirements.', docLine: 164 },
    { name: 'e_we', role: 'West-east staggered grid dimension.', guidance: 'Interpret together with e_sn, dx, dy, projection, and nesting ratios.', docLine: 166 },
    { name: 'e_sn', role: 'South-north staggered grid dimension.', guidance: 'Interpret together with e_we, dx, dy, projection, and nesting ratios.', docLine: 168 },
    { name: 'dx', role: 'Horizontal grid spacing in the x direction.', guidance: 'Grid spacing changes resolved scales, cost, stability constraints, and appropriate physics assumptions.', docLine: 174, unit: 'metres' },
    { name: 'dy', role: 'Horizontal grid spacing in the y direction.', guidance: 'Usually interpreted alongside dx and map projection.', docLine: 175, unit: 'metres' },
  ]},
  { id: 'physics', code: 'PHYS', label: 'Physics selections', parameters: [
    { name: 'mp_physics', role: 'Microphysics scheme selector.', guidance: 'Use the Namelist Lab to inspect Registry mappings and reachable driver branches for this checkout.', docLine: 473 },
    { name: 'ra_lw_physics', role: 'Longwave radiation selector.', guidance: 'Radiation selection and scheduling interval are separate controls.', docLine: 580 },
    { name: 'sf_surface_physics', role: 'Land-surface scheme selector.', guidance: 'Inspect compatibility with the surface-layer and PBL choices rather than treating the scheme in isolation.', docLine: 697 },
    { name: 'bl_pbl_physics', role: 'Planetary boundary-layer selector.', guidance: 'PBL, surface-layer, and land-surface choices exchange state and may have compatibility constraints.', docLine: 740 },
    { name: 'cu_physics', role: 'Cumulus parameterization selector.', guidance: 'Whether a cumulus parameterization is appropriate depends on resolution and experiment design.', docLine: 825 },
  ]},
  { id: 'output', code: 'IO', label: 'History and restart output', parameters: [
    { name: 'history_interval', role: 'Time between history outputs.', guidance: 'Shorter intervals increase temporal resolution and I/O volume.', docLine: 46, unit: 'minutes' },
    { name: 'frames_per_outfile', role: 'Number of output times stored per history file.', guidance: 'This affects file grouping rather than the model timestep.', docLine: 47 },
    { name: 'restart_interval', role: 'Time between restart checkpoints.', guidance: 'Choose according to run duration and recovery requirements.', docLine: 52, unit: 'minutes' },
  ]},
] satisfies Array<{ id: string; code: string; label: string; parameters: ParameterGuide[] }>

const selectedParameterGroup = ref(parameterGroups[0])
const selectedParameter = ref<ParameterGuide | null>(parameterGroups[0].parameters[0])
const parameterQuery = ref('')
const filteredParameters = computed(() => selectedParameterGroup.value.parameters.filter(parameter => parameter.name.includes(parameterQuery.value.trim().toLowerCase())))
const selectedParameterNode = computed(() => selectedParameter.value ? graphStore.getNodeById(`namelist:${selectedParameter.value.name}`) : undefined)
const selectParameterGroup = (group: typeof parameterGroups[number]) => { selectedParameterGroup.value = group; selectedParameter.value = group.parameters[0]; parameterQuery.value = '' }

const runStages = [
  { title: 'Prepare geography and meteorology', scope: 'external', description: 'WPS normally defines domains and horizontally interpolates external meteorology. WPS source is not part of this indexed checkout.', input: 'geography + GRIB meteorology', output: 'met_em.d0* files' },
  { title: 'Create WRF initial and boundary state', scope: 'documented', description: 'The em_real build produces real.exe for a real-data workflow; runtime behavior is documented here without pretending this index has resolved a standalone PROGRAM node.', input: 'met_em + namelist.input', output: 'wrfinput_d0* + wrfbdy_d01', source: { path: 'README', line: 316 } },
  { title: 'Initialize wrf.exe', scope: 'indexed', description: 'PROGRAM wrf calls wrf_init before the forward run. Configuration, domains, and model services are prepared here.', input: 'namelist + WRF input state', output: 'initialized domains', source: { path: 'main/wrf.F', line: 30 } },
  { title: 'Integrate and write model state', scope: 'indexed', description: 'wrf_run reaches integrate, solve_interface, and the ARW solve_em routine in the indexed call graph.', input: 'initialized atmospheric state', output: 'history/restart state', source: { path: 'main/module_wrf_top.F', line: 2074 } },
]

const buildPaths = [
  { id: 'classic', code: 'MAKE', title: 'Classic configure + compile', subtitle: 'The established WRF build scripts.', evidence: { path: 'README', line: 304 }, steps: [
    { title: 'Configure', detail: 'Choose a compiler/parallelism stanza appropriate to the machine.', command: './configure' },
    { title: 'Compile the real-data case', detail: 'The local README lists em_real among supported cases.', command: './compile em_real' },
    { title: 'Inspect the log', detail: 'Capture compiler output and check that required executables were produced.', command: './compile em_real >& compile.log' },
  ]},
  { id: 'cmake', code: 'CMAKE', title: 'configure_new + compile_new', subtitle: 'The checkout-supported CMake path.', evidence: { path: 'doc/README.cmake_build', line: 2 }, steps: [
    { title: 'Configure', detail: 'Create the _build configuration using detected compilers and netCDF.', command: './configure_new' },
    { title: 'Compile', detail: 'Pass ordinary make parallelism options when appropriate.', command: './compile_new -j 12' },
    { title: 'Explicit ARW real-data configuration', detail: 'The local document provides this non-interactive example.', command: './configure_new -p GNU -x -- -DWRF_CORE=ARW -DWRF_NESTING=BASIC -DWRF_CASE=EM_REAL' },
  ]},
]
const selectedBuildPath = ref('cmake')

const openSource = (path: string, line = 1) => router.push({ path: '/source', query: { file: path.replaceAll('\\', '/'), line: String(line || 1) } })

onMounted(async () => { if (!graphStore.isLoaded && !graphStore.loading) await graphStore.loadGraph() })
</script>

<style scoped>
.guide-view { display: flex; width: 100%; max-width: 1480px; margin: 0 auto; flex-direction: column; gap: 18px; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 40px; padding: 5px 2px 8px; }.page-header h1 { margin-top: 6px; font-size: 2rem; font-weight: 580; }.page-header > div > p:last-child { max-width: 760px; margin-top: 7px; color: var(--text-secondary); font-size: .82rem; }
.guide-scope { max-width: 360px; padding-left: 20px; border-left: 1px solid var(--border-subtle); }.guide-scope span { display: flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: .68rem; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; }.guide-scope i { width: 7px; height: 7px; background: var(--accent-emerald); border-radius: 50%; }.guide-scope small { display: block; margin-top: 7px; color: var(--text-muted); font-size: .64rem; line-height: 1.45; }
.guide-tabs { display: grid; grid-template-columns: repeat(5, 1fr); padding: 5px; }.guide-tabs button { display: grid; min-height: 58px; grid-template-columns: 30px 1fr; align-items: center; gap: 8px; padding: 8px 12px; background: transparent; border: 1px solid transparent; border-radius: 5px; color: var(--text-muted); cursor: pointer; text-align: left; }.guide-tabs button:hover { background: var(--bg-surface-hover); }.guide-tabs button.active { background: var(--accent-soft); border-color: color-mix(in srgb,var(--accent-emerald) 25%,var(--border-subtle)); color: var(--text-primary); }.guide-tabs button > span { color: var(--accent-emerald); font-family: var(--font-mono); font-size: .61rem; }.guide-tabs button div { display: flex; flex-direction: column; }.guide-tabs strong { font-size: .75rem; }.guide-tabs small { margin-top: 2px; color: var(--text-muted); font-size: .61rem; }
.section-heading, .detail-heading { display: flex; min-height: 62px; align-items: center; justify-content: space-between; padding: 14px 16px; border-bottom: 1px solid var(--border-subtle); }.section-heading > span,.detail-heading > span { color: var(--border-strong); font-family: var(--font-mono); font-size: .63rem; }
.learn-layout,.input-layout { display: grid; grid-template-columns: 260px minmax(0,1fr); gap: 14px; }.lesson-list,.input-groups { overflow: hidden; }.lesson-list > button,.input-groups > button { display: grid; width: 100%; min-height: 65px; grid-template-columns: 28px 1fr; align-items: center; gap: 8px; padding: 10px 16px; background: transparent; border: 0; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); cursor: pointer; text-align: left; }.lesson-list > button:hover,.input-groups > button:hover { background: var(--bg-surface-hover); }.lesson-list > button.active,.input-groups > button.active { background: var(--accent-soft); color: var(--text-primary); }.lesson-list button > span,.input-groups button > span { color: var(--accent-emerald); font-family: var(--font-mono); font-size: .6rem; }.lesson-list button div,.input-groups button div { display: flex; flex-direction: column; }.lesson-list strong,.input-groups strong { font-size: .75rem; }.lesson-list small,.input-groups small { margin-top: 2px; color: var(--text-muted); font-size: .6rem; }
.lesson-detail { overflow: hidden; }.lesson-intro { display: flex; align-items: flex-start; justify-content: space-between; gap: 30px; padding: 26px; border-bottom: 1px solid var(--border-subtle); }.lesson-intro h2 { margin-top: 6px; font-size: 1.35rem; }.lesson-intro p:last-child { max-width: 720px; margin-top: 8px; color: var(--text-secondary); font-size: .75rem; }.primary-action { display: flex; min-width: 180px; align-items: center; justify-content: space-between; padding: 10px 12px; background: var(--accent-emerald); border-radius: 4px; color: #08130f; font-size: .68rem; font-weight: 650; }.lesson-objective { margin: 20px 26px 4px; padding: 13px 15px; background: var(--bg-inset); border-left: 2px solid var(--accent-amber); }.lesson-objective strong { font-size: .68rem; }.lesson-objective p { margin-top: 4px; color: var(--text-secondary); font-size: .74rem; }.source-stops { padding: 18px 26px 26px; }.stops-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }.stops-heading span { color: var(--text-muted); font-size: .61rem; }.source-stop { display: grid; grid-template-columns: 32px minmax(0,1fr) 70px; align-items: center; gap: 12px; padding: 14px 0; border-bottom: 1px solid var(--border-subtle); }.stop-number { color: var(--text-muted); font-family: var(--font-mono); font-size: .6rem; }.confidence { font-family: var(--font-mono); font-size: .54rem; text-transform: uppercase; }.confidence.exact { color: var(--accent-emerald); }.confidence.unresolved { color: var(--accent-amber); }.source-stop h3 { margin-top: 3px; font-size: .78rem; }.source-stop p { margin-top: 3px; color: var(--text-muted); font-size: .65rem; }.source-stop code { display: inline-block; margin-top: 5px; color: var(--text-secondary); font-size: .61rem; }.source-stop button,.workflow-stage > button { padding: 6px 8px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); cursor: pointer; font-size: .61rem; }
.research-layout { display: grid; grid-template-columns: 270px minmax(0,1fr); gap: 14px; }.workflow-picker { overflow: hidden; }.workflow-picker > button { display: grid; width: 100%; min-height: 68px; grid-template-columns: 42px 1fr; align-items: center; gap: 8px; padding: 10px 16px; background: transparent; border: 0; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); cursor: pointer; text-align: left; }.workflow-picker > button:hover { background: var(--bg-surface-hover); }.workflow-picker > button.active { background: var(--accent-soft); box-shadow: inset 2px 0 var(--accent-emerald); color: var(--text-primary); }.workflow-picker > button > span { color: var(--accent-emerald); font-family: var(--font-mono); font-size: .62rem; }.workflow-picker button div { display: flex; flex-direction: column; }.workflow-picker button strong { font-size: .74rem; }.workflow-picker button small { margin-top: 3px; color: var(--text-muted); font-size: .59rem; }.template-contract { margin: 14px; padding: 12px; background: color-mix(in srgb,var(--accent-amber) 7%,var(--bg-inset)); border-left: 2px solid var(--accent-amber); }.template-contract strong { font-size: .64rem; }.template-contract p { margin-top: 4px; color: var(--text-muted); font-size: .59rem; line-height: 1.5; }.research-detail { overflow: hidden; }.research-hero { display: flex; align-items: flex-start; justify-content: space-between; gap: 32px; padding: 25px 26px; border-bottom: 1px solid var(--border-subtle); }.research-hero h2 { margin-top: 5px; font-size: 1.32rem; }.research-hero p:last-child { max-width: 720px; margin-top: 7px; color: var(--text-secondary); font-size: .73rem; line-height: 1.55; }.research-hero button { border: 0; cursor: pointer; }.research-question { margin: 18px 26px; padding: 12px 14px; background: var(--bg-inset); border-left: 2px solid var(--accent-blue); }.research-question strong { font-size: .65rem; }.research-question p { margin-top: 4px; color: var(--text-secondary); font-size: .7rem; }.workflow-config { margin: 0 26px; border: 1px solid var(--border-subtle); border-radius: 5px; overflow: hidden; }.config-heading { display: flex; align-items: center; justify-content: space-between; padding: 10px 13px; background: var(--bg-inset); }.config-heading > span { color: var(--text-muted); font-size: .58rem; }.workflow-config article { display: grid; min-height: 43px; grid-template-columns: minmax(190px,.8fr) minmax(220px,1fr) 72px; align-items: center; gap: 12px; padding: 7px 13px; border-top: 1px solid var(--border-subtle); }.workflow-config article > div { display: flex; gap: 8px; align-items: baseline; }.workflow-config code { color: var(--accent-amber); font-size: .62rem; }.workflow-config article span { color: var(--text-muted); font-size: .59rem; }.workflow-config article strong { font-size: .66rem; font-weight: 530; }.workflow-config article button { padding: 5px 7px; background: transparent; border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); cursor: pointer; font-size: .57rem; }.workflow-config .unresolved { color: var(--accent-amber); }.workflow-notes { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding: 20px 26px; }.workflow-notes > div { padding: 14px 16px; background: var(--bg-inset); }.workflow-notes ul { margin: 9px 0 0 16px; color: var(--text-secondary); font-size: .65rem; line-height: 1.6; }.workflow-caution { display: grid; grid-template-columns: 180px 1fr; gap: 18px; margin: 0 26px 24px; padding: 12px 14px; background: color-mix(in srgb,var(--accent-amber) 7%,var(--bg-panel)); border: 1px solid color-mix(in srgb,var(--accent-amber) 28%,var(--border-subtle)); }.workflow-caution strong { font-size: .65rem; }.workflow-caution p { color: var(--text-secondary); font-size: .63rem; line-height: 1.5; }
.input-layout { grid-template-columns: 230px minmax(420px,1fr) 310px; }.parameter-catalog,.parameter-detail { overflow: hidden; }.catalog-header { display: flex; min-height: 75px; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid var(--border-subtle); }.catalog-header h2 { margin-top: 4px; font-size: .95rem; }.parameter-search { display: flex; align-items: center; gap: 7px; color: var(--text-muted); font-size: .6rem; }.parameter-search input { width: 130px; padding: 6px 8px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-primary); font-size: .65rem; }.parameter-table { display: flex; flex-direction: column; }.parameter-table button { display: grid; min-height: 55px; grid-template-columns: 150px minmax(0,1fr) 70px; align-items: center; gap: 12px; padding: 9px 16px; background: transparent; border: 0; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); cursor: pointer; text-align: left; }.parameter-table button:hover,.parameter-table button.active { background: var(--bg-surface-hover); }.parameter-table button.active { box-shadow: inset 2px 0 var(--accent-emerald); }.parameter-table code { color: var(--accent-amber); font-size: .65rem; }.parameter-table span { font-size: .68rem; }.parameter-table small { color: var(--text-muted); font-size: .58rem; text-align: right; }.parameter-detail { padding-bottom: 16px; }.parameter-detail > h2,.parameter-detail > .parameter-role,.parameter-detail > dl,.parameter-detail > div:not(.detail-heading),.parameter-detail > button { margin-left: 16px; margin-right: 16px; }.parameter-detail > h2 { margin-top: 17px; font-size: .95rem; }.parameter-detail > h2 code { color: var(--accent-amber); }.parameter-role { margin-top: 6px; color: var(--text-secondary); font-size: .7rem; }.parameter-detail dl { margin-top: 16px; }.parameter-detail dl div { display: grid; grid-template-columns: 100px 1fr; gap: 7px; padding: 7px 0; border-bottom: 1px solid var(--border-subtle); font-size: .63rem; }.parameter-detail dt { color: var(--text-muted); }.parameter-detail dd { color: var(--text-secondary); }.interpretation-note { margin-top: 16px; padding: 11px; background: var(--accent-soft); border-left: 2px solid var(--accent-emerald); }.interpretation-note strong { font-size: .64rem; }.interpretation-note p { margin-top: 4px; color: var(--text-muted); font-size: .61rem; line-height: 1.5; }.source-link { display: flex; width: calc(100% - 32px); align-items: center; justify-content: space-between; margin-top: 12px; padding: 8px; background: var(--accent-soft); border: 1px solid color-mix(in srgb,var(--accent-emerald) 25%,var(--border-subtle)); border-radius: 4px; color: var(--accent-emerald); cursor: pointer; font-size: .61rem; }.source-link.secondary { margin-top: 6px; background: var(--bg-inset); border-color: var(--border-subtle); color: var(--text-secondary); }
.workflow-layout,.build-layout { display: flex; flex-direction: column; gap: 14px; }.workflow-intro,.build-intro { display: grid; grid-template-columns: 1.3fr 1fr; align-items: end; gap: 30px; padding: 22px 24px; }.workflow-intro h2,.build-intro h2 { max-width: 650px; margin-top: 5px; font-size: 1.2rem; }.workflow-intro > p,.build-intro > p { color: var(--text-muted); font-size: .68rem; line-height: 1.5; }.workflow-stages { display: flex; flex-direction: column; gap: 7px; }.workflow-stage { display: grid; grid-template-columns: 42px minmax(300px,1fr) 280px 75px; align-items: center; gap: 15px; padding: 17px 20px; }.stage-index { color: var(--border-strong); font-family: var(--font-mono); font-size: .7rem; }.stage-scope { font-family: var(--font-mono); font-size: .54rem; text-transform: uppercase; }.stage-scope.indexed { color: var(--accent-emerald); }.stage-scope.documented { color: var(--accent-blue); }.stage-scope.external { color: var(--accent-amber); }.stage-main h3 { margin-top: 3px; font-size: .82rem; }.stage-main p { margin-top: 4px; color: var(--text-muted); font-size: .64rem; }.stage-io { display: grid; grid-template-columns: 60px 1fr; gap: 3px 7px; font-size: .58rem; }.stage-io span { color: var(--text-muted); }.stage-io code { overflow: hidden; color: var(--text-secondary); text-overflow: ellipsis; white-space: nowrap; }.workflow-warning { padding: 13px 16px; background: color-mix(in srgb,var(--accent-amber) 8%,var(--bg-panel)); border: 1px solid color-mix(in srgb,var(--accent-amber) 30%,var(--border-subtle)); border-radius: 6px; color: var(--text-secondary); font-size: .66rem; }
.build-paths { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }.build-path { overflow: hidden; }.build-path-header { display: grid; grid-template-columns: 44px 1fr 66px; align-items: center; gap: 12px; padding: 18px; }.build-path-header > span { color: var(--accent-emerald); font-family: var(--font-mono); font-size: .6rem; }.build-path-header h3 { font-size: .84rem; }.build-path-header p { margin-top: 2px; color: var(--text-muted); font-size: .62rem; }.build-path-header button { padding: 6px; background: var(--bg-inset); border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); cursor: pointer; font-size: .59rem; }.build-path.selected .build-path-header { background: var(--accent-soft); }.build-path ol { border-top: 1px solid var(--border-subtle); list-style: none; }.build-path li { display: grid; grid-template-columns: 1fr minmax(190px,.8fr); gap: 15px; padding: 13px 18px; border-bottom: 1px solid var(--border-subtle); }.build-path li strong { font-size: .68rem; }.build-path li p { margin-top: 3px; color: var(--text-muted); font-size: .59rem; }.build-path li > code { align-self: center; overflow-x: auto; padding: 7px; background: var(--bg-inset); color: var(--accent-amber); font-size: .57rem; white-space: nowrap; }.build-proof { display: grid; grid-template-columns: 80px 1fr auto; align-items: center; gap: 8px; padding: 12px 18px; font-size: .58rem; }.build-proof span { color: var(--text-muted); }.build-proof code { color: var(--text-secondary); }.build-proof button { padding: 5px 7px; background: transparent; border: 1px solid var(--border-subtle); border-radius: 4px; color: var(--text-secondary); cursor: pointer; font-size: .57rem; }.prerequisite-panel { display: grid; grid-template-columns: 130px repeat(3,1fr); gap: 20px; padding: 18px 20px; }.prerequisite-panel > div { display: flex; flex-direction: column; gap: 4px; }.prerequisite-panel strong { font-size: .68rem; }.prerequisite-panel span,.prerequisite-panel > p:last-child { color: var(--text-muted); font-size: .59rem; line-height: 1.45; }.prerequisite-panel > p:last-child { grid-column: 2 / -1; }
@media(max-width:1200px){.input-layout{grid-template-columns:220px 1fr}.parameter-detail{grid-column:1/-1}.workflow-stage{grid-template-columns:36px 1fr 220px}.workflow-stage>button{display:none}.build-paths{grid-template-columns:1fr}.prerequisite-panel{grid-template-columns:120px 1fr 1fr}.prerequisite-panel>p:last-child{grid-column:2/-1}}
@media(max-width:850px){.page-header{align-items:flex-start;flex-direction:column}.guide-tabs{grid-template-columns:1fr 1fr}.learn-layout,.input-layout,.research-layout{grid-template-columns:1fr}.lesson-intro,.research-hero{flex-direction:column}.workflow-notes{grid-template-columns:1fr}.workflow-caution{grid-template-columns:1fr}.workflow-intro,.build-intro{grid-template-columns:1fr}.workflow-stage{grid-template-columns:30px 1fr}.stage-io{grid-column:2}.prerequisite-panel{grid-template-columns:1fr}.prerequisite-panel>p:last-child{grid-column:1}.source-stop{grid-template-columns:28px 1fr}.source-stop>button{grid-column:2;width:max-content}}
</style>
