// Inline meal-type / cuisine tag editor on the recipe page (Phase 17). Mirrors
// the 4a ingredient link editor: a view with pills + an edit panel saved via
// AJAX (CSRF via X-CSRFToken; endpoint URL injected with url_for, so it's
// ingress-safe). Cuisine is gated by the meal type's cuisine-bearing flag,
// matching the wizard hierarchy. Tags are a shared property of the recipe — no
// per-user scoping — and editable on any recipe (AI or user).
(function () {
  var root = document.getElementById("recipe-tags");
  if (!root) return;
  var url = root.dataset.tagsUrl;
  var view = root.querySelector(".recipe-tags-view");
  var panel = document.getElementById("recipe-tags-edit");
  var toggle = document.getElementById("tag-edit-toggle");
  var mealPill = document.getElementById("tag-meal-pill");
  var cuisinePill = document.getElementById("tag-cuisine-pill");
  var mealSel = document.getElementById("tag-meal-select");
  var cuisineSel = document.getElementById("tag-cuisine-select");
  var cuisineLabel = document.getElementById("tag-cuisine-label");
  var saveBtn = document.getElementById("tag-save");
  var cancelBtn = document.getElementById("tag-cancel");
  var errEl = document.getElementById("tag-error");

  var cuisineMealTypes = [];
  try {
    var d = document.getElementById("tag-cuisine-meal-types");
    if (d) cuisineMealTypes = JSON.parse(d.textContent) || [];
  } catch (e) { cuisineMealTypes = []; }

  function csrfToken() {
    var m = document.querySelector('meta[name="csrf-token"]');
    return m ? m.getAttribute("content") : "";
  }
  function showErr(m) { if (errEl) { errEl.textContent = m; errEl.hidden = false; } }
  function hideErr() { if (errEl) { errEl.hidden = true; errEl.textContent = ""; } }

  function syncCuisineVisibility() {
    var allowed = mealSel.value && cuisineMealTypes.indexOf(mealSel.value) !== -1;
    if (cuisineLabel) cuisineLabel.hidden = !allowed;
    if (!allowed) cuisineSel.value = "";
  }
  mealSel.addEventListener("change", syncCuisineVisibility);

  function openPanel() { hideErr(); syncCuisineVisibility(); view.hidden = true; panel.hidden = false; }
  function closePanel() { panel.hidden = true; view.hidden = false; }
  toggle.addEventListener("click", openPanel);
  cancelBtn.addEventListener("click", closePanel);

  function setPill(pill, value, noneText) {
    if (value) {
      pill.textContent = value;
      pill.classList.remove("tag-pill--none");
    } else {
      pill.textContent = noneText;
      pill.classList.add("tag-pill--none");
    }
  }

  saveBtn.addEventListener("click", function () {
    saveBtn.disabled = true;
    hideErr();
    fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrfToken() },
      body: new URLSearchParams({ meal_type: mealSel.value, cuisine: cuisineSel.value }),
    })
      .then(function (r) {
        return r.json().catch(function () { return {}; })
          .then(function (data) { return { ok: r.ok, data: data }; });
      })
      .then(function (res) {
        if (!res.ok) { showErr((res.data && res.data.message) || "Could not save tags."); return; }
        setPill(mealPill, res.data.meal_type, "No meal type");
        // Cuisine pill is hidden entirely when the meal type can't bear one.
        if (res.data.cuisine_allowed) {
          cuisinePill.hidden = false;
          setPill(cuisinePill, res.data.cuisine, "No cuisine");
        } else {
          cuisinePill.hidden = true;
        }
        closePanel();
      })
      .catch(function () { showErr("Could not save — is the server still running?"); })
      .finally(function () { saveBtn.disabled = false; });
  });
})();
