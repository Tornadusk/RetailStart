/**
 * Pestañas Todas | Hechos | Dimensiones | Tiempo en /analytics/.
 * Cada bloque marcado con .js-analytics-view y data-analytics-views="todas hechos ...".
 */
(function () {
  var buttons = document.querySelectorAll("[data-analytics-view]");
  var panels = document.querySelectorAll(".js-analytics-view");
  if (!buttons.length || !panels.length) return;

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
  }

  buttons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var v = btn.getAttribute("data-analytics-view");
      if (v) setView(v);
    });
  });

  setView("todas");
})();
