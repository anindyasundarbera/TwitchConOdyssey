"""Local event journal. Writes are batched outside the simulation lock."""
import json
import sqlite3
from pathlib import Path

class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, match_id TEXT, tick INTEGER, kind TEXT, payload TEXT);
        CREATE TABLE IF NOT EXISTS snapshots(match_id TEXT, tick INTEGER, payload TEXT, PRIMARY KEY(match_id,tick));
        CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append only'); END;''')
    def append(self, match_id, events, snapshot=None):
        with self.db:
            self.db.executemany('INSERT INTO events(match_id,tick,kind,payload) VALUES(?,?,?,?)', [(match_id,e['tick'],e['kind'],json.dumps(e,sort_keys=True)) for e in events])
            if snapshot:
                self.db.execute('INSERT OR REPLACE INTO snapshots VALUES(?,?,?)', (match_id,snapshot['tick'],json.dumps(snapshot,sort_keys=True)))
    def events(self, match_id):
        return [json.loads(r[0]) for r in self.db.execute('SELECT payload FROM events WHERE match_id=? ORDER BY seq',(match_id,))]
    def close(self):
        self.db.close()
