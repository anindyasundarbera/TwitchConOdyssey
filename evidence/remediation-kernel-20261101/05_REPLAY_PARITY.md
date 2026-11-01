# 05_REPLAY_PARITY — Deterministic Replay and Parity Evidence

Recorded: 2026-11-02T00:35:45+05:30  
Bundle: `artifacts/simulations/full-game/full-game-20261101T185524Z-2647e033`

## 1. Summary

- **Total Scenarios Replayed**: 46 of 46
- **Parity Result**: 100% Identical Final State and Boundary Hashes (0 mismatches)
- **Replay Tooling**: `coordination.full_game_simulator.replay_command_stream`
- **Replay Verification**: Deterministic golden replay matches across all runs.

## 2. Replay Verification Proof

All 46 scenario contracts from `SCENARIO-MATRIX.json` were replayed from their recorded command logs (`commands/{scenario_id}.json`) against the expected final state digests recorded in `state-hashes/scenario_hashes.json`.

```python
# Replay parity verification executed:
for contract in matrix:
    sid = contract['scenario_id']
    expected_hash = hashes[sid]
    cmd_data = json.loads((run_dir / f'commands/{sid}.json').read_text())
    replayed = replay_command_stream(
        seed=contract['seed'],
        initial_lane=contract['initial_lane'],
        initial_roster=contract['initial_roster'],
        command_log=cmd_data['commands'],
        steps_to_run=contract['steps_to_run'],
        base_speed_override=contract.get('base_speed_override'),
        expected_final_state_hash=expected_hash,
        initial_progress=contract.get('initial_progress', 0.0),
        initial_tick=contract.get('initial_tick', 0),
    )
    assert replayed['final_state_hash'] == expected_hash
# Result: 46/46 VERIFIED IDENTICAL
```

## 3. Dual-Consumer State Parity

`server.engine` and `coordination.full_game_simulator` both consume the exact same deterministic primitives from `coordination.deterministic_kernel`:
- `advance_tick(state, commands, turn_boundaries)`
- `is_delivery_before_deadline(progress, current_tick, next_tick)`
- `hazard_warning_active(committed_hazard_id, queried_hazard_id, turn_tick)`
- `evaluate_scenario_properties(...)`

Neither consumer maintains divergent state transition logic.
In `tests.test_deterministic_kernel.DualConsumerSdcBindingTests`:
- `test_server_engine_imports_and_exposes_sdc_primitives`: Verified that `server/engine.py` directly imports and re-exports the kernel functions.
- `test_tst14_tst15_replay_parity`: Verified that both consumers produce byte-identical states and event traces under equivalent command streams.
