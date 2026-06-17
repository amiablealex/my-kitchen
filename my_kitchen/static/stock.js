// Stock list interactivity: toggle in/out of stock, save notes inline.
// Endpoint URLs come from data-* attributes (built server-side with url_for),
// so this works unchanged behind a reverse proxy / sub-path.

document.addEventListener("change", function (event) {
  const target = event.target;

  if (target.classList.contains("stock-toggle")) {
    const url = target.dataset.toggleUrl;
    target.disabled = true;
    fetch(url, { method: "POST" })
      .then((r) => {
        if (!r.ok) throw new Error("toggle failed");
        return r.json();
      })
      .then((data) => {
        target.checked = data.in_stock;
      })
      .catch(() => {
        target.checked = !target.checked; // revert the optimistic flip
        alert("Could not update stock — is the server still running?");
      })
      .finally(() => {
        target.disabled = false;
      });
  }

  if (target.classList.contains("stock-note")) {
    const url = target.dataset.noteUrl;
    const body = new URLSearchParams({ note: target.value });
    fetch(url, { method: "POST", body: body })
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
  }
});
