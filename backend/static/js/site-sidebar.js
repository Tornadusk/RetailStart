/**
 * Barra lateral global: ocultar / mostrar + overlay en viewport estrecho.
 */
(function () {
  var KEY = "retailstart.sidebar.collapsed";
  var sidebar = document.getElementById("site-sidebar");
  var toggle = document.getElementById("site-sidebar-toggle");
  var backdrop = document.getElementById("site-sidebar-backdrop");
  if (!sidebar || !toggle) return;

  function isMobile() {
    return window.matchMedia("(max-width: 900px)").matches;
  }

  function readCollapsed() {
    try {
      return localStorage.getItem(KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function writeCollapsed(on) {
    try {
      localStorage.setItem(KEY, on ? "1" : "0");
    } catch (e) {}
  }

  function applyDesktop(collapsed) {
    document.body.classList.toggle("sidebarCollapsed", collapsed);
    toggle.setAttribute("aria-expanded", collapsed ? "false" : "true");
    toggle.setAttribute(
      "title",
      collapsed ? "Mostrar menú lateral" : "Ocultar menú lateral"
    );
    if (backdrop) backdrop.hidden = true;
    document.body.classList.remove("sidebarDrawerOpen");
  }

  function applyMobile(open) {
    document.body.classList.toggle("sidebarDrawerOpen", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (backdrop) backdrop.hidden = !open;
    document.body.classList.remove("sidebarCollapsed");
  }

  function sync() {
    if (isMobile()) {
      document.body.classList.add("sidebarMobile");
      applyMobile(document.body.classList.contains("sidebarDrawerOpen"));
    } else {
      document.body.classList.remove("sidebarMobile", "sidebarDrawerOpen");
      if (backdrop) backdrop.hidden = true;
      applyDesktop(readCollapsed());
    }
  }

  toggle.addEventListener("click", function () {
    if (isMobile()) {
      var open = !document.body.classList.contains("sidebarDrawerOpen");
      applyMobile(open);
    } else {
      var collapsed = !document.body.classList.contains("sidebarCollapsed");
      applyDesktop(collapsed);
      writeCollapsed(collapsed);
    }
  });

  if (backdrop) {
    backdrop.addEventListener("click", function () {
      applyMobile(false);
    });
  }

  window.addEventListener("resize", sync);
  sync();

})();
