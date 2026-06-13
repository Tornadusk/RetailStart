(function () {
  var raw = document.getElementById("dashboard-chart-data");
  if (!raw || typeof Chart === "undefined") return;

  var data;
  try {
    data = JSON.parse(raw.textContent);
  } catch (e) {
    return;
  }

  var STORAGE_PREFIX = "retailstart.dashboard.pieType.";
  var EMPTY = { labels: [], values: [] };

  var fontColor = "#52525b"; // text-stone-600
  var gridColor = "rgba(214, 211, 209, 0.4)"; // text-stone-300 con opacidad
  var palette = [
    "#3b82f6", // Blue
    "#ef4444", // Red
    "#10b981", // Emerald (Green)
    "#f59e0b", // Amber (Yellow)
    "#8b5cf6", // Violet
    "#ec4899", // Pink
    "#06b6d4", // Cyan
    "#84cc16", // Lime
    "#6366f1", // Indigo
    "#f97316"  // Orange
  ];

  function colors(n) {
    var arr = palette.slice();
    for (var i = arr.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var temp = arr[i];
      arr[i] = arr[j];
      arr[j] = temp;
    }
    var out = [];
    for (var i = 0; i < n; i++) out.push(arr[i % arr.length]);
    return out;
  }

  function readPieKind(canvasId) {
    try {
      var v = localStorage.getItem(STORAGE_PREFIX + canvasId);
      return v === "doughnut" ? "doughnut" : "pie";
    } catch (e2) {
      return "pie";
    }
  }

  function writePieKind(canvasId, kind) {
    try {
      localStorage.setItem(STORAGE_PREFIX + canvasId, kind);
    } catch (e2) {}
  }

  function syncPieToggleUi(wrap) {
    if (!wrap) return;
    var target = wrap.getAttribute("data-chart-target");
    if (!target) return;
    var k = readPieKind(target);
    var btns = wrap.querySelectorAll(".js-pie-kind");
    for (var i = 0; i < btns.length; i++) {
      var btn = btns[i];
      var isMatch = btn.getAttribute("data-kind") === k;
      btn.classList.toggle("is-active", isMatch);
      btn.setAttribute("aria-pressed", isMatch ? "true" : "false");
    }
  }

  function blockForPieKey(blockKey) {
    if (!blockKey || !data) return EMPTY;
    return data[blockKey] || EMPTY;
  }

  function rebuildPieFromToggle(wrap, chartKind) {
    var canvasId = wrap.getAttribute("data-chart-target");
    var blockKey = wrap.getAttribute("data-chart-block");
    if (!canvasId || !blockKey) return;
    pieOrDonut(canvasId, blockForPieKey(blockKey), chartKind || readPieKind(canvasId));
    syncPieToggleUi(wrap);
  }

  function pieOrDonut(id, block, chartType) {
    var canvas = document.getElementById(id);
    if (!canvas || !block.labels || !block.labels.length) return;
    var donut = chartType === "doughnut";
    var prev = Chart.getChart(canvas);
    if (prev) prev.destroy();

    var circOpts = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right", labels: { color: fontColor } },
      },
    };
    if (donut) circOpts.cutout = "54%";

    new Chart(canvas.getContext("2d"), {
      type: donut ? "doughnut" : "pie",
      data: {
        labels: block.labels,
        datasets: [{ data: block.values, backgroundColor: colors(block.labels.length) }],
      },
      options: circOpts,
    });
  }

  function barHorizontal(id, block) {
    var canvas = document.getElementById(id);
    if (!canvas || !block.labels.length) return;
    new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: block.labels,
        datasets: [
          {
            label: "Total ($)",
            data: block.values,
            backgroundColor: colors(block.labels.length),
            borderColor: colors(block.labels.length),
            borderWidth: 1,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ticks: { color: fontColor },
            grid: { color: gridColor },
          },
          y: {
            ticks: { color: fontColor },
            grid: { color: gridColor },
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  }

  function barVertical(id, block) {
    var canvas = document.getElementById(id);
    if (!canvas || !block.labels.length) return;
    new Chart(canvas.getContext("2d"), {
      type: "bar",
      data: {
        labels: block.labels,
        datasets: [
          {
            label: "Total ($)",
            data: block.values,
            backgroundColor: colors(block.labels.length),
            borderColor: colors(block.labels.length),
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ticks: { color: fontColor, maxRotation: 45, minRotation: 0 },
            grid: { color: gridColor },
          },
          y: {
            ticks: { color: fontColor },
            grid: { color: gridColor },
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  }

  var k = data.kpis || {};
  var km = document.getElementById("dashboard-kpi-monto");
  var kt = document.getElementById("dashboard-kpi-tx");
  var kp = document.getElementById("dashboard-kpi-prom");
  if (km) km.textContent = "$" + (k.total_monto || 0).toLocaleString("es-CL");
  if (kt) kt.textContent = String(k.transacciones || 0);
  if (kp) kp.textContent = "$" + (k.ticket_promedio || 0).toLocaleString("es-CL");

  pieOrDonut("chart-canal", data.by_canal || EMPTY, readPieKind("chart-canal"));
  barHorizontal("chart-clientes", data.top_clientes || EMPTY);
  barVertical("chart-dia", data.by_dia || EMPTY);
  pieOrDonut("chart-dow", data.by_dow || EMPTY, readPieKind("chart-dow"));
  barHorizontal("chart-productos", data.top_productos || EMPTY);

  document.querySelectorAll(".dashboardPieKindToggle").forEach(syncPieToggleUi);

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".js-pie-kind");
    if (!btn) return;
    var wrap = btn.closest(".dashboardPieKindToggle");
    if (!wrap) return;
    var canvasId = wrap.getAttribute("data-chart-target");
    var kind = btn.getAttribute("data-kind");
    if (!canvasId || !kind || (kind !== "pie" && kind !== "doughnut")) return;
    writePieKind(canvasId, kind);
    rebuildPieFromToggle(wrap, kind);
  });
})();
