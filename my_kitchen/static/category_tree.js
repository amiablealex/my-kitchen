// Manage → Categories: reorder within a section (0.30.0).
//
// "Reorder" in a section's header switches just that section into reorder
// mode: rows stop opening, each gets a grip, and the add branch hides. Drag a
// row by its grip (it can't leave its trunk), or focus a grip and use the
// arrow keys. Every drop saves at once: the server renumbers the section 1..n.
// "Done" goes back to normal. Moving a category to another section is done on
// its own page, deliberately.
(function () {
  var cfg = document.getElementById("cat-tree-config");
  if (!cfg) return;
  var url = cfg.dataset.reorderUrl;

  function csrf() { var m = document.querySelector('meta[name="csrf-token"]'); return m ? m.content : ""; }
  function nodes(section) { return Array.prototype.slice.call(section.querySelectorAll(".cat-node[data-id]")); }
  function order(section) { return nodes(section).map(function (n) { return +n.dataset.id; }); }

  function save(section, before) {
    var ids = order(section);
    if (before && before.join() === ids.join()) return;
    fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf() },
      body: JSON.stringify({ section: section.dataset.section, ids: ids }),
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok || !j.ok) throw new Error(j.error || "Couldn't save the new order.");
      });
    }).catch(function (err) {
      if (window.showToast) window.showToast({ message: err.message + " Reloading…" });
      setTimeout(function () { location.reload(); }, 1600);
    });
  }

  function setMode(section, on) {
    section.classList.toggle("is-reordering", on);
    var btn = section.querySelector("[data-reorder]");
    btn.textContent = on ? "Done" : "Reorder";
    btn.setAttribute("aria-pressed", on ? "true" : "false");
    nodes(section).forEach(function (n) {
      n.querySelector(".cat-grip").tabIndex = on ? 0 : -1;
      n.querySelector(".cat-link").tabIndex = on ? -1 : 0;
    });
    var add = section.querySelector(".cat-add");
    if (add) add.open = false;
  }

  document.querySelectorAll(".cat-section").forEach(function (section) {
    var btn = section.querySelector("[data-reorder]");
    if (!btn) return;
    btn.addEventListener("click", function () { setMode(section, !section.classList.contains("is-reordering")); });

    // While reordering, a tap on a row does nothing (it isn't a link then).
    section.addEventListener("click", function (e) {
      if (section.classList.contains("is-reordering") && e.target.closest(".cat-link")) e.preventDefault();
    });

    // Keyboard: arrows on a focused grip move the row and save.
    section.addEventListener("keydown", function (e) {
      var grip = e.target.closest(".cat-grip");
      if (!grip || (e.key !== "ArrowUp" && e.key !== "ArrowDown")) return;
      e.preventDefault();
      var node = grip.closest(".cat-node"), before = order(section);
      var list = nodes(section), i = list.indexOf(node);
      if (e.key === "ArrowUp" && i > 0) list[i - 1].before(node);
      if (e.key === "ArrowDown" && i < list.length - 1) list[i + 1].after(node);
      grip.focus();
      save(section, before);
    });

    // Pointer drag by the grip. The row follows the finger; it swaps with a
    // neighbour once the finger passes that neighbour's middle.
    var drag = null;
    section.addEventListener("pointerdown", function (e) {
      var grip = e.target.closest(".cat-grip");
      if (!grip || !section.classList.contains("is-reordering")) return;
      e.preventDefault();
      var node = grip.closest(".cat-node");
      grip.setPointerCapture(e.pointerId);
      drag = { node: node, grip: grip, startY: e.clientY, top: node.getBoundingClientRect().top, before: order(section) };
      node.classList.add("is-dragging");
    });
    section.addEventListener("pointermove", function (e) {
      if (!drag) return;
      var node = drag.node;
      var list = nodes(section), i = list.indexOf(node);
      var prev = list[i - 1], next = list[i + 1];
      if (prev) { var pr = prev.getBoundingClientRect(); if (e.clientY < pr.top + pr.height / 2) prev.before(node); }
      if (next) { var nr = next.getBoundingClientRect(); if (e.clientY > nr.top + nr.height / 2) next.after(node); }
      // Visual follow: offset from where the row now sits.
      node.style.transform = "";
      var now = node.getBoundingClientRect().top;
      node.style.transform = "translateY(" + (e.clientY - drag.startY - (now - drag.top)) + "px)";
    });
    function end() {
      if (!drag) return;
      var d = drag; drag = null;
      d.node.classList.remove("is-dragging");
      d.node.style.transform = "";
      save(section, d.before);
    }
    section.addEventListener("pointerup", end);
    section.addEventListener("pointercancel", end);
  });
})();
