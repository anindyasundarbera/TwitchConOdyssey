/* W4/TASK-007 offline presentation-state tests (node --test). No browser, network or engine mutation. */
const test = require("node:test");
const assert = require("node:assert/strict");
const { deriveView, controlIntent, statusMessage, connectionNotice, renderHud } = require("./hud.js");

function state(overrides = {}) {
  const base = {
    schema_version: 1,
    tick: 0,
    turn: 1,
    phase: "planning",
    status: "racing",
    is_paused: false,
    avatar: { lane: 1, lateral_pos: 1.0, transition_remaining_ticks: 0 },
    movement: { progress: 12.5, district: "Little Italy / North Embarcadero",
      slowdown_ticks_remaining: 0, turn_slowdown_ticks: 0, match_slowdown_ticks: 0 },
    bounty: { pool: 20, synthetic_fixture_pool: 0, collisions_total: 0, collision_halved: false },
    hazard: { committed: "hz_1", warning_active: false, obstacle_active: false, hazard_countered: false },
    audience: { roster_size: 10, counter_votes_count: 2, eligible_voters_count: 2 },
    booths: [], audio_state: "music",
  };
  return Object.assign(base, overrides);
}

test("planning HUD renders progress, committed hazard id and 1:1 control intents", () => {
  const view = deriveView(state({ tick: 300, hazard: { committed: "hz_1", warning_active: true,
    obstacle_active: false, hazard_countered: false } }), { mode: "live" });
  assert.equal(view.progressPercent, 12.5);
  assert.equal(view.hazard.id, "hz_1");
  assert.equal(view.hazard.secondsLeft, 5);
  assert.equal(view.controls.enabled, true);
  assert.deepEqual(controlIntent(view, "left"), { kind: "streamer.steer", payload: { direction: "left" } });
  assert.deepEqual(controlIntent(view, "right"), { kind: "streamer.steer", payload: { direction: "right" } });
  assert.deepEqual(controlIntent(view, "cancel"), { kind: "streamer.steer", payload: { direction: "cancel" } });
  assert.equal(controlIntent(view, "jump"), null);
});

test("hazard warning timer is bound to the half-open 15s..20s window", () => {
  const at = (tick, active) => deriveView(state({ tick,
    hazard: { committed: "hz_9", warning_active: active, obstacle_active: false, hazard_countered: false } }));
  assert.equal(at(299, false).hazard.secondsLeft, 0);
  assert.equal(at(300, true).hazard.secondsLeft, 5);
  assert.equal(at(399, true).hazard.secondsLeft, 0.05);
  assert.equal(at(400, false).hazard.secondsLeft, 0);
  assert.equal(at(0, false).hazard.id, "hz_9");
});

test("phase previews and terminal outcomes are explicit, with no extra turn", () => {
  assert.match(deriveView(state()).preview, /Hazard proposals|clear_lane/);
  assert.match(deriveView(state({ phase: "resolution", tick: 410,
    hazard: { committed: "hz_1", warning_active: false, obstacle_active: true, hazard_countered: false } })).preview,
    /Obstacle active/);
  assert.match(deriveView(state({ phase: "reward", tick: 500 })).preview, /Reward phase/);
  const delivered = deriveView(state({ status: "delivered" }));
  assert.equal(delivered.terminal, true);
  assert.equal(delivered.controls.enabled, false);
  assert.match(delivered.preview, /Delivered before the deadline/);
  const wiped = deriveView(state({ status: "wiped" }));
  assert.match(wiped.preview, /no extra turn/);
  assert.match(deriveView(state({ is_paused: true })).preview, /Paused/);
});

test("rejected/late/duplicate/expired feedback is textual and accessible", () => {
  const seen = new Set();
  for (const status of ["applied", "rejected", "duplicate", "expired"]) {
    const feedback = statusMessage(status);
    assert.ok(feedback && feedback.message && feedback.announce);
    assert.equal(feedback.status, status);
    seen.add(feedback.message);
  }
  assert.equal(seen.size, 4);
  assert.equal(statusMessage("mystery"), null);
});

test("fixture and live modes are visibly distinct and fixtures never count as live participants", () => {
  const fixture = deriveView(state({ bounty: { pool: 0, synthetic_fixture_pool: 40,
    collisions_total: 0, collision_halved: false } }), { mode: "fixture" });
  assert.match(fixture.modeLabel, /not live Twitch activity/);
  assert.equal(fixture.fixtureHype, 40);
  assert.equal(fixture.audience.liveCounters, 2);
  assert.match(fixture.accessibilitySummary, /Offline fixture/);
  const live = deriveView(state(), { mode: "live" });
  assert.match(live.modeLabel, /Live Twitch/);
});

test("connection states are explicit and recoverable", () => {
  assert.match(connectionNotice("online"), /Connected/);
  assert.match(connectionNotice("retrying"), /Reconnecting/);
  assert.match(connectionNotice("offline"), /retry/i);
  assert.match(connectionNotice("unknown"), /retry/i);
});

test("renderHud writes only text/attributes and never mutates the view input", () => {
  const view = deriveView(state({ tick: 300, hazard: { committed: "hz_1", warning_active: true,
    obstacle_active: false, hazard_countered: false } }));
  const frozen = JSON.stringify(view);
  const nodes = {};
  const make = () => ({ textContent: "", disabled: false, attrs: {}, style: {},
    setAttribute(k, v) { this.attrs[k] = v; } });
  const root = { querySelector: (selector) => (nodes[selector] = nodes[selector] || make()) };
  renderHud(view, root);
  assert.match(nodes["[data-hud=mode]"].textContent, /fixture/i);
  assert.equal(nodes["[data-hud=hazard]"].textContent.includes("hz_1"), true);
  assert.equal(nodes["[data-hud=preview]"].textContent.length > 0, true);
  assert.equal(nodes["[data-control=left]"].disabled, false);
  assert.equal(nodes["[data-control=left]"].attrs["aria-label"], "Steer left");
  assert.equal(nodes["[data-hud=progress-fill]"].style.width, "12.5%");
  assert.equal(JSON.stringify(view), frozen);
});
