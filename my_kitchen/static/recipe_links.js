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

  // --- edit-mode toggle -------------------------------------------------------
  toggle.addEventListener("click", function () {
    var on = section.classList.toggle("is-editing");
    toggle.setAttribute("aria-pressed", on ? "true" : "false");
    if (hint) hint.hidden = !on;
    if (!on) closeEditor();
  });

  // --- open / close the shared editor under a row -----------------------------
  function openEditor(row) {
    activeRow = row;
    var pill = row.querySelector(".link-pill");
    var linkedId = pill ? pill.dataset.linkedId : "";
    var linkedName = linkedId && pill ? pill.textContent.trim() : "";

    elRawText.textContent = row.dataset.rawText || "";
    if (linkedId) {
      elCurrentName.textContent = linkedName;
      elCurrent.hidden = false;
    } else {
      elCurrent.hidden = true;
    }

    elSearch.value = "";
    renderResults("");
    elAddName.value = row.dataset.rawText || "";
    elAddStaple.checked = false;
    if (elAddCategory.options.length) elAddCategory.selectedIndex = 0;
    hideAddError();
    if (elAddDetails) elAddDetails.open = false;

    row.appendChild(editor); // move the single panel inline under this row
    editor.hidden = false;
    elSearch.focus();
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
    var pill = activeRow ? activeRow.querySelector(".link-pill") : null;
    var currentId = pill ? pill.dataset.linkedId : "";
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
      if (String(item.id) === String(currentId)) {
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

  function setPill(row, id, name) {
    var pill = row.querySelector(".link-pill");
    if (!pill) return;
    if (id) {
      pill.textContent = name;
      pill.classList.remove("link-pill--none");
      pill.dataset.linkedId = String(id);
    } else {
      pill.textContent = "not linked";
      pill.classList.add("link-pill--none");
      pill.dataset.linkedId = "";
    }
  }

  // Link to an existing catalogue ingredient (delegated on the results list).
  elResults.addEventListener("click", function (ev) {
    var btn = ev.target.closest(".ri-result-btn");
    if (!btn || btn.disabled || !activeRow) return;
    var row = activeRow;
    btn.disabled = true;
    postForm(row.dataset.linkUrl, { ingredient_id: btn.dataset.ingredientId })
      .then(function (res) {
        if (!res.ok) throw new Error((res.data && res.data.message) || "Could not link.");
        setPill(row, res.data.ingredient_id, res.data.name);
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
        setPill(row, null, null);
        closeEditor();
      })
      .catch(function (err) {
        alert(err.message || "Could not unlink — is the server still running?");
      })
      .finally(function () {
        elUnlink.disabled = false;
      });
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
        setPill(row, res.data.ingredient_id, res.data.name);
        closeEditor();
      })
      .catch(function () {
        showAddError("Could not add — is the server still running?");
      })
      .finally(function () {
        elAddSubmit.disabled = false;
      });
  });
})();
