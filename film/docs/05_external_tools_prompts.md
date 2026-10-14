# ملفات الإنتاج للأدوات غير المتصلة (Runway / Kling / Higgsfield / Blender / Canva / CapCut–DaVinci)

الفيلم الحالي (`out/makhbaz_al_taqa_carbohydrates_1080p.mp4`) **مكتمل وقابل للتشغيل**، وأُنتج بأسلوب Motion Graphics سينمائي (حركات كاميرا 2.5D على لوحات المود بورد + رسوم كيميائية متحركة دقيقة). هذه الملفات تسمح بترقية لقطات محددة إلى فيديو مولَّد بالذكاء الاصطناعي أو 3D حقيقي، **مع الإبقاء على الرسوم الكيميائية من هذا المشروع** (لا تُولَّد الرسوم الكيميائية بالنص).

---

## 1) Runway Gen-4 / Kling 2.x / Higgsfield – Image-to-Video

**القاعدة:** استخدم الصورة المرجعية المعتمدة (`assets/plates/chef_hero.png` أو اللوحة المذكورة) كإطار أول (Start frame)، مدة 5–10 ث، 16:9، 1080p، حركة هادئة. أضف برومبت الشخصية الثابت من `01_character_reference.md` في كل لقطة فيها الشيف.

> ⚠️ لا تستخدم الصورة الحقيقية للشيف رقية في Image-to-Video أو مزامنة الشفاه قبل الحصول على موافقتها المكتوبة.

| لقطة | Start frame | البرومبت (إنجليزي للأداة) | يحل محل |
|---|---|---|---|
| 1A Drone | `fort_wide` | `Slow cinematic drone push-in toward a historic Omani mud-brick fort at sunrise, golden light, palm trees swaying gently, Omani flag waving, dust particles in the air. Smooth, steady, no cuts.` | المشهد 1: 0–9.5 ث |
| 1B Gate | `castle` | `Slow dolly-in to a massive carved wooden fortress gate; the gate slowly swings open and warm golden light spills out; subtle dust; cinematic, steady camera.` | 9.5–14.5 ث |
| 1C Souq | `env_souq` | `Gentle tracking shot moving through a quiet traditional Omani souq in the morning, copper lanterns, baskets of dates and grain, warm light, few blurred background people, steady gimbal.` | 14.5–17 ث |
| 1D Chef | `chef_hero` | `[character prompt] The chef smiles warmly at camera and gestures welcomingly toward a basket of fresh Omani bread; oven fire flickers behind her; slow push-in; natural, calm motion; keep face identical.` | 19.8–33.8 ث |
| 3A Date zoom | `b_ingred` | `Macro push-in into a glossy Omani date on a wooden table, the camera dives inside it as warm light blooms into a dark glowing particle space.` | المشهد 3: نهاية لقطة التمر |
| 9A Store | `b_tools` | `Slow dolly-in into a traditional Omani bakery storeroom: woven palm baskets, clay jars, flour sacks, warm lantern light.` | المشهد 9 |
| 12A Basket | `b_tools` | `Close-up of a woven Omani palm-frond basket, camera slowly pushes into the weave fibres (macro), shallow depth of field.` | المشهد 12 (البداية) |
| 12B Pull-back | `b_tools` | `Reverse of 12A: from macro fibres pulling back to reveal the full basket on the bakery table.` | المشهد 12 (النهاية) |
| 14A Ending | `chef_hero` | `[character prompt] The chef stands proudly behind bread, dates and a palm basket, smiles and nods; slow cinematic pull-back revealing the bakery.` | المشهد 14 |

**مزامنة الشفاه (اختياري):** Higgsfield / Kling Lip-Sync / Runway Act-One باستخدام ملفات `audio/vo/s01_02.mp3`، `s14_01.mp3`، `s14_03.mp3`… — فقط بعد الموافقة إذا كانت الصورة المستخدمة للشخص الحقيقي. مع الشخصية المرسومة لا يلزم إذن إضافي.

---

## 2) Blender – نماذج جزيئية ثلاثية الأبعاد (مواصفات دقيقة)

**أساس الإحداثيات:** استورد الهياكل ثلاثية الأبعاد من PubChem (تبويب *3D Conformer* → تنزيل SDF) بالبحث بالاسم الإنجليزي الدقيق أدناه، ولا تُرسم الذرات يدويًا. (لم أتمكن من الوصول إلى PubChem من بيئة العمل للتحقق من أرقام CID، لذا أدرجت الأسماء فقط.)

| الجزيء | اسم البحث في PubChem | ملاحظة للتحقق |
|---|---|---|
| ألفا جلوكوز | alpha-D-glucopyranose | OH على C1 في الاتجاه المعاكس لـ CH₂OH (لأسفل في هاورث) |
| بيتا جلوكوز | beta-D-glucopyranose | OH على C1 في نفس جهة CH₂OH (لأعلى) |
| الجلوكوز الخطي | aldehydo-D-glucose | C1 مجموعة ألدهيد |
| الفركتوز | beta-D-fructofuranose | حلقة خماسية |
| الجالاكتوز | beta-D-galactopyranose | يختلف عن الجلوكوز عند C4 فقط |
| المالتوز | maltose | α(1→4) |
| السكروز | sucrose | α(1→2)β |
| اللاكتوز | lactose | β(1→4) |
| جليسرالدهيد | D-glyceraldehyde | 3C |
| إريثروز | D-erythrose | 4C |
| ريبوز | D-ribose | 5C |

**الإضافات:** Blender + add-on **Molecular Nodes** (يقرأ SDF/PDB مباشرة). للنشا والجلايكوجين والسليلوز: ابنِ السلاسل من وحدة الجلوكوز المستوردة عبر Geometry Nodes (Instances on points) أو استورد نماذج من GLYCAM-Web (Carbohydrate Builder) وصدّرها PDB:
- **الأميلوز:** `DGlcpa1-4DGlcpa1-4…` (20–30 وحدة) – حلزون (~6 وحدات/لفة).
- **الأميلوبكتين:** سلاسل α(1→4) مع تفرع α(1→6) كل ~24–30 وحدة.
- **الجلايكوجين:** تفرع α(1→6) كل ~8–12 وحدة.
- **السليلوز:** `DGlcpb1-4DGlcpb1-4…`، 4–6 سلاسل متوازية، وروابط هيدروجينية بين السلاسل (مثل O6–H…O3 بين سلسلتين متجاورتين)، إضافة إلى روابط هيدروجينية داخل السلسلة نفسها (O3–H…O5) تزيدها استقامة.

**المواد (Materials):** C = رمادي داكن `#46464A`، O = أحمر `#E23C3C`، H = أبيض `#FAFAFA`؛ Ball-and-stick (نصف قطر الذرة 0.3 Å × مقياس، الروابط 0.12). لون إضافي فقط لـ: مجموعات OH المعنية (هالة سماوية `#78E6FF`)، الروابط الجلايكوسيدية (ذهبي `#D9A441`)، الروابط الهيدروجينية (سماوي متقطع).

**الكاميرا:** Orbit بطيء 20–30° خلال 8 ث، Macro zoom بعدسة 85mm، Depth of field خفيف، خلفية بنفسجية داكنة متدرجة مطابقة لـ `molecular_bg` في `tools/lib.py`. Render: Eevee، 1920×1080، 25fps، PNG sequence مع Alpha.

**تحقق:** قبل التصدير قارن كل نموذج بالرسم ثنائي الأبعاد في الفيلم (اتجاه OH على C1، رقم ذرات الكربون في الرابطة).

---

## 3) Canva – عناصر التصميم

العناصر نفسها مُنفّذة داخل الفيلم برمجيًا بنفس الثيم (لوحات خشبية بحروف ذهبية، بطاقات كريمية بشريط زخرفة عُمانية، شرائح زجاجية داكنة بإطار ذهبي). لإعادة إنشائها في Canva:

| العنصر | المواصفات |
|---|---|
| شارة الافتتاح | لوحة خشبية بنية متدرجة `#844F2E → #54301C`، إطار ذهبي 4px، نص «مخبز الطاقة» Reem Kufi Bold ذهبي `#F0CD78` |
| العناوين الفرعية | Reem Kufi Medium، كريمي `#FBF3E4` بظل خفيف |
| بطاقات الشرح | كريمي 93% شفافية، إطار ذهبي، شريط زخرفة عُمانية (معينات حمراء/خضراء/ذهبية) أعلاها |
| الجداول | خلفية داكنة 86%، عناوين الصفوف ذهبية Noto Naskh Bold 40، الخلايا كريمي 38 |
| بطاقة النهاية | «مخبز الطاقة – مدينة الحياة» + «إعداد: أ. إمتثال العطابي» بخط Amiri Bold |

---

## 4) CapCut / DaVinci Resolve – التجميع وإعادة التحرير

جميع الملفات جاهزة للتجميع دون إعادة توليد:
1. `out/scenes/scene01.mp4 … scene14.mp4` – مشاهد نظيفة (بدون ترجمة/توقيع) بالترتيب.
2. `out/audio/mix_final.m4a` – المزيج النهائي (تعليق + مؤثرات + موسيقى)، أو `audio/vo/*.mp3` لكل سطر، و`out/timeline.json` يعطي وقت بداية كل سطر بالثانية.
3. `out/makhbaz_al_taqa_ar.srt` – الترجمة العربية.
4. `out/signature.png` – طبقة التوقيع: ضعها في مسار مستقل أعلى كل المسارات، أسفل يمين الشاشة (x = 1920 − عرض الصورة − 44، y = 1080 − ارتفاعها − 22)، طوال الفيلم، دون حركة.
5. التصدير: H.264، 1080p أو 4K (Upscale)، 25fps، صوت AAC 192kbps، Loudness −16 LUFS.
