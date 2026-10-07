# Parallel execution QA

Validated locally on 2026-10-06. This records application checks, not a WRF
compilation, observed MPI trace, performance benchmark, or numerical validation.

## Automated

- `npm test`: Python source/snapshot tests and TypeScript transformation tests.
- `npm run build`: TypeScript checking and Vite production build.
- `git diff --check`: no whitespace errors.
- Independent parallel companions regenerated from official WRF 4.7.1,
  official WRF 4.8.0, and the existing local QWRF 4.7.1 graph identity.
- Impeccable detector: no findings in the new parallel component. Two warnings
  concern pre-existing accent borders in the other execution views; those
  unrelated styles were preserved.

## Browser

Inspected desktop 1280 x 800 and mobile 390 x 844 with the local Vite server.
One combined inspection pass, one fix batch, and one confirmation pass.

- dmpar: four illustrative ranks, one thread per rank, thread control disabled.
- smpar: one process, four illustrative threads, rank controls disabled.
- Hybrid: four illustrative ranks with thread teams inside each rank.
- Serial: one process and one thread, both resource controls disabled.
- A selected `MPI_Wait` switches to excluded in smpar. Hiding excluded
  mechanisms gives a truthful empty state in the MPI-only exchange scope.
- An OpenMP worksharing directive switches to ignored in dmpar, with explicit
  explanation that the Fortran body remains sequential within a rank.
- Selecting a catalog event in the same source scope selects its correct stop.
- Source scopes, mesh dimensions, selected patch, previous/next, play/pause,
  speed, and excluded-mechanism controls respond.
- A 1 x 3 patch layout stays within the fixed mesh bounds with no text overflow.
- The mobile page has no horizontal overflow. The source diagram owns its
  horizontal scrolling; event cells have no vertical text overflow.
- `HALO_EM_A.inc` resolves its Registry fields and explicitly inferred
  RSL_LITE implementation links.
- The evidence drawer loads pinned C source around `MPI_Irecv` at
  `external/RSL_LITE/c_code.c:1016` for official 4.8.0. Closing restores focus.
- `MPI_Wait` at line 1027 shows the request and neighbor guard, without a global
  barrier claim. The startup barrier at `module_dm.F:217` shows its actual
  `local_communicator` argument and unresolved communicator membership.
- Both official snapshots and the local snapshot load their own parallel
  evidence when selected. Local and official source line locations can differ.
- Light and dark themes remain legible; no browser warnings/errors were captured.

Saved proof: `parallel-execution-desktop.jpg` and
`parallel-execution-mobile.jpg`. The temporary viewport override was reset.
