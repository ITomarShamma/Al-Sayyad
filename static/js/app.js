/* الصَّيَّاد — سلوكيات صغيرة لا تغطيها HTMX.
   نبقيه بأصغر حجم ممكن: كل التفاعل الأساسي بالسيرفر (HTMX). */

document.addEventListener("DOMContentLoaded", function () {
  var box = document.getElementById("search-suggest");
  if (!box) return;

  // أغلق الاقتراحات عند النقر خارج شريط البحث
  document.addEventListener("click", function (event) {
    if (!event.target.closest(".searchbar")) box.innerHTML = "";
  });

  // Escape تغلق الاقتراحات وترجع التركيز للحقل
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") box.innerHTML = "";
  });
});
