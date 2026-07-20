#!/usr/bin/env python3
"""Independent mechanism reproduction of MicroPsi Doernerian modulators (stdlib only).

REPRODUCTION_STATUS = INDEPENDENT_MECHANISM_REPRODUCTION
This is NOT execution of the complete upstream MicroPsi2 runtime (server/Theano/UI).

ponytail: ceiling = equations only, not full nodenet/world; upgrade = wire into UMBRA need/motive bus after D-000.
Source: micropsi2 micropsi_core/nodenet/stepoperators.py::DoernerianEmotionalModulators
License: MIT (upstream license.txt)
"""

from __future__ import annotations

import math

REPRODUCTION_STATUS = "INDEPENDENT_MECHANISM_REPRODUCTION"
UPSTREAM_RUNTIME_EXECUTED = False


def gentle_sigmoid(x: float) -> float:
    return 2 * ((1 / (1 + math.exp(-0.5 * x))) - 0.5)


def step_modulators(m: dict[str, float]) -> dict[str, float]:
    COMPETENCE_DECAY_FACTOR = 0.1
    JOY_DECAY_FACTOR = 0.01

    def g(k: str, default: float = 0.0) -> float:
        return float(m.get(k, default))

    base_sum_importance_of_intentions = g("base_sum_importance_of_intentions")
    base_sum_urgency_of_intentions = g("base_sum_urgency_of_intentions")
    base_competence_for_intention = g("base_competence_for_intention", 1.0)
    base_importance_of_intention = g("base_importance_of_intention")
    base_urgency_of_intention = g("base_urgency_of_intention")
    base_number_of_active_motives = g("base_number_of_active_motives")
    base_number_of_unexpected_events = g("base_number_of_unexpected_events")
    base_number_of_expected_events = g("base_number_of_expected_events")
    base_urge_change = g("base_urge_change")
    base_age = g("base_age")
    base_unexpectedness_prev = g("base_unexpectedness")
    base_sum_of_urges = g("base_sum_of_urges")
    emo_competence_prev = g("emo_competence", 1.0)
    emo_sustaining_joy_prev = g("emo_sustaining_joy")

    base_age += 1

    emo_activation = max(
        0.0,
        (
            (base_sum_importance_of_intentions + base_sum_urgency_of_intentions)
            / ((base_number_of_active_motives * 2) + 1)
        )
        + base_urge_change,
    )

    base_unexpectedness = max(
        min(
            base_unexpectedness_prev
            + gentle_sigmoid((base_number_of_unexpected_events - base_number_of_expected_events) / 10),
            1.0,
        ),
        0.0,
    )
    fear = 0.0

    emo_securing_rate = (
        (1 - base_competence_for_intention)
        - (0.5 * base_urgency_of_intention * base_importance_of_intention)
        + fear
        + base_unexpectedness
    )
    emo_resolution = 1 - emo_activation
    emo_selection_threshold = emo_activation

    pleasure_from_expectation = gentle_sigmoid(
        (base_number_of_expected_events - base_number_of_unexpected_events) / 10
    )
    pleasure_from_satisfaction = gentle_sigmoid(base_urge_change * -3)
    emo_pleasure = pleasure_from_expectation + pleasure_from_satisfaction

    emo_valence = 0.5 - base_urge_change - base_sum_of_urges

    if emo_pleasure != 0:
        if math.copysign(1, emo_pleasure) == math.copysign(1, emo_sustaining_joy_prev) or emo_sustaining_joy_prev == 0:
            if abs(emo_pleasure) >= abs(emo_sustaining_joy_prev):
                emo_sustaining_joy = emo_pleasure
            else:
                emo_sustaining_joy = emo_sustaining_joy_prev
        else:
            emo_sustaining_joy = emo_pleasure
    else:
        if abs(emo_sustaining_joy_prev) < JOY_DECAY_FACTOR:
            emo_sustaining_joy = 0.0
        else:
            emo_sustaining_joy = emo_sustaining_joy_prev - math.copysign(JOY_DECAY_FACTOR, emo_sustaining_joy_prev)

    pleasurefactor = 1 if emo_pleasure >= 0 else -1
    divisorbaseline = 1 if emo_pleasure >= 0 else 2
    youthful_exuberance_term = 1.0
    emo_competence = (emo_competence_prev + (emo_pleasure * youthful_exuberance_term)) / (
        divisorbaseline + (pleasurefactor * emo_competence_prev * COMPETENCE_DECAY_FACTOR)
    )
    emo_competence = max(min(emo_competence, 0.99), 0.01)

    out = dict(m)
    out.update(
        {
            "base_age": base_age,
            "base_unexpectedness": base_unexpectedness,
            "base_number_of_expected_events": 0.0,
            "base_number_of_unexpected_events": 0.0,
            "base_urge_change": 0.0,
            "emo_pleasure": emo_pleasure,
            "emo_activation": emo_activation,
            "emo_securing_rate": emo_securing_rate,
            "emo_resolution": emo_resolution,
            "emo_selection_threshold": emo_selection_threshold,
            "emo_competence": emo_competence,
            "emo_sustaining_joy": emo_sustaining_joy,
            "emo_valence": emo_valence,
        }
    )
    return out


def _check() -> None:
    # Calm baseline: one motive, matched competence → low activation
    calm = step_modulators(
        {
            "base_sum_importance_of_intentions": 0.2,
            "base_sum_urgency_of_intentions": 0.1,
            "base_number_of_active_motives": 1.0,
            "base_competence_for_intention": 0.8,
            "base_importance_of_intention": 0.2,
            "base_urgency_of_intention": 0.1,
            "emo_competence": 0.7,
        }
    )
    assert calm["emo_activation"] >= 0
    assert 0.01 <= calm["emo_competence"] <= 0.99
    assert abs(calm["emo_resolution"] - (1 - calm["emo_activation"])) < 1e-9

    # Urge spike raises activation vs calm
    urgent = step_modulators(
        {
            "base_sum_importance_of_intentions": 1.5,
            "base_sum_urgency_of_intentions": 1.5,
            "base_number_of_active_motives": 1.0,
            "base_urge_change": 0.4,
            "base_competence_for_intention": 0.3,
            "emo_competence": 0.4,
        }
    )
    assert urgent["emo_activation"] > calm["emo_activation"]
    assert urgent["emo_selection_threshold"] == urgent["emo_activation"]

    # Unexpected events raise securing_rate via unexpectedness
    surprise = step_modulators(
        {
            "base_number_of_unexpected_events": 8.0,
            "base_number_of_expected_events": 0.0,
            "base_competence_for_intention": 1.0,
            "emo_competence": 0.5,
        }
    )
    assert surprise["base_unexpectedness"] > 0
    assert surprise["emo_securing_rate"] > 0

    print("OK micropsi_modulator_repro")


if __name__ == "__main__":
    _check()
