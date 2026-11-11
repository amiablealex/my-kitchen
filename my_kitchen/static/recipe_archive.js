// Archiving from the Recipes page, with Undo (Phase 24; swipe + select 0.30.1).
//
// Three ways in, one mechanism:
//   * Swipe a row LEFT (touch). Past ~40% of its width it archives; short of
//     that it springs back. Left, not right: Android's back gesture lives on
//     the left edge. A pink archive mark shows behind the row as it slides.
//   * Select mode: press and hold a row (or ⋯ → Select recipes), tap more,
//     then Archive in the docked bar. Select all in each group respects the
//     filter.
//   * A failed attempt's × (it has no recipe page, so no ⋯ menu).
// Every row knows what archiving it means (data-archive-key/-id): a picked
// pair archives the pick, an unpicked "Pick one" pair archives both, a failed
// attempt archives the attempt. The server reports exactly what it touched and
// Undo hands that back, putting the same row elements back where they were.
// No confirmation: archiving is fully reversible (Undo, or the Archived page).
// Endpoint URLs come from data-* on #recipe-bank (ingress-safe); POSTs carry
// X-CSRFToken from base.html's meta tag.
(function () {
  var bank = document.getElementById("recipe-bank");
  if (!bank) return;
  var archiveUrl = bank.dataset.archiveUrl;
  var restoreUrl = bank.dataset.restoreUrl;
  var bar = document.getElementById("select-bar");
  var selecting = false;

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  }
  function post(url, body) {
    return fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      body: JSON.stringify(body),
    }).then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); });
  }
  function rows() { return Array.prototype.slice.call(bank.querySelectorAll("li.recipe-row[data-archive-key]")); }
  function recount(group) {
    if (!group) return;
    var n = group.querySelectorAll(".recipe-row").length;
    var count = group.querySelector(".recipe-group-count");
    if (count) count.textContent = n;
    group.hidden = n === 0;
  }
  function itemOf(row) { var o = {}; o[row.dataset.archiveKey] = +row.dataset.archiveId; return o; }
  function recipesIn(row) {
    if (row.hasAttribute("data-archive-failed")) return 0;
    return +(row.dataset.archiveN || 1);
  }

  // Archive a set of rows: remove them, toast, Undo puts them back.
  function archiveRows(list) {
    if (!list.length) return Promise.resolve();
    var spots = list.map(function (row) {
      return { row: row, parent: row.parentNode, next: row.nextSibling, group: row.closest(".recipe-group") };
    });
    return post(archiveUrl, { rows: list.map(itemOf) }).then(function (touched) {
      spots.forEach(function (s) {
        s.row.classList.remove("is-picked", "is-swiping", "is-gone");
        s.row.style.removeProperty("--dx");
        if (s.row.parentNode) s.row.parentNode.removeChild(s.row);
        recount(s.group);
      });
      var nRecipes = list.reduce(function (a, r) { return a + recipesIn(r); }, 0);
      var nFailed = list.filter(function (r) { return r.hasAttribute("data-archive-failed"); }).length;
      var msg = nRecipes === 0 ? (nFailed === 1 ? "Cleared." : "Cleared " + nFailed + " failed attempts.")
              : nRecipes === 1 ? "Archived." : "Archived " + nRecipes + " recipes.";
      window.showToast({
        message: msg, actionLabel: "Undo",
        onAction: function () {
          post(restoreUrl, touched).then(function () {
            // Re-insert in reverse so each "next sibling" is back first.
            spots.slice().reverse().forEach(function (s) {
              s.parent.insertBefore(s.row, s.next && s.next.parentNode === s.parent ? s.next : null);
              recount(s.group);
            });
          }).catch(function () {
            window.showToast({ message: "Couldn't restore. Try the Archived page." });
          });
        },
      });
    }).catch(function () {
      spots.forEach(function (s) { s.row.classList.remove("is-gone", "is-swiping"); s.row.style.removeProperty("--dx"); });
      window.showToast({ message: "Couldn't archive that. Please try again." });
    });
  }

  // ---------------------------------------------------------- failed row ×
  bank.addEventListener("click", function (e) {
    var btn = e.target.closest(".row-archive");
    if (!btn || selecting) return;
    btn.disabled = true;
    archiveRows([btn.closest(".recipe-row")]).then(function () { btn.disabled = false; });
  });

  // ------------------------------------------------------------ select mode
  function picked() { return rows().filter(function (r) { return r.classList.contains("is-picked"); }); }
  function setPicked(row, on) { row.classList.toggle("is-picked", on); row.setAttribute("aria-selected", on ? "true" : "false"); }
  function syncGroupButtons() {
    bank.querySelectorAll("[data-group-select]").forEach(function (b) {
      b.hidden = !selecting;
      if (!selecting) return;
      var vis = Array.prototype.filter.call(b.closest(".recipe-group").querySelectorAll("li.recipe-row"), function (r) { return !r.hidden; });
      var all = vis.length && vis.every(function (r) { return r.classList.contains("is-picked"); });
      b.textContent = all ? "Clear" : "Select all";
    });
  }
  function updateBar() {
    var n = picked().length;
    bar.querySelector(".select-count strong").textContent = n;
    bar.querySelector("[data-archive-selected]").disabled = n === 0;
    syncGroupButtons();
  }
  function startSelecting(first) {
    if (!bar) return;
    selecting = true;
    document.body.classList.add("is-selecting");
    bar.hidden = false;
    var menu = document.querySelector(".topbar details.overflow");
    if (menu) menu.open = false;
    if (first) setPicked(first, true);
    updateBar();
  }
  function stopSelecting() {
    selecting = false;
    document.body.classList.remove("is-selecting");
    rows().forEach(function (r) { setPicked(r, false); r.removeAttribute("aria-selected"); });
    if (bar) bar.hidden = true;
    syncGroupButtons();
  }
  var startBtn = document.querySelector("[data-select-start]");
  if (startBtn) startBtn.addEventListener("click", function () { startSelecting(null); });
  if (bar) {
    bar.querySelector("[data-select-cancel]").addEventListener("click", stopSelecting);
    bar.querySelector("[data-archive-selected]").addEventListener("click", function () {
      var list = picked();
      archiveRows(list).then(stopSelecting);
    });
  }
  bank.querySelectorAll("[data-group-select]").forEach(function (b) {
    b.addEventListener("click", function () {
      var vis = Array.prototype.filter.call(b.closest(".recipe-group").querySelectorAll("li.recipe-row"), function (r) { return !r.hidden; });
      var all = vis.every(function (r) { return r.classList.contains("is-picked"); });
      vis.forEach(function (r) { setPicked(r, !all); });
      updateBar();
    });
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && selecting) stopSelecting(); });

  // --------------------------------------------- press, hold, swipe, tap
  var g = null;            // the gesture in progress
  var swallowClick = false;
  var SWIPE_LOCK = 12, HOLD_MS = 450, HOLD_SLOP = 8, ARCHIVE_AT = 0.4;

  bank.addEventListener("pointerdown", function (e) {
    swallowClick = false;
    var row = e.target.closest("li.recipe-row[data-archive-key]");
    if (!row || e.button > 0 || e.target.closest(".row-archive")) return;
    g = { row: row, id: e.pointerId, x: e.clientX, y: e.clientY, dx: 0, mode: null,
          canSwipe: e.pointerType !== "mouse" && !selecting, w: row.getBoundingClientRect().width };
    if (!selecting) {
      g.hold = setTimeout(function () {
        if (!g || g.mode) return;
        g.mode = "held"; swallowClick = true;
        if (navigator.vibrate) { try { navigator.vibrate(15); } catch (err) {} }
        startSelecting(row);
      }, HOLD_MS);
    }
  });

  bank.addEventListener("pointermove", function (e) {
    if (!g || e.pointerId !== g.id) return;
    var dx = e.clientX - g.x, dy = e.clientY - g.y;
    if (!g.mode) {
      if (Math.abs(dx) > HOLD_SLOP || Math.abs(dy) > HOLD_SLOP) clearTimeout(g.hold);
      if (g.canSwipe && dx < -SWIPE_LOCK && Math.abs(dx) > Math.abs(dy) * 1.4) {
        g.mode = "swipe";
        try { g.row.setPointerCapture(g.id); } catch (err) {}
        g.row.classList.add("is-swiping");
      } else if (Math.abs(dy) > SWIPE_LOCK) {
        clearTimeout(g.hold); g = null;      // it's a scroll; leave it alone
        return;
      }
    }
    if (g.mode === "swipe") {
      g.dx = Math.min(0, dx);
      g.row.style.setProperty("--dx", g.dx + "px");
      g.row.classList.toggle("is-armed", -g.dx > g.w * ARCHIVE_AT);
    }
  });

  function endGesture(e) {
    if (!g || (e && e.pointerId !== g.id)) return;
    clearTimeout(g.hold);
    var cur = g; g = null;
    if (cur.mode !== "swipe") return;
    swallowClick = true;
    var row = cur.row;
    row.classList.remove("is-armed");
    if (-cur.dx > cur.w * ARCHIVE_AT && e && e.type === "pointerup") {
      row.classList.add("is-gone");           // slide fully out, then archive
      row.style.setProperty("--dx", -cur.w + "px");
      setTimeout(function () { archiveRows([row]); }, 180);
    } else {
      row.classList.remove("is-swiping");     // spring back
      row.style.removeProperty("--dx");
    }
  }
  bank.addEventListener("pointerup", endGesture);
  bank.addEventListener("pointercancel", endGesture);

  bank.addEventListener("contextmenu", function (e) { if (e.target.closest("li.recipe-row")) e.preventDefault(); });

  // Taps: after a swipe or hold, swallow the click; in select mode, toggle.
  bank.addEventListener("click", function (e) {
    var row = e.target.closest("li.recipe-row[data-archive-key]");
    if (!row) return;
    if (swallowClick) { swallowClick = false; e.preventDefault(); e.stopPropagation(); return; }
    if (!selecting || e.target.closest(".row-archive")) return;
    e.preventDefault();
    setPicked(row, !row.classList.contains("is-picked"));
    updateBar();
  }, true);
})();
