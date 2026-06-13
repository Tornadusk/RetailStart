/**
 * Navegación Dual: Alternar entre Franja Superior (navbar) y Menú Lateral (sidebar)
 */
(function () {
  var KEY = "retailstart.ui.nav_mode";
  
  function getMode() {
    try {
      var m = localStorage.getItem(KEY);
      return m === 'sidebar' ? 'sidebar' : 'navbar';
    } catch (e) {
      return 'navbar';
    }
  }

  function setMode(mode) {
    try {
      localStorage.setItem(KEY, mode);
    } catch (e) {}
    applyMode(mode);
  }

  function applyMode(mode) {
    if (mode === 'sidebar') {
      document.body.classList.remove('nav-mode-navbar');
      document.body.classList.add('nav-mode-sidebar');
    } else {
      document.body.classList.remove('nav-mode-sidebar');
      document.body.classList.add('nav-mode-navbar');
    }
  }

  // Set initial mode synchronously before render to avoid flicker if possible
  // (though the script has 'defer' in HTML, it will run early enough)
  applyMode(getMode());

  // Attach event listeners when DOM is fully ready
  document.addEventListener('DOMContentLoaded', function() {
    var btnToSidebar = document.getElementById('site-nav-switch-to-sidebar');
    if (btnToSidebar) {
      btnToSidebar.addEventListener('click', function() {
        setMode('sidebar');
      });
    }

    var btnToNavbar = document.getElementById('site-nav-switch-to-navbar');
    if (btnToNavbar) {
      btnToNavbar.addEventListener('click', function() {
        setMode('navbar');
      });
    }
  });
})();
