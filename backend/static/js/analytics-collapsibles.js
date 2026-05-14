/**
 * analytics-collapsibles.js — solo en /analytics/.
 * Recuerda en localStorage si cada <details> está abierto o cerrado (+/−).
 * Plegar la UI no modifica Postgres; solo afecta la vista en el navegador.
 */
(function () {
  var PREFIX = "retailstart.analytics.details.";

  function storageKey(el) {
    return PREFIX + el.getAttribute("data-storage-key");
  }

  function defaultOpen(el) {
    return el.getAttribute("data-default-open") !== "false";
  }

  document.addEventListener("DOMContentLoaded", function () {
    var detailsList = document.querySelectorAll(
      "details.analyticsCollapsible[data-storage-key]"
    );

    detailsList.forEach(function (d) {
      var k = storageKey(d);
      var v = localStorage.getItem(k);
      if (v === "open") d.open = true;
      else if (v === "closed") d.open = false;
      else d.open = defaultOpen(d);
    });

    detailsList.forEach(function (d) {
      d.addEventListener("toggle", function () {
        localStorage.setItem(storageKey(d), d.open ? "open" : "closed");
      });
    });
  });
})();
