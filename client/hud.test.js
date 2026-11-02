/* W4/TASK-007 offline presentation-state tests (node --test). No browser, network or engine mutation. */
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { deriveView, disconnectedView, controlIntent, statusMessage, connectionNotice, renderHud } = require("./hud.js");

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

const fixtureEvidence = { authority: "authoritative-runtime", origin: "fixture",
  origin_label: "Offline fixture (not live Twitch activity)", live_participation: false };
const liveEvidence = { authority: "authoritative-runtime", origin: "live",
  origin_label: "Live Twitch participation", live_participation: true, live_verified: true };

test("planning HUD renders progress, committed hazard id and 1:1 control intents", () => {
  const view = deriveView(state({ tick: 300, hazard: { committed: "hz_1", warning_active: true,
    obstacle_active: false, hazard_countered: false } }), liveEvidence);
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
    hazard: { committed: "hz_9", warning_active: active, obstacle_active: false, hazard_countered: false } }), fixtureEvidence);
  assert.equal(at(299, false).hazard.secondsLeft, 0);
  assert.equal(at(300, true).hazard.secondsLeft, 5);
  assert.equal(at(399, true).hazard.secondsLeft, 0.05);
  assert.equal(at(400, false).hazard.secondsLeft, 0);
  assert.equal(at(0, false).hazard.id, "hz_9");
});

test("phase previews and terminal outcomes are explicit, with no extra turn", () => {
  assert.match(deriveView(state(), fixtureEvidence).preview, /Hazard proposals|clear_lane/);
  assert.match(deriveView(state({ phase: "resolution", tick: 410,
    hazard: { committed: "hz_1", warning_active: false, obstacle_active: true, hazard_countered: false } }), fixtureEvidence).preview,
    /Obstacle active/);
  assert.match(deriveView(state({ phase: "reward", tick: 500 }), fixtureEvidence).preview, /Reward phase/);
  const delivered = deriveView(state({ status: "delivered" }), fixtureEvidence);
  assert.equal(delivered.terminal, true);
  assert.equal(delivered.controls.enabled, false);
  assert.match(delivered.preview, /Delivered before the deadline/);
  const wiped = deriveView(state({ status: "wiped" }), fixtureEvidence);
  assert.match(wiped.preview, /no extra turn/);
  assert.match(deriveView(state({ is_paused: true }), fixtureEvidence).preview, /Paused/);
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
    collisions_total: 0, collision_halved: false } }), fixtureEvidence);
  assert.match(fixture.modeLabel, /not live Twitch activity/);
  assert.equal(fixture.fixtureHype, 40);
  assert.equal(fixture.audience.liveCounters, 2);
  assert.match(fixture.accessibilitySummary, /Offline fixture/);
  const live = deriveView(state(), liveEvidence);
  assert.match(live.modeLabel, /Live Twitch/);
  assert.throws(() => deriveView(state(), { mode: "live" }), /evidence context/);
  assert.throws(() => deriveView(state(), { ...fixtureEvidence, live_participation: true }), /inconsistent/);
});

test("connection states are explicit and recoverable", () => {
  assert.match(connectionNotice("online"), /Connected/);
  assert.match(connectionNotice("online", "fixture"), /not live Twitch activity/i);
  assert.match(connectionNotice("online", "live"), /Verified live Twitch adapter active/);
  assert.match(connectionNotice("retrying"), /Reconnecting/);
  assert.match(connectionNotice("offline"), /retry/i);
  assert.match(connectionNotice("unknown"), /retry/i);
});

test("live mode fails closed unless the server marks the live adapter verified", () => {
  assert.equal(deriveView(state(), liveEvidence).mode, "live");
  assert.equal(deriveView(state(), liveEvidence).liveVerified, true);
  const activeAdapter = deriveView(state(), { ...liveEvidence, fixture: false,
    adapter: { transport: "live", state: "active_live", validated: true, subscribed: true } });
  assert.equal(activeAdapter.mode, "live");
  const workerAEnvelope = deriveView(state(), {
    authority: "authoritative-runtime",
    origin: "live",
    origin_label: "live Twitch EventSub channel.chat.message",
    live_participation: true,
    live_verified: true,
    fixture: false,
    adapter: { transport: "live", state: "active_live", validated: true, subscribed: true,
      notifications: 1, accepted_commands: 1 },
  });
  assert.equal(workerAEnvelope.mode, "live");
  assert.match(workerAEnvelope.badge, /LIVE/);
  assert.throws(() => deriveView(state(), { ...liveEvidence, fixture: true }), /fixture flag/);
  const unverified = deriveView(state(), { authority: "authoritative-runtime", origin: "live",
    origin_label: "Live Twitch participation", live_participation: true });
  assert.equal(unverified.mode, "disconnected");
  assert.equal(unverified.controls.enabled, false);
  assert.match(unverified.connectionNotice, /not verified/i);
  assert.throws(() => deriveView(state(), { ...liveEvidence, live_participation: false }), /inconsistent/);
  assert.throws(() => deriveView(state(), { ...fixtureEvidence, live_verified: true }), /cannot claim live/);
  assert.throws(() => deriveView(state(), { ...liveEvidence, origin: "query" }), /invalid evidence origin/);
});

test("inactive live adapter state fails closed even when the envelope origin is fixture", () => {
  const inactive = deriveView(state(), { ...fixtureEvidence,
    origin_label: "live adapter disconnected / offline (not live Twitch activity)",
    adapter: { transport: "live", state: "disconnected", validated: true, subscribed: false } });
  assert.equal(inactive.mode, "disconnected");
  assert.equal(inactive.controls.enabled, false);
  assert.match(inactive.connectionNotice, /not active/i);
  const failed = deriveView(state(), { ...fixtureEvidence,
    adapter: { transport: "live", state: "failed" } });
  assert.equal(failed.mode, "disconnected");
  const fixtureTransport = deriveView(state(), { ...fixtureEvidence,
    adapter: { transport: "fixture", state: "active_fixture" } });
  assert.equal(fixtureTransport.mode, "fixture");
});

test("disconnected mode disables controls and makes no live claim", () => {
  const view = disconnectedView("Network unavailable");
  assert.equal(view.mode, "disconnected");
  assert.equal(view.liveVerified, false);
  assert.equal(view.controls.enabled, false);
  assert.equal(view.controls.buttons.every((button) => button.disabled), true);
  assert.match(view.connectionNotice, /Network unavailable/);
  assert.match(view.accessibilitySummary, /not inferred/i);
  assert.equal(view.hasState, false);
  assert.equal(view.progressPercent, null);
  const withLastState = deriveView(state(), { authority: "authoritative-runtime",
    origin: "disconnected", reason: "Live adapter lost" });
  assert.equal(withLastState.mode, "disconnected");
  assert.equal(withLastState.hasState, true);
  assert.equal(withLastState.controls.enabled, false);
  assert.match(withLastState.statusLine, /Controls locked/);
  assert.equal(controlIntent(withLastState, "left"), null);
});

test("renderHud writes the truthful badge, connection notice and disabled state", () => {
  const nodes = {};
  const make = () => ({ textContent: "", disabled: false, attrs: {}, style: {},
    setAttribute(k, v) { this.attrs[k] = v; } });
  const root = { querySelector: (selector) => (nodes[selector] = nodes[selector] || make()) };
  renderHud(deriveView(state(), liveEvidence), root);
  assert.equal(nodes["[data-hud=badge]"].textContent, "LIVE · VERIFIED TWITCH");
  assert.equal(nodes["[data-hud=badge]"].attrs["data-mode"], "live");
  assert.match(nodes["[data-hud=connection]"].textContent, /Verified live Twitch adapter active/);
  assert.equal(nodes["[data-control=left]"].disabled, false);
  renderHud(disconnectedView("offline"), root);
  assert.equal(nodes["[data-hud=badge]"].textContent, "DISCONNECTED");
  assert.equal(nodes["[data-hud=badge]"].attrs["data-mode"], "disconnected");
  assert.equal(nodes["[data-control=left]"].disabled, true);
  assert.equal(nodes["[data-control=right]"].disabled, true);
  assert.match(nodes["[data-hud=connection]"].textContent, /offline/);
  assert.match(nodes["[data-hud=preview]"].textContent, /No live status is inferred/);
});

test("the client never infers live mode from URL, storage, local flags or screenshots", () => {
  const app = fs.readFileSync(path.join(__dirname, "app.js"), "utf8");
  const index = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  for (const token of ["URLSearchParams", "location.search", "localStorage",
    "sessionStorage", "event.detail.mode", "?live"]) {
    assert.equal(app.includes(token) || index.includes(token), false, token);
  }
  assert.match(index, /deriveView\(event\.detail\.state, event\.detail\.evidence\)/);
  assert.match(index, /odyssey:disconnected/);
  assert.match(fs.readFileSync(path.join(__dirname, "hud.js"), "utf8"), /live_verified/);
});

test("the presentation shell is mobile-ready, labelled and focus-visible", () => {
  const css = fs.readFileSync(path.join(__dirname, "style.css"), "utf8");
  const index = fs.readFileSync(path.join(__dirname, "index.html"), "utf8");
  assert.match(index, /name="viewport" content="width=device-width,initial-scale=1"/);
  assert.match(index, /aria-label="Steer left"/);
  assert.match(index, /role="status" aria-live="polite"/);
  assert.match(index, /data-hud="mode-detail"/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /@media\(max-width:600px\)/);
  assert.match(css, /@media\(max-width:430px\)/);
  assert.match(css, /\.hud-mode\[data-mode=live\]/);
});

test("renderHud writes only text/attributes and never mutates the view input", () => {
  const view = deriveView(state({ tick: 300, hazard: { committed: "hz_1", warning_active: true,
    obstacle_active: false, hazard_countered: false } }), fixtureEvidence);
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
