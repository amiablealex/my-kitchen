// Notes + @kitchen questions on the recipe page (Phase 27).
// - "Ask @kitchen" puts the mention at the start of the box (only a leading
//   mention makes a question — the server decides, this is a shortcut).
// - The submit button reads "Ask @kitchen" while the box starts with it.
// - viewing_servings carries the scaler's count (sessionStorage, servings.js)
//   so the answer can talk about the servings the cook is looking at.
// - While an answer is still pending, the page checks back every few seconds,
//   but never while someone is mid-way through typing a note.
(function () {
  var box = document.getElementById("note-body");
  var submit = document.getElementById("note-submit");
  var chip = document.getElementById("ask-chip");
  var servings = document.getElementById("servings");
  if (!box || !submit) return;
  var mention = chip ? chip.dataset.mention : "@kitchen";
  // By class, not the first <span>: the pinwheel dot is a span too, and it
  // comes first (0.27.1 wrote the label into the dot).
  var label = submit.querySelector(".note-submit-label");

  function isQuestion() {
    return box.value.trim().toLowerCase().indexOf(mention.toLowerCase()) === 0;
  }
  // Two modes, one primary action each: a note ("Add note" + the chip to
  // switch), or a question ("Ask @kitchen" with the pinwheel, chip hidden).
  // Deleting the mention from the box switches straight back.
  var form = box.form;
  function sync() {
    var q = isQuestion();
    label.textContent = q ? submit.dataset.askLabel : submit.dataset.noteLabel;
    form.classList.toggle("is-asking", q);
    if (chip) chip.hidden = q;
  }
  box.addEventListener("input", sync);

  if (chip) {
    chip.addEventListener("click", function () {
      if (!isQuestion()) box.value = mention + " " + box.value.replace(/^\s+/, "");
      sync();
      box.focus();
      box.setSelectionRange(box.value.length, box.value.length);
    });
  }

  document.querySelectorAll("form").forEach(function (f) {
    var hidden = f.querySelector(".js-viewing-servings");
    if (!hidden) return;
    f.addEventListener("submit", function () {
      var n = "";
      try { if (servings) n = sessionStorage.getItem(servings.dataset.key) || ""; } catch (e) {}
      hidden.value = n;
      if (f.contains(box) && isQuestion()) {
        submit.disabled = true;
        label.textContent = "Asking…";
      }
    });
  });

  sync();

  if (document.querySelector("[data-pending]")) {
    var check = function () {
      if (box.value.trim()) { setTimeout(check, 4000); return; }
      window.location.reload();
    };
    setTimeout(check, 4000);
  }
})();
