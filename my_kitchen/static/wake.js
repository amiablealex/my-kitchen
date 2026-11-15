// Keep screen on (0.37.0). The chip on the recipe's first method heading asks
// the browser to hold the screen awake while the recipe is open. Shown only
// where the Screen Wake Lock API exists (HTTPS; not every WebView). Phones drop
// the lock when the screen locks or the app is switched, so it's asked for
// again on return; leaving the page releases it. Not remembered between
// recipes.
(function () {
  var chip = document.getElementById("wake-chip");
  if (!chip || !("wakeLock" in navigator) || !window.isSecureContext) return;
  var label = chip.querySelector("span");
  var lock = null, want = false;

  function render(text) {
    chip.setAttribute("aria-pressed", want ? "true" : "false");
    chip.classList.toggle("is-on", want);
    label.textContent = text || (want ? "Screen stays on" : "Keep screen on");
  }

  function acquire() {
    return navigator.wakeLock.request("screen").then(function (l) {
      lock = l;
      l.addEventListener("release", function () { lock = null; });
    });
  }

  chip.addEventListener("click", function () {
    if (want) {
      want = false;
      if (lock) lock.release().catch(function () {});
      lock = null;
      render();
      return;
    }
    acquire().then(function () { want = true; render(); }, function () {
      // Refused (battery saver, say): say so briefly, stay off.
      render("Not available right now");
      setTimeout(function () { render(); }, 2500);
    });
  });

  document.addEventListener("visibilitychange", function () {
    if (want && !lock && document.visibilityState === "visible") acquire().catch(function () {});
  });

  chip.hidden = false;
})();
