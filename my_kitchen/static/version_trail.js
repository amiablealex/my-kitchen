// The version trail as a tree (0.42.1).
// A branch row is joined to the version it was made from by an elbow: a line
// down from that version's number bubble, curving into the row. Plain CSS
// can't know where a chip of any width ends up, so this measures it: for
// each branch row (in page order, so a parent row is placed before its
// branches), set the row's indent to meet the line and size the elbow from
// the bubble's bottom to the row's middle. Redrawn once the web fonts are in
// (they change chip widths) and on resize. Without JS, branch rows are just
// set in, with no line.
// Also scrolls the trail so the version being viewed is in sight on a phone.
(function () {
  var nav = document.querySelector(".version-trail");
  var tree = nav && nav.querySelector(".version-tree");
  if (!tree) return;

  function draw() {
    var box = tree.getBoundingClientRect();
    tree.querySelectorAll(".version-row[data-from]").forEach(function (row) {
      var bubble = tree.querySelector('[data-v="' + row.dataset.from + '"] .version-n');
      var elbow = row.querySelector(".version-elbow");
      if (!bubble || !elbow) return;
      var b = bubble.getBoundingClientRect();
      var x = b.left + b.width / 2 - box.left;
      row.style.paddingLeft = Math.round(x + 15) + "px";
      var r = row.getBoundingClientRect();
      var top = b.bottom - r.top + 3;
      elbow.style.left = Math.round(x - 1) + "px";
      elbow.style.top = Math.round(top) + "px";
      elbow.style.height = Math.max(0, Math.round(r.height / 2 - top)) + "px";
      elbow.hidden = false;
    });
  }

  function reveal() {
    var cur = tree.querySelector(".is-current");
    if (!cur) return;
    var n = nav.getBoundingClientRect(), c = cur.getBoundingClientRect();
    if (c.right > n.right) nav.scrollLeft += c.right - n.right + 16;
  }

  draw();
  reveal();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
  var t;
  window.addEventListener("resize", function () {
    clearTimeout(t);
    t = setTimeout(draw, 100);
  });
})();
