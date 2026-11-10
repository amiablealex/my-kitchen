// The app's own "are you sure?" for destructive forms (0.29.4), replacing the
// browser's confirm(). Mark a form with:
//   data-confirm="Body text"  data-confirm-title="Delete Lamb?"  data-confirm-ok="Delete"
// One <dialog class="confirm"> is built on first use and reused. Without
// <dialog> support it falls back to window.confirm, so nothing is ever
// deleted without asking.
(function () {
  var dlg, titleEl, bodyEl, okBtn, pending = null;

  function build() {
    dlg = document.createElement("dialog");
    dlg.className = "confirm confirm--warn";
    dlg.setAttribute("aria-labelledby", "mk-confirm-title");
    dlg.innerHTML =
      '<div class="confirm-head"><span class="confirm-bead" aria-hidden="true"></span>' +
      '<h2 id="mk-confirm-title"></h2></div><p class="confirm-body"></p>' +
      '<div class="btn-row"><button type="button" class="btn btn--danger" data-ok></button>' +
      '<button type="button" class="btn btn--ghost" data-cancel>Cancel</button></div>';
    document.body.appendChild(dlg);
    titleEl = dlg.querySelector("h2");
    bodyEl = dlg.querySelector(".confirm-body");
    okBtn = dlg.querySelector("[data-ok]");
    okBtn.addEventListener("click", function () {
      var f = pending; pending = null; dlg.close();
      if (f) { f.dataset.confirmed = "1"; f.submit(); }
    });
    dlg.querySelector("[data-cancel]").addEventListener("click", function () { pending = null; dlg.close(); });
  }

  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (!f.matches || !f.matches("form[data-confirm]") || f.dataset.confirmed) return;
    e.preventDefault();
    var title = f.dataset.confirmTitle || "Are you sure?";
    var body = f.dataset.confirm || "";
    if (typeof HTMLDialogElement !== "function") {
      if (window.confirm(title + (body ? "\n\n" + body : ""))) { f.dataset.confirmed = "1"; f.submit(); }
      return;
    }
    if (!dlg) build();
    titleEl.textContent = title;
    bodyEl.textContent = body;
    bodyEl.hidden = !body;
    okBtn.textContent = f.dataset.confirmOk || "Delete";
    pending = f;
    var menu = f.closest("details.overflow");
    if (menu) menu.open = false;
    dlg.showModal();
    okBtn.focus();
  }, true);
})();
