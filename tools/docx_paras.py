# -*- coding: utf-8 -*-
"""قراءة ملف وورد مباشرة: فقرات (نمط + نص بإحالات [^N]) وحواشٍ."""
import re, zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


# خط «KFGQPC Arabic Symbols 01»: رموز الصلاة والترضي والترحم
KFGQPC = {"H": "ﷺ", "O": "ﷺ", "I": "رضي الله عنه", "J": "رضي الله عنها", "L": "رضي الله عنهما",
          "M": "رضي الله عنهم", "S": "عليه السلام", "R": "عليهما السلام", "V": "رحمه الله",
          "X": "رحمهم الله", "D": "عز وجل", "E": "تعالى"}


def _sym(el):
    font = (el.get(W + "font") or "").lower()
    ch = el.get(W + "char") or ""
    try: letter = chr(int(ch, 16) & 0xFF)
    except ValueError: return ""
    if "kfgqpc" in font and "symbol" in font:
        return " " + KFGQPC.get(letter, "[unknown symbol]") + " "
    return ""          # خطوط زخرفية (AGA Arabesque وغيرها)


def _walk(p):
    # لا ينزل إلى مربعات النص؛ فقراتها تُقرأ وحدها
    for ch in p:
        if ch.tag == W + "txbxContent": continue
        yield ch
        yield from _walk(ch)


def _run_text(p):
    out = []
    for el in _walk(p):
        tag = el.tag
        if tag == W + "sym":
            out.append(_sym(el))
        elif tag == W + "t":
            out.append(el.text or "")
        elif tag in (W + "tab", W + "br", W + "cr"):
            out.append(" ")
        elif tag == W + "footnoteReference":
            out.append(f"[^{el.get(W + 'id')}]")
        elif tag == W + "noBreakHyphen":
            out.append("-")
    return "".join(out)


MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"


def _skip_deleted(root):
    # يُزيل النصوص المحذوفة في تتبع التغييرات، والنسخ الاحتياطية المكررة لمربعات النص
    for parent in root.iter():
        for ch in list(parent):
            if ch.tag in (W + "del", W + "moveFrom", MC + "Fallback"):
                parent.remove(ch)


def read_docx(path):
    z = zipfile.ZipFile(path)
    styles = {}
    try:
        sr = ET.fromstring(z.read("word/styles.xml"))
        for s in sr.iter(W + "style"):
            n = s.find(W + "name")
            styles[s.get(W + "styleId")] = (n.get(W + "val") if n is not None else "").lower()
    except KeyError:
        pass
    root = ET.fromstring(z.read("word/document.xml"))
    _skip_deleted(root)
    paras = []
    body = root.find(W + "body")
    for p in body.iter(W + "p"):
        ps = p.find(f"{W}pPr/{W}pStyle")
        st = styles.get(ps.get(W + "val"), "") if ps is not None else ""
        paras.append((st, _run_text(p)))
    notes = {}
    if "word/footnotes.xml" in z.namelist():
        fr = ET.fromstring(z.read("word/footnotes.xml"))
        _skip_deleted(fr)
        for fn in fr.iter(W + "footnote"):
            i = int(fn.get(W + "id"))
            if i <= 0: continue
            t = " ".join(_run_text(p) for p in fn.iter(W + "p"))
            notes[i] = re.sub(r"\s+", " ", t.replace("‌", "")).strip(" ()")
    return paras, notes


# ---------------------------------------------------------------- علامات التنصيص
QCH = '"“”″'
OPEN_PREV = set(" \t:(،؛[{-—–«") | {""}


def quotes_to_guillemets(paras_text):
    """يحوّل "…" إلى «…» بحسب السياق، مع تتبّع الاقتباس الممتد عبر الفقرات."""
    state_open = False
    out = []
    for t in paras_text:
        s = list(t)
        for i, ch in enumerate(s):
            if ch not in QCH: continue
            j = i - 1
            while j >= 0 and s[j] in "‌‏‎": j -= 1
            prev = s[j] if j >= 0 else ""
            k = i + 1
            while k < len(s) and s[k] in "‌‏‎": k += 1
            nxt = s[k] if k < len(s) else ""
            if ch == "“" and prev in OPEN_PREV: kind = "o"
            elif prev in OPEN_PREV and nxt and not nxt.isspace() and nxt not in ".،؛:)[]" :
                kind = "o"
            elif prev and not prev.isspace() and (not nxt or nxt.isspace() or nxt in ".،؛:)[]!؟?…"):
                kind = "c"
            else:
                # مسافة من الجهتين: يُحسم بما قبلها
                b = "".join(s[:i]).rstrip()
                kind = "o" if (not b or b[-1] in ":،(") and not state_open else ("c" if state_open else "o")
            s[i] = "«" if kind == "o" else "»"
            state_open = kind == "o"
        out.append("".join(s))
    return out
