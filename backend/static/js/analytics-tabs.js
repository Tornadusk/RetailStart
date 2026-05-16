/**
 * Pestañas Todas | Hechos | Dimensiones | Tiempo en /analytics/ + menú lateral.
 */
(function () {
  var STORAGE_MODEL =
    (window.RetailStartGlobalFilters && window.RetailStartGlobalFilters.STORAGE_MODEL) ||
    "retailstart.analytics.modelView";

  var buttons = document.querySelectorAll("[data-analytics-view]");
  var panels = document.querySelectorAll(".js-analytics-view");
  if (!buttons.length || !panels.length) return;

  function readModelView() {
    try {
      var v = localStorage.getItem(STORAGE_MODEL);
      if (v === "hechos" || v === "dimensiones" || v === "tiempo" || v === "todas") return v;
    } catch (e) {}
    return "todas";
  }

  function writeModelView(view) {
    try {
      localStorage.setItem(STORAGE_MODEL, view);
    } catch (e2) {}
  }

  function visibleFor(view, el) {
    var raw = el.getAttribute("data-analytics-views") || "";
    var allowed = raw.trim().split(/\s+/).filter(Boolean);
    if (!allowed.length) return true;
    if (view === "todas") return allowed.indexOf("todas") !== -1;
    return allowed.indexOf(view) !== -1;
  }

  function setView(view) {
    panels.forEach(function (el) {
      var show = visibleFor(view, el);
      el.hidden = !show;
      el.setAttribute("aria-hidden", show ? "false" : "true");
    });
    buttons.forEach(function (btn) {
      var v = btn.getAttribute("data-analytics-view");
      var on = v === view;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    writeModelView(view);
  }

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var v = btn.getAttribute("data-analytics-view");
      if (v) setView(v);
    });
  });

  setView(readModelView());
})();
