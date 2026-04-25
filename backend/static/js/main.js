(() => {
  const btn = document.getElementById("pingBtn");
  const out = document.getElementById("pingResult");
  if (!btn || !out) return;

  btn.addEventListener("click", () => {
    out.textContent = `JS OK - ${new Date().toLocaleString()}`;
  });
})();
