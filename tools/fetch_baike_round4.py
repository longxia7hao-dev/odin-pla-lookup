#!/usr/bin/env python3
"""Round 4: Baike CDP image fetch for remaining missing/tiny items."""
from __future__ import annotations

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
BASE = "http://127.0.0.1:9333"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)
LOG_PATH = ROOT / "data" / "baike_cdp_log.json"
EP_PATH = ROOT / "data" / "specs_enrichment.json"
BATCH_SIZE = 120
MIN_KEEP = 25000

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
        "搶": "抢", "救": "救", "橋": "桥", "雷": "雷", "巡": "巡", "邏": "逻",
    }
)

# High-value overrides: id -> (queries, keys)
OVERRIDE = {
    "zbd-08": (["ZBL-08", "08式轮式步兵战车", "08式步兵战车"], ["ZBL-08", "08式", "步兵战车"]),
    "zsl-10": (["ZSL-10", "10式轮式装甲车"], ["ZSL-10", "装甲车"]),
    "pcl-181": (["SH-15型155毫米车载加榴炮", "PCL-181", "SH-15"], ["SH-15", "PCL-181", "155", "车载"]),
    "pcl-171": (["PCL-171"], ["PCL-171"]),
    "pcl-161": (["PCL-161"], ["PCL-161"]),
    "phz-11": (["PHZ-11", "11式火箭炮"], ["PHZ-11", "火箭炮"]),
    "phl-81": (["81式火箭炮", "PHL-81"], ["81式", "火箭炮", "122"]),
    "phl-03": (["PHL-03", "03式远程火箭炮", "卫士-2"], ["PHL-03", "远程火箭", "03式"]),
    "phl-11": (["PHL-11"], ["PHL-11"]),
    "phl-16": (["PHL-16", "PCL-191"], ["PHL-16", "PCL-191"]),
    "pgz-04a": (["PGZ-04A"], ["PGZ-04A", "04A"]),
    "plz-05": (["PLZ-05", "05式155毫米自行加榴炮"], ["PLZ-05", "05式", "155"]),
    "plz-05a": (["05A式155毫米加榴炮", "PLZ-05A"], ["05A", "155"]),
    "plz-52": (["PLZ-52"], ["PLZ-52"]),
    "sh-15": (["SH-15型155毫米车载加榴炮", "SH-15"], ["SH-15", "155", "车载"]),
    "sh5-105": (["SH5型105毫米车载榴弹炮", "SH-5"], ["SH5", "SH-5", "105"]),
    "type-052b": (["中国人民解放军海军广州舰", "052B型驱逐舰", "广州舰"], ["广州舰", "052B", "驱逐"]),
    "type-093b": (["093B型核潜艇", "商级核潜艇"], ["093B", "093", "核潜艇"]),
    "type-093a": (["093A型核潜艇", "商级核潜艇"], ["093A", "093", "核潜艇"]),
    "type-094a": (["094A型核潜艇", "晋级核潜艇"], ["094A", "094", "核潜艇"]),
    "type-096": (["096型核潜艇"], ["096", "核潜艇"]),
    "type-039c": (["039C型潜艇", "元级潜艇"], ["039C", "元级", "潜艇"]),
    "type-039b": (["039B型潜艇", "元级潜艇"], ["039B", "元级"]),
    "asn-209": (["ASN-209无人机", "ASN-209"], ["ASN-209", "无人机"]),
    "ch-3": (["CH-3中程长航时无人机", "彩虹-3"], ["CH-3", "彩虹-3", "无人机"]),
    "ch-6": (["彩虹-6", "CH-6"], ["彩虹-6", "CH-6"]),
    "df-15": (["东风-15弹道导弹", "东风-15"], ["东风-15", "东风15", "弹道"]),
    "df-15a": (["东风-15A", "东风-15"], ["东风-15", "东风15"]),
    "df-15b": (["东风-15B", "东风-15"], ["东风-15", "东风15"]),
    "df-16": (["东风-16"], ["东风-16", "东风16"]),
    "df-21": (["东风-21"], ["东风-21", "东风21"]),
    "df-21c": (["东风-21C", "东风-21"], ["东风-21", "东风21"]),
    "df-31": (["东风-31"], ["东风-31", "东风31"]),
    "df-41": (["东风-41洲际战略核导弹", "东风-41"], ["东风-41", "东风41"]),
    "yj-18": (["鹰击-18"], ["鹰击-18", "鹰击18"]),
    "yj-21": (["鹰击-21"], ["鹰击-21", "鹰击21"]),
    "yj-12": (["鹰击-12"], ["鹰击-12", "鹰击12"]),
    "yj-83": (["鹰击-83"], ["鹰击-83", "鹰击83"]),
    "yj-62": (["鹰击-62"], ["鹰击-62", "鹰击62"]),
    "hq-16": (["红旗-16"], ["红旗-16", "红旗16"]),
    "hq-17": (["红旗-17"], ["红旗-17", "红旗17"]),
    "hq-17a": (["红旗-17A", "红旗-17"], ["红旗-17", "红旗17"]),
    "hq-22": (["红旗-22"], ["红旗-22", "红旗22"]),
    "hq-9b": (["红旗-9B", "红旗-9"], ["红旗-9", "红旗9"]),
    "hq-7": (["红旗-7"], ["红旗-7", "红旗7"]),
    "hq-7b": (["红旗-7B", "红旗-7"], ["红旗-7", "红旗7"]),
    "hhq-9": (["海红旗-9", "红旗-9"], ["海红旗", "红旗-9"]),
    "hhq-10": (["海红旗-10", "HQ-10"], ["海红旗-10", "红旗-10"]),
    "hhq-16": (["海红旗-16", "红旗-16"], ["海红旗", "红旗-16"]),
    "pl-15": (["霹雳-15"], ["霹雳-15", "霹雳15"]),
    "pl-10": (["霹雳-10"], ["霹雳-10", "霹雳10"]),
    "pl-12": (["霹雳-12"], ["霹雳-12", "霹雳12"]),
    "pl-17": (["霹雳-17"], ["霹雳-17", "霹雳17"]),
    "type-99a": (["99A式主战坦克", "ZTZ-99A"], ["99A", "99式", "主战坦克"]),
    "type-96a": (["96A式主战坦克", "ZTZ-96A"], ["96A", "96式"]),
    "type-96b": (["96B式主战坦克"], ["96B"]),
    "type-99": (["99式主战坦克", "ZTZ-99"], ["99式", "主战坦克"]),
    "ztq-15": (["15式轻型坦克", "ZTQ-15"], ["15式", "轻型坦克"]),
    "zbd-04": (["04式步兵战车", "ZBD-04"], ["04式", "ZBD-04", "步兵战车"]),
    "zbd-04a": (["04A式步兵战车", "ZBD-04A"], ["04A", "ZBD-04"]),
    "zbd-05": (["05式两栖步兵战车", "ZBD-05"], ["05式", "两栖", "ZBD-05"]),
    "ztd-05": (["05式两栖突击车", "ZTD-05"], ["ZTD-05", "突击车"]),
    "ztl-11": (["11式轮式突击车", "ZTL-11"], ["ZTL-11", "11式", "突击"]),
    "type-056": (["056型护卫舰"], ["056型护卫", "056"]),
    "type-022": (["022型导弹艇"], ["022", "导弹艇"]),
    "type-054": (["054型护卫舰"], ["054型护卫"]),
    "kj-200": (["空警-200"], ["空警-200", "空警200"]),
    "kj-600": (["空警-600"], ["空警-600", "空警600"]),
    "j-15d": (["歼-15D", "歼-15"], ["歼-15", "电子战"]),
    "j-15t": (["歼-15T", "歼-15"], ["歼-15"]),
    "j-16d": (["歼-16D", "歼-16"], ["歼-16", "电子"]),
    "il-76": (["伊尔-76"], ["伊尔-76", "Il-76"]),
    "il-78": (["伊尔-78"], ["伊尔-78", "Il-78"]),
    "mi-17": (["米-17直升机", "米-17"], ["米-17", "米17"]),
    "mi-171": (["米-171", "米-17"], ["米-171", "米-17"]),
    "ka-27": (["卡-27直升机", "卡-27"], ["卡-27", "卡27"]),
    "ka-31": (["卡-31"], ["卡-31", "卡31"]),
    "type-920": (["和平方舟号医院船", "和平方舟"], ["和平方舟", "医院船"]),
    "ccg-2901": (["中国海警2901", "海警2901"], ["2901", "海警"]),
    "qbz-191": (["QBZ-191", "191式自动步枪"], ["QBZ-191", "191式"]),
    "hj-12": (["红箭-12"], ["红箭-12", "红箭12"]),
    "hj-10": (["红箭-10"], ["红箭-10", "红箭10"]),
    "hj-8": (["红箭-8"], ["红箭-8", "红箭8"]),
    "hj-9": (["红箭-9"], ["红箭-9", "红箭9"]),
    "fn-6": (["飞弩-6"], ["飞弩-6", "飞弩6"]),
    "fn-16": (["飞弩-16"], ["飞弩-16", "飞弩16"]),
    "pf-98": (["98式反坦克火箭筒", "PF-98"], ["98式", "PF-98", "火箭筒"]),
    "pf-89": (["89式火箭筒", "PF-89"], ["89式", "火箭筒"]),
    "qw-1": (["前卫-1"], ["前卫-1", "前卫1"]),
    "qw-2": (["前卫-2"], ["前卫-2", "前卫2"]),
    "type-63a": (["63A式水陆坦克"], ["63A", "水陆坦克"]),
    "type-15": (["15式轻型坦克"], ["15式", "轻型坦克"]),
    "type-86": (["86式步兵战车"], ["86式", "步兵战车"]),
    "type-89-apc": (["89式装甲输送车", "ZSD-89"], ["89式", "装甲输送"]),
    "type-92": (["92式轮式装甲车", "ZSL-92"], ["92式", "ZSL-92"]),
    "type-96": (["96式主战坦克"], ["96式", "主战坦克"]),
    "vt-4": (["VT-4主战坦克", "VT-4"], ["VT-4", "主战坦克"]),
    "vt-5": (["VT-5轻型坦克", "VT-5"], ["VT-5"]),
    "mengshi-3": (["第三代猛士CSK181型防护突击车", "CSK-181", "猛士"], ["CSK181", "猛士", "CSK-181"]),
    "type-054b": (["054B型护卫舰"], ["054B"]),
    "type-055a": (["055型驱逐舰"], ["055", "驱逐"]),
    "type-003": (["福建舰"], ["福建", "航母"]),
    "type-001": (["辽宁舰"], ["辽宁"]),
    "type-002": (["山东舰"], ["山东"]),
    "h-6k": (["轰-6K"], ["轰-6K", "轰-6"]),
    "j-10c": (["歼-10C"], ["歼-10C", "歼-10"]),
    "j-20": (["歼-20"], ["歼-20"]),
    "gj-11": (["攻击-11", "利剑无人机"], ["攻击-11", "利剑"]),
    "wz-7": (["无侦-7", "翔龙无人机"], ["无侦-7", "翔龙"]),
    "wing-loong-ii": (["翼龙-2"], ["翼龙-2", "翼龙Ⅱ"]),
    "type-071": (["071型船坞登陆舰"], ["071", "船坞"]),
    "type-075": (["075型两栖攻击舰", "海南舰"], ["075", "两栖", "海南舰"]),
    "s-300": (["S-300防空导弹", "S-300"], ["S-300"]),
    "s-400": (["S-400防空导弹", "S-400"], ["S-400"]),
    "tor-m1": (["道尔-M1", "Tor-M1"], ["道尔", "Tor"]),
    "type-730": (["730近防炮", "H/PJ-12"], ["730", "近防"]),
    "type-1130": (["1130近防炮", "H/PJ-11"], ["1130", "近防"]),
    "yu-6": (["鱼-6鱼雷"], ["鱼-6", "鱼雷"]),
    "yu-7": (["鱼-7鱼雷"], ["鱼-7", "鱼雷"]),
    "jl-2": (["巨浪-2"], ["巨浪-2", "巨浪2"]),
    "jl-3": (["巨浪-3"], ["巨浪-3", "巨浪3"]),
    "type-815a": (["815A型电子侦察船"], ["815A", "电子侦察"]),
    "type-901": (["901型综合补给舰"], ["901", "补给"]),
    "type-926": (["926型潜艇支援舰"], ["926", "潜艇支援"]),
    "type-927": (["927型海洋监视船"], ["927", "海洋监视"]),
    "type-039a": (["039A型潜艇", "元级潜艇"], ["039A", "元级"]),
    "type-039": (["039型潜艇", "宋级潜艇"], ["039", "宋级"]),
    "kilo-636": (["基洛级潜艇"], ["基洛"]),
    "type-091": (["091型攻击核潜艇"], ["091", "核潜艇"]),
    "type-094": (["094型战略核潜艇"], ["094", "核潜艇"]),
    "type-032": (["032型潜艇"], ["032"]),
}


def to_s(t: str) -> str:
    return (t or "").translate(T2S)


def clean(n: str) -> str:
    return re.sub(r"[（(].*?[）)]", "", n or "").replace("／", "/").strip()


def local_size(eid: str, image_field: str = "") -> int:
    best = 0
    if image_field and str(image_field).startswith("assets/"):
        p = ROOT / image_field
        if p.exists():
            best = max(best, p.stat().st_size)
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = IMG / f"{eid}{ext}"
        if p.exists():
            best = max(best, p.stat().st_size)
    return best


def build_jobs(items, log):
    jobs = []
    for it in items:
        eid = it["id"]
        sz = local_size(eid, it.get("image") or "")
        if sz >= MIN_KEEP:
            continue
        name = clean(it.get("name_zh") or "")
        des = (it.get("designation") or "").strip()
        name_s = to_s(name)
        queries, keys = [], []

        def addq(q):
            q = re.sub(r"\s+", "", q).strip("/-")
            if q and q not in queries and len(q) >= 2:
                queries.append(q)

        def addk(k):
            if k and k not in keys:
                keys.append(k)

        if eid in OVERRIDE:
            qs, ks = OVERRIDE[eid]
            for q in qs:
                addq(q)
            for k in ks:
                addk(k)
        addq(name_s)
        m = re.match(r"Type\s*([0-9]{2,4}[A-Za-z]*)", des, re.I)
        if m:
            code = m.group(1).upper()
            if "驱逐" in name_s:
                addq(f"{code}型驱逐舰")
            elif "护卫" in name_s:
                addq(f"{code}型护卫舰")
            elif "潜" in name_s:
                addq(f"{code}型潜艇")
                addq(f"{code}型核潜艇")
            elif "坦克" in name_s:
                addq(f"{code}式主战坦克")
            elif "登陆" in name_s or "两栖" in name_s:
                addq(f"{code}型登陆舰")
            elif "补给" in name_s:
                addq(f"{code}型补给舰")
            else:
                addq(f"{code}型")
                addq(f"{code}式")
            addk(code)
        m2 = re.match(r"([A-Za-z]{1,4})-?(\d{1,4}[A-Za-z]*)", des)
        if m2:
            pref, num = m2.group(1).upper(), m2.group(2).upper()
            cmap = {
                "J": "歼-", "JH": "歼轰-", "H": "轰-", "Q": "强-", "Y": "运-",
                "Z": "直-", "KJ": "空警-", "DF": "东风-", "CJ": "长剑-", "YJ": "鹰击-",
                "HQ": "红旗-", "PL": "霹雳-", "CH": "彩虹-", "GJ": "攻击-", "WZ": "无侦-",
                "SU": "苏-", "MI": "米-", "KA": "卡-", "HJ": "红箭-", "FN": "飞弩-",
                "HHQ": "海红旗-",
            }
            if pref == "JL":
                addq(f"巨浪-{num}" if ("弹" in name_s or "巨浪" in name_s) else f"教练-{num}")
            elif pref in cmap:
                addq(f"{cmap[pref]}{num}")
            else:
                addq(f"{pref}-{num}")
            addk(f"{pref}-{num}")
            addk(num)
        core = re.sub(r"[A-Za-z0-9\-_\s/]", "", name_s)
        if len(core) >= 2:
            addk(core[:2])
        if len(core) >= 3:
            addk(core[:3])
        for w in ["舰", "艇", "机", "弹", "炮", "坦克", "导弹", "潜艇", "直升", "火箭", "无人", "航母", "步枪", "鱼雷"]:
            if w in name_s:
                addk(w)
        if not queries:
            continue
        score = 0
        if it.get("category") == "vehicle":
            score += 3
        if it.get("category") == "weapon":
            score += 2
        if re.search(r"\d", des):
            score += 2
        if sz == 0:
            score += 2
        if eid in OVERRIDE:
            score += 6
        # retry almost-matched from r3 (had real title in log)
        prev = log.get(eid, {})
        if prev.get("title") and not str(prev.get("title", "")).startswith("百度百科"):
            score += 3
            addq(prev["title"])
        if prev.get("reason") == "no_match_or_image" and eid not in OVERRIDE:
            score -= 1
        jobs.append(
            {
                "id": eid,
                "name_zh": it.get("name_zh"),
                "designation": des,
                "queries": queries[:7],
                "keys": keys[:16],
                "score": score,
                "sz": sz,
                "name_s": name_s,
            }
        )
    jobs.sort(key=lambda x: -x["score"])
    return jobs


class Browser:
    def __init__(self):
        tabs = json.load(urllib.request.urlopen(BASE + "/json/list"))
        page = None
        for t in tabs:
            if t.get("type") == "page" and not t.get("url", "").startswith("chrome"):
                page = t
                break
        if not page:
            page = next(t for t in tabs if t.get("type") == "page")
        self.ws = create_connection(page["webSocketDebuggerUrl"], timeout=40)
        self.mid = 0
        self.call("Page.enable")
        self.call("Runtime.enable")

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

    def goto(self, url, wait=1.3):
        self.call("Page.navigate", {"url": url})
        for _ in range(45):
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
  const title = document.title.replace(/_百度百科$/,'').replace(/-百度百科$/,'').trim();
  const h1 = (document.querySelector('h1')||{}).innerText || '';
  const meta = (document.querySelector('meta[name="image"], meta[property="og:image"]')||{}).content || '';
  const summary = (document.querySelector('.lemma-summary, .J-summary, .main-content, .content, #J-lemma-content')||document.body).innerText.slice(0,800);
  const imgs=[];
  const push=(src,w,h,score)=>{
    if(!src||src.startsWith('data:'))return;
    if(/baike\.png|cms\/static\/baike/i.test(src))return;
    if(!/^https?:/i.test(src))return;
    imgs.push({src,w:w||0,h:h||0,score:score||((w||0)*(h||0))});
  };
  if(meta) push(meta,900,900,1e9);
  for(const i of document.images){ push(i.currentSrc||i.src||i.getAttribute('data-src')||'', i.naturalWidth||0, i.naturalHeight||0); }
  for(const el of document.querySelectorAll('[data-src]')){ push(el.getAttribute('data-src')||'',700,700,4e5); }
  const links=[...document.querySelectorAll('a')].filter(a=>/\/item\//.test(a.href)).slice(0,12).map(a=>({href:a.href,text:(a.innerText||'').trim().slice(0,50)}));
  imgs.sort((a,b)=>b.score-a.score);
  const head=(document.body&&document.body.innerText||'').slice(0,250);
  const captcha=/验证|安全验证|BIOC/.test(head)||/验证/.test(title);
  return {title,h1,summary,captcha,imgs:imgs.slice(0,12),links};
})()
"""


def enlarge(u: str) -> str:
    if not u:
        return u
    base = u.split("?")[0]
    if "bkimg" in base or "bcebos" in base or "/pic/" in base:
        return base + "?x-bce-process=image/quality,Q_90"
    return u


def match(title, summary, keys, name_s):
    blob = (title or "") + " " + (summary or "")
    junk = [
        "游戏", "玉米", "学校", "机车", "列车", "电池", "动画", "高达", "杀虫", "手机",
        "综艺", "演员", "音乐", "小说", "公路", "集装箱", "电源", "电解", "工艺", "可选垂直",
        "进化版", "莎塔", "电蟒", "海妖", "麦道", "驱逐舰" if "火箭" in name_s else None,
    ]
    junk = [j for j in junk if j]
    if any(j in blob for j in junk):
        # allow if also clearly military matching
        pass
    if any(j in blob for j in ["游戏", "玉米", "学校", "机车", "列车", "电池", "动画", "高达", "杀虫", "手机", "综艺", "演员", "音乐", "小说", "公路", "电解", "工艺"]):
        return False
    if title in ("百度百科——全球领先的中文百科全书", "百度百科", "") or title.startswith("百度百科"):
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
    if len(core) >= 2 and core[:2] in (title or "") and any(
        w in blob for w in ["舰", "艇", "机", "弹", "炮", "坦克", "导弹", "潜艇", "直升", "火箭", "无人", "航母", "步枪", "鱼雷", "高炮"]
    ):
        return True
    return False


def download(url, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://baike.baidu.com/"})
    try:
        with urllib.request.urlopen(req, timeout=35) as r:
            data = r.read()
        if len(data) < 4000:
            return False
        im = Image.open(BytesIO(data)).convert("RGB")
        if min(im.size) < 140:
            return False
        if im.size == (350, 350) and len(data) < 30000:
            return False
        if max(im.size) > 1600:
            im.thumbnail((1600, 1600))
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=90, optimize=True)
        return dest.stat().st_size > 4000
    except Exception as e:
        print(f"  dl {e}")
        return False


def main():
    items = json.loads(
        (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8")[
            (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8").index("[") : (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8").rindex("]") + 1
        ]
    )
    log = json.loads(LOG_PATH.read_text(encoding="utf-8")) if LOG_PATH.exists() else {}
    jobs = build_jobs(items, log)
    batch = jobs[:BATCH_SIZE]
    print(f"missing_or_tiny={len(jobs)} batch={len(batch)}", flush=True)
    for j in batch[:15]:
        print(j["score"], j["id"], j["queries"][:2], flush=True)

    b = Browser()
    ok = fail = 0
    captcha_stop = False
    for idx, job in enumerate(batch, 1):
        eid = job["id"]
        print(f"[{idx}/{len(batch)}] {eid} | {job['name_zh']}", flush=True)
        saved = False
        last_title = ""
        urls = []
        for q in job["queries"]:
            urls.append("https://baike.baidu.com/item/" + urllib.parse.quote(q))
        for q in job["queries"][:3]:
            urls.append("https://baike.baidu.com/search?word=" + urllib.parse.quote(q))

        tried = set()
        for url in urls:
            if url in tried:
                continue
            tried.add(url)
            try:
                b.goto(url, wait=1.2)
                info = b.eval(EXTRACT)
            except Exception as e:
                print(f"  eval {e}", flush=True)
                try:
                    b.close()
                except Exception:
                    pass
                time.sleep(0.6)
                try:
                    b = Browser()
                except Exception as e2:
                    print(f"  reconnect fail {e2}", flush=True)
                    captcha_stop = True
                    break
                continue
            if not info:
                continue
            if info.get("captcha"):
                print("  CAPTCHA stop", flush=True)
                captcha_stop = True
                break
            title = info.get("title") or info.get("h1") or ""
            summary = info.get("summary") or ""
            last_title = title
            if "search" in url and info.get("links"):
                for lk in info["links"]:
                    text = lk.get("text") or ""
                    href = lk.get("href") or ""
                    if not href or "/item/" not in href:
                        continue
                    if match(text, text, job["keys"], job["name_s"]) or any(
                        k in text for k in job["keys"] if len(str(k)) >= 2
                    ):
                        if href not in tried:
                            # insert after current
                            urls.append(href)
                if title.startswith("百度百科") or "search" in url:
                    continue
            if not match(title, summary, job["keys"], job["name_s"]):
                print(f"  skip {title[:40]!r}", flush=True)
                continue
            for im in info.get("imgs") or []:
                src = enlarge(im.get("src") or "")
                dest = IMG / f"{eid}.jpg"
                if download(src, dest):
                    sz = list(Image.open(dest).size)
                    print(f"  OK {title} {sz}", flush=True)
                    log[eid] = {
                        "ok": True,
                        "query": url,
                        "title": title,
                        "img_url": src,
                        "path": f"assets/images/{eid}.jpg",
                        "source": "baike_cdp_r4",
                        "size": sz,
                    }
                    ok += 1
                    saved = True
                    break
            if saved:
                break
        if captcha_stop:
            break
        if not saved:
            print(f"  FAIL {last_title[:40]!r}", flush=True)
            log[eid] = {
                "ok": False,
                "reason": "no_match_or_image",
                "title": last_title,
                "queries": job["queries"],
                "round": 4,
            }
            fail += 1
        if idx % 10 == 0:
            LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        b.close()
    except Exception:
        pass
    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    ep = json.loads(EP_PATH.read_text(encoding="utf-8"))
    n = 0
    for eid, res in log.items():
        if not res.get("ok") or not res.get("path"):
            continue
        p = ROOT / res["path"]
        if not p.exists() or p.stat().st_size < 4000:
            continue
        ent = ep.setdefault("items", {}).setdefault(eid, {})
        ent["image"] = res["path"]
        ent["image_credit"] = f"图片来自百度百科《{res.get('title')}》（教育参考）"
        n += 1
    EP_PATH.write_text(json.dumps(ep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nR4 ok={ok} fail={fail} enrich={n} captcha={captcha_stop}", flush=True)


if __name__ == "__main__":
    main()
