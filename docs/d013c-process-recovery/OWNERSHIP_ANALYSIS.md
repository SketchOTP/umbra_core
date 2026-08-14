# Ownership analysis

The original owner was generation 1 with status `ACTIVE`. After termination, generation 2 requested the prior generation plus one with `reclaim_dead=True`. The old process identity was no longer live, the old record was moved to a `.stale.<timestamp>` artifact, and generation 2 acquired ownership. No live owner was stolen. The load failure occurred after ownership acquisition.
