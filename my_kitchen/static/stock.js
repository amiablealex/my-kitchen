// Stock editing: single-box search (filters the pantry AND surfaces catalogue
// adds), inline notes, remove-with-undo, and inline create-new-ingredient.
// URLs come from data-* built with url_for() (sub-path safe). POSTs carry
// X-CSRFToken from base.html's meta tag.

function csrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}

function refreshEmptyState() {
  const pantry = document.getElementById("pantry");
  if (!pantry) return;
  const empty = pantry.querySelector(".pantry-empty");
  if (!empty) return;
  empty.hidden = pantry.querySelectorAll(".stock-item").length > 0;
}

// Carry the current query across an add/create reload (one-shot).
var SEARCH_KEY = "mk-stock-search";
function saveSearch(q) { try { sessionStorage.setItem(SEARCH_KEY, q || ""); } catch (e) {} }
function popSearch() {
  try { var v = sessionStorage.getItem(SEARCH_KEY); sessionStorage.removeItem(SEARCH_KEY); return v; }
  catch (e) { return null; }
}
function persistSearch() { var si = document.getElementById("stock-search"); saveSearch(si ? si.value.trim() : ""); }

// --- notes: collapsed preview <-> inline input -------------------------------
function startEditNote(row) {
  const input = row.querySelector(".stock-note");
  if (!input) return;
  row.classList.add("editing");
  input.hidden = false;
  input.focus();
  input.setSelectionRange(input.value.length, input.value.length);
}
function collapseNote(row) {
  const input = row.querySelector(".stock-note");
  const toggle = row.querySelector(".stock-note-toggle");
  const preview = row.querySelector(".stock-note-preview");
  if (!input) return;
  row.classList.remove("editing");
  input.hidden = true;
  const val = input.value.trim();
  if (preview) preview.textContent = val;
  if (toggle) toggle.classList.toggle("has-note", !!val);
}

document.addEventListener("change", function (event) {
  const target = event.target;
  if (!target.classList.contains("stock-note")) return;
  const row = target.closest(".stock-item");
  fetch(target.dataset.noteUrl, {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken() },
    body: new URLSearchParams({ note: target.value }),
  })
    .then((r) => { if (!r.ok) throw new Error("note save failed"); return r.json(); })
    .then((data) => { target.value = data.note; if (row) collapseNote(row); })
    .catch(() => { alert("Could not save note."); });
});

document.addEventListener("blur", function (event) {
  const target = event.target;
  if (target.classList && target.classList.contains("stock-note")) {
    const row = target.closest(".stock-item");
    if (row) collapseNote(row);
  }
}, true);

// --- click delegation: note toggle, remove (undo), add -----------------------
document.addEventListener("click", function (event) {
  const target = event.target;

  const noteToggle = target.closest(".stock-note-toggle");
  if (noteToggle) {
    const row = noteToggle.closest(".stock-item");
    if (row) startEditNote(row);
    return;
  }

  const removeBtn = target.closest(".stock-remove");
  if (removeBtn) {
    const li = removeBtn.closest(".stock-item");
    const nameEl = li ? li.querySelector(".stock-item-name") : null;
    const name = nameEl ? nameEl.textContent.trim() : "the ingredient";
    const addUrl = li ? li.dataset.addUrl : null;
    removeBtn.disabled = true;
    fetch(removeBtn.dataset.removeUrl, { method: "POST", headers: { "X-CSRFToken": csrfToken() } })
      .then((r) => { if (!r.ok) throw new Error("remove failed"); return r.json(); })
      .then(() => {
        const group = removeBtn.closest(".stock-group");
        const ul = li ? li.parentElement : null;
        if (li) li.remove();
        if (group && ul) {
          const remaining = ul.querySelectorAll(".stock-item").length;
          const count = group.querySelector(".stock-group-count");
          if (count) count.textContent = remaining;
          if (remaining === 0) group.remove();
        }
        refreshEmptyState();
        if (window.showToast && addUrl) {
          window.showToast({
            message: "Removed " + name + " from stock",
            actionLabel: "Undo",
            onAction: function () {
              fetch(addUrl, { method: "POST", headers: { "X-CSRFToken": csrfToken() } })
                .then((r) => { if (!r.ok) throw new Error("undo failed"); return r.json(); })
                .then(() => { window.location.reload(); })
                .catch(() => { alert("Could not undo — is the server still running?"); });
            },
          });
        }
      })
      .catch(() => { removeBtn.disabled = false; alert("Could not remove item — is the server still running?"); });
    return;
  }

  // Add an existing catalogue item to stock — persist the query so the reload
  // keeps your search, and the item moves up into the pantry.
  const addBtn = target.closest(".stock-add");
  if (addBtn) {
    addBtn.disabled = true;
    fetch(addBtn.dataset.addUrl, { method: "POST", headers: { "X-CSRFToken": csrfToken() } })
      .then((r) => { if (!r.ok) throw new Error("add failed"); return r.json(); })
      .then(() => { persistSearch(); window.location.reload(); })
      .catch(() => { addBtn.disabled = false; alert("Could not add item — is the server still running?"); });
    return;
  }
});

// --- one search box: filter the pantry + surface catalogue adds --------------
(function () {
  const input = document.getElementById("stock-search");
  if (!input) return;
  const pantry = document.getElementById("pantry");
  const nomatch = pantry ? pantry.querySelector(".pantry-nomatch") : null;
  const catalogue = document.getElementById("stock-catalogue");
  const results = document.getElementById("stock-search-results");
  const newForm = document.getElementById("stock-new-form");
  const newName = document.getElementById("stock-new-name");
  const newNameLabel = document.getElementById("stock-new-name-label");
  const newCategory = document.getElementById("stock-new-category");
  const newStaple = document.getElementById("stock-new-staple");
  const newError = document.getElementById("stock-new-error");
  const newCancel = document.getElementById("stock-new-cancel");
  let timer = null;

  function filterPantry(q) {
    if (!pantry) return;
    const hasGroups = pantry.querySelectorAll(".stock-group").length > 0;
    let anyVisible = false;
    pantry.querySelectorAll(".stock-group").forEach(function (group) {
      let groupVisible = false;
      group.querySelectorAll(".stock-item").forEach(function (item) {
        const match = !q || (item.dataset.name || "").indexOf(q) !== -1;
        item.hidden = !match;
        if (match) groupVisible = true;
      });
      group.hidden = !groupVisible;
      if (groupVisible) anyVisible = true;
    });
    if (nomatch) nomatch.hidden = anyVisible || !q || !hasGroups;
  }

  function hideNewForm() {
    if (!newForm) return;
    newForm.hidden = true;
    if (newError) { newError.hidden = true; newError.textContent = ""; }
  }
  function showNewForm(name) {
    if (!newForm) return;
    if (newName) newName.value = name;
    if (newNameLabel) newNameLabel.textContent = "“" + name + "”";
    if (newStaple) newStaple.checked = false;
    if (newCategory && newCategory.options.length) newCategory.selectedIndex = 0;
    if (newError) { newError.hidden = true; newError.textContent = ""; }
    newForm.hidden = false;
  }

  function runCatalogue(q) {
    hideNewForm();
    if (!results) return;
    if (!q) { results.innerHTML = ""; if (catalogue) catalogue.hidden = true; return; }
    fetch(input.dataset.searchUrl + "?q=" + encodeURIComponent(q))
      .then((r) => { if (!r.ok) throw new Error("search failed"); return r.text(); })
      .then((html) => {
        results.innerHTML = html;
        const hasContent = !!results.querySelector(".search-results, .search-empty");
        if (catalogue) catalogue.hidden = !hasContent;
      })
      .catch(() => {
        results.innerHTML = "<p class='search-empty'><em>Search is unavailable right now.</em></p>";
        if (catalogue) catalogue.hidden = false;
      });
  }

  input.addEventListener("input", function () {
    const raw = input.value.trim();
    filterPantry(raw.toLowerCase());
    clearTimeout(timer);
    timer = setTimeout(function () { runCatalogue(raw); }, 200);
  });

  if (results) {
    results.addEventListener("click", function (ev) {
      const trig = ev.target.closest("#stock-new-trigger");
      if (!trig) return;
      showNewForm(trig.dataset.newName || input.value.trim());
      if (newCategory) newCategory.focus();
    });
  }

  if (newCancel) newCancel.addEventListener("click", hideNewForm);

  if (newForm) {
    newForm.addEventListener("submit", function (ev) {
      ev.preventDefault();
      const name = (newName ? newName.value : "").trim();
      if (!name) return;
      const submitBtn = newForm.querySelector('button[type="submit"]');
      if (submitBtn) submitBtn.disabled = true;
      fetch(newForm.dataset.createUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
        body: new URLSearchParams({
          name: name,
          category_id: newCategory ? newCategory.value : "",
          is_staple: newStaple && newStaple.checked ? "on" : "",
        }),
      })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, data: d }; }); })
        .then(function (res) {
          if (!res.ok || !res.data.ok) {
            if (newError) { newError.textContent = (res.data && res.data.message) || "Could not add."; newError.hidden = false; }
            if (submitBtn) submitBtn.disabled = false;
            return;
          }
          persistSearch();
          window.location.reload();
        })
        .catch(function () {
          if (newError) { newError.textContent = "Could not add — is the server still running?"; newError.hidden = false; }
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  }

  // Restore the query after an add/create reload (one-shot): refilter + refetch.
  (function restore() {
    const q = popSearch();
    if (!q) return;
    input.value = q;
    filterPantry(q.toLowerCase());
    runCatalogue(q);
  })();
})();
