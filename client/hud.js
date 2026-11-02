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
    live: "Live Twitch participation (verified EventSub adapter)",
    fixture: "Offline fixture (not live Twitch activity)",
    disconnected: "Disconnected — no authoritative state",
  };
  const MODE_BADGES = {
    live: "LIVE · VERIFIED TWITCH",
    fixture: "OFFLINE FIXTURE",
    disconnected: "DISCONNECTED",
  };
  const CONNECTION_LABELS = {
    online: "Connected to the authoritative simulation.",
    retrying: "Reconnecting to the authoritative simulation — controls are paused.",
    offline: "Disconnected — no authoritative state. Retry to reconnect; live status is not inferred.",
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

  function requireEvidence(evidence) {
    if (!evidence || typeof evidence !== "object") throw new TypeError("authoritative evidence context required");
    if (evidence.authority !== "authoritative-runtime") throw new TypeError("untrusted evidence context");
    if (evidence.origin !== "fixture" && evidence.origin !== "live" && evidence.origin !== "disconnected") {
      throw new TypeError("invalid evidence origin");
    }
    if ("live_verified" in evidence && typeof evidence.live_verified !== "boolean") {
      throw new TypeError("invalid live verification flag");
    }
    if (evidence.origin === "fixture" &&
        (evidence.live_participation !== false || evidence.live_verified === true)) {
      throw new TypeError("inconsistent evidence origin: fixture cannot claim live participation");
    }
    if (evidence.origin === "live" && evidence.live_participation !== true) {
      throw new TypeError("inconsistent evidence origin");
    }
    if (evidence.origin === "live" && evidence.fixture === true) {
      throw new TypeError("inconsistent evidence origin: fixture flag on live evidence");
    }
    return evidence;
  }

  function evidenceMode(evidence) {
    if (evidence.origin === "disconnected") return "disconnected";
    if (evidence.origin === "fixture") {
      const adapter = evidence.adapter;
      if (adapter && typeof adapter === "object" && adapter.transport === "live" &&
          adapter.state !== "active_live") {
        return "disconnected";
      }
      return "fixture";
    }
    const adapter = evidence.adapter;
    if (adapter && typeof adapter === "object" && adapter.transport === "live" &&
        adapter.state !== "active_live") {
      return "disconnected";
    }
    return "live";
  }

  function disconnectedView(reason, state) {
    const safe = state && typeof state === "object" &&
      typeof state.tick === "number" && typeof state.turn === "number" &&
      state.movement && state.bounty && state.avatar;
    const note = reason || CONNECTION_LABELS.offline;
    return {
      mode: "disconnected",
      modeLabel: MODE_LABELS.disconnected,
      badge: MODE_BADGES.disconnected,
      modeDetail: "No live status is inferred while the authoritative state is unavailable.",
      connectionNotice: note,
      liveVerified: false,
      hasState: Boolean(safe),
      tick: safe ? state.tick : null,
      turn: safe ? state.turn : null,
      phase: safe ? state.phase : "unavailable",
      paused: true,
      terminal: false,
      progressPercent: safe ? Number(Math.min(100, Math.max(0, Number(state.movement.progress) || 0)).toFixed(1)) : null,
      district: safe ? state.movement.district : "Unavailable",
      lane: safe ? state.avatar.lane : null,
      transitioning: false,
      hazard: { id: null, warning: false, secondsLeft: null, active: false, countered: false },
      pool: safe ? state.bounty.pool : null,
      fixtureHype: safe ? state.bounty.synthetic_fixture_pool : null,
      collisions: safe ? state.bounty.collisions_total : null,
      preview: "Controls are disabled. No live status is inferred from local state, a query parameter or a screenshot.",
      statusLine: safe
        ? "Disconnected — last authoritative state shown. Controls locked."
        : "Disconnected — no authoritative state received.",
      audience: { liveEligible: 0, counterVotes: 0, liveCounters: 0 },
      controls: {
        enabled: false,
        buttons: [
          { action: "left", label: "Steer left", kind: "streamer.steer", disabled: true },
          { action: "right", label: "Steer right", kind: "streamer.steer", disabled: true },
        ],
      },
      accessibilitySummary:
        "Disconnected. No authoritative state. Live status is not inferred. Controls disabled.",
    };
  }

  function deriveView(state, evidence) {
    const context = requireEvidence(evidence);
    const mode = evidenceMode(context);
    if (mode === "disconnected") {
      const reason = context.origin === "disconnected"
        ? (context.reason || context.origin_label)
        : "Live adapter is not active. Controls locked; live status is not claimed.";
      return disconnectedView(reason, state);
    }
    if (context.origin === "live" && context.live_verified !== true) {
      return disconnectedView(
        "Live evidence was not verified by the live adapter. Controls locked; live status is not claimed.", state);
    }
    requireState(state);
    const progress = Math.min(100, Math.max(0, Number(state.movement.progress) || 0));
    const terminal = TERMINAL.has(state.status);
    const controlsEnabled = state.status === "racing" && !state.is_paused;
    const hazard = hazardView(state);
    const audience = state.audience || {};
    const notice = connectionNotice("online", mode);
    return {
      mode,
      modeLabel: context.origin_label || MODE_LABELS[mode],
      badge: MODE_BADGES[mode],
      modeDetail: mode === "live"
        ? "Server-owned live provenance; the verified adapter is active."
        : "Server-owned fixture provenance; this is not live Twitch activity.",
      connectionNotice: notice,
      liveVerified: mode === "live",
      hasState: true,
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

  function connectionNotice(status, mode) {
    if (status === "online" && mode === "live") {
      return "Connected to the authoritative runtime. Verified live Twitch adapter active.";
    }
    if (status === "online" && mode === "fixture") {
      return "Connected to the authoritative offline fixture. Not live Twitch activity.";
    }
    return CONNECTION_LABELS[status] || CONNECTION_LABELS.offline;
  }

  function renderHud(view, root) {
    if (!view || !root || typeof root.querySelector !== "function") {
      throw new TypeError("view and root are required");
    }
    const node = (selector) => root.querySelector(selector);
    const set = (selector, text) => {
      const target = node(selector);
      if (target) target.textContent = text;
    };
    const disconnected = view.mode === "disconnected";
    set("[data-hud=mode]", view.modeLabel);
    set("[data-hud=mode-detail]", view.modeDetail || "");
    set("[data-hud=status]", view.statusLine);
    set("[data-hud=progress]", disconnected && !view.hasState
      ? "Route progress unavailable"
      : "Route " + view.progressPercent + "% — " + view.district);
    set("[data-hud=phase]", disconnected && !view.hasState
      ? "No authoritative phase"
      : "Turn " + view.turn + " · " + view.phase + (view.paused ? " · paused" : ""));
    set("[data-hud=hazard]", view.hazard.id
      ? ("Hazard " + view.hazard.id + (view.hazard.warning
          ? " — warning " + view.hazard.secondsLeft + "s"
          : (view.hazard.countered ? " — cleared"
            : (view.hazard.active ? " — active" : " — resolved"))))
      : (disconnected ? "No authoritative hazard" : "No committed hazard this turn"));
    set("[data-hud=preview]", view.preview);
    set("[data-hud=pool]", disconnected && !view.hasState ? "Hype unavailable" : "Hype " + view.pool);
    set("[data-hud=audience]", view.mode === "live"
      ? (view.audience.liveCounters + " of " + view.audience.liveEligible + " eligible accounts countered")
      : (disconnected
        ? "No audience data — not live"
        : "Fixture run — no live Twitch participation"));
    set("[data-hud=connection]", view.connectionNotice);
    const modeNode = node("[data-hud=mode]");
    if (modeNode && typeof modeNode.setAttribute === "function") {
      modeNode.setAttribute("data-mode", view.mode);
    }
    const badge = node("[data-hud=badge]");
    if (badge) {
      badge.textContent = view.badge;
      if (typeof badge.setAttribute === "function") {
        badge.setAttribute("data-mode", view.mode);
        badge.setAttribute("aria-label", "Presentation mode: " + view.modeLabel);
      }
    }
    const fill = node("[data-hud=progress-fill]");
    if (fill && fill.style) fill.style.width = (disconnected ? 0 : view.progressPercent) + "%";
    for (const button of view.controls.buttons) {
      const control = node("[data-control=" + button.action + "]");
      if (control) {
        control.disabled = button.disabled;
        if (typeof control.setAttribute === "function") {
          control.setAttribute("aria-label", button.label);
        }
      }
    }
    return view;
  }

  return {
    TURN_TICKS, PLANNING_TICKS, MODE_LABELS, MODE_BADGES, CONNECTION_LABELS,
    deriveView, disconnectedView, controlIntent, statusMessage, connectionNotice, renderHud,
  };
});
