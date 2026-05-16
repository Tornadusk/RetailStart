/**
 * Descarga PNG desde Chart.js: fondo blanco + escalado para mayor resolución (canvas temporal).
 */
(function () {
  function chartExportScale(srcW, srcH) {
    var dpr = typeof window.devicePixelRatio === "number" ? window.devicePixelRatio : 1;
    var scale = Math.min(4, Math.max(2, Math.round(dpr || 2)));
    var maxSide = 8192;
    var capW = Math.floor(maxSide / Math.max(1, srcW));
    var capH = Math.floor(maxSide / Math.max(1, srcH));
    scale = Math.min(scale, capW, capH);
    if (scale < 1) scale = 1;
    return scale;
  }

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".js-dashboard-chart-png");
    if (!btn || typeof Chart === "undefined") return;

    var canvasId = btn.getAttribute("data-chart-canvas") || "";
    var filename = btn.getAttribute("data-download-filename") || "dashboard_chart.png";
    var canvas = document.getElementById(canvasId);
    if (!canvas) return;

    var chart = Chart.getChart(canvas);
    if (!chart) return;

    chart.update("none");
    var src = chart.canvas;
    var scale = chartExportScale(src.width, src.height);

    var tmp = document.createElement("canvas");
    tmp.width = Math.round(src.width * scale);
    tmp.height = Math.round(src.height * scale);
    var ctx = tmp.getContext("2d");
    if (!ctx) return;

    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, src.width, src.height);
    ctx.drawImage(src, 0, 0);

    var url = tmp.toDataURL("image/png");
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  });
})();
