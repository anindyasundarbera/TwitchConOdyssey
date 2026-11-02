const $ = (id) => document.getElementById(id);
const canvas = $("game");
const ctx = canvas.getContext("2d");

// Landmark waypoints along the San Diego route
const WAYPOINTS = [
  { id: "start", progress: 0.0, name: "Little Italy Arch", district: "LITTLE ITALY / NORTH EMBARCADERO" },
  { id: "twitch_booth", progress: 35.0, name: "Twitch Stage Booth", district: "EMBARCADERO WATERFRONT / MARINA" },
  { id: "codex_booth", progress: 60.0, name: "Codex Arena Booth", district: "GASLAMP QUARTER" },
  { id: "aws_booth", progress: 80.0, name: "AWS Cloud Waypoint", district: "SAN DIEGO CONVENTION CENTER" },
  { id: "fictional_main_stage", progress: 100.0, name: "Fictional Main Stage", district: "FICTIONAL MAIN STAGE" },
];

// Fixed star coordinates for clean, non-jittering night sky
const STARS = Array.from({ length: 65 }, (_, i) => ({
  x: ((i * 137.5) % 1000) / 1000,
  y: ((i * 89.3) % 400) / 1000,
  size: 1 + (i % 3) * 0.8,
  speed: 0.001 + (i % 5) * 0.0006,
}));

// Floating Simulated Twitch Chat Messages for In-World Stream Authenticity
const CHAT_STREAM = [
  { user: "neon_fox", badge: "MOD", color: "#00f0ff", text: "STEER LEFT!! ROADBLOCK AHEAD!" },
  { user: "bay_phantom", badge: "SUB", color: "#a8f276", text: "VOTE CLEAR_LANE CHAT!! 🚀" },
  { user: "pixel_pirate", badge: "VIP", color: "#ffb84d", text: "POGGERS! LOOK AT THAT SPEED!" },
  { user: "gaslamp_pro", badge: "SUB", color: "#ff007f", text: "TWITCHCON HYPE TRAIN LEVEL 5!" },
  { user: "convention_fan", badge: "VIEWER", color: "#b59aff", text: "MAIN STAGE IS IN SIGHT! 💜" },
  { user: "codex_coder", badge: "VIP", color: "#10a37f", text: "AI PATH VECTOR OPTIMIZED [OK]" },
  { user: "cloud_runner", badge: "SUB", color: "#ff9900", text: "AWS CLOUD LOW-LATENCY SYNC ⚡" },
  { user: "marina_surfer", badge: "VIEWER", color: "#00f0ff", text: "DELIVER THE BUILD FOR 50/50 HYPE!" },
];


// Collectible Hype Crystals / Bits along the route
const COLLECTIBLES = Array.from({ length: 18 }, (_, i) => ({
  progress: 8 + i * 5.2,
  lane: (i * 2 + 1) % 3, // alternate lanes
  collected: false,
}));

// Floating floating text notifications (e.g. "+LANE SHIFT", "WAYPOINT UNLOCKED")
const floatingPopups = [];

function addPopup(text, color = "#00f0ff", x = null, y = null) {
  floatingPopups.push({
    text,
    color,
    x: x ?? 0.5,
    y: y ?? 0.62,
    alpha: 1.0,
    vy: -0.0012,
  });
}

let state = null;
let view = null;
let frozen = null;
let bullet = false;
let audio = null;
let soundEnabled = false;
let beat = 0;
let started = false;
let lastGamepadSteerTime = 0;
let lastProgressSeen = 0;
let lastLaneSeen = 1;

// ============================================================================
// Reduced Motion Preference (presentation only; never affects authority)
// ============================================================================
const reducedMotionQuery = typeof window.matchMedia === "function"
  ? window.matchMedia("(prefers-reduced-motion: reduce)")
  : null;
let reducedMotion = Boolean(reducedMotionQuery && reducedMotionQuery.matches);
if (reducedMotionQuery) {
  const onMotionChange = (event) => { reducedMotion = Boolean(event.matches); };
  if (typeof reducedMotionQuery.addEventListener === "function") {
    reducedMotionQuery.addEventListener("change", onMotionChange);
  } else if (typeof reducedMotionQuery.addListener === "function") {
    reducedMotionQuery.addListener(onMotionChange);
  }
}

// ============================================================================
// Modal Focus Management (focus first control, trap Tab, restore on close)
// ============================================================================
const MODAL_IDS = ["modal-start", "modal-pause", "modal-help", "modal-terminal", "modal-disconnected"];
const FOCUSABLE_SELECTOR = [
  "button:not([disabled])",
  "[href]",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");
const openModals = new Map();

function modalElements() {
  return MODAL_IDS.map((id) => $(id)).filter(Boolean);
}

function isModalVisible(modal) {
  return Boolean(modal) && !modal.hidden;
}

function topModal() {
  const visible = modalElements().filter(isModalVisible);
  return visible.length ? visible[visible.length - 1] : null;
}

function anyModalOpen() {
  return topModal() !== null;
}

function focusableIn(container) {
  return Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR))
    .filter((el) => !el.hidden && el.getClientRects().length > 0);
}

function isRestorable(el) {
  return Boolean(el) && el !== document.body && el.isConnected
    && typeof el.focus === "function" && !el.disabled && !el.hidden
    && el.getClientRects().length > 0 && !el.closest("[inert]")
    && !el.closest(".game-modal[hidden]");
}

function syncBackgroundInert() {
  const hudLayer = $("hud-layer");
  if (hudLayer) hudLayer.inert = anyModalOpen();
}

function focusFirstControl(modal) {
  const controls = focusableIn(modal);
  if (controls.length) {
    controls[0].focus();
  } else {
    if (!modal.hasAttribute("tabindex")) modal.setAttribute("tabindex", "-1");
    modal.focus();
  }
}

function syncModalFocus() {
  let closedRestoreTarget = null;
  for (const modal of modalElements()) {
    const visible = isModalVisible(modal);
    if (visible && !openModals.has(modal.id)) {
      openModals.set(modal.id, document.activeElement);
    } else if (!visible && openModals.has(modal.id)) {
      const previous = openModals.get(modal.id);
      openModals.delete(modal.id);
      if (modal.contains(document.activeElement) || document.activeElement === document.body || !document.activeElement) {
        closedRestoreTarget = previous;
      }
    }
  }
  syncBackgroundInert();
  const top = topModal();
  if (top) {
    if (!top.contains(document.activeElement)) {
      if (closedRestoreTarget && top.contains(closedRestoreTarget) && isRestorable(closedRestoreTarget)) {
        closedRestoreTarget.focus();
      } else {
        focusFirstControl(top);
      }
    }
  } else if (closedRestoreTarget) {
    if (isRestorable(closedRestoreTarget)) {
      closedRestoreTarget.focus();
    } else if (document.activeElement && document.activeElement !== document.body
      && document.activeElement.closest && document.activeElement.closest(".game-modal")) {
      document.activeElement.blur();
    }
  }
}

function trapTab(event) {
  const modal = topModal();
  if (!modal) return;
  const controls = focusableIn(modal);
  if (!controls.length) {
    event.preventDefault();
    focusFirstControl(modal);
    return;
  }
  const first = controls[0];
  const last = controls[controls.length - 1];
  const active = document.activeElement;
  if (!modal.contains(active)) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
  } else if (event.shiftKey && active === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && active === last) {
    event.preventDefault();
    first.focus();
  }
}

const modalObserver = new MutationObserver(syncModalFocus);
for (const modal of modalElements()) {
  modalObserver.observe(modal, { attributes: true, attributeFilter: ["hidden"] });
}
syncModalFocus();

// ============================================================================
// Canvas Sizing & Fullscreen Handling
// ============================================================================
function resizeCanvas() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const rect = canvas.getBoundingClientRect();
  const width = rect.width || window.innerWidth;
  const height = rect.height || window.innerHeight;
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
  }
}
window.addEventListener("resize", resizeCanvas);
window.addEventListener("orientationchange", resizeCanvas);

async function toggleFullscreen() {
  try {
    if (!document.fullscreenElement) {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        await document.exitFullscreen();
      }
    }
  } catch (err) {
    console.warn("Fullscreen toggle unavailable:", err.message);
  }
}

document.addEventListener("fullscreenchange", () => {
  const isFull = Boolean(document.fullscreenElement);
  $("btn-fullscreen").textContent = isFull ? "⛶ Exit" : "⛶ Fullscreen";
  resizeCanvas();
});

// ============================================================================
// Disconnected & Feedback State
// ============================================================================
function announceDisconnected(message) {
  state = null;
  view = null;
  $("district").textContent = "No authoritative state";
  $("tick").textContent = "DISCONNECTED / CONTROLS LOCKED";
  $("pause").disabled = true;
  $("restart").hidden = true;
  for (const dir of ["left", "right"]) {
    const btn = document.querySelector(`[data-control="${dir}"]`);
    if (btn) btn.disabled = true;
  }
  window.dispatchEvent(new CustomEvent("odyssey:disconnected", {
    detail: { reason: message || "Authoritative state unavailable." },
  }));
  $("feedback").textContent = "Controls locked — no authoritative state. Live status is not inferred.";
  if (started && $("modal-disconnected")) {
    $("modal-disconnected").hidden = false;
    $("disconnect-detail").textContent = message || "No authoritative state envelope is arriving. Live status is not inferred.";
  }
}

// ============================================================================
// SYNTHWAVE CYBERPUNK ARCADE RUNNER GRAPHICS ENGINE
// ============================================================================
function draw(now) {
  const current = bullet ? frozen : state;
  resizeCanvas();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = canvas.width / dpr;
  const h = canvas.height / dpr;

  ctx.save();
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#050811";
  ctx.fillRect(0, 0, w, h);

  const horizonY = h * 0.44;
  const speedProgress = current ? current.movement.progress : 0;
  const isDelivered = current && current.status === "delivered";
  const inSlowdown = current && (current.movement.slowdown_ticks_remaining || 0) > 0;

  // Waypoint reached detector
  for (const wp of WAYPOINTS) {
    if (speedProgress >= wp.progress && lastProgressSeen < wp.progress && wp.progress > 0) {
      addPopup(`★ UNLOCKED: ${wp.name}!`, "#a8f276", 0.5, 0.48);
      if (soundEnabled && audio) playChime();
    }
  }
  lastProgressSeen = speedProgress;

  // --------------------------------------------------------------------------
  // 1. SKY & SYNTHWAVE SUNSET
  // --------------------------------------------------------------------------
  const skyGrad = ctx.createLinearGradient(0, 0, 0, horizonY);
  skyGrad.addColorStop(0.00, "#05030e");
  skyGrad.addColorStop(0.30, "#190729");
  skyGrad.addColorStop(0.60, "#4a0e3d");
  skyGrad.addColorStop(0.82, "#8e1e4c");
  skyGrad.addColorStop(0.95, "#d6454a");
  skyGrad.addColorStop(1.00, "#ff9a3c");
  ctx.fillStyle = skyGrad;
  ctx.fillRect(0, 0, w, horizonY);

  // Twinkling Night Stars
  ctx.fillStyle = "#ffffff";
  for (let i = 0; i < STARS.length; i++) {
    const st = STARS[i];
    const sx = st.x * w;
    const sy = st.y * (horizonY * 0.72);
    const alpha = reducedMotion ? 0.7 : 0.35 + Math.sin(now * st.speed + i) * 0.4;
    ctx.globalAlpha = Math.max(0.1, alpha);
    ctx.fillRect(sx, sy, st.size, st.size);
  }
  ctx.globalAlpha = 1.0;

  // Overhead Cyber Sponsor Zeppelin / Blimp
  const blimpX = ((now * 0.015) % (w + 240)) - 120;
  const blimpY = horizonY * 0.22;
  ctx.save();
  ctx.translate(blimpX, blimpY);
  // Blimp Hull
  ctx.fillStyle = "#120c22";
  ctx.strokeStyle = "#00f0ff";
  ctx.lineWidth = 1.5;
  ctx.shadowColor = "rgba(0, 240, 255, 0.5)";
  ctx.shadowBlur = 8;
  ctx.beginPath();
  ctx.ellipse(0, 0, 52, 16, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  // Blimp Gondola & Searchlight
  ctx.fillStyle = "#1e1438";
  ctx.fillRect(-16, 12, 32, 6);
  ctx.strokeStyle = "rgba(0, 240, 255, 0.18)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(0, 18);
  ctx.lineTo(-40, horizonY);
  ctx.lineTo(40, horizonY);
  ctx.closePath();
  ctx.fillStyle = "rgba(0, 240, 255, 0.04)";
  ctx.fill();
  // Blimp Scrolling Neon Text
  ctx.fillStyle = "#a8f276";
  ctx.font = "800 8px monospace";
  ctx.textAlign = "center";
  ctx.fillText("TWITCHCON ODYSSEY ✦ AWS & CODEX", 0, 3);
  ctx.restore();

  // Synthwave Sun on the Horizon
  const sunX = w * 0.52;
  const sunY = horizonY - 2;
  const sunR = Math.min(w * 0.15, 82);

  const sunGrad = ctx.createRadialGradient(sunX, sunY, sunR * 0.05, sunX, sunY, sunR);
  sunGrad.addColorStop(0, "#fffbe0");
  sunGrad.addColorStop(0.35, "#ffb84d");
  sunGrad.addColorStop(0.72, "#ff1f7d");
  sunGrad.addColorStop(1, "rgba(255, 0, 127, 0)");
  ctx.fillStyle = sunGrad;
  ctx.beginPath();
  ctx.arc(sunX, sunY, sunR, 0, Math.PI * 2);
  ctx.fill();

  // Horizontal blind cutouts across the lower sun
  ctx.fillStyle = "#05030e";
  const numStripes = 7;
  for (let s = 1; s <= numStripes; s++) {
    const stripeY = sunY + (s / (numStripes + 1)) * (sunR * 0.88);
    const stripeH = 1.4 + s * 0.75;
    ctx.fillRect(sunX - sunR * 1.15, stripeY, sunR * 2.3, stripeH);
  }

  // --------------------------------------------------------------------------
  // 2. SAN DIEGO SKYLINE & WATER REFLECTION
  // --------------------------------------------------------------------------
  // Coronado Bay Hills
  ctx.fillStyle = "#0e061c";
  ctx.beginPath();
  ctx.moveTo(0, horizonY);
  ctx.quadraticCurveTo(w * 0.25, horizonY - 18, w * 0.55, horizonY);
  ctx.lineTo(w, horizonY);
  ctx.lineTo(0, horizonY);
  ctx.fill();

  // Coronado Bridge Silhouette & Light stays
  ctx.fillStyle = "#140b26";
  ctx.beginPath();
  ctx.moveTo(0, horizonY);
  ctx.bezierCurveTo(w * 0.15, horizonY - 28, w * 0.35, horizonY - 14, w * 0.48, horizonY);
  ctx.lineTo(w * 0.48, horizonY + 2);
  ctx.lineTo(0, horizonY + 2);
  ctx.fill();

  // Bridge Spires & Cable Stays
  ctx.strokeStyle = "rgba(0, 240, 255, 0.4)";
  ctx.lineWidth = 1;
  for (const tx of [w * 0.18, w * 0.28]) {
    ctx.beginPath();
    ctx.moveTo(tx, horizonY + 2);
    ctx.lineTo(tx, horizonY - 34);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(tx, horizonY - 32);
    ctx.lineTo(tx - 26, horizonY - 12);
    ctx.moveTo(tx, horizonY - 32);
    ctx.lineTo(tx + 26, horizonY - 12);
    ctx.stroke();
    ctx.fillStyle = "#ff3366";
    ctx.fillRect(tx - 1.5, horizonY - 36, 3, 3);
  }

  // Midground Downtown Skyline
  const numBuildings = 24;
  const bWidth = w / numBuildings;
  for (let i = 0; i < numBuildings; i++) {
    const bx = i * bWidth;
    const bHeight = 22 + ((i * 47) % 62);
    const by = horizonY - bHeight;

    ctx.fillStyle = i % 2 === 0 ? "#110b21" : "#170f2d";
    ctx.fillRect(bx, by, bWidth - 2, bHeight);

    // Glowing Neon Windows
    ctx.fillStyle = (i % 3 === 0) ? "#00f0ff" : ((i % 3 === 1) ? "#ffb84d" : "#ff2a85");
    ctx.globalAlpha = 0.65;
    for (let wy = by + 6; wy < horizonY - 6; wy += 8) {
      if ((i + wy) % 5 !== 0) {
        ctx.fillRect(bx + 3, wy, Math.max(2, bWidth * 0.24), 3);
      }
    }
    ctx.globalAlpha = 1.0;

    // San Diego Convention Center Sail Pavilions near center-right
    if (i === 14 || i === 15) {
      ctx.save();
      const sailPeakX = bx + bWidth * 0.5;
      const sailPeakY = by - 36;
      ctx.beginPath();
      ctx.moveTo(bx - 4, horizonY);
      ctx.quadraticCurveTo(bx + 2, sailPeakY, sailPeakX, sailPeakY);
      ctx.quadraticCurveTo(bx + bWidth - 2, sailPeakY, bx + bWidth + 4, horizonY);
      ctx.closePath();

      const sailGrad = ctx.createLinearGradient(0, sailPeakY, 0, horizonY);
      sailGrad.addColorStop(0, "rgba(240, 248, 255, 0.9)");
      sailGrad.addColorStop(0.5, "rgba(0, 240, 255, 0.5)");
      sailGrad.addColorStop(1, "rgba(181, 154, 255, 0.15)");
      ctx.fillStyle = sailGrad;
      ctx.fill();

      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(sailPeakX, sailPeakY);
      ctx.lineTo(sailPeakX, horizonY);
      ctx.stroke();
      ctx.restore();
    }
  }

  // San Diego Bay Water Sheen
  const waterTopY = horizonY;
  const waterBottomY = h * 0.49;
  const waterGrad = ctx.createLinearGradient(0, waterTopY, 0, waterBottomY);
  waterGrad.addColorStop(0.0, "#0c1522");
  waterGrad.addColorStop(0.4, "#09101a");
  waterGrad.addColorStop(1.0, "#060910");
  ctx.fillStyle = waterGrad;
  ctx.fillRect(0, waterTopY, w, waterBottomY - waterTopY);

  // Water Specular Sunset Ripple Reflection
  ctx.strokeStyle = "rgba(255, 120, 160, 0.28)";
  ctx.lineWidth = 1.5;
  const rippleOffset = reducedMotion ? 0 : (now * 0.04) % 20;
  for (let r = 0; r < 5; r++) {
    const ry = waterTopY + 4 + r * 6 + ((rippleOffset + r * 3) % 8);
    if (ry < waterBottomY) {
      ctx.beginPath();
      ctx.moveTo(sunX - 55 - r * 16, ry);
      ctx.lineTo(sunX + 55 + r * 16, ry);
      ctx.stroke();
    }
  }

  // Bay Diegetic Label
  ctx.fillStyle = "#5d879e";
  ctx.font = "800 10px monospace";
  ctx.textAlign = "center";
  ctx.fillText("S A N  D I E G O  B A Y", w * 0.68, waterTopY + 13);

  // --------------------------------------------------------------------------
  // 3. 3D HIGHWAY & PERSPECTIVE RACING ENGINE
  // --------------------------------------------------------------------------
  const roadTopY = waterBottomY;
  const roadBottomY = h;
  const horizonX = w * 0.5;
  const topRoadWidth = Math.min(w * 0.36, 340);
  const bottomRoadWidth = Math.min(w * 0.96, 1060);

  const roadTopLeft = horizonX - topRoadWidth * 0.5;
  const roadTopRight = horizonX + topRoadWidth * 0.5;
  const roadBottomLeft = horizonX - bottomRoadWidth * 0.5;
  const roadBottomRight = horizonX + bottomRoadWidth * 0.5;

  // Road Asphalt Surface (Deep space black with reflective specular center)
  const roadGrad = ctx.createLinearGradient(0, roadTopY, 0, roadBottomY);
  roadGrad.addColorStop(0, "#070b14");
  roadGrad.addColorStop(0.6, "#090f1a");
  roadGrad.addColorStop(1, "#0c1322");
  ctx.fillStyle = roadGrad;
  ctx.beginPath();
  ctx.moveTo(roadTopLeft, roadTopY);
  ctx.lineTo(roadTopRight, roadTopY);
  ctx.lineTo(roadBottomRight, roadBottomY);
  ctx.lineTo(roadBottomLeft, roadBottomY);
  ctx.closePath();
  ctx.fill();

  // Subtle Asphalt Speed Texture
  const scrollPhase = (speedProgress * 120 + (reducedMotion ? 0 : now * 0.16)) % 60;
  ctx.strokeStyle = "rgba(0, 240, 255, 0.04)";
  ctx.lineWidth = 1;
  for (let gy = roadTopY; gy < roadBottomY; gy += 16) {
    const animatedGy = gy + (scrollPhase * ((gy - roadTopY) / (roadBottomY - roadTopY)));
    if (animatedGy <= roadBottomY) {
      const frac = (animatedGy - roadTopY) / (roadBottomY - roadTopY);
      const span = topRoadWidth + (bottomRoadWidth - topRoadWidth) * frac;
      ctx.beginPath();
      ctx.moveTo(horizonX - span * 0.5, animatedGy);
      ctx.lineTo(horizonX + span * 0.5, animatedGy);
      ctx.stroke();
    }
  }

  // 3D Alternating Racing Curbs (OutRun/F-Zero style)
  const curbSlices = 24;
  const curbScroll = (speedProgress * 80 + (reducedMotion ? 0 : now * 0.14)) % 36;

  for (let s = 0; s < curbSlices; s++) {
    const t0 = Math.pow(s / curbSlices, 1.8);
    const t1 = Math.pow((s + 1) / curbSlices, 1.8);

    const y0 = roadTopY + (roadBottomY - roadTopY) * t0;
    const y1 = roadTopY + (roadBottomY - roadTopY) * t1;

    const rWidth0 = topRoadWidth + (bottomRoadWidth - topRoadWidth) * t0;
    const rWidth1 = topRoadWidth + (bottomRoadWidth - topRoadWidth) * t1;

    const curbWidth0 = 8 + 28 * t0;
    const curbWidth1 = 8 + 28 * t1;

    // Alternate Cyan (#00f0ff) and Magenta (#ff007f)
    const isSegmentA = ((s + Math.floor(curbScroll / 18)) % 2 === 0);
    const curbColor = isSegmentA ? "#00f0ff" : "#ff007f";
    const curbGlowColor = isSegmentA ? "rgba(0, 240, 255, 0.4)" : "rgba(255, 0, 127, 0.4)";

    ctx.fillStyle = curbColor;
    ctx.shadowColor = curbGlowColor;
    ctx.shadowBlur = 6 * t1;

    // Left Curb Segment
    const lx0 = horizonX - rWidth0 * 0.5;
    const lx1 = horizonX - rWidth1 * 0.5;
    ctx.beginPath();
    ctx.moveTo(lx0, y0);
    ctx.lineTo(lx0 - curbWidth0, y0);
    ctx.lineTo(lx1 - curbWidth1, y1);
    ctx.lineTo(lx1, y1);
    ctx.closePath();
    ctx.fill();

    // Right Curb Segment
    const rx0 = horizonX + rWidth0 * 0.5;
    const rx1 = horizonX + rWidth1 * 0.5;
    ctx.beginPath();
    ctx.moveTo(rx0, y0);
    ctx.lineTo(rx0 + curbWidth0, y0);
    ctx.lineTo(rx1 + curbWidth1, y1);
    ctx.lineTo(rx1, y1);
    ctx.closePath();
    ctx.fill();
  }
  ctx.shadowBlur = 0;

  // --------------------------------------------------------------------------
  // 4. ROADSIDE 3D PALM TREES & NEON STREETLAMPS
  // --------------------------------------------------------------------------
  const treeCount = 9;
  for (let i = 0; i < treeCount; i++) {
    const treeFrac = ((i / treeCount) + ((speedProgress * 0.05 + now * 0.0001) % 1)) % 1;
    const t = Math.pow(treeFrac, 2.0);
    if (t < 0.04 || t > 0.96) continue;

    const ty = roadTopY + (roadBottomY - roadTopY) * t;
    const rWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * t;
    const treeScale = 0.3 + t * 1.5;

    // Left Palm Tree
    const treeLeftX = horizonX - rWidth * 0.5 - 28 * treeScale;
    drawPalmTree(ctx, treeLeftX, ty, treeScale, -1);

    // Right Palm Tree
    const treeRightX = horizonX + rWidth * 0.5 + 28 * treeScale;
    drawPalmTree(ctx, treeRightX, ty, treeScale, 1);
  }

  // --------------------------------------------------------------------------
  // 5. 3 DISCRETE LANES & ROAD SURFACE SPEED CHEVRONS (>>>)
  // --------------------------------------------------------------------------
  const forwardScroll = (speedProgress * 80 + (reducedMotion ? 0 : now * 0.14)) % 40;
  ctx.lineWidth = 3;
  ctx.setLineDash([18, 20]);
  ctx.lineDashOffset = -forwardScroll;
  ctx.strokeStyle = "#a8f276";
  ctx.shadowColor = "rgba(168, 242, 118, 0.6)";
  ctx.shadowBlur = 8;

  // Divider 1 (between Lane 0 and 1)
  const d1TopX = roadTopLeft + topRoadWidth * (1 / 3);
  const d1BottomX = roadBottomLeft + bottomRoadWidth * (1 / 3);
  ctx.beginPath();
  ctx.moveTo(d1TopX, roadTopY);
  ctx.lineTo(d1BottomX, roadBottomY);
  ctx.stroke();

  // Divider 2 (between Lane 1 and 2)
  const d2TopX = roadTopLeft + topRoadWidth * (2 / 3);
  const d2BottomX = roadBottomLeft + bottomRoadWidth * (2 / 3);
  ctx.beginPath();
  ctx.moveTo(d2TopX, roadTopY);
  ctx.lineTo(d2BottomX, roadBottomY);
  ctx.stroke();

  ctx.setLineDash([]);
  ctx.shadowBlur = 0;

  // Animated Speed Chevrons on Road Surface (>>>)
  ctx.strokeStyle = "rgba(0, 240, 255, 0.18)";
  ctx.lineWidth = 2;
  for (let c = 0; c < 8; c++) {
    const cFrac = ((c / 8) + ((speedProgress * 0.08 + now * 0.00015) % 1)) % 1;
    const ct = Math.pow(cFrac, 1.8);
    if (ct < 0.1 || ct > 0.92) continue;
    const cy = roadTopY + (roadBottomY - roadTopY) * ct;
    const crWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * ct;
    const cLaneWidth = crWidth / 3;
    const cSpan = 14 * (0.4 + ct);

    for (let l = 0; l < 3; l++) {
      const cx = (horizonX - crWidth * 0.5) + cLaneWidth * (l + 0.5);
      ctx.beginPath();
      ctx.moveTo(cx - cSpan, cy + cSpan * 0.6);
      ctx.lineTo(cx, cy);
      ctx.lineTo(cx + cSpan, cy + cSpan * 0.6);
      ctx.stroke();
    }
  }

  // Diegetic Lane Hologram Labels on Road
  ctx.font = "800 11px monospace";
  ctx.fillStyle = "rgba(0, 240, 255, 0.4)";
  ctx.textAlign = "center";
  const laneY = roadBottomY - 22;
  const lane0Center = roadBottomLeft + (bottomRoadWidth / 6);
  const lane1Center = roadBottomLeft + (bottomRoadWidth / 2);
  const lane2Center = roadBottomLeft + (bottomRoadWidth * 5 / 6);
  ctx.fillText("LANE 0 · MARINA", lane0Center, laneY);
  ctx.fillText("LANE 1 · BOULEVARD", lane1Center, laneY);
  ctx.fillText("LANE 2 · GASLAMP", lane2Center, laneY);

  // --------------------------------------------------------------------------
  // 6. COLLECTIBLE TWITCH BITS / HYPE CRYSTALS
  // --------------------------------------------------------------------------
  for (const item of COLLECTIBLES) {
    if (item.progress >= speedProgress - 5 && item.progress <= speedProgress + 25) {
      const relDist = item.progress - speedProgress;
      const ct = Math.max(0.05, Math.min(0.95, 0.85 - (relDist / 25) * 0.8));
      const cy = roadTopY + (roadBottomY - roadTopY) * ct;
      const crWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * ct;
      const cLaneWidth = crWidth / 3;
      const cx = (horizonX - crWidth * 0.5) + cLaneWidth * (item.lane + 0.5);
      const cSize = (10 + 16 * ct);

      // Draw 3D Rotating Diamond Crystal (Twitch Bit)
      ctx.save();
      ctx.translate(cx, cy);
      const rot = now * 0.003 + item.progress;
      ctx.rotate(rot);

      ctx.fillStyle = item.lane === 1 ? "#a8f276" : "#b59aff";
      ctx.shadowColor = item.lane === 1 ? "rgba(168, 242, 118, 0.8)" : "rgba(181, 154, 255, 0.8)";
      ctx.shadowBlur = 12 * ct;

      ctx.beginPath();
      ctx.moveTo(0, -cSize);
      ctx.lineTo(cSize * 0.7, 0);
      ctx.lineTo(0, cSize);
      ctx.lineTo(-cSize * 0.7, 0);
      ctx.closePath();
      ctx.fill();

      // Inner facet reflection
      ctx.fillStyle = "#ffffff";
      ctx.globalAlpha = 0.6;
      ctx.beginPath();
      ctx.moveTo(0, -cSize * 0.8);
      ctx.lineTo(cSize * 0.4, 0);
      ctx.lineTo(0, cSize * 0.8);
      ctx.closePath();
      ctx.fill();
      ctx.restore();
    }
  }

  // --------------------------------------------------------------------------
  // 7. ROADSIDE SPONSOR PAVILIONS & MEGA-BOOTHS
  // --------------------------------------------------------------------------
  // A. Twitch Stage Booth (Progress 35.0% - Embarcadero Marina)
  if (speedProgress >= 18 && speedProgress <= 52) {
    const rel = 35.0 - speedProgress;
    const t = Math.max(0.05, Math.min(0.96, 0.82 - (rel / 18) * 0.5));
    const py = roadTopY + (roadBottomY - roadTopY) * t;
    const prWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * t;
    const px = horizonX - prWidth * 0.5 - (60 + 120 * t);
    drawTwitchBooth(ctx, px, py, 0.4 + t * 1.1, now);
  }

  // B. OpenAI Codex Arena Booth (Progress 60.0% - Gaslamp Quarter)
  if (speedProgress >= 42 && speedProgress <= 78) {
    const rel = 60.0 - speedProgress;
    const t = Math.max(0.05, Math.min(0.96, 0.82 - (rel / 18) * 0.5));
    const py = roadTopY + (roadBottomY - roadTopY) * t;
    const prWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * t;
    const px = horizonX + prWidth * 0.5 + (60 + 120 * t);
    drawCodexBooth(ctx, px, py, 0.4 + t * 1.1, now);
  }

  // C. AWS Cloud Waypoint (Progress 80.0% - San Diego Convention Center)
  if (speedProgress >= 65 && speedProgress <= 95) {
    const rel = 80.0 - speedProgress;
    const t = Math.max(0.05, Math.min(0.96, 0.82 - (rel / 18) * 0.5));
    const py = roadTopY + (roadBottomY - roadTopY) * t;
    const prWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * t;
    const px = horizonX - prWidth * 0.5 - (60 + 120 * t);
    drawAwsBooth(ctx, px, py, 0.4 + t * 1.1, now);
  }

  // D. Fictional Main Stage Climax Stadium (Progress 100.0%)
  if (speedProgress >= 82) {
    const rel = 100.0 - speedProgress;
    const t = Math.max(0.05, Math.min(0.98, 0.90 - (rel / 18) * 0.6));
    const py = roadTopY + (roadBottomY - roadTopY) * t;
    const prWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * t;
    drawMainStageFinish(ctx, horizonX, py, prWidth, 0.5 + t * 1.2, now, isDelivered);
  }

  // --------------------------------------------------------------------------
  // 8. WAYPOINT GANTRY ARCHES (Landmarks)
  // --------------------------------------------------------------------------
  for (const wp of WAYPOINTS) {
    if (wp.progress <= speedProgress + 16 && wp.progress >= speedProgress - 22) {
      const relDist = wp.progress - speedProgress;
      const normY = 0.85 - (relDist / 20) * 0.35;
      if (normY >= 0.45 && normY <= 0.96) {
        const t = (normY - 0.45) / 0.51;
        const gateY = roadTopY + (roadBottomY - roadTopY) * t;
        const gateRoadWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * t;
        const gLeft = horizonX - gateRoadWidth * 0.54;
        const gRight = horizonX + gateRoadWidth * 0.54;
        const archHeight = 34 + 36 * t;

        ctx.save();
        ctx.strokeStyle = wp.progress === 100 ? "#a8f276" : "#00f0ff";
        ctx.shadowColor = wp.progress === 100 ? "rgba(168, 242, 118, 0.8)" : "rgba(0, 240, 255, 0.8)";
        ctx.shadowBlur = 12;
        ctx.lineWidth = 3 * (1 + t * 0.8);

        // Columns & Overhead Beam
        ctx.beginPath();
        ctx.moveTo(gLeft, gateY);
        ctx.lineTo(gLeft, gateY - archHeight);
        ctx.lineTo(gRight, gateY - archHeight);
        ctx.lineTo(gRight, gateY);
        ctx.stroke();

        // Overhead Digital Banner Box
        ctx.fillStyle = "rgba(10, 16, 28, 0.92)";
        ctx.fillRect(gLeft + 4, gateY - archHeight, (gRight - gLeft) - 8, 22 * (1 + t * 0.5));
        ctx.strokeRect(gLeft + 4, gateY - archHeight, (gRight - gLeft) - 8, 22 * (1 + t * 0.5));

        // District Landmark Text
        ctx.fillStyle = "#ffffff";
        ctx.font = `800 ${Math.round(10 + t * 5)}px monospace`;
        ctx.textAlign = "center";
        ctx.fillText(`⚑ ${wp.district} [${Math.round(wp.progress)}%]`, horizonX, gateY - archHeight + 14 * (1 + t * 0.4));
        ctx.restore();
      }
    }
  }

  // --------------------------------------------------------------------------
  // 9. CENTER LANE HAZARD GATE (Lane 1 Roadblock)
  // --------------------------------------------------------------------------
  if (current && current.hazard) {
    const isWarning = Boolean(current.hazard.warning_active);
    const isActive = Boolean(current.hazard.obstacle_active);
    const isCountered = Boolean(current.hazard.hazard_countered);

    if (isWarning || isActive) {
      const hazardY = roadBottomY - (roadBottomY - roadTopY) * 0.38;
      const hRoadWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * 0.62;
      const hLeft = horizonX - hRoadWidth * 0.5;
      const hLaneWidth = hRoadWidth / 3;
      const hCenterX = hLeft + hLaneWidth * 1.5;

      ctx.save();
      const barrierWidth = hLaneWidth * 0.92;
      const barrierHeight = 36;
      const bLeft = hCenterX - barrierWidth * 0.5;
      const bRight = hCenterX + barrierWidth * 0.5;

      if (isCountered) {
        // Countered by Audience -> Glowing emerald green cleared portal!
        ctx.strokeStyle = "#a8f276";
        ctx.shadowColor = "#a8f276";
        ctx.shadowBlur = 18;
        ctx.lineWidth = 3;
        ctx.strokeRect(bLeft, hazardY - barrierHeight, barrierWidth, barrierHeight);

        ctx.fillStyle = "rgba(168, 242, 118, 0.22)";
        ctx.fillRect(bLeft, hazardY - barrierHeight, barrierWidth, barrierHeight);

        ctx.fillStyle = "#a8f276";
        ctx.font = "800 12px monospace";
        ctx.textAlign = "center";
        ctx.fillText("✔ CLEAR_LANE COUNTERED", hCenterX, hazardY - barrierHeight * 0.4);
      } else if (isActive) {
        // Active Roadblock -> Crimson/amber holographic laser grid!
        const pulse = reducedMotion ? 1 : Math.sin(now * 0.02) * 0.3 + 1;
        ctx.strokeStyle = "#ff3366";
        ctx.shadowColor = "#ff3366";
        ctx.shadowBlur = 24 * pulse;
        ctx.lineWidth = 4;
        ctx.strokeRect(bLeft, hazardY - barrierHeight, barrierWidth, barrierHeight);

        ctx.fillStyle = "rgba(255, 51, 102, 0.35)";
        ctx.fillRect(bLeft, hazardY - barrierHeight, barrierWidth, barrierHeight);

        // Laser horizontal cross-beams
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(bLeft, hazardY - barrierHeight * 0.7);
        ctx.lineTo(bRight, hazardY - barrierHeight * 0.7);
        ctx.moveTo(bLeft, hazardY - barrierHeight * 0.3);
        ctx.lineTo(bRight, hazardY - barrierHeight * 0.3);
        ctx.stroke();

        ctx.fillStyle = "#ffffff";
        ctx.font = "900 12px monospace";
        ctx.textAlign = "center";
        ctx.fillText("⚠ ROADBLOCK ACTIVE", hCenterX, hazardY - barrierHeight * 0.45);
      } else if (isWarning) {
        // Warning State -> Solar amber pulsing caution grid
        const flash = reducedMotion ? true : Math.sin(now * 0.015) > 0;
        ctx.strokeStyle = flash ? "#ffb84d" : "rgba(255, 184, 77, 0.4)";
        ctx.shadowColor = "#ffb84d";
        ctx.shadowBlur = 14;
        ctx.lineWidth = 3;
        ctx.strokeRect(bLeft, hazardY - barrierHeight, barrierWidth, barrierHeight);

        ctx.fillStyle = flash ? "rgba(255, 184, 77, 0.25)" : "rgba(255, 184, 77, 0.08)";
        ctx.fillRect(bLeft, hazardY - barrierHeight, barrierWidth, barrierHeight);

        ctx.fillStyle = "#ffb84d";
        ctx.font = "800 11px monospace";
        ctx.textAlign = "center";
        ctx.fillText("⚠ WARNING: ROADBLOCK COMING", hCenterX, hazardY - barrierHeight * 0.45);
      }
      ctx.restore();
    }
  }

  // --------------------------------------------------------------------------
  // 10. PLAYER COURIER CYBERPUNK RUNNER SPRITE
  // --------------------------------------------------------------------------
  if (current) {
    const latPos = current.avatar.lateral_pos; // 0.0 (left), 1.0 (center), 2.0 (right)
    const charY = roadBottomY - 105;
    const charRoadWidth = topRoadWidth + (bottomRoadWidth - topRoadWidth) * ((charY - roadTopY) / (roadBottomY - roadTopY));
    const charRoadLeft = horizonX - charRoadWidth * 0.5;
    const laneSpan = charRoadWidth / 3;
    const charX = charRoadLeft + laneSpan * 0.5 + latPos * laneSpan;

    const transitioning = (current.avatar.transition_remaining_ticks || 0) > 0;
    if (transitioning && current.avatar.lane !== lastLaneSeen) {
      addPopup(current.avatar.lane > lastLaneSeen ? "EVASION RIGHT ▶" : "◀ EVASION LEFT", "#00f0ff", charX / w, (charY - 50) / h);
      lastLaneSeen = current.avatar.lane;
    }

    ctx.save();
    ctx.translate(charX, charY);

    // Dynamic Lateral Banking & Tilt when changing lanes
    if (transitioning) {
      const tilt = current.avatar.lane > latPos ? 0.22 : -0.22;
      ctx.rotate(tilt);
    }

    // Ground Neon Underglow & Drop Shadow on wet pavement
    ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
    ctx.beginPath();
    ctx.ellipse(0, 26, 26, 8, 0, 0, Math.PI * 2);
    ctx.fill();

    // Neon Ground Glow
    const glowColor = inSlowdown ? "rgba(255, 184, 77, 0.4)" : "rgba(0, 240, 255, 0.35)";
    ctx.fillStyle = glowColor;
    ctx.beginPath();
    ctx.ellipse(0, 26, 34, 11, 0, 0, Math.PI * 2);
    ctx.fill();

    // Twin Thruster Blue Particle Flames (Hover Skates)
    const flameFlicker = reducedMotion ? 12 : 12 + Math.sin(now * 0.04) * 6;
    ctx.fillStyle = inSlowdown ? "#ffb84d" : "#00f0ff";
    ctx.shadowColor = inSlowdown ? "#ffb84d" : "#00f0ff";
    ctx.shadowBlur = 14;

    // Left Foot Thruster Jet
    ctx.beginPath();
    ctx.moveTo(-11, 22);
    ctx.lineTo(-7, 22);
    ctx.lineTo(-9, 22 + flameFlicker);
    ctx.closePath();
    ctx.fill();

    // Right Foot Thruster Jet
    ctx.beginPath();
    ctx.moveTo(7, 22);
    ctx.lineTo(11, 22);
    ctx.lineTo(9, 22 + flameFlicker);
    ctx.closePath();
    ctx.fill();
    ctx.shadowBlur = 0;

    // Runner Stride Animation
    const stride = bullet || reducedMotion ? 0 : Math.sin(now * 0.02) * 5;

    // Cyberpunk Runner Legs
    ctx.lineWidth = 5;
    ctx.strokeStyle = "#1b2838";
    ctx.beginPath();
    ctx.moveTo(-7, 6);
    ctx.lineTo(-9 + stride, 22);
    ctx.moveTo(7, 6);
    ctx.lineTo(9 - stride, 22);
    ctx.stroke();

    // Flowing Neon Scarf / Cyber Jacket Tails
    const scarfWave = bullet || reducedMotion ? 0 : Math.sin(now * 0.03) * 6;
    ctx.fillStyle = "#ff007f";
    ctx.beginPath();
    ctx.moveTo(-6, -6);
    ctx.quadraticCurveTo(-18, 4 + scarfWave, -26, 12 + scarfWave);
    ctx.lineTo(-24, 16 + scarfWave);
    ctx.quadraticCurveTo(-14, 8 + scarfWave, -4, -2);
    ctx.closePath();
    ctx.fill();

    // Athletic Cyber Jacket Torso
    ctx.fillStyle = inSlowdown ? "#ffb84d" : "#0c1826";
    ctx.fillRect(-12, -14, 24, 24);

    // Glowing Neon Circuit Spine / Accents
    ctx.strokeStyle = inSlowdown ? "#ff5c77" : "#00f0ff";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, -14);
    ctx.lineTo(0, 8);
    ctx.moveTo(-10, -4);
    ctx.lineTo(10, -4);
    ctx.stroke();

    // High-Tech DELIVERY CONTAINER (Backpack)
    const packColor = inSlowdown ? "#ffb84d" : (isDelivered ? "#ffd700" : "#a8f276");
    ctx.fillStyle = packColor;
    ctx.shadowColor = packColor;
    ctx.shadowBlur = 16;
    ctx.fillRect(-8, -10, 16, 16);
    ctx.shadowBlur = 0;

    // Backpack Inner Core
    ctx.fillStyle = "#060a12";
    ctx.fillRect(-5, -7, 10, 10);
    ctx.fillStyle = "#ffffff";
    ctx.font = "900 7px monospace";
    ctx.textAlign = "center";
    ctx.fillText("BUILD", 0, 0);

    // Helmet & Visor
    ctx.fillStyle = "#162334";
    ctx.beginPath();
    ctx.arc(0, -20, 8, 0, Math.PI * 2);
    ctx.fill();

    // Cyan Curved Digital Visor
    ctx.fillStyle = "#00f0ff";
    ctx.shadowColor = "#00f0ff";
    ctx.shadowBlur = 8;
    ctx.fillRect(-6, -23, 12, 4);
    ctx.shadowBlur = 0;

    // Slowdown Spark Aura (if impacted)
    if (inSlowdown) {
      ctx.strokeStyle = "#ffb84d";
      ctx.shadowColor = "#ffb84d";
      ctx.shadowBlur = 18;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(0, 0, 32 + (reducedMotion ? 0 : Math.sin(now * 0.03) * 4), 0, Math.PI * 2);
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // Player Status Tag
    ctx.fillStyle = "#ffffff";
    ctx.font = "800 10px monospace";
    ctx.textAlign = "center";
    ctx.fillText("COURIER", 0, -32);

    ctx.restore();
  }

  // --------------------------------------------------------------------------
  // 11. IN-WORLD SIMULATED TWITCH CHAT STREAM
  // --------------------------------------------------------------------------
  drawTwitchChatStream(ctx, w, h, now);

  // --------------------------------------------------------------------------
  // 12. FLOATING TEXT POPUPS & SPEED STREAKS
  // --------------------------------------------------------------------------
  drawFloatingPopups(ctx, w, h);

  // Speed Wind Particles along screen margins
  if (!reducedMotion && speedProgress > 0) {
    ctx.strokeStyle = "rgba(0, 240, 255, 0.25)";
    ctx.lineWidth = 1.5;
    for (let p = 0; p < 8; p++) {
      const px = (p % 2 === 0) ? (p * 24 + 10) : (w - p * 24 - 10);
      const py = (now * 0.6 + p * 130) % h;
      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(px + ((p % 2 === 0) ? -8 : 8), py + 45);
      ctx.stroke();
    }
  }

  ctx.restore();
  requestAnimationFrame(draw);
}

// ============================================================================
// Procedural Art Generators for Sponsor Pavilions & City Elements
// ============================================================================
function drawPalmTree(ctx, x, y, scale, dir) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);

  // Palm Trunk (Deep cyber obsidian with subtle curve)
  ctx.strokeStyle = "#10091d";
  ctx.lineWidth = 7;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.quadraticCurveTo(dir * 12, -28, dir * 18, -62);
  ctx.stroke();

  // Glowing Neon Fronds (Radiating umbrella arch in Cyan, Magenta, Mint)
  const colors = ["#00f0ff", "#ff007f", "#a8f276", "#00f0ff", "#ff007f"];
  const angles = [-1.1, -0.65, -0.2, 0.25, 0.7, 1.15];
  const crownX = dir * 18;
  const crownY = -62;

  for (let a = 0; a < angles.length; a++) {
    const angle = angles[a];
    const frondColor = colors[a % colors.length];
    ctx.strokeStyle = frondColor;
    ctx.shadowColor = frondColor;
    ctx.shadowBlur = 8;
    ctx.lineWidth = 2.4;

    ctx.beginPath();
    ctx.moveTo(crownX, crownY);
    const endX = crownX + Math.cos(angle) * 32;
    const endY = crownY + Math.sin(angle) * 18 + Math.abs(Math.cos(angle)) * 10;
    ctx.quadraticCurveTo(crownX + Math.cos(angle) * 20, crownY - 8, endX, endY);
    ctx.stroke();
  }
  ctx.restore();
}

function drawTwitchBooth(ctx, x, y, scale, now) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);

  // Stadium Stage Base & Trusses
  ctx.fillStyle = "#120924";
  ctx.strokeStyle = "#9146ff";
  ctx.lineWidth = 3;
  ctx.shadowColor = "rgba(145, 70, 255, 0.7)";
  ctx.shadowBlur = 14;

  ctx.fillRect(-60, -90, 120, 90);
  ctx.strokeRect(-60, -90, 120, 90);

  // Animated LED Audio Visualizer Bars
  ctx.fillStyle = "#bf94ff";
  const numBars = 10;
  for (let b = 0; b < numBars; b++) {
    const barH = 10 + Math.abs(Math.sin(now * 0.005 + b * 0.8)) * 36;
    ctx.fillRect(-50 + b * 10, -14 - barH, 7, barH);
  }

  // Iconic Twitch Glitch Logo
  ctx.fillStyle = "#ffffff";
  ctx.beginPath();
  ctx.moveTo(-18, -80);
  ctx.lineTo(18, -80);
  ctx.lineTo(18, -52);
  ctx.lineTo(8, -52);
  ctx.lineTo(2, -44);
  ctx.lineTo(-4, -52);
  ctx.lineTo(-18, -52);
  ctx.closePath();
  ctx.fill();

  // Glitch Logo Eyes
  ctx.fillStyle = "#9146ff";
  ctx.fillRect(-10, -72, 4, 10);
  ctx.fillRect(6, -72, 4, 10);

  // Stage Banner
  ctx.fillStyle = "#ffffff";
  ctx.font = "900 9px monospace";
  ctx.textAlign = "center";
  ctx.fillText("TWITCH STAGE BOOTH", 0, -8);

  ctx.restore();
}

function drawCodexBooth(ctx, x, y, scale, now) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);

  // Cyber AI Research Dome
  ctx.fillStyle = "#081c19";
  ctx.strokeStyle = "#10a37f";
  ctx.lineWidth = 3;
  ctx.shadowColor = "rgba(16, 163, 127, 0.8)";
  ctx.shadowBlur = 14;

  ctx.beginPath();
  ctx.arc(0, 0, 60, Math.PI, 0);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Matrix Digital Stream Waterfall
  ctx.fillStyle = "#a8f276";
  ctx.font = "700 8px monospace";
  ctx.textAlign = "center";
  for (let col = -4; col <= 4; col++) {
    const char = ((col + Math.floor(now * 0.01)) % 2 === 0) ? "1" : "0";
    ctx.fillText(char, col * 12, -24 + (col % 3) * 6);
  }

  // 3D Rotating Neural Nexus Cube
  const cubeRot = now * 0.002;
  ctx.strokeStyle = "#00f0ff";
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.strokeRect(-16, -72, 32, 32);
  ctx.strokeRect(-12 + Math.cos(cubeRot) * 4, -68 + Math.sin(cubeRot) * 4, 24, 24);

  // Billboard Sign
  ctx.fillStyle = "#ffffff";
  ctx.font = "900 9px monospace";
  ctx.fillText("OPENAI CODEX ARENA", 0, -4);
  ctx.fillStyle = "#a8f276";
  ctx.font = "800 6px monospace";
  ctx.fillText("SESSION 01a1955f", 0, 6);

  ctx.restore();
}

function drawAwsBooth(ctx, x, y, scale, now) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);

  // AWS Cloud Server Monolith Towers
  ctx.fillStyle = "#182230";
  ctx.strokeStyle = "#ff9900";
  ctx.lineWidth = 3;
  ctx.shadowColor = "rgba(255, 153, 0, 0.8)";
  ctx.shadowBlur = 14;

  ctx.fillRect(-55, -95, 110, 95);
  ctx.strokeRect(-55, -95, 110, 95);

  // Server Blade LED Racks
  ctx.fillStyle = "#ffb84d";
  for (let r = 0; r < 5; r++) {
    const rx = -44;
    const ry = -85 + r * 16;
    ctx.fillRect(rx, ry, 88, 10);
    // Glowing blinking port lights
    ctx.fillStyle = ((r + Math.floor(now * 0.008)) % 2 === 0) ? "#a8f276" : "#ff3366";
    ctx.fillRect(rx + 4, ry + 3, 4, 4);
    ctx.fillRect(rx + 12, ry + 3, 4, 4);
    ctx.fillStyle = "#ffb84d";
  }

  // Holographic Cloud Icon
  ctx.fillStyle = "rgba(0, 240, 255, 0.35)";
  ctx.strokeStyle = "#00f0ff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(-8, -112, 12, 0, Math.PI * 2);
  ctx.arc(8, -112, 14, 0, Math.PI * 2);
  ctx.arc(0, -118, 16, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();

  // Billboard Sign
  ctx.fillStyle = "#ffffff";
  ctx.font = "900 9px monospace";
  ctx.textAlign = "center";
  ctx.fillText("AWS CLOUD WAYPOINT", 0, -6);

  ctx.restore();
}

function drawMainStageFinish(ctx, x, y, rWidth, scale, now, isDelivered) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);

  // Grand Climax Archway spanning road
  const gWidth = rWidth * 0.6;
  const gHeight = 110;
  ctx.strokeStyle = "#ffd700";
  ctx.shadowColor = "rgba(255, 215, 0, 0.9)";
  ctx.shadowBlur = 22;
  ctx.lineWidth = 6;

  ctx.beginPath();
  ctx.moveTo(-gWidth, 0);
  ctx.lineTo(-gWidth, -gHeight);
  ctx.lineTo(gWidth, -gHeight);
  ctx.lineTo(gWidth, 0);
  ctx.stroke();

  // Grand Header Banner
  ctx.fillStyle = "rgba(10, 16, 28, 0.95)";
  ctx.fillRect(-gWidth + 6, -gHeight, (gWidth * 2) - 12, 34);
  ctx.strokeRect(-gWidth + 6, -gHeight, (gWidth * 2) - 12, 34);

  ctx.fillStyle = "#ffd700";
  ctx.font = "900 13px monospace";
  ctx.textAlign = "center";
  ctx.fillText("🏁 TWITCHCON 2026 MAIN STAGE 🏁", 0, -gHeight + 22);

  // Pyrotechnic Spark Fountains on Curbs
  ctx.fillStyle = "#fff275";
  for (const curbX of [-gWidth, gWidth]) {
    for (let p = 0; p < 6; p++) {
      const py = -((now * 0.3 + p * 20) % 70);
      const px = curbX + (Math.sin(now * 0.05 + p) * 12);
      ctx.fillRect(px, py, 3, 3);
    }
  }

  // Confetti Shower on Delivery
  if (isDelivered) {
    const confettiColors = ["#ffd700", "#ff007f", "#00f0ff", "#a8f276", "#ffffff"];
    for (let c = 0; c < 24; c++) {
      const cx = (Math.sin(c * 17.3 + now * 0.002) * gWidth * 0.9);
      const cy = -gHeight + ((now * 0.08 + c * 18) % (gHeight + 40));
      ctx.fillStyle = confettiColors[c % confettiColors.length];
      ctx.fillRect(cx, cy, 5, 5);
    }
  }

  ctx.restore();
}

function drawTwitchChatStream(ctx, w, h, now) {
  const chatW = 230;
  const chatH = 145;
  const chatX = w - chatW - 16;
  const chatY = 68;

  ctx.save();
  ctx.fillStyle = "rgba(8, 12, 22, 0.75)";
  ctx.strokeStyle = "rgba(145, 70, 255, 0.35)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(chatX, chatY, chatW, chatH, 8);
  } else {
    ctx.rect(chatX, chatY, chatW, chatH);
  }
  ctx.fill();
  ctx.stroke();

  // Chat Header Bar
  ctx.fillStyle = "rgba(145, 70, 255, 0.35)";
  ctx.beginPath();
  if (ctx.roundRect) {
    ctx.roundRect(chatX, chatY, chatW, 22, [8, 8, 0, 0]);
  } else {
    ctx.rect(chatX, chatY, chatW, 22);
  }
  ctx.fill();

  ctx.fillStyle = "#ffffff";
  ctx.font = "800 10px monospace";
  ctx.textAlign = "left";
  ctx.fillText("💬 TWITCH CHAT · ODYSSEY LIVE", chatX + 10, chatY + 15);

  // Rolling Chat Messages
  const step = Math.floor(now * 0.0005);
  for (let m = 0; m < 4; m++) {
    const msg = CHAT_STREAM[(step + m) % CHAT_STREAM.length];
    const my = chatY + 40 + m * 26;

    // Badge
    ctx.fillStyle = msg.color;
    ctx.font = "800 9px monospace";
    ctx.fillText(`[${msg.badge}]`, chatX + 10, my);

    // User
    ctx.fillStyle = "#d0d8e2";
    ctx.fillText(msg.user + ":", chatX + 48, my);

    // Text
    ctx.fillStyle = "#ffffff";
    ctx.font = "600 9px monospace";
    const truncated = msg.text.length > 22 ? msg.text.substring(0, 21) + "…" : msg.text;
    ctx.fillText(truncated, chatX + 10, my + 11);
  }
  ctx.restore();
}


function drawFloatingPopups(ctx, w, h) {
  for (let i = floatingPopups.length - 1; i >= 0; i--) {
    const pop = floatingPopups[i];
    pop.y += pop.vy;
    pop.alpha -= 0.016;

    if (pop.alpha <= 0) {
      floatingPopups.splice(i, 1);
      continue;
    }

    ctx.save();
    ctx.globalAlpha = pop.alpha;
    ctx.fillStyle = pop.color;
    ctx.shadowColor = pop.color;
    ctx.shadowBlur = 10;
    ctx.font = "900 14px monospace";
    ctx.textAlign = "center";
    ctx.fillText(pop.text, w * pop.x, h * pop.y);
    ctx.restore();
  }
}

// ============================================================================
// Authoritative Polling & HUD Synchronization
// ============================================================================
async function poll() {
  try {
    const response = await fetch("/api/state");
    if (!response.ok) throw new Error("Server unavailable");
    const envelope = await response.json();
    if (!envelope.state || !envelope.evidence) throw new Error("Invalid authoritative envelope");
    if (!window.Hud) throw new Error("HUD renderer unavailable");

    view = window.Hud.deriveView(envelope.state, envelope.evidence);
    state = envelope.state;

    // Update in-game top-bar indicators
    $("district").textContent = state.movement.district;
    $("tick").textContent = `TICK ${String(state.tick).padStart(5, "0")} / 20 HZ`;
    $("pause").disabled = !view.controls.enabled && !state.is_paused;
    $("pause").textContent = state.is_paused ? "Resume" : "Pause";
    $("restart").hidden = view.mode === "disconnected" || state.status === "racing";

    // Manage in-game modals based on simulation state
    if (state.is_paused) {
      if ($("modal-pause")) $("modal-pause").hidden = false;
    } else {
      if ($("modal-pause")) $("modal-pause").hidden = true;
    }

    if (state.status !== "racing") {
      if ($("modal-terminal")) {
        $("modal-terminal").hidden = false;
        const isDelivered = state.status === "delivered";
        $("terminal-badge").textContent = isDelivered ? "MISSION ACCOMPLISHED" : "MATCH TERMINATED";
        $("terminal-badge").style.color = isDelivered ? "var(--mint)" : "var(--danger)";
        $("terminal-title").textContent = isDelivered ? "BUILD DELIVERED!" : "MATCH WIPED";
        $("terminal-title").style.color = isDelivered ? "var(--mint)" : "var(--danger)";
        $("terminal-detail").textContent = isDelivered
          ? `Reached the Main Stage before the 90s deadline! Final Hype pool (${state.bounty.pool}) settled 50/50.`
          : "Deadline reached before the Main Stage. Hype pool settles to zero. No extra turns are playable.";
      }
    } else {
      if ($("modal-terminal")) $("modal-terminal").hidden = true;
    }

    if ($("modal-disconnected")) $("modal-disconnected").hidden = true;

    // Dispatch custom event for HUD and integration tests
    window.dispatchEvent(new CustomEvent("odyssey:state", {
      detail: { state: envelope.state, evidence: envelope.evidence },
    }));
  } catch (error) {
    announceDisconnected(error.message);
  }
  setTimeout(poll, 200);
}

// ============================================================================
// Controls: Steering, Operator, Touch, Gamepad
// ============================================================================
async function steer(direction) {
  if (!state || !view || !view.controls.enabled) return;
  if (anyModalOpen()) return;
  try {
    const response = await fetch("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ direction, turn: state.turn }),
    });
    const result = await response.json();
    if (result.status === "applied") {
      $("feedback").textContent = `Control applied: steer ${direction}`;
      if (soundEnabled && audio) playWhoosh();
    } else if (result.status === "rejected") {
      $("feedback").textContent = `Steer rejected: ${result.reason}`;
    }
  } catch (err) {
    $("feedback").textContent = "Command delivery failed.";
  }
}

async function operatorAction(path, body = {}) {
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error("Operator command failed");
    await poll();
  } catch (err) {
    $("feedback").textContent = `Operator command failed: ${err.message}`;
  }
}

// Wire up in-game touch/click buttons
const leftBtn = document.querySelector('[data-control="left"]');
const rightBtn = document.querySelector('[data-control="right"]');
if (leftBtn) leftBtn.addEventListener("click", () => steer("left"));
if (rightBtn) rightBtn.addEventListener("click", () => steer("right"));

$("pause").onclick = () => {
  operatorAction("/api/pause", { paused: state ? !state.is_paused : true });
};
$("restart").onclick = () => {
  operatorAction("/api/restart");
};

// Wire modal button actions
if ($("btn-start")) {
  $("btn-start").addEventListener("click", () => {
    started = true;
    $("modal-start").hidden = true;
    toggleFullscreen().catch(() => {});
  });
}
if ($("btn-start-windowed")) {
  $("btn-start-windowed").addEventListener("click", () => {
    started = true;
    $("modal-start").hidden = true;
  });
}
if ($("btn-modal-resume")) {
  $("btn-modal-resume").addEventListener("click", () => operatorAction("/api/pause", { paused: false }));
}
if ($("btn-modal-restart")) {
  $("btn-modal-restart").addEventListener("click", () => operatorAction("/api/restart"));
}
if ($("btn-modal-help")) {
  $("btn-modal-help").addEventListener("click", () => {
    if ($("modal-help")) $("modal-help").hidden = false;
  });
}
if ($("btn-help")) {
  $("btn-help").addEventListener("click", () => {
    if ($("modal-help")) $("modal-help").hidden = false;
  });
}
if ($("btn-close-help")) {
  $("btn-close-help").addEventListener("click", () => {
    if ($("modal-help")) $("modal-help").hidden = true;
  });
}
if ($("btn-dismiss-help")) {
  $("btn-dismiss-help").addEventListener("click", () => {
    if ($("modal-help")) $("modal-help").hidden = true;
  });
}
if ($("btn-terminal-restart")) {
  $("btn-terminal-restart").addEventListener("click", () => operatorAction("/api/restart"));
}
if ($("btn-reconnect")) {
  $("btn-reconnect").addEventListener("click", () => poll());
}
if ($("btn-fullscreen")) {
  $("btn-fullscreen").addEventListener("click", toggleFullscreen);
}

// Keyboard shortcuts (ArrowLeft, ArrowRight, A, D, P, H, M, F, Escape)
window.addEventListener("keydown", (e) => {
  const modalOpen = anyModalOpen();

  // Keep Tab / Shift+Tab inside the visible top-most modal
  if (e.key === "Tab" && modalOpen) {
    trapTab(e);
    return;
  }

  // Prevent browser scroll on arrow keys; let Space activate focused buttons
  const onControl = e.target && e.target.closest && e.target.closest("button, a, input, select, textarea");
  if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.code)
    || (e.code === "Space" && !onControl)) {
    e.preventDefault();
  }

  // If a modal is open, Escape closes it
  if (e.code === "Escape") {
    if ($("modal-help") && !$("modal-help").hidden) {
      $("modal-help").hidden = true;
      return;
    }
    if ($("modal-pause") && !$("modal-pause").hidden) {
      operatorAction("/api/pause", { paused: false });
      return;
    }
  }

  // Steering (suppressed while any modal is open)
  if (modalOpen && ["ArrowLeft", "ArrowRight", "KeyA", "KeyD"].includes(e.code)) {
    return;
  }
  if (e.code === "ArrowLeft" || e.code === "KeyA") {
    steer("left");
  } else if (e.code === "ArrowRight" || e.code === "KeyD") {
    steer("right");
  } else if (e.code === "KeyP") {
    operatorAction("/api/pause", { paused: state ? !state.is_paused : true });
  } else if (e.code === "KeyH") {
    if ($("modal-help")) $("modal-help").hidden = !$("modal-help").hidden;
  } else if (e.code === "KeyF") {
    toggleFullscreen();
  } else if (e.code === "KeyM") {
    $("sound").click();
  }
});

// Gamepad polling loop
function pollGamepad() {
  const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
  for (const gp of gamepads) {
    if (!gp) continue;
    const now = performance.now();
    if (!anyModalOpen() && now - lastGamepadSteerTime > 250) {
      if (gp.buttons[14]?.pressed || gp.axes[0] < -0.5) {
        steer("left");
        lastGamepadSteerTime = now;
      } else if (gp.buttons[15]?.pressed || gp.axes[0] > 0.5) {
        steer("right");
        lastGamepadSteerTime = now;
      }
    }
  }
  requestAnimationFrame(pollGamepad);
}
requestAnimationFrame(pollGamepad);

// Inspector / Bullet Time Toggle
$("bullet").onclick = () => {
  bullet = !bullet;
  frozen = state ? structuredClone(state) : null;
  document.body.classList.toggle("bullet", bullet);
  $("bullet").setAttribute("aria-pressed", bullet);
  $("bullet").textContent = bullet ? "▶ Resume inspector" : "◷ Bullet time";
};

// Web Audio API Sound Synthesizer
$("sound").onclick = () => {
  soundEnabled = !soundEnabled;
  if (soundEnabled) {
    audio ??= new AudioContext();
    audio.resume();
  }
  $("sound").textContent = soundEnabled ? "♫ Sound on" : "♫ Sound off";
  $("sound").setAttribute("aria-pressed", soundEnabled);
};

function playWhoosh() {
  if (!audio) return;
  const osc = audio.createOscillator();
  const gain = audio.createGain();
  osc.type = "sine";
  osc.frequency.setValueAtTime(420, audio.currentTime);
  osc.frequency.exponentialRampToValueAtTime(140, audio.currentTime + 0.12);
  gain.gain.setValueAtTime(0.04, audio.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.12);
  osc.connect(gain).connect(audio.destination);
  osc.start();
  osc.stop(audio.currentTime + 0.14);
}

function playChime() {
  if (!audio) return;
  const osc = audio.createOscillator();
  const gain = audio.createGain();
  osc.type = "triangle";
  osc.frequency.setValueAtTime(880, audio.currentTime);
  osc.frequency.exponentialRampToValueAtTime(1320, audio.currentTime + 0.22);
  gain.gain.setValueAtTime(0.05, audio.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.25);
  osc.connect(gain).connect(audio.destination);
  osc.start();
  osc.stop(audio.currentTime + 0.26);
}

setInterval(() => {
  if (!soundEnabled || !audio || !state) return;
  const notes = state.status === "delivered" ? [261.63, 329.63, 392, 523.25]
    : state.phase === "resolution" ? [110, 164.81, 220, 164.81] : [220, 261.63, 329.63, 293.66];
  const oscillator = audio.createOscillator();
  const gain = audio.createGain();
  oscillator.type = "triangle";
  oscillator.frequency.value = notes[beat++ % notes.length];
  gain.gain.setValueAtTime(0.022, audio.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.18);
  oscillator.connect(gain).connect(audio.destination);
  oscillator.start();
  oscillator.stop(audio.currentTime + 0.2);
}, 250);

// Initialize runner loop and polling
requestAnimationFrame(draw);
poll();
