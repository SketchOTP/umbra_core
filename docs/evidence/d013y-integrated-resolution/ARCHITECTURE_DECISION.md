# D-013Y architecture decision

The baseline reproduced the cold-start discovery deficit: the first direct
resource observation was after the historical recovery window. The bounded
correction adds an endogenous discovery candidate only when the WorldModel has
no policy-safe resource cue, keeps discovery episode state bounded, separates
remembered resource cues from current observations, and uses bounded
ORIENT/MOVE-style reacquisition. A successful direct CHARGE strengthens the
landmark from verified body-relative contact only.

No map, coordinates, new sensor, planner, physiology threshold, evaluator
truth, or formal harness path was added.

The correction closes cold-start discovery, but the primary 1000-tick proof
still crosses the existing energy critical floor before reacquisition returns
a fresh resource observation.
