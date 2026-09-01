# Evidence

Durable evidence is atomically published and readback-hashed under the AS-003P evidence root. Phase A state reconciliation records exact baseline, parent evidence, Notion authority, GitHub state, and zero pre-start live callsites.

Pre-implementation locks:

- modal evidence contract: `b51c6768676d4a9490c59aac5cc924812423201562bcd6f3af44463ee3f236bb`
- source-instant boundary: `d2068b5385c7a939eb30ba6441d9d72edc81e86dcedeccf7bbf68ed11cfe9e47`
- frame contract: `d7901598c8cf669ed5964b9e330f25b08084915b914fdb6385bc90a4991b3582`
- observer-effect protocol: `c1c454fd5743bfe544c2acbf372d4327feac76e5f7086579f2fa64f485c0bd4d`
- branch-bound lock: `3e776c21cb81094a3caae5d2a7cf2be6262af87dcfc58d5532a96abf9b30c73b`

Body capability, timing, pending execution, world-truth firewall, and bounded external-reference audits are also durably retained before implementation testing.

Pre-shadow implementation gates:

- additive opportunity evidence retains separate root-current and future-belief facts;
- current observations become root `MUST` only at the exact source tick;
- future opportunity possibility follows the pre-existing WorldModel retention floor/decay and remains `MAY`;
- AS-003N `core.py` and AS-003O `adapters.py` / `continuation.py` are byte-unchanged;
- static Habitat/world-truth import scan: PASS;
- pure isolation scan: PASS;
- Authority 3.0: PASS;
- governance: PASS;
- `git diff --check`: PASS;
- focused pure run 03: `41/41`, SHA-256 `764929952d2f08e05110971be9952e46046d7809a34859ac7b302abc3401662e`;
- focused pure run 04: `41/41`, SHA-256 `30fe71555eb3253d51fcd2d19c8cbc5d6d1782200f8cdeafcd36569e340ce719`;
- passing node list and stdout are identical across runs;
- organism executions before the paired diagnostic: `0`.

Frozen non-formal pair: existing CLOSE-02R / AS-003C Diagnostic-A fixture,
R0/S0, seed `45878900`, horizon `500`; one control plus one shadow,
retries `0`, reseeds `0`. The one-shot harness publishes start, each completed
leg, parity, and finish evidence independently with atomic rename/fsync/readback.

Execution disposition:

- command invoked once at `0f9368d5f0add5fb987353488cc9357e82fd7285`;
- top-level import failed with `ModuleNotFoundError: No module named 'experiments'`;
- failure occurred before harness `main`, durable start publication, fixture preparation, organism creation, or ticks;
- durable stop record SHA-256 `d59f438cc409329722594ab79425c67d395ea86956bccb30890a3a285adf8390`;
- control `0`, shadow `0`, organism ticks `0`, retries `0`, reseeds `0`;
- parity and actual-source evidence: `NOT RUN`;
- terminal verdict: `AS003P_EVIDENCE_INSUFFICIENT`.
- final evidence manifest: `6a2f6afcea9394fa1b0d4b75c242b6a359d4f62d3a7bf3ffde4954a9db2ab4c2` (`27` artifacts inventoried before the manifest itself; readback verified).
