# WRF Code Atlas - Source Survey

This document captures the findings from surveying the WRF source code to inform the architecture of the WRF Code Atlas.

## Git Identity
- **Version:** WRF v4.7.1
- **Commit:** `f52c197ed39d12e087d02c50f412d90d418f6186`
- **Branch:** `master`

## Directory Structure
Major directories in the WRF repository:
- `main/`
- `frame/`
- `dyn_em/`
- `phys/` (Contains 233 files and 3 subdirectories)
- `share/`
- `Registry/`
- `inc/`
- `run/`
- `test/`
- `tools/`
- `external/`
- `arch/`
- `var/`
- `chem/`
- `hydro/`

## Entry Points
The core program execution begins in the `main/` directory:
- [wrf.F:L4](file:///E:/QWRF/WRF/main/wrf.F#L4): `PROGRAM wrf`
  - Calls `wrf_init` ([wrf.F:L30](file:///E:/QWRF/WRF/main/wrf.F#L30))
  - Calls `wrf_dfi` ([wrf.F:L33](file:///E:/QWRF/WRF/main/wrf.F#L33))
  - Calls `wrf_run` ([wrf.F:L44](file:///E:/QWRF/WRF/main/wrf.F#L44))
  - Calls `wrf_finalize` ([wrf.F:L57](file:///E:/QWRF/WRF/main/wrf.F#L57))
- [module_wrf_top.F](file:///E:/QWRF/WRF/main/module_wrf_top.F): Contains the implementations of the top-level routines:
  - `wrf_init` ([module_wrf_top.F:L137](file:///E:/QWRF/WRF/main/module_wrf_top.F#L137))
  - `wrf_run` ([module_wrf_top.F:L2013](file:///E:/QWRF/WRF/main/module_wrf_top.F#L2013))
  - `wrf_finalize` ([module_wrf_top.F:L2094](file:///E:/QWRF/WRF/main/module_wrf_top.F#L2094))

Other program entry points include:
- [real_em.F](file:///E:/QWRF/WRF/main/real_em.F): `PROGRAM real_data`
- [ideal_em.F](file:///E:/QWRF/WRF/main/ideal_em.F): `PROGRAM ideal`
- [ndown_em.F](file:///E:/QWRF/WRF/main/ndown_em.F): `PROGRAM ndown`
- [nup_em.F](file:///E:/QWRF/WRF/main/nup_em.F): `PROGRAM nup`
- [tc_em.F](file:///E:/QWRF/WRF/main/tc_em.F): `PROGRAM tc`

## Initialization Flow
1. `wrf_init` calls `initial_config` at [module_wrf_top.F:L209](file:///E:/QWRF/WRF/main/module_wrf_top.F#L209) (and L217).
2. `initial_config` is defined in [module_configure.F:L84](file:///E:/QWRF/WRF/frame/module_configure.F#L84), and it opens `namelist.input` at [module_configure.F:L146](file:///E:/QWRF/WRF/frame/module_configure.F#L146).
3. **Domain creation:** Handled by `alloc_and_configure_domain` in [module_domain.F:L519](file:///E:/QWRF/WRF/frame/module_domain.F#L519).
4. **Physics init:** `phy_init` is called from [start_em.F](file:///E:/QWRF/WRF/dyn_em/start_em.F) and defined in [module_physics_init.F](file:///E:/QWRF/WRF/share/module_physics_init.F).
5. **Configuration validation:** Validated within [module_check_a_mundo.F](file:///E:/QWRF/WRF/share/module_check_a_mundo.F).

## Configuration Machinery
- [module_configure.F](file:///E:/QWRF/WRF/frame/module_configure.F): Contains `model_config_rec_type`, `initial_config`, and `nl_get_*`/`nl_set_*` accessors.
- [module_state_description.F](file:///E:/QWRF/WRF/frame/module_state_description.F): Contains auto-generated physics option constants (e.g., `SFCLAYSCHEME=1`, `LSMSCHEME=2`).
- [module_driver_constants.F](file:///E:/QWRF/WRF/frame/module_driver_constants.F): Contains global driver constants.

## Registry
The Registry defines the state variables, namelist configurations, and package selections.
- Top-level: [Registry.EM](file:///E:/QWRF/WRF/Registry/Registry.EM), which includes [registry.dimspec](file:///E:/QWRF/WRF/Registry/registry.dimspec), [Registry.EM_COMMON](file:///E:/QWRF/WRF/Registry/Registry.EM_COMMON), etc.
- [Registry.EM_COMMON](file:///E:/QWRF/WRF/Registry/Registry.EM_COMMON) (~437KB, 3673 lines) contains `rconfig`, `package`, and `state` entries.
- `rconfig` entries define namelist variables like `sf_surface_physics`, `mp_physics`, `ra_lw_physics`, `ra_sw_physics`, `bl_pbl_physics`, `cu_physics`, and `sf_sfclay_physics`.
- `package` entries map values to named packages + state variables:
  - `sf_surface_physics`: 0→nolsmscheme, 1→slabscheme, 2→lsmscheme, 3→ruclsmscheme, 4→noahmpscheme, 5→clmscheme, 7→pxlsmscheme, 8→ssibscheme
  - `mp_physics`: 2→linscheme, 8→thompson, 10→morr_two_moment, etc.
  - `ra_lw_physics`: 1→rrtmscheme, 4→rrtmg_lwscheme, etc.
  - `ra_sw_physics`: 1→swradscheme, 4→rrtmg_swscheme, etc.
  - `bl_pbl_physics`: 1→ysuscheme, 2→myjpblscheme, 5→mynnpblscheme2, etc.
  - `cu_physics`: 1→kfetascheme, 3→gdscheme, 6→taborechscheme, 16→ntiedtkescheme, etc.
  - `sf_sfclay_physics`: 1→sfclayrevscheme, 2→myjsfcscheme, 5→mynnsfcscheme, etc.
- **Key state variables** in `Registry.EM_COMMON`: `HFX` (L1963), `QFX` (L1964), `TSK` (L1416), `SMOIS` (L839), `PBLH` (L1960), `TSLB`, `SH2O`, `SNOW`, `SNOWH`, `CANWAT`, `VEGFRA`.

## Solver Architecture
- [solve_em.F](file:///E:/QWRF/WRF/dyn_em/solve_em.F): Main solver.
- The Runge-Kutta (RK) loop is at [solve_em.F:L578](file:///E:/QWRF/WRF/dyn_em/solve_em.F#L578) (`rk_step = 1, rk_order`).
- Physics are computed on the first RK step only (L785: `IF rk_step == 1`).
- `first_rk_step_part1` is called at [solve_em.F:L807](file:///E:/QWRF/WRF/dyn_em/solve_em.F#L807).
- `first_rk_step_part2` is called at [solve_em.F:L845](file:///E:/QWRF/WRF/dyn_em/solve_em.F#L845).
- Acoustic sub-steps take place at [solve_em.F:L1266](file:///E:/QWRF/WRF/dyn_em/solve_em.F#L1266).

## Physics Execution Order (within one timestep)
Physics are executed in a specific sequence during the first RK step.
1. **Radiation** ([module_first_rk_step_part1.F:L264](file:///E:/QWRF/WRF/dyn_em/module_first_rk_step_part1.F#L264)) — conditional on the radiation interval.
2. **Surface layer + Land surface** ([module_first_rk_step_part1.F:L594](file:///E:/QWRF/WRF/dyn_em/module_first_rk_step_part1.F#L594)).
3. **PBL** ([module_first_rk_step_part1.F:L1113](file:///E:/QWRF/WRF/dyn_em/module_first_rk_step_part1.F#L1113)).
4. **Cumulus** ([module_first_rk_step_part1.F:L1377](file:///E:/QWRF/WRF/dyn_em/module_first_rk_step_part1.F#L1377)) — conditional on the cumulus interval.
5. **RK dynamics loop** ([solve_em.F:L578-L3459](file:///E:/QWRF/WRF/dyn_em/solve_em.F#L578)).
6. **Microphysics** ([solve_em.F:L3725](file:///E:/QWRF/WRF/dyn_em/solve_em.F#L3725)) — executed after the RK loop.

## Physics Drivers
- **Surface**: [module_surface_driver.F](file:///E:/QWRF/WRF/phys/module_surface_driver.F)
  - `surface_driver` subroutine: L7-L4503
  - `sf_sfclay_physics` `SELECT CASE` at L2004
  - `sf_surface_physics` `SELECT CASE` at L2542
  - `CASE(LSMSCHEME)` at L2585 calls `lsm()` at L2820 (Noah) from [module_sf_noahlsm.F](file:///E:/QWRF/WRF/phys/module_sf_noahlsm.F)
- **Radiation**: [module_radiation_driver.F](file:///E:/QWRF/WRF/phys/module_radiation_driver.F)
  - `radiation_driver`: L12-L3283
  - LW `SELECT CASE` at L1839
  - SW `SELECT CASE` at L2339
- **PBL**: [module_pbl_driver.F](file:///E:/QWRF/WRF/phys/module_pbl_driver.F)
  - `pbl_driver`: L11-L2284
  - `SELECT CASE` at L1157
  - `CASE(YSUSCHEME)` at L1207 calls `ysu()` at L1215
- **Microphysics**: [module_microphysics_driver.F](file:///E:/QWRF/WRF/phys/module_microphysics_driver.F)
  - `microphysics_driver`: L9-L2935
  - `SELECT CASE` at L981
- **Cumulus**: [module_cumulus_driver.F](file:///E:/QWRF/WRF/phys/module_cumulus_driver.F)
  - `cumulus_driver`: L6-L1672
  - `SELECT CASE` at L956

## Key Variables Exchanged
- **Surface → PBL**: `HFX`, `QFX`, `LH`, `UST`, `TSK`, `MOL`, `CHS`, `CHS2`, `CQS2`
- **Radiation → Surface**: `GLW`, `GSW`, `SWDOWN`, `EMISS`, `ALBEDO`
- **Land Surface**: `TSLB`, `SMOIS`, `SH2O`, `SNOW`, `SNOWH`, `CANWAT`, `VEGFRA`
- **Microphysics**: `RAINNC`, `RAINNCV`, `QVAPOR`, `QCLOUD`, `QRAIN`, `QICE`, `QSNOW`, `QGRAUP`
- **PBL**: `PBLH`, `RUBLTEN`, `RVBLTEN`, `RTHBLTEN`, `RQVBLTEN`

## Preprocessor/Generated Code
- [module_state_description.F](file:///E:/QWRF/WRF/frame/module_state_description.F): Auto-generated physics constants.
- [module_configure.F](file:///E:/QWRF/WRF/frame/module_configure.F): Auto-generated config machinery.
- `inc/` directory: Contains auto-generated allocation/deallocation includes.
- Registry tool (`tools/`) generates Fortran code directly from the Registry definitions.
