# Presentation pass validation

Checked against the tracked WRF 4.8.0 snapshot in the local Vite application.

- Variables: opening HFX and selecting it again returns to the unselected view and clears the field route query.
- Variables: Back to variables closes details while preserving an existing `hfx` search filter.
- Field journey: Registry, interface-name matches, and call-site-name matches use separate evidence groups; Physics-linked HFX prioritizes Noah branch handoffs.
- Evidence drawer: HFX Registry evidence loads the pinned source, highlights line 1979, and preserves original surrounding line numbers. Opening evidence does not change the page route.
- Evidence drawer: Escape dismisses it and restores focus to the source button. A full-source link remains available.
- Full source: Back to trace restores the Noah scheme and the Registry inspector stop after a fresh app load; no browser console errors were reported during this check.
- Physics: Noah opens a dedicated inspector with configuration, Registry, driver, and branch-call stops. The inspector distinguishes a current selection from a preview. Call targets are not presented as an unconditional sequence.
- Presentation: light and dark views checked visually; large call lists remain collapsed until requested.
- Responsive: 390 × 844 viewport checked for visible header controls, a compact navigation rail, horizontal physics-family navigation, readable field details, and a usable Back button. Body width remained 390 pixels with no document-level horizontal overflow. Temporary viewport override was reset afterward.

Automated coverage: source excerpt line mapping/range highlights, bounded rendering, out-of-range anchors, and target deduplication. Parser/indexer regression tests remain unchanged except that the frontend test command now includes these checks.

Scope: no scientific WRF source or generated knowledge snapshots were changed. Observed Run/RSL import is not part of this pass. Static source evidence still cannot establish unconditional execution or field read/write direction.
