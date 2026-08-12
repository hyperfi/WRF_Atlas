# AGENTS.md — WRF Code Atlas

## Mission

Build an educational, beautiful, highly interactive web application called **WRF Code Atlas** inside this WRF source repository.

The purpose of WRF Code Atlas is to teach a researcher how the Weather Research and Forecasting (WRF) model actually works by connecting:

**user configuration → WRF decisions → executable code paths → subroutines/modules → exchanged variables → physical meaning**

The application must derive its knowledge primarily from the **actual WRF checkout in this repository**.

It must NOT become a manually written static WRF tutorial.

If this WRF checkout is modified, forked, or contains experimental code, the Atlas should eventually be able to re-index it and show those modifications.


## Project and source locations

The WRF Code Atlas project root is:

E:\QWRF\WRF_Atlas

The authoritative WRF source checkout to analyze is:

E:\QWRF\WRF

These are intentionally separate.

WRF_Atlas contains the application, indexer, generated data, tests, and documentation.

WRF contains the scientific WRF source and should normally be treated as read-only.

The Atlas must analyze the live WRF checkout at E:\QWRF\WRF rather than copying or embedding WRF source knowledge into the application.

The source location should be configurable, with E:\QWRF\WRF as the default development source root.



---

# 1. Core question the application must answer

A user should be able to ask, visually:

> “If I set this namelist option, what actually happens inside WRF?”

For example:

```fortran
sf_surface_physics = 2
```

The interface should discover from the local WRF source that this selects a particular land-surface package, then trace the relevant configuration machinery, package/constant definitions, physics driver dispatch, implementation routines, important arguments/state variables, and interactions with other physics components.

Do NOT assume the exact subroutine chain from general WRF knowledge.

**Discover it from this checkout and cite the actual files and line numbers.**

Likewise, the tool should answer questions such as:

- What happens when I change `mp_physics`?
- Which routines run for a particular PBL scheme?
- Which surface-layer scheme feeds a particular LSM?
- What does a physics suite actually activate?
- Where is a particular namelist variable defined?
- Where is its value checked?
- Which source files consume it?
- Which driver uses it to choose a parameterization?
- What state variables does that scheme read and modify?
- At what point in a timestep does the scheme execute?
- What would change in the execution path if I chose another value?
- Why is one routine active while another is inactive?
- What does a variable such as `HFX`, `QFX`, `TSK`, `SMOIS`, `PBLH`, etc. represent and where does it travel?
- Which components of WRF communicate with each other?
- Which things happen during initialization versus every RK step versus at configured intervals?

The experience should make a huge scientific Fortran application feel understandable.

---

# 2. Product philosophy

This application is not primarily a source-code browser.

It is an **interactive executable mental model of WRF**.

Use three synchronized conceptual layers:

## Layer A — Configuration

“What did I tell WRF to do?”

Examples:

- `namelist.input`
- physics selections
- domain settings
- dynamics options
- timestep controls
- nesting
- radiation intervals
- surface options
- physics suites

## Layer B — Software execution

“What code does that choice activate?”

Examples:

- WRF startup
- initialization
- model configuration
- domain creation
- solver
- RK timestep
- physics drivers
- scheme dispatch
- individual physics implementations
- I/O

## Layer C — Physical meaning

“What physical process is represented here?”

Examples:

- microphysics
- radiation
- land-surface exchange
- surface layer
- PBL
- cumulus convection
- soil moisture
- heat flux
- moisture flux
- atmospheric dynamics

When the user interacts with one layer, the other layers should respond.

For example, clicking a land-surface scheme should highlight:

```text
Namelist selector
        ↓
Configuration value
        ↓
Registry/package association
        ↓
Physics driver
        ↓
Dispatch condition
        ↓
Scheme routine(s)
        ↓
Important state variables
        ↓
Interactions with surface layer and PBL
```

---

# 3. Absolute rule: source-ground everything

The Atlas must distinguish between:

1. **directly proven from source**
2. **strongly inferred from source**
3. **documentation-derived explanation**

Every displayed execution relationship should ideally have evidence such as:

```text
phys/module_....F : lines xxx–yyy
```

Do not fabricate call relationships.

Do not claim that a routine executes merely because its source file exists.

A graph edge such as:

```text
surface_driver → some_scheme
```

should be backed by an actual call, dispatch branch, macro-expanded relationship, generated configuration relationship, or clearly marked inference.

Add a small evidence control to relevant UI items:

**Why?**

Clicking it should show something like:

```text
Activated because

sf_surface_physics = 2
    ↓
Registry associates value 2 with package ...
    ↓
surface_driver receives config_flags%sf_surface_physics
    ↓
driver dispatch selects ...
    ↓
CALL ...
```

with clickable source references.

---

# 4. Do not alter scientific WRF source code

Treat the existing WRF source tree as read-only unless an extremely strong reason exists.

Create the application under something like:

```text
tools/wrf-code-atlas/
```

Do not refactor, format, rename, or “clean up” existing WRF Fortran.

Do not make changes merely to simplify parsing.

The educational tool must adapt to WRF, not the reverse.

---

# 5. Technology

Build the UI with:

```text
Vue 3
TypeScript
Vite
```

Use a clean component architecture.

For graph visualization, evaluate an appropriate library such as Cytoscape.js, Vue Flow, or another mature graph library. Select the one that performs well for medium/large interactive graphs.

For source indexing, use:

```text
Python 3
```

under:

```text
tools/wrf-code-atlas/indexer/
```

Prefer a tolerant source-analysis pipeline over requiring the complete WRF program to compile.

The application should not need a cloud backend.

Ideal architecture:

```text
WRF source
   ↓
Python source indexer
   ↓
generated normalized JSON knowledge graph
   ↓
Vue application
   ↓
interactive visualization
```

After indexing, the UI should be capable of running as a static local web application.

No OpenAI API or external LLM should be required for normal operation.

---

# 6. First task: survey this exact WRF checkout

Before implementing the UI, inspect this repository thoroughly.

Determine locally:

- repository/version/commit
- major source directories
- WRF executable entry point
- initialization path
- configuration/namelist machinery
- Registry organization
- ARW solver entry path
- timestep integration structure
- physics driver architecture
- land-surface dispatch
- microphysics dispatch
- radiation dispatch
- PBL dispatch
- cumulus dispatch
- relevant generated files
- preprocessor usage
- significant `.inc` files
- how physics constants/options are represented
- how package declarations are generated or consumed

Do not rely on filenames from this AGENTS.md if the checkout differs.

Generate:

```text
tools/wrf-code-atlas/docs/source-survey.md
```

containing what was actually found.

Include source paths and important symbols.

Then continue implementation automatically.

Do not stop after producing the survey.

---

# 7. Indexer

Create a WRF-aware static analysis/indexing system.

It should scan relevant files including, as appropriate:

```text
*.F
*.F90
*.f90
*.inc
Registry/*
run/README.namelist
test/*/namelist*
```

and other important configuration files discovered during the survey.

The parser should understand enough Fortran/preprocessor structure to identify at minimum:

- PROGRAM definitions
- MODULE definitions
- SUBROUTINE definitions
- FUNCTION definitions
- `USE` relationships
- `CALL` relationships
- INCLUDE relationships
- `#include`
- conditional preprocessor blocks
- `SELECT CASE`
- `CASE`
- relevant `IF` conditions
- `config_flags%...`
- `model_config_rec`
- `nl_get_*`
- namelist/configuration references
- routine arguments
- source locations

Do not use a completely naive line-by-line regex implementation.

WRF uses continuations, preprocessing, generated code, and macros.

Create a tolerant parsing pipeline that first normalizes logical Fortran statements while preserving original line mappings.

If a suitable parser such as `fparser` is useful and can be added without making the project fragile, use it selectively. A hybrid parser is acceptable and may be preferable for WRF.

The indexer must survive syntax it does not understand.

Unknown syntax should produce diagnostics, not terminate the scan.

---

# 8. Registry intelligence

The WRF Registry is extremely important.

Explicitly parse Registry structures that describe:

- configuration values
- packages
- state variables
- dimensions
- I/O behavior
- configuration predicates
- related generated state/configuration concepts

Build machine-readable relationships such as conceptually:

```text
namelist option
      ↓
allowed/configured value
      ↓
package
      ↓
state/configuration implications
```

Do not hardcode the Noah example as the underlying implementation.

It is allowed as a test scenario, but the result must be derived from Registry/source analysis.

---

# 9. Knowledge graph data model

Design a normalized graph.

Possible node kinds include:

```text
program
module
subroutine
function
driver
physics_scheme
namelist_option
namelist_group
configuration_constant
registry_package
state_variable
source_file
include
physical_process
phase
```

Possible edges include:

```text
CALLS
USES
INCLUDES
DEFINED_IN
SELECTED_BY
ACTIVE_WHEN
READS_CONFIG
READS_VARIABLE
WRITES_VARIABLE
PASSES_VARIABLE
BELONGS_TO
EXECUTES_DURING
INITIALIZES
PROVIDES_TO
DEPENDS_ON
CONFLICTS_WITH
OVERRIDES
```

An edge should support metadata such as:

```ts
{
  source: "...",
  target: "...",
  type: "ACTIVE_WHEN",
  condition: "sf_surface_physics == ...",
  evidence: [
    {
      path: "...",
      startLine: 123,
      endLine: 130
    }
  ],
  confidence: "exact" | "inferred" | "documentation"
}
```

Preserve exact source locations.

---

# 10. WRF lifecycle view

Create a high-level visual explanation of a WRF run.

The graph should begin small and understandable.

For example, after verifying the actual checkout, it may conceptually resemble:

```text
wrf.exe
 │
 ├─ initialization
 │    ├─ configuration
 │    ├─ domain setup
 │    ├─ input
 │    └─ physics initialization
 │
 ├─ model integration
 │    │
 │    ├─ timestep
 │    │    ├─ dynamics
 │    │    ├─ microphysics
 │    │    ├─ radiation
 │    │    ├─ surface
 │    │    ├─ PBL
 │    │    ├─ cumulus
 │    │    └─ ...
 │    │
 │    └─ output / nesting / boundary handling
 │
 └─ finalize
```

This is only a conceptual example.

Derive the actual execution structure from the checkout.

The initial graph must avoid showing thousands of nodes.

Use progressive disclosure:

```text
Concept
   ↓ click
Driver
   ↓ click
Dispatch
   ↓ click
Subroutine
   ↓ click
Detailed calls
```

---

# 11. The Namelist Lab

This should be one of the flagship features.

Provide an editable `namelist.input` experience.

Support:

### A. Paste/load namelist

A user can paste or load a namelist.

Parse it into groups and parameters.

### B. Friendly parameter controls

Important parameters can also be modified through selectors/sliders/checkboxes.

Changing the GUI updates the namelist representation.

Changing the namelist updates the GUI.

### C. Live execution graph

When a relevant parameter changes, update the graph immediately.

Example concept:

```text
sf_surface_physics

0 → ...
1 → ...
2 → ...
3 → ...
4 → ...
```

The names MUST be discovered from this checkout or authoritative metadata available locally.

### D. Explain the consequence

For a selected value show:

```text
You selected
    ↓
what this represents
    ↓
which package becomes active
    ↓
which initialization logic changes
    ↓
which driver dispatch changes
    ↓
which scheme routine becomes reachable
    ↓
important input/output fields
```

### E. Inactive branches

Show alternatives as faded branches.

Hovering one should say:

```text
Inactive because:
sf_surface_physics = 2
but this branch requires ...
```

This is pedagogically important.

---

# 12. “What changed?” configuration comparison

Allow two configurations to be compared.

Example:

```text
Configuration A
sf_surface_physics = X

Configuration B
sf_surface_physics = Y
```

Show a graph diff:

```text
common path       unchanged
A-only path       removed
B-only path       activated
```

Also summarize:

```text
Changed namelist values
Changed packages
Changed drivers/dispatch branches
Changed subroutine reachability
Changed important state variables
Changed physical assumptions
```

This could become one of the most powerful ways to learn WRF.

---

# 13. Scheme Explorer

Create an explorer organized by physical process:

```text
Microphysics
Cumulus
Longwave radiation
Shortwave radiation
Surface layer
Land surface
PBL
Dynamics
Diffusion
Nesting
I/O
...
```

A scheme page should show:

```text
Scheme name

Physical purpose
Namelist selector
Associated values/constants
Source module(s)
Initialization
Runtime driver
Runtime implementation routines
Important inputs
Important outputs/state modifications
Related schemes
Configuration constraints
Source evidence
```

Add a compact diagram.

---

# 14. WRF Timestep Storyboard

Create an educational visualization of **one conceptual WRF timestep**.

This should feel like a timeline rather than a raw graph.

Something like:

```text
TIME t
  │
  ├── dynamics work
  │
  ├── RK stage
  │
  ├── physics driver
  │      │
  │      ├── radiation [only when scheduled]
  │      ├── surface
  │      ├── PBL
  │      ├── microphysics
  │      └── ...
  │
  ├── nesting/boundary operations
  │
  └── output [if interval reached]
       ↓
TIME t + Δt
```

But derive the ordering and conditions from actual source rather than treating this diagram as truth.

Allow:

- Play
- Pause
- Next stage
- Previous stage
- speed control

As the animation moves, highlight the involved code modules.

This is an educational animation, not a simulation of numerical values.

---

# 15. Variable Journey

Allow search for a WRF variable such as:

```text
HFX
QFX
TSK
SMOIS
PBLH
U10
T2
QVAPOR
```

Show a “journey”:

```text
Registry definition
       ↓
allocation/state
       ↓
initialization
       ↓
passed into driver
       ↓
used/modified by scheme
       ↓
consumed elsewhere
       ↓
written to output
```

Where static analysis cannot determine read-versus-write reliably, say so.

Do not invent semantic direction.

This view should help answer:

> “Where did this WRF field come from?”

and:

> “Who changes it?”

---

# 16. Physics interaction map

The user should understand that WRF parameterizations are not isolated.

Build a conceptual interaction view such as:

```text
            Radiation
                │
                ↓
Atmosphere ↔ Surface Layer
                │
                ↓
          Land Surface
                │
       heat / moisture flux
                ↓
              PBL
                │
                ↓
          Atmosphere
```

Other components should be added based on evidence.

Distinguish:

- conceptual physical coupling
- actual routine calls
- shared/passed state

These are not always the same thing.

Use different edge styles and explain the distinction.

---

# 17. “Why did WRF choose this?” inspector

Every important active component should have:

**WHY ACTIVE?**

Example:

```text
Noah LSM

Why active?

1. namelist.input specifies ...
2. Registry/configuration maps that value to ...
3. model configuration stores ...
4. surface driver receives ...
5. dispatch branch matches ...
6. implementation routine is invoked
```

Every step should link to source evidence when available.

This feature is central to the application.

---

# 18. Source viewer

Clicking evidence should open an integrated source viewer.

Requirements:

- syntax-highlight Fortran reasonably
- show file path
- show line numbers
- highlight relevant lines
- display routine/module breadcrumb
- allow “show callers”
- allow “show callees”
- allow “show config references”
- allow “show variables”
- allow returning to previous graph

Do not duplicate the entire repository into generated JSON.

Load source intelligently in development, or generate only required snippets/index metadata.

---

# 19. Search / command palette

Provide fast fuzzy search.

Search entities including:

```text
sf_surface_physics
surface_driver
Noah
HFX
module_physics_init
mp_physics
radiation_driver
PBLH
```

Search results should label their type.

Example:

```text
sf_surface_physics          NAMELIST
surface_driver              SUBROUTINE
module_surface_driver       MODULE
HFX                         STATE VARIABLE
```

---

# 20. Guided educational tours

Add several interactive tutorials once the core exploration system works.

Initial lessons:

### Lesson 1 — How WRF starts

Follow the program from executable entry through configuration and into integration.

### Lesson 2 — Anatomy of one timestep

Show major dynamics/physics stages.

### Lesson 3 — Choosing a land-surface model

Start with the relevant namelist selector and follow the execution path.

### Lesson 4 — Choosing microphysics

Change the microphysics option and watch dispatch change.

### Lesson 5 — Follow a field

Trace a representative state variable through the model.

### Lesson 6 — Physics suites

Show how a suite influences multiple physics selectors and where the corresponding configuration logic exists.

Tours must use the generated graph rather than a second hardcoded model of WRF whenever possible.

---

# 21. Researcher mode vs learning mode

Provide two levels of detail.

## Learning mode

Prioritize:

- physical meaning
- major components
- clear diagrams
- minimal Fortran details
- explanations
- terminology tooltips

## Researcher mode

Reveal:

- exact subroutine names
- source paths
- line numbers
- conditions
- configuration constants
- complete caller/callee relationships
- state-variable relationships
- preprocessing information
- confidence/evidence metadata

Changing mode should not navigate away.

It should change information density.

---

# 22. Physics suite handling

Investigate how `physics_suite` is processed in this checkout.

Show:

```text
physics_suite
      ↓
individual option values
      ↓
any user overrides
      ↓
consistency checks
      ↓
resulting active schemes
```

Pay particular attention to configuration-checking routines and any code that adjusts or validates namelist combinations.

If WRF modifies a user's requested configuration during setup, try to make that behavior visible.

---

# 23. Configuration constraints

Inspect WRF's consistency-checking logic.

Extract useful relationships such as:

```text
requires
compatible with
incompatible with
ignored unless
only valid when
automatically changed when
fatal if combined with
```

These should appear in the Namelist Lab.

Do not attempt to replace WRF's own validation.

The Atlas is educational.

For each rule, link back to the actual validation code.

---

# 24. Optional runtime evidence

Once the static Atlas works, add the ability to import:

```text
rsl.out.*
rsl.error.*
```

and other normal WRF textual logs when useful.

Call this:

**Observed Run**

The static graph answers:

> “What can/should execute for this configuration?”

Runtime logs can answer:

> “What did this particular run visibly report?”

Keep these distinct.

If the logs contain recognizable routine/debug messages, map them onto graph nodes.

Never claim that absence from an `rsl` log proves a routine did not execute.

---

# 25. Optional namelist + run workspace

A user should eventually be able to load:

```text
namelist.input
rsl.out.0000
rsl.error.0000
```

and get a page summarizing:

```text
WRF configuration
active physics
domains
important timings
execution evidence
warnings/errors
relevant source locations
```

This is a later feature; do not block the static Atlas MVP on it.

---

# 26. UI design

The interface should look like a modern scientific visualization application, not an admin dashboard.

Desired feeling:

**interactive scientific atlas + code debugger + educational simulation**

Use:

- excellent typography
- generous spacing
- restrained meteorological visual language
- subtle grid/topography/weather-inspired background elements
- smooth graph transitions
- rounded but professional panels
- clear hierarchy
- dark and light modes
- responsive layout
- tasteful animation

Avoid:

- excessive gradients
- childish illustrations
- giant dashboard cards everywhere
- visual clutter
- rainbow-colored graphs
- forcing all information onto one screen

Graph categories should be visually distinguishable but restrained.

---

# 27. Suggested main navigation

Use approximately:

```text
Overview
Namelist Lab
Execution Map
Physics
Variables
Compare
Guided Tours
Source
```

The exact navigation can evolve based on UX.

---

# 28. Home screen

The landing screen should immediately communicate what the tool does.

Potential centerpiece:

```text
What do you want to understand?

[ Trace my namelist ]
[ Explore a WRF timestep ]
[ How does Noah LSM run? ]
[ Explore microphysics ]
[ Follow a variable ]
[ Browse the entire architecture ]
```

Below it show the indexed source identity:

```text
WRF Code Atlas
Indexed checkout: <git commit>
Branch: <branch>
Working tree: clean/modified
Indexed at: ...
```

This reminds the user that the Atlas describes the code they actually have.

---

# 29. Performance

The complete WRF call graph may be enormous.

Never render everything simultaneously.

Use:

- semantic grouping
- lazy expansion
- graph filtering
- depth limits
- collapsible modules
- worker-based graph processing if necessary
- memoization
- efficient search indexes

The first view should contain tens of nodes, not thousands.

---

# 30. Source provenance

Generate metadata including:

```text
git commit
git branch
dirty status
index generation timestamp
indexer version/schema
```

The app should warn when generated graph data appears stale relative to the source checkout.

Provide a simple command to regenerate it.

---

# 31. Developer experience

From:

```text
tools/wrf-code-atlas/
```

aim for commands similar to:

```bash
npm install
npm run index
npm run dev
npm run build
npm test
```

If useful:

```bash
npm run atlas
```

may perform indexing followed by development startup.

Document exact commands in the project's README.

Do not require compiling WRF to use the Atlas.

---

# 32. Testing

Add meaningful tests.

Indexer tests should cover:

- multiline Fortran calls
- subroutine detection
- module detection
- USE relationships
- CALL relationships
- source line mapping
- config flag detection
- SELECT CASE detection
- Registry package parsing
- Registry configuration parsing
- unsupported syntax handling
- deterministic output

Frontend tests should cover important transformations.

Add at least one end-to-end test for an actual known configuration path discovered from this checkout.

A particularly useful acceptance test is:

```text
select the local checkout's value corresponding to Noah LSM
→ Atlas identifies the scheme
→ shows configuration evidence
→ shows the surface driver path
→ links to actual source
```

Do not encode an assumed implementation path merely to make the test pass.

---

# 33. Validation against real WRF source

Before declaring a relationship correct:

1. locate the namelist/configuration definition
2. locate any constants/package definitions
3. locate runtime use
4. locate dispatch
5. locate actual call target
6. confirm names against this checkout
7. retain source evidence

Where steps cannot be resolved automatically, display a lower confidence level rather than inventing data.

---

# 34. Scope for MVP

WRF is enormous.

For the first complete version, prioritize:

```text
WRF-ARW
wrf.exe
real-data workflow where relevant
namelist configuration
model startup
ARW integration
physics drivers
land-surface physics
surface layer
PBL
microphysics
radiation
cumulus
important Registry state
```

Architect the data model so these can later be added cleanly:

```text
WPS
WRFDA
WRF-Chem
WRF-Hydro
idealized cases
nesting deep dives
I/O architecture
parallel decomposition
```

Do not let those extensions prevent completion of the first useful application.

---

# 35. Suggested implementation phases

## Phase 0 — Understand WRF

Inspect source.

Write `docs/source-survey.md`.

Identify exact architecture.

## Phase 1 — Build source intelligence

Implement Registry parser, Fortran source scanner, symbol table, call graph, configuration references, conditions and source evidence.

Produce deterministic JSON.

## Phase 2 — Core Atlas UI

Implement:

- home
- execution map
- graph exploration
- source evidence
- search
- source viewer

## Phase 3 — Namelist intelligence

Implement:

- namelist parser
- option explorer
- active/inactive path visualization
- configuration comparison

## Phase 4 — Educational experience

Implement:

- physical-process metadata
- timestep storyboard
- Why Active inspector
- guided tours
- researcher/learning modes

## Phase 5 — Polish

Implement:

- responsive UX
- transitions
- accessibility
- tests
- documentation
- performance improvements

## Phase 6 — Runtime evidence

If appropriate, add optional RSL-log importing.

---

# 36. Important engineering behavior

Do not spend the entire task planning.

Survey enough source to understand the architecture, document it, then implement.

Do not ask for permission after each phase.

Continue until there is a functioning application.

If something cannot be fully solved, implement the robust subset and document the limitation.

Prefer working vertical slices.

For example, make this path genuinely excellent early:

```text
namelist
   ↓
sf_surface_physics
   ↓
selected local LSM package
   ↓
configuration
   ↓
surface driver
   ↓
actual scheme
   ↓
important state variables
   ↓
source lines
```

Then generalize the architecture to other physics families.

---

# 37. Anti-goals

Do NOT build:

- just a folder tree
- just a static Mermaid diagram
- just a call graph
- just a namelist editor
- just searchable documentation
- just generated prose about Fortran files
- a UI containing hardcoded WRF knowledge disconnected from the source
- an LLM chatbot pretending to understand the repository

Those can be components, but none of them is the product.

The product is the relationship between all of them.

---

# 38. The “aha” experience

The strongest interaction should be something like:

The user opens **Namelist Lab**.

They change:

```text
sf_surface_physics
```

The application animates the relevant branch.

A panel says conceptually:

```text
You changed the land-surface model.

This configuration value activates:
<scheme discovered from this checkout>

WHY?

<Registry/config evidence>

WHEN DOES IT RUN?

<position in timestep>

HOW DOES WRF REACH IT?

wrf.exe
 → ...
 → physics timestep
 → surface driver
 → dispatch
 → implementation

WHAT DOES IT WORK WITH?

surface-layer scheme
soil fields
surface temperature
heat/moisture fluxes
PBL

SHOW ME THE CODE
```

Clicking **SHOW ME THE CODE** opens the exact source lines.

Changing the option again causes the old branch to fade and the newly activated branch to appear.

That experience is the north star for this project.

---

# 39. Final deliverable

The repository should contain a polished application under:

```text
tools/wrf-code-atlas/
```

with:

```text
README.md
package.json
src/
indexer/
generated/
docs/
tests/
```

The README should explain:

- what WRF Code Atlas is
- prerequisites
- indexing
- development
- production build
- architecture
- data provenance
- limitations
- how to add support for new WRF subsystems

At completion, run all reasonable tests and the production build.

Fix issues found.

Leave the existing WRF scientific code untouched.

The final result should be useful enough that a researcher unfamiliar with WRF internals can spend an hour exploring it and come away with a substantially better mental model of how WRF turns configuration choices into an executing atmospheric model.