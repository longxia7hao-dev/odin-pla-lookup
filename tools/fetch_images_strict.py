#!/usr/bin/env python3
"""嚴格抓圖：只採用維基「指定主圖」(pageimage)，且**檔名必須含該裝備型號**。
兩道關卡杜絕地圖／射程圖／書封面／張冠李戴／家族共用圖。
抓不到就留占位——寧可沒圖，不可錯圖。

用法：python3 tools/fetch_images_strict.py [--only id1,id2]
產出：assets/images/<id>.jpg + data/strict_images.json（id -> {path, file, title}）
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = "odin-pla-lookup/1.0 (educational OSINT reference; github longxia7hao-dev)"
OUT = ROOT / "data" / "strict_images.json"
LOG = open(ROOT / "tools" / "img_strict.log", "a", encoding="utf-8")


def log(*a):
    print(*a)
    print(*a, file=LOG, flush=True)


def GET(url, timeout=20):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout
    )


def norm(s):
    """只留英數小寫，供比對用。"""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# 檔名一看就知道不是裝備照的
BAD_WORDS = ("map", "range", "operator", "locator", "chart", "diagram", "graph",
             "logo", "emblem", "seal", "flag", "insignia", "roundel", "coverbook",
             "cover", "book", "stamp", "poster", "chart", "table", "skyline",
             "location", "world", "distribution")


# 維基檔名常用英文別名（HJ-10 的檔名可能寫 Red_Arrow_10）
PREFIX_ALIASES = {
    "hj": ["redarrow", "hongjian"],
    "hq": ["hongqi", "redflag"],
    "hhq": ["hongqi", "redflag"],
    "pl": ["pili", "thunderbolt"],
    "yj": ["yingji", "eaglestrike"],
    "df": ["dongfeng", "eastwind"],
    "jl": ["julang", "bigwave"],
    "fn": ["feinu"],
    "qw": ["qianwei", "vanguard"],
    "wz": ["wuzhen"],
    "gj": ["gongji"],
    "cj": ["changjian", "longsword"],
    "pf": ["pofang"],
    "ztz": ["type"],
    "ztq": ["type"],
    "zbd": ["type"],
    "zbl": ["type"],
    "zsl": ["type"],
    "zsd": ["type"],
}


def tokens_for(item):
    """可接受的型號 token（長度>=3），檔名須含其一。"""
    src = [item.get("designation", ""), item.get("name_en", ""), item.get("id", "")]
    src += list(item.get("aliases") or [])
    out = set()
    # 由前綴+數字生成英文別名 token，例：HJ-10 → redarrow10 / hongjian10
    for s in src:
        m = re.match(r"^\s*([a-zA-Z]{1,4})[-\s]?(\d{1,3}[a-zA-Z]{0,2})\s*$", str(s))
        if m:
            pre, num = m.group(1).lower(), norm(m.group(2))
            for alt in PREFIX_ALIASES.get(pre, []):
                out.add(alt + num)
    for s in src:
        n = norm(s)
        if len(n) >= 3:
            out.add(n)
        # 「Type 052D」→ 也接受 052d；「DF-5」→ df5
        for m in re.findall(r"[a-zA-Z]{1,4}[-\s]?\d{1,4}[a-zA-Z]{0,3}", str(s)):
            n2 = norm(m)
            if len(n2) >= 3:
                out.add(n2)
        for m in re.findall(r"\b\d{3,4}[a-zA-Z]{0,2}\b", str(s)):
            if len(m) >= 3:
                out.add(norm(m))
    # 過於通用的 token 會誤放行
    return {t for t in out if t not in ("type", "china", "chinese", "pla", "plan", "plaaf")}


def pageimage(title):
    """回傳 (檔名, 原圖URL) —— 維基指定主圖；沒有就 (None, None)。"""
    u = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1"
         "&prop=pageimages&piprop=original|name&titles=" + urllib.parse.quote(title))
    try:
        d = json.load(GET(u, 15))
        for _, pg in d.get("query", {}).get("pages", {}).items():
            if "missing" in pg:
                return None, None
            name = pg.get("pageimage")
            src = (pg.get("original") or {}).get("source", "")
            if name and src:
                return name, src
    except Exception as e:
        log("  api-err", title, str(e)[:60])
    return None, None


def wiki_titles(item):
    """候選條目標題：sources 內的維基網址優先，其次 wiki 欄位。"""
    out = []
    for s in item.get("sources", []) or []:
        m = re.search(r"en\.wikipedia\.org/wiki/([^?#]+)", (s or {}).get("url", "") or "")
        if m:
            out.append(urllib.parse.unquote(m.group(1)).replace("_", " "))
    w = item.get("wiki")
    if w and w not in out:
        out.append(w)
    return out


def main():
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))

    t = (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8")
    arr = json.loads(t[t.index("["):t.rindex("]") + 1])
    done = json.loads(OUT.read_text()) if OUT.exists() else {}

    targets = [x for x in arr if (only is None or x["id"] in only)]
    ok = skip_noimg = skip_name = err = 0

    for i, item in enumerate(targets, 1):
        eid = item["id"]
        if eid in done and (ROOT / done[eid]["path"]).exists():
            continue
        toks = tokens_for(item)
        picked = None
        for title in wiki_titles(item):
            name, src = pageimage(title)
            if not name or not src:
                continue
            nname = norm(name)
            if any(b in nname for b in BAD_WORDS):
                log(f"  ✗ 檔名疑似圖表 {eid}: {name}")
                continue
            if not any(tk in nname for tk in toks):
                log(f"  ✗ 檔名不含型號 {eid}: {name}")
                continue
            picked = (title, name, src)
            break
        if not picked:
            skip_name += 1
            continue
        title, name, src = picked
        try:
            data = GET(src, 30).read()
            if len(data) < 3000:
                skip_noimg += 1
                continue
            ext = ".png" if name.lower().endswith(".png") else ".jpg"
            path = f"assets/images/{eid}{ext}"
            (ROOT / path).write_bytes(data)
            done[eid] = {"path": path, "file": name, "title": title}
            OUT.write_text(json.dumps(done, ensure_ascii=False, indent=0), encoding="utf-8")
            ok += 1
            log(f"[{i}/{len(targets)}] ✓ {eid} ← {name[:60]}")
        except Exception as e:
            err += 1
            log("  dl-err", eid, str(e)[:60])
        time.sleep(0.08)

    log(f"=== 完成 ok={ok} 無合格主圖={skip_name} 太小={skip_noimg} 錯誤={err} 累計={len(done)} ===")


if __name__ == "__main__":
    main()
