#!/usr/bin/env python3
"""CLOSE-02F qualification-only runner.

This runner composes existing production APIs and does not alter umbra_core.
SQLite/WAL scratch stays on a local filesystem; finalized summaries use the
file-scoped transaction helper below.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.d009.run_experiment import _habitat_state_for_scenario
from experiments.d014.run_formal import adapter_burst, config
from umbra_core.embodiment import _make_partner
from umbra_core.embodiment_adapters.profiles import MINIMAL_CREATURE_BODY
from umbra_core.habitat.engine import HabitatEngine
from umbra_core.habitat.state import FreeLocation, make_social_entity_object
from umbra_core.runtime import create_organism, load_organism

DIRECTIVE = 'UMBRA-CLOSE-02R'
BASELINE = 'f085d0e7b3c3ad0120caca6e7e485aeb71152170'
EVIDENCE = Path('/srv/ATLAS/100_ACTIVE/Projects/UMBRA-CORE/evidence/live-evidence/umbra-close-02r-hierarchical-intent-r1')


def durable_json(path: Path, value: Any) -> None:
    payload = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o640)
    try:
        written = 0
        while written < len(payload):
            count = os.write(fd, payload[written:])
            if count <= 0:
                raise OSError('short write')
            written += count
        os.fsync(fd)
    finally:
        os.close(fd)
    if path.exists():
        raise FileExistsError(path)
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def partner_object() -> Any:
    partner = _make_partner('partner:d014', 6.0, 4.0, 'H0', index=0)
    policy = partner.response_policy
    return make_social_entity_object(
        object_id='social:partner:d014',
        entity_ref=partner.hidden_partner_id,
        location=FreeLocation(6.0, 4.0, 'zone:general'),
        history_code=policy.history_code,
        motion_signature=partner.true_cues.motion_signature,
        appearance_signature=partner.true_cues.appearance_signature,
        response_timing_pattern=partner.true_cues.response_timing_pattern,
        interaction_style_cues=partner.true_cues.interaction_style_cues,
        response_mode=policy.mode,
        contingent_probability=policy.contingent_probability,
        flip_at=policy.flip_at,
        absent_windows=tuple(policy.absent_windows),
    )


def prepare(seed: int, db: Path, regime: str):
    organism = create_organism(config(seed, db, regime))
    for method in ('_ensure_development_intervention', '_ensure_memory_history', '_ensure_social_history', '_ensure_individuality_history'):
        getattr(organism, method)()
    engine = HabitatEngine(_habitat_state_for_scenario({'R0': 'S0', 'R1': 'S16', 'R2': 'S10', 'R3': 'S12'}[regime]))
    organism.embodiment.attach_habitat_engine(engine)
    organism.embodiment.body.x, organism.embodiment.body.y = 4.0, 3.0
    organism.perception.perceive_habitat_objects(organism.embodiment, 1.0, organism.rng)
    return organism, engine


def reload_existing(seed: int, db: Path, regime: str, saved_habitat: Any):
    organism = load_organism(config(seed, db, regime))
    engine = HabitatEngine(copy.deepcopy(saved_habitat))
    organism.embodiment.attach_habitat_engine(engine)
    return organism, engine


def run_case(regime: str, seed: int, work: Path, horizon: int) -> dict[str, Any]:
    db = work / f'{regime}-{seed}.sqlite'
    organism, engine = prepare(seed, db, regime)
    identity = organism.identity.agent_id
    state: dict[str, Any] = {'organism': organism, 'engine': engine, 'restart_count': 0, 'restart_identity_preserved': False, 'partner_created': False, 'partner_occluded': False, 'partner_reappeared': False, 'adapter_accepts': 0, 'body_change_count': 0, 'body_identity_preserved': False}
    actions: Counter[str] = Counter()
    extrema = {'min_energy': 1.0, 'max_fatigue': 0.0, 'min_integrity': 1.0, 'min_stimulation': 1.0}
    first_no_safe: int | None = None
    failure: dict[str, Any] | None = None
    started = time.monotonic()
    try:
        for _ in range(horizon):
            organism = state['organism']
            tick = organism.tick + 1
            if regime == 'R2' and tick == 600:
                engine = state['engine']
                engine.commit_object_creation(partner_object(), event_id=f'close02f:create:{seed}', transaction_id=f'close02f:create-txn:{seed}', request_id=f'close02f:create-req:{seed}')
                state['partner_created'] = True
            if regime == 'R2' and tick == 1200:
                state['adapter_accepts'] += int(adapter_burst(organism, seed, tick))
            if regime == 'R2' and tick == 1800:
                saved_habitat = copy.deepcopy(state['engine'].state)
                organism.snapshot_if_due(force=True)
                organism.close()
                organism, engine = reload_existing(seed, db, regime, saved_habitat)
                state.update(organism=organism, engine=engine, restart_count=state['restart_count'] + 1, restart_identity_preserved=organism.identity.agent_id == identity)
            if regime == 'R2' and tick == 2400:
                state['engine'].commit_object_visibility('social:partner:d014', occluded=True, event_id=f'close02f:hide:{seed}', transaction_id=f'close02f:hide-txn:{seed}', request_id=f'close02f:hide-req:{seed}')
                state['partner_occluded'] = True
            if regime == 'R2' and tick == 2600:
                state['engine'].commit_object_visibility('social:partner:d014', occluded=False, event_id=f'close02f:show:{seed}', transaction_id=f'close02f:show-txn:{seed}', request_id=f'close02f:show-req:{seed}')
                state['partner_reappeared'] = True
            if regime == 'R3' and tick == 3600:
                organism.embodiment_adapter.swap_profile(MINIMAL_CREATURE_BODY.profile_id, origin='CLOSE02R_R3_PREREGISTERED')
                state['body_change_count'] = 1
                state['body_identity_preserved'] = organism.identity.agent_id == identity
            result = organism.tick_once()
            state['engine'] = organism.embodiment._habitat_engine
            actions[str(result.get('capability'))] += 1
            extrema['min_energy'] = min(extrema['min_energy'], float(organism.phys.energy))
            extrema['max_fatigue'] = max(extrema['max_fatigue'], float(organism.phys.fatigue))
            extrema['min_integrity'] = min(extrema['min_integrity'], float(organism.phys.integrity))
            extrema['min_stimulation'] = min(extrema['min_stimulation'], float(organism.phys.stimulation))
            if result.get('no_safe_action') and first_no_safe is None:
                first_no_safe = organism.tick
            if organism.phys.critical_any() and failure is None:
                failure = {'tick': organism.tick, 'physiology': organism.phys.as_dict(), 'result': result}
                break
        completed = failure is None and state['organism'].tick >= horizon
        return {'directive': DIRECTIVE, 'regime': regime, 'seed': seed, 'ticks': state['organism'].tick, 'target_ticks': horizon, 'terminal': 'completed' if completed else 'scientific_failure', 'critical_failure': failure, 'first_no_safe_action': first_no_safe, **extrema, 'actions': dict(actions), 'restart_count': state['restart_count'], 'restart_identity_preserved': state['restart_identity_preserved'], 'partner_created': state['partner_created'], 'partner_occluded': state['partner_occluded'], 'partner_reappeared': state['partner_reappeared'], 'adapter_accepts': state['adapter_accepts'], 'body_change_count': state['body_change_count'], 'body_identity_preserved': state['body_identity_preserved'], 'elapsed_seconds': round(time.monotonic() - started, 3)}
    finally:
        state['organism'].close()
        for path in (db, Path(str(db) + '-wal'), Path(str(db) + '-shm')):
            path.unlink(missing_ok=True)


def seeds():
    development = json.loads((EVIDENCE / 'CLOSE02R_DEVELOPMENT_SEEDS.json').read_text())['seeds']
    formal = json.loads((EVIDENCE / 'CLOSE02R_FORMAL_SEEDS.json').read_text())['seeds']
    return development, formal


def preflight(work: Path) -> dict[str, Any]:
    development, _ = seeds()
    work.mkdir(parents=True, exist_ok=True)
    checks = [
        run_case('R0', development['R0'][0], work, 20),
        run_case('R1', development['R1'][0], work, 20),
        run_case('R2', development['R2'][0], work, 2601),
        run_case('R3', development['R3'][0], work, 3601),
    ]
    r2 = [run_case('R2', development['R2'][0], work, 2601)]
    r3 = [run_case('R3', development['R3'][0], work, 3601)]
    checks.extend(r2 + r3)
    passed = all(row['terminal'] == 'completed' for row in checks) and checks[2]['partner_created'] and checks[2]['restart_identity_preserved'] and checks[2]['partner_occluded'] and checks[2]['partner_reappeared'] and checks[3]['body_change_count'] == 1 and checks[3]['body_identity_preserved']
    return {'directive': DIRECTIVE, 'phase': 'regime_preflight', 'runs': len(checks), 'replay_pairs': 2, 'checks': checks, 'overall': 'PASS' if passed else 'FAIL'}


def execute(work: Path, output: Path) -> dict[str, Any]:
    development, formal = seeds()
    rows: list[dict[str, Any]] = []
    stages = [('R0_DEVELOPMENT', 'R0', development['R0']), ('KNOWN_R1', 'R1', development['known_R1']), ('R1_DEVELOPMENT', 'R1', development['R1']), ('R2_DEVELOPMENT', 'R2', development['R2']), ('R3_DEVELOPMENT', 'R3', development['R3'])]
    for stage, regime, population in stages:
        for seed in population:
            row = run_case(regime, seed, work, 7200)
            row['stage'] = stage
            rows.append(row)
            if row['terminal'] != 'completed':
                result = {'directive': DIRECTIVE, 'phase': 'development', 'terminal_stage': stage, 'rows': rows, 'formal_started': False, 'verdict': f'CLOSE02R_{stage}_FAIL'}
                durable_json(output, result)
                return result
    for regime in ('R0', 'R1', 'R2', 'R3'):
        for seed in formal[regime]:
            row = run_case(regime, seed, work, 7200)
            row['stage'] = f'FORMAL_{regime}'
            rows.append(row)
            if row['terminal'] != 'completed':
                result = {'directive': DIRECTIVE, 'phase': 'formal', 'terminal_stage': row['stage'], 'rows': rows, 'formal_started': True, 'verdict': 'CLOSE02R_FORMAL_INTEGRATED_VIABILITY_FAIL'}
                durable_json(output, result)
                return result
    result = {'directive': DIRECTIVE, 'phase': 'formal', 'terminal_stage': 'complete', 'rows': rows, 'formal_started': True, 'verdict': 'CLOSE02R_FINAL_AUTHORITY_INTEGRATED_VIABILITY_QUALIFIED'}
    durable_json(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('preflight', 'execute'), required=True)
    parser.add_argument('--work', type=Path, default=Path('/tmp/close02f-work'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.phase == 'preflight':
        print(json.dumps(preflight(args.work), indent=2, sort_keys=True))
    else:
        if args.output is None:
            raise SystemExit('--output is required for execute')
        print(json.dumps(execute(args.work, args.output), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
