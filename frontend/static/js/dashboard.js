/* ═══════════════════════════════════════════════════════
   CogniMove Dashboard — JavaScript
   ═══════════════════════════════════════════════════════ */

"use strict";

// ── Estado global ─────────────────────────────────────────────
const state = {
  running:     false,
  lightState:  "unknown",
  stats:       { total:0, AVANCO_SINAL_VERMELHO:0, INVASAO_FAIXA:0, BLOQUEIO_CRUZAMENTO:0 },
  evtSource:   null,
  statsTimer:  null,
  logItems:    [],
};

// ── Constantes de tipo ────────────────────────────────────────
const TIPO_META = {
  AVANCO_SINAL_VERMELHO: { label:"Sinal Verm.",  tag:"tag--red",   icon:"🚦", toast:"toast--red"   },
  INVASAO_FAIXA:         { label:"Faixa",        tag:"tag--amber", icon:"🚷", toast:"toast--amber" },
  BLOQUEIO_CRUZAMENTO:   { label:"Bloqueio",     tag:"tag--blue",  icon:"🚧", toast:"toast--blue"  },
};

// ── DOM refs ──────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const EL = {
  statusDot:    $("status-dot"),
  statusText:   $("status-text"),
  btnStart:     $("btn-start"),
  btnStop:      $("btn-stop"),
  liveBadge:    $("live-badge"),
  videoFeed:    $("video-feed"),
  videoPlaceholder: $("video-placeholder"),
  lightInd:     $("light-indicator"),
  lightRed:     $("light-red"),
  lightYellow:  $("light-yellow"),
  lightGreen:   $("light-green"),
  statTotal:    $("stat-total"),
  statSinal:    $("stat-sinal"),
  statFaixa:    $("stat-faixa"),
  statBloq:     $("stat-bloq"),
  logList:      $("log-list"),
  logEmpty:     $("log-empty"),
  modalOverlay: $("modal-overlay"),
  toastCont:    $("toast-container"),
};

// ═══════════════════════════════════════════════════════════════
// MODAL
// ═══════════════════════════════════════════════════════════════

function toggleCustomSourceInput() {
  const sel = $("cfg-source-select");
  const customGroup = $("group-source-custom");
  if (sel && customGroup) {
    customGroup.style.display = sel.value === "custom" ? "block" : "none";
  }
}

async function loadVideosList() {
  try {
    const res = await fetch("/api/videos");
    if (!res.ok) return;
    const videos = await res.json();
    const sel = $("cfg-source-select");
    if (!sel || !videos || videos.length === 0) return;

    const currentVal = sel.value;
    let html = "";
    videos.forEach(v => {
      html += `<option value="${v.path}">🎥 ${v.filename}</option>`;
    });
    html += `<option value="0">📹 Webcam ao Vivo (0)</option>`;
    html += `<option value="custom">⚙️ Outro (Caminho ou URL RTSP)</option>`;
    sel.innerHTML = html;

    if ([...sel.options].some(o => o.value === currentVal)) {
      sel.value = currentVal;
    }
  } catch(_) {}
}

function startDetector() {
  loadVideosList();
  toggleCustomSourceInput();
  EL.modalOverlay.classList.add("open");
}

function closeModal() {
  EL.modalOverlay.classList.remove("open");
}

async function confirmStart() {
  const selVal = $("cfg-source-select").value;
  let source = selVal;
  if (selVal === "custom") {
    source = $("cfg-source-custom").value.trim() || "0";
  }
  const preset      = $("cfg-preset").value;
  const camera_name = $("cfg-camera").value.trim() || "Camera 1";

  closeModal();
  setStatus("connecting");
  showToast("🔄 Iniciando detector…", "toast--green", 2500);

  try {
    const res = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, preset, camera_name }),
    });
    const data = await res.json();
    if (res.ok) {
      setRunning(true);
      startVideoFeed();
      startSSE();
      startStatsPoll();
    } else {
      showToast(`❌ ${data.status || "Erro ao iniciar"}`, "toast--red", 4000);
      setStatus("error");
    }
  } catch(e) {
    showToast("❌ Erro de conexão com o servidor", "toast--red", 4000);
    setStatus("error");
  }
}

async function stopDetector() {
  try {
    await fetch("/api/stop", { method: "POST" });
  } catch(_) {}
  setRunning(false);
  stopVideoFeed();
  stopSSE();
  stopStatsPoll();
  showToast("⏹ Monitoramento encerrado", "toast--amber", 2500);
}

// ═══════════════════════════════════════════════════════════════
// STATUS
// ═══════════════════════════════════════════════════════════════

function setStatus(s) {
  EL.statusDot.className = "status-dot";
  if (s === "running")     { EL.statusDot.classList.add("active"); EL.statusText.textContent = "Monitorando"; }
  else if (s === "connecting") { EL.statusText.textContent = "Conectando…"; }
  else if (s === "error")  { EL.statusDot.classList.add("error"); EL.statusText.textContent = "Erro"; }
  else                     { EL.statusText.textContent = "Desconectado"; }
}

function setRunning(running) {
  state.running = running;
  EL.btnStart.disabled = running;
  EL.btnStop.disabled  = !running;
  EL.liveBadge.classList.toggle("visible", running);
  EL.lightInd.classList.toggle("visible", running);
  if (running) setStatus("running");
  else         setStatus("idle");
}

// ═══════════════════════════════════════════════════════════════
// VIDEO FEED
// ═══════════════════════════════════════════════════════════════

function startVideoFeed() {
  // Timestamp para forçar reload do stream
  EL.videoFeed.src = `/video_feed?t=${Date.now()}`;
  EL.videoFeed.classList.remove("hidden");
  EL.videoPlaceholder.style.display = "none";
}

function stopVideoFeed() {
  EL.videoFeed.src = "";
  EL.videoFeed.classList.add("hidden");
  EL.videoPlaceholder.style.display = "";
}

// ═══════════════════════════════════════════════════════════════
// SSE — INFRAÇÕES EM TEMPO REAL
// ═══════════════════════════════════════════════════════════════

function startSSE() {
  if (state.evtSource) state.evtSource.close();
  state.evtSource = new EventSource("/api/events");

  state.evtSource.onmessage = e => {
    try {
      const data = JSON.parse(e.data);
      if (data.ping) return;
      handleInfracao(data);
    } catch(_) {}
  };

  state.evtSource.onerror = () => {
    // Reconectar silenciosamente
  };
}

function stopSSE() {
  if (state.evtSource) { state.evtSource.close(); state.evtSource = null; }
}

function handleInfracao(inf) {
  const meta = TIPO_META[inf.tipo] || { label: inf.tipo, tag:"tag--red", icon:"⚠", toast:"toast--red" };

  // Update stats localmente (atualização imediata antes do próximo poll)
  state.stats.total++;
  state.stats[inf.tipo] = (state.stats[inf.tipo] || 0) + 1;
  renderStats();

  // Toast
  showToast(
    `${meta.icon} <strong>${meta.label}</strong> — ${inf.classe || ''} #${inf.track_id || ''}`,
    meta.toast, 4000
  );

  // Log
  addLogItem(inf, meta);

  // Atualizar semáforo se disponível
  if (inf.estado_semaforo) updateLightState(inf.estado_semaforo);
}

// ═══════════════════════════════════════════════════════════════
// STATS POLL
// ═══════════════════════════════════════════════════════════════

function startStatsPoll() {
  fetchStats();
  state.statsTimer = setInterval(fetchStats, 3000);
}

function stopStatsPoll() {
  if (state.statsTimer) { clearInterval(state.statsTimer); state.statsTimer = null; }
}

async function fetchStats() {
  try {
    const res  = await fetch("/api/stats");
    const data = await res.json();
    state.stats = { ...state.stats, ...data };
    renderStats();

    // Atualizar indicador de semáforo se disponível nos stats
    // (não há campo direto, mas a SSE cuida disso)
  } catch(_) {}
}

function renderStats() {
  setStatValue(EL.statTotal, state.stats.total);
  setStatValue(EL.statSinal, state.stats.AVANCO_SINAL_VERMELHO || 0);
  setStatValue(EL.statFaixa, state.stats.INVASAO_FAIXA || 0);
  setStatValue(EL.statBloq,  state.stats.BLOQUEIO_CRUZAMENTO || 0);
}

function setStatValue(el, val) {
  if (el.textContent !== String(val)) {
    el.textContent = val;
    el.classList.remove("stat-flash");
    void el.offsetWidth; // reflow
    el.classList.add("stat-flash");
  }
}

// ═══════════════════════════════════════════════════════════════
// SEMÁFORO VISUAL
// ═══════════════════════════════════════════════════════════════

function updateLightState(s) {
  if (state.lightState === s) return;
  state.lightState = s;
  EL.lightRed.className    = "light-bulb" + (s === "red"    ? " on-red"    : "");
  EL.lightYellow.className = "light-bulb" + (s === "yellow" ? " on-yellow" : "");
  EL.lightGreen.className  = "light-bulb" + (s === "green"  ? " on-green"  : "");
}

// ═══════════════════════════════════════════════════════════════
// LOG DE INFRAÇÕES
// ═══════════════════════════════════════════════════════════════

function addLogItem(inf, meta) {
  EL.logEmpty.style.display = "none";

  const ts = inf.timestamp
    ? new Date(inf.timestamp).toLocaleTimeString("pt-BR")
    : new Date().toLocaleTimeString("pt-BR");

  const item = document.createElement("div");
  item.className = "log-item";
  item.innerHTML = `
    <span class="log-item__tag ${meta.tag}">${meta.label}</span>
    <div class="log-item__body">
      <div class="log-item__desc">${escHtml(inf.descricao || inf.tipo)}</div>
      <div class="log-item__meta">
        ${inf.classe || '?'} #${inf.track_id ?? '?'} &nbsp;·&nbsp;
        Frame ${inf.frame ?? '?'} &nbsp;·&nbsp;
        ${ts}
      </div>
    </div>`;

  EL.logList.insertBefore(item, EL.logList.firstChild);
  state.logItems.push(inf);

  // Limitar a 200 itens no DOM
  const items = EL.logList.querySelectorAll(".log-item");
  if (items.length > 200) items[items.length - 1].remove();
}

function clearLog() {
  EL.logList.innerHTML = "";
  EL.logList.appendChild(EL.logEmpty);
  EL.logEmpty.style.display = "";
  state.logItems = [];
}

// ═══════════════════════════════════════════════════════════════
// EXPORTAR CSV
// ═══════════════════════════════════════════════════════════════

function exportCSV() {
  window.open("/api/relatorio/csv", "_blank");
}

// ═══════════════════════════════════════════════════════════════
// TOAST
// ═══════════════════════════════════════════════════════════════

function showToast(html, cls = "", duration = 3500) {
  const t = document.createElement("div");
  t.className = `toast ${cls}`;
  t.innerHTML = html;
  EL.toastCont.appendChild(t);
  setTimeout(() => t.remove(), duration);
}

// ═══════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════

function escHtml(s) {
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// Fechar modal ao clicar fora
EL.modalOverlay.addEventListener("click", e => {
  if (e.target === EL.modalOverlay) closeModal();
});

// Verificar se já está rodando ao carregar a página
(async () => {
  try {
    const res  = await fetch("/api/status");
    const data = await res.json();
    if (data.running) {
      setRunning(true);
      startVideoFeed();
      startSSE();
      startStatsPoll();
      showToast("✅ Detector já em execução", "toast--green", 2500);
    }
  } catch(_) {}
})();
