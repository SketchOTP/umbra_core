# ALIEN / Polyworld embodiment benchmark

ALIEN (`91b5817`, BSD-3-Clause) is a CUDA-oriented particle/physics ALife system with source, CMake, vcpkg, and external dependencies. Polyworld (`99debe8`, LICENSE.txt, C++/Makefile, `src/`, `worldfiles/`) is an embodied ecological simulation. Both are candidates for external black-box benchmarking, not substrate replacement.

| Question | ALIEN | Polyworld | Current conclusion |
|---|---|---|---|
| external controller drive | possible, adapter unverified | possible, adapter unverified | SOURCE_VERIFICATION_PENDING |
| one individual without population semantics | unknown | unknown | must test, do not infer |
| sensor extraction/action injection | likely adapter work | likely adapter work | black-box API study required |
| UMBRA remains authoritative | yes if process boundary is enforced | yes if process boundary is enforced | required |
| deterministic seed/replay | source-level test required | source-level test required | gate before use |
| headless operation | build/runtime test required | build/runtime test required | gate before use |
| IPC/language | likely C++ adapter or process IPC | likely C++ adapter or process IPC | benchmark only |

A simpler custom physics benchmark is the default first candidate because it minimizes authority, seed, IPC, and replay risk. ALIEN/Polyworld should be compared against that cost before integration is proposed.
