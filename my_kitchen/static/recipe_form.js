// Create / edit recipe form (Phase 4b). Build-then-submit: ingredient + step
// rows are added/removed client-side under index-keyed names (ing-{i}-*,
// prep|cook|tips-{i}-*), and the whole form POSTs at once — unlike the 4a
// recipe link editor, which AJAX-edits already-saved rows. The shared catalogue
// picker mirrors the 4a panel; "Add & use" creates a catalogue ingredient via
// the create-only endpoint (url injected, ingress-safe) and selects it.
//
// Drag-to-reorder: each list is its own SortableJS instance with NO shared
// group, so rows stay contained within their section (a prep step can't be
// dragged into cook). Because the server parses rows by the integer baked into
// each field name (sorted ascending), DOM order alone would be ignored — so we
// renumber every row's name attributes to contiguous DOM order on submit
// (reindexRows). After that, ascending index == on-screen order == saved order
// (recipe_ingredients.position and the *_steps_json array order both follow).
(function () {
  function readJSON(id, fallback) {
    var el = document.getElementById(id);
    if (!el) return fallback;
    try { return JSON.parse(el.textContent) || fallback; } catch (e) { return fallback; }
  }
  var catalogue = readJSON("rf-catalogue-data", []);
  var prefill = readJSON("rf-prefill-data", {});
  var urls = readJSON("rf-urls", {});
  // Imported recipes (Phase 34) keep each line's own wording and may leave a
  // line unlinked; hand-made ones link every line to the catalogue.
  var imported = readJSON("rf-imported", false);

  // Six-dot grip, themed via currentColor. Sortable's `handle` option targets
  // this, so dragging only starts from the grip — inputs stay fully tappable.
  var DRAG_HANDLE =
    '<span class="rf-drag-handle" title="Drag to reorder" aria-hidden="true">' +
      '<svg viewBox="0 0 20 20" width="18" height="18" focusable="false">' +
        '<circle cx="7" cy="4" r="1.5"/><circle cx="13" cy="4" r="1.5"/>' +
        '<circle cx="7" cy="10" r="1.5"/><circle cx="13" cy="10" r="1.5"/>' +
        '<circle cx="7" cy="16" r="1.5"/><circle cx="13" cy="16" r="1.5"/>' +
      '</svg>' +
    '</span>';

  function csrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") : "";
  }
  function el(tag, cls) { var e = document.createElement(tag); if (cls) e.className = cls; return e; }
  function setVal(id, v) { var e = document.getElementById(id); if (e) e.value = (v == null ? "" : v); }

  // ---- scalar fields -------------------------------------------------------
  setVal("rf-title", prefill.title);
  setVal("rf-blurb", prefill.blurb);
  setVal("rf-intro", prefill.intro);
  setVal("rf-servings", prefill.servings || "2");
  var mt = document.getElementById("rf-meal-type");
  if (mt && prefill.meal_type) mt.value = prefill.meal_type;

  // ---- cuisine, gated by meal type (mirrors the wizard hierarchy) ----------
  var cuisineSel = document.getElementById("rf-cuisine");
  var cuisineLabel = document.getElementById("rf-cuisine-label");
  var cuisineMealTypes = readJSON("rf-cuisine-meal-types", []);
  if (cuisineSel && prefill.cuisine) cuisineSel.value = prefill.cuisine;
  function syncCuisineVisibility() {
    var allowed = mt && mt.value && cuisineMealTypes.indexOf(mt.value) !== -1;
    if (cuisineLabel) cuisineLabel.hidden = !allowed;
    if (!allowed && cuisineSel) cuisineSel.value = "";  // never submit a stale cuisine
  }
  if (mt) mt.addEventListener("change", syncCuisineVisibility);
  syncCuisineVisibility();

  // ---- ingredient rows -----------------------------------------------------
  var ingList = document.getElementById("rf-ing-list");
  // Keep the unlinked count right when an optional box changes or a row goes.
  ingList.addEventListener("change", function () { syncUnlinked(); });
  if (window.MutationObserver) new MutationObserver(function () { syncUnlinked(); }).observe(ingList, { childList: true });
  var ingIdx = 0;

  // The line as the source wrote it, shown under its link when it differs
  // (or as the label when it isn't linked). Picking a new link by hand drops
  // it, so the old wording can't sit under a different ingredient.
  function syncRaw(row) {
    var raw = row.querySelector(".rf-ing-raw").value;
    var name = row.querySelector(".rf-ing-name").value;
    var note = row.querySelector(".rf-ing-rawnote");
    var lbl = row.querySelector(".rf-ing-chosen");
    var linked = !!row.querySelector(".rf-ing-id").value;
    note.textContent = raw;
    note.hidden = !(raw && linked && raw.toLowerCase() !== name.toLowerCase());
    syncUnlinked();
    if (!linked && raw) {
      lbl.textContent = raw;
      lbl.classList.remove("rf-ing-chosen--empty");
      lbl.classList.add("rf-ing-chosen--unlinked");
    } else {
      lbl.classList.remove("rf-ing-chosen--unlinked");
    }
  }

  // "N ingredients aren't linked" on an import (0.36.2): required lines with
  // the source's wording but no link keep the recipe out of suggestions.
  function syncUnlinked() {
    var note = document.getElementById("rf-unlinked-note");
    if (!note) return;
    var n = Array.prototype.filter.call(ingList.querySelectorAll(".rf-ing-row"), function (r) {
      return !r.querySelector(".rf-ing-id").value && r.querySelector(".rf-ing-raw").value &&
             !r.querySelector(".rf-ing-tobuycb").checked;
    }).length;
    note.hidden = n === 0;
    document.getElementById("rf-unlinked-count").textContent =
      n + " ingredient" + (n === 1 ? " isn't" : "s aren't") + " linked";
  }

  function setRowLink(row, id, name, byHand) {
    var hidId = row.querySelector(".rf-ing-id");
    var hidName = row.querySelector(".rf-ing-name");
    var lbl = row.querySelector(".rf-ing-chosen");
    if (byHand) row.querySelector(".rf-ing-raw").value = "";
    if (id) {
      hidId.value = String(id);
      hidName.value = name;
      lbl.textContent = name;
      lbl.classList.remove("rf-ing-chosen--empty");
    } else {
      hidId.value = "";
      hidName.value = "";
      lbl.textContent = "No ingredient selected";
      lbl.classList.add("rf-ing-chosen--empty");
    }
    syncRaw(row);
  }

  function addIngredientRow(data) {
    data = data || {};
    var i = ingIdx++;
    var row = el("li", "rf-ing-row");
    row.dataset.idx = String(i);
    row.innerHTML =
      DRAG_HANDLE +
      '<div class="rf-row-body">' +
        '<div class="rf-ing-pick">' +
          '<span class="rf-ing-chosen rf-ing-chosen--empty">No ingredient selected</span>' +
          '<input type="hidden" class="rf-ing-id" name="ing-' + i + '-ingredient_id" value="">' +
          '<input type="hidden" class="rf-ing-name" name="ing-' + i + '-name" value="">' +
          '<input type="hidden" class="rf-ing-raw" name="ing-' + i + '-raw" value="">' +
          '<button type="button" class="btn btn--sm rf-ing-choose">Pick</button>' +
          '<span class="rf-ing-rawnote" hidden></span>' +
        '</div>' +
        '<div class="rf-ing-fields">' +
          '<input type="text" class="rf-ing-amount" name="ing-' + i + '-amount" placeholder="amount" value="">' +
          '<input type="text" class="rf-ing-unit" name="ing-' + i + '-unit" placeholder="unit" value="">' +
          '<label class="rf-ing-tobuy"><input type="checkbox" class="rf-ing-tobuycb" name="ing-' + i + '-to_buy"> optional extra</label>' +
          '<button type="button" class="rf-row-remove" aria-label="Remove ingredient">&times;</button>' +
        '</div>' +
      '</div>';
    ingList.appendChild(row);
    row.querySelector(".rf-ing-raw").value = data.raw || "";
    if (data.ingredient_id) setRowLink(row, data.ingredient_id, data.name || "");
    else syncRaw(row);
    row.querySelector(".rf-ing-amount").value = data.amount || "";
    row.querySelector(".rf-ing-unit").value = data.unit || "";
    if (data.to_buy) row.querySelector(".rf-ing-tobuycb").checked = true;
    return row;
  }

  ingList.addEventListener("click", function (ev) {
    var rm = ev.target.closest(".rf-row-remove");
    if (rm) {
      var r = rm.closest(".rf-ing-row");
      if (r) { if (activeRow === r) closePicker(); r.remove(); }
      return;
    }
    var pick = ev.target.closest(".rf-ing-choose") || ev.target.closest(".rf-ing-chosen");
    if (pick) {
      var row = pick.closest(".rf-ing-row");
      if (row) (activeRow === row && !picker.hidden) ? closePicker() : openPicker(row);
    }
  });

  document.getElementById("rf-add-ing").addEventListener("click", function () { addIngredientRow(); });

  // ---- shared catalogue picker --------------------------------------------
  var picker = document.getElementById("rf-picker");
  var pSearch = document.getElementById("rf-picker-search");
  var pResults = document.getElementById("rf-picker-results");
  var pClose = document.getElementById("rf-picker-close");
  var pAddDetails = document.getElementById("rf-picker-add");
  var pAddName = document.getElementById("rf-add-name");
  var pAddCategory = document.getElementById("rf-add-category");
  var pAddStaple = document.getElementById("rf-add-staple");
  var pAddError = document.getElementById("rf-add-error");
  var pAddSubmit = document.getElementById("rf-add-submit");
  var activeRow = null;

  function openPicker(row) {
    activeRow = row;
    pSearch.value = "";
    renderResults("");
    pAddName.value = "";
    pAddStaple.checked = false;
    if (pAddCategory.options.length) pAddCategory.selectedIndex = 0;
    hideAddError();
    if (pAddDetails) pAddDetails.open = false;
    // Append inside the row BODY (not the <li> itself) so the picker drops
    // full-width below the fields and never becomes a stray flex/sort sibling.
    (row.querySelector(".rf-row-body") || row).appendChild(picker);
    picker.hidden = false;
    pSearch.focus();
  }
  function closePicker() { picker.hidden = true; activeRow = null; }
  pClose.addEventListener("click", closePicker);

  function renderResults(q) {
    var query = (q || "").trim().toLowerCase();
    pResults.innerHTML = "";
    if (!query) return;
    var shown = 0;
    for (var i = 0; i < catalogue.length && shown < 25; i++) {
      var item = catalogue[i];
      if (item.name.toLowerCase().indexOf(query) === -1) continue;
      var li = el("li", "rf-result");
      var b = el("button", "rf-result-btn");
      b.type = "button";
      b.dataset.ingredientId = item.id;
      b.dataset.ingredientName = item.name;
      b.textContent = item.name;
      li.appendChild(b);
      pResults.appendChild(li);
      shown++;
    }
    if (shown === 0) {
      var empty = el("li", "rf-result-empty");
      empty.textContent = "No catalogue match — add it below.";
      pResults.appendChild(empty);
    }
  }
  pSearch.addEventListener("input", function () { renderResults(pSearch.value); });

  pResults.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".rf-result-btn");
    if (!btn || !activeRow) return;
    setRowLink(activeRow, btn.dataset.ingredientId, btn.dataset.ingredientName, true);
    closePicker();
  });

  function showAddError(m) { pAddError.textContent = m; pAddError.hidden = false; }
  function hideAddError() { pAddError.textContent = ""; pAddError.hidden = true; }

  pAddSubmit.addEventListener("click", function () {
    if (!activeRow) return;
    var name = (pAddName.value || "").trim();
    if (!name) { showAddError("Name is required."); return; }
    hideAddError();
    pAddSubmit.disabled = true;
    var row = activeRow;
    fetch(urls.add, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken() },
      body: new URLSearchParams({
        name: name,
        category_id: pAddCategory.value,
        is_staple: pAddStaple.checked ? "on" : "",
      }),
    })
      .then(function (r) {
        return r.json().catch(function () { return {}; })
          .then(function (d) { return { ok: r.ok, data: d }; });
      })
      .then(function (res) {
        if (!res.ok) { showAddError((res.data && res.data.message) || "Could not add."); return; }
        catalogue.push({ id: res.data.ingredient_id, name: res.data.name });
        catalogue.sort(function (a, b) { return a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1; });
        setRowLink(row, res.data.ingredient_id, res.data.name, true);
        closePicker();
      })
      .catch(function () { showAddError("Could not add — is the server still running?"); })
      .finally(function () { pAddSubmit.disabled = false; });
  });

  // ---- step rows -----------------------------------------------------------
  var stepIdx = { prep: 0, cook: 0, tips: 0 };
  function addStepRow(listEl, data) {
    data = data || {};
    var prefix = listEl.dataset.prefix;
    var withTimer = listEl.dataset.timer === "1";
    var i = stepIdx[prefix]++;
    var row = el("li", "rf-step-row");
    row.dataset.idx = String(i);
    var body =
      '<input type="text" class="rf-step-title" name="' + prefix + '-' + i + '-title" placeholder="title (optional)" value="">' +
      '<textarea class="rf-step-text" name="' + prefix + '-' + i + '-text" rows="2" placeholder="what to do"></textarea>';
    if (withTimer) {
      body += '<input type="number" class="rf-step-timer" name="' + prefix + '-' + i + '-timer" min="0" placeholder="timer (min)" value="">';
    }
    body += '<button type="button" class="rf-row-remove" aria-label="Remove step">&times;</button>';
    row.innerHTML = DRAG_HANDLE + '<div class="rf-row-body">' + body + '</div>';
    listEl.appendChild(row);
    row.querySelector(".rf-step-title").value = data.title || "";
    row.querySelector(".rf-step-text").value = data.text || "";
    if (withTimer) { var t = row.querySelector(".rf-step-timer"); if (t) t.value = data.timer || ""; }
    return row;
  }

  document.querySelectorAll(".rf-add-step").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var list = document.getElementById(btn.dataset.target);
      if (list) addStepRow(list, {});
    });
  });
  document.querySelectorAll(".rf-step-list").forEach(function (list) {
    list.addEventListener("click", function (ev) {
      var rm = ev.target.closest(".rf-row-remove");
      if (!rm) return;
      var r = rm.closest(".rf-step-row");
      if (r) r.remove();
    });
  });

  // ---- hydrate from prefill (edit / error re-render) -----------------------
  (function hydrate() {
    var prepList = document.getElementById("rf-prep-list");
    var cookList = document.getElementById("rf-cook-list");
    var tipsList = document.getElementById("rf-tips-list");
    (prefill.prep || []).forEach(function (s) { addStepRow(prepList, s); });
    (prefill.cook || []).forEach(function (s) { addStepRow(cookList, s); });
    (prefill.tips || []).forEach(function (s) { addStepRow(tipsList, s); });
    (prefill.ingredients || []).forEach(function (d) { addIngredientRow(d); });
    if (!(prefill.ingredients || []).length) addIngredientRow();      // one to start
    if (!(prefill.cook || []).length) addStepRow(cookList, {});       // cook is required
  })();

  // ---- drag-to-reorder (SortableJS; per-list, no shared group) -------------
  function initSortable(listEl) {
    if (!listEl || !window.Sortable) return;
    window.Sortable.create(listEl, {
      handle: ".rf-drag-handle",
      animation: 150,
      ghostClass: "rf-sort-ghost",
      chosenClass: "rf-sort-chosen",
      dragClass: "rf-sort-drag",
    });
  }
  [ingList,
   document.getElementById("rf-prep-list"),
   document.getElementById("rf-cook-list"),
   document.getElementById("rf-tips-list")].forEach(initSortable);

  // Renumber every row's index-keyed name attributes to contiguous DOM order,
  // so the server (which sorts rows by that integer) honours the arrangement.
  // Only the middle number changes: ing-3-amount -> ing-0-amount, etc. The
  // picker holds no name attributes, so it's untouched wherever it's parked.
  function reindexRows(listEl) {
    if (!listEl) return;
    Array.prototype.forEach.call(listEl.children, function (row, p) {
      Array.prototype.forEach.call(row.querySelectorAll("[name]"), function (inp) {
        inp.name = inp.name.replace(/^([a-z]+)-\d+-/, "$1-" + p + "-");
      });
      row.dataset.idx = String(p);
    });
  }

  // ---- light client guard (server validates regardless) -------------------
  document.getElementById("recipe-form").addEventListener("submit", function (ev) {
    reindexRows(ingList);
    reindexRows(document.getElementById("rf-prep-list"));
    reindexRows(document.getElementById("rf-cook-list"));
    reindexRows(document.getElementById("rf-tips-list"));

    var hasIng = false;
    ingList.querySelectorAll(".rf-ing-row").forEach(function (r) {
      if (r.querySelector(".rf-ing-id").value || (imported && r.querySelector(".rf-ing-raw").value)) hasIng = true;
    });
    if (!hasIng) {
      ev.preventDefault();
      alert("Add at least one ingredient and pick its catalogue link.");
    }
  });
})();
