/* الصَّيَّاد — طبقة تحسين تدريجي (Progressive enhancement).
   كل السلوك الأساسي بالسيرفر (HTMX)؛ هذا الملف يضيف لمسات لا غير:
   الثيم، وكشف العناصر عند التمرير، وميلان البطاقات، وعدّادات متحرّكة.
   كله يحترم prefers-reduced-motion ويعمل الموقع تماماً بدونه. */

(function () {
  "use strict";

  var root = document.documentElement;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var finePointer = window.matchMedia("(pointer: fine)").matches;

  /* ---------- الثيم (فاتح/داكن) ----------
     السكربت المضمّن في <head> ضبط data-theme قبل أول رسم (بلا وميض).
     هنا نربط زر التبديل ونُبقي meta theme-color متزامناً. */
  var THEME_KEY = "sayyad-theme";
  var themeColors = { light: "#F5F7FB", dark: "#0A0E16" };

  function currentTheme() {
    var forced = root.getAttribute("data-theme");
    if (forced) return forced;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function syncThemeMeta(theme) {
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", themeColors[theme] || themeColors.light);
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      var isDark = theme === "dark";
      btn.setAttribute("aria-pressed", String(isDark));
      var icon = btn.querySelector("[data-theme-icon]");
      if (icon) icon.textContent = isDark ? "☀️" : "🌙";
    });
  }

  function setTheme(theme) {
    root.setAttribute("data-theme", theme);
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
    syncThemeMeta(theme);
  }

  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-theme-toggle]");
    if (!btn) return;
    setTheme(currentTheme() === "dark" ? "light" : "dark");
  });
  syncThemeMeta(currentTheme());

  /* ---------- الهيدر يتغيّر عند التمرير ---------- */
  var header = document.querySelector(".site-header");
  if (header) {
    var onScroll = function () {
      header.classList.toggle("is-scrolled", window.scrollY > 8);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---------- كشف العناصر عند التمرير (scroll reveal) ----------
     العناصر بكلاس .reveal تظهر عند دخولها الشاشة. بلا JS أو بلا حركة:
     تبقى ظاهرة (الحالة الأولية تُخفى فقط عند .js في CSS). */
  var revealables = document.querySelectorAll(".reveal");
  if (revealables.length && "IntersectionObserver" in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-in");
          obs.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    revealables.forEach(function (el, i) {
      // تدرّج بسيط للعناصر المتجاورة (stagger)
      var group = el.closest("[data-reveal-group]");
      if (group) el.style.setProperty("--reveal-delay", (i % 8) * 60 + "ms");
      io.observe(el);
    });
  } else {
    revealables.forEach(function (el) { el.classList.add("is-in"); });
  }

  /* ---------- ميلان البطاقات مع المؤشّر (tilt) ----------
     على أجهزة المؤشّر الدقيق فقط، وبلا reduced-motion. لمسة خفيفة جداً. */
  if (finePointer && !reduceMotion) {
    document.querySelectorAll("[data-tilt]").forEach(function (card) {
      var max = 5; // درجة
      card.addEventListener("pointermove", function (e) {
        var r = card.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5;
        var py = (e.clientY - r.top) / r.height - 0.5;
        card.style.setProperty("--tilt-x", (-py * max).toFixed(2) + "deg");
        card.style.setProperty("--tilt-y", (px * max).toFixed(2) + "deg");
      });
      card.addEventListener("pointerleave", function () {
        card.style.setProperty("--tilt-x", "0deg");
        card.style.setProperty("--tilt-y", "0deg");
      });
    });
  }

  /* ---------- عدّادات متحرّكة (count up) ----------
     عناصر [data-count] تعدّ من 0 لقيمتها عند ظهورها. */
  function animateCount(el) {
    var target = parseFloat(el.getAttribute("data-count")) || 0;
    var suffix = el.getAttribute("data-count-suffix") || "";
    if (reduceMotion) { el.textContent = target.toLocaleString() + suffix; return; }
    var start = performance.now(), dur = 1100;
    function step(now) {
      var t = Math.min((now - start) / dur, 1);
      var eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.round(target * eased).toLocaleString() + suffix;
      if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  var counters = document.querySelectorAll("[data-count]");
  if (counters.length && "IntersectionObserver" in window) {
    var co = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { animateCount(entry.target); obs.unobserve(entry.target); }
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { co.observe(el); });
  } else {
    counters.forEach(animateCount);
  }

  /* ---------- PWA: تسجيل عامل الخدمة ---------- */
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js");
  }

  /* ---------- اقتراحات البحث: إغلاق عند النقر خارجاً أو Escape ---------- */
  document.addEventListener("DOMContentLoaded", function () {
    var box = document.getElementById("search-suggest");
    if (!box) return;
    document.addEventListener("click", function (event) {
      if (!event.target.closest(".searchbar")) box.innerHTML = "";
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") box.innerHTML = "";
    });
  });
})();
