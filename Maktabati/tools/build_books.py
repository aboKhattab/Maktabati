# -*- coding: utf-8 -*-
"""يبني بطاقات الكتب والخطب من ملفات وورد مباشرة.

الاستعمال: python3 build_books.py <مجلد ملفات docx> <ملف الإخراج books.json>
"""
import json, re, sys, os, glob
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import core
from docx_paras import read_docx, quotes_to_guillemets

SRC_DIR, OUT = sys.argv[1], sys.argv[2]
AUTHOR = "عبد الرزاق بن فاضل الربيعي"

_D = "[\u064B-\u0652\u0670\u0640]*"
PBUH = re.compile(r"\s*[(\-–]?\s*" + _D.join("صلى") + _D + r"\s+" + _D.join("الله") + _D + r"\s+" + _D.join("عليه") + _D + r"\s+" + _D.join("وسلم") + _D + r"\s*[)\-–]?")

# النصوص هنا مشكولة: قرائن الرفع تُفحص بعد حذف التشكيل
_MARFU = core.MARFU_CTX
class _Strip:
    def search(self, t): return _MARFU.search(re.sub(_D, "", t))
core.MARFU_CTX = _Strip()


GLYPH = re.compile("[\uFB50-\uFDF9\uFDFB-\uFDFF\uFE70-\uFEFF]")


def _glyphy(x):
    return len(GLYPH.findall(x)) > max(2, len(re.sub(r"\s", "", x)) * 0.4)


def fix_quran_unicode(t):
    # {نص مقروء} ← ﴿…﴾ ، {رموز خط المصحف} [السورة: الآية] ← ﴿الآية: السورة: الآية﴾
    t = re.sub(r"\{([^{}]*)\}\s*\[([^\]]+)\]", lambda m: f"﴿الآية: {m.group(2).strip()}﴾" if _glyphy(m.group(1)) else f"﴿{m.group(1).strip()}﴾ [{m.group(2).strip()}]", t)
    t = re.sub(r"\{([^{}]*)\}", lambda m: "﴿…﴾" if _glyphy(m.group(1)) else f"﴿{m.group(1).strip()}﴾", t)
    return GLYPH.sub("", t)


QREF = re.compile(r"^\[?\s*(?:سورة\s+)?[\u0621-\u064A\u064B-\u0652 ]{2,25}\s*[:：]?\s*[\d٠-٩]+(?:\s*[-–،,]\s*[\d٠-٩]+)*\s*\]?\s*\.?$")


def inline_quran_refs(t, notes):
    """{آية}([^N]) والحاشية مرجع قرآني ← ﴿…﴾ بلا حاشية، كي لا تصير بطاقة."""
    def rep(m):
        n = int(m.group(2)); note = notes.get(n, "")
        if not QREF.match(note): return m.group(0)
        ref = note.strip("[]. ")
        return f"﴿الآية: {ref}﴾" if _glyphy(m.group(1)) else f"﴿{m.group(1).strip()}﴾ [{ref}]"
    return re.sub(r"\{([^{}]*)\}\s*\(?\s*\[\^(\d+)\]\s*\)?", rep, t)


core.fix_quran = fix_quran_unicode


def clean(t):
    t = t.replace("‌", "").replace("‏", "").replace("‎", "").replace("\xa0", " ")
    t = PBUH.sub(" ﷺ", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t.strip()


def nk(t):
    return re.sub(r"[ً-ْـ\s:{}]", "", t)


POEM = re.compile(r"\S\s*(\.\.\.|…|\\\.\.\.)\s*\S")


def is_poem(t):
    return bool(POEM.search(t)) and len(t) < 230 and "«" not in t and not re.search(r"(قال|رواه|أخرجه)", t[:30])


def khutba_paras(raw, title_hint=None):
    """خطبة مفردة: [عنوان الخطبة، الخطبة الأولى/الثانية]"""
    title, part, out, wait_title = title_hint, "الخطبة الأولى", [], False
    for i, (st, t) in enumerate(raw):
        t = t.strip()
        if not t: continue
        k = nk(t)
        if "خطبةجمعةمكتوبةبعنوان" in k or "خطبةجمعةبعنوان" in k:
            wait_title = True; continue
        if wait_title:
            title = t.strip("{} "); wait_title = False; continue
        if k in ("بسماللهالرحمنالرحيم",): continue
        if k.startswith("الخطبةالثانية") and len(k) < 20:
            part = "الخطبة الثانية"; continue
        out.append((i, t, [title or "", part]))
    return out


def zad_paras(raw):
    """زاد المنابر: عنوان الخطبة بنمط «العنوان الأول» أو «heading 2»، ثم «الخطبة الثانية»"""
    title, part, out = "المقدمة", "", []
    for i, (st, t) in enumerate(raw):
        t = t.strip()
        if not t or st.startswith("toc") or st == "عنوان جانبي": continue
        k = nk(t)
        if k.startswith("الخطبةالثانية") and len(k) < 22:
            part = "الخطبة الثانية"; continue
        if st in ("العنوان الأول", "heading 2", "heading 1"):
            title, part = t.strip(" :"), "الخطبة الأولى"
            if k.startswith("محتويات") or k.startswith("فهرس"): title = ""
            continue
        if not title: continue
        out.append((i, t, [title, part] if part and title != "المقدمة" else [title]))
    return out


def heads_layout(top, sub, start=None):
    """عناوين بنمطين: أعلى وفرعي؛ العناوين المتتالية بلا متن بينها تُضم."""
    def lay(raw):
        h1, h2, out, last_was_head = "", "", [], None
        started = start is None
        for i, (st, t) in enumerate(raw):
            t = re.sub(r"\s+", " ", t).strip()
            if not t or st.startswith("toc"): continue
            if st in top:
                started = True
                tt = t.strip(" :")
                if re.match(r"^-\s*اسم", tt): continue
                if nk(tt).startswith("فهرس"): h1 = ""; last_was_head = None; continue
                if last_was_head == "top" and h1 and not nk(tt).startswith(nk(h1)): h1 = h1 + ": " + tt
                else: h1 = tt
                h2 = ""; last_was_head = "top"; continue
            if st in sub and h1:
                tt = t.strip(" :")
                h2 = (h2 + ": " + tt) if last_was_head == "sub" and h2 else tt
                last_was_head = "sub"; continue
            last_was_head = None
            if not started or not h1: continue
            out.append((i, t, [h1] + ([h2] if h2 else [])))
        return out
    return lay


def process(path, layout):
    raw, notes = read_docx(path)
    notes = {k: clean(v) for k, v in notes.items()}
    texts = quotes_to_guillemets([inline_quran_refs(clean(t), notes) for _, t in raw])
    raw = [(st, t) for (st, _), t in zip(raw, texts)]
    items = layout(raw)
    paras = [(ln, t, path_, raw[ln][0].startswith("قصيدة") or is_poem(t)) for ln, t, path_ in items]
    units = core.build_units(paras, notes)
    cards = core.build_cards(units, notes)
    for c in cards: refine(c)
    return items, cards


SAHABA_FULL = ("عبد الله بن عباس", "عبد الله بن عمر", "عائشة أم المؤمنين", "عمر بن الخطاب", "أبو بكر الصديق",
               "علي بن أبي طالب", "عبد الله بن مسعود", "حذيفة بن اليمان", "أبو موسى الأشعري", "أنس بن مالك",
               "أبو الدرداء", "أبو ذر", "أبو هريرة", "عبد الله بن عمرو", "عوف بن مالك", "عمار بن ياسر",
               "أبو سعيد الخدري", "أسماء بنت أبي بكر")
HON = r"\s*(?:رضي الله عنهما|رضي الله عنهم|رضي الله عنها|رضي الله عنه|رحمه الله تعالى|رحمه الله|رحمهم الله|عليه السلام|ﷺ)?\s*،?\s*"
NAME = r"([^،:«»﴿﴾()\[\]]{2,40}?)"
SPK_EXTRA = [
    re.compile(r"سمعت\s+" + NAME + HON + r"(?:يقول|قال)\s*:?\s*$"),
    re.compile(r"(?:^|\s)(?:و|ف)?عن\s+" + NAME + HON + r"(?:أنه\s+)?(?:قال|قالت|يقول|كان يقول)\s*:?\s*$"),
    re.compile(r"(?:^|\s)(?:و|ف)?(?:كان|كانت)\s+" + NAME + HON + r"(?:يقول|تقول)\s*:?\s*$"),
    re.compile(r"(?:^|\s)(?:في\s+|ك?ما\s+في\s+)?قول\s+" + NAME + HON + r"(?:في\s+[^:«]{2,60})?:?\s*$"),
    re.compile(r"(?:^|\s)(?:و|ف)?(?:قال|يقول|ذكر|نقل|أورد)\s+" + NAME + HON + r"(?:في\s+[^:«]{2,70})?:\s*$"),
]
BAD_NAME = re.compile(r"(﴿|هم$|كم$|نا$|^ما |^من |^هذا|^ذلك|^تعالى|^الله|^ربنا|^النبي|^رسول|^الشاعر|^بعض|^أحد|^قائل|^رجل|^الرجل|^امرأة|^أبوها|^أبيه|^أمه|^له$|^لها$|^لهم$)")


def _ns(t):
    return re.sub(r"[\u064B-\u0652\u0670\u0640]", "", t)


def kind_for(speaker):
    if speaker in SAHABA_FULL or core.SAHABA_NRE.search(core._n(speaker)): return "أثر صحابي"
    if core.LATE_RE.search(speaker): return "قول عالم"
    return "أثر عن السلف"


def refine(c):
    if c["kind"] in ("شعر", "حديث مرفوع"):
        if c["kind"] == "حديث مرفوع":
            # الراوي: «عن فلان رضي الله عنه» في السياق أو في الحاشية، وإلا يُترك فارغًا
            n = ""
            for src in (_ns(c["intro"]), _ns(" ".join(c["sources"]))):
                m = list(re.finditer(r"(?:^|\s)(?:و|ف)?عن\s+([^،:«»()]{2,40}?)\s*(?:رضي الله عن)", src))
                if m: n = core.canon(m[-1].group(1).strip()); break
            c["narrator"] = n
        return
    intro = _ns(c["intro"]).rstrip()
    sp = ""
    for rx in SPK_EXTRA:
        m = rx.search(intro)
        if m:
            cand = re.sub(r"\s+", " ", m.group(1)).strip()
            if " عن " in cand: cand = cand.split(" عن ")[-1]
            if len(cand.split()) <= 6 and not BAD_NAME.search(cand):
                sp = core.canon(cand)
                if sp: break
    if sp and sp != c["speaker"]:
        c["speaker"] = sp
        if c["kind"] != "نقل": c["kind"] = kind_for(sp)
    if c["speaker"] and BAD_NAME.search(c["speaker"]): c["speaker"] = ""
    if c["kind"] == "نقل" and c["speaker"] and len(c["speaker"].split()) > 4: c["speaker"] = ""
    if not c["speaker"] and c["kind"] == "أثر عن السلف": c["kind"] = "نقل"
    # الترضّي بعد اسم القائل مباشرة دليل على أنه صحابي
    if c["speaker"] and c["kind"] in ("أثر عن السلف", "قول عالم") and re.search(r"رضي الله (عنه|عنها|عنهما)\s*،?\s*(?:قال|يقول|قالت|تقول)?\s*:?\s*$", intro):
        c["kind"] = "أثر صحابي"


ORD = {"الأول": 1, "الثاني": 2, "الثالث": 3, "الرابع": 4, "الخامس": 5, "السادس": 6, "السابع": 7, "الثامن": 8, "التاسع": 9, "العاشر": 10}
MAWLID = "أقوال علماء الإسلام في حكم الاحتفال بالمولد النبوي"


def mawlid_cards(path):
    """كتاب بلا حواشٍ: كل نقل تحت اسم العالم، ومصدره في آخر فقرة."""
    raw, _ = read_docx(path)
    cards, sp, topic, buf = [], "", "", []
    CITE = re.compile(r"\((?:ص\s*/?\s*)?[\d٠-٩]+(?:\s*/\s*[\d٠-٩]+)?\)|\(\s*[\d٠-٩]+\s*/|رقم الفتوى|فتاوى|المجلد|الجزء")
    def flush(src):
        nonlocal buf
        body = [b for b in buf if not re.match(r"^(قال|وقال)\s*[^:]{0,25}:$", b)]
        if body:
            text = " ".join(body)
            cards.append({"kind": "قول عالم", "speaker": sp, "narrator": "", "text": fix_quran_unicode(text),
                          "intro": "", "sources": [src], "grade": "", "hukm": "", "riwaya": False,
                          "locations": [{"path": [sp_full, topic] if topic else [sp_full], "fn": 0, "line": 0}]})
        buf = []
    sp_full = ""
    for st, t in raw:
        t = clean(t)
        if not t or st.startswith("toc"): continue
        if st == "heading 2":
            sp_full = t; buf = []
            sp = core.canon(re.sub(r"\s*\(.*$", "", t).strip()) or t; topic = ""; continue
        if st == "heading 1":
            if buf: flush("")
            topic = t.strip(" :!"); continue
        if not sp_full: continue
        if len(t) < 200 and CITE.search(t) and buf:
            flush(t); continue
        buf.append(t)
    return cards


def book_of(raw):
    head = " ".join(t for _, t in raw[:40])
    if "خطبةجمعة" in nk(" ".join(t for _, t in raw[:6])) and "زاد المنابر" not in head:
        return "خطب الجمعة", khutba_paras, 30
    if "زاد المنابر" in head:
        m = re.search(r"الجزء\s*[-–]?\s*ال?(\S+)", head.split("زاد المنابر", 1)[1])
        w = "ال" + m.group(1).strip("-–").removeprefix("ال") if m else ""
        return f"زاد المنابر - الجزء {w}".strip(), zad_paras, ORD.get(w, 9)
    if "المنتقى المُستطاب" in head or "المنتقى المستطاب" in head:
        return "المنتقى المستطاب في المروءات والآداب", heads_layout({"heading 1"}, {"heading 2"}), 20
    if "مقامات" in head:
        return "المنتقى من مقامات الحريري", heads_layout({"عنوان أنس 1"}, {"heading 2", "heading 3"}), 21
    if "تذكير الأخيار" in head:
        return "تذكير الأخيار بفضائل المكث في مكان أداء الصلاة وقراءة الأذكار", heads_layout({"heading 2"}, {"heading 1"}), 22
    if "أسماء الله الحسنى" in head:
        return "أسماء الله الحسنى", heads_layout({"heading 2"}, {"title"}), 23
    if "الاحتفال بمولد" in head:
        return MAWLID, None, 24
    return "خطب الجمعة", khutba_paras, 30


files = sorted(glob.glob(os.path.join(SRC_DIR, "*.docx")))
books, order = {}, {}
report = []
for f in files:
    raw, _ = read_docx(f)
    b, lay, o = book_of(raw)
    if lay is None:
        items, cards = [], mawlid_cards(f)
    else:
        items, cards = process(f, lay)
    books.setdefault(b, []).extend(cards); order[b] = o
    title = items[0][2][0] if items else b
    report.append((b, title, len(cards), Counter(c["kind"] for c in cards)))

out = []
for b in sorted(books, key=lambda x: order[x]):
    cards = books[b]
    for i, c in enumerate(cards, 1): c["id"] = i
    out.append({"book": b, "author": AUTHOR, "cards": cards})
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in report: print(r[0][:14], "|", r[1][:40], "|", r[2], dict(r[3]))
for b in out: print(b["book"], len(b["cards"]), Counter(c["kind"] for c in b["cards"]).most_common(),
                   "no speaker:", sum(1 for c in b["cards"] if not c["speaker"] and c["kind"] not in ("شعر", "حديث مرفوع")))
