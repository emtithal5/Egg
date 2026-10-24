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
.title{font-family:Taj;font-weight:800;color:#fff;font-size:92px;line-height:1.2;
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
ov.sig_small = `<div class="abs" style="right:40px;bottom:26px;display:flex;align-items:center;gap:10px;direction:rtl;
  font-family:Ruqaa;font-size:40px;color:#fff;text-shadow:0 2px 6px rgba(0,0,0,.75),0 0 2px rgba(0,0,0,.6)">
  ${leaf(40)}<span>أ. إمتثال العطابي</span></div>`;

// Scene 1 title
ov.title = at(960, 150, `<div style="font-size:84px">رحلة بذرة طماطم</div><div style="font-family:Taj;font-weight:800;font-size:44px;color:#ffe08a;margin-top:4px">من بذرة إلى حياة جديدة</div>`, 'title', 'text-align:center;padding:14px 70px 22px');

// Scene 2 stage captions
const cap = (t) => at(960, 960, t, 'pill', 'font-size:54px');
ov.st1 = cap('١  البذرة');
ov.st2 = cap('٢  الإنبات');
ov.st3 = cap('٣  الشتلة');
ov.st4 = cap('٤  النبات الناضج');
ov.st5 = cap('٥  الإزهار والتلقيح والإخصاب');
ov.st6 = cap('٦  الثمرة والبذور الجديدة');
ov.lbl_radicle = at(1180, 860, '⬅ الجُذَير', 'label', 'font-size:40px');
ov.lbl_shoot = at(1180, 560, '⬅ البادرة', 'label', 'font-size:40px');
ov.lbl_ripen = at(960, 120, 'تنضج الثمرة: من الأخضر إلى الأحمر', 'pill', 'font-size:44px');
ov.lbl_seeds = at(960, 120, 'البذور الجديدة داخل الثمرة', 'pill', 'font-size:48px');

// Pollination / fertilization diagram (frame coordinates)
ov.flower = `<svg class="abs" style="left:0;top:0" width="1920" height="1080" viewBox="0 0 1920 1080">
  <rect x="480" y="150" width="960" height="800" rx="44" fill="#fffbea" fill-opacity=".96" stroke="#ffe08a" stroke-width="6"/>
  <path d="M960 935 L960 800" stroke="#689f38" stroke-width="16" stroke-linecap="round"/>
  <g fill="#7cb342" stroke="#558b2f" stroke-width="3">
    <polygon points="935,805 820,840 915,780"/><polygon points="985,805 1100,840 1005,780"/>
    <polygon points="950,812 880,880 930,790"/><polygon points="970,812 1040,880 990,790"/>
  </g>
  <g fill="#fdd835" stroke="#f9a825" stroke-width="3" stroke-linejoin="round">
    <path d="M905 690 Q760 700 690 760 Q760 790 900 722 Z"/><path d="M915 702 Q820 790 800 885 Q860 860 928 728 Z"/>
    <path d="M1015 690 Q1160 700 1230 760 Q1160 790 1020 722 Z"/><path d="M1005 702 Q1100 790 1120 885 Q1060 860 992 728 Z"/>
  </g>
  <ellipse cx="960" cy="745" rx="82" ry="64" fill="#9ccc65" stroke="#558b2f" stroke-width="4"/>
  <g fill="#fff8e1" stroke="#c8a400" stroke-width="3">
    <circle cx="928" cy="737" r="12"/><circle cx="960" cy="722" r="12"/><circle cx="992" cy="737" r="12"/>
    <circle cx="944" cy="768" r="12"/><circle cx="976" cy="768" r="12"/>
  </g>
  <path d="M960 690 L960 334" stroke="#aed581" stroke-width="14" stroke-linecap="round"/>
  <circle cx="960" cy="320" r="20" fill="#cddc39" stroke="#827717" stroke-width="4"/>
  <g fill="#fbc02d" stroke="#f57f17" stroke-width="3" stroke-linejoin="round">
    <polygon points="900,690 946,690 950,372 928,372"/><polygon points="1020,690 974,690 970,372 992,372"/>
  </g>
  <g stroke="#5d4037" stroke-width="3" stroke-dasharray="8 6">
    <line x1="984" y1="320" x2="1130" y2="320"/><line x1="1000" y1="470" x2="1130" y2="470"/><line x1="1046" y1="745" x2="1130" y2="745"/>
  </g>
  <g fill="none" stroke="#64b5f6" stroke-width="7" stroke-linecap="round" opacity=".9">
    <path d="M560 380 q40 -30 80 0 t80 0 t80 0"/><path d="M590 450 q35 -26 70 0 t70 0 t70 0"/><path d="M560 520 q40 -30 80 0 t80 0"/>
  </g>
</svg>
${at(1240, 320, 'المِيسم', 'label', 'font-size:36px')}
${at(1268, 470, 'المِتْك (حبوب اللقاح)', 'label', 'font-size:36px')}
${at(1262, 745, 'المبيض والبويضات', 'label', 'font-size:36px')}
${at(660, 600, 'الرياح تهزّ الزهرة', 'label', 'font-size:34px;color:#0d47a1;border-color:#64b5f6')}`;
ov.cap_poll = at(960, 92, 'التلقيح: انتقال حبوب اللقاح من المتك إلى الميسم', 'pill', 'font-size:44px');
ov.cap_fert = at(960, 92, 'الإخصاب: اتحاد حبة اللقاح بالبويضة لتتكوّن البذرة', 'pill', 'font-size:44px');

// Scene 3 circular diagram
ov.dg_center = `<div class="abs" style="left:960px;top:560px;transform:translate(-50%,-50%);width:330px;height:330px;border-radius:50%;
  background:radial-gradient(circle,#2e7d32,#1b5e20);border:6px solid #ffe08a;box-shadow:0 10px 40px rgba(0,0,0,.45);
  display:flex;align-items:center;justify-content:center;text-align:center;font-family:Taj;font-weight:800;color:#fff;font-size:42px;line-height:1.35">
  دورة حياة<br>نبات الطماطم</div>`;
const R = 330, CX = 960, CY = 560;
const names = ['البذرة', 'الإنبات', 'الشتلة', 'النبات الناضج', 'الإزهار والتلقيح', 'الثمرة والبذور'];
names.forEach((n, i) => {
  const a = (-90 + 60 * i) * Math.PI / 180;
  const x = Math.round(CX + R * Math.cos(a)), y = Math.round(CY + R * Math.sin(a));
  ov['dg_l' + i] = at(x, y + 112, n, 'label', 'font-size:34px;padding:4px 20px 0');
});

// Scene 4
ov.q_life = at(960, 120, 'هل تعيش جميع النباتات المدة نفسها؟', 'pill', 'font-size:60px');

// Scene 7 split + ending
ov.split_annual = at(1440, 900, 'نبات حولي: يموت بعد إنتاج البذور', 'pill', 'font-size:42px');
ov.split_perennial = at(480, 900, 'نبات معمر: يعيش ويُثمر من جديد', 'pill', 'font-size:42px');
ov.split_q = at(960, 110, 'هل تستطيعين التمييز بين النباتات الحولية والمعمرة؟', 'pill', 'font-size:48px');
ov.end_phrase = at(960, 250, 'كل بذرة تحمل بداية حكاية جديدة!', '', 'font-family:Ruqaa;font-size:112px;color:#fff;white-space:nowrap;text-shadow:0 4px 18px rgba(0,0,0,.65),0 0 40px rgba(255,200,90,.55)');
ov.end_sig = at(960, 430, `${leaf(64)}<span style="margin-right:14px">إعداد وتصميم: أ. إمتثال العطابي</span>`, '', 'display:flex;align-items:center;font-family:Ruqaa;font-size:66px;color:#fff;white-space:nowrap;text-shadow:0 3px 12px rgba(0,0,0,.7)');

// Annual / perennial (reused layout from scenes 7-10, Tajawal titles)
ov.annual_title = at(960, 120, 'النباتات الحولية', 'title');
ov.perennial_title = at(960, 120, 'النباتات المعمرة', 'title');
ov.ex_radish = at(669, 930, 'الفجل', 'label');
ov.ex_onion = at(960, 930, 'البصل', 'label');
ov.ex_garlic = at(1245, 930, 'الثوم', 'label');
ov.ex_mango = at(608, 840, 'المانجو', 'label');
ov.ex_lemon = at(1248, 840, 'الليمون', 'label');
ov.ex_palm = at(1640, 840, 'النخيل', 'label');
ov.r_badge = `<div class="abs pill" style="left:60px;top:48px;font-size:40px;padding:12px 34px 8px">⏳ عامٌ واحد</div>`;
const arn = (n) => String(n).replace(/\d/g, (d) => '٠١٢٣٤٥٦٧٨٩'[d]);
for (let y = 1; y <= 12; y++) ov['year_' + y] = `<div class="abs pill" style="left:60px;top:48px;font-size:44px;padding:12px 34px 8px">السنة ${arn(y)}</div>`;
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
