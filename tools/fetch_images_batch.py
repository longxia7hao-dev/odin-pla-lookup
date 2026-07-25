#!/usr/bin/env python3
"""嚴格抓圖（批次版）：一次查 50 個維基標題，避免 429 限流。
規則同 fetch_images_strict：只採「指定主圖」+ 檔名須含型號。
API 錯誤會重試並與「真的沒圖」區分，不再誤判。
"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
UA = "odin-pla-lookup/1.0 (educational OSINT reference; github longxia7hao-dev)"
OUT = ROOT / "data" / "strict_images.json"
LOG = open(ROOT / "tools" / "img_batch.log", "a", encoding="utf-8")

# 沿用嚴格版的 token / 檔名規則
_src = (ROOT / "tools" / "fetch_images_strict.py").read_text(encoding="utf-8").split("def pageimage")[0]
_ns = {"__file__": str(ROOT / "tools" / "fetch_images_strict.py")}
exec(_src, _ns)
norm, tokens_for, BAD_WORDS = _ns["norm"], _ns["tokens_for"], _ns["BAD_WORDS"]


def log(*a):
    print(*a)
    print(*a, file=LOG, flush=True)


def GET(url, timeout=25, tries=6):
    last = None
    for i in range(tries):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout)
        except Exception as e:
            last = e
            code = getattr(e, "code", None)
            if code == 429 or code is None:
                time.sleep(8 * (i + 1))  # 退避（下載端限流較嚴）
                continue
            raise
    raise last


def wiki_titles(item):
    out = []
    for s in item.get("sources", []) or []:
        m = re.search(r"en\.wikipedia\.org/wiki/([^?#]+)", (s or {}).get("url", "") or "")
        if m:
            out.append(urllib.parse.unquote(m.group(1)).replace("_", " "))
    w = item.get("wiki")
    if w and w not in out:
        out.append(w)
    return out


def batch_pageimages(titles):
    """一次查最多 50 個標題 → {原始標題: (檔名, 原圖URL)}"""
    res = {}
    u = ("https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1"
         "&prop=pageimages&piprop=original|name&titles=" + urllib.parse.quote("|".join(titles)))
    d = json.load(GET(u))
    q = d.get("query", {})
    # 追蹤 normalized / redirects，把回應對回原始標題
    alias = {}
    for k in ("normalized", "redirects"):
        for m in q.get(k, []) or []:
            alias[m["to"]] = alias.get(m["from"], m["from"])
    for _, pg in q.get("pages", {}).items():
        if "missing" in pg:
            continue
        name = pg.get("pageimage")
        src = (pg.get("original") or {}).get("source", "")
        if not (name and src):
            continue
        t = pg.get("title", "")
        orig = alias.get(t, t)
        res[orig] = (name, src)
        res[t] = (name, src)
    return res


def main():
    t = (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8")
    arr = json.loads(t[t.index("["):t.rindex("]") + 1])
    done = json.loads(OUT.read_text()) if OUT.exists() else {}

    # 1) 收集所有候選標題
    cand = {x["id"]: wiki_titles(x) for x in arr}
    all_titles = sorted({t for ts in cand.values() for t in ts})
    log(f"批次查詢 {len(all_titles)} 個維基標題…")

    lookup = {}
    for i in range(0, len(all_titles), 50):
        chunk = all_titles[i:i + 50]
        try:
            lookup.update(batch_pageimages(chunk))
        except Exception as e:
            log(f"  批次失敗 {i}: {str(e)[:70]}")
        time.sleep(1.2)
        if (i // 50) % 5 == 0:
            log(f"  …已查 {min(i+50,len(all_titles))}/{len(all_titles)}，找到主圖 {len(lookup)}")
    log(f"查詢完成：{len(lookup)} 個標題有指定主圖")

    # 2) 逐筆比對檔名 → 下載
    byid = {x["id"]: x for x in arr}
    ok = rej_name = rej_bad = no_img = err = 0
    for eid, titles in cand.items():
        if eid in done and (ROOT / done[eid]["path"]).exists():
            continue
        item = byid[eid]
        toks = tokens_for(item)
        picked = None
        for ti in titles:
            hit = lookup.get(ti)
            if not hit:
                continue
            name, src = hit
            n = norm(name)
            if any(b in n for b in BAD_WORDS):
                rej_bad += 1
                log(f"  ✗圖表 {eid}: {name}")
                continue
            if not any(tk in n for tk in toks):
                rej_name += 1
                log(f"  ✗不符 {eid}: {name}")
                continue
            picked = (ti, name, src)
            break
        if not picked:
            no_img += 1
            continue
        ti, name, src = picked
        try:
            data = GET(src, 30).read()
            if len(data) < 3000:
                no_img += 1
                continue
            ext = ".png" if name.lower().endswith(".png") else ".jpg"
            path = f"assets/images/{eid}{ext}"
            (ROOT / path).write_bytes(data)
            done[eid] = {"path": path, "file": name, "title": ti}
            OUT.write_text(json.dumps(done, ensure_ascii=False, indent=0), encoding="utf-8")
            ok += 1
            log(f"  ✓ {eid} ← {name[:58]}")
        except Exception as e:
            err += 1
            log(f"  下載失敗 {eid}: {str(e)[:60]}")
        time.sleep(1.1)   # 放慢下載，避免 429

    log(f"=== 完成 ok={ok} 檔名不符={rej_name} 圖表={rej_bad} 無主圖={no_img} 錯誤={err} 累計={len(done)} ===")


if __name__ == "__main__":
    main()
