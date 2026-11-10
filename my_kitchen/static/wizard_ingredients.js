// Lets Cook, step 1 (0.29.2): find an ingredient, and stock one in place.
//
// The box filters what's on the page (the four lanes and the staples drawer)
// as you type. A lane with no matches hides; the drawer opens while a staple
// matches and goes back to how it was when the box is cleared. Filtering only
// hides, so a picked chip that's hidden is still submitted.
//
// It also asks the server for catalogue matches that are NOT in stock and lists
// them under "Not in stock". Tapping one puts it in stock (household-wide, the
// same call the stock page makes) and drops it into its lane already picked,
// with an Undo toast that reverses both. Escape clears the box; Enter never
// submits (the first submit button in the form is "Edit stock").
(function () {
  var box = document.getElementById("ing-filter");
  if (!box) return;
  var form = document.getElementById("ing-form");
  var nomatch = document.getElementById("ing-nomatch");
  var drawer = document.querySelector(".wizard-staples");
  var catalogue = document.getElementById("ing-catalogue");
  var emptyNote = document.getElementById("ing-empty");
  var drawerWasOpen = drawer ? drawer.open : false;
  var seq = 0, timer = null, lastQ = "";

  function csrf() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.content : "";
  }
  function norm(t) { return (t || "").toLowerCase().trim(); }
  function labelOf(o) { var s = o.querySelector("span"); return norm(s ? s.textContent : o.textContent); }
  function options() { return document.querySelectorAll(".wizard-lane .option, .staple-group .option"); }
  function lanes() { return document.querySelectorAll(".wizard-lane"); }

  function apply() {
    var q = norm(box.value);
    var shown = 0;
    Array.prototype.forEach.call(options(), function (o) {
      var hit = !q || labelOf(o).indexOf(q) !== -1;
      o.hidden = !hit;
      if (hit && q) shown++;
    });
    Array.prototype.forEach.call(lanes(), function (g) {
      var has = !!g.querySelector(".option");
      // An empty lane shows its "nothing in stock" line only when unfiltered and
      // only if the pantry isn't empty altogether (then the empty note speaks).
      g.hidden = q ? !g.querySelector(".option:not([hidden])") : (!has && !!emptyNote);
    });
    Array.prototype.forEach.call(document.querySelectorAll(".staple-group"), function (g) {
      g.hidden = !!q && !g.querySelector(".option:not([hidden])");
    });
    if (drawer) {
      var staplesHit = !!q && !!drawer.querySelector(".option:not([hidden])");
      drawer.hidden = !!q && !staplesHit;
      drawer.open = q ? staplesHit : drawerWasOpen;
    }
    if (emptyNote) emptyNote.hidden = !!q || !!document.querySelector(".wizard-lane .option");
    box.dataset.shown = shown;
    updateNomatch();
  }

  function updateNomatch() {
    var q = norm(box.value);
    var catHits = catalogue && !catalogue.hidden && catalogue.querySelector(".stock-add");
    var pending = q && q !== lastQ;
    if (nomatch) nomatch.hidden = !q || pending || +box.dataset.shown > 0 || !!catHits;
  }

  function fetchCatalogue() {
    var q = norm(box.value);
    if (!catalogue) return;
    if (!q) { catalogue.innerHTML = ""; catalogue.hidden = true; lastQ = ""; updateNomatch(); return; }
    var mine = ++seq;
    fetch(catalogue.dataset.url + "?q=" + encodeURIComponent(q), { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.text() : ""; })
      .then(function (html) {
        if (mine !== seq) return;                   // a newer query has gone out
        lastQ = q;
        catalogue.innerHTML = html;
        catalogue.hidden = !html.trim();
        updateNomatch();
      })
      .catch(function () { lastQ = q; updateNomatch(); });
  }

  function onInput() {
    apply();
    clearTimeout(timer);
    timer = setTimeout(fetchCatalogue, 180);
  }

  // Build a lane chip identical to the server-rendered ones, already picked.
  function makeChip(id, name) {
    var label = document.createElement("label");
    label.className = "option";
    var input = document.createElement("input");
    input.type = "checkbox"; input.name = "ingredient_ids"; input.value = id; input.checked = true;
    var span = document.createElement("span"); span.textContent = name;
    var meta = document.createElement("span"); meta.className = "opt-meta"; meta.textContent = "just added";
    label.appendChild(input); label.appendChild(span); label.appendChild(meta);
    return label;
  }

  function placeChip(section, chip) {
    var lane = document.querySelector('.wizard-lane[data-section="' + section + '"]') ||
               document.querySelector('.wizard-lane[data-section="other"]');
    if (!lane) return;
    var list = lane.querySelector(".options");
    if (!list) {
      var empty = lane.querySelector(".lane-empty");
      if (empty) empty.remove();
      list = document.createElement("div");
      list.className = "options options--chips";
      lane.appendChild(list);
    }
    // Keep the lane alphabetical, as the server renders it.
    var name = labelOf(chip), before = null;
    Array.prototype.some.call(list.querySelectorAll(".option"), function (o) {
      if (labelOf(o) > name) { before = o; return true; }
      return false;
    });
    list.insertBefore(chip, before);
    lane.hidden = false;
    var go = form && form.querySelector(".wizard-dock button span");
    if (go) go.textContent = "Continue";
  }

  function post(url) {
    return fetch(url, { method: "POST", credentials: "same-origin", headers: { "X-CSRFToken": csrf() } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }

  if (catalogue) catalogue.addEventListener("click", function (e) {
    var btn = e.target.closest(".stock-add");
    if (!btn || btn.disabled) return;
    btn.disabled = true;
    var d = btn.dataset;
    post(d.addUrl).then(function () {
      var chip = makeChip(d.id, d.name);
      placeChip(d.section, chip);
      var li = btn.closest(".search-result");
      if (li) li.remove();
      if (!catalogue.querySelector(".stock-add")) catalogue.hidden = true;
      apply();
      if (window.showToast) window.showToast({
        message: d.name + " is now in stock",
        actionLabel: "Undo",
        onAction: function () {
          post(d.removeUrl).then(function () {
            var lane = chip.closest(".wizard-lane");
            chip.remove();
            if (lane && !lane.querySelector(".option")) {
              var list = lane.querySelector(".options");
              if (list) list.remove();
              var p = document.createElement("p");
              p.className = "muted lane-empty"; p.textContent = "Nothing in stock in this lane.";
              lane.appendChild(p);
            }
            apply(); fetchCatalogue();
          });
        }
      });
    }).catch(function () {
      btn.disabled = false;
      if (window.showToast) window.showToast({ message: "Couldn't add " + d.name + " to stock. Try again." });
    });
  });

  box.addEventListener("input", onInput);
  box.addEventListener("keydown", function (e) {
    if (e.key === "Enter") e.preventDefault();
    if (e.key === "Escape" && box.value) { box.value = ""; onInput(); }
  });
  if (drawer) drawer.addEventListener("toggle", function () { if (!norm(box.value)) drawerWasOpen = drawer.open; });
  apply();
})();
