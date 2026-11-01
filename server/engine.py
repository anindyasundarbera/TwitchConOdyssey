"""Pure, fixed-step authoritative simulation. No network, filesystem, or wall clock."""
import copy
import hashlib
from fractions import Fraction
from schemas.validate import contract
ACTIONS = ('shield', 'patch', 'boost', 'sabotage')
SQUADS = ('Neon Foxes', 'Bay Phantoms', 'Golden Glitches', 'Pixel Pirates')
DISTRICTS = ('Little Italy / North Embarcadero', 'Embarcadero Waterfront / Marina',
             'Gaslamp Quarter', 'San Diego Convention Center', 'Fictional Main Stage')

def cohort(viewer, k):
    return int.from_bytes(hashlib.sha256(viewer.encode()).digest()[:8], 'big') % k

class Engine:
    def __init__(self, k=4):
        if not 1 <= k <= 16:
            raise ValueError('K must be 1..16')
        self.k, self.tick, self.round = k, 0, 1
        self.progress, self.integrity, self.pool = 0, 100, 1000
        self.status, self.crisis = 'racing', 'Platform outage'
        self.votes, self.players, self.events, self.history = {}, {}, [], []
        self.tally, self.effects, self.rewards = [], [], {}
        self.emit('crisis', {'name': self.crisis})
    @property
    def phase(self):
        return 'planning' if self.tick % 500 < 400 else 'action'
    def emit(self, kind, data):
        event = {'tick': self.tick, 'kind': kind, **data}
        self.events.append(event)
        self.history = (self.history + [event])[-40:]
    def submit(self, viewer, action, round_id):
        contract('action', action)
        if not isinstance(viewer, str) or not 1 <= len(viewer) <= 64:
            raise ValueError('invalid viewer')
        if self.status != 'racing' or self.phase != 'planning' or round_id != self.round:
            raise ValueError('closed or stale planning window')
        if viewer not in self.players and len(self.players) >= 10000:
            raise ValueError('match capacity reached')
        self.players[viewer] = cohort(viewer, self.k)
        self.votes[viewer] = copy.deepcopy(action) # Replacement: one bounded budget per viewer per round.
        self.emit('vote', {'viewer': viewer, 'action': action, 'squad': self.players[viewer]})
    def aggregate(self):
        totals = [{a: Fraction(0) for a in ACTIONS} for _ in range(self.k)]
        counts = [0] * self.k
        for viewer, vote in self.votes.items():
            squad = self.players[viewer]
            counts[squad] += 1
            for action in vote['choices']:
                totals[squad][action] += Fraction(1, len(vote['choices']))
        result = []
        for squad in range(self.k):
            bot = counts[squad] == 0
            # Empty squads counter the active crisis, prioritizing damaged builds.
            choice = 'patch' if self.integrity < 65 else ('shield' if self.round % 2 else 'boost')
            if bot:
                totals[squad][choice] = Fraction(1)
            else:
                totals[squad] = {a:v/counts[squad] for a,v in totals[squad].items()}
            winner = max(ACTIONS, key=lambda a: totals[squad][a])
            result.append({'squad': squad, 'members': counts[squad], 'bot': bot, 'winner': winner, 'weights': {a:float(v) for a,v in totals[squad].items()}})
        return result
    def resolve(self):
        self.tally = self.aggregate()
        self.effects = [s['winner'] for s in self.tally]
        shield, patch, boost, sabotage = (self.effects.count(a) for a in ACTIONS)
        damage = max(0, 18 + sabotage*6 - shield*12)
        self.integrity = max(0, min(100, self.integrity-damage+patch*15))
        self.pool += 100 + 25*len(self.votes)
        self.emit('execution', {'effects': self.effects, 'damage': damage, 'tally': self.tally})
    def step(self):
        if self.status != 'racing':
            return
        self.tick += 1
        if self.tick % 500 == 400:
            self.resolve()
        if self.phase == 'action':
            self.progress = min(100, self.progress + (0.21 + self.effects.count('boost')*.075))
        if self.integrity <= 0 or self.progress >= 100 or self.tick >= 3000:
            self.status = 'delivered' if self.progress >= 100 and self.integrity > 0 else 'failed'
            if self.status == 'delivered':
                broadcaster = self.pool // 2
                self.rewards = {'broadcaster': broadcaster, 'viewer_pool': self.pool-broadcaster, 'participants': len(self.players), 'per_viewer': (self.pool-broadcaster)//max(1,len(self.players)), 'remainder': (self.pool-broadcaster)%max(1,len(self.players))}
            self.emit('finish', {'status': self.status, 'rewards': self.rewards})
        elif self.tick % 500 == 0:
            self.round += 1
            self.votes = {}
            self.crisis = ('Platform outage', 'Creator burnout', 'Sponsor traffic surge')[(self.round-1)%3]
            self.emit('crisis', {'name': self.crisis})
    def snapshot(self):
        return {'version':1, 'tick':self.tick, 'round':self.round, 'phase':self.phase, 'remaining':round((400-self.tick%500 if self.phase=='planning' else 500-self.tick%500)/20,2), 'progress':round(self.progress,4), 'integrity':self.integrity, 'pool':self.pool, 'status':self.status, 'crisis':self.crisis, 'district':DISTRICTS[min(4,int(self.progress//25))], 'squads':self.aggregate(), 'players':dict(self.players), 'viewer_votes':copy.deepcopy(self.votes), 'viewers':len(self.players), 'votes':len(self.votes), 'effects':self.effects, 'rewards':self.rewards, 'telemetry':copy.deepcopy(self.history)}
