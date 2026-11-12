// Recipe from a photo (Phase 35). Markup: templates/wizard/recipe_photo.html.
// Each picked photo is shrunk on the phone (long edge 1600px, JPEG) and shown
// as a numbered page. On submit the shrunk pages are put into the form's real
// file input (via DataTransfer) and the form posts normally, so the server's
// reply — the review form — simply loads as the next page.
(function () {
  var form = document.getElementById("photo-form");
  if (!form) return;
  var MAX_EDGE = 1600;
  var MAX = +form.dataset.maxPages || 4;
  var pick = document.getElementById("photo-pick");
  var real = document.getElementById("photo-pages");
  var strip = document.getElementById("photo-strip");
  var addBtn = document.getElementById("photo-add");
  var go = document.getElementById("photo-go");
  var err = document.getElementById("photo-error");
  var pages = [];   // [{blob, url}]

  function error(msg) { err.textContent = msg || ""; err.hidden = !msg; }

  function shrink(file) {
    return new Promise(function (resolve, reject) {
      var img = new Image();
      var url = URL.createObjectURL(file);
      img.onload = function () {
        var scale = Math.min(1, MAX_EDGE / Math.max(img.naturalWidth, img.naturalHeight));
        var c = document.createElement("canvas");
        c.width = Math.round(img.naturalWidth * scale);
        c.height = Math.round(img.naturalHeight * scale);
        c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url);
        c.toBlob(function (b) { b ? resolve(b) : reject(); }, "image/jpeg", 0.85);
      };
      img.onerror = function () { URL.revokeObjectURL(url); reject(); };
      img.src = url;
    });
  }

  function render() {
    strip.innerHTML = "";
    pages.forEach(function (p, i) {
      var li = document.createElement("li");
      li.className = "photo-page";
      var im = document.createElement("img");
      im.src = p.url;
      im.alt = "Page " + (i + 1);
      var n = document.createElement("span");
      n.className = "photo-n";
      n.textContent = i + 1;
      var x = document.createElement("button");
      x.type = "button";
      x.className = "photo-x";
      x.setAttribute("aria-label", "Remove page " + (i + 1));
      x.textContent = "×";
      x.addEventListener("click", function () {
        URL.revokeObjectURL(p.url);
        pages.splice(i, 1);
        render();
      });
      li.appendChild(im); li.appendChild(n); li.appendChild(x);
      strip.appendChild(li);
    });
    strip.hidden = pages.length === 0;
    addBtn.hidden = pages.length >= MAX;
    addBtn.querySelector("span").textContent = pages.length ? "Add another page" : "Add a page";
    go.disabled = pages.length === 0;
    go.textContent = pages.length > 1 ? "Read the recipe (" + pages.length + " pages)" : "Read the recipe";
  }

  pick.addEventListener("change", function () {
    var files = Array.prototype.slice.call(pick.files || []);
    pick.value = "";
    error("");
    var room = MAX - pages.length;
    if (files.length > room) error("Up to " + MAX + " pages — the first " + room + " were added.");
    files.slice(0, room).reduce(function (chain, f) {
      return chain.then(function () {
        return shrink(f).then(function (blob) {
          pages.push({ blob: blob, url: URL.createObjectURL(blob) });
          render();
        }, function () { error("One photo couldn't be opened, so it was skipped."); });
      });
    }, Promise.resolve());
  });

  form.addEventListener("submit", function (e) {
    if (!pages.length) { e.preventDefault(); return; }
    try {
      var dt = new DataTransfer();
      pages.forEach(function (p, i) {
        dt.items.add(new File([p.blob], "page-" + (i + 1) + ".jpg", { type: "image/jpeg" }));
      });
      real.files = dt.files;
    } catch (ex) {
      e.preventDefault();
      error("This browser can't send the photos. Try another browser, or paste the recipe's text instead.");
      return;
    }
    go.disabled = true;
    addBtn.hidden = true;
    strip.querySelectorAll(".photo-x").forEach(function (b) { b.hidden = true; });
    go.textContent = "Reading " + (pages.length > 1 ? pages.length + " pages" : "the recipe") + "…";
  });

  render();
})();
