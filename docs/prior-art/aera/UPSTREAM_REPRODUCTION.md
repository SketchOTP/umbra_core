# UPSTREAM_REPRODUCTION — AERA

Pinned: `77b570226d12052828ff5b7ee0ca968bf1702221`

## Build attempts

### 1. Windows / Visual Studio

- **Attempted:** no (host is Linux; no VS/Win32 toolchain)
- **Documented path:** `INSTALL.md` — VS 2019/2022, Win32 Release, `AERA.sln`

### 2. Native Linux CMake

- **Attempted:** yes
- **Result:** blocked — host lacks `cmake` and `g++-multilib`; sudo unavailable

### 3. Containerized Linux CMake (`ubuntu:22.04`)

- **Configure:** PASS (`cmake` + multilib + protobuf)
- **Compile:** FAIL — `r_exec/mem.tpl.cpp` template errors (`state_`, `RUNNING`, `deleted_`, `objects_` undeclared in `MemExec` destructor) across multiple TUs
- **Compatibility patches:** none (directive: do not rewrite AERA before recording original result)

## Examples (genuine attempts; binary unavailable)

| Seed | Class | Result |
|---|---|---|
| `hello.world.1.replicode` | infrastructure (not reasoning) | blocked — no binary |
| `hand-grab-sphere.replicode` | seed reasoning (authored mdls) | blocked — no binary |
| `hand-grab-sphere-learn.replicode` | learning (babble + TPX; `m_drive` seeded) | blocked — no binary |

Source skim confirms: hello = print probe only; hand-grab = 9 seed mdls; hand-grab-learn = babble programs + `m_drive` only.

Evidence JSON: `docs/evidence/d000-track5/upstream-results.json`

## Verdict

`UPSTREAM_BUILD_BLOCKED_EXAMPLES_ATTEMPTED` — Gate 2 records genuine attempts; scientific mechanism gates rely on independent reproduction.
