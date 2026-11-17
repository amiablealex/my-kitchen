// Refine on the recipe page (Phase 26, reshaped in 0.28 and 0.41).
// - The panel opens from the "+" on the version being viewed in the trail.
// - Chips append their text to the instruction.
// - Submitting never goes straight to the AI: a confirmation dialog quotes the
//   instruction and says what will happen. Only its "Create" button submits.
// - 0.41.0: when the request reads like a question or a swap, the dialog shows
//   its @kitchen face instead: "Ask @kitchen" posts it as a question in the
//   notes (no rewrite), "Make vN anyway" carries on. Plain text rules, no
//   model call; a wrong guess costs one tap. Skipped when the text came from
//   @kitchen's own "Make this version N" or the servings rewrite, and when
//   there are no questions left today.
// - The "Stick to what's in stock" box swaps its one-line hint.
// - The submit button disables once confirmed (the server's one-running-job-
//   per-user guard is the real backstop).
// - window.mkRefine lets the servings scaler pre-fill "Make this for N people"
//   and open the panel; the same confirmation still applies.
(function () {
  var panel = document.getElementById("refine");
  var box = document.getElementById("refine-instruction");
  var form = document.getElementById("refine-form");
  if (!panel || !box || !form) return;
  var toggle = document.getElementById("refine-toggle");
  var dialog = document.getElementById("refine-confirm");
  var submitBtn = document.getElementById("refine-btn");
  var askForm = document.getElementById("refine-ask-form");
  var confirmed = false;
  var fromApp = false;   // text set by mkRefine, not typed: never nudge it back

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

  box.addEventListener("input", function () { fromApp = false; });

  function add(text) {
    var cur = box.value.replace(/[\s,.]+$/, "");
    if (cur.toLowerCase().indexOf(text.toLowerCase()) !== -1) return;
    var next = cur ? cur + ", " + text.charAt(0).toLowerCase() + text.slice(1) : text;
    if (next.length <= box.maxLength) box.value = next;
  }
  panel.querySelectorAll(".request-chip").forEach(function (chip) {
    chip.addEventListener("click", function () { add(chip.dataset.chip); box.focus(); });
  });

  // "Stick to what's in stock": one hint line that says what each state does.
  var stock = document.getElementById("refine-use-stock");
  var hint = panel.querySelector(".refine-stock-hint");
  if (stock && hint) {
    stock.addEventListener("change", function () {
      hint.textContent = stock.checked ? hint.dataset.on : hint.dataset.off;
    });
  }

  // Does this read like something to ask rather than a change to make?
  var QUESTION_START = /^(how|what|why|when|where|which|who|can|could|should|would|will|is|are|do|does|did|am|any|whats|what's|hows|how's)\b/;
  var SWAP = /\b(instead of|in place of|substitut\w*|swap\w*|replace\w*|don'?t have|do not have|run out|ran out|out of)\b/;
  function looksLikeQuestion(text) {
    var t = text.trim().toLowerCase();
    return /\?\s*$/.test(t) || QUESTION_START.test(t) || SWAP.test(t);
  }

  function go() {
    confirmed = true;
    submitBtn.disabled = true;
    submitBtn.textContent = "Starting…";
    form.submit();  // bypasses the submit handler below; validation already passed
  }

  function ask(text) {
    askForm.querySelector("[name=body]").value = askForm.dataset.mention + " " + text;
    // requestSubmit fires "submit", so notes.js fills in the servings being viewed.
    if (askForm.requestSubmit) askForm.requestSubmit(); else askForm.submit();
  }

  function face(asking) {
    dialog.querySelector(".refine-confirm-normal").hidden = asking;
    dialog.querySelector(".refine-confirm-ask").hidden = !asking;
  }

  // "submit" only fires once the browser's own validation (required) passes.
  form.addEventListener("submit", function (e) {
    if (confirmed) return;
    e.preventDefault();
    var text = box.value.trim();
    var asking = !fromApp && askForm && Number(askForm.dataset.questionsLeft || 0) > 0
                 && looksLikeQuestion(text);
    if (dialog && typeof dialog.showModal === "function") {
      dialog.querySelectorAll(".refine-confirm-quote").forEach(function (q) {
        q.textContent = "“" + text + "”";
      });
      face(asking);
      dialog.showModal();
      document.getElementById(asking ? "refine-confirm-ask" : "refine-confirm-go").focus();
    } else if (window.confirm("Create a new version of this recipe with: “" + text + "”? The current version is kept.")) {
      go();
    }
  });

  if (dialog) {
    document.getElementById("refine-confirm-go").addEventListener("click", function () {
      dialog.close();
      go();
    });
    document.getElementById("refine-confirm-anyway").addEventListener("click", function () {
      dialog.close();
      go();
    });
    document.getElementById("refine-confirm-ask").addEventListener("click", function () {
      dialog.close();
      ask(box.value.trim());
    });
    dialog.querySelectorAll("[data-refine-cancel]").forEach(function (b) {
      b.addEventListener("click", function () {
        dialog.close();
        box.focus();
      });
    });
  }

  window.mkRefine = function (text) {
    box.value = text;
    fromApp = true;
    setOpen(true, true);
  };

  // Phase 29: "Make this version N" under a @kitchen reply that proposed a
  // major change. Same path as the servings rewrite: pre-fill, open, confirm.
  document.querySelectorAll("[data-refine-change]").forEach(function (b) {
    b.addEventListener("click", function () { window.mkRefine(b.dataset.refineChange); });
  });
})();
