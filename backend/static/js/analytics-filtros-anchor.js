/**
 * analytics-filtros-anchor.js — incluido solo en templates/core/analytics.html.
 *
 * Flujo:
 *   GET del formulario de filtros (action …#segmentar-ventas)
 *     → respuesta HTML con id="segmentar-ventas" en el cluster de filtros
 *     → el hash pide al navegador posicionar el ancla; este script llama scrollIntoView
 *       por si el submit no deja el viewport alineado de forma consistente.
 */
document.addEventListener("DOMContentLoaded", function () {
  if (location.hash.replace(/^#/, "") !== "segmentar-ventas") return;
  var el = document.getElementById("segmentar-ventas");
  if (!el) return;
  requestAnimationFrame(function () {
    el.scrollIntoView({ block: "start", behavior: "auto" });
  });
});
