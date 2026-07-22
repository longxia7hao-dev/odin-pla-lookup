#!/usr/bin/env python3
"""為缺圖條目自維基百科抓主圖（REST media-list，取第一張非圖示圖），下載到
assets/images/<id>.<ext>；可續傳。產出 data/downloaded_images.json（id -> 本機路徑）。"""
import json, urllib.request, urllib.parse, os, time, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
UA = "odin-pla-lookup/1.0 (educational OSINT reference; github longxia7hao-dev)"
LOG = open("tools/img_fetch.log", "a", encoding="utf-8")
def log(*a):
    print(*a); print(*a, file=LOG, flush=True)

def GET(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=timeout)

SKIP = ("flag", "icon", "logo", "symbol", "seal", "emblem", "roundel", "ensign",
        "insignia", "map", "locator", "coat_of_arms", "commons-logo", "edit-icon")

def resolve_redirect(title):
    """用 Action API（redirects=1）把重定向標題解析成正式標題（media-list 不跟隨重定向）。"""
    u = ("https://en.wikipedia.org/w/api.php?action=query&redirects=1&format=json&titles="
         + urllib.parse.quote(title))
    try:
        d = json.load(GET(u, 12))
        pages = d.get("query", {}).get("pages", {})
        for _, pg in pages.items():
            if "missing" not in pg:
                return pg.get("title", title)
    except Exception:
        pass
    return title

def medialist_image(title):
    title = resolve_redirect(title)
    u = "https://en.wikipedia.org/api/rest_v1/page/media-list/" + urllib.parse.quote(title.replace(" ", "_"), safe="")
    d = json.load(GET(u))
    svg_fallback = None  # 只有側視線圖時的退路（維基會轉成 PNG）
    for it in d.get("items", []):
        if it.get("type") != "image" or not it.get("showInGallery", True):
            continue
        ttl = (it.get("title") or "").lower()
        if any(k in ttl for k in SKIP):
            continue
        srcs = it.get("srcset") or []
        if not srcs:
            continue
        src = srcs[-1]["src"]  # 取最大倍率
        src = ("https:" + src) if src.startswith("//") else src
        if ttl.endswith(".svg"):
            if svg_fallback is None:
                svg_fallback = src
            continue
        return src  # 優先真實照片
    return svg_fallback

def search_title(query):
    u = ("https://en.wikipedia.org/w/api.php?action=query&list=search&format=json"
         "&srlimit=1&srsearch=" + urllib.parse.quote(query))
    d = json.load(GET(u))
    hits = d.get("query", {}).get("search", [])
    return hits[0]["title"] if hits else None

def _norm(s):
    return "".join(c for c in (s or "").lower() if c.isalnum())

def commons_file_image(query):
    """直接搜 Wikimedia Commons 檔案，回傳第一張合適圖（私有自用；仍過濾旗幟/圖示）。"""
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search"
         "&gsrnamespace=6&gsrlimit=8&gsrsearch=" + urllib.parse.quote(query)
         + "&prop=imageinfo&iiprop=url|size|mime&iiurlwidth=800")
    try:
        d = json.load(GET(u))
    except Exception:
        return None
    pages = list(d.get("query", {}).get("pages", {}).values())
    pages.sort(key=lambda p: p.get("index", 99))
    svg_fb = None
    for pg in pages:
        ttl = (pg.get("title") or "").lower()
        if any(k in ttl for k in SKIP):
            continue
        ii = (pg.get("imageinfo") or [{}])[0]
        mime = ii.get("mime", "")
        if mime and not mime.startswith("image"):
            continue  # 跳過 PDF 等
        url = ii.get("thumburl") or ii.get("url")
        if not url:
            continue
        if ttl.endswith(".svg"):
            if svg_fb is None:
                svg_fb = url
            continue
        return url
    return svg_fb

def titles_from_sources(item):
    """精修時存的 sources 內含正確的英文維基網址，抽出條目標題（最可靠）。"""
    out = []
    for s in item.get("sources", []) or []:
        u = (s or {}).get("url", "") or ""
        m = re.search(r"en\.wikipedia\.org/wiki/([^?#]+)", u)
        if m:
            out.append(urllib.parse.unquote(m.group(1)).replace("_", " "))
    return out

def get_image_url(item):
    # 1) 最可靠：精修 sources 內的正確維基標題
    for t in titles_from_sources(item):
        try:
            u = medialist_image(t)
            if u:
                return u
        except Exception:
            pass
    # 2) 該條目 wiki 欄位（可能是重定向，medialist_image 內會解析）
    wiki = item.get("wiki") or ""
    if wiki:
        try:
            u = medialist_image(wiki)
            if u:
                return u
        except Exception:
            pass
    # 3) 維基搜尋解析正確條目（修正 sources/wiki 標題錯誤，如 Type 83）→ 取前幾筆條目試圖
    desig = item.get("designation", "")
    q = " ".join(x for x in [item.get("name_en", ""), desig, "China"] if x)
    try:
        u = ("https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit=3&srsearch="
             + urllib.parse.quote(q))
        d = json.load(GET(u))
        for h in d.get("query", {}).get("search", []):
            img = medialist_image(h["title"])
            if img:
                return img
    except Exception:
        pass
    # 4) 直接搜 Commons 檔案（私有自用）
    for cq in [f"{desig} China", f"{item.get('name_en','')} {desig}", desig]:
        if cq.strip():
            img = commons_file_image(cq.strip())
            if img:
                return img
    return None

t = open("js/equipment-data.js", encoding="utf-8").read()
arr = json.loads(t[t.index("["):t.rindex("]")+1])
need = [x for x in arr if not (x.get("image") or "").startswith("assets/")]
result_path = ROOT / "data" / "downloaded_images.json"
done = json.load(open(result_path)) if result_path.exists() else {}
ok = 0; fail = 0
for i, x in enumerate(need):
    eid = x["id"]
    if eid in done and (ROOT / done[eid]).exists():
        continue
    try:
        src = get_image_url(x)
        if not src:
            log("no-image", eid, x.get("name_en", "")); fail += 1; continue
        ext = ".png" if ".png" in src.lower() else ".jpg"
        path = f"assets/images/{eid}{ext}"
        data = GET(src, 25).read()
        if len(data) < 2500:
            log("too-small", eid); fail += 1; continue
        open(path, "wb").write(data)
        done[eid] = path
        json.dump(done, open(result_path, "w"), ensure_ascii=False, indent=0)
        ok += 1
        log(f"[{i+1}/{len(need)}] OK", eid, f"{len(data)//1024}KB")
    except Exception as e:
        log("ERR", eid, x.get("name_en", ""), str(e)[:50]); fail += 1
    time.sleep(0.1)
log(f"=== DONE ok={ok} fail={fail} mapped={len(done)} ===")
