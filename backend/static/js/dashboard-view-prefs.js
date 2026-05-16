/**
 * Persiste el modo Visualización (charts / tables / both) en localStorage y lo reaplica
 * cuando la URL no trae ?view= (p. ej. enlaces rápidos de filtros sin ese parámetro).
 * Por defecto el servidor usa charts; si la preferencia guardada es charts, no hay redirección.
 */
(function () {
  var KEY = "retailstart.dashboard.viewMode";
  var ALLOWED = ["charts", "tables", "both"];
  var DEFAULT = "charts";

  try {
    var url = new URL(window.location.href);
    var raw = (url.searchParams.get("view") || "").toLowerCase();
    if (raw && ALLOWED.indexOf(raw) !== -1) {
      localStorage.setItem(KEY, raw);
      return;
    }

    var stored = localStorage.getItem(KEY);
    if (!stored || ALLOWED.indexOf(stored) === -1) {
      return;
    }

    if (stored === DEFAULT) {
      return;
    }

    url.searchParams.set("view", stored);
    var hash = window.location.hash || "";
    window.location.replace(url.pathname + url.search + hash);
  } catch (e) {}
})();
