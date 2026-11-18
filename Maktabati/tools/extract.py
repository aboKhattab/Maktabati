# -*- coding: utf-8 -*-
"""استخراج بطاقات النصوص المنقولة من كتاب «الجامع في الخشوع».

الإدخال: نص الكتاب المصدَّر من وورد (حواشٍ بصيغة [^N]).
الإخراج: cards.json + تقرير إحصائي.
"""
import json, re, sys
from collections import Counter, defaultdict

SRC, OUT = sys.argv[1], sys.argv[2]
BODY_START, BODY_END = 189, 5708          # من «الفصل الأول» إلى ما قبل «الخاتمة شعرًا»
BOOK = "الجامع في الخشوع"

lines = open(SRC, encoding="utf-8").read().split("\n")

# ---------------------------------------------------------------- الحواشي
notes = {}
for ln in lines:
    m = re.match(r"^\[\^(\d+)\]:\s*\(\)\s*(.*)$", ln)
    if m:
        notes[int(m.group(1))] = m.group(2).strip()

# ---------------------------------------------------------------- تنظيف
QURAN_GLYPHS = re.compile("[\uFB50-\uFDF9\uFDFB-\uFDFF\uFE70-\uFEFF]+")

def clean(t):
    t = t.replace("**", "").replace("‌", "").replace("‏", "").replace("‎", "")
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()

def fix_quran(t):
    # {رموز خط المصحف} [السورة: الآية] ← ﴿آية: السورة الآية﴾
    t = re.sub(r"\{[^{}]*\}\s*\[([^\]]+)\]", lambda m: f"﴿الآية: {m.group(1).strip()}﴾", t)
    t = re.sub(r"\{[^{}]*\}", "﴿…﴾", t)
    t = QURAN_GLYPHS.sub("", t)
    return t

# ---------------------------------------------------------------- الصيغ
PROPHET_CTX = re.compile(r"(رسول الله|رسولُ الله|رسولِ الله|رسولَ الله|النبي|النبيُّ|النبيِّ|النبيَّ|نبي الله|نبيَّ الله|نبيُّ الله|محمد|محمدًا|محمدٍ|المصطفى|نبيه|نبيِّه|نبينا|سيد الخاشعين|الرسول|رسوله|خير الخلق|حِبِّي أبو القاسم|أبو القاسم)\s*$")
GOD_CTX = re.compile(r"(الله|اللهَ|اللهِ|اللهُ|لله|ربنا|ربُّنا|الرب|الربِّ|الرحمن|ربك|ربِّه|ربه|الباري|المولى|الخالق|ربي)\s*$")
ANBIYA = re.compile(r"(موسى|عيسى|إبراهيم|يوسف|زكريا|داود|آدم|جبريل|يحيى|نوح|هارون|سليمان|يعقوب|شعيب|إسماعيل|الخليل إبراهيم)\s*$")
FEMALE = re.compile(r"(عائشة|أسماء|فاطمة|حفصة|أم سلمة|ميمونة|خولة|أم أيمن|صفية|أسماء بنت أبي بكر)\s*$")
DUAL = re.compile(r"(ابن عمر|ابن عباس|ابن عمرو|عبد الله بن عمرو|ابن الزبير|عبد الله بن عمر|عبد الله بن الزبير|عبد الله بن عمرو بن العاص|عبيد الله بن عمر|ابن عمرَ)\s*$")
PLURAL_SAHABA = re.compile(r"(الصحابة|أصحابه|أصحاب رسول الله|صحابته|الصحابة الكرام|أصحاب محمد)\s*$")
PLURAL_SALAF = re.compile(r"(السلف|العلماء|أهل العلم|التابعين|بإحسان)\s*$")

SAHABA = """أبو بكر|أبي بكر|أبا بكر|الصديق|عمر|عمرَ|عمرُ|الفاروق|عثمان|عثمانُ|علي|عليٍّ|عليّ|عليًّا|ابن مسعود|عبد الله بن مسعود|عبدِ الله بن مسعود|أبو هريرة|أبي هريرة|أبو الدرداء|أبي الدرداء|أبو ذر|أبي ذر|أبي ذَرٍّ|أنس|أنس بن مالك|حذيفة|حذيفةُ|حذيفة بن اليمان|معاذ|معاذ بن جبل|سلمان|أبو موسى|أبي موسى|أبو موسى الأشعري|أبي موسى الأشعري|جابر|جابر بن عبد الله|جابر بن سمرة|عوف بن مالك|عوفِ بنِ مالك|شداد بن أوس|خباب|خَبَّاب بن الأرت|أبو أمامة|أبي أمامة|أبي أمامة الباهلي|أُبي|أبي بن كعب|عمرو بن العاص|معاوية|الزبير|عمار|عمار بن ياسر|عمَّار بن ياسر|تميم الداري|عقبة بن عامر|عمرو بن عبسة السلمي|سعد|سعد بن أبي وقاص|سعد بن عبادة|البراء|البراء بن عازب|أبو سعيد|أبي سعيد|أبي سعيد الخدري|أبو سعيد الخدري|عبد الرحمن بن عوف|زيد بن أرقم|زيد بن ثابت|أسامة|أسامة بن زيد|ثوبان|المقداد|أبو قتادة|أبي قتادة|عبد الله بن الشخير|العرباض|الْعِرْبَاض بْنِ سَارِيَةَ|معاوية بن الحكم السلمي|سهل بن سعد|عبد الرحمن بن شبل|أبي مسعود البدري|مُعَيْقِيبٍ|معيقيب|النعمان بن بشير|عبد الله بن عامر بن ربيعة|عبد الله بن السائب|قطبة بن مالك|أبي برزة|أبي برزة الأسلمي|عبد الله بن الأرقم|الحارث الأشعري|البياضي|الْبَيَاضِيِّ|عثمان بن أبي العاص|زياد بن لبيد|عبد الله بن حكيم|أبي عنبة الخولاني|سهل بن أبي حثمة|حارثة بن وهب الخزاعي|المقدام بن معدي كرب|عمرو|عبد الله بن عيسى""".split("|")
SAHABA_RE = re.compile(r"(" + "|".join(sorted(map(re.escape, SAHABA), key=len, reverse=True)) + r")\s*$")


def _n(t):
    t = re.sub(r"[\u064B-\u0652\u0670\u0640\u200c]", "", t)
    t = re.sub(r"[إأآ]", "ا", t)
    t = re.sub(r"\b(ابا|ابي)\b", "ابو", t)
    return t

SAHABA_N = sorted({_n(x) for x in SAHABA} | {_n(x) for x in ["عمر بن الخطاب","عثمان بن عفان","علي بن أبي طالب","أبو بكر الصديق","سعد بن معاذ","أسيد بن حضير","الطفيل بن عمرو","جبير بن مطعم","عبد الله بن الزبير","الزبير بن العوام","جعفر بن أبي طالب","سلمان الفارسي","مصعب بن عمير","حمزة","عبادة بن الصامت","أسعد بن زرارة","أبو حذيفة","أبو طلحة","عثمان بن مظعون","المقداد","حاطب بن أبي بلتعة","أسامة","أبو سلمة","عتبة بن غزوان","أبو مسعود","أبو سعيد الخدري","أبو موسى الأشعري","أبو أمامة الباهلي","أبو مسعود البدري","أبو برزة","أبو أيوب","أبو عنبة الخولاني","أبو لبابة","أبو طلحة","سهل بن سعد","سلمان الفارسي","عبد الله بن عباس","عبد الله بن عمر","عبد الله بن مسعود","عبد الله بن عمرو"]}, key=len, reverse=True)
SAHABA_NRE = re.compile(r"(?<![\u0621-\u064A])(" + "|".join(map(re.escape, SAHABA_N)) + r")\s*$")

def honorific(before):
    b = before[-40:].rstrip(" ،,؛-")
    if PROPHET_CTX.search(b) or re.search(r"(النبي|للنبي|بالنبي|رسول الله|لرسول الله|برسول الله|الرسول|نبيه|نبينا|محمد)\s*$", _n(b)): return "ﷺ"
    if PLURAL_SAHABA.search(b): return "رضي الله عنهم"
    if PLURAL_SALAF.search(b): return "رحمهم الله"
    if FEMALE.search(b): return "رضي الله عنها"
    if DUAL.search(b): return "رضي الله عنهما"
    if SAHABA_NRE.search(_n(b)): return "رضي الله عنه"
    if ANBIYA.search(b) and not re.search(r"(أبو|أبي|أبا|بن)\s+\S+\s*$", b): return "عليه السلام"
    if GOD_CTX.search(b): return "عز وجل"
    return "رحمه الله"


def fix_honorifics(t):
    out, pos = [], 0
    for m in re.finditer(r"\s*\[unknown symbol\]", t):
        before = "".join(out) + t[pos:m.start()]
        h = honorific(before)
        out.append(t[pos:m.start()])
        out.append(" " + h if h != "ﷺ" else " ﷺ")
        pos = m.end()
    out.append(t[pos:])
    return "".join(out)

# ---------------------------------------------------------------- العناوين
HEAD_RE = re.compile(r"^(الفصل\s+\S+|المبحث\s*\S+|المطلب\s+\S+(\s+\S+)?|المطب\s+\S+\s+\S+|مطلب|مطلب آخر|تمهيد|فائدة|فائــدة|فائــــدة)\s*[:：]")
NUM_RE = re.compile(r"^(\d+)\s*[-–]\s*(.+)$")
LEVEL = {"الفصل": 0, "المبحث": 1, "المطلب": 2, "المطب": 2}


def norm_head(t):
    t = re.sub(r"ـ+", "", t)
    t = re.sub(r"\s+", " ", t).strip(" :：.")
    return t

# ---------------------------------------------------------------- القراءة
paras, cur = [], []
for i in range(BODY_START - 1, BODY_END):
    ln = lines[i]
    if ln.strip() == "":
        if cur: paras.append((cur_start, " ".join(cur))); cur = []
    else:
        if not cur: cur_start = i + 1
        cur.append(ln.strip())
if cur: paras.append((cur_start, " ".join(cur)))

stack = []
units = []
REF = re.compile(r"\(?\s*\[\^(\d+)\]\s*\)?")

# 1) تيار نصي واحد مع تتبع العنوان لكل فقرة
stream, marks = [], []          # marks: (offset, path, line, poem)
off = 0
for lineno, raw in paras:
    p = clean(raw)
    is_poem = p.startswith("|")
    if is_poem:
        p_txt = " … ".join(c.strip() for c in p.split("|") if c.strip() and not set(c.strip()) <= set("- "))
    else:
        p_txt = p
    plain = REF.sub("", p_txt)
    hm = HEAD_RE.match(plain)
    nm = NUM_RE.match(plain)
    hk = None
    if hm and len(plain) < 140 and "«" not in plain and not REF.search(p_txt):
        k = hm.group(1).split()[0]
        hk = {"الفصل": "F", "المبحث": "B", "المطلب": "M", "المطب": "M", "تمهيد": "M"}.get(k, "X")
    elif nm and len(plain) < 110 and "«" not in plain and not REF.search(p_txt):
        hk = "N"
    if hk:
        title = norm_head(fix_honorifics(plain))
        if hk in ("F", "B"):
            keep = {"F": [], "B": ["F"]}[hk]
            stack[:] = [x for x in stack if x[0] in keep]
        elif hk == "X":
            if stack and stack[-1][0] == "X": stack.pop()
        else:
            ks = [x[0] for x in stack]
            if hk in ks: del stack[ks.index(hk):]
            elif stack and stack[-1][0] == "X": stack.pop()
        stack.append((hk, title))
        continue
    marks.append((off, [t for _, t in stack], lineno, is_poem))
    stream.append(p_txt + "\n")
    off += len(p_txt) + 1
body = "".join(stream)

def mark_at(pos):
    lo = None
    for m in marks:
        if m[0] <= pos: lo = m
        else: break
    return lo

def is_citation(note):
    return bool(re.search(r"(\(\s*[\d٠-٩]|ص\s*/|رقم|رواه|أخرجه|الحديث|\[[^\]]+:\s*[\d٠-٩])", note))

CITE_START = re.compile(r"^(فتاوى|نونية|رواه|أخرجه|أخرج|وأخرجه|صحيح|سنن|مسند|المصدر|سلسلة|اللجنة|الدرر|مجموع|موطأ|الرابط|تفسير|شرح|فتح|انظر|ذكره|نقلت|مقتبس|من بحر|النونية|كتاب|[^()«»]{0,70}?[\(\[]\s*[\d٠-٩]|[^()«»]{0,70}?\(\s*ص)")

def match_open(pos):
    dd, i = 0, pos - 1
    lim = max(0, pos - 9000)
    while i >= lim:
        ch = body[i]
        if ch == "»": dd += 1
        elif ch == "«":
            dd -= 1
            if dd == 0: return i
        i -= 1
    return -1

last = 0
for m in REF.finditer(body):
    n = int(m.group(1))
    note = notes.get(n, "")
    before = body[last:m.start()]
    tail = body[:m.start()].rstrip()
    ends_quote = tail.endswith("»")
    if not ends_quote and not CITE_START.search(note):
        continue                      # حاشية تعريفية: لا تُنشئ بطاقة
    if ends_quote:
        o = match_open(len(tail))
        if o >= 0:
            start = body.rfind("\n", 0, o) + 1
            seg = body[start:o] + "\uE000" + body[o:m.start()]
        else:
            seg = tail.split("\n")[-1]
    else:
        seg = tail.split("\n")[-1]
        seg = REF.sub("", seg)
    last = m.end()
    mk = mark_at(m.start())
    units.append({"n": n, "seg": REF.sub("", seg).replace("\n", " "), "line": mk[2], "path": mk[1], "poem": mk[3]})

# ---------------------------------------------------------------- الاقتباس
def top_quotes(t):
    spans, depth, start = [], 0, None
    for i, ch in enumerate(t):
        if ch == "«":
            if depth == 0: start = i
            depth += 1
        elif ch == "»" and depth:
            depth -= 1
            if depth == 0: spans.append((start, i + 1))
    return spans

COLLECTIONS = r"(البخاري|مسلم|الترمذي|أبو داود|أبي داود|النسائي|ابن ماجه|أحمد|المسند|الدارمي|ابن حبان|الحاكم|الطبراني|البيهقي|مالك في الموطأ|الموطأ|ابن خزيمة|البزار|أبو يعلى|الديلمي|عبد الرزاق|ابن أبي شيبة|الخرائطي|ابن السني|الطحاوي)"
MARFU_CTX = re.compile(r"(رسول الله|رسولَ الله|رسولُ الله|رسولِ الله|النبي|النبيُّ|النبيِّ|النبيَّ|نبي الله|نبيُّ الله|نبيَّ الله|الرسول|أبو القاسم)")


def grade(note):
    g = {"grade": "", "hukm": ""}
    note = re.sub(r"[\u064B-\u0652]", "", note)
    m = re.search(r"((?:و)?(?:صحَّحه|صححه|حسَّنه|حسنه|ضعَّفه|ضعفه|جوَّد إسناده|جود إسناده|إسناده (?:صحيح|حسن|ضعيف|جيد)|قال المنذري|قال العراقي|قال ابن كثير|قال الشوكاني|قال أبو موسى|هذا حديث حسن|حديث حسن|لا يصح|لم يصح)[^.؛]*)", note)
    if m:
        h = m.group(1).strip()
        if re.match(r"^و?(قال|إسناده)", h) and not re.search(r"(صحيح|حسن|ضعيف|جيد|يصح|مطعن)", h):
            h = ""
        if h:
            g["hukm"] = re.sub(r"^و", "", h).strip()
            hh = g["hukm"]
            if re.search(r"^(ضع|ضعف)|ضعيف|لا يصح|لم يصح|ضعَّف", hh): g["grade"] = "ضعيف"
            elif re.search(r"لغيره", hh) and re.search(r"^حس|حسن", hh): g["grade"] = "حسن لغيره"
            elif re.search(r"لغيره", hh): g["grade"] = "صحيح لغيره"
            elif re.search(r"^(حسَّنه|حسنه|حسن)|إسناده حسن|حسن أو", hh): g["grade"] = "حسن"
            else: g["grade"] = "صحيح"
    if not g["grade"]:
        if re.match(r"^(رواه|أخرجه)\s+(البخاري|مسلم)", note) or re.match(r"^(صحيح البخاري|صحيح مسلم)", note):
            g["grade"] = "صحيح"; g["hukm"] = "في الصحيحين أو أحدهما"
    return g

LATE_SCHOLARS = """ابن القيم|ابن تيمية|شيخ الإسلام|ابن رجب|النووي|ابن حجر|الحافظ ابن حجر|القرطبي|الطبري|ابن جرير|ابن كثير|السعدي|ابن عثيمين|ابن باز|اللجنة الدائمة|الشوكاني|البغوي|ابن عطية|الراغب|الزبيدي|المعجم الوسيط|مختار الصحاح|السندي|الطيبي|المباركفوري|العظيم آبادي|الملا علي القاري|علي القاري|ابن الملك|النسفي|الماوردي|الألوسي|الرازي|الزجاج|الواحدي|القشيري|السبكي|ابن العربي|أبو الوليد الباجي|الباجي|القاضي عياض|الغزالي|أبو حامد|الآجري|ابن قدامة|ابن الجوزي|الذهبي|ابن دقيق العيد|الخطابي|السيوطي|الزركشي|ابن الأثير|الجصاص|الأزهري|ابن قتيبة|السمعاني|الثعلبي|البيضاوي|الشنقيطي|ابن باديس|ابن قرقول|محمد بن علي الترمذي|الحارث المحاسبي|المحاسبي|أبو طالب|الخطيب|ابن الملقن|المناوي|الصنعاني|ابن عبد البر|ابن بطال|عبد الدائم الكحيل|الباحث|ابن دحية|ابن المنير|أبو الليث السمرقندي|البدر الفيومي|ابن خلكان|الحجاوي|ابن هشام|ابن إسحاق|ابن سعد|ابن عساكر|أبو نعيم|الترمذي|ابن حبان|أبو حاتم|العلماء|قال العلماء|أهل العربية|الطيبي""".split("|")
LATE_RE = re.compile(r"(" + "|".join(sorted(map(re.escape, LATE_SCHOLARS), key=len, reverse=True)) + r")")

ALIASES = [
    (r"^(الإمام |الحافظ |العلامة |الشيخ |الفقيه )+", ""),
    (r"^شيخ الإسلام( ابن تيمية)?$", "ابن تيمية"),
    (r"^ابن جرير( الطبري)?$", "الطبري"), (r"^ابن قيم الجوزية$", "ابن القيم"),
    (r"^ابن رجب الحنبلي$", "ابن رجب"), (r"^الحسن( البصري)?$", "الحسن البصري"),
    (r"^الراغب( الأصفهاني)?$", "الراغب الأصفهاني"), (r"^أبو حامد( الغزالي)?$", "الغزالي"),
    (r"^الملا علي القاري|^علي القاري$", "الملا علي القاري"), (r"^ابنُ كثيرٍ$", "ابن كثير"),
    (r"^أبو الوليد الباجي$", "الباجي"), (r"^ابن حجر$", "ابن حجر"),
    (r"^عمر بن الخطاب$|^عمرُ$|^عمرَ$|^الفاروق( عمر)?$", "عمر بن الخطاب"),
    (r"^أبي بكر$|^أبو بكر$|^أبو بكر الصديق$|^الصديق$", "أبو بكر الصديق"),
    (r"^ابن مسعود$|^عبد الله بن مسعود$|^عبدِ الله بن مسعود$", "عبد الله بن مسعود"),
    (r"^ابن عمر$|^عبد الله بن عمر$", "عبد الله بن عمر"),
    (r"^ابن عباس$|^ابن عباسٍ$|^ابْنُ عَبَّاسٍ$", "عبد الله بن عباس"),
    (r"^أبي هريرة$", "أبو هريرة"), (r"^أبي الدرداء$", "أبو الدرداء"), (r"^أبي ذر$|^أبي ذَرٍّ$", "أبو ذر"),
    (r"^أبي موسى( الأشعري)?$|^أبو موسى$", "أبو موسى الأشعري"), (r"^أبي سعيد( الخدري)?$|^أبي سعيدٍ الخدري$|^أبو سعيد$", "أبو سعيد الخدري"),
    (r"^أبي أمامة( الباهلي)?$|^أبو أمامة$", "أبو أمامة الباهلي"), (r"^أبي قتادة$", "أبو قتادة"),
    (r"^عليٍّ$|^عليّ$|^علي$|^علي بن أبي طالب$|^عليِّ$", "علي بن أبي طالب"),
    (r"^عائشة$", "عائشة أم المؤمنين"), (r"^أنس$|^‌?أنس بن مالك$|^أنسٍ$", "أنس بن مالك"),
    (r"^مجاهد بن جبر$|^مجاهدٍ$", "مجاهد"), (r"^عطاء ابن أبي رباح$|^عطاء بن أبي رباح$", "عطاء بن أبي رباح"),
    (r"^الفضيل( بن عياض)?$|^فضيل بن عياض$", "الفضيل بن عياض"), (r"^ابنُ القيم$", "ابن القيم"),
    (r"^حذيفةُ$|^حذيفة$", "حذيفة بن اليمان"), (r"^سفيان الثوري$|^الثوريَّ$|^الثوري$", "سفيان الثوري"),
    (r"^ابن عثيمين$|^الشيخ ابن عثيمين$", "ابن عثيمين"),
    (r"^محمد ابن سيرين$|^ابن سيرين$", "محمد بن سيرين"), (r"^ابن قدامة$", "ابن قدامة"),
    (r"^محمد بن كعب القرظي$", "محمد بن كعب القرظي"), (r"^أبو عمران الجوني$", "أبو عمران الجوني"),
    (r"^مقاتل بن حيان$", "مقاتل بن حيان"), (r"^سبكي$|^السبكي$", "السبكي"),
    (r"^القاضي أبو بكر بن العربي$|^ابن العربي المالكي$|^ابن العربي$", "ابن العربي"),
    (r"^عطاء$|^عطاء بن أبي رباح$", "عطاء بن أبي رباح"), (r"^أحمد بن حنبل$|^أحمد$", "أحمد بن حنبل"),
    (r"^صاحب الإحياء$", "الغزالي"), (r"^فخر الدين الرازي$", "الرازي"), (r"^الشافعي$", "الشافعي"),
    (r"^عوفِ بنِ مالك$", "عوف بن مالك"), (r"^عمَّار بن ياسر$", "عمار بن ياسر"),
]


JUNK = re.compile(r"(آخرون|الأرض|^رحمه الله$|الصلاة|لأصحابها|أصحابنا|الراكع|^النبي$|^أصله$|جماعتها|^أبيه$|^أمه$|^أبي$|^أبو$|^الخشوع$|الاحتمال|^القراءة$|محاذاة|مدارسة|حماره|اكتم|غمض|^القاضي$|^ثابت$|^حاتم$|^زائدة$|^الناس|^هذا|^هذه|^ذلك|^قوم|^أحد|^الرجل|^امرأة|^الله|^تعالى|^رسول|^رجل|^لي$|^له$|^لها$|^لهم$|^بعض|^أهل|^قوله|^في |^إن |^أن |^عمرو$|^سمعت )")


def canon(name):
    name = re.sub(r"[ً-ْٰـ]", "", name)
    name = re.split(r"[,،؛]", name)[0].strip(" :-–")
    name = re.sub(r"\s+(قال|قالت|أيضا|أنه|التابعي)$", "", name).strip()
    if " عن " in name: name = name.split(" عن ")[-1]
    if " أن " in name: name = name.split(" أن ")[-1]
    name = re.sub(r"^(به|جدته|جده|أبيه|عمه|سمعت)\s+", "", name).strip()
    name = re.sub(r"^أبي(?=\s)", "أبو", name)
    name = re.sub(r"^براهيم", "إبراهيم", name)
    name = name.replace("اللَّه", "الله")
    if not name or JUNK.search(name): return ""
    for pat, rep in ALIASES[:1]:
        name = re.sub(pat, rep, name)
    for pat, rep in ALIASES[1:]:
        if re.search(pat, name):
            name = re.sub(pat, rep, name) if rep else name
            break
    return name.strip()

SPEAKER_RE = re.compile(r"(?:^|[\s،.؛:(])(?:و|ف)?(قال|قالت|يقول|عن|سُئل|سئل|كتب|روى)\s+((?:ال|أب|ابن|عبد|أم|بن|[ء-ي])[^،,؛:«»\[\]()]{1,60}?)\s*(?:\[unknown symbol\]|ﷺ|رضي|رحمه|عليه السلام|عز وجل|:|،|,|؛|\s-\s|$)")
BAD_SPEAKER = re.compile(r"^(الناس|هذا|هذه|ذلك|قوم|أحد|من |الرجل|امرأة|الله|تعالى|رسول|النبي|رجل|لي|له|لها|لهم|بعض|أهل|ابن آدم|قوله|في|إن|أن|عمرو$)")

NAME_FROM_BOOK = {"مدارج السالكين": "ابن القيم", "الوابل الصيب": "ابن القيم", "كتاب الصلاة": "ابن القيم", "الفوائد": "ابن القيم", "زاد المعاد": "ابن القيم", "الداء والدواء": "ابن القيم", "مفتاح دار السعادة": "ابن القيم", "طريق الهجرتين": "ابن القيم", "بدائع الفوائد": "ابن القيم", "كتاب الروح": "ابن القيم", "إغاثة اللهفان": "ابن القيم", "مجموع الفتاوى": "ابن تيمية", "تفسير ابن رجب": "ابن رجب", "تفسير القرطبي": "القرطبي", "تفسير الطبري": "الطبري", "تفسير ابن كثير": "ابن كثير", "تفسير السعدي": "السعدي", "تفسير البغوي": "البغوي", "فتح القدير": "الشوكاني", "المعجم الوسيط": "المعجم الوسيط", "سلسلة فتاوى نور على الدرب": "ابن عثيمين", "سلسلة لقاءات الباب المفتوح": "ابن عثيمين", "سلسلة اللقاء الشهري": "ابن عثيمين", "اللجنة الدائمة": "اللجنة الدائمة", "الدرر الثرية": "ابن باز", "http://www.kaheel7.com": "عبد الدائم الكحيل", "مختصر منهاج القاصدين": "ابن قدامة"}


def find_speaker(prefix, note):
    cands = [m for m in SPEAKER_RE.finditer(prefix)]
    for m in reversed(cands):
        nm = m.group(2).strip()
        nm = re.sub(r"\s+(في|عند|بعد|من|يومًا|يوما|وهو|حين|حينما|لما|إذا)\b.*$", "", nm)
        nm = re.sub(r"\s+", " ", nm).strip()
        words = nm.split()
        if len(words) > 7 or not nm or BAD_SPEAKER.search(nm):
            continue
        return canon(nm)
    for k, v in NAME_FROM_BOOK.items():
        if k in note: return v
    return ""

# ---------------------------------------------------------------- بناء البطاقات
raw_cards = []
for u in units:
    note = notes.get(u["n"], "")
    seg = u["seg"]
    seg_fixed = fix_quran(fix_honorifics(seg))
    qmark = seg_fixed.find("\uE000")
    seg = seg.replace("\uE000", "")
    note_fixed = fix_quran(fix_honorifics(note))
    seg_fixed = seg_fixed.replace("\uE000", "") if qmark < 0 else seg_fixed
    if u["poem"]:
        kind = "شعر"
        text = seg_fixed.strip(" …|")
        prefix = ""
    elif qmark >= 0:
        text = seg_fixed[qmark + 1:]
        prefix = seg_fixed[:qmark]
        kind = None
    else:
        text = seg_fixed.replace("\uE000", "").strip(" .،:")
        prefix = text
        kind = "نقل"
    text = re.sub(r"\s+", " ", text).strip()
    if len(re.sub(r"[«»\s.]", "", text)) < 6:
        continue
    g = grade(note)
    has_coll = re.search(COLLECTIONS, note) is not None
    # التصنيف
    pre_raw = prefix if kind is None else fix_honorifics(seg)
    if kind is None or kind == "نقل":
        marfu_ctx = bool(MARFU_CTX.search(pre_raw[-170:]))
        is_marfu = marfu_ctx and (g["grade"] or (has_coll and re.search(r"(رواه|أخرجه|سنن|صحيح|مسند)", note)))
        if not is_marfu and kind is None and re.search(r"(رواه|أخرجه|سنن|مسند|صحيح البخاري|صحيح مسلم)", note) and re.search(COLLECTIONS, note) \
                and MARFU_CTX.search(text[:160]) and not re.search(r"(عبد الرزاق|ابن أبي شيبة|المصنف|الزهد|ابن أبي الدنيا)", note.split("و")[0] if note else ""):
            is_marfu = True
        if not is_marfu and kind is None and re.match(r"^(رواه|أخرجه|صحيح البخاري|صحيح مسلم|سنن|مسند)", note) and re.search(COLLECTIONS, note):
            imm = pre_raw[-90:]
            named = re.search(r"(قال|قالت|يقول)\s+[^:«]{2,50}?(رضي الله عنه|رضي الله عنها|رضي الله عنهما|رحمه الله|عليه السلام)?\s*:\s*$", imm) and not re.search(r"(قال|يقول)\s*:\s*$", imm)
            via = re.search(r"عن\s+\S+", imm) and not MARFU_CTX.search(imm)
            if not named and not via:
                is_marfu = True
        if is_marfu:
            kind = "حديث مرفوع"
        elif kind is None:
            kind = "قول"
    if kind == "حديث مرفوع" and not g["grade"] and not re.match(r"^(رواه|أخرجه|صحيح البخاري|صحيح مسلم)\s*(الإمام\s*)?(البخاري|مسلم|أبو داود|الترمذي|النسائي|ابن ماجه|أحمد)?", note):
        kind = "قول"
    if kind != "حديث مرفوع" and g["hukm"] == "في الصحيحين أو أحدهما":
        g = {"grade": "", "hukm": ""}
    speaker = "" if kind == "شعر" else find_speaker(prefix if prefix else pre_raw, note)
    narrator = ""
    if kind == "حديث مرفوع":
        m = re.search(r"(?:^|\s)(?:و|ف)?عن\s+([^،:«\[]{2,40}?)\s*(?:ﷺ|رضي|رحمه|،|:|قال|أنه|أن)", fix_honorifics(seg))
        narrator = canon(m.group(1).strip()) if m else (speaker if speaker and speaker not in ("رسول الله",) else "")
        speaker = "النبي ﷺ"
    elif kind == "قول":
        if speaker and (SAHABA_NRE.search(_n(speaker)) or speaker in ("عبد الله بن عباس", "عبد الله بن عمر", "عائشة أم المؤمنين", "عمر بن الخطاب", "أبو بكر الصديق", "علي بن أبي طالب", "عبد الله بن مسعود", "حذيفة بن اليمان", "أبو موسى الأشعري", "أنس بن مالك", "أبو الدرداء", "أبو ذر", "أبو هريرة", "عبد الله بن عمرو", "عوف بن مالك", "عمار بن ياسر", "أبو سعيد الخدري", "أسماء بنت أبي بكر")):
            kind = "أثر صحابي"
        elif speaker and LATE_RE.search(speaker):
            kind = "قول عالم"
        elif speaker:
            kind = "أثر عن السلف"
        else:
            kind = "قول عالم" if LATE_RE.search(note) else "أثر عن السلف"
    raw_cards.append({
        "fn": u["n"], "kind": kind, "speaker": speaker, "narrator": narrator,
        "text": text, "intro": re.sub(r"\s+", " ", prefix if kind not in ("نقل", "شعر") else "").strip()[-220:],
        "source": note_fixed, "grade": g["grade"], "hukm": g["hukm"],
        "path": u["path"], "line": u["line"],
        "riwaya": bool(re.search(r"(^|\s)(و)?(رُوي|رُويَ|روي|يروى|يُروى|ويروى)(\s|$)", seg)),
    })

# ---------------------------------------------------------------- الدمج
def norm(t):
    t = re.sub(r"[ً-ْٰـ]", "", t)
    t = re.sub(r"[إأآٱ]", "ا", t).replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    t = re.sub(r"[^ء-ي\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def toks(t):
    return set(w for w in norm(t).split() if len(w) > 2)

cards = []
for c in raw_cards:
    tk = toks(c["text"])
    merged = False
    if len(tk) >= 5:
        for d in cards:
            if d["kind"] == "شعر" or c["kind"] == "شعر": continue
            inter = len(tk & d["_tk"])
            small = min(len(tk), len(d["_tk"])); big = max(len(tk), len(d["_tk"]))
            if small and inter / small >= 0.85 and inter / big >= 0.6 and inter >= 5 and (c["kind"] == d["kind"] or "نقل" in (c["kind"], d["kind"])):
                d["locations"].append({"path": c["path"], "fn": c["fn"], "line": c["line"]})
                if c["source"] not in d["sources"]: d["sources"].append(c["source"])
                if not d["grade"] and c["grade"]: d["grade"], d["hukm"] = c["grade"], c["hukm"]
                if len(c["text"]) > len(d["text"]): d["text"] = c["text"]
                merged = True; break
    if not merged:
        cards.append({**c, "_tk": tk, "sources": [c["source"]],
                      "locations": [{"path": c["path"], "fn": c["fn"], "line": c["line"]}]})

for i, d in enumerate(cards, 1):
    d["id"] = i
    d["topic"] = " ← ".join(d["locations"][0]["path"])
    for k in ("_tk", "source", "path", "line"): d.pop(k, None)

json.dump({"book": BOOK, "author": "عبد الرزاق بن فاضل الربيعي", "cards": cards},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

kinds = Counter(c["kind"] for c in cards)
grades = Counter(c["grade"] for c in cards if c["kind"] == "حديث مرفوع")
print("units:", len(units), "raw:", len(raw_cards), "cards:", len(cards))
print(kinds.most_common()); print(grades.most_common())
print("no speaker:", sum(1 for c in cards if not c["speaker"] and c["kind"] != "شعر"))
print("multi-location:", sum(1 for c in cards if len(c["locations"]) > 1))
print(Counter(c["speaker"] for c in cards).most_common(40))
