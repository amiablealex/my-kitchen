// Servings scaler for the recipe page (Phase 24). Front-end only: nothing is
// posted or saved server-side; the chosen count lives in sessionStorage per
// recipe, so it survives the page's own reloads (adding a note, favouriting).
//
// Amounts are stored as verbatim text ("2", "½", "1 1/2", "1-2", "a splash",
// "2 large"), so only a LEADING number — or a leading range — is scaled; any
// trailing words are kept, and anything that doesn't start with a number
// ("a pinch", "to taste") is left exactly as written.
(function () {
  var box = document.getElementById("servings");
  if (!box) return;
  var base = parseInt(box.dataset.base, 10);
  if (!(base > 0)) return;

  var MIN = 1, MAX = Math.max(24, base * 4);
  var key = box.dataset.key;
  var out = box.querySelector(".servings-value");
  var reset = box.querySelector(".servings-reset");
  var note = box.querySelector(".servings-note");
  var servesEls = document.querySelectorAll(".js-serves");
  var amts = Array.prototype.slice.call(document.querySelectorAll(".ing-amt"));

  var GLYPHS = { "½": "1/2", "⅓": "1/3", "⅔": "2/3", "¼": "1/4", "¾": "3/4",
                 "⅕": "1/5", "⅙": "1/6", "⅛": "1/8", "⅜": "3/8", "⅝": "5/8", "⅞": "7/8" };
  var NICE = [[0, ""], [1 / 8, "⅛"], [1 / 4, "¼"], [1 / 3, "⅓"], [1 / 2, "½"],
              [2 / 3, "⅔"], [3 / 4, "¾"], [1, ""]];
  var NUM = "(\\d+\\s+\\d+\\/\\d+|\\d+\\/\\d+|\\d+(?:\\.\\d+)?)";
  var LEAD = new RegExp("^\\s*" + NUM + "(?:\\s*(-|–|to)\\s*" + NUM + ")?(.*)$");
  var METRIC = /^\s*(g|grams?|kg|kilos?|ml|millilitres?|l|litres?|liters?|cl)\b/i;

  function normalise(s) {
    return s.replace(/(\d)?([½⅓⅔¼¾⅕⅙⅛⅜⅝⅞])/g, function (_, d, g) {
      return (d ? d + " " : "") + GLYPHS[g];
    });
  }

  function toNumber(tok) {
    var parts = tok.trim().split(/\s+/), n = 0;
    parts.forEach(function (p) {
      if (p.indexOf("/") > -1) {
        var f = p.split("/");
        n += parseFloat(f[0]) / parseFloat(f[1]);
      } else {
        n += parseFloat(p);
      }
    });
    return n;
  }

  function fmtMetric(n) {
    if (n >= 100) return String(Math.round(n / 5) * 5);
    if (n >= 10) return String(Math.round(n));
    return String(Math.round(n * 10) / 10);
  }

  function fmtFraction(n) {
    if (n >= 10) return String(Math.round(n));
    var whole = Math.floor(n), frac = n - whole, best = NICE[0];
    NICE.forEach(function (c) { if (Math.abs(c[0] - frac) < Math.abs(best[0] - frac)) best = c; });
    if (best[0] === 1) { whole += 1; best = NICE[0]; }
    if (whole === 0 && best[1] === "") return "⅛"; // never scale a real amount to nothing
    return (whole ? String(whole) : "") + best[1];
  }

  // Returns the scaled text, or null when the amount has no leading number.
  function scale(raw, factor, unitText) {
    var m = normalise(raw).match(LEAD);
    if (!m) return null;
    var suffix = m[4] || "";
    var metric = METRIC.test(suffix) || METRIC.test(unitText);
    var fmt = metric ? fmtMetric : fmtFraction;
    var text = fmt(toNumber(m[1]) * factor);
    if (m[3]) text += (m[2] === "to" ? " to " : "–") + fmt(toNumber(m[3]) * factor);
    return text + suffix;
  }

  // The unit sits in the text node straight after the amount span.
  function unitAfter(el) {
    var t = el.nextSibling;
    return t && t.nodeType === 3 ? t.textContent : "";
  }

  function apply(n) {
    var factor = n / base;
    amts.forEach(function (el) {
      var raw = el.dataset.amount;
      if (factor === 1) { el.textContent = raw; el.classList.remove("is-scaled"); return; }
      var scaled = scale(raw, factor, unitAfter(el));
      el.textContent = scaled === null ? raw : scaled;
      el.classList.toggle("is-scaled", scaled !== null);
    });
    out.textContent = n;
    servesEls.forEach(function (s) { s.textContent = n; });
    reset.hidden = note.hidden = n === base;
    box.querySelector('[data-step="-1"]').disabled = n <= MIN;
    box.querySelector('[data-step="1"]').disabled = n >= MAX;
    try {
      if (n === base) sessionStorage.removeItem(key);
      else sessionStorage.setItem(key, String(n));
    } catch (e) { /* storage unavailable — scaling still works for this view */ }
  }

  var current = base;
  try {
    var saved = parseInt(sessionStorage.getItem(key), 10);
    if (saved >= MIN && saved <= MAX) current = saved;
  } catch (e) { /* ignore */ }

  box.addEventListener("click", function (e) {
    var b = e.target.closest("[data-step]");
    if (b) {
      current = Math.min(MAX, Math.max(MIN, current + parseInt(b.dataset.step, 10)));
      apply(current);
    } else if (e.target.closest(".servings-reset")) {
      current = base;
      apply(current);
    }
  });

  box.hidden = false;
  apply(current);
})();
