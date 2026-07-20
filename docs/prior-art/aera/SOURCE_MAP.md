# SOURCE_MAP — AERA `@77b57022`

Local clone: `docs/prior-art/aera/upstream/AERA` (gitignored).

## Runtime

| Path | Role |
|---|---|
| `AERA/main.cpp`, `AERA/AERA_main.cpp` | Load settings + seed; start rMem |
| `r_exec/mem.cpp` | Inject/eject, cores, export |
| `r_exec/reduction_core.cpp`, `time_core.cpp` | Async job workers |
| `r_exec/group.cpp` | Saliency / activity scheduling |
| `r_exec/factory.cpp` | Facts, preds, goals |

## Models / goals / learning

| Path | Role |
|---|---|
| `r_exec/mdl_controller.cpp` | Forward predict, abduce, rate |
| `r_exec/model_base.cpp` | White/black lists, GC |
| `r_exec/p_monitor.cpp` | Prediction success/failure |
| `r_exec/g_monitor.cpp` | Goal / simulation monitors |
| `r_exec/pattern_extractor.cpp` | CTPX / PTPX / GTPX |
| `r_exec/auto_focus.cpp` | TPX dispatch |
| `AERA/settings.h` | Inertia, horizons, TPX limits |

## Programs / I/O

| Path | Role |
|---|---|
| `r_exec/pgm_overlay.cpp` | inj/eject/cmd |
| `usr_operators/auto_focus_callback.cpp` | `icpp_pgm auto_focus` |
| `AERA/replicode_v1.2/*.replicode` | Seed demos |

## Build

| Path | Role |
|---|---|
| `AERA.sln` | Documented Windows VS Win32 |
| `CMakeLists.txt` | Linux `-m32` executable target |
| `INSTALL.md` | Prerequisites |
