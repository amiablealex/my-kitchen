// The ingredient page's pick-an-ingredient sheets: Merge into… (0.38.0, one
// choice) and Add kinds (0.39.0, several). Both filter as you type and name
// the outcome on their button; the forms post normally.
(function () {
  function setup(sheet, opener, go, label) {
    if (!sheet || !opener || !sheet.showModal) return;
    var filter = sheet.querySelector("[data-sheet-filter]");
    function sync() { label(go, sheet.querySelectorAll("input:checked")); }
    function applyFilter() {
      var q = filter.value.trim().toLowerCase();
      sheet.querySelectorAll("[data-sheet-lane]").forEach(function (lane) {
        var any = false;
        lane.querySelectorAll("[data-sheet-name]").forEach(function (o) {
          var show = !q || o.dataset.sheetName.indexOf(q) !== -1;
          o.hidden = !show;
          if (show) any = true;
        });
        lane.hidden = !any;
      });
    }
    opener.addEventListener("click", function () {
      var menu = opener.closest("details");
      if (menu) menu.open = false;
      filter.value = "";
      applyFilter();
      sync();
      sheet.showModal();
      filter.focus();
    });
    filter.addEventListener("input", applyFilter);
    sheet.addEventListener("change", sync);
    sheet.querySelector("[data-sheet-cancel]").addEventListener("click", function () { sheet.close(); });
  }

  var merge = document.getElementById("merge-sheet");
  setup(merge, document.querySelector("[data-merge-open]"),
        merge && merge.querySelector("[data-merge-go]"), function (go, picked) {
    go.disabled = !picked.length;
    go.textContent = picked.length ? "Merge into " + picked[0].dataset.name : "Merge";
  });

  var kinds = document.getElementById("kinds-sheet");
  setup(kinds, document.querySelector("[data-kinds-open]"),
        kinds && kinds.querySelector("[data-kinds-go]"), function (go, picked) {
    var n = picked.length;
    go.disabled = !n;
    go.textContent = n ? "Add " + n + " kind" + (n === 1 ? "" : "s") : "Add kinds";
  });
})();
