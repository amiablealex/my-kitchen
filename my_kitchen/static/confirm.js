// The app's own "are you sure?" for destructive actions (0.29.4), replacing the
// browser's confirm(). Two ways in:
//   1. Mark a form:  data-confirm="Body text"  data-confirm-title="Delete Lamb?"
//                    data-confirm-ok="Delete"
//   2. From script:  window.mkConfirm({ title, body, ok }) → Promise<boolean>
// One <dialog class="confirm"> is built on first use and reused. Without
// <dialog> support it falls back to window.confirm, so nothing destructive
// ever happens without asking.
(function () {
  var dlg, titleEl, bodyEl, okBtn, resolver = null;

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
    okBtn.addEventListener("click", function () { finish(true); });
    dlg.querySelector("[data-cancel]").addEventListener("click", function () { finish(false); });
    dlg.addEventListener("cancel", function () { finish(false); });   // Esc / back
  }

  function finish(answer) {
    var r = resolver; resolver = null;
    if (dlg.open) dlg.close();
    if (r) r(answer);
  }

  window.mkConfirm = function (opts) {
    opts = opts || {};
    var title = opts.title || "Are you sure?";
    var body = opts.body || "";
    if (typeof HTMLDialogElement !== "function") {
      return Promise.resolve(window.confirm(title + (body ? "\n\n" + body : "")));
    }
    if (!dlg) build();
    if (resolver) finish(false);
    titleEl.textContent = title;
    bodyEl.textContent = body;
    bodyEl.hidden = !body;
    okBtn.textContent = opts.ok || "Delete";
    dlg.showModal();
    okBtn.focus();
    return new Promise(function (res) { resolver = res; });
  };

  document.addEventListener("submit", function (e) {
    var f = e.target;
    if (!f.matches || !f.matches("form[data-confirm]") || f.dataset.confirmed) return;
    e.preventDefault();
    var menu = f.closest("details.overflow");
    if (menu) menu.open = false;
    window.mkConfirm({
      title: f.dataset.confirmTitle, body: f.dataset.confirm, ok: f.dataset.confirmOk,
    }).then(function (yes) {
      if (yes) { f.dataset.confirmed = "1"; f.submit(); }
    });
  }, true);
})();
