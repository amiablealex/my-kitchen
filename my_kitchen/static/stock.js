// Stock editing: filter, inline notes (collapsed→expanded), remove, search-to-add.
// Endpoint URLs come from data-* attributes built server-side with url_for(), so
// this works unchanged behind a reverse proxy / sub-path. POSTs carry the CSRF
// token via X-CSRFToken (from base.html's <meta name="csrf-token">). Search is a
// GET (read-only), so it needs no token.

function csrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}

// Show the "nothing in stock" line iff the pantry has no items left.
function refreshEmptyState() {
  const pantry = document.getElementById("pantry");
  if (!pantry) return;
  const empty = pantry.querySelector(".pantry-empty");
  if (!empty) return;
  empty.hidden = pantry.querySelectorAll(".stock-item").length > 0;
}

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

// Save on change (fires on blur when the value changed), then collapse.
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

// Collapse on blur even when unchanged (change won't have fired). Capture phase
// because blur doesn't bubble.
document.addEventListener("blur", function (event) {
  const target = event.target;
  if (target.classList && target.classList.contains("stock-note")) {
    const row = target.closest(".stock-item");
    if (row) collapseNote(row);
  }
}, true);

// --- click delegation: note toggle, remove, add ------------------------------
document.addEventListener("click", function (event) {
  const target = event.target;

  // Open the note editor for this row.
  const noteToggle = target.closest(".stock-note-toggle");
  if (noteToggle) {
    const row = noteToggle.closest(".stock-item");
    if (row) startEditNote(row);
    return;
  }

  // Remove from stock — drop the row in place, update the group count, tidy an
  // emptied group, and reveal the empty-state line if the pantry clears out.
  const removeBtn = target.closest(".stock-remove");
  if (removeBtn) {
    removeBtn.disabled = true;
    fetch(removeBtn.dataset.removeUrl, { method: "POST", headers: { "X-CSRFToken": csrfToken() } })
      .then((r) => { if (!r.ok) throw new Error("remove failed"); return r.json(); })
      .then(() => {
        const li = removeBtn.closest(".stock-item");
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
      })
      .catch(() => { removeBtn.disabled = false; alert("Could not remove item — is the server still running?"); });
    return;
  }

  // Add to stock — reload so the new item appears via the normal server render
  // (also resets the search box).
  const addBtn = target.closest(".stock-add");
  if (addBtn) {
    addBtn.disabled = true;
    fetch(addBtn.dataset.addUrl, { method: "POST", headers: { "X-CSRFToken": csrfToken() } })
      .then((r) => { if (!r.ok) throw new Error("add failed"); return r.json(); })
      .then(() => { window.location.reload(); })
      .catch(() => { addBtn.disabled = false; alert("Could not add item — is the server still running?"); });
    return;
  }
});

// --- instant filter over the rendered pantry ---------------------------------
(function () {
  const input = document.getElementById("pantry-filter");
  if (!input) return;
  const pantry = document.getElementById("pantry");
  const nomatch = pantry ? pantry.querySelector(".pantry-nomatch") : null;

  input.addEventListener("input", function () {
    const q = input.value.trim().toLowerCase();
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
    if (nomatch) nomatch.hidden = anyVisible || !q;
  });
})();

// --- search-to-add ------------------------------------------------------------
// Debounced catalogue search: GET the server-rendered results fragment and drop
// it into the results container. Keep the "add a new ingredient" link's ?name=
// in sync so the manage form arrives pre-filled.
(function () {
  const input = document.getElementById("stock-search-input");
  if (!input) return;
  const results = document.getElementById("stock-search-results");
  const addNew = document.getElementById("stock-add-new-link");
  let timer = null;

  function updateAddNewLink(q) {
    if (!addNew) return;
    const base = addNew.dataset.baseUrl;
    addNew.href = q ? base + "?name=" + encodeURIComponent(q) : base;
  }

  function runSearch(q) {
    if (!results) return;
    if (!q) { results.innerHTML = ""; return; }
    fetch(input.dataset.searchUrl + "?q=" + encodeURIComponent(q))
      .then((r) => { if (!r.ok) throw new Error("search failed"); return r.text(); })
      .then((html) => { results.innerHTML = html; })
      .catch(() => { results.innerHTML = "<p><em>Search is unavailable right now.</em></p>"; });
  }

  input.addEventListener("input", function () {
    const q = input.value.trim();
    updateAddNewLink(q);
    clearTimeout(timer);
    timer = setTimeout(function () { runSearch(q); }, 200);
  });
})();
