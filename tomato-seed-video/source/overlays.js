// Renders transparent 1920x1080 PNG text overlays with proper Arabic shaping.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const DIR = __dirname;
const OUT = path.join(DIR, 'ov');
fs.mkdirSync(OUT, { recursive: true });
const F = (n) => 'data:font/woff2;base64,' + fs.readFileSync(path.join(DIR, 'fonts', n)).toString('base64');

const fonts = `
@font-face{font-family:Ruqaa;src:url(${F('x_fontsource-amiri-5.3.0/files/amiri-arabic-700-normal.woff2')});}
@font-face{font-family:Taj;font-weight:800;src:url(${F('x_fontsource-tajawal-5.3.0/files/tajawal-arabic-800-normal.woff2')});}
@font-face{font-family:Taj;font-weight:700;src:url(${F('x_fontsource-tajawal-5.3.0/files/tajawal-arabic-700-normal.woff2')});}
@font-face{font-family:Kufi;font-weight:700;src:url(${F('x_fontsource-reem-kufi-5.3.0/files/reem-kufi-arabic-700-normal.woff2')});}
`;

const leaf = (size, fill = '#7cc36a', vein = '#2f6b2a') => `
<svg width="${size}" height="${size}" viewBox="0 0 64 64" style="vertical-align:middle">
  <path d="M8 56 C8 28 28 8 58 6 C56 36 36 56 8 56 Z" fill="${fill}"/>
  <path d="M10 54 C24 40 38 26 54 10" stroke="${vein}" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M24 40 L22 28 M32 32 L32 20 M40 24 L42 14 M24 40 L36 42 M32 32 L44 34" stroke="${vein}" stroke-width="2" fill="none" stroke-linecap="round" opacity=".7"/>
</svg>`;

const base = `*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;background:transparent;overflow:hidden}
body{position:relative;direction:rtl}
.abs{position:absolute}
.pill{font-family:Taj;font-weight:800;color:#fff;background:rgba(22,70,38,.78);
  border:3px solid rgba(255,236,170,.85);border-radius:999px;padding:14px 44px 10px;
  box-shadow:0 8px 30px rgba(0,0,0,.35);white-space:nowrap}
.title{font-family:Kufi;font-weight:700;color:#fff;font-size:92px;line-height:1.2;
  background:linear-gradient(180deg,rgba(46,125,50,.92),rgba(27,94,32,.92));
  border:4px solid #ffe08a;border-radius:36px;padding:10px 60px 18px;
  box-shadow:0 12px 40px rgba(0,0,0,.4);white-space:nowrap}
.label{font-family:Taj;font-weight:800;font-size:44px;color:#1b4d24;background:#fffbe8;
  border:3px solid #7cb342;border-radius:22px;padding:8px 28px 4px;box-shadow:0 6px 18px rgba(0,0,0,.3);white-space:nowrap}
.center{left:50%;transform:translateX(-50%)}
`;

function at(x, y, inner, cls = '', extra = '') {
  return `<div class="abs ${cls}" style="left:${x}px;top:${y}px;transform:translate(-50%,-50%);${extra}">${inner}</div>`;
}

const ov = {};
// Persistent small signature, bottom-right corner
ov.sig_small = `<div class="abs" style="right:40px;bottom:26px;display:flex;align-items:center;gap:10px;direction:rtl;
  font-family:Ruqaa;font-size:40px;color:#fff;text-shadow:0 2px 6px rgba(0,0,0,.75),0 0 2px rgba(0,0,0,.6)">
  ${leaf(40)}<span>أ. إمتثال العطابي</span></div>`;

// Scene 7
ov.s7_question = at(960, 120, 'هل تعيش جميع النباتات المدة نفسها؟', 'pill', 'font-size:60px');
const q = 'font-family:Kufi;font-weight:700;font-size:150px;color:#fff;width:190px;height:190px;line-height:190px;text-align:center;border-radius:50%;background:rgba(22,70,38,.72);border:5px solid #ffe08a;box-shadow:0 10px 30px rgba(0,0,0,.4)';
ov.s7_split = `
<div class="abs" style="left:1078px;top:200px;width:6px;height:760px;border-radius:3px;
  background:repeating-linear-gradient(180deg,rgba(255,236,170,.95) 0 28px,transparent 28px 46px);
  box-shadow:0 0 14px rgba(255,220,120,.8)"></div>
${at(560, 330, '؟', '', q)}${at(1500, 330, '؟', '', q)}`;

// Radish captions (bottom center)
const cap = (t) => at(960, 930, t, 'pill', 'font-size:52px');
ov.r_c1 = cap('بذرة');
ov.r_c2 = cap('تنبت وتنمو');
ov.r_c3 = cap('يصبح نباتًا ناضجًا');
ov.r_c4 = cap('يُزهر ويُنتج بذورًا جديدة');
ov.r_c5 = cap('يموت النبات بعد اكتمال دورة حياته');
ov.r_badge = `<div class="abs pill" style="left:60px;top:48px;font-size:40px;padding:12px 34px 8px">⏳ عامٌ واحد</div>`;
ov.annual_title = at(960, 120, 'النباتات الحولية', 'title');
ov.ex_radish = at(669, 930, 'الفجل', 'label');
ov.ex_onion = at(960, 930, 'البصل', 'label');
ov.ex_garlic = at(1245, 930, 'الثوم', 'label');

// Mango captions
ov.m_c1 = cap('تنمو الشجرة');
ov.m_c2 = cap('تظهر الأزهار');
ov.m_c3 = cap('تتكوّن الثمار');
ov.m_c4 = cap('تُقطف الثمار… وتبقى الشجرة حيّة');
ov.m_c5 = cap('تُزهر وتُثمر مجددًا في موسم لاحق');
const ar = (n) => String(n).replace(/\d/g, (d) => '٠١٢٣٤٥٦٧٨٩'[d]);
for (const y of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]) {
  ov['year_' + y] = `<div class="abs pill" style="left:60px;top:48px;font-size:44px;padding:12px 34px 8px">السنة ${ar(y)}</div>`;
}
ov.perennial_title = at(960, 120, 'النباتات المعمرة', 'title');
ov.ex_mango = at(608, 840, 'المانجو', 'label');
ov.ex_lemon = at(1248, 840, 'الليمون', 'label');
ov.ex_palm = at(1640, 840, 'النخيل', 'label');

// Scene 10
ov.ch_title = at(960, 470, `${leaf(90)} تحدّي عالمة النباتات ${leaf(90)}`, 'title', 'font-size:110px;padding:20px 70px 30px');
ov.ch_q1 = at(960, 150, 'هل يمكنكِ تسمية المراحل الست لدورة حياة نبات الطماطم بالترتيب؟', 'pill', 'font-size:46px;white-space:normal;width:1700px;text-align:center;border-radius:40px;line-height:1.5');
ov.ch_q2 = at(960, 150, 'أيّ هذه النباتات حولي، وأيّها معمر؟', 'pill', 'font-size:58px');
// plant names (RTL order: first item on the right)
const names = ['الفجل', 'النخيل', 'الثوم', 'المانجو', 'البصل', 'الليمون'];
names.forEach((n, i) => {
  const x = 1920 - (175 + i * 314);
  ov['pn_' + i] = at(x, 720, n, 'label', 'font-size:40px');
});

// Ending
ov.end_phrase = at(960, 250, 'كل بذرة تحمل بداية حكاية جديدة!', '', 'font-family:Ruqaa;font-size:112px;color:#fff;white-space:nowrap;text-shadow:0 4px 18px rgba(0,0,0,.65),0 0 40px rgba(255,200,90,.55)');
ov.end_sig = at(960, 430, `${leaf(64)}<span style="margin-right:14px">إعداد وتصميم: أ. إمتثال العطابي</span>`, '', 'display:flex;align-items:center;font-family:Ruqaa;font-size:66px;color:#fff;white-space:nowrap;text-shadow:0 3px 12px rgba(0,0,0,.7)');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const only = process.argv.slice(2);
  for (const [name, html] of Object.entries(ov)) {
    if (only.length && !only.includes(name)) continue;
    await page.setContent(`<!doctype html><html lang="ar"><head><meta charset="utf-8"><style>${fonts}${base}</style></head><body>${html}</body></html>`);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(OUT, name + '.png'), omitBackground: true });
  }
  await browser.close();
  console.log('rendered', Object.keys(ov).length);
})();
