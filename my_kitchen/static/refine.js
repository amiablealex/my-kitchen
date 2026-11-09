// Refine panel on the recipe page (Phase 26): chips append their text, the
// submit button disables on submit (the server's one-running-job-per-user
// guard is the real backstop), and window.mkRefine lets the servings scaler
// pre-fill "Make this for N people" and open the panel.
(function () {
  var panel = document.getElementById("refine");
  var box = document.getElementById("refine-instruction");
  if (!panel || !box) return;

  function add(text) {
    var cur = box.value.replace(/[\s,.]+$/, "");
    if (cur.toLowerCase().indexOf(text.toLowerCase()) !== -1) return;
    var next = cur ? cur + ", " + text.charAt(0).toLowerCase() + text.slice(1) : text;
    if (next.length <= box.maxLength) box.value = next;
  }

  panel.querySelectorAll(".request-chip").forEach(function (chip) {
    chip.addEventListener("click", function () { add(chip.dataset.chip); box.focus(); });
  });

  document.getElementById("refine-form").addEventListener("submit", function () {
    var b = document.getElementById("refine-btn");
    b.disabled = true;
    b.textContent = "Starting…";
  });

  window.mkRefine = function (text) {
    box.value = text;
    panel.open = true;
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
    box.focus();
  };
})();
