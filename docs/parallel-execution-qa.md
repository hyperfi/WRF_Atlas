# Nested parallel lanes verification

Date: 2026-10-07. Scope: parallel execution view, not WRF runtime validation.

## Automated checks

- `npm test`: 25 Python tests and 22 frontend tests passed.
- `npm run build`: TypeScript check and production Vite build passed.
- New regressions cover source selection identity, empty-filter recovery, stable
  source pages, conservative thread extents and request associations, and neutral
  rank patches for unresolved communicator membership.
- The official 4.8.0 fixture resolves the solver parallel region at lines
  491-533 and the RSL_LITE `yp_recv` post/wait anchors at 1016/1027.

## Browser checks

- Serial: one process/one thread; no thread tracks.
- dmpar: multiple illustrative ranks; disabled thread selector displays one.
- smpar: one process with thread tracks.
- Hybrid: rank lanes containing thread tracks and local team joins.
- Hiding excluded mechanisms and switching to Serial gives an explicit notice
  when the selected OpenMP directive is removed; a nearby source stop is selected.
- Returning to a compatible mode preserves enabled rank preferences.
- Keyboard navigation updates selected source evidence; the selected node
  remains within the canvas on mobile. Horizontal scrolling stays inside it.
- MPI_Wait search reaches results 13-23 of 23 via pagination.
- The RSL_LITE request association exposes both source anchors and labels the
  association inferred. The source drawer opens the corresponding line/commit.
- No console warnings/errors were observed in the development tab.
- CSS viewports 1440x900 and 390x844 had no document overflow. An additional
  compact view was checked at 355x767.
- The reported Local source site caption collision is corrected. The compact
  Serial lane has 13px measured clearance between node and caption bounds.

## Independent review

The finish reviewer confirmed caption separation and the approved lane structure.
It requested one semantic correction: communicator events must not highlight
every other illustrative patch as a peer. The corrected partner helper returns
no neighbors for barriers/collectives, with a focused regression.

The detector found no warnings in the parallel components. Two pre-existing
colored-border warnings in other execution views remain outside this change.

Captures live in `.impeccable/review/`. Initial captures were clipped by a browser
zoom/DPR capture mismatch, not demonstrated application overflow. Physical-pixel
clip bounds (CSS dimensions multiplied by the measured 1.1 DPR) correct the
full-width capture. `desktop-complete.jpg` supersedes the initial cropped frames.
This verification is
of the educational interface, not runtime participation, timing, numerical WRF
results, or performance.

## Documentation check

The documentation finish check compared `ParallelLanes.vue` and
`ParallelExecution.vue` with `src/styles/index.css`, the incumbent
`ExecutionMapView.vue`, and the implemented parallel helpers/regressions.
The documented lane extents, join/request styling, selection retention, source
pages, compact controls, detail modes, catalog pagination, and list/keyboard
alternatives match those implementations. Shared theme tokens, font stacks,
and compact corner treatments remain the existing workbench vocabulary.
Communicator barriers and collectives return no illustrative neighbors; the
mesh therefore leaves other patches neutral.

This was a code/documentation comparison, without a new browser session or
test run. Browser measurements and test/build outcomes above are the recorded
verification evidence. No root `PRODUCT.md`, `DESIGN.md`, or design sidecar was
created for this view extension.
