#!/usr/bin/env python3
"""Wikimedia Commons 搜尋版抓圖：突破「條目沒有指定主圖」的限制。

維基條目常常沒有 pageimage，但 Commons 檔案庫裡有照片。
本工具直接搜尋 Commons 檔案，並沿用嚴格規則：
  1) 檔名必須含該裝備型號（杜絕張冠李戴）
  2) 檔名不得含 map/chart/logo 等圖表關鍵字
  3) 優先照片（.jpg/.png），線稿 .svg 僅在無照片時採用
抓不到就留占位——寧可沒圖，不可錯圖。
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = "odin-pla-lookup/1.0 (educational OSINT reference; github longxia7hao-dev)"
OUT = ROOT / "data" / "commons_images.json"
LOG = open(ROOT / "tools" / "img_commons.log", "a", encoding="utf-8")

# 沿用嚴格版的 token / 檔名規則
_src = (ROOT / "tools" / "fetch_images_strict.py").read_text(encoding="utf-8").split("def pageimage")[0]
_ns = {"__file__": str(ROOT / "tools" / "fetch_images_strict.py")}
exec(_src, _ns)
norm, tokens_for, BAD_WORDS = _ns["norm"], _ns["tokens_for"], _ns["BAD_WORDS"]


def log(*a):
    print(*a)
    print(*a, file=LOG, flush=True)


def GET(url, timeout=25, tries=5):
    last = None
    for i in range(tries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout)
        except Exception as e:
            last = e
            if getattr(e, "code", None) in (429, None):
                time.sleep(6 * (i + 1))
                continue
            raise
    raise last


def commons_search(query, limit=15):
    """搜尋 Commons 檔案，回傳 [檔名]。"""
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search"
         f"&srnamespace=6&srlimit={limit}&srsearch=" + urllib.parse.quote(query))
    try:
        d = json.load(GET(u, 20))
        return [h["title"].replace("File:", "") for h in d.get("query", {}).get("search", [])]
    except Exception as e:
        log("  搜尋失敗", query, str(e)[:50])
        return []


def image_url(filename, width=1400):
    """取得檔案的下載網址（縮至指定寬度，省流量）。"""
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=imageinfo"
         f"&iiprop=url|size&iiurlwidth={width}&titles=" + urllib.parse.quote("File:" + filename))
    try:
        d = json.load(GET(u, 20))
        for _, pg in d.get("query", {}).get("pages", {}).items():
            ii = (pg.get("imageinfo") or [{}])[0]
            return ii.get("thumburl") or ii.get("url")
    except Exception:
        pass
    return None


# 必須「整個詞」出現，不能用子字串（"pla" 會誤中 display/place，"plan" 誤中 plane）
CHINA_WORDS = (r"\bchina\b", r"\bchinese\b", r"\bprc\b", r"\bplaaf\b", r"\bplan\b",
               r"\bpla\b", r"people'?s\s+liberation", r"\bnorinco\b", r"\bcasc\b",
               r"\bcatic\b", r"\bavic\b", r"中国", r"中國", r"解放軍", r"解放军",
               r"人民海軍", r"人民海军")
# 明顯不是裝備照的檔案類型（Commons 有大量老檔案掃描件）
EXTRA_BAD = ("conveyances", "watercraft-", "ships-boats", "hydria", "statuette",
             "peugeot", "autorail", "cemetery", "lachaise", "building", "platz",
             "prototyp", "warhead", "abrams", "heinkel")


def is_china_related(filename):
    """查該檔案的分類，必須與中國／解放軍相關（詞邊界比對），避免同名外國事物。"""
    n = filename.lower()
    if any(b in n.replace(" ", "").replace("_", "") for b in EXTRA_BAD):
        return False
    u = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&prop=categories"
         "&cllimit=80&titles=" + urllib.parse.quote("File:" + filename))
    try:
        d = json.load(GET(u, 20))
        for _, pg in d.get("query", {}).get("pages", {}).items():
            cats = " ".join(c.get("title", "") for c in (pg.get("categories") or []))
            low = cats.lower()
            return any(re.search(w, low) for w in CHINA_WORDS)
    except Exception:
        pass
    return False


def queries_for(item):
    """產生搜尋詞：型號 + 名稱 + 類別關鍵字。"""
    desig = item.get("designation", "")
    en = item.get("name_en", "")
    sub = item.get("subcategory", "")
    hint = {
        "warship": "ship", "submarine": "submarine", "aircraft_fighter": "aircraft",
        "aircraft_bomber": "bomber", "helicopter": "helicopter", "mbt": "tank",
        "ifv": "vehicle", "sph": "howitzer", "mlrs": "rocket launcher",
        "sam": "missile", "asm": "missile", "aam": "missile", "ballistic": "missile",
        "uav": "UAV drone", "amphibious_ship": "landing ship", "auxiliary": "ship",
    }.get(sub, "")
    qs = []
    if desig:
        qs.append(f"{desig} {hint}".strip())
        qs.append(desig)
    if en and en != desig:
        qs.append(f"{en} {hint}".strip())
    return list(dict.fromkeys([q for q in qs if q]))


def pick(files, toks):
    """依規則挑出合格檔名：先照片、後線稿。"""
    photo = svg = None
    for f in files:
        n = norm(f)
        if any(b in n for b in BAD_WORDS):
            continue
        if not any(tk in n for tk in toks):
            continue
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            photo = photo or f
    return photo


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    limit_n = None
    if "--limit" in sys.argv:
        limit_n = int(sys.argv[sys.argv.index("--limit") + 1])

    t = (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8")
    arr = json.loads(t[t.index("["):t.rindex("]") + 1])
    done = json.loads(OUT.read_text()) if OUT.exists() else {}

    # 只處理「目前沒有圖」的項目
    targets = [x for x in arr if not (x.get("image") or "").startswith("assets/")]
    if only:
        targets = [x for x in targets if x["id"] in only]
    if limit_n:
        targets = targets[:limit_n]
    log(f"=== Commons 搜尋抓圖：目標 {len(targets)} 筆 ===")

    ok = miss = err = 0
    for i, item in enumerate(targets, 1):
        eid = item["id"]
        if eid in done and (ROOT / done[eid]["path"]).exists():
            continue
        toks = tokens_for(item)
        chosen = None
        for q in queries_for(item):
            files = commons_search(q)
            time.sleep(0.4)
            f = pick(files, toks)
            if f and not is_china_related(f):
                log(f"  ✗非中國相關 {eid}: {f[:50]}")
                time.sleep(0.3)
                f = None
            if f:
                chosen = (q, f)
                break
        if not chosen:
            miss += 1
            continue
        q, fname = chosen
        url = image_url(fname)
        if not url:
            err += 1
            continue
        try:
            data = GET(url, 30).read()
            if len(data) < 3000:
                miss += 1
                continue
            ext = ".png" if fname.lower().endswith((".png", ".svg")) else ".jpg"
            path = f"assets/images/{eid}{ext}"
            (ROOT / path).write_bytes(data)
            done[eid] = {"path": path, "file": fname, "query": q}
            OUT.write_text(json.dumps(done, ensure_ascii=False, indent=0), encoding="utf-8")
            ok += 1
            log(f"[{i}/{len(targets)}] ✓ {eid} ← {fname[:60]}")
        except Exception as e:
            err += 1
            log(f"  下載失敗 {eid}: {str(e)[:50]}")
        time.sleep(0.9)

    log(f"=== 完成 ok={ok} 無合格圖={miss} 錯誤={err} 累計={len(done)} ===")


if __name__ == "__main__":
    main()
