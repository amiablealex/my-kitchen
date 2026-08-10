// Shared client-side list filter. Any page with a #recipe-filter input, one or
// more .recipe-group tables, and (optionally) a #recipe-nomatch line gets live
// filtering: rows whose data-title doesn't match are hidden, and a group with no
// visible rows hides entirely. Groups marked [data-no-filter] are skipped (e.g.
// the retired drawer). Used by Manage → Ingredients. (History and Favourites
// moved to recipe_facets.js in Phase 21; this file was deliberately left alone
// rather than extended, to keep the blast radius off Manage.)
(function () {
  var input = document.getElementById("recipe-filter");
  if (!input) return;
  var groups = document.querySelectorAll(".recipe-group:not([data-no-filter])");
  var nomatch = document.getElementById("recipe-nomatch");
  input.addEventListener("input", function () {
    var q = input.value.trim().toLowerCase();
    var any = false;
    groups.forEach(function (g) {
      var gv = false;
      g.querySelectorAll(".recipe-row").forEach(function (r) {
        var m = !q || (r.dataset.title || "").indexOf(q) !== -1;
        r.hidden = !m; if (m) gv = true;
      });
      g.hidden = !gv; if (gv) any = true;
    });
    if (nomatch) nomatch.hidden = any || !q;
  });
})();
