// Minimal toast/snackbar with an optional action button. Dependency-free.
// window.showToast({ message, actionLabel, onAction, duration }) → { dismiss }.
// Auto-dismisses after `duration` ms (default 8s). Used by the stock editor's
// remove→undo, and available to any other page that loads this file.
(function () {
  var root;
  function ensureRoot() {
    if (root && document.body.contains(root)) return root;
    root = document.createElement("div");
    root.className = "toast-root";
    document.body.appendChild(root);
    return root;
  }

  window.showToast = function (opts) {
    opts = opts || {};
    var r = ensureRoot();
    var toast = document.createElement("div");
    toast.className = "toast";
    toast.setAttribute("role", "status");

    var msg = document.createElement("span");
    msg.className = "toast-msg";
    msg.textContent = opts.message || "";
    toast.appendChild(msg);

    var timer;
    function dismiss() {
      clearTimeout(timer);
      toast.classList.remove("is-in");
      setTimeout(function () { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 220);
    }

    if (opts.actionLabel && typeof opts.onAction === "function") {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "toast-action";
      btn.textContent = opts.actionLabel;
      btn.addEventListener("click", function () { dismiss(); opts.onAction(); });
      toast.appendChild(btn);
    }

    var close = document.createElement("button");
    close.type = "button";
    close.className = "toast-close";
    close.setAttribute("aria-label", "Dismiss");
    close.innerHTML = "&times;";
    close.addEventListener("click", dismiss);
    toast.appendChild(close);

    r.appendChild(toast);
    requestAnimationFrame(function () { toast.classList.add("is-in"); });
    timer = setTimeout(dismiss, opts.duration || 8000);
    return { dismiss: dismiss };
  };
})();
