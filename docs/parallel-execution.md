# Parallel execution map

Open **Execution Map > Parallel execution**. The mode control represents build
assumptions, not an inspected executable or a change to WRF itself.

| Mode | Illustrated compute processes | OpenMP team |
| --- | --- | --- |
| Serial | One | One thread |
| dmpar | Adjustable MPI rank mesh | One thread per rank |
| smpar | One | Adjustable threads |
| dm+sm / hybrid | Adjustable MPI rank mesh | Adjustable threads per rank |

Switching modes updates the effective dimensions, disables irrelevant controls,
evaluates supported build guards, and changes event explanations. Excluded
mechanisms remain visible by default for comparison. Ignoring an OpenMP
directive does not remove its Fortran body. Thread-count and rank controls are
illustrative and do not write a namelist.

## Source intelligence

`indexer/parallel_analysis.py` uses the existing logical-statement normalizer
with original line mappings, preserves OpenMP sentinels and continuation
clauses, retains CPP alternatives and recognizable runtime IF guards, and
lexically tracks thread constructs. A balanced C-token scanner indexes MPI
calls inside RSL_LITE, retaining argument and request evidence. Registry
communication declarations come from the include-aware ARW Registry parser.

`npm run index`, `index:v4.7.1`, and `index:v4.8.0` now generate a companion
`<snapshot>.parallel.json` automatically. Refresh only this companion with:

```powershell
python tools/index_parallel.py --wrf-root E:\QWRF\WRF --graph public/data/local/qwrf-v4.7.1.json
python tools/index_parallel.py --wrf-root E:\QWRF\WRF-v4.7.1-clean --graph public/data/snapshots/wrf-v4.7.1.json
python tools/index_parallel.py --wrf-root E:\QWRF\WRF-v4.8.0-clean --graph public/data/snapshots/wrf-v4.8.0.json
```

The refresh refuses a commit or tracked-dirty-status mismatch with the graph.
The frontend also rejects mismatched snapshot identity or graph-generation
timestamps. The companion records its own generation time and a scanned-source
digest. Dirty status alone cannot prove that a modified checkout is unchanged;
regenerate both indexes after scientific-source edits.

## What the diagram establishes

- Calls and directives have exact source anchors for the selected snapshot.
- A halo include matching its Registry name identifies exchanged fields.
- Generated communication joins are labeled inferred. The map links to the
  generator and lets the user inspect the RSL_LITE implementation separately.
- `MPI_Wait` is request-specific completion, not a global barrier. An explicit
  MPI barrier concerns its supplied communicator. Collectives remain distinct.
- OpenMP worksharing and end-of-team joins are separate events. `NOWAIT`,
  `MASTER`, and `CRITICAL` endings are not labeled team barriers. `SINGLE` and
  `MASTER` do not depict simultaneous work by all threads.
- Neighbor coloring is an illustrative halo/Cartesian-axis model. Arbitrary
  MPI calls do not acquire invented neighbor topology. Actual peers, rank
  numbering, and communicator membership require source/runtime inspection.
- Monitor predicates do not imply global rank zero or a wait by other ranks.

Reference semantics: [MPI Wait](https://docs.open-mpi.org/en/main/man-openmpi/man3/MPI_Wait.3.html),
[MPI Barrier](https://docs.open-mpi.org/en/main/man-openmpi/man3/MPI_Barrier.3.html),
[OpenMP execution model](https://www.openmp.org/spec-html/5.2/openmpse3.html).

## Deliberate limits

This is an educational source-order walkthrough, not a runtime dependency graph,
profiler, measured scaling prediction, or simulation. Equal-width columns do
not encode durations. Loops and runtime alternatives remain unresolved; playback
can pass mutually exclusive source branches. An ordinary call outside a
lexically modeled OpenMP region is not proof of globally serial execution.

Only `DM_PARALLEL`, `STUBMPI`, and `_OPENMP` build assumptions are evaluated.
Other macros remain conditional. Thread context is lexical rather than
interprocedural, and parser diagnostics disclose unresolved constructs. MPI
thread-support levels, I/O quilting ranks, complete communicator membership,
arbitrary preprocessor expansion, and generated include contents are not
modeled. Uncompiled WRF is sufficient; scientific source is never modified.

The local development snapshot, official 4.7.1, and official 4.8.0 each have
independent evidence. Source references must not be transferred between them.

## Verification

`npm test` covers mode dimensions, guarded alternatives, conditional
participation, ignored OpenMP directives, request versus barrier semantics,
bounded neighbor topology, snapshot identity, multiline statements, C requests,
OpenMP continuation/join rules, reachable Registry includes, deterministic
fixtures, and actual halo/OpenMP/C-wait anchors in both official snapshots.
`npm run build` checks TypeScript and the static production build.
