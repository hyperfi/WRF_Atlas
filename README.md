# WRF Code Atlas

WRF Code Atlas is a source-grounded Vue application for learning how WRF turns configuration into executable code and physical model behavior. It connects namelist choices to Registry definitions, dispatch branches, routines, variables, and exact source evidence.

The public Atlas is static. It does **not** download or compile WRF in a visitor's browser and does not require a cloud backend. The Python indexer reads a WRF checkout ahead of time and produces versioned JSON snapshots that the Vue application can publish with GitHub Pages.

## Source layout

The application and WRF checkouts are intentionally separate:

| Folder | Purpose | Mutation policy |
| --- | --- | --- |
| `E:\QWRF\WRF_Atlas` | Atlas application, indexer, tests, and public snapshots | Atlas development |
| `E:\QWRF\WRF` | Original v4.7.1 QWRF research checkout | Preserve as historical working source |
| `E:\QWRF\WRF-v4.7.1-clean` | Clean official v4.7.1 baseline | Read-only |
| `E:\QWRF\WRF-v4.8.0-clean` | Clean official v4.8.0 baseline | Read-only |
| `E:\QWRF\WRF-v4.8.0-qwrf` | v4.8.0 worktree on branch `qwrf-v4.8.0` | QWRF migration only |

See `docs/migration/wrf-4.8-migration.md` for commit identities, backups, and validation gates.

## Local development

Prerequisites are Node.js 22+, npm, Python 3.10+, and a local WRF checkout.

```powershell
npm install
npm run index
npm test
npm run dev
```

`npm run index` reads `E:\QWRF\WRF` by default and writes an ignored local snapshot to `public/data/local/`. Set `WRF_SOURCE_ROOT` to use another checkout:

```powershell
$env:WRF_SOURCE_ROOT = 'D:\source\WRF'
npm run index
```

In development, the application detects that local snapshot and offers it in the source selector. Local source evidence is loaded through the Vite development server, so clicking source references opens files from that checkout.

For a separate Ubuntu WRF build walkthrough, open **Guided Tours → Build locally → Ubuntu + gfortran** in the Atlas. It covers a serial `em_quarter_ss` idealized case with `NETCDF=/usr`, from dependency checks through `ideal.exe` and `wrf.exe`. The guide is instructional; the Atlas does not execute these commands or validate the scientific output.

For the fastest source browsing, click **Local folder** in the Atlas header and choose the root of any WRF checkout. In Chromium-based browsers, the Atlas reads source files directly from that folder without copying or uploading them. The selected knowledge-graph snapshot remains visible separately, so choose the matching WRF version when exact graph-to-source correspondence matters. The browser may remember the folder handle, but it controls whether read permission persists between sessions.

Useful commands:

```powershell
npm run index:v4.7.1   # regenerate tracked official 4.7.1 snapshot
npm run index:v4.8.0   # regenerate tracked official 4.8.0 snapshot
npm run index:official # regenerate both official snapshots
npm run atlas          # local indexing followed by Vite
npm run build
npm run preview
```

## Optional Graphify sidecar

Graphify can add broad symbol, path, and relationship search across the WRF
codebase. It is intentionally supplementary: the Atlas indexer remains the
authority for Registry mappings, physics dispatch, active branches, variable
meaning, and all evidence shown as an executable WRF path.

Generate the local sidecar index with:

```powershell
$env:WRF_SOURCE_ROOT = 'E:\QWRF\WRF-v4.8.0-clean'
npm run graphify:index
npm run dev
```

The command prefers the pinned `graphifyy` 0.9.63 release through `uv`, even
if another standalone `graphify` version is installed. Without `uv`, the
standalone version must match 0.9.63; this avoids a Windows extractor crash
observed with 0.9.66 on the `share` scope. It performs local AST-only extraction over
`main`, `share`, `frame`, `dyn_em`, and `phys`; no model API or cloud backend is
required. Raw Graphify working data stays in ignored `.graphify-work/`. The
adapter writes an ignored compact index to
`public/data/local/graphify-search.json`.

Open the command palette and choose **Broader codebase / Graphify** to search
that index. Results retain file, line, confidence, and Graphify provenance. A
result opens the normal Atlas source viewer with a visible warning that broad
discovery does not itself prove WRF execution.

For one-click local indexing, run `npm run dev`, choose **Local folder** in the
Atlas header, then open **Broader codebase** and click **Build index**. The
browser cannot disclose a selected folder's absolute path to Python, so the
palette pre-fills `WRF_SOURCE_ROOT` (or the default checkout) and lets you
correct it. Before launching Graphify, the local server compares two WRF files
against the selected browser folder to ensure the path matches. Progress and
errors appear in the palette; on success, search refreshes without a restart.
The runner only accepts requests from the local Atlas on loopback and is not
included in the static GitHub Pages deployment. A local checkout requires a
working Python and Graphify installation (or `uv` for the pinned fallback).

To reuse existing raw graphs after changing only the adapter:

```powershell
npm run graphify:adapt
```

The public GitHub Pages build does not include the local sidecar by default. A
reviewed, size-limited index may be placed at `public/data/graphify/search.json`
later; the application treats its absence as a supported state.

## Public and GitHub Pages behavior

The repository contains source-path-free official snapshots under `public/data/snapshots/`. The public application defaults to WRF 4.8.0 and lets visitors switch to 4.7.1 or compare both versions. Source references are fetched from the exact indexed commit on the public [wrf-model/WRF repository](https://github.com/wrf-model/WRF), so a separate copy of WRF does not have to be committed to the Atlas repository.

To publish:

1. Create one public GitHub repository for `WRF_Atlas`; a second WRF repository is not required.
2. Before running the deployment workflow, open **Settings → Pages** in GitHub.
3. Under **Build and deployment**, choose **GitHub Actions** as the source. This one-time step creates the repository's Pages site; without it, `configure-pages` returns a `Get Pages site ... Not Found` error.
4. Push this Atlas repository to its `main` branch, then run or wait for `.github/workflows/deploy-pages.yml`.

The workflow uses the Node 24 generations of the official checkout, setup-node, configure-pages, upload-pages-artifact, and deploy-pages actions. Do not enable the deprecated Node 20 compatibility environment variable.

The workflow tests and builds the already-indexed static data, then deploys `dist`. It intentionally does not clone or re-index WRF in CI, which makes a public build deterministic and keeps the published source identity explicit.

## Data provenance and evidence

Each snapshot records its WRF version, exact commit, tag, dirty status, source mode, generation time, and submodule commits. Public snapshots omit local absolute paths. Relationships carry evidence locations and one of three confidence levels:

- `exact`: directly represented by an indexed definition, Registry entry, reference, or call;
- `inferred`: joined from independently evidenced source facts;
- `documentation`: explained by local authoritative documentation rather than executable source.

The Atlas must display unresolved boundaries instead of inventing a path. A routine's presence in the source tree is not evidence that it executes.

## Architecture

```text
WRF checkout
  -> Atlas Fortran + Registry analysis -> authoritative execution graph
  -> optional Graphify AST analysis    -> supplementary search sidecar
  -> Vue 3 + TypeScript + Cytoscape application
  -> local Vite experience or static GitHub Pages site
```

The strongest current vertical slice is the Namelist Lab: a physics selector resolves through checkout-derived Registry mappings and symbolic driver dispatch to actual calls and source lines. The Atlas also includes the execution storyboard, Field Guide, source viewer, search, and structural version comparison.

The Physics explorer now expands a selected scheme into a source-linked trace: Registry selection, matching driver branch, exact call sites, an indexed timestep call, one level of possible implementation calls, and Registry fields passed at those call sites. The Variables view follows a field from its Registry declaration through matching routine interfaces and direct call-site handoffs. Argument matches establish that a field name is passed; they do **not** establish whether a routine reads or writes the field, nor whether a guarded call runs in a particular simulation.

The compact trace diagrams are evidence groups, not unconditional runtime timelines. Select a stop to read its explanation in the scheme inspector or field journey; full branch lists and deeper calls use progressive disclosure. Physics clearly separates a preview from the current configuration. Click a selected variable again or use **Back to variables** to close its details without losing the current search filter.

Evidence buttons in Physics, Variables, Namelist Lab, and Execution Map open a shared drawer with original line numbers, a bounded source excerpt, and provenance. **Escape**, the close button, or the backdrop closes it and restores focus without leaving your view. **Open full source** remains available for deeper browsing, with **Back to trace** returning to the original view and selected scheme/inspector stop. Local-folder and pinned-upstream loading follow the same source policy as the existing Source viewer; an unmatched local folder may have different line locations. The presentation supports dark/light themes and a compact navigation rail on small screens.

In Namelist Lab, use **Load namelist.input** or paste the file to inspect its physics settings by domain. The editor and friendly selectors stay in sync without discarding unrelated lines or comments. For indexed `physics_suite` assignments, the Lab shows the effective setting when the raw option is `-1` and shows explicit per-domain overrides. Source-linked combination checks are advisory, not a replacement for WRF's own validation. The imported text stays only in page memory and is lost on refresh; copy any edits before leaving. Select a source snapshot matching the namelist's WRF version for the most relevant scheme mappings.

## Tests and limitations

`npm test` runs Python indexer and snapshot tests plus frontend namelist-parser and presentation-helper tests. It covers multiline Fortran normalization, scope detection, symbolic dispatch, Registry provenance, deterministic line mapping, suite/constraint extraction, direct field arguments, source-evidenced timestep construction, bounded source excerpts, and compact target deduplication. `npm run build` performs TypeScript checking and a production Vite build. Manual interaction and responsive checks are recorded in `docs/presentation-qa.md`.

The scanner is tolerant rather than a complete Fortran compiler. Read/write direction, generated/preprocessed paths, full configuration validation, arbitrary physics-suite behavior, and some scheduling conditions remain incomplete and must be labelled accordingly. The suite and compatibility displays cover only patterns extracted from the indexed checkout; an absent warning does not imply a valid WRF configuration. The version comparison is structural: it reports indexed additions, removals, and mapping changes, not scientific equivalence or forecast impact.

## Adding a version or subsystem

1. Create a clean, pinned WRF checkout outside this repository.
2. Add an explicit indexing script and a manifest entry.
3. Generate a snapshot with source mode `upstream`, exact repository URL, tag, and no local path.
4. Add regression coverage for new parser behavior.
5. Verify the UI source links and version comparison.
6. Publish only generated knowledge data, never the WRF source tree or local run products.

See `AGENTS.md` for the product contract and `docs/source-survey.md` for the original checkout survey.
