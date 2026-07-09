/* الصَّيَّاد — عامل الخدمة (Service Worker).

   وظيفته متعمَّدة الصِّغَر: صفحة «ما في اتصال» عند انقطاع النت، لا أكثر.
   لا نخزّن صفحات المتجر ولا المنتجات — الأسعار والمخزون يتغيّران،
   وبيانات قديمة تُعرض بثقة أخطر من رسالة انقطاع صريحة.

   يُقدَّم من الجذر (/sw.js) عبر view خاص: لو قُدِّم من /static/ لكان
   نطاقه /static/ فقط ولا يغطي صفحات الموقع. */

const CACHE = "sayyad-v1";           /* غيّر الرقم عند تعديل هذا الملف */
const OFFLINE_URL = "/offline/";

/* التنصيب: خزّن صفحة الانقطاع (مكتفية بذاتها — بلا CSS خارجي) */
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.add(OFFLINE_URL))
      .then(() => self.skipWaiting())
  );
});

/* التفعيل: احذف كاشات الإصدارات القديمة وتولَّ الصفحات المفتوحة */
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))
      ))
      .then(() => self.clients.claim())
  );
});

/* التصفح فقط (mode navigate): جرّب الشبكة، وعند الفشل اعرض صفحة الانقطاع.
   طلبات HTMX والصور والأنماط تمرّ للشبكة مباشرة بلا تدخّل. */
self.addEventListener("fetch", (event) => {
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => caches.match(OFFLINE_URL))
    );
  }
});
