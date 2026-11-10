// Refine on the recipe page (Phase 26, reshaped in 0.28).
// - The panel opens from the "+ New version" node at the end of the trail.
// - Chips append their text to the instruction.
// - Submitting never goes straight to the AI: a confirmation dialog quotes the
//   instruction and says what will happen, so a question can't turn into a
//   full regeneration by accident. Only its "Create" button submits.
// - The submit button disables once confirmed (the server's one-running-job-
//   per-user guard is the real backstop).
// - window.mkRefine lets the servings scaler pre-fill "Make this for N people"
//   and open the panel; the same confirmation still applies. @kitchen replies
//   that propose a major change use it too (Phase 29).
(function () {
  var panel = document.getElementById("refine");
  var box = document.getElementById("refine-instruction");
  var form = document.getElementById("refine-form");
  if (!panel || !box || !form) return;
  var toggle = document.getElementById("refine-toggle");
  var dialog = document.getElementById("refine-confirm");
  var quote = document.getElementById("refine-confirm-quote");
  var submitBtn = document.getElementById("refine-btn");
  var confirmed = false;

  // The trail scrolls sideways on a phone; start at its newest end.
  var trail = document.querySelector(".version-trail");
  if (trail) trail.scrollLeft = trail.scrollWidth;

  function setOpen(on, focus) {
    panel.hidden = !on;
    if (toggle) toggle.setAttribute("aria-expanded", on ? "true" : "false");
    if (on && focus) {
      panel.scrollIntoView({ behavior: "smooth", block: "center" });
      box.focus({ preventScroll: true });
    }
  }
  if (toggle) toggle.addEventListener("click", function () { setOpen(panel.hidden, true); });
  var cancel = document.getElementById("refine-cancel");
  if (cancel) cancel.addEventListener("click", function () { setOpen(false); });
  var toNotes = document.getElementById("refine-to-notes");
  if (toNotes) toNotes.addEventListener("click", function () { setOpen(false); });

  function add(text) {
    var cur = box.value.replace(/[\s,.]+$/, "");
    if (cur.toLowerCase().indexOf(text.toLowerCase()) !== -1) return;
    var next = cur ? cur + ", " + text.charAt(0).toLowerCase() + text.slice(1) : text;
    if (next.length <= box.maxLength) box.value = next;
  }
  panel.querySelectorAll(".request-chip").forEach(function (chip) {
    chip.addEventListener("click", function () { add(chip.dataset.chip); box.focus(); });
  });

  function go() {
    confirmed = true;
    submitBtn.disabled = true;
    submitBtn.textContent = "Starting…";
    form.submit();  // bypasses the submit handler below; validation already passed
  }

  // "submit" only fires once the browser's own validation (required) passes.
  form.addEventListener("submit", function (e) {
    if (confirmed) return;
    e.preventDefault();
    var text = box.value.trim();
    if (dialog && typeof dialog.showModal === "function") {
      quote.textContent = "“" + text + "”";
      dialog.showModal();
      document.getElementById("refine-confirm-go").focus();
    } else if (window.confirm("Create a new version of this recipe with: “" + text + "”? The current version is kept.")) {
      go();
    }
  });

  if (dialog) {
    document.getElementById("refine-confirm-go").addEventListener("click", function () {
      dialog.close();
      go();
    });
    document.getElementById("refine-confirm-cancel").addEventListener("click", function () {
      dialog.close();
      box.focus();
    });
  }

  window.mkRefine = function (text) {
    box.value = text;
    setOpen(true, true);
  };

  // Phase 29: "Make this version N" under a @kitchen reply that proposed a
  // major change. Same path as the servings rewrite: pre-fill, open, confirm.
  document.querySelectorAll("[data-refine-change]").forEach(function (b) {
    b.addEventListener("click", function () { window.mkRefine(b.dataset.refineChange); });
  });
})();
