/* Johanna L — progressive enhancement only. The site works without this file. */
(function () {
  "use strict";

  var doc = document.documentElement;
  doc.classList.add("js");
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- Header: blur when scrolled, hide when scrolling down ------------ */
  var header = document.querySelector("[data-header]");
  var progress = document.querySelector(".scroll-progress");
  var lastY = window.scrollY;
  var ticking = false;

  function onScroll() {
    var y = window.scrollY;
    if (header) {
      header.classList.toggle("is-scrolled", y > 8);
      var menuOpen = document.querySelector(".nav.is-open");
      header.classList.toggle("is-hidden", y > lastY && y > 320 && !menuOpen);
    }
    if (progress && document.querySelector(".post-body")) {
      var max = doc.scrollHeight - window.innerHeight;
      progress.style.transform = "scaleX(" + (max > 0 ? Math.min(y / max, 1) : 0) + ")";
    }
    lastY = y;
    ticking = false;
  }
  window.addEventListener("scroll", function () {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(onScroll);
    }
  }, { passive: true });
  onScroll();

  /* ---- Appearance: mode (light / dark / auto) and colour palette ------- */
  var toggleBtn = document.querySelector(".appearance-toggle");
  var panel = document.getElementById("appearance-panel");
  if (toggleBtn && panel) {
    var root = document.documentElement;

    function store(key, value) {
      try { localStorage.setItem(key, value); } catch (e) {}
    }
    function currentTheme() { return root.getAttribute("data-theme") || "auto"; }
    function currentPalette() { return root.getAttribute("data-palette") || "atelier"; }

    function syncUI() {
      panel.querySelectorAll("[data-theme-choice]").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-theme-choice") === currentTheme()));
      });
      panel.querySelectorAll("[data-palette-choice]").forEach(function (b) {
        b.setAttribute("aria-pressed", String(b.getAttribute("data-palette-choice") === currentPalette()));
      });
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute("content", getComputedStyle(root).getPropertyValue("--c-paper").trim() || "#FBF7F0");
    }

    function fade() {
      if (reduceMotion) return;
      root.classList.add("theme-fade");
      setTimeout(function () { root.classList.remove("theme-fade"); }, 500);
    }

    function setPanel(open) {
      panel.hidden = !open;
      toggleBtn.setAttribute("aria-expanded", String(open));
    }

    toggleBtn.addEventListener("click", function () { setPanel(panel.hidden); });
    document.addEventListener("click", function (e) {
      if (!panel.hidden && !e.target.closest(".appearance")) setPanel(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !panel.hidden) { setPanel(false); toggleBtn.focus(); }
    });

    panel.addEventListener("click", function (e) {
      var themeBtn = e.target.closest("[data-theme-choice]");
      var paletteBtn = e.target.closest("[data-palette-choice]");
      if (themeBtn) {
        var choice = themeBtn.getAttribute("data-theme-choice");
        fade();
        if (choice === "auto") { root.removeAttribute("data-theme"); store("jl-theme", "auto"); }
        else { root.setAttribute("data-theme", choice); store("jl-theme", choice); }
      } else if (paletteBtn) {
        var name = paletteBtn.getAttribute("data-palette-choice");
        fade();
        if (name === "atelier") root.removeAttribute("data-palette");
        else root.setAttribute("data-palette", name);
        store("jl-palette", name);
      } else {
        return;
      }
      syncUI();
    });

    // "Auto" follows the device: keep the browser colour in step when it changes
    if (window.matchMedia) {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", syncUI);
    }
    syncUI();
  }

  /* ---- Mobile menu ----------------------------------------------------- */
  var toggle = document.querySelector(".menu-toggle");
  var nav = document.getElementById("site-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      var open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    function closeMenu(refocus) {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
      if (refocus) toggle.focus();
    }
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("is-open")) closeMenu(true);
    });
    document.addEventListener("click", function (e) {
      if (nav.classList.contains("is-open") && !e.target.closest("#site-nav, .menu-toggle")) closeMenu(false);
    });
    nav.addEventListener("click", function (e) {
      if (e.target.closest("a")) closeMenu(false);
    });
  }

  /* ---- Headline: words rise in one after another ----------------------- */
  document.querySelectorAll("[data-rise]").forEach(function (el) {
    if (reduceMotion) return;
    var i = 0;
    (function split(node) {
      Array.prototype.slice.call(node.childNodes).forEach(function (child) {
        if (child.nodeType === 3) {
          var frag = document.createDocumentFragment();
          child.textContent.split(/(\s+)/).forEach(function (part) {
            if (!part) return;
            if (/^\s+$/.test(part)) {
              frag.appendChild(document.createTextNode(part));
            } else {
              var span = document.createElement("span");
              span.textContent = part;
              span.style.setProperty("--i", i++);
              frag.appendChild(span);
            }
          });
          node.replaceChild(frag, child);
        } else if (child.nodeType === 1 && !child.classList.contains("brush")) {
          split(child);
        }
      });
    })(el);
    el.classList.add("rise");
  });

  /* ---- Reveal on scroll ------------------------------------------------ */
  var revealEls = document.querySelectorAll("[data-reveal]");
  if ("IntersectionObserver" in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });

    // stagger siblings inside the same grid
    document.querySelectorAll("[data-reveal-group]").forEach(function (group) {
      Array.prototype.forEach.call(group.querySelectorAll("[data-reveal]"), function (el, i) {
        el.style.setProperty("--d", i % 6);
      });
    });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("is-visible"); });
  }

  /* ---- Lazy images fade in -------------------------------------------- */
  document.querySelectorAll('img[loading="lazy"]').forEach(function (img) {
    function done() { img.classList.add("is-loaded"); }
    if (img.complete) done();
    else {
      img.addEventListener("load", done, { once: true });
      img.addEventListener("error", done, { once: true });   // never leave a broken image invisible
    }
  });

  /* ---- Hero card follows the pointer ---------------------------------- */
  var heroArt = document.querySelector(".hero-art");
  var heroCard = document.querySelector(".hero-card");
  if (heroArt && heroCard && !reduceMotion && window.matchMedia("(hover: hover)").matches) {
    var tiltFrame = 0;
    heroArt.addEventListener("pointermove", function (e) {
      if (tiltFrame) return;
      var cx = e.clientX, cy = e.clientY;
      tiltFrame = requestAnimationFrame(function () {
        tiltFrame = 0;
        var r = heroArt.getBoundingClientRect();
        var x = (cx - r.left) / r.width - 0.5;
        var y = (cy - r.top) / r.height - 0.5;
        heroCard.style.transform =
          "rotate(-2deg) rotateY(" + (x * 10).toFixed(2) + "deg) rotateX(" + (-y * 8).toFixed(2) + "deg)";
      });
    }, { passive: true });
    heroArt.addEventListener("pointerleave", function () {
      heroCard.style.transform = "";
    });
  }

  /* ---- Lightbox: arrows, swipe, focus kept inside, page scroll locked -- */
  var lightbox = document.querySelector(".lightbox");
  if (lightbox) {
    var lbImg = lightbox.querySelector("img");
    var lastFocus = null;
    var items = [];
    var index = 0;

    function collect() {
      items = Array.prototype.slice.call(document.querySelectorAll("[data-lightbox]"));
    }
    function show(i) {
      if (!items.length) return;
      index = (i + items.length) % items.length;
      var t = items[index];
      lbImg.src = t.getAttribute("data-lightbox");
      lbImg.alt = t.getAttribute("data-alt") || "";
      // warm the neighbour so the next step feels instant
      var next = items[(index + 1) % items.length].getAttribute("data-lightbox");
      if (next) new Image().src = next;
    }
    function openLightbox(trigger) {
      collect();
      lastFocus = trigger;
      lightbox.hidden = false;
      doc.style.overflow = "hidden";
      show(Math.max(items.indexOf(trigger), 0));
      lightbox.querySelector(".lightbox-close").focus();
    }
    function closeLightbox() {
      lightbox.hidden = true;
      lbImg.removeAttribute("src");
      doc.style.overflow = "";
      if (lastFocus) lastFocus.focus();
    }
    document.addEventListener("click", function (e) {
      var trigger = e.target.closest("[data-lightbox]");
      if (trigger) {
        e.preventDefault();
        openLightbox(trigger);
      } else if (!lightbox.hidden && (e.target === lightbox || e.target.closest(".lightbox-close"))) {
        closeLightbox();
      }
    });
    document.addEventListener("keydown", function (e) {
      if (lightbox.hidden) return;
      if (e.key === "Escape") closeLightbox();
      else if (e.key === "ArrowRight") show(index + 1);
      else if (e.key === "ArrowLeft") show(index - 1);
      else if (e.key === "Tab") {
        // only the close button is interactive: keep focus on it
        e.preventDefault();
        lightbox.querySelector(".lightbox-close").focus();
      }
    });
    var touchX = null;
    lightbox.addEventListener("touchstart", function (e) { touchX = e.touches[0].clientX; }, { passive: true });
    lightbox.addEventListener("touchend", function (e) {
      if (touchX === null) return;
      var dx = e.changedTouches[0].clientX - touchX;
      touchX = null;
      if (Math.abs(dx) > 50) show(index + (dx < 0 ? 1 : -1));
    }, { passive: true });
  }

  /* ---- Artwork gallery thumbnails swap the main image ------------------ */
  var main = document.querySelector("[data-main-image]");
  document.querySelectorAll("[data-thumb]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      if (!main) return;
      var img = main.querySelector("img");
      img.style.opacity = 0;
      setTimeout(function () {
        img.src = btn.getAttribute("data-thumb");
        img.alt = btn.getAttribute("data-alt") || "";
        main.querySelector("button").setAttribute("data-lightbox", btn.getAttribute("data-full"));
        img.style.opacity = 1;
      }, 180);
      document.querySelectorAll("[data-thumb]").forEach(function (b) { b.classList.remove("is-active"); });
      btn.classList.add("is-active");
    });
  });

  /* ---- Checkout: live shipping cost ------------------------------------ */
  var table = document.getElementById("shipping-table");
  var countrySelect = document.querySelector("[data-country-select]");
  if (table && countrySelect) {
    var rates = JSON.parse(table.textContent);
    var subtotal = parseFloat(document.querySelector("[data-subtotal]").getAttribute("data-subtotal"));
    var shipEl = document.querySelector("[data-shipping]");
    var totalEl = document.querySelector("[data-total]");
    var estimateEl = document.querySelector("[data-estimate]");
    var lang = document.documentElement.lang;

    function money(n) {
      var s = n.toFixed(2);
      return lang === "de" ? s.replace(".", ",") + " €" : "€" + s;
    }
    function update() {
      var rate = rates[countrySelect.value];
      if (!rate) {
        shipEl.textContent = "—";
        totalEl.textContent = money(subtotal);
        if (estimateEl) estimateEl.textContent = "";
        return;
      }
      var ship = parseFloat(rate.cost);
      shipEl.textContent = ship === 0 ? shipEl.getAttribute("data-free") : money(ship);
      totalEl.textContent = money(subtotal + ship);
      if (estimateEl) estimateEl.textContent = rate.estimate || "";
    }
    countrySelect.addEventListener("change", update);
    update();
  }

  /* ---- Layers slider: drag from the sketch to the finished painting ---- */
  document.querySelectorAll("[data-layers] .layers-range").forEach(function (range) {
    var stage = range.closest(".layers-stage");
    function set() { stage.style.setProperty("--pos", range.value + "%"); }
    range.addEventListener("input", set);
    set();
  });

  /* ---- Instant navigation: fetch a page when the pointer/finger approaches */
  if (!(navigator.connection && navigator.connection.saveData)) {
    var prefetched = {};
    var prefetch = function (e) {
      var a = e.target.closest && e.target.closest("a[href]");
      if (!a || a.origin !== location.origin || a.target || a.hasAttribute("download")) return;
      if (/^\/(admin|documents|cart|checkout)/.test(a.pathname) || a.hash && a.pathname === location.pathname) return;
      if (prefetched[a.href] || a.href === location.href) return;
      prefetched[a.href] = true;
      var l = document.createElement("link");
      l.rel = "prefetch";
      l.href = a.href;
      document.head.appendChild(l);
    };
    document.addEventListener("pointerenter", prefetch, { capture: true, passive: true });
    document.addEventListener("touchstart", prefetch, { passive: true });
  }

  /* ---- Toasts can be dismissed with a click ---------------------------- */
  document.querySelectorAll(".toast").forEach(function (t) {
    t.addEventListener("click", function () { t.remove(); });
  });
})();
