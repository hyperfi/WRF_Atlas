# WRF Code Atlas

WRF Code Atlas is a local, source-grounded learning environment for the Weather Research and Forecasting model. It connects a user configuration choice to the Registry, runtime dispatch, executable Fortran calls, and model state in the WRF checkout being indexed.

The product goal is not to display the largest possible call graph. It is to make questions such as “what happens when I set this namelist value?” answerable with a small, navigable explanation whose claims link back to source.

## Source boundaries

- Atlas application: `E:\QWRF\WRF_Atlas`
- Authoritative WRF source: `E:\QWRF\WRF`

The WRF source tree is treated as read-only. The Atlas reads and indexes it; it does not modify it.

## Prerequisites

- Node.js and npm
- Python 3.10 or newer
- A local WRF checkout (the development default is `E:\QWRF\WRF`)

## Commands

```powershell
npm install
npm run index
npm test
npm run dev
npm run build
```

`npm run atlas` regenerates the index and then starts the development server.

## Architecture

```text
Local WRF checkout
  -> tolerant Python Fortran and Registry parsers
  -> normalized knowledge graph with source evidence
  -> Vue 3 application
  -> focused configuration, execution, physics, variable, and source views
```

The generated graph is written to `public/data/wrf-knowledge-graph.json`. It includes source identity, indexing time, node and edge data, confidence, and source locations.

## Evidence model

The UI distinguishes:

- `exact`: a relationship directly represented by an indexed Registry entry, Fortran call, definition, or reference;
- `inferred`: a join between separately evidenced facts, such as a Registry package constant matched to a symbolic `CASE` branch;
- `documentation`: an explanation derived from local documentation rather than executable source.

Presentation code must not create a missing relationship and label it `exact`. If the indexer cannot resolve a path, the UI should show the unresolved boundary.

## Current strongest vertical slice

The Namelist Lab traces one physics decision at a time. For example, on this checkout:

```text
sf_surface_physics = 2
  -> Registry package LSMSCHEME
  -> surface_driver dispatch branch
  -> exact calls indexed inside CASE (LSMSCHEME)
  -> live source navigation
```

Option names, constants, branch calls, and evidence locations come from the generated index.

The Execution view now derives the forward ARW path and timestep driver order from exact `CALLS` edges and source-line positions. It includes a conceptual playback view while explicitly marking the dynamics span and unresolved scheduling conditions as inferred.

The WRF Field Guide provides:

- source-led lessons that open indexed entities;
- research workflows for regional forecasting, urban heat islands, severe convection, and tropical cyclones, presented as checkout-valid exploration templates rather than universal scientific recommendations;
- a Registry-backed input parameter guide with links to the local `run/README.namelist`;
- a real-data workflow that marks WPS as external to this checkout;
- classic and CMake build paths quoted from the checkout's own documentation.

## Tests

The initial indexer tests cover:

- multiline Fortran call normalization and line mapping;
- symbolic `SELECT CASE` dispatch extraction;
- correct program-versus-subroutine call scope;
- rejection of `CALL` words inside diagnostic strings;
- Registry package source-file and source-line provenance.
- source-evidenced timestep phase construction.

Add a regression test whenever parser or graph-building behavior changes. Frontend transformation and browser-level acceptance coverage still need expansion.

## Known limitations

- The Fortran analysis is tolerant and hybrid, not a complete compiler frontend.
- Read/write direction for model fields is not yet reliable enough across all WRF calling conventions.
- Configuration consistency rules and `physics_suite` override behavior are not yet comprehensively indexed.
- Full caller paths from `wrf.exe` to every physics driver are not yet resolved through generated and preprocessed code.
- Enclosing `IF` conditions and scheduling predicates are not yet attached to every call edge; the execution storyboard labels this boundary.
- Physics and Variables still contain prototype-era interaction and presentation patterns that need the same evidence-first rebuild.
- The frontend bundle currently includes Cytoscape in the main chunk and should be code-split.

## Development priorities

1. Extract `INTENT` and argument associations for defensible variable journeys.
2. Index enclosing conditions, configuration validation, compatibility, override, and fatal-condition rules.
3. Add configuration comparison using only evidenced reachability.
4. Rebuild Physics and Variables with the scientific-workbench design and evidence contract.
5. Code-split route views and Cytoscape to reduce the initial frontend bundle.

## Adding another WRF subsystem

1. Identify its configuration and Registry definitions in the local checkout.
2. Add tolerant extraction with preserved line mappings.
3. Emit normalized nodes and evidence-bearing edges.
4. Add a small acceptance fixture plus a checkout-backed acceptance test.
5. Expose the subsystem progressively; do not render its complete graph by default.
6. Document unresolved preprocessing or generated-code boundaries as lower confidence.

See `AGENTS.md` for the complete product and scientific requirements and `docs/source-survey.md` for the current checkout survey.
