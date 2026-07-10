// ملف تعريفي بمتجر الصَّيَّاد — مُقدَّم لشركة شام كاش لطلب واجهة الدفع البرمجية.
// عربي RTL بالكامل، بألوان هوية الصَّيَّاد (Deep Sea / Tide / Catch Gold).
const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, BorderStyle, WidthType, ShadingType,
  Footer, PageNumber, HeadingLevel,
} = require("docx");

const DEEP_SEA = "0B4A41";
const TIDE = "0E6B5E";
const GOLD = "D99A2B";
const SEA_FOAM = "E4F1ED";
const INK = "16261F";
const SLATE = "5B6B64";
const LINE = "E6E1D3";

// كل النصوص عربية → كل فقرة bidirectional وكل run rightToLeft
const rtl = (opts) => ({ bidirectional: true, ...opts });
const t = (text, opts = {}) => new TextRun({ text, rightToLeft: true, ...opts });

const body = (text, opts = {}) =>
  new Paragraph(rtl({ spacing: { after: 160 }, ...opts, children: [t(text, opts.run)] }));

const heading = (text) =>
  new Paragraph(rtl({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 160 },
    keepNext: true,        // العنوان لا ينفصل عن أول سطر بعده عند نهاية الصفحة
    children: [t(text, { bold: true, color: DEEP_SEA })],
  }));

const bullet = (strong, rest) =>
  new Paragraph(rtl({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 100 },
    children: rest === undefined
      ? [t(strong)]
      : [t(strong + ": ", { bold: true, color: DEEP_SEA }), t(rest)],
  }));

const numbered = (text) =>
  new Paragraph(rtl({
    numbering: { reference: "requests", level: 0 },
    spacing: { after: 100 },
    children: [t(text)],
  }));

// جدول «أرقام سريعة»: عمود عنوان مظلَّل + عمود قيمة
const border = { style: BorderStyle.SINGLE, size: 1, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
const CONTENT_W = 9026;              // A4 بهامش 1 إنش
const factRow = (label, value) =>
  new TableRow({
    children: [
      new TableCell({
        borders, width: { size: 6326, type: WidthType.DXA },
        margins: { top: 100, bottom: 100, left: 160, right: 160 },
        children: [new Paragraph(rtl({ children: [t(value)] }))],
      }),
      new TableCell({
        borders, width: { size: 2700, type: WidthType.DXA },
        shading: { fill: SEA_FOAM, type: ShadingType.CLEAR },
        margins: { top: 100, bottom: 100, left: 160, right: 160 },
        children: [new Paragraph(rtl({ children: [t(label, { bold: true, color: DEEP_SEA })] }))],
      }),
    ],
  });

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Segoe UI", size: 22, color: INK } } }, // 11pt
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal",
        run: { size: 28, bold: true, font: "Segoe UI", color: DEEP_SEA },
        paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 0 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 620, hanging: 300 } } } }] },
      { reference: "requests",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 620, hanging: 300 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },          // A4
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph(rtl({
          alignment: AlignmentType.CENTER,
          border: { top: { style: BorderStyle.SINGLE, size: 4, color: LINE, space: 6 } },
          children: [
            t("الصَّيَّاد — سوقك السوري الموثوق   ·   صفحة ", { size: 18, color: SLATE }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, color: SLATE, rightToLeft: true }),
          ],
        }))],
      }),
    },
    children: [
      // ——— الترويسة ———
      new Paragraph(rtl({
        alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [t("متجر الصَّيَّاد", { bold: true, size: 52, color: DEEP_SEA })],
      })),
      new Paragraph(rtl({
        alignment: AlignmentType.CENTER, spacing: { after: 60 },
        children: [t("سوق إلكتروني سوري — عربي أولاً", { size: 26, color: TIDE })],
      })),
      new Paragraph(rtl({
        alignment: AlignmentType.CENTER, spacing: { after: 360 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: GOLD, space: 10 } },
        children: [t("ملف تعريفي مُقدَّم إلى شركة «شام كاش» — طلب واجهة الدفع البرمجية (Payment API)",
                     { size: 20, color: SLATE })],
      })),

      // ——— 1. المشروع باختصار ———
      heading("المشروع باختصار"),
      body("«الصَّيَّاد» متجر إلكتروني سوري يجمع تنوّع المتاجر الكبرى في مكان واحد: " +
           "إلكترونيات وأدوات منزلية وكل ما يحتاجه البيت، مع توصيل يغطي المحافظات السورية كافة. " +
           "بُني المتجر من أول سطر ليناسب زبوناً يشتري أونلاين لأول مرة: واجهة عربية بالكامل، " +
           "كل شاشة بمهمة واحدة واضحة، وطلب بلا أي حساب إجباري — رقم الموبايل يكفي."),
      body("نعمل اليوم بنظام الدفع عند الاستلام، والمنصة جاهزة برمجياً منذ تصميمها لإضافة " +
           "«شام كاش» كطريقة دفع إلكترونية أولى — ما ينقصنا هو واجهة الدفع البرمجية الخاصة بكم."),

      // ——— 2. أرقام سريعة ———
      heading("لمحة سريعة"),
      new Table({
        visuallyRightToLeft: true,
        width: { size: CONTENT_W, type: WidthType.DXA },
        columnWidths: [6326, 2700],
        rows: [
          factRow("الحالة", "نسخة كاملة جاهزة للإطلاق — تُعرض مباشرةً عند الطلب"),
          factRow("التغطية", "المحافظات السورية الـ14، برسوم توصيل لكل محافظة"),
          factRow("اللغات", "العربية أولاً + الإنجليزية بالكامل"),
          factRow("الدفع الحالي", "عند الاستلام (COD) — وشام كاش هي الخطوة التالية"),
          factRow("نموذج العمل", "سوق مفتوح: بضاعتنا + تجّار معتمدون يبيعون عبر المنصة"),
        ],
      }),
      new Paragraph(rtl({ spacing: { after: 60 }, children: [] })),

      // ——— 3. ماذا يقدّم المتجر ———
      heading("ماذا يقدّم المتجر؟"),
      bullet("كاتالوج متنوّع", "تصنيفات شجرية، صور محسَّنة، تخفيضات، وبحث عربي ذكي يفهم اختلاف أشكال الكتابة"),
      bullet("شراء بلا حواجز", "سلة وإتمام طلب بلا تسجيل — ثم حساب اختياري يحفظ البيانات والطلبات"),
      bullet("تتبع واضح", "رقم طلب قصير يتتبعه الزبون بخط زمني لحالة طلبه حتى باب البيت"),
      bullet("نظام تجّار", "انضمام بموافقة الإدارة، وكل تاجر يدير منتجاته فقط ضمن لوحة تحكم معرَّبة"),
      bullet("أدوات بيع", "كوبونات خصم، تقييمات من مشترين موثَّقين، وإشعارات فورية للإدارة مع كل طلب"),

      // ——— 4. لمن المتجر ———
      heading("لمن هذا المتجر؟"),
      body("للأسر والأفراد داخل سوريا الباحثين عن تجربة شراء أونلاين آمنة وبسيطة بلغتهم، " +
           "وللتجّار أصحاب البضائع الراغبين بالبيع الإلكتروني دون كلفة بناء متجر خاص بهم — " +
           "فكل تاجر معتمد يعرض بضاعته عبر منصتنا ونتكفّل نحن بالواجهة والطلبات."),

      // ——— 5. الجاهزية التقنية ———
      heading("جاهزيتنا لدمج شام كاش"),
      bullet("نقطة دمج جاهزة", "بوابة الدفع معزولة في المنصة وتُفعَّل فور استلام وثائق الواجهة البرمجية"),
      bullet("موثوقية مالية", "كل عملية شراء معاملة واحدة غير قابلة للتجزئة، والفواتير تحفظ الأسعار لحظة الشراء ولا تتغيّر"),
      bullet("أمان", "حماية الحسابات من التخمين، نسخ احتياطي آلي، وتشغيل عبر HTTPS عند الإطلاق"),
      bullet("سرعة تنفيذ", "الدمج والتجربة خلال أيام من استلام الوثائق وبيئة الاختبار"),

      // ——— 6. ما نطلبه ———
      heading("ما نطلبه من شام كاش"),
      numbered("وثائق واجهة الدفع البرمجية (Payment API) وآلية تأكيد العمليات"),
      numbered("بيانات بيئة اختبار (Sandbox) لإجراء عمليات دفع تجريبية قبل الإطلاق"),
      numbered("الهوية البصرية الرسمية لعرض خيار «ادفع بشام كاش» بالشكل الصحيح"),

      // ——— 7. التواصل ———
      heading("معلومات التواصل"),
      bullet("الاسم", "عمر محمد نور شمه"),
      bullet("الهاتف / واتساب", "0998625984"),
      bullet("البريد الإلكتروني", "tahashamma222@gmail.com"),
      body("نسعد بعرض المتجر مباشرةً على فريقكم وبأي استفسار تقني حول الدمج.",
           { run: { color: SLATE } }),
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("output.docx", buffer);
  console.log("written output.docx", buffer.length, "bytes");
});
