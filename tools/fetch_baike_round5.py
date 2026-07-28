#!/usr/bin/env python3
"""Round 5: Baike CDP image fetch for remaining missing/tiny items."""
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
BATCH_SIZE = 110
MIN_KEEP = 25000
SOURCE_TAG = "baike_cdp_r5"
ROUND_N = 5

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

# High-value overrides: id -> (queries, keys) — R5 refined after R4 fails
OVERRIDE = {
    "zbd-08": (["ZBL-08轮式步兵战车", "08式轮式步兵战车", "ZBL08"], ["ZBL-08", "ZBL08", "08式", "轮式步兵战车"]),
    "zsl-10": (["ZSL-10装甲输送车", "08式轮式装甲输送车", "ZSL10"], ["ZSL-10", "ZSL10", "装甲输送"]),
    "zbd-03": (["03式空降步兵战车", "ZBD-03"], ["03式", "ZBD-03", "空降", "步兵战车"]),
    "zsd-89": (["89式装甲输送车", "ZSD-89"], ["89式", "ZSD-89", "装甲输送"]),
    "pcl-181": (["SH-15型155毫米车载加榴炮", "PCL-181车载榴弹炮"], ["SH-15", "PCL-181", "155", "车载"]),
    "pcl-171": (["PCL-171车载榴弹炮", "122毫米卡车炮"], ["PCL-171", "车载榴弹"]),
    "pcl-161": (["PCL-161", "122毫米车载榴弹炮", "PCL161"], ["PCL-161", "PCL161", "122", "车载"]),
    "phz-11": (["PHZ-11火箭炮", "11式122毫米火箭炮"], ["PHZ-11", "火箭炮", "122"]),
    "phl-03": (["PHL-03远程火箭炮", "03式远程火箭炮"], ["PHL-03", "远程火箭", "03式"]),
    "phl-11": (["PHL-11火箭炮", "11式300毫米火箭炮"], ["PHL-11", "火箭炮"]),
    "phl-16": (["PHL-16远程火箭炮", "PCL-191", "191式箱式火箭炮"], ["PHL-16", "PCL-191", "191式"]),
    "pgz-04a": (["PGZ-04A自行高炮", "04A式自行高炮", "25毫米自行高炮"], ["PGZ-04A", "04A", "自行高炮"]),
    "plz-05": (["05式155毫米自行加榴炮", "PLZ-05自行榴弹炮", "PLZ05"], ["PLZ-05", "05式", "155", "自行加榴"]),
    "plz-52": (["PLZ-52自行榴弹炮", "52倍径155毫米自行榴弹炮"], ["PLZ-52", "155", "自行"]),
    "sh-15": (["SH-15型155毫米车载加榴炮", "SH-15车载炮"], ["SH-15", "155", "车载"]),
    "type-093b": (["093型核潜艇", "商级核潜艇", "09III型核潜艇"], ["093", "商级", "核潜艇"]),
    "type-093a": (["093A型核潜艇", "商级核潜艇"], ["093A", "093", "核潜艇"]),
    "type-096": (["096型战略核潜艇", "唐级核潜艇"], ["096", "核潜艇", "战略"]),
    "type-039c": (["039C型潜艇", "元级潜艇"], ["039C", "元级", "潜艇"]),
    "type-039b": (["039B型潜艇", "元级潜艇"], ["039B", "元级"]),
    "asn-209": (["ASN-209无人机", "ASN-209无人侦察机"], ["ASN-209", "无人机", "侦察"]),
    "ch-3": (["彩虹-3无人机", "CH-3无人机"], ["彩虹-3", "CH-3", "无人机"]),
    "ch-6": (["彩虹-6无人机", "CH-6无人机"], ["彩虹-6", "CH-6", "无人机"]),
    "df-15a": (["东风-15A弹道导弹", "东风-15"], ["东风-15", "东风15", "弹道"]),
    "df-15b": (["东风-15B弹道导弹", "东风-15"], ["东风-15", "东风15"]),
    "df-16": (["东风-16弹道导弹"], ["东风-16", "东风16", "弹道"]),
    "df-21": (["东风-21中程弹道导弹"], ["东风-21", "东风21"]),
    "df-21c": (["东风-21C", "东风-21"], ["东风-21", "东风21"]),
    "df-27": (["东风-27", "东风27高超音速"], ["东风-27", "东风27"]),
    "df-31": (["东风-31洲际弹道导弹"], ["东风-31", "东风31"]),
    "df-31b": (["东风-31B", "东风-31"], ["东风-31", "东风31"]),
    "df-41": (["东风-41洲际战略核导弹"], ["东风-41", "东风41"]),
    "yj-18": (["鹰击-18反舰导弹", "鹰击18"], ["鹰击-18", "鹰击18", "反舰"]),
    "yj-21": (["鹰击-21高超音速导弹", "鹰击21"], ["鹰击-21", "鹰击21", "高超音速"]),
    "yj-12": (["鹰击-12反舰导弹"], ["鹰击-12", "鹰击12"]),
    "yj-83": (["鹰击-83反舰导弹"], ["鹰击-83", "鹰击83"]),
    "yj-62": (["鹰击-62反舰导弹"], ["鹰击-62", "鹰击62"]),
    "hq-16": (["红旗-16地空导弹"], ["红旗-16", "红旗16"]),
    "hq-17": (["红旗-17防空导弹系统"], ["红旗-17", "红旗17"]),
    "hq-17a": (["红旗-17A", "红旗-17"], ["红旗-17", "红旗17"]),
    "hq-22": (["红旗-22防空导弹", "红旗22"], ["红旗-22", "红旗22", "防空"]),
    "hq-9b": (["红旗-9B", "红旗-9防空导弹"], ["红旗-9", "红旗9"]),
    "hq-7": (["红旗-7近程防空导弹", "海红旗-7"], ["红旗-7", "红旗7", "近程"]),
    "hq-7b": (["红旗-7B", "红旗-7"], ["红旗-7", "红旗7"]),
    "hhq-9": (["海红旗-9", "红旗-9"], ["海红旗-9", "红旗-9"]),
    "hhq-10": (["海红旗-10", "HHQ-10"], ["海红旗-10", "红旗-10"]),
    "hhq-16": (["海红旗-16", "红旗-16"], ["海红旗-16", "红旗-16"]),
    "pl-15": (["霹雳-15空空导弹"], ["霹雳-15", "霹雳15"]),
    "pl-10": (["霹雳-10空空导弹"], ["霹雳-10", "霹雳10"]),
    "pl-12": (["霹雳-12空空导弹"], ["霹雳-12", "霹雳12"]),
    "pl-17": (["霹雳-17空空导弹", "霹雳17"], ["霹雳-17", "霹雳17", "空空"]),
    "j-11a": (["歼-11A", "歼-11战斗机"], ["歼-11", "歼11"]),
    "j-8f": (["歼-8F", "歼-8战斗机"], ["歼-8", "歼8"]),
    "su-30mk2": (["苏-30MK2", "苏-30战斗机"], ["苏-30", "苏30", "MK2"]),
    "su-35": (["苏-35战斗机", "苏-35S"], ["苏-35", "苏35"]),
    "su-27ubk": (["苏-27UBK", "苏-27战斗机"], ["苏-27", "苏27", "UBK"]),
    "h-6k": (["轰-6K轰炸机", "轰-6K"], ["轰-6K", "轰-6", "轰炸机"]),
    "h-6h": (["轰-6H", "轰-6轰炸机"], ["轰-6H", "轰-6"]),
    "y-9": (["运-9运输机", "运-9"], ["运-9", "运9", "运输机"]),
    "y-8gx": (["运-8特种飞机", "运-8"], ["运-8", "运8"]),
    "y-20b": (["运-20运输机", "运-20"], ["运-20", "运20"]),
    "z-18": (["直-18直升机", "直-18"], ["直-18", "直18"]),
    "kj-200": (["空警-200预警机"], ["空警-200", "空警200", "预警"]),
    "kj-600": (["空警-600预警机"], ["空警-600", "空警600"]),
    "j-15d": (["歼-15D电子战飞机", "歼-15"], ["歼-15", "电子战"]),
    "il-76": (["伊尔-76运输机"], ["伊尔-76", "Il-76"]),
    "il-78": (["伊尔-78加油机"], ["伊尔-78", "Il-78"]),
    "ka-31": (["卡-31预警直升机", "卡-31"], ["卡-31", "卡31"]),
    "type-920": (["和平方舟号医院船", "和平方舟"], ["和平方舟", "医院船"]),
    "hj-12": (["红箭-12反坦克导弹"], ["红箭-12", "红箭12"]),
    "hj-10": (["红箭-10反坦克导弹"], ["红箭-10", "红箭10"]),
    "hj-8": (["红箭-8反坦克导弹"], ["红箭-8", "红箭8"]),
    "hj-9": (["红箭-9反坦克导弹"], ["红箭-9", "红箭9"]),
    "fn-6": (["飞弩-6便携式防空导弹"], ["飞弩-6", "飞弩6", "防空"]),
    "fn-16": (["飞弩-16便携式防空导弹"], ["飞弩-16", "飞弩16"]),
    "pf-98": (["98式反坦克火箭筒", "PF-98"], ["98式", "PF-98", "火箭筒"]),
    "pf-89": (["89式反坦克火箭筒", "PF-89"], ["89式", "火箭筒"]),
    "qw-1": (["前卫-1便携式防空导弹"], ["前卫-1", "前卫1"]),
    "qw-2": (["前卫-2便携式防空导弹"], ["前卫-2", "前卫2"]),
    "type-63a": (["63A式水陆坦克"], ["63A", "水陆坦克"]),
    "type-86": (["86式步兵战车", "ZBD-86"], ["86式", "步兵战车"]),
    "type-89-apc": (["89式装甲输送车", "ZSD-89"], ["89式", "装甲输送"]),
    "type-92": (["92式轮式装甲车", "ZSL-92"], ["92式", "ZSL-92"]),
    "type-021": (["021型导弹艇", "黄蜂级导弹艇"], ["021", "导弹艇", "黄蜂"]),
    "type-19-ifv": (["19式步兵战车", "VN22"], ["19式", "步兵战车"]),
    "s-300": (["S-300防空导弹系统", "S-300"], ["S-300", "防空导弹"]),
    "s-400": (["S-400防空导弹系统", "S-400"], ["S-400"]),
    "tor-m1": (["道尔-M1防空导弹", "Tor-M1"], ["道尔", "Tor-M1"]),
    "yu-6": (["鱼-6鱼雷", "鱼6鱼雷"], ["鱼-6", "鱼6", "鱼雷"]),
    "yu-7": (["鱼-7鱼雷", "鱼7轻型鱼雷"], ["鱼-7", "鱼7", "鱼雷"]),
    "yu-10": (["鱼-10鱼雷"], ["鱼-10", "鱼10", "鱼雷"]),
    "jl-2": (["巨浪-2潜射弹道导弹"], ["巨浪-2", "巨浪2"]),
    "type-901": (["901型综合补给舰"], ["901", "补给舰"]),
    "type-927": (["927型海洋监视船", "天狼星级"], ["927", "海洋监视"]),
    "kilo-636": (["基洛级潜艇", "基洛级"], ["基洛", "潜艇"]),
    "type-091": (["091型核潜艇", "汉级核潜艇"], ["091", "汉级", "核潜艇"]),
    "type-094": (["094型战略核潜艇", "晋级核潜艇"], ["094", "晋级", "核潜艇"]),
    "type-032": (["032型潜艇", "清级潜艇"], ["032", "清级"]),
    "type-054": (["054型导弹护卫舰", "马鞍山舰"], ["054型", "护卫舰"]),
    "type-022": (["022型导弹艇", "候鸟级"], ["022", "导弹艇"]),
    "type-056": (["056型轻型护卫舰"], ["056", "护卫舰"]),
    "dzj-08": (["DZJ-08", "08式火箭筒", "单兵火箭"], ["DZJ-08", "08式", "火箭"]),
    "pp-87": (["87式迫击炮", "82毫米迫击炮"], ["87式", "迫击炮", "82"]),
    "pp-89": (["89式迫击炮", "100毫米迫击炮"], ["89式", "迫击炮"]),
    "qlg-10": (["QLG-10", "枪挂榴弹发射器"], ["QLG-10", "榴弹发射"]),
    "qjz-89": (["QJZ-89", "89式重机枪", "12.7毫米重机枪"], ["QJZ-89", "89式", "重机枪"]),
    "gcl-111": (["GCL-111", "84式坦克架桥车", "架桥车"], ["架桥", "GCL"]),
    "type-84-minelayer": (["84式布雷车", "履带式布雷车"], ["84式", "布雷"]),
    "pll-01": (["PLL-01", "100毫米突击炮"], ["PLL-01", "突击炮"]),
    "pcz-171": (["PCZ-171", "突击车"], ["PCZ-171"]),
    "fb-6c": (["FB-6C", "防空导弹"], ["FB-6", "防空"]),
    "cx-1": (["CX-1超音速反舰导弹", "CX-1"], ["CX-1", "反舰"]),
    "cm-401": (["CM-401反舰弹道导弹", "CM-401"], ["CM-401", "反舰"]),
    "ba-9": (["蓝箭-9", "蓝箭9导弹"], ["蓝箭-9", "蓝箭9"]),
    "ld-10": (["雷霆-10", "LD-10反辐射导弹"], ["雷霆-10", "LD-10"]),
    "gj-11": (["攻击-11无人机", "利剑无人机"], ["攻击-11", "利剑"]),
    "wz-5": (["无侦-5", "长虹无人机"], ["无侦-5", "无人机"]),
    "z-8g": (["直-8G", "直-8直升机"], ["直-8G", "直-8"]),
    "wing-loong-1": (["翼龙-1无人机", "翼龙无人机"], ["翼龙-1", "翼龙"]),
    "bzk-005": (["BZK-005无人机"], ["BZK-005", "无人机"]),
    "cj-20": (["长剑-20巡航导弹", "长剑20"], ["长剑-20", "长剑20"]),
    "hq-22": (["红旗-22中远程防空导弹"], ["红旗-22", "红旗22"]),
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
            score -= 4
        if prev.get("source") in ("baike_cdp_r4", "baike_cdp_r3") and prev.get("ok") and sz >= 8000:
            score -= 8  # already have something; only if tiny
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
        ]
    ):
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
    print(f"\nR5 ok={ok} fail={fail} enrich={n} captcha={captcha_stop}", flush=True)


if __name__ == "__main__":
    main()
