// Facet filter for the Recipes list (Phase 21).
//
// One input drives two things: a free-text match on the row title, and a
// suggestion list of facet VALUES (cuisine / meal type / cook / source) drawn
// from #facet-options. Tapping a suggestion turns it into a chip; untokenised
// text stays a plain title filter.
//
// Why suggestion-driven rather than auto-detecting tags: typing "italian"
// is ambiguous — it's a cuisine tag AND a word that appears in recipe titles.
// Auto-converting would make "Italian Wedding Soup" vanish when you typed its
// own name. The user picks which they meant; both stay reachable.
//
// Chip semantics: different facets AND together, same-facet chips OR together,
// free text ANDs on top. Purely client-side — the whole bank is in the DOM, so
// filtering is instant with no reload.
//
// Separate from recipe_filter.js on purpose: that one is shared with Manage →
// Ingredients and must keep working untouched.
(function () {
  var box = document.getElementById("facet-box");
  if (!box) return;

  var input = document.getElementById("facet-input");
  var chipTray = document.getElementById("facet-chips");
  var suggestList = document.getElementById("facet-suggest");
  var nomatch = document.getElementById("recipe-nomatch");
  var groups = document.querySelectorAll(".recipe-group:not([data-no-filter])");

  // #facet-options MUST be parsed before this script runs — it's a plain IIFE,
  // not deferred. Missing element and malformed JSON are different failures and
  // shouldn't share a silent catch.
  var optionsEl = document.getElementById("facet-options");
  var OPTIONS = [];
  if (!optionsEl) {
    console.error("recipe_facets: #facet-options not found — is it above this script tag?");
  } else {
    try {
      OPTIONS = JSON.parse(optionsEl.textContent) || [];
    } catch (e) {
      console.error("recipe_facets: could not parse #facet-options", e);
    }
  }

  var FACET_NAMES = { cuisine: "Cuisine", meal: "Meal type", cook: "Cook", source: "Source" };
  var chips = [];  // [{facet, value, label}]

  function hasChip(facet, value) {
    return chips.some(function (c) { return c.facet === facet && c.value === value; });
  }

  // A row matches a facet if it carries ANY of that facet's chipped values.
  // Fields are pipe-bounded ("|italian|indian|"), so testing "|italian|" is a
  // whole-value match — "indian" can't half-match "west indian".
  function rowMatches(row, text) {
    if (text && (row.dataset.title || "").indexOf(text) === -1) return false;
    var byFacet = {};
    chips.forEach(function (c) {
      (byFacet[c.facet] = byFacet[c.facet] || []).push(c.value);
    });
    for (var facet in byFacet) {
      var field = row.dataset[facet] || "";
      var ok = byFacet[facet].some(function (v) { return field.indexOf("|" + v + "|") !== -1; });
      if (!ok) return false;
    }
    return true;
  }

  function apply() {
    var text = input.value.trim().toLowerCase();
    var any = false;
    groups.forEach(function (g) {
      var groupVisible = false;
      g.querySelectorAll(".recipe-row").forEach(function (r) {
        var m = rowMatches(r, text);
        r.hidden = !m;
        if (m) groupVisible = true;
      });
      g.hidden = !groupVisible;
      if (groupVisible) any = true;
    });
    // Only claim "no matches" when a filter is actually active.
    if (nomatch) nomatch.hidden = any || (!text && chips.length === 0);
  }

  function renderChips() {
    chipTray.innerHTML = "";
    chips.forEach(function (c, i) {
      var chip = document.createElement("button");
      chip.type = "button";
      chip.className = "facet-chip facet-chip--" + c.facet;
      chip.setAttribute("aria-label", "Remove filter " + FACET_NAMES[c.facet] + ": " + c.label);
      chip.innerHTML = '<span class="facet-chip-facet">' + FACET_NAMES[c.facet] +
                       '</span><span class="facet-chip-value"></span><span class="facet-chip-x">\u00d7</span>';
      chip.querySelector(".facet-chip-value").textContent = c.label;
      chip.addEventListener("click", function () {
        chips.splice(i, 1);
        renderChips(); apply(); renderSuggestions();
      });
      chipTray.appendChild(chip);
    });
    chipTray.hidden = chips.length === 0;
  }

  function renderSuggestions() {
    var q = input.value.trim().toLowerCase();
    suggestList.innerHTML = "";
    if (!q) { suggestList.hidden = true; return; }
    var hits = OPTIONS.filter(function (o) {
      return !hasChip(o.facet, o.value) && o.label.toLowerCase().indexOf(q) !== -1;
    }).slice(0, 8);
    if (!hits.length) { suggestList.hidden = true; return; }
    hits.forEach(function (o) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "facet-suggest-btn";
      btn.innerHTML = '<span class="facet-suggest-facet">' + FACET_NAMES[o.facet] + '</span>';
      var v = document.createElement("span");
      v.className = "facet-suggest-value";
      v.textContent = o.label;
      btn.appendChild(v);
      btn.addEventListener("click", function () { addChip(o); });
      li.appendChild(btn);
      suggestList.appendChild(li);
    });
    suggestList.hidden = false;
  }

  function addChip(o) {
    if (!hasChip(o.facet, o.value)) chips.push(o);
    input.value = "";
    renderChips(); renderSuggestions(); apply();
    input.focus();
  }

  input.addEventListener("input", function () { renderSuggestions(); apply(); });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      // Enter takes the top suggestion — the fast path once you know the tags.
      e.preventDefault();
      var first = suggestList.querySelector(".facet-suggest-btn");
      if (first) first.click();
    } else if (e.key === "Escape") {
      suggestList.hidden = true;
    } else if (e.key === "Backspace" && input.value === "" && chips.length) {
      // Backspace on an empty input drops the last chip, as in any token field.
      chips.pop();
      renderChips(); apply(); renderSuggestions();
    }
  });

  document.addEventListener("click", function (e) {
    if (!box.contains(e.target)) suggestList.hidden = true;
  });

  renderChips();
  apply();
})();
