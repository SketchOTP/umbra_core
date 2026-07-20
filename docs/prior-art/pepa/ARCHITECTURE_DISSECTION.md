# PEPA architecture dissection

## Claimed loop

```text
Sys3 (personality → goals/rewards + reflection)
    ↓ intrinsic reward / hierarchical goals
Sys2 (LLM-MCTS or distilled policy)
    ↓ discrete action
Sys1 (skills, body, episodic writeback)
    ↓ memories
Sys3 (daily reflection)
```

## Mechanism origin table

| Mechanism | AUTHORED | LEARNED | GENERATED | EMERGENT | FIXED_SKILL | PAPER_ONLY |
|---|---|---|---|---|---|---|
| Big Five / NL personality | ✓ | | | | | |
| Ultimate/daily goals | | | ✓ LLM | claimed | | code missing |
| Intrinsic rewards | | | ✓ LLM | | | code missing |
| Daily reflection prose | | | ✓ LLM | | | prompts only |
| MCTS / BERT policy | | ✓ distill | ✓ LLM prior | | | code missing |
| Nav / elevator / stairs | | | | | ✓ | code blocked |
| Charge when low battery | | | goal from Sys3 | | ✓ | |
| Action repertoire | | | | | ✓ | |
| Open-ended evolution | | | | claimed | | ✓ unverified here |
| Trait-aligned behavior | ✓ config | | ✓ | claimed | | |

## Separation used for UMBRA tests

Useful **structure** (keep as candidates):

1. Sys1 / Sys2 / Sys3 separation  
2. Internal vs external goal arbitration  
3. Periodic **bounded** reflection that retunes weights from outcomes  
4. Embodiment-aware filtering (battery, critical energy)  
5. Skill-level execution separated from goal generation  
6. Persistent operation without continuous user instruction  

Weak **foundation** (reject as organism core):

1. User-authored Big Five as individuality  
2. LLM-generated rewards as primary motivation  
3. LLM reflection as development  
4. Generated goals as inherently autonomous  
5. Fixed action diversity as open-ended evolution  
6. Personality alignment as proof of aliveness  
7. PEPA as complete UMBRA brain  

## Independent causal question

After removing authored personality and LLM motivation, does a layered autonomy loop still produce:

- unprompted activity,
- satiation,
- history-dependent behavior,
- governance-respecting arbitration,
- bounded goals/retries,
- measurable reflection value?

Answer from `independent_reproduction/`: **yes for the structural loop; no for personality/LLM-as-will.**
