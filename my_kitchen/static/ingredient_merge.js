// Merge into… sheet on an ingredient's page (0.38.0). Opens from the ⋯ menu,
// filters the choices as you type, and names the outcome on the button
// ("Merge into Button mushrooms"). The form posts normally.
(function () {
  var sheet = document.getElementById("merge-sheet");
  var opener = document.querySelector("[data-merge-open]");
  if (!sheet || !opener || !sheet.showModal) return;
  var go = sheet.querySelector("[data-merge-go]");
  var filter = document.getElementById("merge-filter");

  function chosen() { return sheet.querySelector('input[name="into"]:checked'); }
  function syncGo() {
    var c = chosen();
    go.disabled = !c;
    go.textContent = c ? "Merge into " + c.dataset.name : "Merge";
  }
  opener.addEventListener("click", function () {
    var menu = opener.closest("details");
    if (menu) menu.open = false;
    filter.value = "";
    applyFilter();
    syncGo();
    sheet.showModal();
  });
  function applyFilter() {
    var q = filter.value.trim().toLowerCase();
    sheet.querySelectorAll("[data-merge-lane]").forEach(function (lane) {
      var any = false;
      lane.querySelectorAll("[data-merge-name]").forEach(function (o) {
        var show = !q || o.dataset.mergeName.indexOf(q) !== -1;
        o.hidden = !show;
        if (show) any = true;
      });
      lane.hidden = !any;
    });
  }
  filter.addEventListener("input", applyFilter);
  sheet.addEventListener("change", syncGo);
  sheet.querySelector("[data-merge-cancel]").addEventListener("click", function () { sheet.close(); });
})();
