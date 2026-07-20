# Upgrade / rollback

Pipeline: validate → shadow → compare → canary → activate → monitor → retain/rollback.

- Shadow: no external effects
- Canary: narrower authority; still cannot mutate constitution
- Rollback restores prior capability; **must not** erase unrelated memory or change identity
- Learned models **cannot self-promote**
- Capability upgrade ≠ developmental learning
