/**
 * PNG tabla (html2canvas) + PNG/SVG/HTML/CSV/PDF desde Chart.js.
 * Vista «Todos»: exportación combinada en el menú Descargar del encabezado.
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

  /** Trocea Base64 grande para pegar sin superar límites de celda típicos (~32 767 en Excel). */
  function pngBase64ExportChunks(rawB64, maxLen) {
    var chunks = [];
    var cap = typeof maxLen === "number" && maxLen > 0 ? maxLen : 28000;
    for (var i = 0; i < rawB64.length; i += cap) {
      chunks.push(rawB64.slice(i, i + cap));
    }
    return chunks;
  }

  function csvCell(v) {
    var val = v === undefined || v === null ? "" : v;
    var str = typeof val === "object" ? JSON.stringify(val) : String(val);
    if (/[",\n\r]/.test(str)) return '"' + str.replace(/"/g, '""') + '"';
    return str;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeXml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
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

  function triggerAnchorDataUrl(url, filename) {
    if (!url) return;
    var a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  function readBundleSpecs() {
    var el = document.getElementById("dashboard-bundle-manifest");
    if (!el) return [];
    try {
      var arr = JSON.parse(el.textContent);
      return Array.isArray(arr) ? arr : [];
    } catch (e) {
      return [];
    }
  }

  function tableRasterScale() {
    var dpr = typeof window.devicePixelRatio === "number" ? window.devicePixelRatio : 1;
    return Math.min(3, Math.max(2, Math.round(dpr || 2)));
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

  /** Tamaño completo del contenido con scroll (no solo el viewport del .tableWrap). */
  function tableExportPixelBox(el) {
    var w = Math.max(el.scrollWidth, el.offsetWidth);
    var h = Math.max(el.scrollHeight, el.offsetHeight);
    var tbl = el.querySelector("table");
    if (tbl) {
      w = Math.max(w, tbl.scrollWidth, tbl.offsetWidth);
      h = Math.max(h, tbl.scrollHeight, tbl.offsetHeight);
    }
    return { w: Math.ceil(w), h: Math.ceil(h) };
  }

  function captureTableWrapPngPromise(el, stem) {
    if (!el || typeof html2canvas === "undefined") return Promise.resolve();
    var prevSL = el.scrollLeft;
    var prevST = el.scrollTop;
    el.scrollLeft = 0;
    el.scrollTop = 0;
    var box = tableExportPixelBox(el);
    return html2canvas(el, {
      scale: tableRasterScale(),
      width: box.w,
      height: box.h,
      windowWidth: box.w,
      windowHeight: box.h,
      scrollX: 0,
      scrollY: 0,
      backgroundColor: "#ffffff",
      logging: false,
      onclone: function (_doc, cloned) {
        cloned.style.overflow = "visible";
        cloned.style.overflowX = "visible";
        cloned.style.overflowY = "visible";
        cloned.style.width = box.w + "px";
        cloned.style.height = box.h + "px";
        cloned.style.maxHeight = "none";
        cloned.style.padding = "10px";
        cloned.style.borderRadius = "8px";
        cloned.style.background = "#ffffff";
        cloned.style.boxSizing = "border-box";
        var cells = cloned.querySelectorAll("th, td");
        for (var i = 0; i < cells.length; i++) {
          cells[i].style.color = "#0f172a";
          cells[i].style.border = "1px solid #cbd5e1";
          cells[i].style.backgroundColor = "transparent";
        }
        var ths = cloned.querySelectorAll("thead th");
        for (var j = 0; j < ths.length; j++) {
          ths[j].style.backgroundColor = "#e2e8f0";
          ths[j].style.color = "#0f172a";
          ths[j].style.fontWeight = "600";
        }
        var muted = cloned.querySelectorAll(".muted");
        for (var m = 0; m < muted.length; m++) {
          muted[m].style.color = "#64748b";
        }
        var inner = cloned.querySelector("table");
        if (inner) {
          inner.style.width = "max-content";
          inner.style.maxWidth = "none";
          inner.style.minWidth = "0";
        }
      },
    })
      .then(function (canvas) {
        triggerAnchorDataUrl(canvas.toDataURL("image/png"), stem + "_table.png");
      })
      .catch(function () {})
      .then(function () {
        el.scrollLeft = prevSL;
        el.scrollTop = prevST;
      });
  }

  /** Filas CSV: etiquetas/valores + bloque PNG Base64 (equivale al menú por tarjeta). */
  function csvTabularAndPngRows(chart) {
    var rows = [];
    var labels = chart.data.labels || [];
    var ds0 = chart.data.datasets && chart.data.datasets[0];
    var vals = ds0 && ds0.data ? ds0.data : [];
    var seriesLabel = ds0 && ds0.label ? ds0.label : "Valor";
    var pngDataUrl = chartToWhiteDataUrl(chart);
    var b64 = "";
    if (pngDataUrl && pngDataUrl.indexOf(",") !== -1) {
      b64 = pngDataUrl.slice(pngDataUrl.indexOf(",") + 1);
    }
    var cwCsv = chart.canvas ? chart.canvas.width : "";
    var chCsv = chart.canvas ? chart.canvas.height : "";
    rows.push(["Etiqueta", seriesLabel]);
    var n = Math.max(labels.length, vals.length);
    for (var i = 0; i < n; i++) {
      rows.push([labels[i], vals[i]]);
    }
    rows.push([]);
    rows.push([
      "En Excel LibreOffice/Office abra antes “Excel (.xlsx) · servidor” desde Descargar: ahí sí hay imagen embebida. Lo siguiente NO es foto en celdas, solo texto Base64 troceado para decodificar aparte.",
      "",
    ]);
    rows.push(["grafico_visual_png_mime_type", "image/png"]);
    rows.push(["grafico_visual_png_px_ancho", String(cwCsv)]);
    rows.push(["grafico_visual_png_px_alto", String(chCsv)]);
    if (b64) {
      var parts = pngBase64ExportChunks(b64, 28000);
      rows.push(["grafico_visual_png_partes_totales", String(parts.length)]);
      for (var ip = 0; ip < parts.length; ip++) {
        rows.push(["grafico_visual_png_parte_" + ("00000" + String(ip + 1)).slice(-5), parts[ip]]);
      }
    } else {
      rows.push(["grafico_visual_png_estado", "sin_datos_png"]);
    }
    return rows;
  }

  function bundleChartsCsvAll() {
    if (typeof Chart === "undefined") return;
    var specs = readBundleSpecs();
    var rows = [["RetailStart — export combinado gráficos · CSV es solo TEXTO (+ Base64 PNG por panel para decodificar aparte); use .xlsx del servidor si quiere foto en Excel", ""]];
    rows.push([]);
    for (var s = 0; s < specs.length; s++) {
      var spec = specs[s];
      if (s > 0) rows.push([]);
      rows.push(["Panel gráfico", spec.title]);
      rows.push([]);
      var canvas = document.getElementById(spec.canvasId);
      var chart = canvas ? Chart.getChart(canvas) : null;
      if (!chart) {
        rows.push(["(sin datos Chart.js en este momento)", ""]);
        rows.push([]);
        continue;
      }
      var block = csvTabularAndPngRows(chart);
      for (var b = 0; b < block.length; b++) {
        rows.push(block[b]);
      }
    }
    var csvText = rows
      .map(function (row) {
        return row.map(csvCell).join(",");
      })
      .join("\r\n");
    var csvBlob = new Blob(["\ufeff" + csvText], { type: "text/csv;charset=utf-8;" });
    triggerBlobDownload(csvBlob, "retailstart_dashboard_graficos_todos.csv");
  }

  function bundleChartsHtmlAll() {
    if (typeof Chart === "undefined") return;
    var specs = readBundleSpecs();
    var parts = [];
    parts.push("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'/><title>RetailStart · gráficos</title>");
    parts.push(
      "<style>body{font-family:system-ui,sans-serif;background:#fafafa;color:#111;padding:24px;}h1{font-size:1.1rem;}h2{font-size:.95rem;margin-top:22px;color:#374151;}img{max-width:100%;height:auto;border:1px solid #ddd;border-radius:8px;background:#fff;display:block;margin:12px auto;}</style></head><body>"
    );
    parts.push("<h1>RetailStart · todos los gráficos del dashboard</h1>");
    for (var i = 0; i < specs.length; i++) {
      var spec = specs[i];
      var canvas = document.getElementById(spec.canvasId);
      var chart = canvas ? Chart.getChart(canvas) : null;
      var dataUrl = chart ? chartToWhiteDataUrl(chart) : "";
      parts.push("<h2>" + escapeHtml(spec.title) + "</h2>");
      parts.push("<p>" + (dataUrl ? '<img alt="" src="' + dataUrl + '"/>' : "<em>No hay gráfico disponible.</em>") + "</p>");
    }
    parts.push("</body></html>");
    triggerBlobDownload(new Blob([parts.join("")], { type: "text/html;charset=utf-8;" }), "retailstart_dashboard_graficos_todos.html");
  }

  function bundleChartsPdfAll() {
    if (typeof Chart === "undefined") return;
    var specs = readBundleSpecs();
    var w = window.open("", "_blank");
    if (!w) return;
    var chunks = [];
    chunks.push("<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'/>");
    chunks.push(
      "<title>RetailStart · imprimir gráficos</title><style>@page{margin:14mm}body{font-family:system-ui,sans-serif;padding:14px;color:#111;}h1{font-size:15px;}h2{font-size:12px;margin:16px 0 8px;}img{max-width:100%;height:auto;page-break-inside:avoid;}</style></head><body>"
    );
    chunks.push("<h1>RetailStart · todos los gráficos</h1>");
    for (var i = 0; i < specs.length; i++) {
      var spec = specs[i];
      var canvas = document.getElementById(spec.canvasId);
      var chart = canvas ? Chart.getChart(canvas) : null;
      var dataUrl = chart ? chartToWhiteDataUrl(chart) : "";
      chunks.push("<h2>" + escapeHtml(spec.title) + "</h2>");
      chunks.push("<p>");
      chunks.push(dataUrl ? '<img alt="" src="' + dataUrl + '"/>' : "<em>No hay gráfico.</em>");
      chunks.push("</p>");
    }
    chunks.push("</body></html>");
    var doc = w.document;
    doc.open();
    doc.write(chunks.join(""));
    doc.close();
    setTimeout(function () {
      w.focus();
      w.print();
    }, 520);
  }

  function runBundleChartsPng() {
    if (typeof Chart === "undefined") return;
    var specs = readBundleSpecs();
    var i = 0;
    function step() {
      if (i >= specs.length) return;
      var spec = specs[i];
      i++;
      var canvas = document.getElementById(spec.canvasId);
      var chart = canvas ? Chart.getChart(canvas) : null;
      if (chart) {
        var pngUrl = chartToWhiteDataUrl(chart);
        triggerAnchorDataUrl(pngUrl, spec.stem + ".png");
      }
      setTimeout(step, 420);
    }
    step();
  }

  function runBundleChartsSvg() {
    if (typeof Chart === "undefined") return;
    var specs = readBundleSpecs();
    var idx = 0;
    function step() {
      if (idx >= specs.length) return;
      var spec = specs[idx];
      idx++;
      var canvas = document.getElementById(spec.canvasId);
      var chart = canvas ? Chart.getChart(canvas) : null;
      if (chart) {
        var imgHref = chartToWhiteDataUrl(chart);
        if (imgHref) {
          var cw = chart.canvas.width;
          var ch = chart.canvas.height;
          var svg =
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" +
            '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="' +
            cw +
            '" height="' +
            ch +
            '" viewBox="0 0 ' +
            cw +
            " " +
            ch +
            "\">\n" +
            "<title>" +
            escapeXml(spec.title) +
            "</title>\n" +
            '<rect width="100%" height="100%" fill="#ffffff"/>\n' +
            '<image width="' +
            cw +
            '" height="' +
            ch +
            '" preserveAspectRatio="xMidYMid meet" href="' +
            imgHref +
            '" xlink:href="' +
            imgHref +
            '"/>\n' +
            "</svg>";
          triggerBlobDownload(new Blob([svg], { type: "image/svg+xml;charset=utf-8" }), spec.stem + "_chart.svg");
        }
      }
      setTimeout(step, 380);
    }
    step();
  }

  function runBundleTablesPng() {
    if (typeof html2canvas === "undefined") return;
    var specs = readBundleSpecs();
    function step(i) {
      if (i >= specs.length) return;
      var spec = specs[i];
      var elWrap = document.getElementById(spec.tableWrapId);
      captureTableWrapPngPromise(elWrap, spec.stem).then(function () {
        setTimeout(function () {
          step(i + 1);
        }, 440);
      });
    }
    step(0);
  }

  document.addEventListener("click", function (ev) {
    if (ev.target.closest(".js-dashboard-bundle-charts-png")) {
      ev.preventDefault();
      runBundleChartsPng();
      return;
    }
    if (ev.target.closest(".js-dashboard-bundle-charts-svg")) {
      ev.preventDefault();
      runBundleChartsSvg();
      return;
    }
    if (ev.target.closest(".js-dashboard-bundle-charts-csv")) {
      ev.preventDefault();
      bundleChartsCsvAll();
      return;
    }
    if (ev.target.closest(".js-dashboard-bundle-charts-html")) {
      ev.preventDefault();
      bundleChartsHtmlAll();
      return;
    }
    if (ev.target.closest(".js-dashboard-bundle-charts-pdf")) {
      ev.preventDefault();
      bundleChartsPdfAll();
      return;
    }
    if (ev.target.closest(".js-dashboard-bundle-tables-png")) {
      ev.preventDefault();
      runBundleTablesPng();
      return;
    }

    var tableBtn = ev.target.closest(".js-dashboard-table-png");
    if (tableBtn) {
      var wrapTb = resolveWrap(tableBtn);
      if (!wrapTb) return;
      var tid = wrapTb.getAttribute("data-dashboard-table-id");
      var stemTb = wrapTb.getAttribute("data-export-stem") || "retailstart_dashboard_tabla";
      if (!tid || typeof html2canvas === "undefined") return;
      var elTb = document.getElementById(tid);
      if (!elTb) return;
      captureTableWrapPngPromise(elTb, stemTb);
      return;
    }

    var pngBtn = ev.target.closest(".js-dashboard-chart-png");
    var svgBtn = ev.target.closest(".js-dashboard-chart-svg");
    var csvBtn = ev.target.closest(".js-dashboard-chart-csv");
    var htmlBtn = ev.target.closest(".js-dashboard-chart-html");
    var pdfBtn = ev.target.closest(".js-dashboard-chart-pdf");

    var btn = pngBtn || svgBtn || csvBtn || htmlBtn || pdfBtn;
    if (!btn) return;

    var wrap = resolveWrap(btn);
    if (!wrap) return;

    var stem = wrap.getAttribute("data-export-stem") || "retailstart_dashboard_chart";
    var title = wrap.getAttribute("data-chart-title") || "Gráfico";

    var chart = resolveChart(btn);
    if (!chart) return;

    if (pngBtn) {
      var pngUrl = chartToWhiteDataUrl(chart);
      triggerAnchorDataUrl(pngUrl, stem + ".png");
      return;
    }

    if (svgBtn) {
      var imgHref = chartToWhiteDataUrl(chart);
      if (!imgHref) return;
      var cw = chart.canvas.width;
      var ch = chart.canvas.height;
      var svg =
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" +
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="' +
        cw +
        '" height="' +
        ch +
        '" viewBox="0 0 ' +
        cw +
        " " +
        ch +
        "\">\n" +
        "<title>" +
        escapeXml(title) +
        "</title>\n" +
        '<rect width="100%" height="100%" fill="#ffffff"/>\n' +
        '<image width="' +
        cw +
        '" height="' +
        ch +
        '" preserveAspectRatio="xMidYMid meet" href="' +
        imgHref +
        '" xlink:href="' +
        imgHref +
        '"/>\n' +
        "</svg>";
      var blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
      triggerBlobDownload(blob, stem + "_chart.svg");
      return;
    }

    if (csvBtn) {
      var rows = [];
      rows.push(["RetailStart — datos numéricos del gráfico (Chart.js) + Base64 PNG del lienzo; Excel no mostrará la imagen. Para imagen en hoja elija “Excel (tabla + gráfico servidor)”.", ""]);
      rows.push([title]);
      rows.push([]);
      var csvBlock = csvTabularAndPngRows(chart);
      for (var r = 0; r < csvBlock.length; r++) rows.push(csvBlock[r]);
      var csv = rows
        .map(function (row) {
          return row.map(csvCell).join(",");
        })
        .join("\r\n");
      var csvBlob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8;" });
      triggerBlobDownload(csvBlob, stem + "_chart_data.csv");
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
      var blobHtml = new Blob([html], { type: "text/html;charset=utf-8" });
      triggerBlobDownload(blobHtml, stem + "_chart.html");
      return;
    }

    if (pdfBtn) {
      var imgData = chartToWhiteDataUrl(chart);
      if (!imgData) return;
      var win = window.open("", "_blank");
      if (!win) return;
      var docPdf = win.document;
      docPdf.open();
      docPdf.write(
        "<!DOCTYPE html><html lang=\"es\"><head><meta charset=\"utf-8\"/><title>" +
          escapeHtml(title) +
          '</title><style>@page{margin:16mm}body{font-family:system-ui,sans-serif;text-align:center;margin:0;padding:16px;color:#111;}h1{font-size:14px;margin:0 0 12px;}img{max-width:100%;height:auto;}</style></head><body>'
      );
      docPdf.write("<h1>" + escapeHtml(title) + "</h1>");
      docPdf.write(
        '<img src="' + imgData + '" alt="" onload="window.focus();window.print();" />'
      );
      docPdf.write("</body></html>");
      docPdf.close();
    }
  });
})();
