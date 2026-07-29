#!/usr/bin/env python3
"""CDP 多平台補圖：百度百科 + 知乎（搜狗 site:zhihu.com）+ 搜狗百科。

需 Chrome remote debugging :9333（已開百科/知乎可沿用 cookies）。
嚴格：標題/摘要須含型號關鍵字；拒絕民用/外軍/泛用錯配。

用法：
  .venv/bin/python tools/fetch_cn_platforms_cdp.py
  .venv/bin/python tools/fetch_cn_platforms_cdp.py --limit 40
  .venv/bin/python tools/fetch_cn_platforms_cdp.py --ids zbd-08,pcl-181
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image
from websocket import create_connection

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "assets" / "images"
LOG_PATH = ROOT / "data" / "cn_platforms_log.json"
EP_PATH = ROOT / "data" / "specs_enrichment.json"
BASE = "http://127.0.0.1:9333"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)
MIN_KEEP = 25000
MIN_SAVE = 8000
SOURCE_TAG = "cn_platforms_cdp"

T2S = str.maketrans(
    {
        "驅": "驱", "艦": "舰", "護": "护", "衛": "卫", "潛": "潜", "彈": "弹",
        "導": "导", "戰": "战", "機": "机", "轟": "轰", "運": "运", "預": "预",
        "無": "无", "偵": "侦", "擊": "击", "殲": "歼", "強": "强", "裝": "装",
        "砲": "炮", "槍": "枪", "飛": "飞", "東": "东", "風": "风", "長": "长",
        "劍": "剑", "紅": "红", "級": "级", "陸": "陆", "軍": "军", "雙": "双",
        "載": "载", "兩": "两", "棲": "栖", "補": "补", "給": "给", "輕": "轻",
        "車": "车", "輪": "轮", "後": "后", "單": "单", "練": "练", "電": "电",
        "際": "际", "遠": "远", "發": "发", "號": "号", "龍": "龙", "蘇": "苏",
        "鷹": "鹰", "靂": "雳", "魚": "鱼", "雲": "云", "進": "进", "測": "测",
        "掃": "扫", "視": "视", "儀": "仪", "變": "变", "備": "备", "隊": "队",
    }
)

# id -> (queries for baike/sogou/zhihu, keys for match)
OVERRIDE = {
    "zbd-08": (["ZBL-08", "08式轮式步兵战车", "08式步兵战车"], ["ZBL-08", "ZBL08", "08式", "轮式步兵战车"]),
    "zsl-10": (["ZSL-10", "08式轮式装甲输送车"], ["ZSL-10", "ZSL10", "08式", "装甲输送"]),
    "pcl-181": (["PCL-181", "SH-15型155毫米车载加榴炮", "SH-15"], ["PCL-181", "SH-15", "SH15", "155", "车载"]),
    "pcl-171": (["PCL-171", "PCL171车载榴弹炮"], ["PCL-171", "PCL171"]),
    "phz-11": (["PHZ-11", "PHZ11火箭炮"], ["PHZ-11", "PHZ11"]),
    "pgz-04a": (["PGZ-04A", "04A式自行高炮"], ["PGZ-04A", "04A式", "自行高炮"]),
    "pl-17": (["霹雳-17", "霹雳17空空导弹", "PL-17"], ["霹雳-17", "霹雳17", "PL-17"]),
    "yu-6": (["鱼-6鱼雷", "鱼6重型鱼雷"], ["鱼-6", "鱼6", "鱼雷"]),
    "yu-7": (["鱼-7鱼雷", "鱼7轻型鱼雷"], ["鱼-7", "鱼7", "鱼雷"]),
    "asn-209": (["ASN-209无人机", "ASN209"], ["ASN-209", "ASN209", "无人机"]),
    "df-27": (["东风-27", "东风27导弹"], ["东风-27", "东风27"]),
    "df-21c": (["东风-21C", "东风21C"], ["东风-21C", "东风21C", "东风-21"]),
    "gcl-111": (["84式坦克架桥车", "坦克架桥车"], ["架桥车", "84式", "坦克架桥"]),
    "pp-89": (["89式100毫米迫击炮", "100毫米迫击炮"], ["100毫米迫击炮", "89式迫击炮"]),
    "qlg-10": (["QLG-10", "枪挂榴弹发射器"], ["QLG-10", "QLG10", "枪挂榴弹"]),
    "phl-11": (["PHL-11", "PHL11火箭炮"], ["PHL-11", "PHL11"]),
    "su-35": (["苏-35战斗机", "苏-35S"], ["苏-35", "苏35"]),
    "h-6k": (["轰-6K", "轰-6K轰炸机"], ["轰-6K", "轰6K"]),
    "sh-15": (["SH-15型155毫米车载加榴炮", "SH-15"], ["SH-15", "SH15", "155"]),
    "yj-18b": (["鹰击-18", "鹰击18"], ["鹰击-18", "鹰击18", "YJ-18"]),
    "z-9d": (["直-9D", "直-9反舰直升机"], ["直-9D", "直-9", "直9"]),
    "type-904": (["904型补给舰", "大运级"], ["904", "补给舰", "大运"]),
    "type-053h": (["053H型护卫舰", "江湖级护卫舰"], ["053H", "江湖", "护卫舰"]),
    "type-053h1g": (["053H1G型护卫舰"], ["053H1G", "江湖"]),
    "type-053h2g": (["053H2G型护卫舰", "江卫级"], ["053H2G", "江卫"]),
    "type-037is": (["037IS型猎潜艇", "海青级"], ["037IS", "037", "猎潜"]),
    "ptl-02": (["PTL-02", "PTL02轮式突击炮"], ["PTL-02", "PTL02", "突击炮"]),
    "bzk-007": (["BZK-007", "BZK007无人机"], ["BZK-007", "BZK007"]),
    "pl-11": (["霹雳-11", "PL-11"], ["霹雳-11", "霹雳11", "PL-11"]),
    "pl-21": (["霹雳-21", "PL-21"], ["霹雳-21", "霹雳21", "PL-21"]),
    "hj-11": (["红箭-11", "红箭11"], ["红箭-11", "红箭11"]),
    "gb-6": (["GB-6滑翔制导炸弹", "GB-6"], ["GB-6", "滑翔制导炸弹"]),
    "type-096": (["096型核潜艇"], ["096", "核潜艇"]),
    "type-925": (["925型潜艇支援舰", "大峰级"], ["925", "大峰", "潜艇支援"]),
    "pgz-88": (["88式自行高炮", "PGZ-88"], ["88式", "PGZ-88", "自行高炮"]),
    "w85-hmg": (["W85高射机枪", "W85"], ["W85", "高射机枪"]),
    "type-84-minelayer": (["84式布雷车"], ["84式", "布雷车"]),
    "fb-6c": (["FB-6C", "飞弩防空导弹"], ["FB-6", "飞弩"]),
    "cs-sm1": (["CS/SM1", "120毫米车载迫击炮"], ["CS/SM1", "120毫米", "迫击炮"]),
    "slc-7": (["SLC-7雷达"], ["SLC-7", "雷达"]),
    "type-120-radar": (["120型雷达", "低空补盲雷达"], ["120型", "补盲", "雷达"]),
    "df-15a": (["东风-15A", "东风15A"], ["东风-15A", "东风-15", "东风15"]),
    "ba-9": (["蓝箭-9", "蓝箭9导弹"], ["蓝箭-9", "蓝箭9"]),
    "type-91b-gl": (["91B枪挂榴弹", "QLG-10"], ["91B", "枪挂榴弹"]),
    "qgf-11": (["QGF-11头盔", "11式头盔"], ["QGF-11", "头盔"]),
    "yu-10": (["鱼-10鱼雷"], ["鱼-10", "鱼10", "鱼雷"]),
    "type-818": (["818型海警船", "昭头级"], ["818", "海警", "昭头"]),
    "type-718b": (["718B型海警船"], ["718B", "海警"]),
    "gcz-112": (["GCZ-112", "装甲工程车"], ["GCZ-112", "工程车"]),
    "gcj-112": (["GCJ工程车", "装甲工程车"], ["GCJ", "工程车"]),
    "pll-01": (["PLL-01", "100毫米突击炮"], ["PLL-01", "PLL01", "突击炮"]),
    "pcz-171": (["PCZ-171"], ["PCZ-171"]),
    "ft-series": (["飞腾精确制导炸弹", "飞腾系列炸弹"], ["飞腾", "制导炸弹"]),
    "gb-series": (["GB系列精确制导炸弹"], ["GB系列", "制导炸弹"]),
    "ls-500j": (["雷石-500", "雷石制导炸弹"], ["雷石", "LS-500"]),
    "asn-301": (["ASN-301", "反辐射无人机"], ["ASN-301", "反辐射"]),
    "type-024": (["024型导弹艇", "河谷级"], ["024", "导弹艇", "河谷"]),
    "type-909": (["909型试验舰", "毕昇级"], ["909", "试验舰", "毕昇"]),
    "type-65-aaa": (["65式37毫米高射炮"], ["65式", "37毫米", "高射炮"]),
    "type-74-aaa": (["74式双37毫米高射炮"], ["74式", "37毫米", "高射炮"]),
    "cetc-jammer": (["电子战干扰车", "通信干扰系统"], ["干扰", "电子战"]),
    "bbg011a": (["BBG011A", "夜视仪"], ["BBG011A", "夜视"]),
    "w86-120": (["W86迫击炮", "120毫米迫击炮"], ["W86", "120毫米迫击炮"]),
}


def to_s(t: str) -> str:
    return (t or "").translate(T2S)


def clean(n: str) -> str:
    return re.sub(r"[（(].*?[）)]", "", n or "").replace("／", "/").strip()


def local_size(eid: str) -> int:
    best = 0
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = IMG / f"{eid}{ext}"
        if p.exists():
            best = max(best, p.stat().st_size)
    return best


def build_queries(item: dict) -> tuple[list[str], list[str]]:
    eid = item["id"]
    name = to_s(clean(item.get("name_zh") or ""))
    des = (item.get("designation") or "").strip()
    qs: list[str] = []
    keys: list[str] = []

    def addq(q):
        q = re.sub(r"\s+", "", q).strip()
        if q and q not in qs and len(q) >= 2:
            qs.append(q)

    def addk(k):
        if k and k not in keys:
            keys.append(k)

    if eid in OVERRIDE:
        for q in OVERRIDE[eid][0]:
            addq(q)
        for k in OVERRIDE[eid][1]:
            addk(k)
    addq(name)
    if des:
        addq(des)
        addk(des.replace(" ", ""))
        m = re.match(r"Type\s*([0-9]{2,4}[A-Za-z]*)", des, re.I)
        if m:
            addq(f"{m.group(1)}型")
            addq(f"{m.group(1)}式")
            addk(m.group(1))
        m2 = re.match(r"([A-Za-z]{1,5})-?(\d{1,4}[A-Za-z]*)", des)
        if m2:
            pref, num = m2.group(1).upper(), m2.group(2).upper()
            cmap = {
                "J": "歼-", "H": "轰-", "Y": "运-", "Z": "直-", "KJ": "空警-",
                "DF": "东风-", "YJ": "鹰击-", "HQ": "红旗-", "PL": "霹雳-",
                "JL": "巨浪-", "HJ": "红箭-", "FN": "飞弩-", "SU": "苏-",
                "CH": "彩虹-", "WZ": "无侦-", "CJ": "长剑-",
            }
            if pref in cmap:
                addq(f"{cmap[pref]}{num}")
                addk(f"{cmap[pref]}{num}")
            addq(f"{pref}-{num}")
            addk(f"{pref}-{num}")
            addk(num)
    for w in ["舰", "艇", "机", "弹", "炮", "坦克", "导弹", "潜艇", "直升", "火箭", "无人", "鱼雷", "雷达"]:
        if w in name:
            addk(w)
    return qs[:8], keys[:18]


JUNK = [
    "游戏", "玉米", "学校", "机车", "列车", "电池", "动画", "高达", "手机", "综艺",
    "演员", "音乐", "小说", "公路", "俱乐部", "广场", "小米", "手环", "快干胶",
    "东风小康", "洒水车", "骁龙", "三星", "尼康", "轴承", "基因", "CV90", "BTP",
    "AMX", "BMD", "哈比", "Panasonic", "安全验证", "SCP", "基金会", "红缨-6",
]


def match_blob(title: str, summary: str, keys: list[str], name_s: str) -> bool:
    blob = f"{title or ''} {summary or ''}"
    if any(j in blob for j in JUNK):
        return False
    if not title or title.startswith("百度百科") or "百科全书" in title:
        return False
    if title in ("自行加榴炮", "火箭武器", "防空导弹", "空空导弹", "鱼雷", "多管火箭炮", "装甲输送车"):
        return False
    up = blob.upper().replace(" ", "").replace("-", "")
    for k in keys:
        if not k:
            continue
        if k.upper().replace("-", "") in up or k in blob:
            return True
    core = re.sub(r"[A-Za-z0-9\-_\s/]", "", name_s)
    if len(core) >= 3 and core[:3] in blob:
        return True
    return False


class Browser:
    def __init__(self):
        tabs = json.load(urllib.request.urlopen(BASE + "/json/list", timeout=5))
        page = None
        for t in tabs:
            if t.get("type") == "page" and not str(t.get("url", "")).startswith("chrome"):
                page = t
                break
        if not page:
            page = next(t for t in tabs if t.get("type") == "page")
        self.ws = create_connection(page["webSocketDebuggerUrl"], timeout=50)
        self.mid = 0
        self.call("Page.enable")
        self.call("Runtime.enable")
        self.call("Network.enable")

    def call(self, method, params=None):
        self.mid += 1
        i = self.mid
        self.ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == i:
                if "error" in r:
                    raise RuntimeError(r["error"])
                return r.get("result", {})

    def eval(self, expr):
        r = self.call(
            "Runtime.evaluate",
            {"expression": expr, "returnByValue": True, "awaitPromise": True},
        )
        res = r.get("result", {})
        if res.get("subtype") == "error":
            raise RuntimeError(res.get("description"))
        return res.get("value")

    def goto(self, url, wait=1.4):
        self.call("Page.navigate", {"url": url})
        for _ in range(50):
            time.sleep(0.2)
            try:
                if self.eval("document.readyState") == "complete":
                    time.sleep(wait)
                    return
            except Exception:
                pass
        time.sleep(wait)

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


EXTRACT = r"""
(() => {
  const title = document.title.replace(/_百度百科$/,'').replace(/-百度百科$/,'').replace(/_搜狗百科$/,'').replace(/-搜狗搜索$/,'').replace(/ - 知乎$/,'').trim();
  const h1 = (document.querySelector('h1')||{}).innerText || '';
  const meta = (document.querySelector('meta[name="image"], meta[property="og:image"]')||{}).content || '';
  const summary = (document.querySelector('.lemma-summary, .J-summary, .main-content, .content, #J-lemma-content, .RichText, .Post-RichText')||document.body).innerText.slice(0,900);
  const imgs=[];
  const push=(src,w,h,score)=>{
    if(!src||src.startsWith('data:'))return;
    if(/baike\.png|cms\/static\/baike|logo|avatar|icon|emoji|qrcode|sprite/i.test(src))return;
    if(!/^https?:/i.test(src))return;
    // skip tiny thumbs
    if(/[?&](w|width|h|height)=\d{1,2}\b/i.test(src))return;
    imgs.push({src,w:w||0,h:h||0,score:score||((w||0)*(h||0))});
  };
  if(meta) push(meta,1000,1000,1e9);
  for(const i of document.images){
    push(i.currentSrc||i.src||i.getAttribute('data-src')||i.getAttribute('data-original')||'', i.naturalWidth||0, i.naturalHeight||0);
  }
  for(const el of document.querySelectorAll('[data-src], [data-original]')){
    push(el.getAttribute('data-src')||el.getAttribute('data-original')||'', 800, 800, 3e5);
  }
  imgs.sort((a,b)=>b.score-a.score);
  const links=[...document.querySelectorAll('a')].filter(a=>/baike\.baidu|baike\.sogou|zhihu\.com\/(question|p|zvideo|answer)/i.test(a.href)).slice(0,16).map(a=>({href:a.href,text:(a.innerText||'').trim().slice(0,60)}));
  const head=(document.body&&document.body.innerText||'').slice(0,200);
  const captcha=/验证|安全验证|BIOC|请完成|滑动/.test(head)||/验证/.test(title);
  return {title,h1,summary,captcha,imgs:imgs.slice(0,15),links,url:location.href};
})()
"""


def enlarge(u: str) -> str:
    if not u:
        return u
    base = u.split("?")[0]
    # baike / bos
    if "bkimg" in base or "bcebos" in base or "/pic/" in base:
        return base + "?x-bce-process=image/quality,Q_90"
    # zhihu often has size in path - try strip size params for larger
    if "zhimg.com" in u:
        # v2-xxx_720w -> try without suffix sometimes
        return re.sub(r"_(720|540|400|200)w", "_1440w", u)
    return u


def download(url: str, dest: Path) -> bool:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Referer": "https://baike.baidu.com/", "Accept": "image/*,*/*"},
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            data = r.read()
        if len(data) < 4000:
            return False
        im = Image.open(BytesIO(data)).convert("RGB")
        if min(im.size) < 140:
            return False
        if im.size[0] == im.size[1] and im.size[0] <= 400 and len(data) < 35000:
            return False
        if max(im.size) > 1600:
            im.thumbnail((1600, 1600))
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=90, optimize=True)
        return dest.stat().st_size >= MIN_SAVE
    except Exception as e:
        print(f"    dl {e}", flush=True)
        return False


def try_page(b: Browser, url: str, keys: list[str], name_s: str, dest: Path, platform: str):
    b.goto(url, wait=1.5)
    info = b.eval(EXTRACT)
    if not info:
        return None, None
    if info.get("captcha"):
        return "CAPTCHA", info
    title = info.get("title") or info.get("h1") or ""
    summary = info.get("summary") or ""
    if not match_blob(title, summary, keys, name_s):
        # search pages: follow links
        if "search" in url or "sogou.com" in url:
            for lk in info.get("links") or []:
                text = lk.get("text") or ""
                href = lk.get("href") or ""
                if href and match_blob(text, text, keys, name_s):
                    return try_page(b, href, keys, name_s, dest, platform)
        print(f"    skip {platform} {title[:45]!r}", flush=True)
        return None, info
    for im in info.get("imgs") or []:
        src = enlarge(im.get("src") or "")
        if download(src, dest):
            return {
                "ok": True,
                "source": platform,
                "title": title,
                "url": info.get("url") or url,
                "img_url": src,
                "path": f"assets/images/{dest.stem}.jpg",
                "bytes": dest.stat().st_size,
            }, info
    return None, info


def process_item(b: Browser, item: dict, log: dict) -> bool:
    eid = item["id"]
    name_s = to_s(clean(item.get("name_zh") or ""))
    qs, keys = build_queries(item)
    dest = IMG / f"{eid}.jpg"
    print(f"  queries={qs[:4]} keys={keys[:6]}", flush=True)

    urls: list[tuple[str, str]] = []  # (platform, url)
    for q in qs[:4]:
        urls.append(("baike", "https://baike.baidu.com/item/" + urllib.parse.quote(q)))
    for q in qs[:2]:
        urls.append(("baike_search", "https://baike.baidu.com/search?word=" + urllib.parse.quote(q)))
    for q in qs[:2]:
        # 搜狗百科
        urls.append(("sogou_baike", "https://www.sogou.com/sogou?query=" + urllib.parse.quote(q + " site:baike.sogou.com")))
    for q in qs[:3]:
        # 知乎 via 搜狗（用户已开此方式）
        urls.append(
            (
                "zhihu_sogou",
                "https://www.sogou.com/sogou?query="
                + urllib.parse.quote(q)
                + "&ie=utf8&insite=zhihu.com",
            )
        )
    for q in qs[:2]:
        urls.append(("zhihu", "https://www.zhihu.com/search?type=content&q=" + urllib.parse.quote(q)))

    last_info = None
    for platform, url in urls:
        try:
            res, info = try_page(b, url, keys, name_s, dest, platform)
            last_info = info
            if res == "CAPTCHA":
                print("  CAPTCHA", flush=True)
                log[eid] = {"ok": False, "reason": "captcha", "platform": platform}
                return False
            if isinstance(res, dict) and res.get("ok"):
                # prefer larger than existing tiny
                if local_size(eid) and dest.stat().st_size < local_size(eid):
                    # we overwrote - ok if we had 0 before
                    pass
                res["source"] = f"{SOURCE_TAG}:{platform}"
                log[eid] = res
                print(f"  OK {platform} {res['title'][:40]} {res['bytes']}", flush=True)
                return True
        except Exception as e:
            print(f"  err {platform}: {e}", flush=True)
            time.sleep(0.8)
            continue
        time.sleep(0.45)

    log[eid] = {
        "ok": False,
        "reason": "no_match",
        "title": (last_info or {}).get("title"),
        "queries": qs[:6],
    }
    print("  FAIL", flush=True)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", type=str, default="")
    args = ap.parse_args()

    text = (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8")
    items = json.loads(text[text.index("[") : text.rindex("]") + 1])
    log = json.loads(LOG_PATH.read_text(encoding="utf-8")) if LOG_PATH.exists() else {}

    only = set(x for x in args.ids.split(",") if x) if args.ids else None
    targets = []
    for it in items:
        eid = it["id"]
        if only and eid not in only:
            continue
        if local_size(eid) >= MIN_KEEP:
            continue
        targets.append(it)

    def score(it):
        eid = it["id"]
        s = 0 if local_size(eid) == 0 else 1
        if eid in OVERRIDE:
            s -= 10
        return (s, eid)

    targets.sort(key=score)
    if args.limit:
        targets = targets[: args.limit]

    print(f"targets={len(targets)} CDP={BASE}", flush=True)
    b = Browser()
    ok = fail = 0
    captcha_stop = False
    try:
        for i, it in enumerate(targets, 1):
            print(f"\n[{i}/{len(targets)}] {it['id']} | {it.get('name_zh')}", flush=True)
            if process_item(b, it, log):
                ok += 1
            else:
                fail += 1
                if log.get(it["id"], {}).get("reason") == "captcha":
                    captcha_stop = True
                    # try continue a few more; soft stop after 3 captchas
            if i % 4 == 0:
                LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
            time.sleep(0.55)
    finally:
        try:
            b.close()
        except Exception:
            pass

    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    ep = json.loads(EP_PATH.read_text(encoding="utf-8")) if EP_PATH.exists() else {"items": {}}
    n = 0
    for eid, res in log.items():
        if not res.get("ok") or not res.get("path"):
            continue
        p = ROOT / res["path"]
        if not p.exists() or p.stat().st_size < MIN_SAVE:
            continue
        ent = ep.setdefault("items", {}).setdefault(eid, {})
        ent["image"] = res["path"]
        src = res.get("source", SOURCE_TAG)
        title = res.get("title") or eid
        if "zhihu" in src:
            ent["image_credit"] = f"图片来自知乎相关公开页《{title}》（教育参考）"
        elif "sogou" in src:
            ent["image_credit"] = f"图片来自搜狗百科/搜索《{title}》（教育参考）"
        else:
            ent["image_credit"] = f"图片来自百度百科《{title}》（教育参考）"
        n += 1
    EP_PATH.write_text(json.dumps(ep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDONE ok={ok} fail={fail} enrich={n} captcha_hit={captcha_stop}", flush=True)


if __name__ == "__main__":
    main()
