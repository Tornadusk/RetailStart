(function () {
  var raw = document.getElementById("dashboard-chart-data");
  if (!raw || typeof Chart === "undefined") return;

  var data;
  try {
    data = JSON.parse(raw.textContent);
  } catch (e) {
    return;
  }

  var fontColor = "#c8dcff";
  var gridColor = "rgba(105, 210, 255, 0.12)";
  var palette = [
    "#69d2ff",
    "#a78bfa",
    "#58f2b3",
    "#ffd166",
    "#ff6b9d",
    "#7fd8be",
    "#f9844a",
    "#94a3b8",
  ];

  function colors(n) {
    var out = [];
    for (var i = 0; i < n; i++) out.push(palette[i % palette.length]);
    return out;
  }

  function pie(id, block) {
    var canvas = document.getElementById(id);
    if (!canvas || !block.labels.length) return;
    new Chart(canvas.getContext("2d"), {
      type: "pie",
      data: {
        labels: block.labels,
        datasets: [{ data: block.values, backgroundColor: colors(block.labels.length) }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "right", labels: { color: fontColor } },
        },
      },
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
            backgroundColor: "rgba(105, 210, 255, 0.55)",
            borderColor: "rgba(105, 210, 255, 0.9)",
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
            backgroundColor: "rgba(167, 139, 250, 0.55)",
            borderColor: "rgba(167, 139, 250, 0.95)",
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

  pie("chart-canal", data.by_canal || { labels: [], values: [] });
  barHorizontal("chart-clientes", data.top_clientes || { labels: [], values: [] });
  barVertical("chart-dia", data.by_dia || { labels: [], values: [] });
  pie("chart-dow", data.by_dow || { labels: [], values: [] });
  barHorizontal("chart-productos", data.top_productos || { labels: [], values: [] });
})();
