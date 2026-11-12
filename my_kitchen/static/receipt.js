// Scan a receipt (Phase 33). Markup: templates/stock/_receipt.html.
// 1. pick  — a file input (the phone offers camera or gallery).
// 2. frame — two bars the cook drags to just the item lines.
// 3. read  — the browser crops to the frame and shrinks it, then uploads ONLY
//            that crop. The server reads it with the AI and replies with the
//            stock sheet's contents; the stock sheet takes it from there.
(function () {
  var dlg = document.getElementById("receipt-sheet");
  var openBtn = document.getElementById("receipt-open");
  if (!dlg || !openBtn || !window.mkStockSheet) return;

  var MAX_EDGE = 2000;        // px, long edge of the upload — legible, and small
  var MIN_GAP = 0.08;         // the frame can't close up completely
  var TOAST_KEY = "mk-stock-toast";   // stock.js shows it after the reload

  var fileInput = dlg.querySelector("[data-file]");
  var img = dlg.querySelector("[data-img]");
  var frame = dlg.querySelector(".frame");
  var shadeTop = dlg.querySelector('[data-shade="top"]');
  var shadeBottom = dlg.querySelector('[data-shade="bottom"]');
  var readBtn = dlg.querySelector("[data-read]");
  var anotherBtn = dlg.querySelector("[data-another]");
  var errEl = dlg.querySelector("[data-error]");
  var steps = dlg.querySelectorAll("[data-step]");
  var top = 0.06, bottom = 0.94, objectUrl = null;

  function csrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") : "";
  }

  function show(step) {
    steps.forEach(function (s) { s.hidden = s.dataset.step !== step; });
    readBtn.hidden = step !== "frame";
    anotherBtn.hidden = step !== "frame";
    readBtn.disabled = false;
  }
  function error(msg) { errEl.textContent = msg || ""; errEl.hidden = !msg; }

  function reset() {
    if (objectUrl) { URL.revokeObjectURL(objectUrl); objectUrl = null; }
    img.removeAttribute("src");
    fileInput.value = "";
    top = 0.06; bottom = 0.94;
    error("");
    show("pick");
  }

  openBtn.addEventListener("click", function (e) {
    e.preventDefault();          // it sits inside the search box's <label>
    reset();
    dlg.showModal();
  });
  dlg.querySelector("[data-cancel]").addEventListener("click", function () { dlg.close(); reset(); });
  dlg.addEventListener("cancel", reset);
  anotherBtn.addEventListener("click", function () { fileInput.click(); });

  // ---- 1. pick ---------------------------------------------------------------
  fileInput.addEventListener("change", function () {
    var f = fileInput.files && fileInput.files[0];
    if (!f) return;
    error("");
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = URL.createObjectURL(f);
    img.onload = function () { top = 0.06; bottom = 0.94; layout(); show("frame"); };
    img.onerror = function () { error("That photo couldn't be opened. Try another one?"); show("pick"); };
    img.src = objectUrl;
  });

  // ---- 2. frame --------------------------------------------------------------
  function layout() {
    shadeTop.style.height = (top * 100) + "%";
    shadeBottom.style.height = ((1 - bottom) * 100) + "%";
    frame.querySelector('[data-handle="top"]').style.top = (top * 100) + "%";
    frame.querySelector('[data-handle="bottom"]').style.top = (bottom * 100) + "%";
  }

  frame.querySelectorAll("[data-handle]").forEach(function (h) {
    h.addEventListener("pointerdown", function (e) {
      e.preventDefault();
      h.setPointerCapture(e.pointerId);
      h.classList.add("is-dragging");
    });
    h.addEventListener("pointermove", function (e) {
      if (!h.hasPointerCapture(e.pointerId)) return;
      var r = img.getBoundingClientRect();
      var y = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height));
      if (h.dataset.handle === "top") top = Math.min(y, bottom - MIN_GAP);
      else bottom = Math.max(y, top + MIN_GAP);
      layout();
    });
    function end(e) {
      if (h.hasPointerCapture(e.pointerId)) h.releasePointerCapture(e.pointerId);
      h.classList.remove("is-dragging");
    }
    h.addEventListener("pointerup", end);
    h.addEventListener("pointercancel", end);
  });

  // ---- 3. crop, shrink, read -------------------------------------------------
  function croppedBlob() {
    var W = img.naturalWidth, H = img.naturalHeight;
    var sy = Math.round(top * H), sh = Math.max(1, Math.round((bottom - top) * H));
    var scale = Math.min(1, MAX_EDGE / Math.max(W, sh));
    var canvas = document.createElement("canvas");
    canvas.width = Math.round(W * scale);
    canvas.height = Math.round(sh * scale);
    canvas.getContext("2d").drawImage(img, 0, sy, W, sh, 0, 0, canvas.width, canvas.height);
    return new Promise(function (res) { canvas.toBlob(res, "image/jpeg", 0.85); });
  }

  readBtn.addEventListener("click", function () {
    readBtn.disabled = true;
    error("");
    croppedBlob()
      .then(function (blob) {
        if (!blob) throw new Error("crop failed");
        show("reading");
        var body = new FormData();
        body.append("image", blob, "receipt.jpg");
        return fetch(dlg.dataset.receiptUrl, {
          method: "POST", headers: { "X-CSRFToken": csrfToken() }, body: body,
        });
      })
      .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
      .then(function (d) {
        if (!d.ok) {
          show("frame");
          error(d.message || "The receipt couldn't be read just now. Try again?");
          return;
        }
        dlg.close();
        reset();
        openResults(d);
      })
      .catch(function () {
        show("frame");
        error("Couldn't reach the server. Try again?");
      });
  });

  function openResults(d) {
    var skipped = [];
    if (d.already) skipped.push(d.already + " already in stock");
    if (d.staples) skipped.push(d.staples + (d.staples === 1 ? " staple" : " staples") + " (always assumed)");
    if (!d.matched.length && !d.unplaced.length) {
      if (window.showToast) window.showToast({ message: "Everything on it is already in stock." });
      return;
    }
    window.mkStockSheet.open({
      mode: "in",
      title: "Found on your receipt",
      note: skipped.join(" · "),
      items: d.matched,
      unplaced: d.unplaced,
      onDone: function (changed) {
        try {
          sessionStorage.setItem(TOAST_KEY, JSON.stringify({
            message: "Added " + changed.length + " to stock", ids: changed }));
        } catch (e) {}
        window.location.reload();
      },
    });
  }
})();
