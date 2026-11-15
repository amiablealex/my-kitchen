// Recipe ingredient link editor (Phase 4a). Makes the catalogue links on the
// recipe page editable inline: re-link, unlink, or add a new catalogue
// ingredient and link it — all via AJAX. Endpoint URLs are injected per row
// with url_for (data-* attributes), so this works behind the HA ingress
// sub-path; POSTs carry the CSRF token via the X-CSRFToken header (same pattern
// as stock.js). Link edits are a property of the recipe and shared across the
// household — there is no per-user scoping here.
(function () {
  var section = document.getElementById("ingredients-section");
  if (!section) return;
  var list = document.getElementById("ingredient-list");
  var toggle = document.getElementById("link-edit-toggle");
  var hint = document.getElementById("link-edit-hint");
  var editor = document.getElementById("ri-editor");
  if (!list || !toggle || !editor) return;

  // Injected catalogue: [{id, name}] — active, incl. staples, excl. retired.
  var catalogue = [];
  try {
    var dataEl = document.getElementById("link-catalogue-data");
    if (dataEl) catalogue = JSON.parse(dataEl.textContent) || [];
  } catch (e) {
    catalogue = [];
  }

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  // Editor sub-elements (single shared panel).
  var elClose = document.getElementById("ri-editor-close");
  var elRawText = document.getElementById("ri-editor-rawtext");
  var elCurrent = document.getElementById("ri-editor-current");
  var elCurrentName = document.getElementById("ri-editor-current-name");
  var elUnlink = document.getElementById("ri-editor-unlink");
  var elSearch = document.getElementById("ri-editor-search");
  var elResults = document.getElementById("ri-editor-results");
  var elAddDetails = editor.querySelector(".ri-editor-add");
  var elAddName = document.getElementById("ri-add-name");
  var elAddCategory = document.getElementById("ri-add-category");
  var elAddStaple = document.getElementById("ri-add-staple");
  var elAddError = document.getElementById("ri-add-error");
  var elAddSubmit = document.getElementById("ri-add-submit");

  var activeRow = null; // the <li> currently being edited
  // Which link the search and add-new act on: the line's main link, or its
  // "or" alternative (0.38.0). On an "or" line with a main link (0.39.0) the
  // editor shows both links as rows, and the search only appears once Change
  // or Add has been tapped — headed with what it will do.
  var slot = "main";
  var elOr = document.getElementById("ri-editor-or");
  var elOrMain = document.getElementById("ri-or-main");
  var elOrUnlink = document.getElementById("ri-or-unlink");
  var elOrAlt = document.getElementById("ri-or-alt");
  var elOrAltActions = document.getElementById("ri-or-alt-actions");
  var elOrAdd = document.getElementById("ri-or-add");
  var elAltRemove = document.getElementById("ri-editor-alt-remove");
  var elSearchArea = document.getElementById("ri-editor-search-area");
  var elSearchText = document.getElementById("ri-editor-search-text");

  function linkOf(row, alt) {
    var p = row.querySelector(alt ? ".link-pill--alt" : ".link-pill:not(.link-pill--alt)");
    return p && p.dataset.linkedId ? { id: p.dataset.linkedId, name: p.textContent.trim() } : null;
  }

  // Lay the editor out for this row: the two-row "or" view, or the plain one.
  function layout(row) {
    var main = linkOf(row, false), alt = linkOf(row, true);
    var orMode = row.hasAttribute("data-or") && !!main;
    elOr.hidden = !orMode;
    elCurrent.hidden = orMode || !main;
    if (main && !orMode) elCurrentName.textContent = main.name;
    if (orMode) {
      elOrMain.textContent = main.name;
      elOrAlt.hidden = elOrAltActions.hidden = !alt;
      elOrAdd.hidden = !!alt;
      if (alt) elOrAlt.textContent = alt.name;
    }
    elSearchArea.hidden = orMode;   // shown by Change / Add
    slot = "main";
    elSearchText.textContent = "Link to a catalogue ingredient";
  }

  // Change (main or alternative) / Add the other ingredient: open the search.
  function openSearch(nextSlot, heading) {
    slot = nextSlot;
    elSearchText.textContent = heading;
    elSearchArea.hidden = false;
    elSearch.value = "";
    renderResults("");
    elAddName.value = "";
    if (elAddDetails) elAddDetails.open = false;
    elSearch.focus();
  }

  // --- edit-mode toggle -------------------------------------------------------
  toggle.addEventListener("click", function () {
    var on = section.classList.toggle("is-editing");
    toggle.setAttribute("aria-pressed", on ? "true" : "false");
    var label = toggle.querySelector("span");          // 0.30.2: Edit links ↔ Done
    if (label) label.textContent = on ? "Done editing links" : "Edit links";
    if (hint) hint.hidden = !on;
    if (!on) closeEditor();
  });

  // --- open / close the shared editor under a row -----------------------------
  function openEditor(row) {
    activeRow = row;
    elRawText.textContent = row.dataset.rawText || "";

    elSearch.value = "";
    renderResults("");
    elAddName.value = row.dataset.rawText || "";
    elAddStaple.checked = false;
    if (elAddCategory.options.length) elAddCategory.selectedIndex = 0;
    hideAddError();
    if (elAddDetails) elAddDetails.open = false;

    layout(row);
    row.appendChild(editor); // move the single panel inline under this row
    editor.hidden = false;
    if (!elSearchArea.hidden) elSearch.focus();
  }

  function closeEditor() {
    editor.hidden = true;
    activeRow = null;
  }

  elClose.addEventListener("click", closeEditor);

  // Open the editor when a row's edit button is clicked (delegated).
  list.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".ri-edit-btn");
    if (!btn) return;
    var row = btn.closest(".ingredient-row");
    if (!row) return;
    if (activeRow === row && !editor.hidden) {
      closeEditor();
    } else {
      openEditor(row);
    }
  });

  // --- client-side catalogue search ------------------------------------------
  function renderResults(q) {
    var query = (q || "").trim().toLowerCase();
    elResults.innerHTML = "";
    if (!query) return;
    var taken = activeRow ? Array.prototype.map.call(activeRow.querySelectorAll(".link-pill"),
      function (p) { return p.dataset.linkedId; }).filter(Boolean) : [];
    var shown = 0;
    for (var i = 0; i < catalogue.length && shown < 25; i++) {
      var item = catalogue[i];
      if (item.name.toLowerCase().indexOf(query) === -1) continue;
      var li = document.createElement("li");
      li.className = "ri-result";
      var b = document.createElement("button");
      b.type = "button";
      b.className = "ri-result-btn";
      b.dataset.ingredientId = item.id;
      if (taken.indexOf(String(item.id)) !== -1) {
        b.disabled = true;
        b.textContent = item.name + " (linked)";
      } else {
        b.textContent = item.name;
      }
      li.appendChild(b);
      elResults.appendChild(li);
      shown++;
    }
    if (shown === 0) {
      var empty = document.createElement("li");
      empty.className = "ri-result-empty";
      empty.textContent = "No catalogue match — add it below.";
      elResults.appendChild(empty);
    }
  }

  elSearch.addEventListener("input", function () {
    renderResults(elSearch.value);
  });

  // --- link / unlink / add — AJAX --------------------------------------------
  function postForm(url, params) {
    return fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken() },
      body: new URLSearchParams(params),
    }).then(function (r) {
      return r
        .json()
        .catch(function () {
          return {};
        })
        .then(function (data) {
          return { ok: r.ok, data: data };
        });
    });
  }

  // Stock mark in the bullet position (0.37.0): the server sends the line's
  // state with every link change, so the mark follows the link.
  var MARK_LABELS = { have: "In stock", need: "Not in stock", unlinked: "Not linked" };
  function setMark(row, state, haveLabel) {
    var mark = row.querySelector(".stock-mark");
    if (!mark || !state) return;
    mark.className = "stock-mark stock-mark--" + state;
    var label = state === "have" && haveLabel ? haveLabel : MARK_LABELS[state];
    if (label) {
      mark.setAttribute("role", "img");
      mark.setAttribute("aria-label", label);
      mark.setAttribute("title", label);
      mark.removeAttribute("aria-hidden");
    } else {
      ["role", "aria-label", "title"].forEach(function (a) { mark.removeAttribute(a); });
      mark.setAttribute("aria-hidden", "true");
    }
  }

  // Both pills and the mark follow the server's answer after any change.
  function setPill(row, d) {
    setMark(row, d.stock, d.stock_label);
    var pill = row.querySelector(".link-pill:not(.link-pill--alt)");
    if (pill) {
      if (d.ingredient_id) {
        pill.textContent = d.name;
        pill.classList.remove("link-pill--none");
        pill.dataset.linkedId = String(d.ingredient_id);
      } else {
        pill.textContent = "not linked";
        pill.classList.add("link-pill--none");
        pill.dataset.linkedId = "";
      }
    }
    var or = row.querySelector(".link-or");
    var alt = row.querySelector(".link-pill--alt");
    if (or && alt) {
      or.hidden = !d.alt_id;
      alt.textContent = d.alt_name || "";
      alt.dataset.linkedId = d.alt_id ? String(d.alt_id) : "";
    }
    syncUnlinkedNote();
  }

  // ---- "N ingredients aren't linked" (0.36.2) ------------------------------
  // Required (not optional-extra) lines without a link keep the recipe out of
  // suggestions. The note counts them live and hides at zero; "Link it" turns
  // on edit mode and opens the editor on the first one.
  function unlinkedRows() {
    return Array.prototype.filter.call(document.querySelectorAll(".ingredient-row"), function (r) {
      return !r.hasAttribute("data-optional") && r.querySelector(".link-pill--none");
    });
  }
  function syncUnlinkedNote() {
    var note = document.getElementById("unlinked-note");
    if (!note) return;
    var n = unlinkedRows().length;
    note.hidden = n === 0;
    document.getElementById("unlinked-count").textContent =
      n + " ingredient" + (n === 1 ? " isn't" : "s aren't") + " linked";
  }
  var fixBtn = document.getElementById("unlinked-fix");
  if (fixBtn) fixBtn.addEventListener("click", function () {
    var first = unlinkedRows()[0];
    if (!first) return;
    var toggle = document.getElementById("link-edit-toggle");
    if (toggle && toggle.getAttribute("aria-pressed") !== "true") toggle.click();
    var edit = first.querySelector(".ri-edit-btn");
    if (edit) edit.click();
    first.scrollIntoView({ block: "center", behavior: "smooth" });
  });

  // Link to an existing catalogue ingredient (delegated on the results list).
  elResults.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".ri-result-btn");
    if (!btn || btn.disabled || !activeRow) return;
    var row = activeRow;
    btn.disabled = true;
    postForm(row.dataset.linkUrl, { ingredient_id: btn.dataset.ingredientId, slot: slot })
      .then(function (res) {
        if (!res.ok) throw new Error((res.data && res.data.message) || "Could not link.");
        setPill(row, res.data);
        closeEditor();
      })
      .catch(function (err) {
        btn.disabled = false;
        alert(err.message || "Could not link — is the server still running?");
      });
  });

  // Unlink the current row.
  elUnlink.addEventListener("click", function () {
    if (!activeRow) return;
    var row = activeRow;
    elUnlink.disabled = true;
    postForm(row.dataset.linkUrl, { ingredient_id: "" })
      .then(function (res) {
        if (!res.ok) throw new Error((res.data && res.data.message) || "Could not unlink.");
        setPill(row, res.data);
        closeEditor();
      })
      .catch(function (err) {
        alert(err.message || "Could not unlink — is the server still running?");
      })
      .finally(function () {
        elUnlink.disabled = false;
      });
  });

  editor.addEventListener("click", function (ev) {
    var ch = ev.target.closest("[data-or-change]");
    if (!ch || !activeRow) return;
    var which = ch.dataset.orChange;
    var cur = linkOf(activeRow, which === "alt");
    openSearch(which, "Replace " + (cur ? cur.name : "it") + " with…");
  });
  elOrAdd.addEventListener("click", function () {
    if (activeRow) openSearch("alt", "Add the other ingredient");
  });
  // Unlink on the "or" view's main row: same as the plain Unlink (the server
  // promotes the alternative to the main link).
  elOrUnlink.addEventListener("click", function () { elUnlink.click(); });

  // Remove the alternative; the main link stays.
  elAltRemove.addEventListener("click", function () {
    if (!activeRow) return;
    var row = activeRow;
    elAltRemove.disabled = true;
    postForm(row.dataset.linkUrl, { ingredient_id: "", slot: "alt" })
      .then(function (res) {
        if (!res.ok) throw new Error((res.data && res.data.message) || "Could not remove.");
        setPill(row, res.data);
        closeEditor();
      })
      .catch(function (err) { alert(err.message || "Could not remove — is the server still running?"); })
      .finally(function () { elAltRemove.disabled = false; });
  });

  // Add a new catalogue ingredient + link, in one action.
  function showAddError(msg) {
    elAddError.textContent = msg;
    elAddError.hidden = false;
  }
  function hideAddError() {
    elAddError.textContent = "";
    elAddError.hidden = true;
  }

  elAddSubmit.addEventListener("click", function () {
    if (!activeRow) return;
    var row = activeRow;
    var name = (elAddName.value || "").trim();
    if (!name) {
      showAddError("Name is required.");
      return;
    }
    hideAddError();
    elAddSubmit.disabled = true;
    postForm(row.dataset.addLinkUrl, {
      slot: slot,
      name: name,
      category_id: elAddCategory.value,
      is_staple: elAddStaple.checked ? "on" : "",
    })
      .then(function (res) {
        if (!res.ok) {
          showAddError((res.data && res.data.message) || "Could not add that ingredient.");
          return;
        }
        // The new ingredient now exists — reflect it in the in-memory catalogue
        // so a later search this session finds it, then update the pill + close.
        catalogue.push({ id: res.data.ingredient_id, name: res.data.name });
        catalogue.sort(function (a, b) {
          return a.name.toLowerCase() < b.name.toLowerCase() ? -1 : 1;
        });
        setPill(row, res.data);
        closeEditor();
      })
      .catch(function () {
        showAddError("Could not add — is the server still running?");
      })
      .finally(function () {
        elAddSubmit.disabled = false;
      });
  });

  // Back to this page from the stock page: the browser may show its cached
  // copy, so re-read the marks (0.37.0). A normal load is already fresh.
  window.addEventListener("pageshow", function (e) {
    if (!e.persisted || !list.dataset.stockUrl) return;
    fetch(list.dataset.stockUrl, { headers: { Accept: "application/json" }, credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (states) {
        if (!states) return;
        list.querySelectorAll(".ingredient-row").forEach(function (row) {
          var st = states[row.dataset.riId];
          if (st) setMark(row, st.state, st.label);
        });
      })
      .catch(function () {});
  });
})();
