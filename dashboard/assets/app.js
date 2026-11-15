(function () {
  "use strict";

  const DATA = window.ASFI_DATA;
  const ROOT = document.documentElement;

  if (!DATA || !DATA.bancos || !DATA.series) {
    document.body.innerHTML = '<main style="padding:120px 24px;font-family:Inter,sans-serif;color:#eaf0fb"><h1>No se pudo cargar data.js</h1><p>Verifique que el archivo dashboard/data.js exista junto a index.html.</p></main>';
    return;
  }

  const $ = (id) => document.getElementById(id);
  const state = {
    banco: DATA.bancos[0].id,
    indicador: DATA.indicadores_meta[0].id,
    chartTab: "serie",
    tema: "dark",
    sev: "todas",
    query: "",
    onlyBank: false,
    alertLimit: 60,
    highlightedMonth: null,
    horizon: 2,
    motion: false
  };

  const charts = {};
  const bankById = Object.fromEntries(DATA.bancos.map((b) => [b.id, b]));
  const indById = Object.fromEntries(DATA.indicadores_meta.map((i) => [i.id, i]));
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const STATUS = {
    verde: { label: "Verde", tone: "ok" },
    amarillo: { label: "Amarillo", tone: "warn" },
    naranja: { label: "Naranja", tone: "warn" },
    rojo: { label: "Rojo", tone: "bad" }
  };
  const SEVERIDAD = {
    critica: { label: "Crítica", cls: "sev-critica", z: "critical" },
    alerta: { label: "Alerta", cls: "sev-alerta", z: "alert" },
    vigilancia: { label: "Vigilancia", cls: "sev-vigilancia", z: "watch" }
  };
  const SENALES = {
    racha_deterioro: "Racha",
    fuera_banda_95: "Fuera IC95",
    residuo_z_2: "|z|>2",
    residuo_z_3: "|z|>3",
    cusum: "CUSUM",
    salto_estado: "Salto Markov"
  };
  const HORIZONTES = [1, 2, 3, 6, 12];
  const nfCache = {};

  function nf(d) {
    const key = String(d);
    if (!nfCache[key]) {
      nfCache[key] = new Intl.NumberFormat("es-BO", {
        minimumFractionDigits: d,
        maximumFractionDigits: d
      });
    }
    return nfCache[key];
  }

  function num(value, d = 2) {
    const v = Number(value);
    return Number.isFinite(v) ? nf(d).format(v) : "—";
  }

  function pct(value, d = 2) {
    const v = Number(value);
    return Number.isFinite(v) ? `${nf(d).format(v)} %` : "—";
  }

  function pText(value) {
    const v = Number(value);
    if (!Number.isFinite(v)) return "—";
    if (v < 0.001) return "< 0,001";
    return nf(3).format(v);
  }

  function signed(value, d = 2) {
    const v = Number(value);
    if (!Number.isFinite(v)) return "—";
    return `${v > 0 ? "+" : ""}${nf(d).format(v)}`;
  }

  function esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    }[ch]));
  }

  function cssVar(name) {
    return getComputedStyle(ROOT).getPropertyValue(name).trim();
  }

  function themeColors() {
    return {
      text: cssVar("--text"),
      soft: cssVar("--text-soft"),
      muted: cssVar("--muted"),
      grid: cssVar("--line"),
      line: cssVar("--line-strong"),
      accent: cssVar("--accent"),
      accent2: cssVar("--accent-2"),
      green: cssVar("--green"),
      yellow: cssVar("--yellow"),
      orange: cssVar("--orange"),
      red: cssVar("--red"),
      blue: cssVar("--blue"),
      surface: cssVar("--surface-solid")
    };
  }

  function bank() {
    return bankById[state.banco];
  }

  function ind() {
    return indById[state.indicador];
  }

  function serie() {
    return DATA.series[state.banco] && DATA.series[state.banco][state.indicador];
  }

  function statusBadge(semaforo) {
    const key = STATUS[semaforo] ? semaforo : "verde";
    return `<span class="status-badge status-${key}"><i class="status-dot"></i>${STATUS[key].label}</span>`;
  }

  function setBadge(el, text, tone) {
    if (!el) return;
    el.className = `badge ${tone || ""}`.trim();
    el.textContent = text;
  }

  function signalLabel(signal) {
    return SENALES[signal] || String(signal).replace(/_/g, " ");
  }

  function orderText(order) {
    return Array.isArray(order) ? `(${order.join(",")})` : "—";
  }

  function seasonText(order) {
    if (!Array.isArray(order)) return "—";
    return `(${order[0]},${order[1]},${order[2]})₁₂`;
  }

  function storageGet(key) {
    try {
      return window.localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  function storageSet(key, value) {
    try {
      window.localStorage.setItem(key, value);
    } catch (error) {
      return;
    }
  }

  function applyTheme(theme) {
    state.tema = theme === "light" ? "light" : "dark";
    ROOT.setAttribute("data-theme", state.tema);
    storageSet("asfi-theme", state.tema);
    const btn = $("theme-toggle");
    if (btn) btn.setAttribute("aria-pressed", state.tema === "light" ? "true" : "false");
  }

  function setAnimated(el, value, formatter) {
    if (!el) return;
    const numeric = Number(value);
    const prev = Number(el.dataset.value);
    if (!Number.isFinite(numeric)) {
      el.textContent = "—";
      return;
    }
    el.dataset.value = String(numeric);
    const paint = (v) => {
      el.innerHTML = formatter(v);
    };
    if (!state.motion || reducedMotion || !Number.isFinite(prev) || prev === numeric) {
      paint(numeric);
      return;
    }
    const lib = window.MotionLib;
    if (lib) {
      lib.animate(prev, numeric, {
        duration: 0.55,
        easing: [0.22, 1, 0.36, 1],
        onUpdate: paint
      });
      return;
    }
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / 550);
      const eased = 1 - Math.pow(1 - t, 3);
      paint(prev + (numeric - prev) * eased);
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function movePill(container, pill, active) {
    if (!container || !pill || !active) return;
    const c = container.getBoundingClientRect();
    const b = active.getBoundingClientRect();
    pill.style.width = `${b.width}px`;
    pill.style.transform = `translateX(${b.left - c.left - 4}px)`;
  }

  function syncPills() {
    const chartTabs = $("chart-tabs");
    movePill(chartTabs, $("chart-pill"), chartTabs && chartTabs.querySelector(".seg-btn.active"));
  }

  function populateSelects() {
    const bankSelect = $("bank-select");
    const indSelect = $("indicator-select");
    bankSelect.innerHTML = DATA.bancos.map((b) => `<option value="${esc(b.id)}">${esc(b.nombre)}</option>`).join("");
    indSelect.innerHTML = DATA.indicadores_meta.map((i) => `<option value="${esc(i.id)}">${esc(i.nombre)}</option>`).join("");
    bankSelect.value = state.banco;
    indSelect.value = state.indicador;
  }

  function renderMeta() {
    const meta = DATA.meta;
    $("meta-source").textContent = meta.fuente || "ASFI Bolivia";
    $("meta-range").textContent = `${meta.rango_fechas[0]} → ${meta.rango_fechas[1]}`;
    $("meta-obs").textContent = num(meta.total_observaciones, 0);
    $("meta-mode").innerHTML = `Modo <strong>${meta.modo_demo ? "DEMO" : "REAL"}</strong>`;
    if (meta.modo_demo) {
      document.body.classList.add("demo-on");
      $("demo-banner").classList.remove("hidden");
    }
  }

  function renderBankCards() {
    const grid = $("bank-grid");
    const ordered = DATA.bancos.slice().sort((a, b) => b.score_anomalia - a.score_anomalia);
    grid.innerHTML = ordered.map((b) => {
      const last = DATA.series[b.id] && DATA.series[b.id].mora
        ? DATA.series[b.id].mora.observado[DATA.series[b.id].mora.observado.length - 1]
        : null;
      const pulse = b.semaforo === "rojo" || b.semaforo === "naranja" ? " pulse" : "";
      return `
        <article class="bank-card${pulse}" data-bank="${esc(b.id)}" data-status="${esc(b.semaforo)}" tabindex="0" role="button" aria-label="Seleccionar ${esc(b.nombre)}">
          <div class="bank-top">
            <div>
              <h3 class="bank-name">${esc(b.nombre)}</h3>
              <p class="bank-meta">${esc(b.id.toUpperCase())} · ${esc(b.tipo)}</p>
            </div>
            ${statusBadge(b.semaforo)}
          </div>
          <div class="spark-wrap"><canvas id="spark-${esc(b.id)}"></canvas></div>
          <div class="bank-foot">
            <span>Mora final <strong>${last === null ? "—" : pct(last)}</strong></span>
            <span class="bank-score">score <strong>${num(b.score_anomalia)}</strong></span>
          </div>
        </article>`;
    }).join("");

    if (!window.Chart) return;
    const colors = themeColors();
    ordered.forEach((b) => {
      const canvas = $(`spark-${b.id}`);
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      const gradient = ctx.createLinearGradient(0, 0, 0, 48);
      const lineColor = b.semaforo === "rojo" ? colors.red : b.semaforo === "naranja" ? colors.orange : b.semaforo === "amarillo" ? colors.yellow : colors.green;
      gradient.addColorStop(0, `${lineColor}44`);
      gradient.addColorStop(1, `${lineColor}00`);
      charts[`spark-${b.id}`] = new window.Chart(ctx, {
        type: "line",
        data: {
          labels: b.sparkline_mora.map((_, index) => index),
          datasets: [{
            data: b.sparkline_mora,
            borderColor: lineColor,
            backgroundColor: gradient,
            borderWidth: 1.8,
            pointRadius: 0,
            fill: true,
            tension: 0.36
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: 0 },
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: {
            x: { display: false },
            y: { display: false }
          },
          layout: { padding: { top: 4, bottom: 2, left: 0, right: 0 } }
        }
      });
    });
  }

  function updateBankActive() {
    document.querySelectorAll("[data-bank]").forEach((card) => {
      const active = card.getAttribute("data-bank") === state.banco;
      card.classList.toggle("active", active);
      card.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function renderHero() {
    const b = bank();
    const s = serie();
    const mora = DATA.series[state.banco].mora;
    const lastMora = mora ? mora.observado[mora.observado.length - 1] : null;
    const last = s && s.observado.length ? s.observado[s.observado.length - 1] : null;
    $("hero-bank").textContent = b.nombre;
    $("hero-sub").textContent = `${b.id.toUpperCase()} · ${b.tipo} · ${ind().nombre}`;
    $("hero-status").innerHTML = statusBadge(b.semaforo);
    $("hero-coverage").textContent = `${num(b.cobertura_meses, 0)} meses`;
    $("hero-mora").textContent = lastMora === null ? "—" : pct(lastMora);
    setAnimated($("hero-score"), b.score_anomalia, (v) => num(v));
    $("hero-score-track").style.width = `${Math.min(100, (Number(b.score_anomalia) / 5) * 100)}%`;
    $("hero-summary").textContent = last === null
      ? "No hay observaciones suficientes para este indicador."
      : `Último dato de ${ind().nombre.toLowerCase()}: ${pct(last)}. Semáforo ${STATUS[b.semaforo].label.toLowerCase()} y ${num(b.cobertura_meses, 0)} meses continuos de cobertura.`;
  }

  function renderKpis() {
    const b = bank();
    const s = serie();
    const indActual = ind();
    const sorted = DATA.bancos.slice().sort((a, c) => c.score_anomalia - a.score_anomalia);
    const rank = sorted.findIndex((x) => x.id === b.id) + 1;
    const last = s.observado[s.observado.length - 1];
    const forecast = s.pronostico.media;
    const f6 = forecast.slice(0, 6).reduce((acc, v) => acc + v, 0) / Math.min(6, forecast.length);
    const f6inf = s.pronostico.ic95_inf[Math.min(5, s.pronostico.ic95_inf.length - 1)];
    const f6sup = s.pronostico.ic95_sup[Math.min(5, s.pronostico.ic95_sup.length - 1)];
    const bt = s.backtest;
    const delta = bt.rmse_naive ? ((bt.rmse_naive - bt.rmse_modelo) / bt.rmse_naive) * 100 : NaN;

    setAnimated($("kpi-score"), b.score_anomalia, (v) => num(v));
    $("kpi-score-rank").textContent = `Puesto ${rank} / ${DATA.bancos.length}`;
    $("kpi-score-sub").textContent = `Semáforo ${STATUS[b.semaforo].label.toLowerCase()} · ranking por score`;

    setAnimated($("kpi-current"), last, (v) => `${num(v)}<small>%</small>`);
    $("kpi-current-label").textContent = indActual.nombre;
    $("kpi-current-sub").textContent = `Riesgo ${indActual.direccion_riesgo} · ${b.nombre}`;

    setAnimated($("kpi-forecast"), f6, (v) => `${num(v)}<small>%</small>`);
    $("kpi-forecast-sub").textContent = `IC95 a 6m: ${num(f6inf)} – ${num(f6sup)} %`;

    setAnimated($("kpi-coverage"), b.cobertura_meses, (v) => `${num(v, 0)}`);
    $("kpi-coverage-sub").textContent = `${DATA.meta.rango_fechas[0]} a ${DATA.meta.rango_fechas[1]} · serie continua`;

    setAnimated($("kpi-backtest"), delta, (v) => `${signed(v, 1)}<small>%</small>`);
    $("kpi-backtest-sub").textContent = `RMSE ${num(bt.rmse_modelo, 3)} vs ${num(bt.rmse_naive, 3)} · ${bt.supera_baseline ? "supera" : "no supera"} a Naive`;
  }

  function renderSeriesFacts() {
    const s = serie();
    const b = bank();
    $("series-facts-title").textContent = `${ind().nombre} · ${b.id.toUpperCase()}`;
    $("series-facts-text").textContent = `Serie mensual en porcentaje. Dirección de riesgo ${s.direccion_riesgo}. Se modelaron ${num(s.sarima.modelos_evaluados, 0)} combinaciones y se reporta el top 3 por AIC.`;
    $("fact-mean").textContent = num(s.momentos.media);
    $("fact-var").textContent = num(s.momentos.varianza, 3);
    $("fact-obs").textContent = num(s.observado.length, 0);
    $("fact-models").textContent = num(s.sarima.modelos_evaluados, 0);
  }

  function renderChartHeader() {
    const b = bank();
    const s = serie();
    $("chart-title").textContent = `${ind().nombre} · ${b.nombre}`;
    $("chart-sub").textContent = `${s.observado.length} observaciones · ${s.pronostico.fechas.length} meses de pronóstico · unidad: %`;
    $("analysis-sub").textContent = `${b.id.toUpperCase()} · ${ind().nombre} · ${s.fechas[0]} → ${s.pronostico.fechas[s.pronostico.fechas.length - 1]}`;
  }

  function renderInterpretation() {
    const s = serie();
    const b = bank();
    const e = s.estacionariedad;
    const sa = s.sarima;
    const bt = s.backtest;
    $("how-read").textContent = "La línea sólida es el dato observado; la punteada muestra el ajuste dentro de la muestra. Las bandas 80 % y 95 % son intervalos de predicción: describen incertidumbre del proceso estimado, no certezas.";
    $("finding").textContent = `${b.id.toUpperCase()} · ${ind().nombre}: ADF p = ${pText(e.adf_pval)} y KPSS p = ${pText(e.kpss_pval)}, veredicto “${e.veredicto}”. El SARIMA seleccionado es ${orderText(sa.orden)}${seasonText(sa.orden_estacional)} con AIC ${num(sa.aic, 2)}. En el backtest, RMSE = ${num(bt.rmse_modelo, 3)} frente a Naive = ${num(bt.rmse_naive, 3)}; ${bt.supera_baseline ? "supera" : "no supera"} al baseline.`;
    $("limitation").textContent = "La banda de un paso usa la desviación estándar de los residuos como aproximación gaussiana. Un p-valor no mide la probabilidad de quiebra ni la magnitud económica del riesgo; la muestra de 84 meses limita la potencia de algunas pruebas.";
  }

  function renderCurrent() {
    $("bank-select").value = state.banco;
    $("indicator-select").value = state.indicador;
    renderHero();
    renderKpis();
    renderSeriesFacts();
    renderChartHeader();
    renderInterpretation();
    updateBankActive();
    if (typeof renderSeriesChart === "function") renderSeriesChart();
    if (typeof renderResidualChart === "function") renderResidualChart();
    if (typeof renderDiagnosticCharts === "function") renderDiagnosticCharts();
    if (typeof renderDiagnosticCards === "function") renderDiagnosticCards();
    if (typeof renderMarkov === "function") renderMarkov();
    if (typeof renderAlerts === "function") renderAlerts();
    syncPills();
  }

  function switchChartTab(tab) {
    state.chartTab = tab;
    document.querySelectorAll("[data-chart-tab]").forEach((btn) => {
      const active = btn.getAttribute("data-chart-tab") === tab;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-selected", active ? "true" : "false");
    });
    $("stage-serie").classList.toggle("hidden", tab !== "serie");
    $("stage-residuos").classList.toggle("hidden", tab !== "residuos");
    $("stage-diagnostico").classList.toggle("hidden", tab !== "diagnostico");
    requestAnimationFrame(syncPills);
  }

  applyTheme(storageGet("asfi-theme") || "dark");
  setupChartDefaults();
  populateSelects();
  renderMeta();
  renderBankCards();
  renderCurrent();
  window.ASFI_UI = { state, charts, DATA, num, pct, pText, esc, themeColors, setBadge, statusBadge, switchChartTab };
  function setupChartDefaults() {
    if (!window.Chart) return;
    const c = themeColors();
    window.Chart.defaults.font.family = "Inter, system-ui, sans-serif";
    window.Chart.defaults.font.size = 10;
    window.Chart.defaults.color = c.muted;
    window.Chart.defaults.borderColor = c.grid;
    window.Chart.register({
      id: "asfiHighlightMonth",
      afterDatasetsDraw(chart) {
        if (chart.canvas.id !== "chart-serie" || !state.highlightedMonth) return;
        const index = chart.data.labels.indexOf(state.highlightedMonth);
        if (index < 0) return;
        const x = chart.scales.x.getPixelForValue(index);
        if (!Number.isFinite(x)) return;
        const area = chart.chartArea;
        const ctx = chart.ctx;
        ctx.save();
        ctx.beginPath();
        ctx.setLineDash([4, 4]);
        ctx.lineWidth = 1;
        ctx.strokeStyle = "rgba(103, 232, 249, 0.72)";
        ctx.moveTo(x, area.top);
        ctx.lineTo(x, area.bottom);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.font = "600 9px 'JetBrains Mono', monospace";
        ctx.fillStyle = "rgba(103, 232, 249, 0.95)";
        ctx.fillText(state.highlightedMonth, Math.min(x + 5, area.right - 48), area.top + 11);
        ctx.restore();
      }
    });
  }

  function baseOptions(yTitle, extra) {
    const c = themeColors();
    return Object.assign({
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: state.motion && !reducedMotion ? 480 : 0 },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: c.surface,
          titleColor: c.text,
          bodyColor: c.soft,
          borderColor: c.line,
          borderWidth: 1,
          padding: 9,
          cornerRadius: 8,
          titleFont: { family: "Inter", size: 10, weight: "600" },
          bodyFont: { family: "JetBrains Mono", size: 9 },
          displayColors: true,
          boxWidth: 7,
          boxHeight: 7
        }
      },
      scales: {
        x: {
          grid: { color: c.grid, drawTicks: false },
          border: { display: false },
          ticks: {
            color: c.muted,
            font: { family: "JetBrains Mono", size: 9 },
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 12
          }
        },
        y: {
          grid: { color: c.grid, drawTicks: false },
          border: { display: false },
          ticks: {
            color: c.muted,
            font: { family: "JetBrains Mono", size: 9 },
            padding: 5
          },
          title: yTitle ? {
            display: true,
            text: yTitle,
            color: c.muted,
            font: { size: 9, family: "JetBrains Mono" }
          } : { display: false }
        }
      }
    }, extra || {});
  }

  function bandDatasets(s, n, total, c) {
    return [
      {
        label: "IC 95 % inferior",
        data: [...Array(n).fill(null), ...s.pronostico.ic95_inf],
        borderColor: "transparent",
        backgroundColor: "rgba(96, 165, 250, 0.10)",
        fill: "+1",
        pointRadius: 0,
        pointHitRadius: 0,
        borderWidth: 0,
        spanGaps: false
      },
      {
        label: "IC 95 % superior",
        data: [...Array(n).fill(null), ...s.pronostico.ic95_sup],
        borderColor: "transparent",
        backgroundColor: "transparent",
        fill: false,
        pointRadius: 0,
        pointHitRadius: 0,
        borderWidth: 0,
        spanGaps: false
      },
      {
        label: "IC 80 % inferior",
        data: [...Array(n).fill(null), ...s.pronostico.ic80_inf],
        borderColor: "transparent",
        backgroundColor: "rgba(103, 232, 249, 0.10)",
        fill: "+1",
        pointRadius: 0,
        pointHitRadius: 0,
        borderWidth: 0,
        spanGaps: false
      },
      {
        label: "IC 80 % superior",
        data: [...Array(n).fill(null), ...s.pronostico.ic80_sup],
        borderColor: "transparent",
        backgroundColor: "transparent",
        fill: false,
        pointRadius: 0,
        pointHitRadius: 0,
        borderWidth: 0,
        spanGaps: false
      },
      {
        label: "Observado",
        data: [...s.observado, ...Array(total - n).fill(null)],
        borderColor: c.accent,
        backgroundColor: c.accent,
        borderWidth: 2.1,
        pointRadius: s.fechas.map((f) => f === state.highlightedMonth ? 4.5 : 0),
        pointHoverRadius: 5,
        pointBackgroundColor: c.accent,
        tension: 0.22,
        fill: false,
        spanGaps: false
      },
      {
        label: "Ajuste SARIMA",
        data: [...s.ajuste_in_sample, ...Array(total - n).fill(null)],
        borderColor: c.accent2,
        backgroundColor: c.accent2,
        borderWidth: 1.3,
        borderDash: [4, 4],
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.18,
        fill: false,
        spanGaps: false
      },
      {
        label: "Pronóstico",
        data: [...Array(n).fill(null), ...s.pronostico.media],
        borderColor: c.yellow,
        backgroundColor: c.yellow,
        borderWidth: 2,
        borderDash: [6, 4],
        pointRadius: 2,
        pointHoverRadius: 4,
        pointBackgroundColor: c.yellow,
        tension: 0.18,
        fill: false,
        spanGaps: false
      }
    ];
  }

  function renderSeriesChart() {
    if (!window.Chart) return;
    const s = serie();
    const c = themeColors();
    const n = s.fechas.length;
    const labels = [...s.fechas, ...s.pronostico.fechas];
    const total = labels.length;
    const datasets = bandDatasets(s, n, total, c);
    const options = baseOptions("%");
    options.plugins.tooltip.callbacks = {
      title(items) {
        return items.length ? items[0].label : "";
      },
      label(ctx) {
        const value = ctx.parsed.y;
        if (value === null || !Number.isFinite(Number(value))) return null;
        return `${ctx.dataset.label}: ${num(value)} %`;
      }
    };
    if (!charts.serie) {
      charts.serie = new window.Chart($("chart-serie"), {
        type: "line",
        data: { labels, datasets },
        options
      });
      return;
    }
    charts.serie.data.labels = labels;
    charts.serie.data.datasets = datasets;
    charts.serie.options = options;
    charts.serie.update("active");
  }

  function renderResidualChart() {
    if (!window.Chart) return;
    const s = serie();
    const c = themeColors();
    const z = s.residuos_estandarizados;
    const pointColors = z.map((v) => Math.abs(v) > 3 ? c.red : Math.abs(v) > 2 ? c.orange : c.accent);
    const datasets = [
      {
        label: "Banda ±2",
        data: Array(z.length).fill(2),
        borderColor: "rgba(251, 146, 60, 0.42)",
        borderDash: [4, 5],
        borderWidth: 1,
        pointRadius: 0,
        fill: false
      },
      {
        label: "Banda −2",
        data: Array(z.length).fill(-2),
        borderColor: "rgba(251, 146, 60, 0.42)",
        borderDash: [4, 5],
        borderWidth: 1,
        pointRadius: 0,
        fill: false
      },
      {
        label: "Residuo estandarizado",
        data: z,
        borderColor: c.accent,
        backgroundColor: c.accent,
        borderWidth: 1.6,
        pointRadius: s.fechas.map((f) => f === state.highlightedMonth ? 4.5 : 2.1),
        pointHoverRadius: 5,
        pointBackgroundColor: pointColors,
        tension: 0.16,
        fill: false
      }
    ];
    const options = baseOptions("z");
    options.plugins.tooltip.callbacks = {
      label(ctx) {
        const value = ctx.parsed.y;
        if (value === null || !Number.isFinite(Number(value))) return null;
        return `${ctx.dataset.label}: ${signed(value, 2)}`;
      }
    };
    if (!charts.residuos) {
      charts.residuos = new window.Chart($("chart-residuos"), {
        type: "line",
        data: { labels: s.fechas, datasets },
        options
      });
      return;
    }
    charts.residuos.data.labels = s.fechas;
    charts.residuos.data.datasets = datasets;
    charts.residuos.options = options;
    charts.residuos.update("active");
  }

  function renderAcfChart(id, original, differentiated, title) {
    if (!window.Chart) return;
    const c = themeColors();
    const maxLen = Math.max(original.length, differentiated.length);
    const labels = Array.from({ length: maxLen }, (_, index) => index);
    const datasets = [
      {
        label: "Original",
        data: original,
        borderColor: c.accent,
        backgroundColor: c.accent,
        borderWidth: 1.7,
        pointRadius: 2.2,
        pointHoverRadius: 4,
        tension: 0
      },
      {
        label: "Diferenciada",
        data: differentiated,
        borderColor: c.accent2,
        backgroundColor: c.accent2,
        borderWidth: 1.3,
        pointRadius: 1.7,
        pointHoverRadius: 4,
        tension: 0
      }
    ];
    const options = baseOptions(title, {
      scales: {
        x: {
          grid: { color: c.grid, drawTicks: false },
          border: { display: false },
          ticks: { color: c.muted, font: { family: "JetBrains Mono", size: 8 }, maxTicksLimit: 8 }
        },
        y: {
          min: -1.05,
          max: 1.05,
          grid: {
            color: (ctx) => ctx.tick.value === 0 ? c.line : c.grid,
            drawTicks: false
          },
          border: { display: false },
          ticks: { color: c.muted, font: { family: "JetBrains Mono", size: 8 }, maxTicksLimit: 6 }
        }
      }
    });
    options.plugins.tooltip.callbacks = {
      label(ctx) {
        return `${ctx.dataset.label} · rezago ${ctx.label}: ${num(ctx.parsed.y, 3)}`;
      }
    };
    const key = id.replace("chart-", "");
    if (!charts[key]) {
      charts[key] = new window.Chart($(id), {
        type: "line",
        data: { labels, datasets },
        options
      });
      return;
    }
    charts[key].data.labels = labels;
    charts[key].data.datasets = datasets;
    charts[key].options = options;
    charts[key].update("active");
  }

  function renderQqChart() {
    if (!window.Chart) return;
    const s = serie();
    const c = themeColors();
    const theoretical = s.sarima.qq_teorico;
    const sample = s.sarima.qq_muestral;
    const points = theoretical.map((x, index) => ({ x, y: sample[index] }));
    const all = [...theoretical, ...sample];
    const min = Math.min(...all);
    const max = Math.max(...all);
    const datasets = [
      {
        label: "Cuantiles",
        data: points,
        borderColor: c.accent,
        backgroundColor: "rgba(103, 232, 249, 0.72)",
        pointRadius: 2.2,
        pointHoverRadius: 4,
        showLine: false
      },
      {
        label: "Referencia 45°",
        data: [{ x: min, y: min }, { x: max, y: max }],
        borderColor: "rgba(139, 92, 246, 0.72)",
        borderDash: [5, 4],
        borderWidth: 1.2,
        pointRadius: 0,
        showLine: true
      }
    ];
    const options = baseOptions("", {
      interaction: { mode: "nearest", intersect: true },
      scales: {
        x: {
          type: "linear",
          grid: { color: c.grid, drawTicks: false },
          border: { display: false },
          ticks: { color: c.muted, font: { family: "JetBrains Mono", size: 8 }, maxTicksLimit: 5 },
          title: { display: true, text: "teórico", color: c.muted, font: { size: 8 } }
        },
        y: {
          type: "linear",
          grid: { color: c.grid, drawTicks: false },
          border: { display: false },
          ticks: { color: c.muted, font: { family: "JetBrains Mono", size: 8 }, maxTicksLimit: 5 },
          title: { display: true, text: "muestral", color: c.muted, font: { size: 8 } }
        }
      }
    });
    options.plugins.tooltip.callbacks = {
      label(ctx) {
        return `teórico ${num(ctx.parsed.x, 2)} · muestral ${num(ctx.parsed.y, 2)}`;
      }
    };
    if (!charts.qq) {
      charts.qq = new window.Chart($("chart-qq"), {
        type: "scatter",
        data: { datasets },
        options
      });
      return;
    }
    charts.qq.data.datasets = datasets;
    charts.qq.options = options;
    charts.qq.update("active");
  }

  function renderDiagnosticCharts() {
    if (!window.Chart) return;
    const s = serie();
    renderAcfChart("chart-acf", s.estacionariedad.acf_orig, s.estacionariedad.acf_diff, "ACF");
    renderAcfChart("chart-pacf", s.estacionariedad.pacf_orig, s.estacionariedad.pacf_diff, "PACF");
    renderQqChart();
  }

  function refreshChartTheme() {
    if (!window.Chart) return;
    const c = themeColors();
    window.Chart.defaults.color = c.muted;
    window.Chart.defaults.borderColor = c.grid;
    renderSeriesChart();
    renderResidualChart();
    renderDiagnosticCharts();
  }

  function renderDiagnosticCards() {
    const s = serie();
    const e = s.estacionariedad;
    const sa = s.sarima;
    const ols = s.regresion_ols;
    const bt = s.backtest;
    const verdictTone = e.veredicto === "Estacionaria" ? "ok" : e.veredicto === "Inconclusa" ? "warn" : e.veredicto === "Estacionaria en Tendencia" ? "warn" : "bad";
    setBadge($("diag-verdict"), e.veredicto, verdictTone);
    $("diag-adf").textContent = pText(e.adf_pval);
    $("diag-kpss").textContent = pText(e.kpss_pval);
    $("diag-d").textContent = num(e.d_recomendado, 0);
    $("diag-ds").textContent = num(e.D_estacional, 0);
    $("diag-note").textContent = e.veredicto === "Inconclusa"
      ? "ADF y KPSS no permiten una conclusión única; se documenta la discrepancia sin forzar el diagnóstico."
      : `Lectura conjunta ADF + KPSS: ${e.veredicto.toLowerCase()}. La diferenciación sugerida usa d = ${e.d_recomendado} y D = ${e.D_estacional}.`;

    setBadge($("ols-badge"), ols.dw_stat < 1.5 ? "DW bajo" : "DW ok", ols.dw_stat < 1.5 ? "warn" : "ok");
    $("ols-r2").textContent = num(ols.r2_adj, 3);
    $("ols-dw").textContent = num(ols.dw_stat, 2);
    $("ols-lb").textContent = pText(ols.ljung_box_pval);
    $("ols-arch").textContent = pText(ols.arch_lm_pval);
    const trend = ols.tendencia.find((t) => t.termino === "t");
    const curvature = ols.tendencia.find((t) => t.termino === "t2");
    $("ols-trend").textContent = trend
      ? `t ${signed(trend.coef, 3)} · t² ${curvature ? signed(curvature.coef, 5) : "—"}`
      : "—";

    setBadge($("sarima-badge"), `AIC ${num(sa.aic, 1)}`, "ok");
    $("sarima-order").textContent = orderText(sa.orden);
    $("sarima-seasonal").textContent = seasonText(sa.orden_estacional);
    $("sarima-aic").textContent = num(sa.aic, 3);
    $("sarima-bic").textContent = num(sa.bic, 3);
    $("sarima-lb").textContent = pText(sa.ljung_box_pval);
    $("sarima-top3").innerHTML = sa.top3_modelos.map((m) => `
      <div class="top3-row">
        <span>${esc(orderText(m.orden))}${esc(seasonText(m.orden_estacional))}</span>
        <span>AIC ${num(m.aic, 1)}</span>
        <span>BIC ${num(m.bic, 1)}</span>
      </div>`).join("");

    setBadge($("bt-badge"), bt.supera_baseline ? "Supera Naive" : "No supera Naive", bt.supera_baseline ? "ok" : "bad");
    $("bt-rmse").textContent = num(bt.rmse_modelo, 3);
    $("bt-mae").textContent = num(bt.mae_modelo, 3);
    $("bt-smape").textContent = `${num(bt.smape_modelo, 2)} %`;
    $("bt-naive").textContent = num(bt.rmse_naive, 3);
    $("bt-snaive").textContent = num(bt.rmse_snaive, 3);
    const delta = bt.rmse_naive ? ((bt.rmse_naive - bt.rmse_modelo) / bt.rmse_naive) * 100 : NaN;
    $("bt-note").textContent = bt.supera_baseline
      ? `Mejora de ${num(Math.abs(delta), 1)} % en RMSE frente a Naive sobre ${bt.observaciones_eval} meses fuera de muestra.`
      : `El baseline Naive obtiene ${num(Math.abs(delta), 1)} % menos RMSE; se reporta el resultado sin ocultarlo.`;
  }

  function multiplyMatrices(a, b) {
    return a.map((row, i) => b[0].map((_, j) => row.reduce((acc, value, k) => acc + value * b[k][j], 0)));
  }

  function matrixPower(matrix, power) {
    let result = matrix.map((row, i) => row.map((_, j) => i === j ? 1 : 0));
    let base = matrix;
    let exponent = power;
    while (exponent > 0) {
      if (exponent % 2 === 1) result = multiplyMatrices(result, base);
      base = multiplyMatrices(base, base);
      exponent = Math.floor(exponent / 2);
    }
    return result;
  }

  function renderBars(container, values, labels, criticalIndex) {
    container.innerHTML = values.map((value, index) => {
      const p = Math.max(0, Math.min(1, Number(value)));
      const critical = index === criticalIndex ? " critical" : "";
      return `
        <div class="bar-row${critical}">
          <span>${esc(labels[index])}</span>
          <div class="bar-track"><div class="bar-fill" style="width:${(p * 100).toFixed(1)}%"></div></div>
          <strong>${num(p * 100, 1)} %</strong>
        </div>`;
    }).join("");
  }

  function showTooltip(text, x, y) {
    const tip = $("tooltip");
    if (!tip) return;
    tip.textContent = text;
    tip.classList.add("show");
    const width = tip.offsetWidth;
    tip.style.left = `${Math.min(window.innerWidth - width - 12, x + 14)}px`;
    tip.style.top = `${Math.min(window.innerHeight - 70, y + 14)}px`;
  }

  function hideTooltip() {
    const tip = $("tooltip");
    if (tip) tip.classList.remove("show");
  }

  function renderMarkov() {
    const m = DATA.markov.por_banco[state.banco];
    if (!m) return;
    const states = DATA.markov.estados;
    const current = Number(m.estado_actual);
    const horizon = HORIZONTES[state.horizon];
    const powered = matrixPower(m.matriz_transicion, horizon);
    const pCritical = powered[current][3];
    const p3 = m.prob_critico_h.m3;
    $("matrix-title").textContent = `Matriz de transición · ${bank().id.toUpperCase()}`;
    setBadge($("markov-prop"), m.cumple_propiedad_markov ? "Markov orden 1" : "Revisar orden", m.cumple_propiedad_markov ? "ok" : "warn");
    $("markov-state-note").textContent = `${bank().nombre}. Umbrales de mora: ${DATA.markov.umbrales.map((v) => `${num(v * 100, 1)} %`).join(" / ")}.`;
    $("markov-current").textContent = states[current];
    $("markov-test").textContent = `p = ${pText(m.test_orden_1_vs_2_pval)}`;
    $("markov-ok").textContent = m.cumple_propiedad_markov ? "Sí" : "No";
    $("horizon-label").textContent = `${horizon} ${horizon === 1 ? "mes" : "meses"}`;
    $("markov-aggregate").textContent = `Sistema: π(Crítica) = ${num(DATA.markov.sistema_agregado.dist_estacionaria[3] * 100, 1)} %`;

    const cells = [`<div class="matrix-corner">origen / destino</div>`];
    states.forEach((state) => cells.push(`<div class="matrix-colhead">${esc(state)}</div>`));
    states.forEach((state, i) => {
      cells.push(`<div class="matrix-rowhead">${esc(state)}</div>`);
      states.forEach((target, j) => {
        const value = Number(m.matriz_transicion[i][j]);
        const alpha = Math.min(0.34, value * 0.36);
        const background = j === 3
          ? `rgba(244, 63, 94, ${alpha})`
          : `rgba(103, 232, 249, ${alpha * 0.78})`;
        cells.push(`<div class="matrix-cell" data-i="${i}" data-j="${j}" data-value="${value}" style="background:${background}" role="gridcell" aria-label="${esc(states[i])} a ${esc(target)}: ${num(value * 100, 1)} por ciento">${num(value * 100, 1)}</div>`);
      });
    });
    $("markov-matrix").innerHTML = cells.join("");

    document.querySelectorAll(".matrix-cell").forEach((cell) => {
      const i = Number(cell.dataset.i);
      const j = Number(cell.dataset.j);
      const value = Number(cell.dataset.value);
      cell.addEventListener("mouseenter", (event) => {
        document.querySelectorAll(".matrix-cell").forEach((other) => {
          other.classList.toggle("row-active", Number(other.dataset.i) === i);
          other.classList.toggle("col-active", Number(other.dataset.j) === j);
        });
        showTooltip(`Probabilidad de pasar de ${states[i]} a ${states[j]} el próximo mes: ${num(value * 100, 1)} %.`, event.clientX, event.clientY);
      });
      cell.addEventListener("mousemove", (event) => {
        showTooltip(`Probabilidad de pasar de ${states[i]} a ${states[j]} el próximo mes: ${num(value * 100, 1)} %.`, event.clientX, event.clientY);
      });
      cell.addEventListener("mouseleave", () => {
        document.querySelectorAll(".matrix-cell").forEach((other) => {
          other.classList.remove("row-active", "col-active");
        });
        hideTooltip();
      });
    });

    renderBars($("markov-dist"), m.dist_estacionaria, states, 3);
    renderBars($("markov-crit"), states.map((_, i) => powered[i][3]), states.map((stateName) => `Desde ${stateName}`), current);
    $("side-markov-text").textContent = `Desde el estado actual, la probabilidad de alcanzar Crítica a 3 meses es ${num(p3 * 100, 2)} %. La distribución estacionaria asigna ${num(m.dist_estacionaria[3] * 100, 1)} % a ese estado.`;
    $("side-state").textContent = states[current];
    $("side-crit").textContent = pct(p3 * 100, 2);
  }

  function alertMatches(alert, query, onlyBank) {
    if (onlyBank && alert.banco_id !== state.banco) return false;
    if (!query) return true;
    const b = bankById[alert.banco_id];
    const indicator = indById[alert.indicador_id];
    const haystack = [
      alert.fecha,
      alert.banco_id,
      b ? b.nombre : "",
      alert.indicador_id,
      indicator ? indicator.nombre : "",
      alert.severidad,
      alert.explicacion_clara,
      ...(alert.senales_activadas || []).map(signalLabel)
    ].join(" ").toLowerCase();
    return haystack.includes(query);
  }

  function renderAlerts() {
    const query = state.query.trim().toLowerCase();
    const filtered = DATA.alertas
      .filter((alert) => state.sev === "todas" || alert.severidad === state.sev)
      .filter((alert) => alertMatches(alert, query, state.onlyBank))
      .sort((a, b) => {
        const byDate = String(b.fecha).localeCompare(String(a.fecha));
        if (byDate !== 0) return byDate;
        const ranks = { critica: 3, alerta: 2, vigilancia: 1 };
        return (ranks[b.severidad] || 0) - (ranks[a.severidad] || 0);
      });
    const visible = filtered.slice(0, state.alertLimit);
    $("alert-total").textContent = `${num(filtered.length, 0)} de ${num(DATA.alertas.length, 0)} alertas`;
    $("alert-count").textContent = `Mostrando ${num(visible.length, 0)} de ${num(filtered.length, 0)} resultados · orden: fecha descendente`;
    $("load-more").classList.toggle("hidden", visible.length >= filtered.length);
    if (!visible.length) {
      $("alerts-body").innerHTML = '<tr><td colspan="7" class="empty">No hay alertas con los filtros seleccionados.</td></tr>';
      return;
    }
    $("alerts-body").innerHTML = visible.map((alert) => {
      const b = bankById[alert.banco_id];
      const indicator = indById[alert.indicador_id];
      const sev = SEVERIDAD[alert.severidad] || SEVERIDAD.vigilancia;
      const zClass = Math.abs(alert.z_score) > 3 ? "critical" : Math.abs(alert.z_score) > 2 ? "alert" : "watch";
      const signals = (alert.senales_activadas || []).map((signal) => `<span class="signal">${esc(signalLabel(signal))}</span>`).join("");
      return `
        <tr data-alert-id="${esc(alert.id)}">
          <td class="cell-date">${esc(alert.fecha)}</td>
          <td class="cell-bank">${esc(b ? b.nombre : alert.banco_id)}</td>
          <td>${esc(indicator ? indicator.nombre : alert.indicador_id)}</td>
          <td><span class="sev-chip ${sev.cls}">${sev.label}</span></td>
          <td class="alert-z ${zClass}">${signed(alert.z_score, 2)}</td>
          <td><div class="signal-list">${signals}</div></td>
          <td class="cell-exp" title="${esc(alert.explicacion_clara)}">${esc(alert.explicacion_clara)}</td>
        </tr>`;
    }).join("");
  }

  function showAlertDetail(alert) {
    const b = bankById[alert.banco_id];
    const indicator = indById[alert.indicador_id];
    const sev = SEVERIDAD[alert.severidad] || SEVERIDAD.vigilancia;
    const detail = $("alert-detail");
    detail.classList.remove("hidden");
    detail.innerHTML = `
      <strong>${sev.label} · ${esc(alert.fecha)} · ${esc(b ? b.nombre : alert.banco_id)}</strong><br>
      ${esc(indicator ? indicator.nombre : alert.indicador_id)} · z = ${signed(alert.z_score, 3)}<br>
      ${esc(alert.explicacion_clara)}<br>
      <strong>Señales:</strong> ${esc((alert.senales_activadas || []).map(signalLabel).join(", "))}`;
  }

  function selectBank(id) {
    if (!bankById[id]) return;
    state.banco = id;
    state.highlightedMonth = null;
    state.alertLimit = 60;
    $("alert-detail").classList.add("hidden");
    renderCurrent();
  }

  function selectIndicator(id) {
    if (!indById[id]) return;
    state.indicador = id;
    state.highlightedMonth = null;
    state.alertLimit = 60;
    $("alert-detail").classList.add("hidden");
    renderCurrent();
  }

  function selectAlert(id) {
    const alert = DATA.alertas.find((item) => item.id === id);
    if (!alert) return;
    state.banco = alert.banco_id;
    state.indicador = alert.indicador_id;
    state.highlightedMonth = alert.fecha;
    state.chartTab = "serie";
    switchChartTab("serie");
    renderCurrent();
    showAlertDetail(alert);
    const target = $("analisis");
    if (target) {
      window.setTimeout(() => target.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" }), 90);
    }
    const toast = $("toast");
    toast.textContent = `Mes ${alert.fecha} resaltado en ${bankById[alert.banco_id].nombre}.`;
    toast.classList.add("show");
    window.clearTimeout(selectAlert.timer);
    selectAlert.timer = window.setTimeout(() => toast.classList.remove("show"), 2600);
  }

  function updateProgress() {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const progress = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    const bar = $("reading-progress");
    if (bar) bar.style.width = `${progress * 100}%`;
  }

  function setupMotion() {
    if (state.motionSetup) return;
    if (reducedMotion || !window.MotionLib) {
      state.motion = false;
      return;
    }
    state.motionSetup = true;
    state.motion = true;
    const lib = window.MotionLib;
    const easing = [0.22, 1, 0.36, 1];
    try {
      lib.animate(".hero > *", { opacity: [0, 1], y: [14, 0] }, {
        duration: 0.7,
        delay: lib.stagger ? lib.stagger(0.08) : 0,
        easing
      });
      lib.animate(".kpi-card", { opacity: [0, 1], y: [18, 0] }, {
        duration: 0.6,
        delay: lib.stagger ? lib.stagger(0.06) : 0,
        easing
      });
      lib.animate(".bank-card", { opacity: [0, 1], y: [10, 0] }, {
        duration: 0.45,
        delay: lib.stagger ? lib.stagger(0.025) : 0,
        easing
      });
      if (lib.inView) {
        lib.inView(".section", (info) => {
          const element = info && info.target ? info.target : info;
          if (element) lib.animate(element, { opacity: [0, 1], y: [18, 0] }, { duration: 0.55, easing });
        }, { amount: 0.12 });
      }
    } catch (error) {
      state.motion = false;
    }
    syncPills();
  }

  function openGlossary() {
    const drawer = $("glossary");
    const backdrop = $("glossary-backdrop");
    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    backdrop.classList.add("open");
    document.body.style.overflow = "hidden";
    if (window.renderMathInElement) {
      try {
        window.renderMathInElement($("glossary-body"), {
          delimiters: [
            { left: "\\[", right: "\\]", display: true },
            { left: "\\(", right: "\\)", display: false }
          ],
          throwOnError: false
        });
      } catch (error) {
        return;
      }
    }
  }

  function closeGlossary() {
    const drawer = $("glossary");
    const backdrop = $("glossary-backdrop");
    drawer.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true");
    backdrop.classList.remove("open");
    document.body.style.overflow = "";
    $("glossary-open").focus();
  }

  function setQuery(value, source) {
    state.query = value;
    state.alertLimit = 60;
    if (source !== "dock") $("dock-search").value = value;
    if (source !== "alerts") $("alert-search").value = value;
    renderAlerts();
  }

  function bindEvents() {
    $("bank-select").addEventListener("change", (event) => selectBank(event.target.value));
    $("indicator-select").addEventListener("change", (event) => selectIndicator(event.target.value));

    document.querySelectorAll("[data-chart-tab]").forEach((button) => {
      button.addEventListener("click", () => switchChartTab(button.getAttribute("data-chart-tab")));
    });

    $("bank-grid").addEventListener("click", (event) => {
      const card = event.target.closest("[data-bank]");
      if (card) selectBank(card.getAttribute("data-bank"));
    });

    $("bank-grid").addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const card = event.target.closest("[data-bank]");
      if (card) {
        event.preventDefault();
        selectBank(card.getAttribute("data-bank"));
      }
    });

    $("alert-search").addEventListener("input", (event) => setQuery(event.target.value, "alerts"));
    $("dock-search").addEventListener("input", (event) => setQuery(event.target.value, "dock"));
    $("dock-search").addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        $("alertas").scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
      }
    });

    $("alert-only-bank").addEventListener("change", (event) => {
      state.onlyBank = event.target.checked;
      state.alertLimit = 60;
      renderAlerts();
    });

    $("sev-tabs").addEventListener("click", (event) => {
      const button = event.target.closest("[data-sev]");
      if (!button) return;
      state.sev = button.getAttribute("data-sev");
      state.alertLimit = 60;
      document.querySelectorAll("[data-sev]").forEach((item) => {
        const active = item === button;
        item.classList.toggle("active", active);
        item.setAttribute("aria-selected", active ? "true" : "false");
      });
      renderAlerts();
    });

    $("alerts-body").addEventListener("click", (event) => {
      const row = event.target.closest("[data-alert-id]");
      if (row) selectAlert(row.getAttribute("data-alert-id"));
    });

    $("load-more").addEventListener("click", () => {
      state.alertLimit += 60;
      renderAlerts();
    });

    $("horizon").addEventListener("input", (event) => {
      state.horizon = Number(event.target.value);
      renderMarkov();
    });

    $("theme-toggle").addEventListener("click", () => {
      applyTheme(state.tema === "dark" ? "light" : "dark");
      refreshChartTheme();
      syncPills();
    });

    $("glossary-open").addEventListener("click", openGlossary);
    $("glossary-close").addEventListener("click", closeGlossary);
    $("glossary-backdrop").addEventListener("click", closeGlossary);

    document.addEventListener("keydown", (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        $("dock-search").focus();
        $("dock-search").select();
      }
      if (event.key === "Escape") {
        if ($("glossary").classList.contains("open")) closeGlossary();
        hideTooltip();
      }
    });

    window.addEventListener("resize", syncPills);
    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("motion-ready", setupMotion);
    if (window.MotionLib) setupMotion();
  }

  bindEvents();
  updateProgress();
  window.setTimeout(setupMotion, 0);
})();
