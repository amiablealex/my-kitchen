// Manage → Ingredients: Standard / Staples tabs + a filter scoped to the active
// tab. Tab choice persists in sessionStorage so a pin/unpin (which reloads the
// page) keeps you on the tab you were working in, with no server round-trip.
(function () {
  var KEY = "mk-ingredients-tab";
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));
  if (!tabs.length) return;

  var panels = {};
  document.querySelectorAll(".tab-panel").forEach(function (p) { panels[p.dataset.panel] = p; });
  var filterInput = document.getElementById("ing-filter");
  var stapleCheckbox = document.getElementById("add-is-staple");

  function filterPanel(panel, q) {
    if (!panel) return;
    q = (q || "").trim().toLowerCase();
    var any = false;
    panel.querySelectorAll(".recipe-group:not([data-no-filter])").forEach(function (g) {
      var gv = false;
      g.querySelectorAll(".recipe-row").forEach(function (r) {
        var m = !q || (r.dataset.title || "").indexOf(q) !== -1;
        r.hidden = !m; if (m) gv = true;
      });
      g.hidden = !gv; if (gv) any = true;
    });
    var nomatch = panel.querySelector(".recipe-nomatch");
    if (nomatch) nomatch.hidden = any || !q;
  }

  function activate(name) {
    if (!panels[name]) name = "standard";
    tabs.forEach(function (t) {
      var on = t.dataset.tab === name;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    Object.keys(panels).forEach(function (k) { panels[k].hidden = k !== name; });
    if (stapleCheckbox) stapleCheckbox.checked = (name === "staples");
    filterPanel(panels[name], filterInput ? filterInput.value : "");
    try { sessionStorage.setItem(KEY, name); } catch (e) {}
  }

  tabs.forEach(function (t) { t.addEventListener("click", function () { activate(t.dataset.tab); }); });
  if (filterInput) filterInput.addEventListener("input", function () {
    var active = document.querySelector(".tab.is-active");
    filterPanel(panels[active ? active.dataset.tab : "standard"], filterInput.value);
  });

  var saved = null;
  try { saved = sessionStorage.getItem(KEY); } catch (e) {}
  activate(saved || "standard");
})();
