# ALIEN / Polyworld embodiment benchmark

ALIEN (`91b5817`, BSD-3-Clause) is a CUDA-oriented particle/physics ALife system with source, CMake, vcpkg, and external dependencies. Polyworld (`99debe8`, LICENSE.txt, C++/Makefile, `src/`, `worldfiles/`) is an embodied ecological simulation. Both are candidates for external black-box benchmarking, not substrate replacement.

| Question | ALIEN | Polyworld | Current conclusion |
|---|---|---|---|
| external controller drive | possible, adapter unverified | possible, adapter unverified | UNKNOWN_AFTER_REVIEW |
| one individual without population semantics | unknown | unknown | must test, do not infer |
| sensor extraction/action injection | likely adapter work | likely adapter work | black-box API study required |
| UMBRA remains authoritative | yes if process boundary is enforced | yes if process boundary is enforced | required |
| deterministic seed/replay | source-level test required | source-level test required | gate before use |
| headless operation | build/runtime test required | build/runtime test required | gate before use |
| IPC/language | likely C++ adapter or process IPC | likely C++ adapter or process IPC | benchmark only |

A simpler custom physics benchmark is the default first candidate. Final recommendation: `multiple benchmark tiers` — Tier 1 custom deterministic body, Tier 2 ALIEN/Polyworld black-box environments only if controller injection, sensor extraction, headless execution, deterministic seeding, replay, performance, IPC, license, build, platform, population, and authority gates pass. CAX is a substrate reference, not an embodiment benchmark. The benchmark tests one UMBRA individual retaining identity and learned organization across bodies; it does not evolve a replacement organism.
