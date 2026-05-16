/**
 * Filtro global año / mes / día + vista modelo estrella.
 * Sincroniza menú lateral, URL (?y=&m=&d=) y localStorage entre /dashboard/ y /analytics/.
 */
(function () {
  var STORAGE_TIME = "retailstart.global.timeFilter";
  var STORAGE_PAGE = "retailstart.global.filterPage";
  var STORAGE_MODEL = "retailstart.analytics.modelView";

  var DIAS_CANON = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
  ];

  var form = document.getElementById("site-filter-form");
  var inputY = document.getElementById("site-filter-y");
  var inputM = document.getElementById("site-filter-m");
  var inputD = document.getElementById("site-filter-d");
  var statusEl = document.getElementById("site-filter-status");
  var clearBtn = document.getElementById("site-filter-clear");

  if (!form || !inputY || !inputM || !inputD) return;

  function isTodos(val) {
    var s = String(val == null ? "" : val)
      .trim()
      .toLowerCase();
    return !s || s === "todos" || s === "todo" || s === "all" || s === "*";
  }

  function stripAccents(s) {
    return String(s)
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function normalizeYear(raw) {
    if (isTodos(raw)) return "";
    var n = parseInt(String(raw).trim(), 10);
    if (!n || n < 1990 || n > 2100) return null;
    return String(n);
  }

  function normalizeMonth(raw) {
    if (isTodos(raw)) return "";
    var n = parseInt(String(raw).trim(), 10);
    if (!n || n < 1 || n > 12) return null;
    return String(n);
  }

  function normalizeDay(raw) {
    if (isTodos(raw)) return "";
    var s = stripAccents(String(raw).trim().toLowerCase());
    for (var i = 0; i < DIAS_CANON.length; i++) {
      if (stripAccents(DIAS_CANON[i].toLowerCase()) === s) return DIAS_CANON[i];
    }
    var cap = String(raw).trim();
    return cap.charAt(0).toUpperCase() + cap.slice(1);
  }

  function displayToken(raw, normalized) {
    if (normalized === "") return "todos";
    return normalized == null ? String(raw).trim() : normalized;
  }

  function readStorageTime() {
    try {
      var raw = localStorage.getItem(STORAGE_TIME);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  function writeStorageTime(state) {
    try {
      localStorage.setItem(STORAGE_TIME, JSON.stringify(state));
    } catch (e2) {}
  }

  function readFromUrl() {
    var p = new URLSearchParams(window.location.search);
    var fde = p.get("fde");
    var fha = p.get("fha");
    return {
      y: p.get("y") || "",
      m: p.get("m") || "",
      d: p.get("d") || "",
      fde: fde || "",
      fha: fha || "",
      range: !!(fde && fha),
    };
  }

  function urlToDisplay(urlState) {
    return {
      y: urlState.y ? urlState.y : "todos",
      m: urlState.m ? urlState.m : "todos",
      d: urlState.d ? urlState.d : "todos",
      range: urlState.range,
      fde: urlState.fde,
      fha: urlState.fha,
    };
  }

  function inputsToQuery() {
    var y = normalizeYear(inputY.value);
    var m = normalizeMonth(inputM.value);
    var d = normalizeDay(inputD.value);
    if (y === null || m === null || d === null) return null;
    var q = new URLSearchParams();
    if (y) q.set("y", y);
    if (m) q.set("m", m);
    if (d) q.set("d", d);
    return { q: q, y: y, m: m, d: d };
  }

  function preserveParams(q) {
    var cur = new URLSearchParams(window.location.search);
    if (cur.get("view")) q.set("view", cur.get("view"));
    [
      "fact_page",
      "fact_sort",
      "fact_dir",
      "cli_sort",
      "cli_dir",
      "prod_sort",
      "prod_dir",
      "canal_sort",
      "canal_dir",
    ].forEach(function (k) {
      if (cur.get(k)) q.set(k, cur.get(k));
    });
  }

  function resolveTarget() {
    var path = window.location.pathname || "";
    if (path.indexOf("/analytics") !== -1) {
      return { base: "/analytics/", hash: "#segmentar-ventas", page: "analytics" };
    }
    if (path.indexOf("/dashboard") !== -1) {
      return { base: "/dashboard/", hash: "#dashboard-filters", page: "dashboard" };
    }
    var last = "dashboard";
    try {
      last = localStorage.getItem(STORAGE_PAGE) || "dashboard";
    } catch (e) {}
    if (last === "analytics") {
      return { base: "/analytics/", hash: "#segmentar-ventas", page: "analytics" };
    }
    return { base: "/dashboard/", hash: "#dashboard-filters", page: "dashboard" };
  }

  function updateStatus(display) {
    if (!statusEl) return;
    if (display.range) {
      statusEl.textContent =
        "Rango: " + display.fde + " → " + display.fha + " (atajos en página)";
      return;
    }
    statusEl.textContent =
      "Selección: Año " + display.y + " · Mes " + display.m + " · Día " + display.d;
  }

  function fillInputs(display) {
    inputY.value = display.y;
    inputM.value = display.m;
    inputD.value = display.d;
    var disabled = !!display.range;
    inputY.disabled = disabled;
    inputM.disabled = disabled;
    inputD.disabled = disabled;
    updateStatus(display);
  }

  function syncPageSelects(display) {
    var yVal = display.y === "todos" ? "" : display.y;
    var mVal = display.m === "todos" ? "" : display.m;
    var dVal = display.d === "todos" ? "" : display.d;
    ["db_y", "fy"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.tagName === "SELECT") el.value = yVal;
    });
    ["db_m", "fm"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.tagName === "SELECT") el.value = mVal;
    });
    ["db_d", "fd"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el && el.tagName === "SELECT") {
        if (!dVal) el.value = "";
        else el.value = dVal;
      }
    });
  }

  function filterQueryFromUrlState(urlState) {
    var q = new URLSearchParams();
    if (urlState.range) {
      if (urlState.fde) q.set("fde", urlState.fde);
      if (urlState.fha) q.set("fha", urlState.fha);
    } else {
      if (urlState.y) q.set("y", urlState.y);
      if (urlState.m) q.set("m", urlState.m);
      if (urlState.d) q.set("d", urlState.d);
    }
    return q;
  }

  function updateNavFilterLinks(q) {
    var qs = q.toString();
    document.querySelectorAll(".siteSidebar__nav a").forEach(function (a) {
      var href = a.getAttribute("href") || "";
      if (href.indexOf("/dashboard") === -1 && href.indexOf("/analytics") === -1) return;
      var base = href.split("?")[0];
      a.setAttribute("href", base + (qs ? "?" + qs : ""));
    });
  }

  function syncFromUrl() {
    var urlState = readFromUrl();
    var display = urlToDisplay(urlState);
    fillInputs(display);
    syncPageSelects(display);
    writeStorageTime({ y: display.y, m: display.m, d: display.d });
    updateNavFilterLinks(filterQueryFromUrlState(urlState));
    try {
      localStorage.setItem(STORAGE_PAGE, resolveTarget().page);
    } catch (e) {}
  }

  function navigateWithQuery(q, target) {
    var qs = q.toString();
    var url = target.base + (qs ? "?" + qs : "") + target.hash;
    try {
      localStorage.setItem(STORAGE_PAGE, target.page);
    } catch (e2) {}
    window.location.assign(url);
  }

  function applyFilters() {
    var built = inputsToQuery();
    if (!built) {
      if (statusEl) statusEl.textContent = "Valor no válido en año, mes o día.";
      return;
    }
    var target = resolveTarget();
    preserveParams(built.q);
    writeStorageTime({
      y: displayToken(inputY.value, built.y),
      m: displayToken(inputM.value, built.m),
      d: displayToken(inputD.value, built.d),
    });
    navigateWithQuery(built.q, target);
  }

  function clearFilters() {
    inputY.value = "todos";
    inputM.value = "todos";
    inputD.value = "todos";
    writeStorageTime({ y: "todos", m: "todos", d: "todos" });
    var target = resolveTarget();
    var q = new URLSearchParams();
    preserveParams(q);
    navigateWithQuery(q, target);
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    applyFilters();
  });

  if (clearBtn) {
    clearBtn.addEventListener("click", clearFilters);
  }

  document.addEventListener("change", function (ev) {
    var t = ev.target;
    if (!t || t.tagName !== "SELECT") return;
    if (t.id === "db_y" || t.id === "fy") inputY.value = t.value ? t.value : "todos";
    if (t.id === "db_m" || t.id === "fm") inputM.value = t.value ? t.value : "todos";
    if (t.id === "db_d" || t.id === "fd") inputD.value = t.value ? t.value : "todos";
    var built = inputsToQuery();
    if (built) {
      writeStorageTime({
        y: displayToken(inputY.value, built.y),
        m: displayToken(inputM.value, built.m),
        d: displayToken(inputD.value, built.d),
      });
      updateStatus(urlToDisplay({ y: built.y, m: built.m, d: built.d, range: false }));
    }
  });

  syncFromUrl();

  window.RetailStartGlobalFilters = {
    syncFromUrl: syncFromUrl,
    STORAGE_MODEL: STORAGE_MODEL,
  };
})();
