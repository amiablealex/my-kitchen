// Viewport debug overlay (diagnostic only). Turn on with ?vp=1 on any page (it
// sticks across pages via localStorage); turn off with ?vp=0. Shows what the
// browser thinks the viewport is, and where the bottom bar actually sits.
(function () {
  var q = new URLSearchParams(location.search).get("vp");
  try {
    if (q === "1") localStorage.setItem("mk-vp", "1");
    if (q === "0") localStorage.removeItem("mk-vp");
    if (localStorage.getItem("mk-vp") !== "1") return;
  } catch (e) { if (q !== "1") return; }

  function probe(css) {
    var d = document.createElement("div");
    d.style.cssText = "position:absolute;visibility:hidden;pointer-events:none;left:0;top:0;width:1px;" + css;
    document.body.appendChild(d);
    return d;
  }
  var pSafe = probe("height:0;padding-bottom:env(safe-area-inset-bottom,0px)");
  var pSvh = probe("height:100svh"), pDvh = probe("height:100dvh"), pLvh = probe("height:100lvh"), pVh = probe("height:100vh");
  var box = document.createElement("pre");
  box.style.cssText = "position:fixed;z-index:9999;top:60px;right:6px;margin:0;padding:6px 8px;max-width:62vw;" +
    "font:11px/1.35 ui-monospace,monospace;background:rgba(0,0,0,.82);color:#9ff;border-radius:8px;pointer-events:none;white-space:pre-wrap";
  document.body.appendChild(box);
  var nav = document.querySelector(".bottom-nav");
  var dock = document.querySelector(".wizard-dock");
  function r(n) { return Math.round(n * 10) / 10; }
  function tick() {
    var vv = window.visualViewport;
    var nr = nav ? nav.getBoundingClientRect() : null;
    var dr = dock ? dock.getBoundingClientRect() : null;
    box.textContent = [
      location.pathname,
      "innerH " + innerHeight + "  clientH " + document.documentElement.clientHeight,
      vv ? "vv.h " + r(vv.height) + "  vv.top " + r(vv.offsetTop) + "  scale " + r(vv.scale) : "no visualViewport",
      "vh " + pVh.offsetHeight + " svh " + pSvh.offsetHeight + " dvh " + pDvh.offsetHeight + " lvh " + pLvh.offsetHeight,
      "safe-bottom " + pSafe.offsetHeight + "  dpr " + devicePixelRatio,
      "scrollY " + Math.round(scrollY) + " / " + (document.documentElement.scrollHeight - innerHeight),
      "docW " + document.documentElement.scrollWidth + "  innerW " + innerWidth,
      nr ? "nav top " + r(nr.top) + " bottom " + r(nr.bottom) + " h " + r(nr.height) : "no nav",
      dr ? "dock bottom " + r(dr.bottom) : "",
    ].join("\n");
  }
  tick();
  ["scroll", "resize"].forEach(function (ev) { addEventListener(ev, tick, { passive: true }); });
  if (window.visualViewport) { visualViewport.addEventListener("resize", tick); visualViewport.addEventListener("scroll", tick); }
  setInterval(tick, 500);
})();
