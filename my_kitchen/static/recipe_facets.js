// The Recipes / Favourites filter (Phase 21; reworked 0.36.2).
//
// One newest-first list, organised by the search box rather than by groups.
// The filter button at the end of the box (0.36.4) opens a panel listing every
// filter value that occurs, under Made by / Meal / Cuisine / Cook
// (#facet-options, already in that order), without the keyboard; tapping it
// again closes it, and it always shows every value whatever is typed (0.36.5),
// so "brown sugar" + Dessert works in either order; picking keeps the text.
// Tapping the text only types: the panel then appears just for values matching
// what's typed, and picking one of those swaps the typed text for the chip.
// Either way the panel closes on a pick. While anything is filtering, "N recipes" shows with
// Clear, and the button turns teal.
//
// Why pick-a-value rather than auto-detecting tags: "italian" is both a
// cuisine and a word in recipe titles. Auto-converting would hide "Italian
// wedding soup" when you typed its own name. The cook picks which they meant.
//
// Chip semantics: different facets AND together, same-facet chips OR together,
// free text ANDs on top. Client-side: the whole list is in the DOM.
//
// Ingredient search (0.36.3): when the typed text is an ingredient's whole
// name (#facet-ingredients, name -> id), recipes using it join the title
// matches, and the count line says so ("3 recipes use brown sugar"). Whole
// names only, so "brown" doesn't drag in brown sugar AND brown rice; a simple
// plural either way is forgiven ("eggs" finds Egg).
//
// The filter is kept in sessionStorage per page, so opening a recipe and
// coming back finds it as you left it.
(function () {
  var box = document.getElementById("facet-box");
  if (!box) return;

  var input = document.getElementById("facet-input");
  var panel = document.getElementById("facet-panel");
  var chipTray = document.getElementById("facet-chips");
  var countLine = document.getElementById("facet-count");
  var countN = document.getElementById("facet-count-n");
  var clearBtn = document.getElementById("facet-clear");
  var toggle = document.getElementById("facet-toggle");
  var pinned = false;   // opened with the filter button: show every value
  var nomatch = document.getElementById("recipe-nomatch");
  var rows = Array.prototype.slice.call(document.querySelectorAll(".recipe-group .recipe-row"));
  var noun = box.dataset.noun || "recipe";
  var STORE_KEY = "mk-facets:" + location.pathname;

  // #facet-options MUST be parsed before this script runs (a plain IIFE).
  var OPTIONS = [];
  var optionsEl = document.getElementById("facet-options");
  if (!optionsEl) {
    console.error("recipe_facets: #facet-options not found — is it above this script tag?");
  } else {
    try { OPTIONS = JSON.parse(optionsEl.textContent) || []; }
    catch (e) { console.error("recipe_facets: could not parse #facet-options", e); }
  }

  var INGREDIENTS = {};
  var ingEl = document.getElementById("facet-ingredients");
  if (ingEl) {
    try { INGREDIENTS = JSON.parse(ingEl.textContent) || {}; }
    catch (e) { console.error("recipe_facets: could not parse #facet-ingredients", e); }
  }

  // The ingredient the typed text names, as {id, name}, or null.
  function ingredientFor(text) {
    var q = text.replace(/\s+/g, " ");
    if (q.length < 2) return null;
    var tries = [q, q + "s", q + "es"];
    if (/es$/.test(q)) tries.push(q.slice(0, -2));
    if (/s$/.test(q)) tries.push(q.slice(0, -1));
    for (var i = 0; i < tries.length; i++) {
      if (Object.prototype.hasOwnProperty.call(INGREDIENTS, tries[i])) {
        return { id: INGREDIENTS[tries[i]], name: tries[i] };
      }
    }
    return null;
  }

  var GROUP_NAMES = { source: "Made by", meal: "Meal", cuisine: "Cuisine", cook: "Cook" };
  var GROUP_ORDER = ["source", "meal", "cuisine", "cook"];
  var chips = [];  // [{facet, value, label}]

  function hasChip(facet, value) {
    return chips.some(function (c) { return c.facet === facet && c.value === value; });
  }

  function dotFor(o) {
    if (o.facet !== "source") return null;
    var d = document.createElement("span");
    var kind = o.value === "user" || o.value === "imported" ? o.value : "ai";
    d.className = "source-dot source-dot--" + kind;
    d.setAttribute("aria-hidden", "true");
    return d;
  }

  // A row matches a facet if it carries ANY of that facet's chipped values.
  // Fields are pipe-bounded ("|italian|indian|"), so "|italian|" is a whole-
  // value match: "indian" can't half-match "west indian".
  function rowMatches(row, text, ing) {
    if (text && (row.dataset.title || "").indexOf(text) === -1 &&
        !(ing && (row.dataset.ing || "").indexOf("|" + ing.id + "|") !== -1)) return false;
    var byFacet = {};
    chips.forEach(function (c) { (byFacet[c.facet] = byFacet[c.facet] || []).push(c.value); });
    for (var facet in byFacet) {
      var field = row.dataset[facet] || "";
      var ok = byFacet[facet].some(function (v) { return field.indexOf("|" + v + "|") !== -1; });
      if (!ok) return false;
    }
    return true;
  }

  function apply() {
    var text = input.value.trim().toLowerCase();
    var filtering = !!text || chips.length > 0;
    var ing = text ? ingredientFor(text) : null;
    var shown = 0;
    rows.forEach(function (r) {
      if (!r.isConnected) return;           // archived away since load
      var m = rowMatches(r, text, ing);
      r.hidden = !m;
      if (m) shown++;
    });
    countLine.hidden = !filtering;
    box.classList.toggle("has-filters", chips.length > 0);
    countN.textContent = shown + " " + noun + (shown === 1 ? "" : "s") +
      (ing && shown ? (shown === 1 ? " uses " : " use ") + ing.name : "");
    if (nomatch) nomatch.hidden = !filtering || shown > 0;
    save();
  }

  function renderChips() {
    chipTray.innerHTML = "";
    chips.forEach(function (c, i) {
      var chip = document.createElement("button");
      chip.type = "button";
      chip.className = "facet-chip";
      chip.setAttribute("aria-label", "Remove filter " + GROUP_NAMES[c.facet] + ": " + c.label);
      var dot = dotFor(c);
      if (dot) chip.appendChild(dot);
      var v = document.createElement("span");
      v.textContent = c.label;
      chip.appendChild(v);
      var x = document.createElement("span");
      x.className = "facet-chip-x";
      x.setAttribute("aria-hidden", "true");
      x.textContent = "×";
      chip.appendChild(x);
      chip.addEventListener("click", function () {
        chips.splice(i, 1);
        renderChips(); apply();
        if (!panel.hidden) renderPanel();
      });
      chipTray.appendChild(chip);
    });
    chipTray.hidden = chips.length === 0;
  }

  // The panel: every value not already chipped, grouped. Typing narrows it.
  // Unless the filter button opened it, it only shows while something typed
  // matches a value, so plain searching keeps the list in view.
  function renderPanel() {
    // Opened from the button: every value. Otherwise: matches for the text.
    var q = pinned ? "" : input.value.trim().toLowerCase();
    panel.innerHTML = "";
    if (!pinned && !q) { closePanel(); return; }
    var any = false;
    GROUP_ORDER.forEach(function (facet) {
      var vals = OPTIONS.filter(function (o) {
        return o.facet === facet && !hasChip(o.facet, o.value) &&
               (!q || o.label.toLowerCase().indexOf(q) !== -1);
      });
      if (!vals.length) return;
      any = true;
      var group = document.createElement("div");
      group.className = "facet-group";
      var name = document.createElement("p");
      name.className = "facet-group-name";
      name.textContent = GROUP_NAMES[facet];
      group.appendChild(name);
      var list = document.createElement("div");
      list.className = "facet-values";
      vals.forEach(function (o) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "facet-value";
        var dot = dotFor(o);
        if (dot) b.appendChild(dot);
        b.appendChild(document.createTextNode(o.label));
        b.addEventListener("click", function () { addChip(o); });
        list.appendChild(b);
      });
      group.appendChild(list);
      panel.appendChild(group);
    });
    panel.hidden = !any;
    box.classList.toggle("is-open", any);
    toggle.setAttribute("aria-expanded", any ? "true" : "false");
  }

  function closePanel() {
    pinned = false;
    panel.hidden = true;
    box.classList.remove("is-open");
    toggle.setAttribute("aria-expanded", "false");
  }

  function addChip(o) {
    if (!hasChip(o.facet, o.value)) chips.push(o);
    // A suggestion found by typing replaces that text; a pick from the full
    // panel leaves your search alone.
    if (!pinned) input.value = "";
    renderChips(); apply(); closePanel();
    input.blur();                            // put the results in view on a phone
  }

  // The button lives inside the box's <label>: stop the tap reaching the
  // label (which would focus the field and raise the keyboard).
  toggle.addEventListener("mousedown", function (e) { e.preventDefault(); });
  toggle.addEventListener("click", function (e) {
    e.preventDefault();
    if (!panel.hidden) { closePanel(); return; }
    pinned = true;
    input.blur();                            // filters don't need the keyboard
    renderPanel();
  });
  input.addEventListener("input", function () { renderPanel(); apply(); });
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      // Enter takes the first value when typing narrowed the panel to some.
      e.preventDefault();
      var first = !pinned && input.value.trim() && panel.querySelector(".facet-value");
      if (first) first.click(); else { closePanel(); input.blur(); }
    } else if (e.key === "Escape") {
      closePanel();
    } else if (e.key === "Backspace" && input.value === "" && chips.length) {
      // Backspace on an empty box drops the last chip, as in any token field.
      chips.pop();
      renderChips(); apply();
      if (!panel.hidden) renderPanel();
    }
  });
  document.addEventListener("click", function (e) {
    if (!box.contains(e.target)) closePanel();
  });
  clearBtn.addEventListener("click", function () {
    chips = [];
    input.value = "";
    renderChips(); apply(); closePanel();
  });

  // ---- kept across opening a recipe and coming back -------------------------
  function save() {
    try {
      sessionStorage.setItem(STORE_KEY, JSON.stringify({ chips: chips, text: input.value }));
    } catch (e) {}
  }
  (function restore() {
    var saved = null;
    try { saved = JSON.parse(sessionStorage.getItem(STORE_KEY) || "null"); } catch (e) {}
    if (!saved) return;
    // Only values that still exist (a cuisine may have gone since).
    chips = (saved.chips || []).filter(function (c) {
      return OPTIONS.some(function (o) { return o.facet === c.facet && o.value === c.value; });
    });
    input.value = saved.text || "";
  })();

  renderChips();
  apply();
})();
