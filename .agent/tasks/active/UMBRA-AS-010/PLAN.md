# AS-010 plan

1. Audit and lock the AS-007 full configuration; prove zero production
   semantic drift and create one canonical AS-010 factory.
2. Build and preflight fresh full-configuration R0–R3 and downstream lifecycle
   harnesses, including HabitatEngine restoration after every reload.
3. Freeze disjoint seeds and execute the population and downstream gates once,
   preserving exact terminal boundaries and evidence.

## Terminal disposition

The population and lifecycle gates passed under the canonical full
configuration. The post-lock boundedness harness reached `100000` ticks but
failed during final authoritative snapshot collection with
`habitat_engine_reattachment_required`; AS-010 is therefore permanently
terminal as `AS010_PROTOCOL_FAIL`. Soak and ablation were not run.
