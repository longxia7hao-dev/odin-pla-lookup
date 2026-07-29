#!/usr/bin/env python3
"""多來源補圖（教育 OSINT）：中文維基 / 英文維基 / Wikimedia Commons。

不依賴百度百科。規則：
  1) 條目標題或檔名必須與型號關鍵字相符
  2) 拒絕地圖／標誌／書封面／明顯外軍錯配
  3) 圖檔 ≥ 8KB、最短邊 ≥ 140
  4) 寧可缺圖，不可錯圖

用法：
  .venv/bin/python tools/fetch_multisource_images.py
  .venv/bin/python tools/fetch_multisource_images.py --limit 40
  .venv/bin/python tools/fetch_multisource_images.py --ids zbd-08,pl-17
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "assets" / "images"
LOG_PATH = ROOT / "data" / "multisource_image_log.json"
EP_PATH = ROOT / "data" / "specs_enrichment.json"
UA = "odin-pla-lookup/1.1 (educational OSINT; contact via github longxia7hao-dev)"
MIN_BYTES = 8000
MIN_EDGE = 140
MIN_KEEP_EXISTING = 25000

T2S = str.maketrans(
    {
        "驅": "驱", "艦": "舰", "護": "护", "衛": "卫", "潛": "潜", "彈": "弹",
        "導": "导", "戰": "战", "機": "机", "轟": "轰", "運": "运", "預": "预",
        "無": "无", "偵": "侦", "擊": "击", "殲": "歼", "強": "强", "裝": "装",
        "砲": "炮", "槍": "枪", "飛": "飞", "東": "东", "風": "风", "長": "长",
        "劍": "剑", "紅": "红", "級": "级", "陸": "陆", "軍": "军", "進": "进",
        "雙": "双", "載": "载", "兩": "两", "棲": "栖", "補": "补", "給": "给",
        "輕": "轻", "車": "车", "輪": "轮", "後": "后", "單": "单", "練": "练",
        "電": "电", "際": "际", "遠": "远", "發": "发", "號": "号", "龍": "龙",
        "蘇": "苏", "現": "现", "遼": "辽", "寧": "宁", "漢": "汉", "羅": "罗",
        "歐": "欧", "凱": "凯", "島": "岛", "確": "确", "聲": "声", "數": "数",
        "舊": "旧", "種": "种", "隊": "队", "變": "变", "備": "备", "醫": "医",
        "測": "测", "掃": "扫", "鷹": "鹰", "獵": "猎", "衝": "冲", "鋒": "锋",
        "視": "视", "儀": "仪", "揮": "挥", "銷": "销", "歷": "历", "魚": "鱼",
        "雲": "云", "鵬": "鹏", "鬥": "斗", "輸": "输", "襲": "袭", "蹤": "踪",
        "帶": "带", "牽": "牵", "頭": "头", "關": "关", "開": "开", "論": "论",
        "靂": "雳", "砲": "炮",
    }
)

BAD_FILE = (
    "map", "range", "operator", "locator", "chart", "diagram", "graph", "logo",
    "emblem", "seal", "flag", "insignia", "roundel", "cover", "book", "stamp",
    "poster", "table", "skyline", "location", "world", "distribution", "icon",
    "coatofarms", "signature", "qrcode", "barcode",
)

# High-value query overrides: id -> list of (lang_or_source, query)
# lang: zh / en / commons
OVERRIDE_QUERIES: dict[str, list[tuple[str, str]]] = {
    "zbd-08": [("en", "Type 08"), ("zh", "ZBL-08"), ("zh", "08式装甲车族"), ("commons", "ZBL-08")],
    "zsl-10": [("en", "Type 08"), ("zh", "08式装甲车族"), ("commons", "ZBL-08 APC")],
    "plz-05": [("en", "PLZ-05"), ("zh", "PLZ-05自行加榴炮"), ("commons", "PLZ-05")],
    "pcl-181": [("en", "PCL-181"), ("zh", "PCL-181"), ("commons", "SH-15 howitzer"), ("en", "SH-15 howitzer")],
    "pcl-171": [("en", "PCL-171"), ("commons", "PCL-171")],
    "phz-11": [("en", "PHZ-11"), ("zh", "PHZ-11"), ("commons", "PHZ-11")],
    "pgz-04a": [("en", "PGZ-04A"), ("zh", "PGZ-04A"), ("commons", "PGZ-04")],
    "hq-22": [("zh", "红旗-22中远程防空导弹"), ("en", "HQ-22"), ("commons", "HQ-22")],
    "pl-17": [("en", "PL-17"), ("zh", "霹雳-17"), ("commons", "PL-17 missile")],
    "pl-11": [("en", "PL-11"), ("zh", "霹雳-11"), ("commons", "PL-11")],
    "pl-21": [("en", "PL-21"), ("zh", "霹雳-21")],
    "yj-12b": [("en", "YJ-12"), ("zh", "鹰击-12"), ("commons", "YJ-12")],
    "yu-6": [("en", "Yu-6 torpedo"), ("zh", "鱼-6鱼雷")],
    "yu-7": [("en", "Yu-7 torpedo"), ("zh", "鱼-7鱼雷")],
    "df-27": [("en", "DF-27"), ("zh", "东风-27")],
    "df-21c": [("en", "DF-21"), ("zh", "东风-21"), ("commons", "DF-21")],
    "type-096": [("en", "Type 096 submarine"), ("zh", "096型核潜艇")],
    "asn-209": [("en", "ASN-209"), ("zh", "ASN-209")],
    "su-35": [("en", "Sukhoi Su-35"), ("zh", "Su-35戰鬥機"), ("commons", "Su-35")],
    "su-27ubk": [("en", "Sukhoi Su-27"), ("zh", "苏-27战斗机"), ("commons", "Su-27UBK")],
    "h-6k": [("en", "Xian H-6"), ("zh", "轰-6"), ("commons", "H-6K")],
    "type-053h": [("en", "Type 053 frigate"), ("zh", "053H型护卫舰"), ("commons", "Type 053H")],
    "type-053h1g": [("en", "Type 053H1G"), ("zh", "053H1G型护卫舰")],
    "type-053h2g": [("en", "Type 053H2G"), ("zh", "053H2G型护卫舰"), ("commons", "Jiangwei")],
    "type-037is": [("en", "Type 037 corvette"), ("zh", "037型猎潜艇")],
    "type-904": [("en", "Type 904 replenishment"), ("zh", "904型补给舰")],
    "ptl-02": [("en", "PTL-02"), ("zh", "PTL-02"), ("commons", "PTL-02")],
    "sh-15": [("en", "SH-15 howitzer"), ("zh", "SH-15"), ("commons", "SH-15")],
    "z-9d": [("en", "Harbin Z-9"), ("zh", "直-9"), ("commons", "Z-9")],
    "bzk-007": [("en", "BZK-007"), ("zh", "BZK-007")],
    "pll-01": [("en", "PLL-01"), ("zh", "PLL-01")],
    "gcl-111": [("en", "Type 84 AVLB"), ("zh", "84式坦克架桥车"), ("commons", "bridge layer tank China")],
    "type-84-minelayer": [("zh", "84式布雷车"), ("en", "minelayer vehicle China")],
    "pgz-88": [("en", "Type 88 SPAAG"), ("zh", "88式自行高炮")],
    "w85-hmg": [("en", "W85 heavy machine gun"), ("zh", "W85高射机枪")],
    "qlg-10": [("en", "QLG-10"), ("zh", "QLG-10")],
    "pp-89": [("zh", "100毫米迫击炮"), ("en", "Type 89 mortar")],
    "phl-11": [("en", "PHL-11"), ("zh", "PHL-11")],
    "gb-6": [("en", "GB-6 bomb"), ("zh", "GB-6")],
    "cs-sm1": [("en", "CS/SM1"), ("zh", "CS/SM1")],
    "type-024": [("en", "Type 024 missile boat"), ("zh", "024型导弹艇")],
    "type-909": [("zh", "909型试验舰"), ("en", "Type 909")],
    "type-925": [("zh", "925型潜艇支援舰"), ("en", "Type 925")],
    "fb-6c": [("en", "FN-6"), ("zh", "飞弩-6")],  # family photo only if no better
    "hj-11": [("en", "HJ-11"), ("zh", "红箭-11")],
    "ls-500j": [("zh", "雷石制导炸弹"), ("en", "LS-6 bomb")],
    "yj-18b": [("en", "YJ-18"), ("zh", "鹰击-18"), ("commons", "YJ-18")],
    "hpj-38": [("en", "H/PJ-38"), ("zh", "H/PJ-38"), ("commons", "130mm naval gun China")],
    "type-60-122": [("zh", "60式122毫米加农炮"), ("en", "Type 60 122 mm")],
    "type-67-82": [("zh", "67式82毫米迫击炮"), ("en", "Type 67 mortar")],
    "df-4": [("en", "DF-4"), ("zh", "东风-4"), ("commons", "DF-4")],
}


def to_s(t: str) -> str:
    return (t or "").translate(T2S)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def clean_name(n: str) -> str:
    return re.sub(r"[（(].*?[）)]", "", n or "").replace("／", "/").strip()


def http_get(url: str, timeout: int = 30, retries: int = 5) -> bytes:
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": UA,
                    "Accept": "application/json,image/*,*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 503, 502):
                wait = 8 * (i + 1) + (3 * i)
                print(f"    HTTP {e.code}, sleep {wait}s", flush=True)
                time.sleep(wait)
                continue
            raise
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise last  # type: ignore


def http_json(url: str) -> dict:
    return json.loads(http_get(url).decode("utf-8", errors="replace"))


def local_size(eid: str) -> int:
    best = 0
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = IMG / f"{eid}{ext}"
        if p.exists():
            best = max(best, p.stat().st_size)
    return best


# id-specific extra tokens for filename matching
EXTRA_TOKS = {
    "zbd-08": {"zbl08", "zbd08", "type08", "08式"},
    "zsl-10": {"zsl10", "zbl08", "type08"},
    "pcl-181": {"pcl181", "sh15", "sh-15"},
    "sh-15": {"sh15", "pcl181"},
    "yj-12b": {"yj12", "yj12b", "yingji12"},
    "yj-18b": {"yj18", "yingji18"},
    "su-35": {"su35", "sukhoi"},
    "su-27ubk": {"su27", "su27ubk"},
    "h-6k": {"h6k", "h6", "xianh6"},
    "type-053h": {"053h", "type053", "jianghu"},
    "type-053h2g": {"053h2g", "jiangwei"},
    "type-053h1g": {"053h1g", "jianghu"},
    "gcl-111": {"type84", "84式", "avlb", "bridgelayer"},
    "pgz-88": {"type88", "pgz88", "88式"},
    "phz-11": {"phz11", "type11"},
    "plz-05": {"plz05", "type05"},
}


def tokens_for(item: dict) -> set[str]:
    src = [item.get("designation", ""), item.get("name_en", ""), item.get("id", "")]
    src += list(item.get("aliases") or [])
    out: set[str] = set()
    for s in src:
        n = norm(s)
        if len(n) >= 3:
            out.add(n)
        for m in re.findall(r"[a-zA-Z]{1,5}[-\s]?\d{1,4}[a-zA-Z]{0,3}", str(s)):
            n2 = norm(m)
            if len(n2) >= 3:
                out.add(n2)
        for m in re.findall(r"\b\d{2,4}[a-zA-Z]{0,2}\b", str(s)):
            if len(m) >= 3:
                out.add(norm(m))
    name = to_s(clean_name(item.get("name_zh") or ""))
    for m in re.findall(
        r"(歼|轰|运|直|空警|东风|鹰击|红旗|霹雳|巨浪|彩虹|红箭|飞弩|前卫|鱼)[-]?\d+[A-Za-z]?",
        name,
    ):
        out.add(norm(m))
        out.add(m)
    eid = item.get("id") or ""
    out |= EXTRA_TOKS.get(eid, set())
    # drop overly short pure numbers that cause false hits (unless 3+ digit model)
    cleaned = set()
    for t in out:
        if t.isdigit() and len(t) < 3:
            continue
        if t in ("type", "china", "chinese", "pla", "plan", "plaaf", "series", "class", "mod"):
            continue
        cleaned.add(t)
    return cleaned


def zh_keys(item: dict) -> list[str]:
    """Chinese keywords that should appear in zh wiki title/summary."""
    name = to_s(clean_name(item.get("name_zh") or ""))
    keys = []
    des = item.get("designation") or ""
    for m in re.findall(r"([A-Za-z]{1,5})-?(\d{1,4}[A-Za-z]{0,2})", des):
        pref, num = m[0].upper(), m[1].upper()
        cmap = {
            "J": "歼-", "JH": "歼轰-", "H": "轰-", "Y": "运-", "Z": "直-",
            "KJ": "空警-", "DF": "东风-", "YJ": "鹰击-", "HQ": "红旗-",
            "PL": "霹雳-", "JL": "巨浪-", "CH": "彩虹-", "HJ": "红箭-",
            "FN": "飞弩-", "QW": "前卫-", "WZ": "无侦-", "GJ": "攻击-",
            "CJ": "长剑-", "HHQ": "海红旗-", "SU": "苏-",
        }
        if pref in cmap:
            keys.append(f"{cmap[pref]}{num}")
            keys.append(f"{cmap[pref]}{num}".replace("-", ""))
        keys.append(f"{pref}-{num}")
        keys.append(f"{pref}{num}")
    m = re.match(r"Type\s*([0-9]{2,4}[A-Za-z]*)", des, re.I)
    if m:
        keys.append(m.group(1))
        keys.append(f"{m.group(1)}型")
        keys.append(f"{m.group(1)}式")
    core = re.sub(r"[A-Za-z0-9\-_\s/]", "", name)
    if len(core) >= 2:
        keys.append(core[:4])
    # id fragments
    eid = item.get("id") or ""
    keys.append(eid.replace("-", ""))
    return [k for k in dict.fromkeys(keys) if k and len(k) >= 2]


GENERIC_TITLES = {
    "多管火箭炮", "自行加榴炮", "防空导弹", "空空导弹", "鱼雷", "巡航导弹",
    "步兵战车", "装甲输送车", "扫雷车", "布雷车", "架桥坦克", "智能炸弹",
    "东风猛士", "SCP基金会", "火箭炮", "迫击炮", "高射炮",
}


def title_matches(title: str, item: dict, toks: set[str], keys: list[str]) -> bool:
    """Strict: model token/number must appear; reject generic/wrong pages."""
    t = title or ""
    tl = t.lower()
    tn = norm(t)
    ts = to_s(t)
    if any(b in tn for b in BAD_FILE):
        return False
    junk = ["游戏", "电影", "小说", "演员", "公司", "大学", "公路", "车站", "基金会", "猛士"]
    if any(j in ts for j in junk):
        return False
    if ts.strip() in GENERIC_TITLES or t.strip() in GENERIC_TITLES:
        return False
    # Extract significant model numbers from designation/id (e.g. 08, 21C, 181)
    des = item.get("designation") or ""
    eid = item.get("id") or ""
    model_nums = set(re.findall(r"\d{2,4}[A-Za-z]{0,2}", des + " " + eid, flags=re.I))
    model_nums = {m.lower() for m in model_nums if len(m) >= 2}

    # Must hit at least one strong token (len>=4) OR (token len>=3 AND model num in title)
    strong = [tok for tok in toks if len(tok) >= 4]
    for tok in strong:
        if tok in tn:
            # if we have model nums, prefer title also containing one
            if model_nums and not any(n in tn for n in model_nums):
                # allow chinese name pages like 鹰击12 without latin
                if any(k in ts for k in keys if re.search(r"\d", k)):
                    return True
                continue
            return True
    for k in keys:
        kn = norm(k)
        if len(kn) >= 4 and (k in ts or kn in tn or k.lower() in tl):
            return True
        if len(k) >= 3 and k in ts and any(n in tn or n in ts.lower() for n in model_nums):
            return True
    # Type NNN pages: title contains Type 0xx and matches item type code
    m = re.search(r"type\s*([0-9]{2,4}[a-z]*)", tl)
    if m:
        code = m.group(1)
        if code in tn or any(code in n for n in model_nums) or code in norm(des) or code in norm(eid):
            # reject if title is different type family (Type 08 when we want Type 88)
            want = re.findall(r"\d{2,4}[a-z]{0,2}", norm(des) + norm(eid))
            if want and not any(w in code or code in w for w in want):
                return False
            return True
    return False


def wiki_search(lang: str, query: str, limit: int = 6) -> list[str]:
    base = f"https://{lang}.wikipedia.org/w/api.php"
    url = base + "?" + urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }
    )
    try:
        j = http_json(url)
        return [x["title"] for x in j.get("query", {}).get("search", [])]
    except Exception:
        return []


def wiki_pageimage(lang: str, title: str) -> tuple[str | None, str | None, str | None]:
    """Return (filename, url, resolved_title)."""
    base = f"https://{lang}.wikipedia.org/w/api.php"
    url = base + "?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": title,
            "prop": "pageimages|info",
            "pithumbsize": 1400,
            "piprop": "thumbnail|name|original",
            "redirects": 1,
            "format": "json",
            "utf8": 1,
        }
    )
    try:
        j = http_json(url)
        pages = j.get("query", {}).get("pages", {})
        for _, pg in pages.items():
            if "missing" in pg:
                return None, None, None
            rtitle = pg.get("title") or title
            name = pg.get("pageimage")
            src = None
            if pg.get("original"):
                src = pg["original"].get("source")
            if not src and pg.get("thumbnail"):
                src = pg["thumbnail"].get("source")
            if name and src:
                return name, src, rtitle
    except Exception:
        pass
    return None, None, None


def wiki_page_images(lang: str, title: str, limit: int = 8) -> list[tuple[str, str]]:
    """List images used on page with URLs."""
    base = f"https://{lang}.wikipedia.org/w/api.php"
    url = base + "?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": title,
            "prop": "images",
            "imlimit": limit,
            "redirects": 1,
            "format": "json",
            "utf8": 1,
        }
    )
    out = []
    try:
        j = http_json(url)
        pages = j.get("query", {}).get("pages", {})
        titles = []
        for _, pg in pages.items():
            for im in pg.get("images") or []:
                ft = im.get("title") or ""
                if ft.lower().startswith("file:"):
                    titles.append(ft)
        if not titles:
            return []
        # batch imageinfo
        url2 = base + "?" + urllib.parse.urlencode(
            {
                "action": "query",
                "titles": "|".join(titles[:limit]),
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
                "iiurlwidth": 1400,
                "format": "json",
                "utf8": 1,
            }
        )
        j2 = http_json(url2)
        for _, pg in j2.get("query", {}).get("pages", {}).items():
            ii = (pg.get("imageinfo") or [{}])[0]
            u = ii.get("thumburl") or ii.get("url")
            fn = (pg.get("title") or "").replace("File:", "").replace("檔案:", "")
            if u and fn:
                out.append((fn, u))
    except Exception:
        pass
    return out


def commons_search(query: str, limit: int = 12) -> list[str]:
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srnamespace": 6,
            "srlimit": limit,
            "srsearch": query,
            "format": "json",
        }
    )
    try:
        j = http_json(url)
        return [h["title"].replace("File:", "") for h in j.get("query", {}).get("search", [])]
    except Exception:
        return []


def commons_url(filename: str, width: int = 1400) -> str | None:
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
        {
            "action": "query",
            "titles": "File:" + filename,
            "prop": "imageinfo",
            "iiprop": "url|size",
            "iiurlwidth": width,
            "format": "json",
        }
    )
    try:
        j = http_json(url)
        for _, pg in j.get("query", {}).get("pages", {}).items():
            ii = (pg.get("imageinfo") or [{}])[0]
            return ii.get("thumburl") or ii.get("url")
    except Exception:
        pass
    return None


def file_ok(filename: str, toks: set[str]) -> bool:
    n = norm(filename)
    if any(b in n for b in BAD_FILE):
        return False
    if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff")):
        return False
    # require a token of length >= 4, or two overlapping model signals
    hits = [t for t in toks if len(t) >= 3 and t in n]
    if any(len(t) >= 4 for t in hits):
        return True
    return len(hits) >= 2


def save_image(data: bytes, dest: Path) -> bool:
    if len(data) < MIN_BYTES:
        return False
    try:
        im = Image.open(BytesIO(data)).convert("RGB")
        if min(im.size) < MIN_EDGE:
            return False
        # reject tiny logo-like squares
        if im.size[0] == im.size[1] and im.size[0] <= 400 and len(data) < 40000:
            return False
        if max(im.size) > 1600:
            im.thumbnail((1600, 1600))
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=90, optimize=True)
        return dest.stat().st_size >= MIN_BYTES
    except Exception:
        return False


def build_queries(item: dict) -> list[tuple[str, str]]:
    eid = item["id"]
    qs: list[tuple[str, str]] = []
    if eid in OVERRIDE_QUERIES:
        qs.extend(OVERRIDE_QUERIES[eid])
    des = (item.get("designation") or "").strip()
    name_en = (item.get("name_en") or "").strip()
    name_zh = to_s(clean_name(item.get("name_zh") or ""))
    if des:
        qs.append(("en", des))
        qs.append(("commons", des))
        qs.append(("zh", des))
    if name_en and name_en != des:
        qs.append(("en", name_en))
        qs.append(("commons", name_en))
    if name_zh:
        qs.append(("zh", name_zh))
    # Type NNN style
    m = re.match(r"Type\s*([0-9]{2,4}[A-Za-z]*)", des, re.I)
    if m:
        code = m.group(1)
        qs.append(("zh", f"{code}型"))
        qs.append(("zh", f"{code}式"))
        qs.append(("en", f"Type {code}"))
        qs.append(("commons", f"Type {code}"))
    # dedupe preserve order
    seen = set()
    out = []
    for src, q in qs:
        key = (src, q)
        if key not in seen and q:
            seen.add(key)
            out.append((src, q))
    return out[:14]


def try_download(url: str, dest: Path) -> bool:
    try:
        data = http_get(url, timeout=35)
        return save_image(data, dest)
    except Exception as e:
        print(f"    dl fail: {e}", flush=True)
        return False


def fetch_one(item: dict, log: dict) -> dict:
    eid = item["id"]
    toks = tokens_for(item)
    keys = zh_keys(item)
    dest = IMG / f"{eid}.jpg"
    print(f"  toks={list(toks)[:8]} keys={keys[:6]}", flush=True)

    for src, q in build_queries(item):
        print(f"  try {src}: {q}", flush=True)
        if src in ("zh", "en"):
            titles = wiki_search(src, q)
            time.sleep(0.25)
            for title in titles:
                if not title_matches(title, item, toks, keys):
                    print(f"    skip title {title[:50]}", flush=True)
                    continue
                # pageimage first
                fname, url, rtitle = wiki_pageimage(src, title)
                time.sleep(0.2)
                candidates: list[tuple[str, str, str]] = []
                if fname and url:
                    candidates.append((fname, url, rtitle or title))
                # more images on page
                for fn, u in wiki_page_images(src, title, limit=6):
                    candidates.append((fn, u, rtitle or title))
                for fn, u, rt in candidates:
                    n = norm(fn)
                    if any(b in n for b in BAD_FILE):
                        continue
                    ok_file = file_ok(fn, toks)
                    ok_title = title_matches(rt, item, toks, keys)
                    # Require title match; filename match preferred for non-pageimage bulk
                    if not ok_title:
                        continue
                    if not ok_file:
                        # only allow pageimage (first candidate) without filename token
                        # when title is strong (contains model digits)
                        des = item.get("designation") or ""
                        nums = re.findall(r"\d{2,4}[A-Za-z]{0,2}", des + item["id"], flags=re.I)
                        if not nums or not any(num.lower() in n or num.lower() in norm(rt) for num in nums):
                            if not any(len(t) >= 5 and t in n for t in toks):
                                # still allow exact zh title pageimage
                                if src != "zh" or not any(k in (rt or "") for k in keys if len(k) >= 4):
                                    continue
                    if try_download(u, dest):
                        res = {
                            "ok": True,
                            "source": f"wikipedia_{src}",
                            "title": rt,
                            "file": fn,
                            "query": q,
                            "path": f"assets/images/{eid}.jpg",
                            "bytes": dest.stat().st_size,
                        }
                        log[eid] = res
                        print(f"    OK wiki {src} {rt} / {fn[:40]} ({dest.stat().st_size})", flush=True)
                        return res
                time.sleep(0.6)
        elif src == "commons":
            files = commons_search(q)
            time.sleep(0.6)
            for fn in files:
                if not file_ok(fn, toks):
                    print(f"    skip file {fn[:50]}", flush=True)
                    continue
                u = commons_url(fn)
                if not u:
                    continue
                if try_download(u, dest):
                    res = {
                        "ok": True,
                        "source": "commons",
                        "title": fn,
                        "file": fn,
                        "query": q,
                        "path": f"assets/images/{eid}.jpg",
                        "bytes": dest.stat().st_size,
                    }
                    log[eid] = res
                    print(f"    OK commons {fn[:60]} ({dest.stat().st_size})", flush=True)
                    return res
                time.sleep(0.5)

    res = {"ok": False, "reason": "no_match", "queries": [f"{a}:{b}" for a, b in build_queries(item)[:8]]}
    log[eid] = res
    print("    FAIL", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", type=str, default="")
    args = ap.parse_args()

    text = (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8")
    items = json.loads(text[text.index("[") : text.rindex("]") + 1])
    log = json.loads(LOG_PATH.read_text(encoding="utf-8")) if LOG_PATH.exists() else {}

    targets = []
    only = set(args.ids.split(",")) if args.ids else None
    for it in items:
        eid = it["id"]
        if only and eid not in only:
            continue
        sz = local_size(eid)
        if sz >= MIN_KEEP_EXISTING:
            continue
        targets.append(it)
    # prioritize none over tiny, and override ids
    def score(it):
        s = 0 if local_size(it["id"]) == 0 else 1
        if it["id"] in OVERRIDE_QUERIES:
            s -= 5
        return (s, it["id"])

    targets.sort(key=score)
    if args.limit:
        targets = targets[: args.limit]

    print(f"targets={len(targets)}", flush=True)
    ok = fail = 0
    for i, it in enumerate(targets, 1):
        eid = it["id"]
        print(f"\n[{i}/{len(targets)}] {eid} | {it.get('name_zh')}", flush=True)
        # skip if already ok this run with decent file
        if local_size(eid) >= MIN_KEEP_EXISTING:
            continue
        try:
            res = fetch_one(it, log)
            if res.get("ok"):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  ERR {e}", flush=True)
            log[eid] = {"ok": False, "reason": str(e)[:200]}
            fail += 1
        if i % 3 == 0:
            LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(1.2)  # be gentle to Wikimedia

    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    # enrich
    ep = json.loads(EP_PATH.read_text(encoding="utf-8")) if EP_PATH.exists() else {"items": {}}
    n = 0
    for eid, res in log.items():
        if not res.get("ok") or not res.get("path"):
            continue
        p = ROOT / res["path"]
        if not p.exists() or p.stat().st_size < MIN_BYTES:
            continue
        ent = ep.setdefault("items", {}).setdefault(eid, {})
        ent["image"] = res["path"]
        src = res.get("source", "multi")
        title = res.get("title") or eid
        if src.startswith("wikipedia"):
            ent["image_credit"] = f"图片来自维基百科《{title}》（教育参考）"
        elif src == "commons":
            ent["image_credit"] = f"图片来自 Wikimedia Commons《{title}》（教育参考）"
        else:
            ent["image_credit"] = f"公开百科图片《{title}》（教育参考）"
        n += 1
    EP_PATH.write_text(json.dumps(ep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDONE ok={ok} fail={fail} enrich={n}", flush=True)


if __name__ == "__main__":
    main()
