/**
 * /evidence/ — anclas de sección, badges cafecito (?d=) y apertura al saltar.
 */
(function () {
  var SECTION_IDS = [
    "evidence-graficos",
    "evidence-csv",
    "evidence-estado",
    "evidence-pipeline",
  ];

  function isDayFilterActive() {
    var d = new URLSearchParams(window.location.search).get("d");
    if (!d) return false;
    var s = String(d).trim().toLowerCase();
    return s !== "" && s !== "todos" && s !== "todo" && s !== "all" && s !== "*";
  }

  function syncDayFilterBadges() {
    var active = isDayFilterActive();
    document.querySelectorAll(".evidenceBadge").forEach(function (el) {
      el.classList.toggle("evidenceBadge--dayFilter", active);
    });
  }

  function openSection(id) {
    if (!id) return;
    var el = document.getElementById(id);
    if (el && el.tagName === "DETAILS") el.open = true;
  }

  function scrollToHash() {
    var id = (location.hash || "").replace(/^#/, "");
    if (!id) return;
    openSection(id);
    var el = document.getElementById(id);
    if (!el) return;
    requestAnimationFrame(function () {
      el.scrollIntoView({ block: "start", behavior: "smooth" });
      highlightNav();
    });
  }

  function highlightNav() {
    var links = document.querySelectorAll(".evidenceSectionNav__link");
    if (!links.length) return;

    var current = "";
    SECTION_IDS.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      var top = el.getBoundingClientRect().top;
      if (top <= 120) current = id;
    });

    links.forEach(function (a) {
      var href = a.getAttribute("href") || "";
      var linkId = href.replace(/^#/, "");
      a.classList.toggle("is-active", linkId === current);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    syncDayFilterBadges();
    scrollToHash();

    document.querySelectorAll(".evidenceSectionNav__link").forEach(function (a) {
      a.addEventListener("click", function (ev) {
        var href = a.getAttribute("href") || "";
        if (href.charAt(0) !== "#") return;
        var id = href.slice(1);
        var el = document.getElementById(id);
        if (!el) return;
        ev.preventDefault();
        openSection(id);
        history.pushState(null, "", href);
        el.scrollIntoView({ block: "start", behavior: "smooth" });
        highlightNav();
      });
    });

    SECTION_IDS.forEach(function (id) {
      var el = document.getElementById(id);
      if (!el || el.tagName !== "DETAILS") return;
      el.addEventListener("toggle", highlightNav);
    });

    window.addEventListener("scroll", highlightNav, { passive: true });
    highlightNav();
  });

  window.addEventListener("hashchange", scrollToHash);
})();
