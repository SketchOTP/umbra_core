# AS-005 scientific freeze protocol

Freeze commit is the commit containing this protocol, the AS-005 production seam, the explicit route-learning harness, and the additive focused tests. The scientific command is frozen as:

```text
working directory: /home/sketch/Projects/umbra-close02x-work
interpreter: /home/sketch/cs14n-runtime/bin/python
command: /home/sketch/cs14n-runtime/bin/python -m experiments.as005.qualification --phase scientific --work <fresh local scratch directory>
sequence: Diagnostic A R0 seed 45878900 horizon 500; Diagnostic B R0 seed 22023239 horizon 3500; Known R1 R1 seed 57531938 horizon 7200
evidence root: /srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-as-005-preventive-modal-continuation-integrated-viability-r1/
retries: 0
reseeds: 0
```

Each leg writes a decision trace and planning trace directly into the fresh evidence root. The runner stops at the first non-completed leg and publishes one durable sequence result. No code, tests, fixture, seed, horizon, or environment changes are allowed after the freeze commit.

The development-only source-activation gate already completed pre-freeze on R0/45878900/500 with route evidence, 262 nonempty modal O0 rows, and retained dense traces. It is not a qualification result.
