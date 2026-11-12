// The stock confirmation sheet (Phase 32): window.mkStockSheet.open({...}).
// Markup: templates/stock/_sheet.html. One <dialog>, two uses:
//   mode "in"  — "Mark these as in stock?" Pills start picked. Lines the app
//                couldn't place sit under "Needs a hand" until the cook says
//                what they were (search the catalogue, add as new, or skip).
//   mode "out" — "Used anything up?" Pills start unpicked; nothing to place.
// Confirm posts {ids, in_stock} to stock.bulk and hands the changed ids to
// onDone, so the caller can offer Undo. URLs come from data-* (url_for).
(function () {
  var dlg = document.getElementById("stock-sheet");
  if (!dlg) return;

  var titleEl = dlg.querySelector("[data-title]");
  var noteEl = dlg.querySelector("[data-note]");
  var picks = dlg.querySelector("[data-picks]");
  var needs = dlg.querySelector("[data-needs]");
  var needsList = dlg.querySelector("[data-needs-list]");
  var leftEl = dlg.querySelector("[data-left]");
  var goBtn = dlg.querySelector("[data-go]");
  var tpl = document.getElementById("needs-panel-tpl");
  var catalogue = [];
  try { catalogue = JSON.parse(document.getElementById("stock-sheet-catalogue").textContent); } catch (e) {}

  var state = null;   // { mode, onDone }

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

  // ---- pills ---------------------------------------------------------------
  function findPill(id) { return picks.querySelector('input[value="' + id + '"]'); }

  function addPill(item, checked) {
    var existing = findPill(item.id);
    if (existing) { existing.checked = true; refresh(); return; }
    var label = el("label", "option sec-pick--" + (item.section || "other"));
    var input = el("input");
    input.type = "checkbox";
    input.value = item.id;
    input.checked = !!checked;
    label.appendChild(input);
    label.appendChild(el("span", null, item.name));
    if (item.raw) {
      label.dataset.raw = item.raw;
      label.appendChild(el("small", "opt-meta", "“" + item.raw + "”"));
    }
    picks.appendChild(label);
  }

  // Unticking a guess (a pill named differently from its line) means "that's
  // not it", so the line goes back to Needs a hand instead of being lost.
  picks.addEventListener("change", function (e) {
    var label = e.target.closest("label");
    if (state && state.mode === "in" && tpl && label && label.dataset.raw && !e.target.checked) {
      addNeedsRow({ text: label.dataset.raw, guess: label.dataset.raw }, true);
      label.remove();
    }
    refresh();
  });

  // ---- needs a hand ----------------------------------------------------------
  function addNeedsRow(line, atTop) {
    var li = el("li", "needs-row");
    li.dataset.text = line.text;
    li.dataset.guess = line.guess || line.text;
    if (line.category_id) li.dataset.cat = line.category_id;
    var btn = el("button", "needs-line");
    btn.type = "button";
    btn.appendChild(el("span", "needs-text", line.text));
    // An AI guess that differs from the line reads as a question ("dragon fruit?").
    var hasGuess = line.guess && line.guess.toLowerCase() !== line.text.toLowerCase();
    btn.appendChild(el("span", "needs-ask", hasGuess ? cap(line.guess) + "?" : "What was this?"));
    li.appendChild(btn);
    if (atTop) needsList.insertBefore(li, needsList.firstChild); else needsList.appendChild(li);
    refresh();
  }

  function closePanels() {
    needsList.querySelectorAll(".needs-panel").forEach(function (p) {
      p.closest(".needs-row").classList.remove("is-open");
      p.remove();
    });
  }

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

  function renderResults(panel, row) {
    var q = panel.querySelector("[data-needs-q]").value.trim();
    var box = panel.querySelector("[data-needs-results]");
    box.innerHTML = "";
    var hits = search(q);
    if (!hits.length) {
      box.appendChild(el("p", "needs-none", q ? "Nothing in your catalogue matches." : "Type what it was."));
      // With a suggested category, "add it as new" is almost certainly next.
      if (q && row.dataset.cat) panel.querySelector("[data-needs-new]").hidden = false;
      return;
    }
    hits.forEach(function (c) {
      var b = el("button", "needs-pick sec-pick--" + c.section, c.name);
      b.type = "button";
      b.addEventListener("click", function () { place(row, c); });
      box.appendChild(b);
    });
  }

  function place(row, item) {
    addPill({ id: item.id, name: item.name, section: item.section, raw: row.dataset.text }, true);
    row.remove();
    refresh();
  }

  function openPanel(row) {
    var wasOpen = row.classList.contains("is-open");
    closePanels();
    if (wasOpen) return;
    var panel = tpl.content.firstElementChild.cloneNode(true);
    var q = panel.querySelector("[data-needs-q]");
    var newBox = panel.querySelector("[data-needs-new]");
    var err = panel.querySelector("[data-needs-error]");
    q.value = row.dataset.guess;
    if (row.dataset.cat) panel.querySelector("[data-needs-cat]").value = row.dataset.cat;
    row.appendChild(panel);
    row.classList.add("is-open");
    renderResults(panel, row);
    q.addEventListener("input", function () { renderResults(panel, row); });
    q.focus();
    q.select();

    panel.querySelector("[data-needs-skip]").addEventListener("click", function () {
      row.remove();
      refresh();
    });
    panel.querySelector("[data-needs-addnew]").addEventListener("click", function () {
      newBox.hidden = !newBox.hidden;
    });
    panel.querySelector("[data-needs-create]").addEventListener("click", function () {
      var name = cap(q.value.trim());   // catalogue names start with a capital
      var cat = panel.querySelector("[data-needs-cat]");
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
          // Already in the catalogue (and not a staple): just use that one.
          if (!d.ok && d.id && !d.is_staple) { place(row, { id: d.id, name: d.name, section: d.section }); return; }
          if (!d.ok) { err.textContent = d.message || "Could not add it."; err.hidden = false; return; }
          var item = { id: d.id, name: d.name, section: d.section };
          catalogue.push(item);
          place(row, item);
        })
        .catch(function () { err.textContent = "Could not add it — is the server running?"; err.hidden = false; });
    });
  }

  needsList.addEventListener("click", function (e) {
    var btn = e.target.closest(".needs-line");
    if (btn) openPanel(btn.closest(".needs-row"));
  });

  // ---- footer ----------------------------------------------------------------
  function refresh() {
    if (!state) return;
    var n = picks.querySelectorAll("input:checked").length;
    goBtn.disabled = n === 0;
    goBtn.textContent = state.mode === "out"
      ? (n ? "Mark " + n + " as used up" : "Mark as used up")
      : (n ? "Mark " + n + " as in stock" : "Mark as in stock");
    var left = needsList.querySelectorAll(".needs-row").length;
    needs.hidden = left === 0;
    leftEl.hidden = left === 0;
    leftEl.textContent = plural(left, "line", "lines") + " still to place";
  }

  function close() {
    closePanels();
    if (dlg.open) dlg.close();
    state = null;
  }
  dlg.querySelector("[data-cancel]").addEventListener("click", close);
  dlg.addEventListener("cancel", function () { state = null; });

  goBtn.addEventListener("click", function () {
    if (!state) return;
    var ids = Array.prototype.map.call(picks.querySelectorAll("input:checked"), function (i) { return +i.value; });
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
    // opts: { mode, title, note, items: [{id, name, section, raw}],
    //         unplaced: [{text, guess, category_id}], onDone(changedIds) }
    open: function (opts) {
      state = { mode: opts.mode || "in", onDone: opts.onDone };
      titleEl.textContent = opts.title || "";
      noteEl.textContent = opts.note || "";
      noteEl.hidden = !opts.note;
      picks.innerHTML = "";
      needsList.innerHTML = "";
      (opts.items || []).forEach(function (it) { addPill(it, state.mode === "in"); });
      if (tpl) (opts.unplaced || []).forEach(function (u) { addNeedsRow(u); });
      refresh();
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
