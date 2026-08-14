# Seed Pairing Contract

The frozen D-009 job builder pairs the same seed across matrix cells. CC-4
preserves that matched-seed design while creating each subject with its own
Store, organism, and RNG instance. No RNG object is passed between subjects;
execution order is reversed in a second isolated run and produces the same
pair comparison.
