// Stock editing: inline notes, remove-from-stock, and search-to-add. Used on
// both /stock and the wizard's /cook/stock step (same partial, same JS).
// Endpoint URLs come from data-* attributes built server-side with url_for(),
// so this works unchanged behind a reverse proxy / sub-path. POSTs carry the
// CSRF token via the X-CSRFToken header, sourced from base.html's
// <meta name="csrf-token">. Search is a GET (read-only), so it needs no token.

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

// Inline note saving — same pattern as before (change event, JSON echo back).
document.addEventListener("change", function (event) {
  const target = event.target;
  if (!target.classList.contains("stock-note")) return;

  const url = target.dataset.noteUrl;
  const body = new URLSearchParams({ note: target.value });
  fetch(url, {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken() },
    body: body,
  })
    .then((r) => {
      if (!r.ok) throw new Error("note save failed");
      return r.json();
    })
    .then((data) => {
      target.value = data.note;
    })
    .catch(() => {
      alert("Could not save note.");
    });
});

// Click delegation for both Remove (pantry) and Add (search results).
document.addEventListener("click", function (event) {
  const target = event.target;

  // Remove from stock — drops the row in place (hybrid update, no reload).
  // Tidies an emptied category section, and reveals the empty-state line if
  // the pantry clears out entirely.
  if (target.classList.contains("stock-remove")) {
    const url = target.dataset.removeUrl;
    target.disabled = true;
    fetch(url, { method: "POST", headers: { "X-CSRFToken": csrfToken() } })
      .then((r) => {
        if (!r.ok) throw new Error("remove failed");
        return r.json();
      })
      .then(() => {
        const li = target.closest(".stock-item");
        const group = target.closest(".stock-group");
        const ul = li ? li.parentElement : null;
        if (li) li.remove();
        if (group && ul && ul.querySelectorAll(".stock-item").length === 0) {
          group.remove(); // no items left under this category — drop the header
        }
        refreshEmptyState();
      })
      .catch(() => {
        target.disabled = false;
        alert("Could not remove item — is the server still running?");
      });
    return;
  }

  // Add to stock — reload so the new item appears in the pantry via the normal
  // server render (this also resets the search box). Reloads whichever surface
  // we're on, so the wizard step returns to itself.
  if (target.classList.contains("stock-add")) {
    const url = target.dataset.addUrl;
    target.disabled = true;
    fetch(url, { method: "POST", headers: { "X-CSRFToken": csrfToken() } })
      .then((r) => {
        if (!r.ok) throw new Error("add failed");
        return r.json();
      })
      .then(() => {
        window.location.reload();
      })
      .catch(() => {
        target.disabled = false;
        alert("Could not add item — is the server still running?");
      });
    return;
  }
});

// --- Search-to-add ------------------------------------------------------------
// Debounced catalogue search: GET the server-rendered results fragment and drop
// it into the results container. Also keep the "add a new ingredient" link's
// ?name= in sync with what's typed, so the manage form arrives pre-filled.
(function () {
  const input = document.getElementById("stock-search-input");
  if (!input) return; // surface without the search box (shouldn't happen)
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
    if (!q) {
      results.innerHTML = "";
      return;
    }
    const url = input.dataset.searchUrl + "?q=" + encodeURIComponent(q);
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error("search failed");
        return r.text();
      })
      .then((html) => {
        results.innerHTML = html;
      })
      .catch(() => {
        results.innerHTML = "<p><em>Search is unavailable right now.</em></p>";
      });
  }

  input.addEventListener("input", function () {
    const q = input.value.trim();
    updateAddNewLink(q);
    clearTimeout(timer);
    timer = setTimeout(function () {
      runSearch(q);
    }, 200);
  });
})();
