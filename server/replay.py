import hashlib
import json
from pathlib import Path
from server.engine import Engine
from server.providers import MockProvider

def load_fixture(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    for row in rows:
        from schemas.validate import contract
        contract('input',row)
    if rows != sorted(rows,key=lambda r:r['tick']):
        raise ValueError('fixture must be ordered by tick')
    return rows

def replay(path, ticks=3000):
    engine, provider = Engine(), MockProvider()
    rows = load_fixture(path)
    for _ in range(ticks):
        for row in rows:
            if row['tick'] == engine.tick:
                action = provider.parse(row['text'],{})
                engine.emit('chat', {'viewer':row['viewer'],'text':row['text'],'provider':provider.name})
                engine.emit('tool_call', {'name':'submit_game_action','arguments':action,'provider':provider.name})
                engine.submit(row['viewer'],action,engine.round)
        engine.step()
        if engine.status != 'racing':
            break
    snapshot = engine.snapshot()
    return snapshot, hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline-fixture',default='fixtures/stage.jsonl')
    args = parser.parse_args()
    state,digest = replay(args.offline_fixture)
    print(json.dumps({'status':state['status'],'tick':state['tick'],'digest':digest,'state':state},indent=2))


def replay_journal(events, final_tick, k=4):
    """Replay accepted vote events; regenerate engine-derived events from ticks.

    Chat/proposal/validation audit rows do not affect gameplay state.
    """
    engine=Engine(k)
    votes=[event for event in events if event['kind']=='vote']
    cursor=0
    while engine.tick <= final_tick:
        while cursor < len(votes) and votes[cursor]['tick']==engine.tick:
            row=votes[cursor]
            engine.submit(row['viewer'],row['action'],engine.round)
            cursor+=1
        if engine.tick==final_tick or engine.status!='racing':break
        engine.step()
    return engine.snapshot()
