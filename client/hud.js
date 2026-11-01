/* W4/TASK-007 — Presentation & mobile HUD renderer.
 *
 * Pure view layer: derives everything from an authoritative canonical state
 * snapshot (TASK-006 contract). It never mutates engine state, never performs
 * physics, and never reads chat. Transport/intent objects map 1:1 to canonical
 * command kinds; the caller builds the signed envelope via
 * coordination.canonical_commands.make_command and submits it to the engine.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.Hud = factory();
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const TURN_TICKS = 600;        // 30s turns: 20s planning / 5s resolution / 5s reward
  const PLANNING_TICKS = 400;
  const HAZARD_WARNING_START = 300; // warning window [15s, 20s)
  const TERMINAL = new Set(["delivered", "wiped", "failed"]);
  const STATUS_LABELS = {
    applied: "Input accepted.",
    rejected: "Input rejected. Check the control and try again.",
    duplicate: "Already counted this turn — one influence per subject.",
    expired: "Too late — the window closed. Input was not counted.",
  };
  const MODE_LABELS = {
    live: "Live Twitch participation",
    fixture: "Offline fixture (not live Twitch activity)",
  };
  const CONNECTION_LABELS = {
    online: "Connected to the authoritative simulation.",
    retrying: "Reconnecting to the authoritative simulation — controls are paused.",
    offline: "Connection lost. The last authoritative state is shown; retry to reconnect.",
  };

  function requireState(state) {
    if (!state || typeof state !== "object") throw new TypeError("canonical state required");
    for (const key of ["tick", "turn", "phase", "status", "movement", "avatar", "hazard"]) {
      if (!(key in state)) throw new TypeError("canonical state missing " + key);
    }
    return state;
  }

  function hazardView(state) {
    const committed = state.hazard.committed || null;
    if (!committed) {
      return { id: null, warning: false, secondsLeft: null, active: false, countered: false };
    }
    const turnTick = state.tick % TURN_TICKS;
    const inWarning = Boolean(state.hazard.warning_active) &&
      turnTick >= HAZARD_WARNING_START && turnTick < PLANNING_TICKS;
    const secondsLeft = inWarning
      ? Math.max(0, (PLANNING_TICKS - turnTick) / 20)
      : 0;
    return {
      id: committed,
      warning: inWarning,
      secondsLeft: Number(secondsLeft.toFixed(2)),
      active: Boolean(state.hazard.obstacle_active),
      countered: Boolean(state.hazard.hazard_countered),
    };
  }

  function previewFor(state) {
    if (TERMINAL.has(state.status)) {
      return state.status === "delivered"
        ? "Delivered before the deadline. Final Hype has been settled once."
        : "Run ended with no delivery. Hype settles to zero — no extra turn is playable.";
    }
    if (state.is_paused) return "Paused by the stage operator. Controls are locked until resume.";
    if (state.phase === "planning") {
      return state.hazard.committed
        ? "Vote clear_lane on the committed hazard before the 20s window closes."
        : "Hazard proposals are open until 15s; counter votes stay open until 20s.";
    }
    if (state.phase === "resolution") {
      return state.hazard.obstacle_active
        ? "Obstacle active in the center lane. A collision slows you for 2s, no HP loss."
        : "Resolution in progress. Steering remains available.";
    }
    return "Reward phase: the settled outcome is shown; the next turn starts automatically.";
  }

  function deriveView(state, options) {
    requireState(state);
    const opts = options || {};
    const mode = opts.mode === "live" ? "live" : "fixture";
    const progress = Math.min(100, Math.max(0, Number(state.movement.progress) || 0));
    const terminal = TERMINAL.has(state.status);
    const controlsEnabled = state.status === "racing" && !state.is_paused;
    const hazard = hazardView(state);
    const audience = state.audience || {};
    return {
      mode,
      modeLabel: MODE_LABELS[mode],
      tick: state.tick,
      turn: state.turn,
      phase: state.phase,
      paused: Boolean(state.is_paused),
      terminal,
      progressPercent: Number(progress.toFixed(1)),
      district: state.movement.district,
      lane: state.avatar.lane,
      transitioning: state.avatar.transition_remaining_ticks > 0,
      hazard,
      pool: state.bounty.pool,
      fixtureHype: state.bounty.synthetic_fixture_pool,
      collisions: state.bounty.collisions_total,
      preview: previewFor(state),
      statusLine: terminal
        ? (state.status === "delivered" ? "Match delivered." : "Match ended in a wipe.")
        : "Turn " + state.turn + " — " + state.phase + " phase.",
      audience: {
        liveEligible: audience.roster_size || 0,
        counterVotes: audience.counter_votes_count || 0,
        liveCounters: audience.eligible_voters_count || 0,
      },
      controls: {
        enabled: controlsEnabled,
        buttons: [
          { action: "left", label: "Steer left", kind: "streamer.steer", disabled: !controlsEnabled },
          { action: "right", label: "Steer right", kind: "streamer.steer", disabled: !controlsEnabled },
        ],
      },
      accessibilitySummary:
        MODE_LABELS[mode] + ". " + previewFor(state) + " Progress " +
        Math.round(progress) + " percent.",
    };
  }

  function controlIntent(view, action) {
    if (!view || !view.controls.enabled) return null;
    if (action !== "left" && action !== "right" && action !== "cancel") return null;
    return { kind: "streamer.steer", payload: { direction: action } };
  }

  function statusMessage(status) {
    if (!(status in STATUS_LABELS)) return null;
    return { status, message: STATUS_LABELS[status], announce: STATUS_LABELS[status] };
  }

  function connectionNotice(status) {
    return CONNECTION_LABELS[status] || CONNECTION_LABELS.offline;
  }

  function renderHud(view, root) {
    if (!view || !root || typeof root.querySelector !== "function") {
      throw new TypeError("view and root are required");
    }
    const set = (selector, text) => {
      const node = root.querySelector(selector);
      if (node) node.textContent = text;
    };
    set("[data-hud=mode]", view.modeLabel);
    set("[data-hud=status]", view.statusLine);
    set("[data-hud=progress]", "Route " + view.progressPercent + "% — " + view.district);
    set("[data-hud=phase]", "Turn " + view.turn + " · " + view.phase +
      (view.paused ? " · paused" : ""));
    set("[data-hud=hazard]", view.hazard.id
      ? ("Hazard " + view.hazard.id + (view.hazard.warning
          ? " — warning " + view.hazard.secondsLeft + "s"
          : (view.hazard.countered ? " — cleared" : " — resolved")))
      : "No committed hazard this turn");
    set("[data-hud=preview]", view.preview);
    set("[data-hud=pool]", "Hype " + view.pool);
    set("[data-hud=audience]", view.mode === "live"
      ? (view.audience.liveCounters + " of " + view.audience.liveEligible + " eligible accounts countered")
      : "Fixture run — no live Twitch participation");
    const fill = root.querySelector("[data-hud=progress-fill]");
    if (fill && fill.style) fill.style.width = view.progressPercent + "%";
    for (const button of view.controls.buttons) {
      const node = root.querySelector("[data-control=" + button.action + "]");
      if (node) {
        node.disabled = button.disabled;
        if (typeof node.setAttribute === "function") {
          node.setAttribute("aria-label", button.label);
        }
      }
    }
    return view;
  }

  return {
    TURN_TICKS, PLANNING_TICKS,
    deriveView, controlIntent, statusMessage, connectionNotice, renderHud,
  };
});
