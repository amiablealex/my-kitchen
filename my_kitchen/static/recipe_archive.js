// Per-row archive on the Recipes page (Phase 24), with an Undo toast.
// Since 0.28 only failed-generation rows carry the button (recipes archive
// from their own page's ⋯ menu); the mechanism is unchanged.
// Endpoint URLs come from data-* on #recipe-bank (ingress-safe — JS never builds
// paths); POSTs carry X-CSRFToken from base.html's meta tag. Archiving removes
// the row element; Undo restores exactly the set the server reported and puts
// the same element back where it was.
(function () {
  var bank = document.getElementById("recipe-bank");
  if (!bank) return;
  var archiveUrl = bank.dataset.archiveUrl;
  var restoreUrl = bank.dataset.restoreUrl;

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  }

  function post(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(body),
    }).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  function recount(group) {
    if (!group) return;
    var n = group.querySelectorAll(".recipe-row").length;
    var count = group.querySelector(".recipe-group-count");
    if (count) count.textContent = n;
    group.hidden = n === 0;
  }

  bank.addEventListener("click", function (e) {
    var btn = e.target.closest(".row-archive");
    if (!btn) return;
    var row = btn.closest(".recipe-row");
    var list = row.parentNode;
    var next = row.nextSibling;
    var group = row.closest(".recipe-group");
    var body = {};
    body[btn.dataset.archiveKey] = parseInt(btn.dataset.archiveId, 10);
    btn.disabled = true;

    post(archiveUrl, body).then(function (touched) {
      list.removeChild(row);
      recount(group);
      window.showToast({
        message: "Cleared.",
        actionLabel: "Undo",
        onAction: function () {
          post(restoreUrl, touched).then(function () {
            list.insertBefore(row, next && next.parentNode === list ? next : null);
            btn.disabled = false;
            recount(group);
          }).catch(function () {
            window.showToast({ message: "Couldn't restore — try the Archive page." });
          });
        },
      });
    }).catch(function () {
      btn.disabled = false;
      window.showToast({ message: "Couldn't archive that — please try again." });
    });
  });
})();
