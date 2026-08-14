# Source-level audits

These are targeted source reviews, not README summaries. The AGENTS-required jCodemunch indexer was unavailable; locations below were verified from pinned Git trees and targeted symbol scans.

## ALIEN

- Pin: `chrxh/alien`, `91b58172391014c1512d6919a45fdcc9f6e8b3ba`, BSD-3-Clause.
- Directories: `source/EngineInterface`, `source/Engine`, `source/Simulation`, `source/PersisterInterface`, `source/Gui`, `source/EngineTests`.
- Entry points: `source/Cli/Main.cpp`, `source/Gui/Main.cpp`.
- Symbols: `SerializerService` in `source/PersisterInterface/SerializerService.h` (serialization); `SimulationInteractionController` in `source/Gui/SimulationInteractionController.h` (interaction); `SimulationControlTests` in `source/EngineTests/SimulationControlTests.cpp` (control tests).
- Dependencies/build: CMake, CMake presets, vcpkg, CUDA/HIP-oriented GPU stack and external modules.
- Authority: simulator owns state and physics; GUI/controller is an interaction layer; identity is organism/body/genome oriented and population-compatible, not UMBRA constitutional authority.
- Integration: external benchmark feasible only through a process/API adapter after seed, headless, sensor/action, replay, and authority tests. Direct reuse is not recommended.

## Polyworld

- Pin: `polyworld/polyworld`, `99debe8c40fd9f8e58eaae49bb86a68fd1af3703`, `LICENSE.txt`.
- Directories: `src/app`, `src/library/agent`, `src/library/brain`, `src/library/environment`, `src/library/genome`, `src/library/sim`, `src/library/logs`.
- Entry points: `src/app/main.cc`, `src/app/ui/SimulationController.h`.
- Symbols: `agent` in `src/library/agent/agent.h`; `Brain` in `src/library/brain/Brain.h`; `TSimulation` in `src/library/sim/Simulation.h`; `AgentTracker` in `src/library/monitor/AgentTracker.h`.
- Dependencies/build: C++ Makefiles, Qt/rendering and simulation libraries; exact platform matrix requires build execution.
- Authority: `TSimulation` owns world evolution; agents and brains are embodied ecology participants; logs provide measurements, not UMBRA authority.
- Integration: external benchmark feasible, but individual instantiation, action injection, headless operation, deterministic seed, and replay need explicit experiments. Custom benchmark is cheaper first.

## MABE2

- Pin: `mercere99/MABE2`, `1fc9eb6d261b2cb4372cfb739f0a498cd7bd22e0`, MIT.
- Directories: `source/core`, `source/orgs`, `source/evaluate`, `source/select`, `source/placement`, `source/tools`, `tests`.
- Symbols: `MABE`/`MABEBase` in `source/core/MABE.hpp`/`MABEBase.hpp`; `Population` in `source/core/Population.hpp`; `Organism` in `source/core/Organism.hpp`; `Module`/`ModuleBase` in `source/core/Module.hpp`/`ModuleBase.hpp`; `EvalModule` in `source/core/EvalModule.hpp`; `AvidaGPOrg` and `VirtualCPUOrg` under `source/orgs`.
- Dependencies/build: C++/Empirical, Makefile-based build, module registry/configuration.
- Authority: population/organism/evaluation modules define experiment semantics; selection and placement are population authority; no persistent constitutional individual.
- Integration: direct dependency not recommended. Clean adaptation of interface boundaries is feasible; use as architecture pattern for internal harness refactor.

## ASAL

- Pin: `SakanaAI/asal`, `677ba0ea4d3b3ca78273c9906c6e84d2b1481ce7`, Apache-2.0.
- Files: `rollout.py`, `asal_metrics.py`, `substrates/__init__.py`, `foundation_models/__init__.py`, `main_opt.py`, `main_illuminate.py`, `requirements.txt`.
- Symbols: `rollout_simulation`; `calc_open_endedness_score`; `create_substrate`; `create_foundation_model`; `main` in optimization/illumination entrypoints.
- Dependencies/build: Python, JAX, substrate-specific libraries, optional GPU accelerator, CLIP/DINO or pixel foundation-model adapters, evosax/Sep-CMA-ES path.
- Authority: candidate parameters and rollout metrics are owned by the offline search process; foundation models score representations; neither is organism identity or qualification authority.
- Integration: research tooling only, clean adaptation feasible behind an offline evaluator boundary. No dependency in `umbra_core/` under CC-1.

## CAX

- Pin: `maxencefaldor/cax`, `1af11859674142463c163f542aad9ac90ace3f1e`, MIT, `LICENSE`.
- Directories: `src/cax/core`, `src/cax/cs`, `src/cax/nn`, `src/cax/utils`, `tests`.
- Symbols: `ComplexSystem` in `src/cax/core/cs.py`; `Perceive`, `NeighborhoodPerceive`, `ConvPerceive` under `src/cax/core/perceive`; `Update`, `MLPUpdate`, `NCAUpdate` under `src/cax/core/update`; `Lenia`, `FlowLenia`, `ParticleLenia`, `ParticleLife`, and `Boids` in their `src/cax/cs/*/cs.py` modules; `metrics_fn` in `src/cax/cs/lenia/metrics.py`.
- Dependencies/build: Python 3.12+, JAX, Flax NNX, uv/pyproject; CPU/GPU/TPU acceleration; tests cover systems and core update/perception primitives.
- Authority: state is a JAX/Flax complex-system state; perceive/update functions produce substrate transitions; no constitutional identity, autobiographical memory, governance, or persistent companion authority.
- Integration: reference-only or isolated external research substrate. Do not copy code or replace UMBRA state semantics.

## Evochora

- Pin: `evochora/evochora`, `7b45ae32d83f1cec7bce3bcd011ea29a375cf92b`, MIT.
- Directories: `src/main/java/org/evochora/runtime`, `src/main/java/org/evochora/datapipeline`, `src/main/java/org/evochora/node`, `assembly`, `extensions`.
- Symbols: `Simulation`, `Environment`, `Organism` in `runtime`; `IBirthHandler`, `IDeathHandler`, `ITickPlugin`; `SimulationEngine`; `SimulationRestorer`; `AbstractAnalyticsPlugin`; `OrganismIndexer` and `EnvironmentIndexer`.
- Dependencies/build: Java 21, Gradle, HOCON, Parquet/data pipeline, web controllers and optional frontend.
- Authority: runtime owns grid, VM organisms, thermodynamics and mutation; persistence/indexers own stored simulation records; web controllers expose views/actions. Deterministic seeds and complete tick persistence are strong references, but population organisms remain the unit.
- Integration: reference architecture and external research substrate; direct UMBRA integration conflicts with identity and authority semantics.

## Ribossome

- Pin: `Manalokosdev/Ribossome`, `cb3bb85f12b8aad44969437de56696583f8847b8`, no verified top-level license; `docs/LICENSE` is not sufficient for direct-use clearance.
- Files: `src/main.rs`, `src/amino_acids.rs`, shaders and maps/configuration.
- Symbols: `Agent`, `BodyPart`, `SavedAgent`, `AgentSnapshot`, `SimulationSnapshot`, `GpuState`, and `RecordingPipe` in `src/main.rs`; `load_amino_acids` in `src/amino_acids.rs`.
- Dependencies/build: Rust/Cargo, GPU shader path, simulation and rendering configuration.
- Authority: simulation/GPU state owns body and environmental process; body construction is tightly coupled to organism representation. The body-is-genome direction is opposite to UMBRA body-independent constitutional identity.
- Integration: reference-only; license blocked for direct reuse. Non-identity GPU/body benchmark ideas remain needs-further-test.
