#!/usr/bin/env python3
"""Round 6: Baike CDP image fetch for remaining missing/tiny items."""
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
BATCH_SIZE = 100
MIN_KEEP = 25000
SOURCE_TAG = "baike_cdp_r6"
ROUND_N = 6

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

# High-value overrides: id -> (queries, keys) — R6 focus remaining gaps
OVERRIDE = {
    "zbd-08": (["08式轮式步兵战车", "ZBL-08", "08式步兵战车"], ["08式", "ZBL-08", "轮式", "步兵战车"]),
    "zsl-10": (["08式轮式装甲输送车", "ZSL-10", "ZBL-08装甲"], ["08式", "ZSL-10", "装甲输送"]),
    "zbd-03": (["03式空降步兵战车", "ZBD-03空降战车"], ["03式", "ZBD-03", "空降"]),
    "plz-05": (["PLZ05式自行加榴炮", "05式155毫米自行加榴炮", "PLZ-05"], ["PLZ", "05式", "155", "自行加榴炮"]),
    "pcl-171": (["PCL-171", "122毫米车载榴弹炮"], ["PCL-171", "车载", "122"]),
    "phz-11": (["PHZ-11", "11式履带火箭炮", "122毫米火箭炮"], ["PHZ-11", "火箭炮"]),
    "pgz-04a": (["04A式25毫米自行高炮", "PGZ-04A", "PGZ04A"], ["04A", "自行高炮", "25毫米"]),
    "phl-11": (["PHL-11", "11式火箭炮"], ["PHL-11", "火箭炮"]),
    "phl-16": (["PHL-16", "PCL-191箱式火箭炮", "191式远程火箭炮"], ["PHL-16", "PCL-191", "191"]),
    "asn-209": (["ASN-209", "ASN209无人机"], ["ASN-209", "ASN209", "无人机"]),
    "yj-18": (["鹰击-18", "鹰击18反舰导弹", "YJ-18"], ["鹰击-18", "鹰击18", "YJ-18", "反舰导弹"]),
    "pl-17": (["霹雳-17", "霹雳17空空导弹", "PL-17"], ["霹雳-17", "霹雳17", "PL-17"]),
    "pl-9": (["霹雳-9", "霹雳9空空导弹"], ["霹雳-9", "霹雳9"]),
    "hq-22": (["红旗-22", "红旗22防空导弹系统"], ["红旗-22", "红旗22"]),
    "hq-16": (["红旗-16", "红旗16地空导弹"], ["红旗-16", "红旗16"]),
    "hq-17": (["红旗-17", "红旗17防空导弹"], ["红旗-17", "红旗17"]),
    "hq-17a": (["红旗-17A", "红旗-17"], ["红旗-17", "红旗17"]),
    "hhq-9": (["海红旗-9", "HHQ-9"], ["海红旗-9", "红旗-9"]),
    "hhq-10": (["海红旗-10近防导弹", "HHQ-10"], ["海红旗-10", "红旗-10"]),
    "hhq-16": (["海红旗-16", "HHQ-16"], ["海红旗-16", "红旗-16"]),
    "fn-6": (["飞弩-6", "FN-6便携式防空导弹"], ["飞弩-6", "飞弩6", "FN-6"]),
    "df-15a": (["东风-15A", "东风15甲", "DF-15A弹道导弹"], ["东风-15", "东风15", "弹道导弹"]),
    "df-15b": (["东风-15B", "东风15乙"], ["东风-15", "东风15", "弹道"]),
    "df-16": (["东风-16弹道导弹", "东风16"], ["东风-16", "东风16", "弹道导弹"]),
    "df-21": (["东风-21中程弹道导弹"], ["东风-21", "东风21", "弹道导弹"]),
    "df-21c": (["东风-21C", "东风21丙"], ["东风-21", "东风21"]),
    "df-27": (["东风-27弹道导弹", "东风27"], ["东风-27", "东风27", "弹道导弹"]),
    "df-3": (["东风-3中程弹道导弹", "东风3号"], ["东风-3", "东风3", "弹道导弹"]),
    "df-4": (["东风-4远程弹道导弹", "东风4号"], ["东风-4", "东风4", "弹道导弹"]),
    "cj-20": (["长剑-20", "长剑20巡航导弹", "空射巡航导弹"], ["长剑-20", "长剑20", "巡航导弹"]),
    "yu-6": (["鱼-6重型鱼雷", "鱼6鱼雷", "Yu-6鱼雷"], ["鱼-6", "鱼6", "重型鱼雷"]),
    "yu-7": (["鱼-7轻型鱼雷", "鱼7鱼雷", "Yu-7"], ["鱼-7", "鱼7", "轻型鱼雷"]),
    "type-093a": (["093A型核潜艇", "商级核潜艇"], ["093A", "093", "核潜艇", "商级"]),
    "type-096": (["中国下一代战略核潜艇", "096型核潜艇"], ["096", "战略核潜艇"]),
    "type-039c": (["039C型潜艇", "元级潜艇"], ["039C", "元级"]),
    "type-039b": (["039B型潜艇", "元级潜艇"], ["039B", "元级"]),
    "gcl-111": (["84式坦克架桥车", "坦克架桥车"], ["架桥车", "84式", "坦克"]),
    "type-84-minelayer": (["84式布雷系统", "履带布雷车", "机械布雷"], ["布雷", "84式"]),
    "gsl-131": (["131式扫雷车", "扫雷破障车", "GSL-131"], ["扫雷", "破障"]),
    "type-654-arv": (["654式装甲抢救车", "装甲抢救车"], ["654", "抢救车", "装甲"]),
    "z-21": (["直-21", "武装直升机"], ["直-21", "武装直升"]),
    "kj-200": (["空警-200", "空警200预警机"], ["空警-200", "空警200", "预警机"]),
    "kj-600": (["空警-600", "空警600"], ["空警-600", "空警600"]),
    "j-15d": (["歼-15D", "歼15电子战"], ["歼-15", "电子战"]),
    "il-76": (["伊尔-76", "Il-76运输机"], ["伊尔-76", "Il-76"]),
    "il-78": (["伊尔-78", "Il-78加油机"], ["伊尔-78", "Il-78"]),
    "ka-31": (["卡-31", "卡31预警直升机"], ["卡-31", "卡31"]),
    "s-300": (["S-300防空导弹", "S-300PMU"], ["S-300", "防空导弹"]),
    "s-400": (["S-400防空导弹系统", "凯旋防空"], ["S-400", "凯旋"]),
    "hj-12": (["红箭-12", "红箭12反坦克导弹"], ["红箭-12", "红箭12"]),
    "hj-10": (["红箭-10", "红箭10反坦克导弹"], ["红箭-10", "红箭10"]),
    "hj-8": (["红箭-8反坦克导弹"], ["红箭-8", "红箭8"]),
    "hj-9": (["红箭-9反坦克导弹"], ["红箭-9", "红箭9"]),
    "hj-11": (["红箭-11", "红箭11"], ["红箭-11", "红箭11"]),
    "pf-98": (["98式反坦克火箭筒", "PF98"], ["98式", "火箭筒", "反坦克"]),
    "qw-1": (["前卫-1", "前卫1便携式防空导弹"], ["前卫-1", "前卫1"]),
    "qw-2": (["前卫-2", "前卫2便携式防空导弹"], ["前卫-2", "前卫2"]),
    "type-86": (["86式步兵战车", "ZBD-86"], ["86式", "步兵战车"]),
    "type-92": (["92式轮式装甲车", "ZSL-92"], ["92式", "ZSL-92", "轮式装甲"]),
    "type-63a": (["63A式水陆坦克"], ["63A", "水陆坦克"]),
    "type-054": (["054型导弹护卫舰"], ["054型", "护卫舰"]),
    "type-022": (["022型导弹艇"], ["022型", "导弹艇"]),
    "type-056": (["056型护卫舰"], ["056型", "护卫舰"]),
    "type-901": (["901型综合补给舰", "呼伦湖舰"], ["901型", "补给舰"]),
    "type-091": (["091型核潜艇", "汉级核潜艇"], ["091", "汉级", "核潜艇"]),
    "type-094": (["094型战略核潜艇", "晋级核潜艇"], ["094", "晋级"]),
    "type-032": (["032型潜艇", "清级"], ["032", "清级"]),
    "kilo-636": (["基洛级潜艇", "基洛级"], ["基洛"]),
    "jl-2": (["巨浪-2", "巨浪2潜射弹道导弹"], ["巨浪-2", "巨浪2"]),
    "type-920": (["和平方舟号", "和平方舟医院船"], ["和平方舟", "医院船"]),
    "ba-9": (["蓝箭-9", "蓝箭9空地导弹"], ["蓝箭-9", "蓝箭9"]),
    "cx-1": (["CX-1反舰导弹", "超音速反舰导弹出口"], ["CX-1", "反舰导弹"]),
    "cm-401": (["CM-401", "反舰弹道导弹"], ["CM-401", "反舰弹道"]),
    "wz-5": (["无侦-5", "长虹一号无人机", "高空无人侦察机"], ["无侦", "长虹", "无人侦察"]),
    "gj-11": (["攻击-11", "利剑无人机", "GJ-11"], ["攻击-11", "利剑", "GJ-11"]),
    "ch-2": (["彩虹-2无人机", "CH-2无人机"], ["彩虹-2", "CH-2", "无人机"]),
    "pl-21": (["霹雳-21", "霹雳21空空导弹"], ["霹雳-21", "霹雳21"]),
    "gb-6": (["GB-6滑翔制导炸弹", "GB6炸弹"], ["GB-6", "滑翔", "制导炸弹"]),
    "ls-500j": (["雷石-500", "LS-500制导炸弹"], ["雷石", "LS-500", "制导炸弹"]),
    "type-85-122": (["85式122毫米自行榴弹炮", "85式自行火炮"], ["85式", "122", "自行"]),
    "type-83-273": (["83式273毫米火箭炮"], ["83式", "273", "火箭炮"]),
    "type-82-130": (["82式130毫米火箭炮"], ["82式", "130", "火箭炮"]),
    "type-81-122": (["81式122毫米火箭炮", "81式火箭炮"], ["81式", "122", "火箭炮"]),
    "w85-hmg": (["W85高射机枪", "12.7毫米高射机枪"], ["W85", "高射机枪", "12.7"]),
    "type-77-hmg": (["77式高射机枪", "77式12.7毫米"], ["77式", "高射机枪"]),
    "fhj-84": (["84式火箭筒", "双管燃烧火箭筒"], ["84式", "火箭筒", "燃烧"]),
    "pp-89": (["100毫米迫击炮", "89式100毫米迫击炮"], ["100毫米", "迫击炮", "89式"]),
    "qlg-10": (["QLG-10榴弹发射器", "10式枪挂榴弹"], ["QLG-10", "枪挂榴弹", "榴弹发射器"]),
    "pll-01": (["PLL-01突击炮", "100毫米轮式突击炮"], ["PLL-01", "突击炮", "100毫米"]),
    "jy-27": (["JY-27雷达", "警戒-27雷达"], ["JY-27", "警戒-27", "雷达"]),
    "ylc-8b": (["YLC-8B", "反隐身雷达"], ["YLC-8B", "雷达"]),
    "slc-2": (["SLC-2炮位侦察雷达", "炮兵定位雷达"], ["SLC-2", "炮位", "雷达"]),
    "jyl-1": (["JYL-1雷达", "三坐标雷达"], ["JYL-1", "三坐标", "雷达"]),
    "type-19-ifv": (["19式步兵战车", "VN-22", "出口轮式步兵战车"], ["19式", "VN-22", "步兵战车"]),
    "su-35": (["苏-35战斗机", "苏-35S"], ["苏-35", "苏35"]),
    "h-6k": (["轰-6K", "轰-6K轰炸机"], ["轰-6K", "轰6K"]),
    "z-18": (["直-18", "直-18直升机"], ["直-18", "直18"]),
    "pcl-181": (["SH-15型155毫米车载加榴炮", "PCL-181"], ["SH-15", "PCL-181", "155"]),
    "sh-15": (["SH-15型155毫米车载加榴炮"], ["SH-15", "155", "车载"]),
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
            score += 3
        elif sz < MIN_KEEP:
            score += 1  # retry tiny
        if eid in OVERRIDE:
            score += 10
        prev = log.get(eid, {})
        # already good from prior CDP — skip (handled by MIN_KEEP)
        title = str(prev.get("title") or "")
        if title and not title.startswith("百度百科") and "百科全书" not in title:
            score += 2
            if eid in OVERRIDE or prev.get("ok") is False:
                addq(title)
        # demote hopeless r4 fails without override
        if prev.get("reason") == "no_match_or_image" and eid not in OVERRIDE:
            score -= 5
        if str(prev.get("reason", "")).startswith("strict_clean") and eid not in OVERRIDE:
            score -= 3
        if prev.get("source") in ("baike_cdp_r4", "baike_cdp_r3", "baike_cdp_r5") and prev.get("ok") and sz >= 8000:
            score -= 8  # already have something; only if tiny
        if prev.get("round") is None and sz == 0:
            score += 2  # never attempted
        jobs.append(
            {
                "id": eid,
                "name_zh": it.get("name_zh"),
                "designation": des,
                "queries": queries[:8],
                "keys": keys[:18],
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

    def suggest(self, q: str):
        """Resolve lemma URLs via Baike suggest API inside the browser (cookies)."""
        q_js = json.dumps(q)
        expr = f"""
        (async () => {{
          try {{
            const r = await fetch('https://baike.baidu.com/api/searchui/suggest?wd='+encodeURIComponent({q_js})+'&enc=utf8', {{credentials:'include'}});
            const j = await r.json();
            const list = j.list || (j.data && j.data.list) || j.result || [];
            return (list || []).slice(0, 10).map(x => {{
              const title = x.lemmaTitle || x.title || x.name || x.lemma || '';
              const id = x.lemmaId || x.id || x.encLemmaId || '';
              let url = x.lemmaUrl || x.url || '';
              if (!url && title) {{
                url = 'https://baike.baidu.com/item/' + encodeURIComponent(title) + (id ? ('/' + id) : '');
              }}
              if (url && url.startsWith('/')) url = 'https://baike.baidu.com' + url;
              return {{title, url, id: String(id)}};
            }}).filter(x => x.url || x.title);
          }} catch (e) {{
            return [{{error: String(e)}}];
          }}
        }})()
        """
        try:
            return self.eval(expr) or []
        except Exception:
            return []


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
    if any(
        j in blob
        for j in [
            "游戏", "玉米", "学校", "机车", "列车", "电池", "动画", "高达", "杀虫", "手机",
            "综艺", "演员", "音乐", "小说", "公路", "电解", "工艺", "俱乐部", "广场", "天语",
            "雷瓦", "桑塔纳", "琦基", "彩虹网", "NVH-1", "米格-19", "风暴之影", "代号021",
            "单壳体潜艇", "可选垂直", "莎塔", "电蟒", "海妖", "麦道", "谷神星", "利·卡兹",
            "小米", "手环", "快干胶", "东风小康", "洒水车", "骁龙", "三星", "三菱", "杨太极",
            "德恩特", "柴油机车", "大气光学", "模板漆", "XIAOMI", "VBCI", "红缨-6",
            "自动步枪", "冲锋枪", "安全验证", "雄风",
        ]
    ):
        return False
    if title in ("百度百科——全球领先的中文百科全书", "百度百科", "") or title.startswith("百度百科"):
        return False
    # reject civil when military id/name expects weapons
    if any(w in name_s for w in ["导弹", "鱼雷", "火箭", "坦克", "战车", "潜艇", "飞机", "舰"]):
        if any(w in blob for w in ["汽车", "轿车", "手机", "手表", "胶水", "电梯", "空调"]):
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
        # Prefer suggest-API resolved lemmas (more accurate than raw /item/name)
        for q in job["queries"][:4]:
            for sug in b.suggest(q):
                if not isinstance(sug, dict):
                    continue
                st = sug.get("title") or ""
                su = sug.get("url") or ""
                if su and match(st, st, job["keys"], job["name_s"]):
                    if su not in urls:
                        urls.append(su)
                elif su and any(k and k in st for k in job["keys"] if len(str(k)) >= 2):
                    if su not in urls:
                        urls.append(su)
            time.sleep(0.15)
        for q in job["queries"]:
            urls.append("https://baike.baidu.com/item/" + urllib.parse.quote(q))
            # mobile lemma sometimes less captcha
            urls.append("https://wapbaike.baidu.com/item/" + urllib.parse.quote(q))
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
                    # prefer larger than existing tiny
                    if job["sz"] and dest.stat().st_size < job["sz"]:
                        print(f"  skip smaller than existing {dest.stat().st_size}<{job['sz']}", flush=True)
                        dest.unlink(missing_ok=True)
                        continue
                    sz = list(Image.open(dest).size)
                    print(f"  OK {title} {sz}", flush=True)
                    log[eid] = {
                        "ok": True,
                        "query": url,
                        "title": title,
                        "img_url": src,
                        "path": f"assets/images/{eid}.jpg",
                        "source": SOURCE_TAG,
                        "round": ROUND_N,
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
                "round": ROUND_N,
            }
            fail += 1
        if idx % 8 == 0:
            LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(0.35)

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
    print(f"\nR6 ok={ok} fail={fail} enrich={n} captcha={captcha_stop}", flush=True)


if __name__ == "__main__":
    main()
