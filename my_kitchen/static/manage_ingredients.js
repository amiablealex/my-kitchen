// Manage → Ingredients.
//
// Tabs + filter: Standard / Staples tabs with a filter scoped to the active
// tab. The tab persists in sessionStorage, so coming back from an ingredient's
// page (or a bulk action's reload) keeps you where you were.
//
// Select mode (0.30.0): press and hold a chip (or ⋯ → Select ingredients) to
// select several. Taps then toggle chips instead of opening them; each
// category header offers Select all (of what's visible, so it respects the
// filter). The docked bar moves them to a category, makes them staples or
// standard, or retires them. One POST does the lot; the page reloads where it
// was and shows a toast whose Undo puts every item back as it was. Selection is
// per tab: switching tab clears it.
(function () {
  var KEY = "mk-ingredients-tab";
  var TOAST_KEY = "mk-ingredients-toast";
  var SCROLL_KEY = "mk-ingredients-scroll";
  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tab"));
  if (!tabs.length) return;

  var panels = {};
  document.querySelectorAll(".tab-panel").forEach(function (p) { panels[p.dataset.panel] = p; });
  var filterInput = document.getElementById("ing-filter");
  var stapleCheckbox = document.getElementById("add-is-staple");
  var bar = document.getElementById("select-bar");
  var sheet = document.getElementById("move-sheet");
  var selecting = false;

  function activeTab() { var a = document.querySelector(".tab.is-active"); return a ? a.dataset.tab : "standard"; }
  function activePanel() { return panels[activeTab()]; }

  // ---------------------------------------------------------------- filter
  function filterPanel(panel, q) {
    if (!panel) return;
    q = (q || "").trim().toLowerCase();
    var any = false;
    panel.querySelectorAll(".recipe-group:not([data-no-filter])").forEach(function (g) {
      var gv = false;
      g.querySelectorAll("[data-title]").forEach(function (r) {
        var m = !q || (r.dataset.title || "").indexOf(q) !== -1;
        r.hidden = !m; if (m) gv = true;
      });
      g.hidden = !gv; if (gv) any = true;
    });
    var nomatch = panel.querySelector(".recipe-nomatch");
    if (nomatch) nomatch.hidden = any || !q;
    syncGroupButtons();
  }

  function activate(name) {
    if (!panels[name]) name = "standard";
    if (selecting && name !== activeTab()) stopSelecting();
    tabs.forEach(function (t) {
      var on = t.dataset.tab === name;
      t.classList.toggle("is-active", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    Object.keys(panels).forEach(function (k) { panels[k].hidden = k !== name; });
    if (stapleCheckbox) stapleCheckbox.checked = (name === "staples");
    filterPanel(panels[name], filterInput ? filterInput.value : "");
    try { sessionStorage.setItem(KEY, name); } catch (e) {}
  }

  tabs.forEach(function (t) { t.addEventListener("click", function () { activate(t.dataset.tab); }); });
  if (filterInput) filterInput.addEventListener("input", function () {
    filterPanel(activePanel(), filterInput.value);
  });

  // ------------------------------------------------------------ select mode
  function picked() { return Array.prototype.slice.call(document.querySelectorAll("[data-selectable] > li.is-picked")); }

  function updateBar() {
    var n = picked().length;
    bar.querySelector(".select-count strong").textContent = n;
    bar.querySelector("[data-move]").disabled = n === 0;
    bar.querySelectorAll("[data-bulk]").forEach(function (b) { b.disabled = n === 0; });
    // Only the staple action that makes sense for this tab.
    var onStaples = activeTab() === "staples";
    bar.querySelector('[data-bulk="staple"]').hidden = onStaples;
    bar.querySelector('[data-bulk="standard"]').hidden = !onStaples;
    syncGroupButtons();
  }

  function syncGroupButtons() {
    document.querySelectorAll("[data-group-select]").forEach(function (b) {
      b.hidden = !selecting;
      if (!selecting) return;
      var lis = b.closest(".recipe-group").querySelectorAll("[data-selectable] > li:not([hidden])");
      var all = lis.length && Array.prototype.every.call(lis, function (li) { return li.classList.contains("is-picked"); });
      b.textContent = all ? "Clear" : "Select all";
    });
  }

  function setPicked(li, on) {
    li.classList.toggle("is-picked", on);
    var a = li.querySelector("a");
    if (a) a.setAttribute("aria-pressed", on ? "true" : "false");
  }

  function startSelecting(firstLi) {
    if (!bar) return;
    selecting = true;
    document.body.classList.add("is-selecting");
    bar.hidden = false;
    var menu = document.querySelector(".topbar details.overflow");
    if (menu) menu.open = false;
    if (firstLi) setPicked(firstLi, true);
    updateBar();
  }

  function stopSelecting() {
    selecting = false;
    document.body.classList.remove("is-selecting");
    picked().forEach(function (li) { setPicked(li, false); });
    if (bar) { bar.hidden = true; var d = bar.querySelector("details"); if (d) d.open = false; }
    syncGroupButtons();
  }

  // Long-press: hold ~450ms without moving. Suppresses the click that follows,
  // and the browser's own long-press menu on links.
  var pressTimer = null, pressStart = null, swallowClick = false;
  document.querySelectorAll("[data-selectable]").forEach(function (list) {
    list.addEventListener("pointerdown", function (e) {
      swallowClick = false;
      var li = e.target.closest("li[data-id]");
      if (!li || selecting || e.button > 0) return;
      pressStart = { x: e.clientX, y: e.clientY };
      pressTimer = setTimeout(function () {
        pressTimer = null; swallowClick = true;
        if (navigator.vibrate) { try { navigator.vibrate(15); } catch (err) {} }
        startSelecting(li);
      }, 450);
    });
    list.addEventListener("pointermove", function (e) {
      if (pressTimer && pressStart && (Math.abs(e.clientX - pressStart.x) > 8 || Math.abs(e.clientY - pressStart.y) > 8)) {
        clearTimeout(pressTimer); pressTimer = null;
      }
    });
    ["pointerup", "pointercancel", "pointerleave"].forEach(function (ev) {
      list.addEventListener(ev, function () { if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; } });
    });
    list.addEventListener("contextmenu", function (e) { if (e.target.closest("li[data-id]")) e.preventDefault(); });
    list.addEventListener("click", function (e) {
      var li = e.target.closest("li[data-id]");
      if (!li) return;
      if (swallowClick) { swallowClick = false; e.preventDefault(); return; }
      if (!selecting) return;              // normal tap: open the ingredient
      e.preventDefault();
      setPicked(li, !li.classList.contains("is-picked"));
      updateBar();
    });
  });

  document.querySelectorAll("[data-group-select]").forEach(function (b) {
    b.addEventListener("click", function () {
      var lis = Array.prototype.slice.call(b.closest(".recipe-group").querySelectorAll("[data-selectable] > li:not([hidden])"));
      var all = lis.every(function (li) { return li.classList.contains("is-picked"); });
      lis.forEach(function (li) { setPicked(li, !all); });
      updateBar();
    });
  });

  var startBtn = document.querySelector("[data-select-start]");
  if (startBtn) startBtn.addEventListener("click", function () { startSelecting(null); });
  if (bar) bar.querySelector("[data-select-cancel]").addEventListener("click", stopSelecting);
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && selecting && !(sheet && sheet.open)) stopSelecting();
  });

  // ------------------------------------------------------------- actions
  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ""; }

  function bulk(payload) {
    return fetch(bar.dataset.bulkUrl, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify(payload),
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok || !j.ok) throw new Error(j.error || ("Something went wrong (" + r.status + ")."));
        return j;
      });
    });
  }

  // Reload in place, then show the toast (with Undo when there's a previous state).
  function reloadWithToast(message, previous) {
    try {
      sessionStorage.setItem(TOAST_KEY, JSON.stringify({ message: message, previous: previous || null }));
      sessionStorage.setItem(SCROLL_KEY, String(window.scrollY));
    } catch (e) {}
    location.reload();
  }

  function run(payload) {
    var ids = picked().map(function (li) { return +li.dataset.id; });
    payload.ids = ids;
    return bulk(payload).then(function (j) { reloadWithToast(j.message, j.previous); })
      .catch(function (err) { if (window.showToast) window.showToast({ message: err.message }); });
  }

  if (bar) bar.querySelectorAll("[data-bulk]").forEach(function (b) {
    b.addEventListener("click", function () {
      var action = b.dataset.bulk;
      var n = picked().length;
      bar.querySelector("details").open = false;
      if (action === "retire") {
        window.mkConfirm({
          title: "Retire " + n + " ingredient" + (n === 1 ? "" : "s") + "?",
          body: "They're hidden from stock and Lets Cook but kept in your history. You can undo this straight after.",
          ok: "Retire",
        }).then(function (yes) { if (yes) run({ action: "retire" }); });
      } else {
        run({ action: action });
      }
    });
  });

  // Move sheet
  if (sheet && bar) {
    var go = sheet.querySelector("[data-move-go]");
    var title = sheet.querySelector("#move-title");
    function chosen() { return sheet.querySelector('input[name="move-target"]:checked'); }
    function syncGo() {
      var n = picked().length, c = chosen();
      go.disabled = !c;
      go.textContent = c ? "Move " + n + " to " + c.dataset.name : "Move";
    }
    bar.querySelector("[data-move]").addEventListener("click", function () {
      var n = picked().length;
      title.textContent = "Move " + n + " ingredient" + (n === 1 ? "" : "s") + " to…";
      sheet.querySelectorAll('input[name="move-target"]').forEach(function (i) { i.checked = false; });
      syncGo();
      sheet.showModal();
    });
    sheet.addEventListener("change", syncGo);
    sheet.querySelector("[data-move-cancel]").addEventListener("click", function () { sheet.close(); });
    go.addEventListener("click", function () {
      var c = chosen(); if (!c) return;
      go.disabled = true;
      run({ action: "move", category_id: +c.value }).then(function () { go.disabled = false; });
    });
  }

  // ------------------------------------------------------------- start up
  var saved = null;
  try { saved = sessionStorage.getItem(KEY); } catch (e) {}
  activate(saved || "standard");

  // A bulk action just reloaded the page: restore the scroll, show its toast.
  try {
    var y = sessionStorage.getItem(SCROLL_KEY);
    if (y !== null) { sessionStorage.removeItem(SCROLL_KEY); window.scrollTo(0, +y); }
    var t = sessionStorage.getItem(TOAST_KEY);
    if (t) {
      sessionStorage.removeItem(TOAST_KEY);
      t = JSON.parse(t);
      if (window.showToast) window.showToast({
        message: t.message,
        actionLabel: t.previous ? "Undo" : null,
        onAction: t.previous ? function () {
          bulk({ action: "restore", previous: t.previous })
            .then(function (j) { reloadWithToast(j.message, null); })
            .catch(function (err) { window.showToast({ message: err.message }); });
        } : null,
      });
    }
  } catch (e) {}
})();
