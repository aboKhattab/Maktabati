# -*- coding: utf-8 -*-
"""يدمج بطاقات كل الكتب في data.json مضغوط للواجهة.

- بطاقات «الجامع في الخشوع» تحتفظ بأرقامها (1..N) كي لا تضيع العلامات السابقة.
- النص المكرر بين الكتب يُدمج في بطاقة واحدة لها عدة مواضع.
الاستعمال: python3 pack.py cards.json books.json data.json
"""
import json, re, sys


def norm(t):
    t = re.sub(r"[ً-ْٰـ]", "", t)
    t = re.sub(r"[إأآٱ]", "ا", t).replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    t = re.sub(r"[^ء-ي\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

KHUSHU, BOOKS, OUT = sys.argv[1:4]
PREV = sys.argv[4] if len(sys.argv) > 4 else None   # data.json السابق: لتثبيت أرقام البطاقات
KIND = {"حديث مرفوع": "h", "أثر صحابي": "s", "أثر عن السلف": "a", "قول عالم": "q", "نقل": "n", "شعر": "p"}

kh = json.load(open(KHUSHU, encoding="utf-8"))
others = json.load(open(BOOKS, encoding="utf-8"))
books = [{"t": kh["book"], "a": kh["author"]}] + [{"t": b["book"], "a": b["author"]} for b in others]


def toks(t):
    return set(w for w in norm(t).split() if len(w) > 2)


cards = []
def add(c, b):
    tk = toks(c["text"])
    for L in c["locations"]: L["book"] = b
    if len(tk) >= 5 and c["kind"] != "شعر":
        for d in cards:
            if d["kind"] == "شعر": continue
            inter = len(tk & d["_tk"])
            if not inter: continue
            small, big = min(len(tk), len(d["_tk"])), max(len(tk), len(d["_tk"]))
            if inter / small >= 0.85 and inter / big >= 0.6 and inter >= 5 and (c["kind"] == d["kind"] or "نقل" in (c["kind"], d["kind"])):
                d["locations"] += c["locations"]
                for s in c["sources"]:
                    if s not in d["sources"]: d["sources"].append(s)
                if not d["grade"] and c["grade"]: d["grade"], d["hukm"] = c["grade"], c["hukm"]
                if d["kind"] == "نقل" and c["kind"] != "نقل": d["kind"], d["speaker"] = c["kind"], c["speaker"]
                if not d["speaker"] and c["speaker"]: d["speaker"] = c["speaker"]
                if not d.get("narrator") and c.get("narrator"): d["narrator"] = c["narrator"]
                return False
    c["_tk"] = tk
    cards.append(c)
    return True

def key(t):
    return re.sub(r"\s+", " ", norm(t).replace("صلي الله عليه وسلم", " ")).strip()


prev_ids = {}
if PREV:
    for r in json.load(open(PREV, encoding="utf-8"))["cards"]:
        prev_ids.setdefault(key(r[4]), r[0])
for c in kh["cards"]: add(c, 0)
merged = 0
for bi, b in enumerate(others, 1):
    for c in b["cards"]:
        c["id"] = None
        if not add(c, bi): merged += 1
used = {c["id"] for c in cards if c["id"] is not None}
for c in cards:
    if c["id"] is None:
        pid = prev_ids.get(key(c["text"]))
        if pid and pid not in used: c["id"] = pid; used.add(pid)
next_id = max(max(used), max(prev_ids.values(), default=0)) + 1
for c in cards:
    if c["id"] is None: c["id"] = next_id; next_id += 1
kept = sum(1 for c in cards if prev_ids.get(key(c["text"])) == c["id"])
print("ids kept from previous version:", kept, "of", len(prev_ids))

paths, pidx = [], {}
def path_id(L):
    key = json.dumps([L["book"]] + L["path"], ensure_ascii=False)
    if key not in pidx:
        pidx[key] = len(paths); paths.append([L["book"]] + L["path"])
    return pidx[key]

rows = []
for c in cards:
    locs = []
    for L in c["locations"]:
        i = path_id(L)
        if i not in locs: locs.append(i)
    rows.append([c["id"], KIND[c["kind"]], c["speaker"], c.get("narrator", ""), c["text"], c.get("intro", ""),
                 c["grade"], c["hukm"], c["sources"], locs, 1 if c.get("riwaya") else 0])

json.dump({"books": books, "paths": paths, "cards": rows}, open(OUT, "w", encoding="utf-8"),
          ensure_ascii=False, separators=(",", ":"))
multi = sum(1 for c in cards if len({L["book"] for L in c["locations"]}) > 1)
print("cards:", len(rows), "merged:", merged, "in >1 book:", multi, "paths:", len(paths))
