// Stock editing: inline notes + remove-from-stock, on both /stock and the
// wizard's /cook/stock step (same partial, same JS). Endpoint URLs come from
// data-* attributes built server-side with url_for(), so this works unchanged
// behind a reverse proxy / sub-path. POSTs carry the CSRF token via the
// X-CSRFToken header, sourced from base.html's <meta name="csrf-token">.

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

// Remove from stock — drops the row in place (hybrid update, no reload).
// Tidies an emptied category section, and reveals the empty-state line if the
// pantry clears out entirely.
document.addEventListener("click", function (event) {
  const target = event.target;
  if (!target.classList.contains("stock-remove")) return;

  const url = target.dataset.removeUrl;
  target.disabled = true;
  fetch(url, {
    method: "POST",
    headers: { "X-CSRFToken": csrfToken() },
  })
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
        group.remove(); // no items left under this category — drop the header too
      }
      refreshEmptyState();
    })
    .catch(() => {
      target.disabled = false;
      alert("Could not remove item — is the server still running?");
    });
});
