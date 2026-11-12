// "Used anything up?" on the recipe page (Phase 32). Opens the stock sheet in
// "out" mode with this recipe's in-stock ingredients, none picked. Marking
// them out removes them from the list here (no reload); Undo puts them back.
(function () {
  var btn = document.getElementById("used-up-open");
  var data = document.getElementById("used-up-items");
  if (!btn || !data || !window.mkStockSheet) return;
  var items = [];
  try { items = JSON.parse(data.textContent); } catch (e) { return; }

  function sync() { btn.closest(".used-up").hidden = items.length === 0; }

  btn.addEventListener("click", function () {
    window.mkStockSheet.open({
      mode: "out",
      title: "Used anything up?",
      note: "Tap anything that's run out.",
      items: items,
      onDone: function (changed) {
        if (!changed.length) return;
        var gone = items.filter(function (i) { return changed.indexOf(i.id) !== -1; });
        items = items.filter(function (i) { return changed.indexOf(i.id) === -1; });
        sync();
        if (!window.showToast) return;
        window.showToast({
          message: "Marked " + changed.length + " as used up",
          actionLabel: "Undo",
          onAction: function () {
            window.mkStockUndo(changed, false)
              .then(function () { items = items.concat(gone); sync(); })
              .catch(function () { alert("Could not undo — is the server still running?"); });
          },
        });
      },
    });
  });
})();
