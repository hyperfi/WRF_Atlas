# Atlas interface refinement

Completed on 2026-10-01 against the critique snapshot
`2026-09-30T20-04-46Z__src-app-vue.md`.

## Priorities addressed

1. Namelist Lab places configuration and its explanation before the graph.
   Desktop shows them side by side; phone shows them sequentially.
   Import actions remain inside the phone viewport.
2. Learning mode presents Registry meanings and units in physical field groups.
   Researcher mode retains detailed source relationships and counts.
   Mode changes preserve the current field or scheme.
3. Search ranks exact matches before substring matches and preserves entity
   identity in navigation. Native modal behavior plus keyboard boundary handling
   contains search focus; Escape works outside the input and restores the trigger.
4. Evidence excerpts, source controls, caveats, and timestep details use larger
   text. Muted text tokens have stronger contrast in both themes.
5. Physics selectors start at the visible left edge with pressed-state semantics
   and arrow/Home/End navigation. Phone navigation is a labeled modal instead of
   a permanent abbreviation rail. Graphs offer a keyboard trace list built from
   the same visible nodes and relationships, with selection announcements.

## Validation

- `npm test`: 16 Python tests and 10 frontend tests passed.
- `npm run build`: TypeScript checking and Vite production build passed.
- `git diff --check`: passed.
- Browser checks at 1280 x 720 and 390 x 844, including dark and light themes.
- Exact HFX search ranked first and opened `/variables?field=hfx`; Registry
  meaning and units appeared. Researcher mode showed additional technical detail.
- Noah LSM package search opened `/physics/land_surface?scheme=2` without
  silently changing the current configuration.
- Changing the Lab to Noah-MP updated the branch, implementation call, field
  groups, and Registry evidence. Registry line 3213 loaded in the evidence drawer
  for the selected official WRF 4.8.0 snapshot.
- Search Shift+Tab stayed inside the dialog; Escape from a scope button closed
  it and returned focus to search. Phone menu navigation closed its modal.
- Trace-list selection announced `Selected sf_surface_physics` and exposed the
  same evidence controls as canvas selection.
- Browser console: no captured errors or warnings in the checked workflows.

## Limits and detector disposition

Learning explanations are deliberately bounded: Registry descriptions establish
field meaning, while matching call arguments indicate possible handoffs, not
proven read/write direction or observed execution. Value-to-branch joins remain
labeled inferred. No source reindex or scientific WRF edits were performed.

The single post-edit Impeccable detector scan retained 18 incumbent findings:
15 accent-stripe warnings, two width-transition warnings, and one background-grid
advisory. Source-line highlights remain intentional evidence cues. Other
incumbent tour/comparison accents and transitions were left outside this scoped
refinement; reduced-motion preferences suppress animation. This is not a full
accessibility certification or a new indexer correctness audit.
