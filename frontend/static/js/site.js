/**
 * CogniMove — site.js
 * Módulos IIFE para o site de demonstração FECART 2026.
 *
 * Módulos:
 *   Utils               — helpers compartilhados (fetch, labels, badges, toasts)
 *   ThemeModule         — dark/light toggle persistido em localStorage
 *   NavModule           — navegação SPA por hash, highlight do link ativo
 *   MonitorModule       — MJPEG feed + SSE /api/events + log de infrações
 *   AnaliseModule       — curados reais + causa-raiz + donut Chart.js
 *   RelatorioModule     — histórico + donut + horizontal bar Chart.js + tabela
 *   InteratividadeModule — wizard 3 passos (GTA curados)
 */

'use strict';

/* ══════════════════════════════════════════════════════════════════════════
   UTILS
══════════════════════════════════════════════════════════════════════════ */
const Utils = (() => {

  /** Mapeia código interno → label de exibição (regra hard-coded, nunca inventar). */
  const TIPO_LABELS = {
    AVANCO_SINAL_VERMELHO: 'Avanço de sinal vermelho',
    INVASAO_FAIXA:         'Invasão de faixa de pedestres/bike box',
    BLOQUEIO_CRUZAMENTO:   'Bloqueio de cruzamento',
  };

  /** Classe CSS do log-item conforme tipo. */
  const TIPO_CLASS = {
    AVANCO_SINAL_VERMELHO: 'cm-log-item--sinal',
    INVASAO_FAIXA:         'cm-log-item--faixa',
    BLOQUEIO_CRUZAMENTO:   'cm-log-item--bloq',
  };

  /** Classe da badge conforme tipo. */
  const TIPO_BADGE = {
    AVANCO_SINAL_VERMELHO: 'cm-badge--red',
    INVASAO_FAIXA:         'cm-badge--amber',
    BLOQUEIO_CRUZAMENTO:   'cm-badge--blue',
  };

  function tipoLabel(codigo) {
    return TIPO_LABELS[codigo] || codigo || '—';
  }

  function tipoClass(codigo) {
    return TIPO_CLASS[codigo] || '';
  }

  function tipoBadgeClass(codigo) {
    return TIPO_BADGE[codigo] || 'cm-badge--outline';
  }

  function formatTimestamp(ts) {
    if (!ts) return '—';
    try {
      const d = new Date(ts);
      return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'medium' });
    } catch { return ts; }
  }

  function formatConf(v) {
    const n = parseFloat(v);
    if (isNaN(n)) return '—';
    return (n <= 1 ? (n * 100).toFixed(1) : n.toFixed(1)) + '%';
  }

  async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${url}`);
    return res.json();
  }

  function showToast(msg, type = 'info', duration = 4000) {
    const c = document.getElementById('cm-toast-container');
    if (!c) return;
    const el = document.createElement('div');
    el.className = `cm-toast cm-toast--${type}`;
    el.textContent = msg;
    c.appendChild(el);
    setTimeout(() => el.remove(), duration);
  }

  /** Retorna URL de clip relativa ao endpoint /clips/ */
  function clipUrl(path) {
    if (!path) return null;
    // path pode ser absoluto do sistema ou só o nome do arquivo
    const name = path.split(/[\\/]/).pop();
    return `/clips/${name}`;
  }

  /** Retorna URL de screenshot */
  function screenshotUrl(path) {
    if (!path) return null;
    const name = path.split(/[\\/]/).pop();
    return `/clips/${name}`;
  }

  return { tipoLabel, tipoClass, tipoBadgeClass, formatTimestamp, formatConf, fetchJSON, showToast, clipUrl, screenshotUrl };
})();


/* ══════════════════════════════════════════════════════════════════════════
   THEME MODULE
══════════════════════════════════════════════════════════════════════════ */
const ThemeModule = (() => {
  const LS_KEY = 'cm-theme';

  function apply(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(LS_KEY, theme);
  }

  function toggle() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    apply(current === 'dark' ? 'light' : 'dark');
  }

  function init() {
    const saved = localStorage.getItem(LS_KEY) || 'dark';
    apply(saved);
    const btn = document.getElementById('btn-dark-toggle');
    if (btn) btn.addEventListener('click', toggle);
  }

  return { init, apply, toggle };
})();


/* ══════════════════════════════════════════════════════════════════════════
   NAV MODULE
══════════════════════════════════════════════════════════════════════════ */
const NavModule = (() => {
  const SECTION_IDS = ['inicio', 'monitoramento', 'analise', 'relatorios', 'interatividade', 'sobre'];
  let _active = 'inicio';

  function showSection(id) {
    if (!SECTION_IDS.includes(id)) return;
    _active = id;

    // Toggle sections
    SECTION_IDS.forEach(sid => {
      const el = document.getElementById(sid);
      if (!el) return;
      if (sid === id) {
        el.classList.add('cm-section--active');
        el.removeAttribute('hidden');
      } else {
        el.classList.remove('cm-section--active');
      }
    });

    // Highlight nav links
    document.querySelectorAll('.cm-nav__item').forEach(a => {
      a.classList.toggle('is-active', a.dataset.target === id);
    });

    // Lazy init sections
    if (id === 'analise')       AnaliseModule.onEnter();
    if (id === 'relatorios')    RelatorioModule.onEnter();
    if (id === 'interatividade') InteratividadeModule.onEnter();

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function handleHash() {
    const hash = window.location.hash.replace('#', '') || 'inicio';
    showSection(hash);
  }

  function init() {
    // Wire all .cm-nav-link elements
    document.querySelectorAll('.cm-nav-link').forEach(a => {
      a.addEventListener('click', e => {
        const target = a.dataset.target;
        if (target) {
          e.preventDefault();
          history.pushState(null, '', `#${target}`);
          showSection(target);
        }
      });
    });

    window.addEventListener('hashchange', handleHash);
    handleHash();
  }

  return { init, showSection };
})();


/* ══════════════════════════════════════════════════════════════════════════
   MONITOR MODULE
══════════════════════════════════════════════════════════════════════════ */
const MonitorModule = (() => {
  let _sse = null;
  let _stats = { total: 0, AVANCO_SINAL_VERMELHO: 0, INVASAO_FAIXA: 0, BLOQUEIO_CRUZAMENTO: 0 };

  function init() {
    const sel = document.getElementById('mon-video-select');
    if (sel) sel.addEventListener('change', () => {
      const v = sel.value;
      document.getElementById('mon-btn-start').disabled = !v;
    });
    updateStatus('idle');
  }

  function updateStatus(state, label) {
    const pill = document.getElementById('mon-status-pill');
    const text = document.getElementById('mon-status-text');
    if (pill) pill.className = `cm-status-pill cm-status-pill--${state}`;
    if (text) text.textContent = label || { idle: 'Aguardando', running: 'Processando…', error: 'Erro' }[state] || state;
  }

  async function start() {
    const sel   = document.getElementById('mon-video-select');
    const opt   = sel?.options[sel.selectedIndex];
    const video = sel?.value;
    if (!video) return;

    const preset = opt?.dataset.preset || 'general';
    const camera = `Câmera — ${opt?.text || video}`;

    clearLog();
    try {
      const r = await fetch('/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: `videos_originais/${video}`, preset, camera_name: camera }),
      });
      if (!r.ok) {
        const j = await r.json().catch(() => ({}));
        if (j.status === 'already_running') { Utils.showToast('Já em execução.', 'info'); return; }
        throw new Error(r.status);
      }
    } catch (err) {
      Utils.showToast(`Erro ao iniciar: ${err.message}`, 'danger');
      return;
    }

    // Show video feed
    const feed = document.getElementById('mon-video-feed');
    const ph   = document.getElementById('mon-video-placeholder');
    if (feed) { feed.src = '/video_feed'; feed.classList.remove('hidden'); }
    if (ph)   ph.classList.add('hidden');

    document.getElementById('mon-btn-start').disabled = true;
    document.getElementById('mon-btn-stop').disabled  = false;
    document.getElementById('mon-cam-info').style.display = '';
    document.getElementById('mon-cam-label').textContent = camera;
    document.getElementById('mon-live-badge').style.display = '';
    updateStatus('running');

    _openSSE();
  }

  function stop() {
    fetch('/api/stop', { method: 'POST' }).catch(() => {});
    _closeSSE();

    const feed = document.getElementById('mon-video-feed');
    const ph   = document.getElementById('mon-video-placeholder');
    if (feed) { feed.src = ''; feed.classList.add('hidden'); }
    if (ph)   ph.classList.remove('hidden');

    document.getElementById('mon-btn-start').disabled = false;
    document.getElementById('mon-btn-stop').disabled  = true;
    document.getElementById('mon-live-badge').style.display = 'none';
    updateStatus('idle', 'Parado');
  }

  function _openSSE() {
    _closeSSE();
    _sse = new EventSource('/api/events');
    _sse.onmessage = e => {
      try {
        const data = JSON.parse(e.data);
        if (data.ping) return;
        _appendLogItem(data);
        _updateStats(data.tipo);
      } catch {}
    };
    _sse.onerror = () => updateStatus('error', 'Erro SSE');
  }

  function _closeSSE() {
    if (_sse) { _sse.close(); _sse = null; }
  }

  function _formatTimeOnly(ts) {
    try {
      const d = new Date(ts);
      return isNaN(d.getTime()) ? '' : d.toLocaleTimeString('pt-BR');
    } catch {
      return '';
    }
  }

  function _appendLogItem(inf) {
    const list  = document.getElementById('mon-log-list');
    const empty = document.getElementById('mon-log-empty');
    if (empty) empty.style.display = 'none';

    const tipoCls = Utils.tipoClass(inf.tipo);
    const eventTime = inf.timestamp ? new Date(inf.timestamp).getTime() : Date.now();
    const firstItem = list?.querySelector('.cm-log-item');

    // Agrupamento visual: mesmo tipo e intervalo menor que 8s
    if (firstItem && tipoCls && firstItem.classList.contains(tipoCls)) {
      const lastTime = Number(firstItem.dataset.timeLast || 0);
      const diffSec = Math.abs(eventTime - lastTime) / 1000;

      if (lastTime > 0 && diffSec < 8) {
        const count = parseInt(firstItem.dataset.count || '1', 10) + 1;
        firstItem.dataset.count = String(count);
        firstItem.dataset.timeLast = String(eventTime);

        const firstTimeStr = firstItem.dataset.timeFirstStr || _formatTimeOnly(Number(firstItem.dataset.timeFirst));
        const lastTimeStr = _formatTimeOnly(eventTime);
        const timeRange = `${firstTimeStr} - ${lastTimeStr} (${count}x)`;

        // Atualiza ou insere o contador na tag de tipo
        const tipoEl = firstItem.querySelector('.cm-log-item__tipo');
        if (tipoEl) {
          let countBadge = tipoEl.querySelector('.cm-log-item__count');
          if (!countBadge) {
            countBadge = document.createElement('span');
            countBadge.className = 'cm-log-item__count';
            tipoEl.appendChild(countBadge);
          }
          countBadge.textContent = `×${count}`;
        }

        // Atualiza timestamp para o intervalo "HH:MM:SS - HH:MM:SS (Nx)"
        const metaEl = firstItem.querySelector('.cm-log-item__meta');
        if (metaEl) {
          metaEl.textContent = `${timeRange} · ID ${inf.track_id ?? '—'} · ${Utils.formatConf(inf.confianca)}`;
        }
        return;
      }
    }

    const timeStr = _formatTimeOnly(eventTime);
    const item = document.createElement('div');
    item.className = `cm-log-item ${tipoCls}`;
    item.dataset.timeFirst = String(eventTime);
    item.dataset.timeLast = String(eventTime);
    item.dataset.timeFirstStr = timeStr;
    item.dataset.count = '1';

    item.innerHTML = `
      <div class="cm-log-item__tipo">${Utils.tipoLabel(inf.tipo)}</div>
      <div class="cm-log-item__meta">${Utils.formatTimestamp(inf.timestamp)} · ID ${inf.track_id ?? '—'} · ${Utils.formatConf(inf.confianca)}</div>
    `;
    list?.prepend(item);

    // Keep max 60 items
    const items = list?.querySelectorAll('.cm-log-item');
    if (items && items.length > 60) items[items.length - 1].remove();
  }

  function _updateStats(tipo) {
    _stats.total++;
    if (_stats[tipo] !== undefined) _stats[tipo]++;
    else _stats[tipo] = (_stats[tipo] || 0) + 1;

    document.getElementById('mon-stat-total').textContent = _stats.total;
    document.getElementById('mon-stat-sinal').textContent = _stats.AVANCO_SINAL_VERMELHO;
    document.getElementById('mon-stat-faixa').textContent = _stats.INVASAO_FAIXA;
    document.getElementById('mon-stat-bloq').textContent  = _stats.BLOQUEIO_CRUZAMENTO;
  }

  function clearLog() {
    const list = document.getElementById('mon-log-list');
    if (!list) return;
    list.querySelectorAll('.cm-log-item').forEach(i => i.remove());
    const empty = document.getElementById('mon-log-empty');
    if (empty) empty.style.display = '';
    _stats = { total: 0, AVANCO_SINAL_VERMELHO: 0, INVASAO_FAIXA: 0, BLOQUEIO_CRUZAMENTO: 0 };
    ['mon-stat-total','mon-stat-sinal','mon-stat-faixa','mon-stat-bloq']
      .forEach(id => { const el = document.getElementById(id); if (el) el.textContent = '0'; });
  }

  return { init, start, stop, clearLog };
})();


/* ══════════════════════════════════════════════════════════════════════════
   ANÁLISE MODULE
══════════════════════════════════════════════════════════════════════════ */
const AnaliseModule = (() => {
  let _curados = [];
  let _chart   = null;
  let _loaded  = false;

  const CHART_COLORS = ['#8B5CF6','#3B82F6','#10B981','#F59E0B','#EF4444','#EC4899'];

  async function onEnter() {
    if (_loaded) return;
    _loaded = true;
    await _loadCurados();
  }

  async function _loadCurados() {
    try {
      _curados = await Utils.fetchJSON('/api/curados');
    } catch {
      _curados = [];
    }

    const sel     = document.getElementById('anal-occ-select');
    const count   = document.getElementById('anal-occ-count');
    const ph      = document.getElementById('anal-placeholder');
    const content = document.getElementById('anal-content');

    if (_curados.length === 0) {
      // Placeholder state (Opção A)
      if (ph) ph.style.display = '';
      if (content) content.classList.add('hidden');
      if (count) count.textContent = '(pasta curados/real/ vazia — Prompt 9)';
      if (sel) sel.innerHTML = '<option value="">— Nenhuma ocorrência disponível —</option>';
      return;
    }

    if (ph) ph.style.display = 'none';
    if (count) count.textContent = `${_curados.length} ocorrência(s)`;

    if (sel) {
      sel.innerHTML = '<option value="">— Selecione —</option>' +
        _curados.map((o, i) =>
          `<option value="${i}">${Utils.formatTimestamp(o.timestamp)} — ${Utils.tipoLabel(o.tipo)} — ${o.camera || '—'}</option>`
        ).join('');
    }

    // Auto-select first
    if (_curados.length > 0) selecionarOcorrencia(0);
  }

  async function selecionarOcorrencia(idx) {
    const occ = _curados[parseInt(idx, 10)];
    if (!occ) return;

    const content = document.getElementById('anal-content');
    if (content) content.classList.remove('hidden');

    // Metadata
    _set('anal-timestamp', Utils.formatTimestamp(occ.timestamp));
    _set('anal-tipo', Utils.tipoLabel(occ.tipo));
    _set('anal-camera', occ.camera || '—');
    _set('anal-classe', occ.classe || '—');
    _set('anal-track', occ.track_id ?? '—');

    const conf = parseFloat(occ.confianca) || 0;
    const confPct = conf <= 1 ? conf * 100 : conf;
    _set('anal-confianca', confPct.toFixed(1) + '%');
    const fill = document.getElementById('anal-conf-bar-fill');
    if (fill) fill.style.width = confPct + '%';

    // Screenshot
    const screenshotEl = document.getElementById('anal-screenshot');
    const ssUrl = Utils.screenshotUrl(occ.screenshot);
    if (screenshotEl) screenshotEl.src = ssUrl || '';

    // Type badge
    const badge = document.getElementById('anal-tipo-badge');
    if (badge) {
      badge.textContent = Utils.tipoLabel(occ.tipo);
      badge.className = `cm-badge ${Utils.tipoBadgeClass(occ.tipo)}`;
    }

    // Clip
    const clipWrap = document.getElementById('anal-clip-wrap');
    const clipPlayer = document.getElementById('anal-clip-player');
    const clipUrl = Utils.clipUrl(occ.clip);
    if (clipUrl && clipPlayer) {
      clipPlayer.src = clipUrl;
      if (clipWrap) clipWrap.classList.remove('hidden');
    } else {
      if (clipWrap) clipWrap.classList.add('hidden');
    }

    // Causa-raiz: use stored data first, then fetch for live context
    let causaData = {
      causa_principal: occ.causa_principal || '—',
      confianca: parseFloat(occ.causa_confianca) || 0,
      distribuicao: {},
      fatores_ativos: occ.cenarios_ativos ? occ.cenarios_ativos.split(', ').filter(Boolean) : [],
    };

    // Try to parse distribuicao_causas if stored as JSON string
    if (occ.distribuicao_causas) {
      try {
        causaData.distribuicao = typeof occ.distribuicao_causas === 'string'
          ? JSON.parse(occ.distribuicao_causas)
          : occ.distribuicao_causas;
      } catch {}
    }

    // Also fetch live (may differ due to context changes)
    try {
      const live = await Utils.fetchJSON(`/api/causa_raiz?tipo=${encodeURIComponent(occ.tipo)}`);
      causaData = live;
    } catch {}

    _renderCausaRaiz(causaData);
  }

  function _renderCausaRaiz(data) {
    const causeConf = parseFloat(data.confianca) * 100;

    _set('anal-causa-nome', data.causa_principal || '—');
    _set('anal-causa-pct', (causeConf).toFixed(0) + '%');

    const bar = document.getElementById('anal-causa-bar');
    if (bar) bar.style.width = causeConf + '%';

    const badge = document.getElementById('anal-causa-badge');
    if (badge) badge.textContent = data.causa_principal || '—';

    // Origin
    const orig = document.getElementById('anal-origem');
    if (orig && data.origem) {
      const labels = { contexto: 'Influenciada por contexto urbano', evidencia: 'Influenciada por evidência', ambos: 'Influenciada por contexto e evidência', nenhuma: 'Distribuição base — sem modificadores ativos' };
      orig.textContent = labels[data.origem] || '';
    }

    // Fatores ativos
    const fatores = document.getElementById('anal-fatores-list');
    if (fatores) {
      const list = Array.isArray(data.fatores_ativos) ? data.fatores_ativos : [];
      if (list.length === 0) {
        fatores.innerHTML = '<span class="cm-badge cm-badge--outline">Nenhum fator ativo</span>';
      } else {
        fatores.innerHTML = list.map(f => `<span class="cm-badge cm-badge--amber">${f}</span>`).join('');
      }
    }

    // Donut chart
    _updateChart(data.distribuicao || {});
  }

  function _updateChart(dist) {
    const canvas = document.getElementById('anal-donut-chart');
    if (!canvas) return;

    const labels = Object.keys(dist);
    const values = Object.values(dist).map(v => Math.round(v * 100));

    if (_chart) { _chart.destroy(); _chart = null; }

    if (labels.length === 0) return;

    _chart = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels,
        datasets: [{ data: values, backgroundColor: CHART_COLORS.slice(0, labels.length), borderWidth: 0, hoverOffset: 6 }],
      },
      options: {
        responsive: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}%` },
          },
        },
        cutout: '65%',
      },
    });
  }

  function _set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val ?? '—';
  }

  return { onEnter, selecionarOcorrencia };
})();


/* ══════════════════════════════════════════════════════════════════════════
   RELATÓRIO MODULE
══════════════════════════════════════════════════════════════════════════ */
const RelatorioModule = (() => {
  let _donutChart = null;
  let _barChart   = null;
  let _loaded     = false;

  const TIPO_COLORS = {
    AVANCO_SINAL_VERMELHO: '#EF4444',
    INVASAO_FAIXA:         '#F59E0B',
    BLOQUEIO_CRUZAMENTO:   '#3B82F6',
  };

  async function onEnter() {
    if (_loaded) return;
    _loaded = true;
    await _load();
  }

  async function _load() {
    let records = [];
    try {
      records = await Utils.fetchJSON('/api/relatorio/historico');
    } catch {
      records = [];
    }

    // Also try curados reais as fallback
    if (records.length === 0) {
      try {
        records = await Utils.fetchJSON('/api/curados');
      } catch {}
    }

    const count = document.getElementById('rel-count-badge');
    if (count) count.textContent = `${records.length} ocorrência(s)`;

    if (records.length === 0) {
      _showEmpty();
      return;
    }

    _renderKPIs(records);
    _renderDonut(records);
    _renderBar(records);
    _renderTable(records);
  }

  function _showEmpty() {
    document.getElementById('rel-empty-state')?.removeAttribute('style');
    document.getElementById('rel-table')?.classList.add('hidden');
  }

  function _renderKPIs(records) {
    const total = records.length;
    document.getElementById('rel-kpi-total').textContent = total;

    const confs = records.map(r => parseFloat(r.confianca)).filter(v => !isNaN(v) && v > 0);
    if (confs.length > 0) {
      const avg = confs.reduce((a, b) => a + b, 0) / confs.length;
      const avgPct = avg <= 1 ? avg * 100 : avg;
      document.getElementById('rel-kpi-conf').textContent = avgPct.toFixed(1) + '%';
    }

    // Top type
    const freq = {};
    records.forEach(r => { freq[r.tipo] = (freq[r.tipo] || 0) + 1; });
    const topTipo = Object.entries(freq).sort((a, b) => b[1] - a[1])[0];
    if (topTipo) {
      document.getElementById('rel-kpi-top-tipo').textContent = Utils.tipoLabel(topTipo[0]);
    }
  }

  function _renderDonut(records) {
    const canvas = document.getElementById('rel-donut-chart');
    if (!canvas) return;

    const freq = { AVANCO_SINAL_VERMELHO: 0, INVASAO_FAIXA: 0, BLOQUEIO_CRUZAMENTO: 0 };
    records.forEach(r => { if (freq[r.tipo] !== undefined) freq[r.tipo]++; });

    const labels = Object.keys(freq).map(Utils.tipoLabel);
    const values = Object.values(freq);
    const colors = Object.keys(freq).map(k => TIPO_COLORS[k] || '#6B7280');

    if (_donutChart) { _donutChart.destroy(); _donutChart = null; }

    _donutChart = new Chart(canvas, {
      type: 'doughnut',
      data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 0, hoverOffset: 6 }] },
      options: {
        responsive: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}` } },
        },
        cutout: '60%',
      },
    });

    // Custom legend
    const legend = document.getElementById('rel-donut-legend');
    if (legend) {
      legend.innerHTML = Object.keys(freq).map((k, i) =>
        `<div class="cm-chart-legend-item">
          <div class="cm-chart-legend-dot" style="background:${colors[i]}"></div>
          <span>${Utils.tipoLabel(k)}: <strong>${freq[k]}</strong></span>
        </div>`
      ).join('');
    }
  }

  function _renderBar(records) {
    const canvas = document.getElementById('rel-bar-chart');
    if (!canvas) return;

    // Aggregate causes
    const causaFreq = {};
    records.forEach(r => {
      if (r.causa_principal) causaFreq[r.causa_principal] = (causaFreq[r.causa_principal] || 0) + 1;
    });

    // Sort descending, take top 6
    const sorted = Object.entries(causaFreq).sort((a, b) => b[1] - a[1]).slice(0, 6);
    if (sorted.length === 0) return;

    const labels = sorted.map(([k]) => k);
    const values = sorted.map(([, v]) => v);

    if (_barChart) { _barChart.destroy(); _barChart = null; }

    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    const textColor = isDark ? '#94A3B8' : '#6B7280';
    const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

    _barChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: 'rgba(139, 92, 246, 0.7)',
          borderColor: '#8B5CF6',
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        indexAxis: 'y',  // Horizontal bar
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => ` ${ctx.raw} ocorrência(s)` } },
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: { color: textColor, stepSize: 1 },
            grid: { color: gridColor },
          },
          y: {
            ticks: { color: textColor, font: { size: 11 } },
            grid: { display: false },
          },
        },
      },
    });
  }

  function _renderTable(records) {
    const empty  = document.getElementById('rel-empty-state');
    const table  = document.getElementById('rel-table');
    const tbody  = document.getElementById('rel-table-body');
    const range  = document.getElementById('rel-occ-range');

    if (!tbody) return;

    if (empty) empty.style.display = 'none';
    if (table) table.classList.remove('hidden');
    if (range) range.textContent = `Mostrando ${Math.min(records.length, 100)} de ${records.length}`;

    // Show max 100
    tbody.innerHTML = records.slice(0, 100).map(r => {
      const ssUrl = Utils.screenshotUrl(r.screenshot);
      const ssHtml = ssUrl
        ? `<a href="${ssUrl}" target="_blank" rel="noopener" class="cm-badge cm-badge--outline">🖼 Ver</a>`
        : '—';
      const confVal = parseFloat(r.confianca);
      const confPct = (confVal <= 1 ? confVal * 100 : confVal).toFixed(1);
      return `
        <tr>
          <td class="cm-mono" style="font-size:.8rem">${Utils.formatTimestamp(r.timestamp)}</td>
          <td><span class="cm-badge ${Utils.tipoBadgeClass(r.tipo)}">${Utils.tipoLabel(r.tipo)}</span></td>
          <td style="font-size:.85rem">${r.camera || '—'}</td>
          <td class="cm-mono" style="font-size:.85rem">${confPct}%</td>
          <td style="font-size:.85rem">${r.causa_principal || '—'}</td>
          <td>${ssHtml}</td>
        </tr>`;
    }).join('');
  }

  async function exportCSV() {
    try {
      const resp = await fetch('/api/relatorio/csv');
      if (resp.ok) {
        const blob = await resp.blob();
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href = url; a.download = 'relatorio_cognimove.csv'; a.click();
        URL.revokeObjectURL(url);
        Utils.showToast('CSV baixado com sucesso.', 'success');
      } else {
        Utils.showToast('CSV não disponível. Inicie uma sessão de monitoramento primeiro.', 'info');
      }
    } catch (e) {
      Utils.showToast('Erro ao exportar CSV.', 'danger');
    }
  }

  // Re-render on theme change (bar chart colors)
  function refresh() {
    _loaded = false;
    if (_donutChart) { _donutChart.destroy(); _donutChart = null; }
    if (_barChart)   { _barChart.destroy();   _barChart   = null; }
  }

  return { onEnter, exportCSV, refresh };
})();


/* ══════════════════════════════════════════════════════════════════════════
   INTERATIVIDADE MODULE — Sorteio Automático (Prompt 7)
   Fluxo: início → vídeo → quiz → resultado
   - Pool embaralhado de curados GTA; sem repetição até esgotar todos
   - Contador "N de 6 vistas" atualizado a cada rodada
   - Quiz: 3 opções (1 correta + 2 distratoras) embaralhadas
══════════════════════════════════════════════════════════════════════════ */
const InteratividadeModule = (() => {
  const MAX_POOL = 6;
  const TODOS_TIPOS = [
    'AVANCO_SINAL_VERMELHO',
    'INVASAO_FAIXA',
    'BLOQUEIO_CRUZAMENTO',
  ];
  const CHART_COLORS = ['#8B5CF6','#3B82F6','#10B981','#F59E0B','#EF4444'];

  let _curadosGTA   = [];   // todas as ocorrências carregadas
  let _pool         = [];   // fila embaralhada da sessão
  let _vistas       = 0;    // quantas foram vistas nesta sessão
  let _atual        = null; // ocorrência corrente
  let _respostaUser = null; // tipo escolhido pelo usuário no quiz
  let _causaResult  = null;
  let _wizChart     = null;
  let _loaded       = false;
  let _step         = 1;    // 1=início, 2=vídeo, 3=quiz, 4=resultado

  // ── Utils ────────────────────────────────────────────────────────────────

  function _shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function _refillPool() {
    // Garante pool com pelo menos MAX_POOL itens (ou todos se < MAX_POOL)
    const base = _curadosGTA.length > 0 ? _curadosGTA : [];
    _pool = _shuffle(base).slice(0, MAX_POOL);
  }

  function _updateCounter() {
    const total = Math.min(_curadosGTA.length, MAX_POOL);
    const el = document.getElementById('wiz-counter-text');
    if (el) el.textContent = `${_vistas} de ${total} vistas`;
  }

  // ── Inicialização ────────────────────────────────────────────────────────

  async function onEnter() {
    if (_loaded) return;
    _loaded = true;
    await _loadGTA();
  }

  async function _loadGTA() {
    try {
      _curadosGTA = await Utils.fetchJSON('/api/curados/gta');
    } catch {
      _curadosGTA = [];
    }
    _refillPool();
    _updateCounter();

    const semEl = document.getElementById('wiz-sem-ocorrencias');
    const btnEl = document.getElementById('wiz-btn-iniciar');
    if (_curadosGTA.length === 0) {
      if (semEl) semEl.style.display = '';
      if (btnEl) btnEl.disabled = true;
    } else {
      if (semEl) semEl.style.display = 'none';
      if (btnEl) btnEl.disabled = false;
    }
  }

  // ── Sorteio ──────────────────────────────────────────────────────────────

  function sortearEIniciar() {
    if (_pool.length === 0) {
      // Esgotou a sessão — reinicia pool para nova sessão
      _vistas = 0;
      _refillPool();
      _updateCounter();
    }
    if (_pool.length === 0) {
      Utils.showToast('Nenhuma ocorrência disponível ainda.', 'info');
      return;
    }
    _atual = _pool.shift();  // retira do início da fila embaralhada
    _respostaUser = null;
    _causaResult  = null;

    // Carrega vídeo no player
    const player = document.getElementById('wiz-clip-player');
    const clipUrl = Utils.clipUrl(_atual.clip);
    if (player && clipUrl) {
      player.src = clipUrl;
      player.load();
    }

    // Metadados da câmera
    const metaEl = document.getElementById('wiz-clip-meta');
    const camEl  = document.getElementById('wiz-clip-camera');
    const confEl = document.getElementById('wiz-clip-conf');
    if (metaEl && _atual.camera) {
      metaEl.style.display = '';
      if (camEl)  camEl.textContent  = _atual.camera || '—';
      if (confEl) confEl.textContent = Utils.formatConf(_atual.confianca);
    }

    irParaStep(2);
  }

  // ── Navegação entre passos ──────────────────────────────────────────────

  function irParaStep(n) {
    _step = n;
    const TOTAL_STEPS = 4;

    // Mostrar/ocultar painéis
    for (let i = 1; i <= TOTAL_STEPS; i++) {
      const panel = document.getElementById(`wiz-panel-${i}`);
      if (panel) panel.classList.toggle('hidden', i !== n);

      const stepEl = document.getElementById(`wiz-step-${i}`);
      if (stepEl) {
        stepEl.classList.remove('cm-wizard-step--active', 'cm-wizard-step--done');
        if (i === n) stepEl.classList.add('cm-wizard-step--active');
        if (i < n)  stepEl.classList.add('cm-wizard-step--done');
      }
    }

    // Atualizar linhas de conexão
    document.querySelectorAll('.cm-wizard-step__line').forEach((l, i) => {
      l.style.background = (i + 1) < n ? 'var(--success)' : 'var(--card-border)';
    });

    // Ações por passo
    if (n === 3) _renderQuiz();
    if (n === 4) _renderResultado();

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── Quiz ────────────────────────────────────────────────────────────────

  function _renderQuiz() {
    if (!_atual) return;

    const container = document.getElementById('wiz-quiz-opcoes');
    const btnConfirmar = document.getElementById('wiz-btn-confirmar');
    if (!container) return;
    if (btnConfirmar) btnConfirmar.disabled = true;
    _respostaUser = null;

    // Monta opções: 1 correta + 2 distratoras embaralhadas
    const distratoras = TODOS_TIPOS.filter(t => t !== _atual.tipo);
    const opcoes = _shuffle([_atual.tipo, ...distratoras]);

    container.innerHTML = opcoes.map(tipo => `
      <button class="cm-quiz-opcao" data-tipo="${tipo}"
              onclick="InteratividadeModule.selecionarResposta('${tipo}')"
              role="radio" aria-checked="false">
        <span class="cm-quiz-opcao__icon" aria-hidden="true">${_tipoIcon(tipo)}</span>
        <span class="cm-quiz-opcao__label">${Utils.tipoLabel(tipo)}</span>
      </button>
    `).join('');
  }

  function _tipoIcon(tipo) {
    const icons = {
      AVANCO_SINAL_VERMELHO: '🚦',
      INVASAO_FAIXA: '🚷',
      BLOQUEIO_CRUZAMENTO: '🚧',
    };
    return icons[tipo] || '❓';
  }

  function selecionarResposta(tipo) {
    _respostaUser = tipo;
    document.querySelectorAll('.cm-quiz-opcao').forEach(btn => {
      const isSelected = btn.dataset.tipo === tipo;
      btn.classList.toggle('is-selected', isSelected);
      btn.setAttribute('aria-checked', isSelected ? 'true' : 'false');
    });
    const btn = document.getElementById('wiz-btn-confirmar');
    if (btn) btn.disabled = false;
  }

  // ── Resultado ────────────────────────────────────────────────────────────

  async function _renderResultado() {
    if (!_atual) return;

    // Incrementa contador ao chegar no resultado
    _vistas++;
    _updateCounter();
    if (_vistas >= Math.min(_curadosGTA.length, MAX_POOL)) {
      // Esgotou — botão "Próxima" passa a reiniciar sessão
      const btnProx = document.getElementById('wiz-btn-proxima');
      if (btnProx) btnProx.textContent = '🔄  Reiniciar sessão';
    }

    const acertou = _respostaUser === _atual.tipo;

    // Header de acerto/erro
    const headerEl = document.getElementById('wiz-resultado-header');
    if (headerEl) {
      headerEl.innerHTML = acertou
        ? `<div class="cm-resultado-acerto"><span class="cm-resultado-emoji">✅</span><span class="cm-resultado-msg">Você acertou! O CogniMove também detectou <strong>${Utils.tipoLabel(_atual.tipo)}</strong>.</span></div>`
        : `<div class="cm-resultado-erro"><span class="cm-resultado-emoji">❌</span><span class="cm-resultado-msg">Sua resposta: <strong>${Utils.tipoLabel(_respostaUser || '—')}</strong> — A detecção correta foi: <strong>${Utils.tipoLabel(_atual.tipo)}</strong>.</span></div>`;
    }

    // Sua resposta
    const userTipoEl = document.getElementById('wiz-user-tipo');
    if (userTipoEl) userTipoEl.textContent = `Você respondeu: ${Utils.tipoLabel(_respostaUser || '—')}`;
    const userAcertoEl = document.getElementById('wiz-user-acerto');
    if (userAcertoEl) userAcertoEl.textContent = acertou ? '✅ Resposta correta!' : '❌ Resposta incorreta.';

    // CogniMove
    const cmTipoEl = document.getElementById('wiz-cm-tipo');
    if (cmTipoEl) cmTipoEl.textContent = `Infração detectada: ${Utils.tipoLabel(_atual.tipo)}`;

    const cmInfBadge = document.getElementById('wiz-cm-infracao-badge');
    if (cmInfBadge) {
      cmInfBadge.textContent = Utils.tipoLabel(_atual.tipo);
      cmInfBadge.className = `cm-badge cm-badge--lg ${Utils.tipoBadgeClass(_atual.tipo)}`;
    }
    const confBadge = document.getElementById('wiz-cm-conf-badge');
    if (confBadge) confBadge.textContent = Utils.formatConf(_atual.confianca);

    // Causa-raiz
    try {
      _causaResult = await Utils.fetchJSON(`/api/causa_raiz?tipo=${encodeURIComponent(_atual.tipo)}`);
    } catch {
      _causaResult = {
        causa_principal: _atual.causa_principal || '—',
        confianca: parseFloat(_atual.causa_confianca) || 0,
        distribuicao: {},
        fatores_ativos: _atual.cenarios_ativos ? _atual.cenarios_ativos.split(', ').filter(Boolean) : [],
      };
      if (_atual.distribuicao_causas) {
        try { _causaResult.distribuicao = typeof _atual.distribuicao_causas === 'string'
          ? JSON.parse(_atual.distribuicao_causas)
          : _atual.distribuicao_causas;
        } catch {}
      }
    }

    const cmCausa = document.getElementById('wiz-cm-causa');
    if (cmCausa) cmCausa.textContent = _causaResult.causa_principal || '—';
    const cmCausaPct = document.getElementById('wiz-cm-causa-pct');
    const causaConf = parseFloat(_causaResult.confianca) * 100;
    if (cmCausaPct) cmCausaPct.textContent = (isNaN(causaConf) ? 0 : causaConf).toFixed(0) + '%';

    const fatEl = document.getElementById('wiz-cm-fatores');
    const fatores = Array.isArray(_causaResult.fatores_ativos) ? _causaResult.fatores_ativos : [];
    if (fatEl) fatEl.textContent = fatores.length > 0
      ? `Integração com dados urbanos: ${fatores.join(', ')}`
      : 'Integração com dados urbanos: nenhum fator ativo';

    // Barras de causa
    const causasList = document.getElementById('wiz-causas-list');
    if (causasList && _causaResult.distribuicao) {
      const sorted = Object.entries(_causaResult.distribuicao).sort((a, b) => b[1] - a[1]);
      causasList.innerHTML = sorted.map(([causa, prob]) => `
        <div class="cm-causa-bar-item">
          <span class="cm-causa-bar-item__name">${causa}</span>
          <div class="cm-causa-bar-item__bar">
            <div class="cm-causa-bar-item__fill" style="width:${(prob*100).toFixed(0)}%"></div>
          </div>
          <span class="cm-causa-bar-item__pct">${(prob*100).toFixed(0)}%</span>
        </div>
      `).join('');
    }

    // Donut chart
    _renderWizChart(_causaResult.distribuicao || {});
  }

  function _renderWizChart(dist) {
    const canvas = document.getElementById('wiz-donut-chart');
    if (!canvas) return;
    const labels = Object.keys(dist);
    const values = Object.values(dist).map(v => Math.round(v * 100));
    if (_wizChart) { _wizChart.destroy(); _wizChart = null; }
    if (!labels.length) return;
    _wizChart = new Chart(canvas, {
      type: 'doughnut',
      data: { labels, datasets: [{ data: values, backgroundColor: CHART_COLORS.slice(0, labels.length), borderWidth: 0, hoverOffset: 4 }] },
      options: {
        responsive: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${ctx.label}: ${ctx.raw}%` } } },
        cutout: '60%',
      },
    });
  }

  // ── Reiniciar ────────────────────────────────────────────────────────────

  function reiniciar() {
    _atual         = null;
    _respostaUser  = null;
    _causaResult   = null;

    // Replenish pool if empty
    if (_pool.length === 0) {
      _vistas = 0;
      _refillPool();
    }

    _updateCounter();

    const player = document.getElementById('wiz-clip-player');
    if (player) { player.src = ''; player.load(); }

    const btnProx = document.getElementById('wiz-btn-proxima');
    if (btnProx) {
      const remaining = _pool.length;
      btnProx.textContent = remaining > 0 ? '🎲  Próxima ocorrência' : '🔄  Reiniciar sessão';
    }

    irParaStep(1);
  }

  return { onEnter, sortearEIniciar, selecionarResposta, irParaStep, reiniciar };
})();


/* ══════════════════════════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  ThemeModule.init();
  NavModule.init();
  MonitorModule.init();

  // Refresh chart colors on theme toggle
  document.getElementById('btn-dark-toggle')?.addEventListener('click', () => {
    RelatorioModule.refresh();
  });
});
