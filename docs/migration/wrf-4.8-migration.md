# WRF 4.8 and QWRF migration record

Date: 2026-08-12

This migration separates immutable upstream baselines from the research branch. It does not overwrite the original v4.7.1 checkout.

## Checkout inventory

| Folder | Git identity | State |
| --- | --- | --- |
| `E:\QWRF\WRF` | v4.7.1 lineage, commit `f52c197ed39d12e087d02c50f412d90d418f6186` | Original dirty research checkout, preserved |
| `E:\QWRF\WRF-v4.7.1-clean` | official `v4.7.1`, commit `f52c197ed39d12e087d02c50f412d90d418f6186` | Detached clean baseline, three pinned submodules |
| `E:\QWRF\WRF-v4.8.0-clean` | official `v4.8.0`, commit `06d4240ae989cc3e50af412bb472df3d9048783c` | Detached clean baseline, eight pinned submodules |
| `E:\QWRF\WRF-v4.8.0-qwrf` | branch `qwrf-v4.8.0` from official v4.8.0 | Research migration worktree |

The clean baselines must remain unmodified. Future QWRF work belongs only on the dedicated branch/worktree.

## Recovery artifacts

The original working tree was inspected before migration. A whole-repository Git bundle could not be produced because Windows reported an insufficient paging file, so the recoverable research delta was preserved with two narrower artifacts:

| Artifact | SHA-256 | Contents |
| --- | --- | --- |
| `E:\QWRF\migration-backups\2026-08-12-wrf-v4.7.1\morrison-working-tree.patch` | `45F16C0FC22520915382468A59AB77510013AC279F66DBAA8064CBE859E3E320` | Exact tracked working-tree delta for the Morrison module |
| `E:\QWRF\migration-backups\2026-08-12-wrf-v4.7.1\qwrf-research-artifacts.zip` | `2A5B8B08CBC93A0C7526FEBD2B40855EDFC990B3199090CB1D5C84D92048B2B1` | Selected QWRF research artifacts and supporting material |

The original `E:\QWRF\WRF\.git` directory remains the authoritative full history. The backup artifacts supplement it; they do not replace it.

## Port status

The saved Morrison patch passed `git apply --check` against official WRF 4.8.0 and was applied only to `E:\QWRF\WRF-v4.8.0-qwrf`. The current research worktree delta is:

```text
phys/module_mp_morr_two_moment.F | 134 lines changed
131 insertions, 3 deletions
```

This establishes a reviewable v4.8 port of the existing profiling/trace instrumentation. It is intentionally uncommitted until validation is complete. No modifications were made to either clean baseline.

The earlier Py-Morrison/VQLS and WRFDA quantum work remains staged research rather than a proven, end-to-end WRF 4.8 integration. It must not be represented as production-active in the Atlas until code, execution, and numerical evidence exist.

## Validation gates before committing QWRF v4.8

1. Review the applied diff against the v4.7.1 patch and v4.8 Morrison changes.
2. Build a clean official v4.8 control and the QWRF v4.8 branch with the same compiler configuration.
3. Run the same Morrison case with instrumentation disabled and confirm unchanged numerical outputs within an explicit tolerance.
4. Enable the instrumentation and verify trace completeness, ordering, and overhead.
5. If Py-Morrison/VQLS is connected, validate interface dimensions, units, state ownership, failure handling, and classical fallback.
6. Keep WRFDA/QAOA claims separate until the relevant executable has been built and exercised.
7. Commit the QWRF branch only after recording commands, compiler identity, case inputs, and result hashes.

## Atlas snapshots

The tracked public snapshots are generated from the two clean baselines:

- `public/data/snapshots/wrf-v4.7.1.json`
- `public/data/snapshots/wrf-v4.8.0.json`

They contain exact upstream commit and submodule provenance but no local absolute source path. The local dirty research graph is generated separately under ignored `public/data/local/` and appears only during local development.
