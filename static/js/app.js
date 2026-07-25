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

  /* ---------- اختيار المقاس/اللون (تحسين لصفحة المنتج) ----------
     بدون هذا السكربت الصفحة تعمل بالكامل: الأزرار حقول radio داخل النموذج،
     والسيرفر يحسم التركيبة ويرفض غير المتوفر برسالة. هنا نضيف فقط:
     السعر الحيّ، وسطر التوفّر، وتعطيل التركيبات المستحيلة قبل الضغط. */
  document.querySelectorAll("[data-variant-map]").forEach(function (form) {
    var variants;
    try {
      variants = JSON.parse(form.dataset.variantMap || "[]");
    } catch (e) {
      return;                       // بيانات غير صالحة: نترك السلوك الأساسي
    }
    var priceEl = document.querySelector("[data-price]");
    var fromEl = document.querySelector(".buybox__from");
    var note = form.querySelector("[data-stock-note]");
    var button = form.querySelector("[data-buy-button]");
    var groups = Array.prototype.slice.call(form.querySelectorAll(".variant-group"));

    function chosenIds() {
      return Array.prototype.map.call(
        form.querySelectorAll('input[type="radio"]:checked'),
        function (r) { return parseInt(r.value, 10); });
    }

    function findVariant(ids) {
      for (var i = 0; i < variants.length; i++) {
        var v = variants[i];
        if (v.values.length !== ids.length) continue;
        var all = v.values.every(function (x) { return ids.indexOf(x) !== -1; });
        if (all) return v;
      }
      return null;
    }

    /* يعطّل القيم التي لا تشكّل مع الاختيار الحالي أي تركيبة متوفرة */
    function refreshAvailability() {
      groups.forEach(function (group, gi) {
        var others = [];
        groups.forEach(function (other, i) {
          if (i === gi) return;
          var picked = other.querySelector('input[type="radio"]:checked');
          if (picked) others.push(parseInt(picked.value, 10));
        });
        group.querySelectorAll('input[type="radio"]').forEach(function (radio) {
          var wrap = radio.closest(".variant-option");
          if (wrap.classList.contains("is-sold-out")) return;   // حسمه السيرفر
          var id = parseInt(radio.value, 10);
          var ok = variants.some(function (v) {
            return v.stock > 0 && v.values.indexOf(id) !== -1 &&
              others.every(function (o) { return v.values.indexOf(o) !== -1; });
          });
          radio.disabled = !ok;
          wrap.classList.toggle("is-unavailable", !ok);
        });
      });
    }

    /* العربية تميّز المفرد والمثنى: «قطعة وحدة» / «قطعتين» / «3 قطع» */
    function lowStockText(stock) {
      if (stock > 5) return note.dataset.okText;
      if (stock === 1) return note.dataset.oneText;
      if (stock === 2) return note.dataset.twoText;
      return note.dataset.lowText.replace("{n}", stock);
    }

    function update() {
      // اسم القيمة المختارة بجانب عنوان المجموعة («المقاس: L»)
      form.querySelectorAll("[data-chosen]").forEach(function (el) {
        var picked = form.querySelector(
          'input[name="option_' + el.dataset.chosen + '"]:checked');
        el.textContent = picked
          ? picked.closest(".variant-option").textContent.trim() : "";
      });

      refreshAvailability();

      var ids = chosenIds();
      if (ids.length < groups.length) {          // لسا ما اكتمل الاختيار
        if (note) {
          note.textContent = note.dataset.promptText || note.textContent;
          note.className = "variant-note caption";
        }
        return;
      }

      var variant = findVariant(ids);
      if (priceEl && variant) {
        priceEl.textContent = variant.price;
        if (fromEl) fromEl.hidden = true;        // صار السعر محدداً لا «يبدأ من»
      }
      if (!note) return;
      if (!variant || variant.stock <= 0) {
        note.textContent = note.dataset.soldText;
        note.className = "variant-note caption variant-note--out";
        if (button) button.disabled = true;
      } else {
        note.textContent = lowStockText(variant.stock);
        note.className = "variant-note caption variant-note--ok";
        if (button) button.disabled = false;
      }
    }

    if (note) note.dataset.promptText = note.textContent.trim();
    form.querySelectorAll('input[type="radio"]').forEach(function (radio) {
      radio.addEventListener("change", update);
    });
    update();
  });

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
