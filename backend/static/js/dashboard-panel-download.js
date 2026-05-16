/**
 * Exportaciones desde Chart.js (canvas → PNG / CSV serie / HTML con imagen / ventana imprimir PDF).
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

  function chartToWhiteDataUrl(chart) {
    chart.update("none");
    var src = chart.canvas;
    var scale = chartExportScale(src.width, src.height);

    var tmp = document.createElement("canvas");
    tmp.width = Math.round(src.width * scale);
    tmp.height = Math.round(src.height * scale);
    var ctx = tmp.getContext("2d");
    if (!ctx) return "";

    ctx.setTransform(scale, 0, 0, scale, 0, 0);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, src.width, src.height);
    ctx.drawImage(src, 0, 0);

    return tmp.toDataURL("image/png");
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function csvCell(v) {
    var val = v === undefined || v === null ? "" : v;
    var str = typeof val === "object" ? JSON.stringify(val) : String(val);
    if (/[",\n\r]/.test(str)) return '"' + str.replace(/"/g, '""') + '"';
    return str;
  }

  function triggerBlobDownload(blob, filename) {
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 2000);
  }

  function resolveWrap(btn) {
    return btn.closest(".dashboardDownload--card");
  }

  function resolveChart(btn) {
    var wrap = resolveWrap(btn);
    if (!wrap || typeof Chart === "undefined") return null;
    var id = wrap.getAttribute("data-chart-canvas");
    var canvas = id ? document.getElementById(id) : null;
    if (!canvas) return null;
    return Chart.getChart(canvas);
  }

  document.addEventListener("click", function (ev) {
    var pngBtn = ev.target.closest(".js-dashboard-chart-png");
    var csvBtn = ev.target.closest(".js-dashboard-chart-csv");
    var htmlBtn = ev.target.closest(".js-dashboard-chart-html");
    var pdfBtn = ev.target.closest(".js-dashboard-chart-pdf");

    var btn = pngBtn || csvBtn || htmlBtn || pdfBtn;
    if (!btn) return;

    var wrap = resolveWrap(btn);
    if (!wrap) return;

    var stem = wrap.getAttribute("data-export-stem") || "retailstart_dashboard_chart";
    var title = wrap.getAttribute("data-chart-title") || "Gráfico";

    var chart = resolveChart(btn);
    if (!chart) return;

    if (pngBtn) {
      var pngUrl = chartToWhiteDataUrl(chart);
      if (!pngUrl) return;
      var a = document.createElement("a");
      a.href = pngUrl;
      a.download = stem + ".png";
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      return;
    }

    if (csvBtn) {
      var labels = chart.data.labels || [];
      var ds0 = chart.data.datasets && chart.data.datasets[0];
      var vals = ds0 && ds0.data ? ds0.data : [];
      var seriesLabel = ds0 && ds0.label ? ds0.label : "Valor";
      var rows = [];
      rows.push(["RetailStart — serie del gráfico"]);
      rows.push([title]);
      rows.push([]);
      rows.push(["Etiqueta", seriesLabel]);
      var n = Math.max(labels.length, vals.length);
      for (var i = 0; i < n; i++) {
        rows.push([labels[i], vals[i]]);
      }
      var csv = rows.map(function (row) {
        return row.map(csvCell).join(",");
      }).join("\r\n");
      var blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
      triggerBlobDownload(blob, stem + "_chart.csv");
      return;
    }

    if (htmlBtn) {
      var dataUrl = chartToWhiteDataUrl(chart);
      if (!dataUrl) return;
      var html =
        "<!DOCTYPE html><html lang=\"es\"><head><meta charset=\"utf-8\"/><title>" +
        escapeHtml(title) +
        "</title><style>body{font-family:system-ui,sans-serif;margin:24px;text-align:center;background:#fafafa;color:#111;}h1{font-size:1.05rem;font-weight:600;}img{max-width:100%;height:auto;border:1px solid #ddd;border-radius:8px;background:#fff;}</style></head><body>" +
        "<h1>" +
        escapeHtml(title) +
        '</h1><p><img src="' +
        dataUrl +
        '" alt="Gráfico exportado"/></p></body></html>';
      var blob = new Blob([html], { type: "text/html;charset=utf-8" });
      triggerBlobDownload(blob, stem + "_chart.html");
      return;
    }

    if (pdfBtn) {
      var imgData = chartToWhiteDataUrl(chart);
      if (!imgData) return;
      var w = window.open("", "_blank");
      if (!w) return;
      var doc = w.document;
      doc.open();
      doc.write(
        "<!DOCTYPE html><html lang=\"es\"><head><meta charset=\"utf-8\"/><title>" +
          escapeHtml(title) +
          '</title><style>@page{margin:16mm}body{font-family:system-ui,sans-serif;text-align:center;margin:0;padding:16px;color:#111;}h1{font-size:14px;margin:0 0 12px;}img{max-width:100%;height:auto;}</style></head><body>'
      );
      doc.write("<h1>" + escapeHtml(title) + "</h1>");
      doc.write(
        '<img src="' +
          imgData +
          '" alt="" onload="window.focus();window.print();" />'
      );
      doc.write("</body></html>");
      doc.close();
    }
  });
})();
