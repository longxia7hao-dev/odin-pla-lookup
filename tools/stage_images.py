#!/usr/bin/env python3
"""為缺圖條目抓「候選圖」到暫存區 /tmp/img_stage/，供人工逐張檢視後才採用。
來源優先：中文維基（中國裝備照片較全）→ 英文維基。含相關性檢查避免張冠李戴。"""
import json, urllib.request, urllib.parse, os, time, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
UA = "odin-pla-lookup/1.0 (educational; github longxia7hao-dev)"
STAGE = Path("/tmp/img_stage"); STAGE.mkdir(exist_ok=True)
def GET(u, t=15): return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=t)
SKIP = ("flag","icon","logo","symbol","seal","emblem","roundel","ensign","insignia",
        "map","locator","coat_of_arms","commons-logo","edit-icon","ambox","question")
def norm(s): return "".join(c for c in (s or "").lower() if c.isalnum())

def search(host, q):
    u = f"https://{host}/w/api.php?action=query&list=search&format=json&srlimit=4&srsearch=" + urllib.parse.quote(q)
    try:
        d = json.load(GET(u, 12)); return [h["title"] for h in d.get("query", {}).get("search", [])]
    except Exception: return []

def medialist(host, title):
    t = title.replace(" ", "_")
    u = f"https://{host}/api/rest_v1/page/media-list/" + urllib.parse.quote(t, safe="")
    try: d = json.load(GET(u))
    except Exception: return None
    svg = None
    for it in d.get("items", []):
        if it.get("type") != "image" or not it.get("showInGallery", True): continue
        ttl = (it.get("title") or "").lower()
        if any(k in ttl for k in SKIP): continue
        srcs = it.get("srcset") or []
        if not srcs: continue
        src = srcs[-1]["src"]; src = ("https:"+src) if src.startswith("//") else src
        if ttl.endswith(".svg"):
            if svg is None: svg = src
            continue
        return src
    return svg

def relevant(title, item):
    """找到的條目標題要與該裝備相關，避免抓到同名不相干頁。"""
    nt = norm(title)
    desig = norm(item.get("designation", ""))
    if len(desig) >= 4 and desig in nt: return True
    # 中文「NN式」型號數字
    m = re.match(r"(\d{2,3})式", item.get("name_zh", "") or "")
    if m and (m.group(1)+"式") in (title or ""): return True
    if m and m.group(1) in (title or "") and "式" in (title or ""): return True
    # 別名
    for a in (item.get("aliases") or []):
        na = norm(a)
        if len(na) >= 4 and na in nt: return True
    return False

def candidate(item):
    tries = []
    zh = item.get("name_zh", "") or ""
    zh_clean = re.sub(r"[（(].*", "", zh).strip()
    desig = item.get("designation", "")
    # 中文維基
    for q in [desig, zh_clean, zh]:
        if not q.strip(): continue
        for tt in search("zh.wikipedia.org", q):
            if relevant(tt, item):
                img = medialist("zh.wikipedia.org", tt)
                if img: return img, ("zh:"+tt)
    # 英文維基
    for q in [f"{item.get('name_en','')} {desig}", desig]:
        if not q.strip(): continue
        for tt in search("en.wikipedia.org", q):
            if relevant(tt, item):
                img = medialist("en.wikipedia.org", tt)
                if img: return img, ("en:"+tt)
    return None, None

t = open("js/equipment-data.js", encoding="utf-8").read()
arr = json.loads(t[t.index("["):t.rindex("]")+1])
miss = [x for x in arr if not (x.get("image") or "").startswith("assets/")]
report = {}
for i, x in enumerate(miss):
    eid = x["id"]
    try:
        url, srcinfo = candidate(x)
        if not url:
            report[eid] = {"status": "none"}; print(f"[{i+1}/{len(miss)}] {eid} none"); continue
        ext = ".png" if ".png" in url.lower() else ".jpg"
        data = GET(url, 25).read()
        if len(data) < 2500:
            report[eid] = {"status": "tiny"}; continue
        p = STAGE / f"{eid}{ext}"
        p.write_bytes(data)
        report[eid] = {"status": "staged", "file": str(p), "source": srcinfo, "kb": len(data)//1024}
        print(f"[{i+1}/{len(miss)}] {eid} <- {srcinfo} ({len(data)//1024}KB)")
    except Exception as e:
        report[eid] = {"status": "err", "msg": str(e)[:40]}; print(f"[{i+1}/{len(miss)}] {eid} ERR {str(e)[:30]}")
    time.sleep(0.1)
json.dump(report, open("/tmp/img_stage/_report.json", "w"), ensure_ascii=False, indent=2)
staged = sum(1 for v in report.values() if v["status"] == "staged")
print(f"=== staged {staged}/{len(miss)} ===")
