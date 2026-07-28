#!/usr/bin/env python3
"""
從百度百科（wapbaike）為缺圖裝備下載主圖。
嚴格規則：條目標題必須與型號/名稱關鍵字相符，否則跳過。
用法：
  python3 tools/fetch_baike_images.py              # 處理全部缺圖
  python3 tools/fetch_baike_images.py --limit 40   # 先跑前 40 筆
  python3 tools/fetch_baike_images.py --ids type-055,j-20
  python3 tools/fetch_baike_images.py --dry-run
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
IMG_DIR = ROOT / "assets" / "images"
LOG_PATH = ROOT / "data" / "baike_image_log.json"
MISSING_PATH = ROOT / "data" / "missing_for_baike.json"

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
)

# 繁→簡僅單字（str.maketrans 限制）
T2S = str.maketrans(
    {
        "驅": "驱", "艦": "舰", "護": "护", "衛": "卫", "潛": "潜", "彈": "弹",
        "導": "导", "戰": "战", "鬥": "斗", "機": "机", "轟": "轰", "運": "运",
        "輸": "输", "預": "预", "昇": "升", "無": "无", "偵": "侦", "擊": "击",
        "殲": "歼", "強": "强", "襲": "袭", "裝": "装", "砲": "炮", "槍": "枪",
        "飛": "飞", "東": "东", "風": "风", "長": "长", "劍": "剑", "鷹": "鹰",
        "紅": "红", "靂": "雳", "魚": "鱼", "級": "级", "陸": "陆", "軍": "军",
        "進": "进", "雙": "双", "載": "载", "兩": "两", "棲": "栖", "補": "补",
        "給": "给", "醫": "医", "測": "测", "輕": "轻", "車": "车", "輪": "轮",
        "帶": "带", "牽": "牵", "揮": "挥", "後": "后", "單": "单", "頭": "头",
        "視": "视", "儀": "仪", "練": "练", "電": "电", "蹤": "踪", "際": "际",
        "遠": "远", "歷": "历", "銷": "销", "發": "发", "號": "号", "龍": "龙",
        "鳳": "凤", "鯊": "鲨", "鯨": "鲸", "蘇": "苏", "爾": "尔", "圖": "图",
        "現": "现", "遼": "辽", "寧": "宁", "漢": "汉", "晉": "晋", "羅": "罗",
        "歐": "欧", "滬": "沪", "凱": "凯", "島": "岛", "鷲": "鹫", "鴻": "鸿",
        "堅": "坚", "蠍": "蝎", "雲": "云", "鯤": "鲲", "鵬": "鹏", "獵": "猎",
        "衝": "冲", "鋒": "锋", "賓": "宾", "確": "确", "聲": "声", "攜": "携",
        "數": "数", "舊": "旧", "種": "种", "討": "讨", "論": "论", "開": "开",
        "隊": "队", "變": "变", "備": "备", "關": "关",
    }
)


def to_simplified(text: str) -> str:
    """軍事條目足夠用的繁→簡（不全表，缺字時保留原文仍可查數字型號）。"""
    if not text:
        return ""
    s = text.translate(T2S)
    pairs = [
        ("擊", "击"), ("彈", "弹"), ("導", "导"), ("戰", "战"), ("機", "机"), ("艦", "舰"),
        ("潛", "潜"), ("護", "护"), ("衛", "卫"), ("驅", "驱"), ("飛", "飞"), ("槍", "枪"),
        ("砲", "炮"), ("車", "车"), ("東", "东"), ("風", "风"), ("長", "长"), ("劍", "剑"),
        ("紅", "红"), ("無", "无"), ("偵", "侦"), ("轟", "轰"), ("殲", "歼"), ("強", "强"),
        ("運", "运"), ("預", "预"), ("電", "电"), ("裝", "装"), ("級", "级"), ("號", "号"),
        ("雙", "双"), ("載", "载"), ("兩", "两"), ("棲", "栖"), ("輕", "轻"), ("單", "单"),
        ("後", "后"), ("備", "备"), ("種", "种"), ("確", "确"), ("聲", "声"), ("攜", "携"),
        ("數", "数"), ("舊", "旧"), ("隊", "队"), ("變", "变"), ("論", "论"), ("討", "讨"),
        ("開", "开"), ("關", "关"), ("際", "际"), ("遠", "远"), ("進", "进"), ("發", "发"),
        ("陸", "陆"), ("軍", "军"), ("蘇", "苏"), ("爾", "尔"), ("圖", "图"), ("現", "现"),
        ("遼", "辽"), ("寧", "宁"), ("羅", "罗"), ("歐", "欧"), ("滬", "沪"), ("凱", "凯"),
        ("島", "岛"), ("龍", "龙"), ("鯊", "鲨"), ("鯨", "鲸"), ("蠍", "蝎"), ("鴻", "鸿"),
        ("堅", "坚"), ("雲", "云"), ("鯤", "鲲"), ("鵬", "鹏"), ("鷹", "鹰"), ("獵", "猎"),
        ("衝", "冲"), ("鋒", "锋"), ("賓", "宾"), ("視", "视"), ("儀", "仪"), ("揮", "挥"),
        ("醫", "医"), ("測", "测"), ("掃", "扫"), ("補", "补"), ("給", "给"), ("輪", "轮"),
        ("牽", "牵"), ("銷", "销"), ("歷", "历"), ("魚", "鱼"), ("練", "练"), ("襲", "袭"),
        ("際", "际"), ("陞", "升"), ("昇", "升"), ("臺", "台"), ("灣", "湾"), ("國", "国"),
        ("們", "们"), ("這", "这"), ("還", "还"), ("與", "与"), ("為", "为"), ("於", "于"),
        ("從", "从"), ("對", "对"), ("會", "会"), ("說", "说"), ("經", "经"), ("過", "过"),
    ]
    for a, b in pairs:
        s = s.replace(a, b)
    return s


def load_items():
    t = (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8")
    return json.loads(t[t.index("[") : t.rindex("]") + 1])


def has_local_image(item_id: str, image_field: str = "") -> bool:
    if image_field and image_field.startswith("assets/"):
        p = ROOT / image_field
        if p.exists() and p.stat().st_size > 1000:
            return True
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        p = IMG_DIR / f"{item_id}{ext}"
        if p.exists() and p.stat().st_size > 1000:
            return True
    return False


def clean_name(name_zh: str) -> str:
    s = name_zh or ""
    s = re.sub(r"[（(].*?[）)]", "", s)
    s = s.replace("／", "/").strip()
    return s


def candidate_queries(item: dict) -> list[str]:
    """產生百度百科查詢詞（簡體），優先精準。"""
    des = (item.get("designation") or "").strip()
    name = clean_name(item.get("name_zh") or "")
    name_s = to_simplified(name)
    des_s = to_simplified(des)
    sub = (item.get("subcategory") or "").lower()
    branch = item.get("branch") or ""
    qs: list[str] = []

    def add(q: str):
        q = re.sub(r"\s+", "", q).strip(" /-")
        if q and q not in qs and len(q) >= 2:
            qs.append(q)

    # 直接中文名
    add(name_s)
    # 去掉尾綴「型/式」重複
    add(re.sub(r"(战斗机|轰炸机|驱逐舰|护卫舰|潜艇|坦克|步兵战车|直升机)$", "", name_s))

    # 型號規則
    m = re.match(r"Type\s*([0-9]{2,4}[A-Za-z]*)", des, re.I)
    if m:
        code = m.group(1).upper().replace("TYPE", "")
        # 依子類加後綴
        if any(k in sub for k in ["destroyer", "ddg"]) or "驱逐" in name_s:
            add(f"{code}型驱逐舰")
            add(f"{code}型导弹驱逐舰")
        elif any(k in sub for k in ["frigate", "ffg", "corvette"]) or "护卫" in name_s:
            add(f"{code}型护卫舰")
            add(f"{code}型导弹护卫舰")
        elif "submarine" in sub or "潜" in name_s:
            add(f"{code}型潜艇")
            add(f"{code}型核潜艇")
        elif "carrier" in sub or "航母" in name_s:
            add(f"{code}型航空母舰")
        elif "landing" in sub or "两栖" in name_s or "登陆" in name_s:
            add(f"{code}型登陆舰")
            add(f"{code}型船坞登陆舰")
            add(f"{code}型两栖攻击舰")
        elif "replenish" in sub or "补给" in name_s:
            add(f"{code}型补给舰")
            add(f"{code}型综合补给舰")
        elif "mbt" in sub or "坦克" in name_s:
            add(f"{code}式坦克")
            add(f"{code}式主战坦克")
        else:
            add(f"{code}型")
            add(f"{code}式")

    # 代號如 J-20, H-6, DF-41, Z-10, HQ-9, YJ-18, PL-15, KJ-500
    m2 = re.match(r"([A-Za-z]{1,4})-?(\d{1,3}[A-Za-z]*)", des)
    if m2:
        pref, num = m2.group(1).upper(), m2.group(2).upper()
        mapping = {
            "J": "歼-",
            "JH": "歼轰-",
            "H": "轰-",
            "Q": "强-",
            "Y": "运-",
            "Z": "直-",
            "KJ": "空警-",
            "DF": "东风-",
            "CJ": "长剑-",
            "YJ": "鹰击-",
            "HQ": "红旗-",
            "HHQ": "海红旗-",
            "HJ": "红箭-",
            "PL": "霹雳-",
            "KD": "空地-",
            "FN": "飞弩-",
            "QW": "前卫-",
            "CH": "彩虹-",
            "GJ": "攻击-",
            "WZ": "无侦-",
            "SU": "苏-",
            "MI": "米-",
            "KA": "卡-",
            "IL": "伊尔-",
            "TU": "图-",
            "YY": "运油-",
            "HY": "轰油-",
            "KQ": "空潜-",
            "FC": "鹘鹰",
            "VT": "VT-",
            "MBT": "主战坦克",
        }
        # JL special: 巨浪 vs 教练
        if pref == "JL":
            if "弹" in name_s or "SLBM" in des.upper() or branch == "火箭军" or "巨浪" in name_s:
                add(f"巨浪-{num}")
            else:
                add(f"教练-{num}")
                add(f"教-{num}")
                add(f"JL-{num}")
        elif pref in ("PHL", "PLZ", "ZTZ", "ZBD", "ZBL", "ZTD", "ZSL", "ZSD", "ZTQ", "PGZ", "PCL", "PLL", "PHZ", "QBZ", "QBU", "QSZ", "QJY", "QJZ", "QLZ", "PF", "QTS", "QLG", "QCW", "QCQ"):
            add(f"{pref}-{num}")
            add(des_s)
            if pref.startswith("Q"):
                add(f"{pref}-{num}")
        elif pref in mapping:
            add(f"{mapping[pref]}{num}" if mapping[pref].endswith("-") or mapping[pref].endswith("油-") or mapping[pref].endswith("潜-") else f"{mapping[pref]}{num}")
            if pref == "FC":
                add("鹘鹰")
                add("FC-31")
        else:
            add(f"{pref}-{num}")
            add(f"{pref}{num}")

    # 俄/北約名
    if "现代级" in name_s or "Sovremenny" in des:
        add("现代级驱逐舰")
    if "基洛" in name_s or "Kilo" in des:
        add("基洛级潜艇")
    if "福建" in name_s:
        add("福建舰")
    if "辽宁" in name_s:
        add("辽宁舰")
    if "山东" in name_s:
        add("山东舰")

    # designation 本身（去 Type）
    if des_s and not des_s.lower().startswith("type"):
        add(des_s)

    return qs[:8]


def extract_title_img(html: str) -> tuple[str | None, str | None]:
    title = None
    img = None
    m = re.search(r'property="og:title"\s+content="([^"]+)"', html)
    if m:
        title = m.group(1).strip()
    if not title:
        m = re.search(r"<title>([^<]+)</title>", html)
        if m:
            title = m.group(1).replace("_百度百科", "").replace("-百度百科", "").strip()
    m = re.search(r'name="image"\s+content="([^"]+)"', html)
    if m:
        img = m.group(1).strip()
    if not img:
        m = re.search(r'property="og:image"\s+content="([^"]+)"', html)
        if m:
            img = m.group(1).strip()
    # 放大：拿掉過度縮小參數，或保留 bce process
    return title, img


def title_matches(title: str, item: dict, query: str) -> bool:
    """嚴格：標題需含型號數字或核心名。"""
    if not title:
        return False
    t = to_simplified(title)
    # 排除明顯不相關
    bad = ["游戏", "手游", "小说", "电影", "演员", "歌曲", "专辑"]
    if any(b in t for b in bad):
        return False

    des = (item.get("designation") or "")
    name_s = to_simplified(clean_name(item.get("name_zh") or ""))

    # 抽取型號 token
    tokens = set()
    for src in (des, name_s, query):
        for tok in re.findall(r"[A-Za-z]{0,4}-?\d{1,4}[A-Za-z]{0,3}", src):
            tokens.add(tok.upper().replace("TYPE", "").strip("-"))
        for tok in re.findall(r"\d{2,4}[A-Z]{0,2}", src.upper()):
            tokens.add(tok)

    t_up = t.upper().replace(" ", "")
    # 數字型號出現在標題
    for tok in tokens:
        if len(tok) >= 2 and tok in t_up.replace("-", ""):
            # 再要求至少一個漢字角色詞或 query 重疊
            core = re.sub(r"[A-Za-z0-9\-_\s]", "", name_s)
            if core:
                # 標題含核心名中至少 2 字連續
                ok_han = False
                for i in range(len(core) - 1):
                    if core[i : i + 2] in t:
                        ok_han = True
                        break
                if ok_han or any(k in t for k in ["舰", "艇", "机", "弹", "炮", "枪", "车", "坦克", "直升", "雷达", "导弹"]):
                    return True
            else:
                return True

    # 無數字時：名稱高度重疊
    core = re.sub(r"[A-Za-z0-9\-_\s/]", "", name_s)
    if len(core) >= 2 and core[:2] in t and (core in t or sum(1 for i in range(len(core) - 1) if core[i : i + 2] in t) >= 2):
        return True

    # query 本身與標題一致
    q = to_simplified(query)
    if q and (q in t or t in q):
        return True

    return False


def fetch_html(url: str, timeout: int = 20) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"    HTTP fail: {e}")
        return None


def download_image(url: str, dest: Path) -> bool:
    # 取較大尺寸：調整 bce process
    u = url
    if "x-bce-process=" in u:
        u = re.sub(r"x-bce-process=[^&]+", "x-bce-process=image/quality,Q_85", u)
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": "https://baike.baidu.com/"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        if len(data) < 2000:
            return False
        im = Image.open(BytesIO(data))
        im = im.convert("RGB")
        # 過濾太小的圖示
        if min(im.size) < 120:
            return False
        if max(im.size) > 1400:
            im.thumbnail((1400, 1400))
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, "JPEG", quality=88, optimize=True)
        return dest.stat().st_size > 2000
    except Exception as e:
        print(f"    download fail: {e}")
        return False


def resolve_item(item: dict, delay: float = 0.6) -> dict:
    """回傳 {ok, query, title, img_url, path, reason}"""
    for q in candidate_queries(item):
        enc = urllib.parse.quote(q)
        url = f"https://wapbaike.baidu.com/item/{enc}"
        html = fetch_html(url)
        time.sleep(delay)
        if not html or len(html) < 500:
            continue
        if "百度安全验证" in html or "BIOC_OPTIONS" in html:
            return {"ok": False, "reason": "captcha", "query": q}
        title, img = extract_title_img(html)
        if not title or not img:
            # 嘗試 search
            continue
        if not title_matches(title, item, q):
            print(f"    skip mismatch: query={q!r} title={title!r}")
            continue
        dest = IMG_DIR / f"{item['id']}.jpg"
        if download_image(img, dest):
            return {
                "ok": True,
                "query": q,
                "title": title,
                "img_url": img,
                "path": f"assets/images/{item['id']}.jpg",
                "baike_url": url,
            }
        else:
            print(f"    image bad for {q} / {title}")
    return {"ok": False, "reason": "no_match"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ids", type=str, default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=float, default=0.7)
    args = ap.parse_args()

    items = load_items()
    by_id = {x["id"]: x for x in items}
    missing = [x for x in items if not has_local_image(x["id"], x.get("image") or "")]

    if args.ids:
        want = {s.strip() for s in args.ids.split(",") if s.strip()}
        missing = [by_id[i] for i in want if i in by_id and not has_local_image(i, by_id[i].get("image") or "")]

    # 優先：載具 > 有 Type/字母數字型號
    def score(it):
        s = 0
        if it.get("category") == "vehicle":
            s += 3
        if it.get("category") == "weapon":
            s += 1
        if re.search(r"\d", it.get("designation") or ""):
            s += 2
        return s

    missing.sort(key=score, reverse=True)
    if args.limit:
        missing = missing[: args.limit]

    print(f"待處理缺圖：{len(missing)} 筆")
    log = json.loads(LOG_PATH.read_text(encoding="utf-8")) if LOG_PATH.exists() else {}
    ok_n = skip_n = fail_n = 0
    successes = {}

    for i, item in enumerate(missing, 1):
        eid = item["id"]
        print(f"[{i}/{len(missing)}] {eid} | {item.get('name_zh')} | {item.get('designation')}")
        if args.dry_run:
            print("    queries:", candidate_queries(item))
            continue
        res = resolve_item(item, delay=args.delay)
        log[eid] = {**res, "name_zh": item.get("name_zh"), "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
        if res.get("ok"):
            ok_n += 1
            successes[eid] = res
            print(f"    ✓ {res['title']} ← {res['query']}")
        elif res.get("reason") == "captcha":
            fail_n += 1
            print("    ✗ 遇到驗證碼，停止批次")
            break
        else:
            skip_n += 1
            print(f"    ✗ {res.get('reason', 'fail')}")

        if i % 10 == 0:
            LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    if successes and not args.dry_run:
        ep = ROOT / "data" / "specs_enrichment.json"
        d = json.loads(ep.read_text(encoding="utf-8"))
        for eid, res in successes.items():
            ent = d.setdefault("items", {}).setdefault(eid, {})
            ent["image"] = res["path"]
            # 附百度來源（教育用途標註）
            srcs = ent.setdefault("sources", [])
            label = f"百度百科：{res.get('title', eid)}"
            if not any(s.get("url") == res.get("baike_url") for s in srcs if isinstance(s, dict)):
                srcs.append({"label": label, "url": res.get("baike_url", "")})
            ent.setdefault("image_credit", f"图片来自百度百科《{res.get('title')}》（教育参考）")
        ep.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已寫入 specs_enrichment.json：{len(successes)} 筆")
        print("請執行：python3 tools/apply_us_authority.py")

    print(f"\n完成：成功 {ok_n}，無匹配 {skip_n}，失敗 {fail_n}")


if __name__ == "__main__":
    main()
