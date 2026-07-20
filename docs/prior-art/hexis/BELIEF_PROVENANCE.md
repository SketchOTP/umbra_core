# Belief and provenance

Upstream: semantic sources, trust, CONTRADICTS/SUPPORTS, belief revision SQL, protected memories.

Independent tests (see `provenance-results.json`):

- independent support raises confidence
- duplicates ignored
- contradiction reduces confidence
- low-quality cannot smash strong support
- correction supersedes with history retained
- embedding delete ≠ memory delete
- transactional rollback on partial failure

UMBRA: require provenance classes (observation / testimony / inference / config).
