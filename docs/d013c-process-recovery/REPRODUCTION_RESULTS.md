# Reproduction results

Initial exact-test isolation: 1 pass. Five additional exact-test repetitions: 5 passes. The broad test therefore did not reproduce deterministically.

The diagnostic equivalent reproduced ordinary SIGTERM as 1 failure and 2 passes across three attempts. Force-kill reproduced 0 failures across three attempts. Every attempt confirmed the diagnostic tick marker before termination. The pre-correction failure had the same organism identity before termination and would fail during generation-2 startup.

The post-correction diagnostic comparison completed 3/3 ordinary-SIGTERM and 3/3 SIGKILL recoveries, with identity preserved in all six attempts.
