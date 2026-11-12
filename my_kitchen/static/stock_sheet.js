// The stock confirmation sheet: window.mkStockSheet.open({...}).
// Markup: templates/stock/_sheet.html. One <dialog>, two modes.
//
// mode "in" (0.36.1) — a pasted list or a receipt. EVERY line read is shown
//   as a row, so the cook can check them all against the receipt, grouped:
//     Add to stock  — out of stock: ticked, with a tick box to leave it out
//     Needs a hand  — nobody could place it
//     Already have  — in stock or a staple: faded, no action
//     Skipped       — not food, or skipped by the cook: folded away
//   One rule for every row: tap the line to change what it is. The panel
//   searches the catalogue (or adds a new ingredient, or skips the line), and
//   the line re-files itself by what it is now. You never pick a group.
//
// mode "out" — "Used anything up?" on a recipe: pills, none picked.
//
// Confirm posts {ids, in_stock} to stock.bulk and hands the changed ids to
// onDone, so the caller can offer Undo. URLs come from data-* (url_for).
(function () {
  var dlg = document.getElementById("stock-sheet");
  if (!dlg) return;

  var titleEl = dlg.querySelector("[data-title]");
  var noteEl = dlg.querySelector("[data-note]");
  var picks = dlg.querySelector("[data-picks]");
  var linesEl = dlg.querySelector("[data-lines]");
  var leftEl = dlg.querySelector("[data-left]");
  var goBtn = dlg.querySelector("[data-go]");
  var tpl = document.getElementById("needs-panel-tpl");
  var catalogue = [];
  try { catalogue = JSON.parse(document.getElementById("stock-sheet-catalogue").textContent); } catch (e) {}

  var state = null;   // { mode, onDone, lines, open (index), moved (index) }

  function csrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") : "";
  }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

  // ---- mode "out": pills ----------------------------------------------------
  function addPill(item) {
    var label = el("label", "option sec-pick--" + (item.section || "other"));
    var input = el("input");
    input.type = "checkbox";
    input.value = item.id;
    label.appendChild(input);
    label.appendChild(el("span", null, item.name));
    picks.appendChild(label);
  }
  picks.addEventListener("change", refresh);

  // ---- mode "in": lines --------------------------------------------------------
  var GROUPS = [
    ["add", "Add to stock"],
    ["unplaced", "Needs a hand"],
    ["have", "Already have"],
    ["skipped", "Skipped"],
  ];

  // Re-file a line by what it is now.
  function setItem(line, item) {
    line.id = item.id;
    line.name = item.name;
    line.section = item.section;
    line.staple = !!item.staple;
    line.status = (item.staple || item.in_stock) ? "have" : "add";
    line.checked = true;
  }

  function renderLines() {
    linesEl.innerHTML = "";
    var counts = {};
    GROUPS.forEach(function (g) {
      var idx = [];
      state.lines.forEach(function (l, i) { if (l.status === g[0]) idx.push(i); });
      counts[g[0]] = idx.length;
      if (!idx.length) return;
      var box = g[0] === "skipped" ? el("details", "sheet-group sheet-group--skipped") : el("section", "sheet-group");
      var head = el(g[0] === "skipped" ? "summary" : "h3", "sheet-group-head");
      head.appendChild(el("span", null, g[1]));
      head.appendChild(el("span", "sheet-group-n", String(idx.length)));
      box.appendChild(head);
      if (g[0] === "skipped" && idx.indexOf(state.open) !== -1) box.open = true;
      idx.forEach(function (i) { box.appendChild(renderRow(state.lines[i], i)); });
      linesEl.appendChild(box);
    });
    refresh(counts);
  }

  function renderRow(line, i) {
    var row = el("div", "sheet-row sheet-row--" + line.status);
    if (line.status === "add" || line.status === "have") row.classList.add("sec-pick--" + (line.section || "other"));
    if (state.open === i) row.classList.add("is-open");
    if (state.moved === i) row.classList.add("is-moved");
    var main = el("button", "sheet-row-main");
    main.type = "button";
    main.setAttribute("aria-expanded", state.open === i ? "true" : "false");
    var text = el("span", "sheet-row-text");
    if (line.status === "unplaced") {
      text.appendChild(el("span", "needs-text", line.text));
    } else {
      var name = line.status === "skipped" ? (line.name || "Not food") : line.name;
      var nm = el("span", "sheet-row-name", name);
      if (line.staple) nm.appendChild(el("span", "sheet-row-tag", " · staple"));
      text.appendChild(nm);
      // The line as written, unless it just repeats the name ("butter").
      if (!name || line.text.toLowerCase() !== name.toLowerCase()) {
        text.appendChild(el("span", "needs-text sheet-row-raw", line.text));
      }
    }
    main.appendChild(text);
    if (line.status === "unplaced") {
      var hasGuess = line.guess && line.guess.toLowerCase() !== line.text.toLowerCase();
      main.appendChild(el("span", "needs-ask", hasGuess ? cap(line.guess) + "?" : "What was this?"));
    } else if (tpl && state.open !== i) {
      main.appendChild(el("span", "sheet-row-change", "Change"));
    }
    if (tpl) main.addEventListener("click", function () { toggle(i); });
    else main.disabled = true;
    row.appendChild(main);
    if (line.status === "add") {
      var tick = el("input", "sheet-row-tick");
      tick.type = "checkbox";
      tick.checked = line.checked !== false;
      tick.setAttribute("aria-label", "Add " + line.name + " to stock");
      tick.addEventListener("change", function () { line.checked = tick.checked; refresh(); });
      row.appendChild(tick);
    }
    if (state.open === i) row.appendChild(panel(line, i));
    return row;
  }

  function toggle(i) {
    state.open = state.open === i ? null : i;
    state.moved = null;
    renderLines();
    var q = linesEl.querySelector("[data-needs-q]");
    if (q) { q.focus(); q.select(); }
  }

  function done(i) {
    state.open = null;
    state.moved = i;
    renderLines();
  }

  // ---- the "change this line" panel -----------------------------------------------
  function search(q) {
    var words = q.toLowerCase().split(/\s+/).filter(function (w) { return w.length > 1; });
    if (!words.length) return [];
    var all = catalogue.filter(function (c) {
      var n = c.name.toLowerCase();
      return words.every(function (w) { return n.indexOf(w) !== -1; });
    });
    if (!all.length) {   // no item holds every word: fall back to any word
      all = catalogue.filter(function (c) {
        var n = c.name.toLowerCase();
        return words.some(function (w) { return w.length > 2 && n.indexOf(w) !== -1; });
      });
    }
    return all.slice(0, 8);
  }

  function panel(line, i) {
    var p = tpl.content.firstElementChild.cloneNode(true);
    var q = p.querySelector("[data-needs-q]");
    var box = p.querySelector("[data-needs-results]");
    var newBox = p.querySelector("[data-needs-new]");
    var cat = p.querySelector("[data-needs-cat]");
    var err = p.querySelector("[data-needs-error]");
    q.value = line.status === "unplaced" ? (line.guess || line.text) : line.text;
    if (line.category_id) cat.value = line.category_id;

    function results() {
      box.innerHTML = "";
      var hits = search(q.value.trim());
      if (!hits.length) {
        box.appendChild(el("p", "needs-none", q.value.trim() ? "Nothing in your catalogue matches." : "Type what it was."));
        if (q.value.trim() && line.category_id) newBox.hidden = false;
        return;
      }
      hits.forEach(function (c) {
        var b = el("button", "needs-pick" + (c.id === line.id ? " is-current" : ""), c.name);
        b.type = "button";
        b.addEventListener("click", function () { setItem(line, c); done(i); });
        box.appendChild(b);
      });
    }
    q.addEventListener("input", results);
    results();

    p.querySelector("[data-needs-skip]").addEventListener("click", function () {
      line.status = "skipped";
      line.id = null;
      line.name = null;
      line.staple = false;
      done(i);
    });
    p.querySelector("[data-needs-addnew]").addEventListener("click", function () {
      newBox.hidden = !newBox.hidden;
    });
    p.querySelector("[data-needs-create]").addEventListener("click", function () {
      var name = cap(q.value.trim());   // catalogue names start with a capital
      if (!name) { q.focus(); return; }
      if (!cat.value) { err.textContent = "Pick a category first."; err.hidden = false; cat.focus(); return; }
      err.hidden = true;
      fetch(dlg.dataset.createUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
        // stock=0: created now, stocked only when the sheet is confirmed.
        body: new URLSearchParams({ name: name, category_id: cat.value, stock: "0" }),
      })
        .then(function (r) { return r.json().catch(function () { return {}; }); })
        .then(function (d) {
          if (!d.id) { err.textContent = d.message || "Could not add it."; err.hidden = false; return; }
          // New, or already in the catalogue: either way, that's what it is.
          var item = { id: d.id, name: d.name, section: d.section, in_stock: d.in_stock, staple: d.is_staple };
          if (d.ok) catalogue.push(item);
          setItem(line, item);
          done(i);
        })
        .catch(function () { err.textContent = "Could not add it — is the server running?"; err.hidden = false; });
    });
    return p;
  }

  // ---- footer ----------------------------------------------------------------------
  function selectedIds() {
    if (state.mode === "out") {
      return Array.prototype.map.call(picks.querySelectorAll("input:checked"), function (i) { return +i.value; });
    }
    var ids = [];
    state.lines.forEach(function (l) {
      if (l.status === "add" && l.checked !== false && ids.indexOf(l.id) === -1) ids.push(l.id);
    });
    return ids;
  }

  function refresh() {
    if (!state) return;
    var n = selectedIds().length;
    goBtn.disabled = n === 0;
    goBtn.textContent = state.mode === "out"
      ? (n ? "Mark " + n + " as used up" : "Mark as used up")
      : (n ? "Mark " + n + " as in stock" : "Mark as in stock");
    var left = state.mode === "in"
      ? state.lines.filter(function (l) { return l.status === "unplaced"; }).length : 0;
    leftEl.hidden = left === 0;
    leftEl.textContent = plural(left, "line", "lines") + " still to place";
  }

  function close() {
    if (dlg.open) dlg.close();
    state = null;
  }
  dlg.querySelector("[data-cancel]").addEventListener("click", close);
  dlg.addEventListener("cancel", function () { state = null; });

  goBtn.addEventListener("click", function () {
    if (!state) return;
    var ids = selectedIds();
    var mode = state.mode, onDone = state.onDone;
    goBtn.disabled = true;
    fetch(dlg.dataset.bulkUrl, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken(), "Content-Type": "application/json" },
      body: JSON.stringify({ ids: ids, in_stock: mode === "in" }),
    })
      .then(function (r) { if (!r.ok) throw new Error("bulk failed"); return r.json(); })
      .then(function (d) { close(); if (onDone) onDone(d.changed || []); })
      .catch(function () { goBtn.disabled = false; alert("Could not update stock — is the server running?"); });
  });

  window.mkStockSheet = {
    // in:  { mode: "in", title, lines: [{text, status, id, name, section, staple, guess, category_id}],
    //        source: "receipt" | "list", onDone(changedIds) }
    // out: { mode: "out", title, note, items: [{id, name, section}], onDone(changedIds) }
    open: function (opts) {
      state = { mode: opts.mode || "in", onDone: opts.onDone, open: null, moved: null };
      titleEl.textContent = opts.title || "";
      picks.innerHTML = "";
      linesEl.innerHTML = "";
      if (state.mode === "out") {
        noteEl.textContent = opts.note || "";
        (opts.items || []).forEach(addPill);
        refresh();
      } else {
        state.lines = (opts.lines || []).map(function (l) { return Object.assign({ checked: true }, l); });
        var n = state.lines.length;
        noteEl.textContent = plural(n, "line", "lines") + (opts.source === "receipt" ? " read" : "") +
          (tpl ? " · tap a line to change it" : "");
        renderLines();
      }
      noteEl.hidden = !noteEl.textContent;
      if (typeof dlg.showModal === "function") dlg.showModal(); else dlg.setAttribute("open", "");
    },
  };

  // Bulk Undo for callers: flip exactly the changed ids back.
  window.mkStockUndo = function (ids, wasInStock) {
    return fetch(dlg.dataset.bulkUrl, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken(), "Content-Type": "application/json" },
      body: JSON.stringify({ ids: ids, in_stock: !wasInStock }),
    }).then(function (r) { if (!r.ok) throw new Error("undo failed"); return r.json(); });
  };
})();
