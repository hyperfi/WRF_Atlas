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

Useful commands:

```powershell
npm run index:v4.7.1   # regenerate tracked official 4.7.1 snapshot
npm run index:v4.8.0   # regenerate tracked official 4.8.0 snapshot
npm run index:official # regenerate both official snapshots
npm run atlas          # local indexing followed by Vite
npm run build
npm run preview
```

## Public and GitHub Pages behavior

The repository contains source-path-free official snapshots under `public/data/snapshots/`. The public application defaults to WRF 4.8.0 and lets visitors switch to 4.7.1 or compare both versions. Source references are fetched from the exact indexed commit on the public [wrf-model/WRF repository](https://github.com/wrf-model/WRF), so a separate copy of WRF does not have to be committed to the Atlas repository.

To publish:

1. Create one public GitHub repository for `WRF_Atlas`; a second WRF repository is not required.
2. Push this Atlas repository to its `main` branch.
3. In GitHub, open **Settings → Pages** and choose **GitHub Actions** as the source.
4. Run or wait for `.github/workflows/deploy-pages.yml`.

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
  -> tolerant Python Fortran and Registry analysis
  -> normalized, evidence-bearing version snapshot
  -> Vue 3 + TypeScript + Cytoscape application
  -> local Vite experience or static GitHub Pages site
```

The strongest current vertical slice is the Namelist Lab: a physics selector resolves through checkout-derived Registry mappings and symbolic driver dispatch to actual calls and source lines. The Atlas also includes the execution storyboard, Field Guide, source viewer, search, and structural version comparison.

## Tests and limitations

`npm test` covers multiline Fortran normalization, scope detection, symbolic dispatch, Registry provenance, deterministic line mapping, and source-evidenced timestep construction. `npm run build` performs TypeScript checking and a production Vite build.

The scanner is tolerant rather than a complete Fortran compiler. Read/write direction, generated/preprocessed paths, full configuration validation, physics-suite overrides, and some scheduling conditions remain incomplete and must be labelled accordingly. The version comparison is structural: it reports indexed additions, removals, and mapping changes, not scientific equivalence or forecast impact.

## Adding a version or subsystem

1. Create a clean, pinned WRF checkout outside this repository.
2. Add an explicit indexing script and a manifest entry.
3. Generate a snapshot with source mode `upstream`, exact repository URL, tag, and no local path.
4. Add regression coverage for new parser behavior.
5. Verify the UI source links and version comparison.
6. Publish only generated knowledge data, never the WRF source tree or local run products.

See `AGENTS.md` for the product contract and `docs/source-survey.md` for the original checkout survey.
