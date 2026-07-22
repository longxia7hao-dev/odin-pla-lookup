#!/usr/bin/env python3
"""
以美方公開權威來源校正裝備「形式／分類／型號／射程」：
- DoD China Military Power Report 2025 (CMPR)
- FAS Chinese Nuclear Weapons 2024 (CSS 編號)
- 美軍慣用艦級名 (Renhai / Luyang / Jiangkai 等)
- ODIN WEG 分類語彙（訓練用 WEG 風格）

來源檔：data/sources/cmpr2025.txt、fas-china-2024.txt
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_JS = ROOT / "js" / "equipment-data.js"
OUT_JS = DATA_JS
CROSSWALK = ROOT / "data" / "us_authority_crosswalk.json"

# id -> 校正欄位（覆蓋／補強）
# 僅納入美方公開報告或公認 US 軍事文獻可對應者
US_PATCH: dict[str, dict] = {
    # ---- 彈道／巡航（DoD CMPR 2025 Fielded Conventional Strike + FAS CSS）----
    "df-15b": {
        "us_designation": "CSS-6 (family)",
        "dod_class": "SRBM",
        "range_m": "300–1,000 km（DoD：DF-11A/DF-15/DF-16 族 SRBM 帶）",
        "notes_zh": "近程彈道飛彈（SRBM）。DoD CMPR 將 DF-15 與 DF-11A、DF-16 列為對陸 SRBM（約 300–1000 km）。",
        "notes_en": "SRBM. DoD CMPR lists DF-15 with DF-11A/DF-16 as land-attack SRBMs (300–1000 km).",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "category": "weapon",
        "subcategory": "ballistic",
        "form_zh": "近程彈道飛彈（SRBM）",
        "form_en": "Short-Range Ballistic Missile (SRBM)",
    },
    "df-16": {
        "us_designation": "CSS-11 (reported family)",
        "dod_class": "SRBM",
        "range_m": "300–1,000 km（DoD SRBM 帶）",
        "notes_zh": "近程彈道飛彈。DoD 將 DF-16 與 DF-11A、DF-15 並列 SRBM 對陸打擊。",
        "notes_en": "SRBM land-attack. Grouped with DF-11A/DF-15 in DoD CMPR table.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "近程彈道飛彈（SRBM）",
        "form_en": "SRBM",
    },
    "df-21d": {
        "us_designation": "CSS-5 Mod (ASBM variant)",
        "dod_class": "MRBM / ASBM",
        "range_m": "1,500–2,000 km（DoD：DF-17/DF-21 帶；公開常稱 DF-21D >1,500 km）",
        "notes_zh": "中程彈道飛彈／反艦彈道飛彈（ASBM）。DoD 將 DF-21 列為 MRBM，任務含對陸／反艦。公開報告指 DF-21D 為反艦型。FAS：DF-21 族 NATO CSS-5。",
        "notes_en": "MRBM/ASBM. DoD lists DF-21 as MRBM (land attack/anti-ship). FAS: CSS-5 family.",
        "source_authority": ["DoD CMPR 2025", "FAS 2024"],
        "source_tier": "US_DoD",
        "form_zh": "中程彈道飛彈／反艦彈道飛彈（MRBM/ASBM）",
        "form_en": "MRBM / Anti-Ship Ballistic Missile",
    },
    "df-21a": {
        "us_designation": "CSS-5 Mod 2",
        "dod_class": "MRBM",
        "range_m": "約 1,750–2,150 km（DoD／USAF 公開區間）",
        "notes_zh": "中程彈道飛彈。FAS：CSS-5 Mods。DoD 近年核任務敘述中 DF-21 核角色淡出，以 DF-26 為主。",
        "notes_en": "MRBM. FAS CSS-5. Nuclear role largely superseded by DF-26 per recent DoD/FAS assessments.",
        "source_authority": ["DoD CMPR 2025", "FAS 2024"],
        "source_tier": "US_DoD",
        "form_zh": "中程彈道飛彈（MRBM）",
        "form_en": "Medium-Range Ballistic Missile (MRBM)",
    },
    "df-26": {
        "us_designation": "CSS-18",
        "dod_class": "IRBM",
        "range_m": "3,000–4,000 km（DoD CMPR）",
        "notes_zh": "中程彈道飛彈（IRBM）。DoD：對陸／反艦；雙重能力（核／常規）公開敘述。FAS NATO：CSS-18。",
        "notes_en": "IRBM. DoD: land attack/anti-ship; dual-capable. FAS: CSS-18.",
        "source_authority": ["DoD CMPR 2025", "FAS 2024"],
        "source_tier": "US_DoD",
        "form_zh": "中程彈道飛彈（IRBM）",
        "form_en": "Intermediate-Range Ballistic Missile (IRBM)",
    },
    "df-17": {
        "us_designation": "DF-17 (HGV booster)",
        "dod_class": "MRBM (HGV)",
        "range_m": "1,500–2,000 km（DoD：與 DF-21 同列 MRBM 帶）",
        "notes_zh": "中程彈道飛彈＋高超音速滑翔載具（HGV）。DoD 將 DF-17 列為常規 MRBM（對陸／反艦帶），非核表列系統（FAS 亦採 DoD 常規判定）。",
        "notes_en": "MRBM with HGV. DoD lists as conventional MRBM; not in nuclear table per FAS reading of DoD.",
        "source_authority": ["DoD CMPR 2025", "FAS 2024"],
        "source_tier": "US_DoD",
        "form_zh": "中程彈道飛彈／高超音速滑翔（MRBM+HGV）",
        "form_en": "MRBM with Hypersonic Glide Vehicle",
    },
    "df-31ag": {
        "us_designation": "CSS-10 Mod 2",
        "dod_class": "ICBM",
        "range_m": "約 11,200 km（FAS 據美方資料）",
        "notes_zh": "洲際彈道飛彈（ICBM），公路機動。FAS：CSS-10 Mod 2。DoD 亦提及 DF-31 級井射固推 ICBM。",
        "notes_en": "Road-mobile ICBM. FAS: CSS-10 Mod 2.",
        "source_authority": ["FAS 2024", "DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "洲際彈道飛彈（ICBM）",
        "form_en": "Intercontinental Ballistic Missile (ICBM)",
    },
    "df-41": {
        "us_designation": "CSS-20",
        "dod_class": "ICBM",
        "range_m": "約 12,000 km（FAS）",
        "notes_zh": "洲際彈道飛彈。FAS：CSS-20（機動／井射敘述）。可多彈頭公開估計。",
        "notes_en": "ICBM. FAS: CSS-20. MIRV-capable estimates in open US-linked analyses.",
        "source_authority": ["FAS 2024", "DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "洲際彈道飛彈（ICBM）",
        "form_en": "ICBM",
    },
    "df-5c": {
        "us_designation": "CSS-4 Mod 4 (reported)",
        "dod_class": "ICBM",
        "range_m": "約 13,000 km（FAS：DF-5 族）",
        "notes_zh": "井基液體燃料洲際彈道飛彈。FAS：DF-5 族 CSS-4。",
        "notes_en": "Silo liquid-fuel ICBM. FAS: CSS-4 family.",
        "source_authority": ["FAS 2024"],
        "source_tier": "US_DoD",
        "form_zh": "洲際彈道飛彈（井基液體）",
        "form_en": "Silo-based liquid-fuel ICBM",
    },
    "jl-2": {
        "us_designation": "CSS-N-14",
        "dod_class": "SLBM",
        "range_m": "約 7,000+ km（FAS）",
        "notes_zh": "潛射彈道飛彈。FAS：CSS-N-14。美方公開敘述 094 型正升級至 JL-3。",
        "notes_en": "SLBM. FAS: CSS-N-14. Type 094 force upgrading toward JL-3 per US open reporting.",
        "source_authority": ["FAS 2024", "DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "潛射彈道飛彈（SLBM）",
        "form_en": "Submarine-Launched Ballistic Missile (SLBM)",
    },
    "jl-3": {
        "us_designation": "CSS-N-20",
        "dod_class": "SLBM",
        "range_m": "約 9,000+ km（FAS）",
        "notes_zh": "潛射彈道飛彈。FAS：CSS-N-20。裝備／升級 094／094A，未來或對應 096。",
        "notes_en": "SLBM. FAS: CSS-N-20. Type 094/A; future Type 096.",
        "source_authority": ["FAS 2024", "DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "潛射彈道飛彈（SLBM）",
        "form_en": "SLBM",
    },
    "cj-10": {
        "us_designation": "CJ-10 / DH-10 (GLCM)",
        "dod_class": "GLCM",
        "range_m": "1,500–2,000 km（DoD：CJ-10/CJ-100 GLCM 帶）",
        "notes_zh": "陸射巡航飛彈（GLCM）。DoD 將 CJ-10 與 CJ-100 並列，對陸／反艦帶。",
        "notes_en": "Ground-launched cruise missile. DoD table: CJ-10/CJ-100 GLCM 1500–2000 km.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "陸射巡航飛彈（GLCM）",
        "form_en": "Ground-Launched Cruise Missile (GLCM)",
        "subcategory": "cruise",
    },
    "df-100": {
        "us_designation": "CJ-100 / DF-100",
        "dod_class": "GLCM",
        "range_m": "1,500–2,000 km（DoD GLCM 帶）",
        "notes_zh": "陸射巡航飛彈。DoD 表列 CJ-100 與 CJ-10 同帶（1500–2000 km）。",
        "notes_en": "GLCM. DoD lists CJ-100 with CJ-10.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "陸射巡航飛彈（GLCM）",
        "form_en": "GLCM",
        "subcategory": "cruise",
    },
    "cj-20": {
        "us_designation": "CJ-20 (ALCM)",
        "dod_class": "ALCM",
        "range_m": "與 H-6 組合作戰半徑合計約 4,000–5,500 km（DoD：H-6+YJ-21/CJ-20）",
        "notes_zh": "空射巡航飛彈。DoD：H-6 掛載 CJ-20／YJ-21 之對陸能力。",
        "notes_en": "Air-launched cruise missile used with H-6 per DoD strike table.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "空射巡航飛彈（ALCM）",
        "form_en": "Air-Launched Cruise Missile (ALCM)",
    },
    "yj-12": {
        "us_designation": "YJ-12 (AShM)",
        "dod_class": "ALCM / AShM",
        "range_m": "與 H-6 組合約 3,100–4,000 km 作戰半徑（DoD 表；彈本身為反艦）",
        "notes_zh": "超音速反艦飛彈。DoD：H-6 掛 YJ-12／YJ-83 反艦。",
        "notes_en": "Supersonic anti-ship missile. DoD: H-6 with YJ-12/YJ-83 anti-ship.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "空射／反艦巡航飛彈（AShM）",
        "form_en": "Anti-Ship Cruise Missile (supersonic)",
    },
    "yj-83": {
        "us_designation": "YJ-83 / C-802 family (export)",
        "dod_class": "AShM",
        "range_m": "與 H-6 組合 DoD 反艦帶；彈本身典型約 180+ km 級（公開）",
        "notes_zh": "亞音速反艦飛彈。DoD 明確將 YJ-83 與 YJ-12 並列 H-6 反艦掛載。",
        "notes_en": "Subsonic AShM. Explicitly listed with YJ-12 on H-6 in DoD CMPR.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "反艦巡航飛彈（AShM）",
        "form_en": "Anti-Ship Cruise Missile",
    },
    "yj-21": {
        "us_designation": "YJ-21 (hypersonic ASBM/ALBM)",
        "dod_class": "ALBM / hypersonic AShM",
        "range_m": "與 H-6 組合約 4,000–5,500 km（DoD）；2024 公開轟炸機投射型",
        "notes_zh": "高超音速反艦／空射彈道類武器。DoD 2025：2024 年 5 月公開轟炸機投射型 YJ-21；亦有 055 型試射公開報導。",
        "notes_en": "Hypersonic ASBM/ALBM. DoD: bomber-launched YJ-21 revealed May 2024; Type 055 tests in open reporting.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "高超音速反艦／空射彈道飛彈",
        "form_en": "Hypersonic anti-ship / air-launched ballistic missile",
    },
    "yj-18": {
        "us_designation": "YJ-18 (AShM)",
        "dod_class": "AShM",
        "range_m": "公開估計約 220–540 km（非 CMPR 表列彈種；艦／潛射主力反艦）",
        "notes_zh": "艦射／潛射反艦巡航飛彈（亞音速巡航＋末端超音速公開描述）。美方海軍／智庫常作 PLAN 垂發反艦主力討論；CMPR 2025 常規遠程表以 YJ-12/83 為空射代表。",
        "notes_en": "Ship/sub AShM widely discussed in US naval analyses; CMPR long-range table highlights air-launched YJ-12/83.",
        "source_authority": ["US open naval analyses", "DoD CMPR context"],
        "source_tier": "US_open",
        "form_zh": "反艦巡航飛彈（艦／潛射）",
        "form_en": "Anti-Ship Cruise Missile (ship/sub launched)",
    },
    "pl-15": {
        "us_designation": "PL-15 (AAM)",
        "dod_class": "BVR AAM",
        "range_m": "遠程主動雷達（公開）；DoD 提及出口改進型 PL-15",
        "notes_zh": "遠程空對空飛彈。DoD 2025：航展公開 PL-15 等出口型改進。",
        "notes_en": "Long-range AAM. DoD notes export PL-15 variants at Airshow China 2024.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "遠程空對空飛彈（BVR AAM）",
        "form_en": "Beyond-Visual-Range Air-to-Air Missile",
    },
    "pl-17": {
        "us_designation": "PL-17 (AAM)",
        "dod_class": "VLRAAM",
        "range_m": "DoD：J-16+PL-17 反航空高價值目標合計作戰半徑示意約 1,400 km",
        "notes_zh": "超遠程空對空飛彈。DoD 表：J-16 with PL-17，任務反空／高價值空中目標（HVAA）。",
        "notes_en": "Very-long-range AAM. DoD table: J-16 with PL-17 against HVAA.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "超遠程空對空飛彈",
        "form_en": "Very-Long-Range Air-to-Air Missile",
    },
    "pl-12": {
        "us_designation": "PL-12 / SD-10 (export)",
        "dod_class": "BVR AAM",
        "notes_zh": "中遠程空對空飛彈。DoD 提及出口型 PL-12A 等。",
        "notes_en": "BVR AAM. DoD notes export PL-12A variants.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "中遠程空對空飛彈",
        "form_en": "BVR AAM",
    },
    "pl-10": {
        "us_designation": "PL-10 (AAM)",
        "dod_class": "SRAAM",
        "notes_zh": "近距紅外成像空對空飛彈（高離軸角公開描述）。",
        "notes_en": "Short-range IR AAM (HOBS).",
        "source_authority": ["US open airpower analyses"],
        "source_tier": "US_open",
        "form_zh": "近距空對空飛彈（IR）",
        "form_en": "Short-Range IR Air-to-Air Missile",
    },
    # ---- 航空 ----
    "j-20": {
        "us_designation": "J-20 (PLAAF 5th-gen)",
        "dod_class": "5th-generation fighter",
        "notes_zh": "第五代戰鬥機。DoD：已作戰部署；持續增產與改進；雙座型可控制無人僚機公開模型。",
        "notes_en": "5th-gen fighter. DoD: operationally fielded; production expansion; two-seat loyal wingman control model shown.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "第五代匿蹤制空／多用途戰鬥機",
        "form_en": "5th-generation stealth fighter",
        "service_zh": "解放軍空軍（PLAAF）",
    },
    "j-20s": {
        "us_designation": "J-20 two-seat variant",
        "dod_class": "5th-generation fighter",
        "notes_zh": "殲-20 雙座型。DoD：公開展示可控制無人僚機之雙座構型。",
        "notes_en": "Two-seat J-20; DoD notes loyal-wingman control concept model.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "第五代雙座戰鬥機",
        "form_en": "5th-gen two-seat fighter",
    },
    "j-35a": {
        "us_designation": "J-35A",
        "dod_class": "5th-generation fighter",
        "notes_zh": "第五代戰鬥機（空軍型）。DoD 2025：2024 重大亮相包括 J-35A。",
        "notes_en": "5th-gen fighter. DoD: major 2024 debut includes J-35A.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "第五代戰鬥機（空軍）",
        "form_en": "5th-generation fighter (PLAAF)",
    },
    "j-35": {
        "us_designation": "J-35 (carrier)",
        "dod_class": "5th-generation carrier fighter",
        "notes_zh": "艦載第五代戰鬥機。DoD：福建艦未來艦載機聯隊含 J-35。",
        "notes_en": "Carrier 5th-gen fighter. DoD: intended for Fujian air wing.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "艦載第五代戰鬥機",
        "form_en": "Carrier-based 5th-generation fighter",
        "service_zh": "解放軍海軍航空兵（PLANAF）",
    },
    "j-16": {
        "us_designation": "J-16",
        "dod_class": "4.5-gen multirole fighter",
        "notes_zh": "重型多用途戰鬥機。DoD 多次提及 J-16 與 J-20 為 PLAAF 先進戰力，並可掛 PL-17。",
        "notes_en": "Heavy multirole fighter. DoD pairs J-16 with advanced PLAAF force and PL-17.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "重型多用途戰鬥機",
        "form_en": "Heavy multirole fighter",
    },
    "j-16d": {
        "us_designation": "J-16D (EW)",
        "dod_class": "Electronic warfare aircraft",
        "notes_zh": "電子戰型殲-16。",
        "notes_en": "Electronic-warfare variant of J-16.",
        "source_authority": ["US open airpower analyses"],
        "source_tier": "US_open",
        "form_zh": "電子戰飛機",
        "form_en": "Electronic warfare aircraft",
    },
    "j-10c": {
        "us_designation": "J-10C",
        "dod_class": "4th-generation multirole fighter",
        "notes_zh": "第四代多用途戰鬥機。DoD 提及出口巴基斯坦等。",
        "notes_en": "4th-gen multirole; DoD notes exports (e.g., Pakistan).",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "第四代多用途戰鬥機",
        "form_en": "4th-generation multirole fighter",
    },
    "j-15": {
        "us_designation": "J-15 Flying Shark",
        "dod_class": "Carrier-based fighter",
        "notes_zh": "艦載戰鬥機。DoD：遼寧／山東艦載 J-15；福建艦聯隊含 J-15T。",
        "notes_en": "Carrier fighter. DoD: J-15 on Liaoning/Shandong; J-15T for Fujian air wing.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "艦載戰鬥機",
        "form_en": "Carrier-based multirole fighter",
    },
    "j-15t": {
        "us_designation": "J-15T",
        "dod_class": "Carrier fighter (CATOBAR-capable)",
        "notes_zh": "彈射適改装艦載戰鬥機。DoD：福建艦未來聯隊含 J-15T。",
        "notes_en": "CATOBAR-capable J-15. DoD: Fujian air wing.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "艦載戰鬥機（彈射）",
        "form_en": "Carrier fighter (catapult-capable)",
    },
    "j-15d": {
        "us_designation": "J-15D",
        "dod_class": "Carrier EW aircraft",
        "notes_zh": "艦載電子戰機。DoD 2025 列為 2024 重大亮相與福建聯隊組成。",
        "notes_en": "Carrier EW. DoD 2024 debut; Fujian air wing.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "艦載電子戰機",
        "form_en": "Carrier-borne electronic warfare aircraft",
    },
    "h-6k": {
        "us_designation": "H-6K",
        "dod_class": "Bomber",
        "notes_zh": "轟炸機。DoD 以 H-6 系列掛載巡航／反艦／YJ-21 等執行遠程打擊。",
        "notes_en": "Bomber. DoD strike tables center on H-6 family weapons.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "轟炸機",
        "form_en": "Bomber",
    },
    "h-6n": {
        "us_designation": "H-6N",
        "dod_class": "Bomber (nuclear-capable ALBM role in US reporting)",
        "notes_zh": "可空中加油轟炸機。DoD：H-6N 之空射彈道飛彈（ALBM）屬高精度戰區核／打擊選項敘述之一。",
        "notes_en": "Probe-equipped bomber. DoD: H-6N ALBM as precise theater weapon option.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "轟炸機（可加油／ALBM 任務敘述）",
        "form_en": "Bomber with ALBM mission in US reporting",
    },
    "h-6j": {
        "us_designation": "H-6J (PLANAF)",
        "dod_class": "Maritime strike bomber",
        "notes_zh": "海軍航空兵轟炸機，反艦任務導向。",
        "notes_en": "PLANAF maritime strike bomber.",
        "source_authority": ["US open naval aviation analyses"],
        "source_tier": "US_open",
        "form_zh": "海軍轟炸機（反艦）",
        "form_en": "Naval bomber (anti-ship)",
    },
    "kj-500": {
        "us_designation": "KJ-500",
        "dod_class": "AEW&C",
        "notes_zh": "空中預警與管制機。DoD 點名 KJ-500 為支援先進戰機整合之重要支援機。",
        "notes_en": "AEW&C. DoD cites KJ-500 supporting advanced fighter integration.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "空中預警管制機（AEW&C）",
        "form_en": "Airborne Early Warning and Control",
    },
    "y-20": {
        "us_designation": "Y-20 / Y-20B",
        "dod_class": "Strategic transport",
        "notes_zh": "戰略運輸機。DoD：Y-20B＋WS-20 引擎；並發展 Y-20B 平台預警等特種任務。",
        "notes_en": "Strategic airlifter. DoD: Y-20B/WS-20; AEW program on Y-20B airframe.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "戰略運輸機",
        "form_en": "Strategic transport aircraft",
    },
    "z-20": {
        "us_designation": "Z-20",
        "dod_class": "Medium utility helicopter",
        "notes_zh": "中型通用直升機。DoD：福建艦聯隊含 Z-20；054B 可搭載更大型通用直升機如 Z-20。",
        "notes_en": "Medium utility helo. DoD: Fujian air wing; Type 054B can embark larger helos such as Z-20.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "中型通用直升機",
        "form_en": "Medium utility helicopter",
    },
    "kj-600": {
        "us_designation": "KJ-600",
        "dod_class": "Carrier AEW",
        "notes_zh": "艦載預警機。DoD：福建艦未來聯隊含 KJ-600。",
        "notes_en": "Carrier AEW. DoD: Fujian air wing includes KJ-600.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "艦載預警機",
        "form_en": "Carrier-based AEW aircraft",
    },
    # ---- 海軍 ----
    "type-003": {
        "name_zh": "003型航空母艦 福建艦（CV-18）",
        "us_designation": "Fujian (CV-18) / Type 003",
        "dod_class": "Aircraft carrier (CATOBAR/EMALS)",
        "notes_zh": "航空母艦。DoD：福建艦（CV-18），首艘國產平甲板彈射航母，電磁彈射；2024 海試／著艦報導。未來聯隊：J-35、J-15T、J-15D、Z-20、KJ-600 與 UAV。",
        "notes_en": "Carrier CV-18 Fujian. DoD: first indigenous flat-deck EMALS carrier; air wing J-35, J-15T/D, Z-20, KJ-600, UAVs.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "航空母艦（電磁彈射／平甲板）",
        "form_en": "Aircraft carrier (EMALS CATOBAR)",
        "aliases": ["福建艦", "003", "CV-18", "Fujian"],
    },
    "type-002": {
        "us_designation": "Shandong (CV-17) / Type 002",
        "dod_class": "Aircraft carrier (STOBARski-jump)",
        "notes_zh": "航空母艦。DoD：山東艦與遼寧艦為現役雙航母，2024 首次雙航母演訓。",
        "notes_en": "CV-17 Shandong. DoD: dual-carrier ops with Liaoning in 2024.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "航空母艦（滑躍）",
        "form_en": "Aircraft carrier (ski-jump)",
        "aliases": ["山東艦", "002", "CV-17"],
    },
    "type-001": {
        "us_designation": "Liaoning (CV-16) / Type 001",
        "dod_class": "Aircraft carrier (ski-jump)",
        "notes_zh": "航空母艦。DoD：遼寧艦（與山東艦）現役作戰訓練。",
        "notes_en": "CV-16 Liaoning. Operational with Shandong per DoD.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "航空母艦（滑躍）",
        "form_en": "Aircraft carrier (ski-jump)",
        "aliases": ["遼寧艦", "001", "CV-16"],
    },
    "type-055": {
        "us_designation": "Renhai-class / Type 055",
        "dod_class": "Cruiser / large destroyer (USN often cruiser)",
        "notes_zh": "大型水面作戰艦。美軍／美方文獻常稱 Renhai 級巡洋艦（cruisers），112 單元垂發；公開討論可發射反艦、對陸、防空、反潛等多型導彈，含 YJ-21 試射報導。",
        "notes_en": "Renhai class. US analyses often classify as cruiser; 112 VLS; multi-mission including reported YJ-21 tests.",
        "source_authority": ["DoD CMPR 2025", "US Naval War College / open US naval analyses"],
        "source_tier": "US_DoD",
        "form_zh": "大型導彈驅逐艦／巡洋艦（Renhai 級）",
        "form_en": "Renhai-class cruiser / large multi-mission combatant",
        "aliases": ["055", "南昌艦級", "Renhai", "Renhai-class"],
    },
    "type-052d": {
        "us_designation": "Luyang III-class / Type 052D",
        "dod_class": "Guided-missile destroyer (DDG)",
        "notes_zh": "導彈驅逐艦。美方艦級名 Luyang III；PLAN 主力區域防空／多用途驅逐艦。",
        "notes_en": "Luyang III-class DDG. Mainstay PLAN multi-mission destroyer.",
        "source_authority": ["US Navy open ship-class nomenclature", "DoD CMPR context"],
        "source_tier": "US_DoD",
        "form_zh": "導彈驅逐艦（DDG，Luyang III 級）",
        "form_en": "Guided-missile destroyer (Luyang III)",
        "aliases": ["052D", "昆明艦級", "Luyang III"],
    },
    "type-052c": {
        "us_designation": "Luyang II-class / Type 052C",
        "dod_class": "Guided-missile destroyer (DDG)",
        "notes_zh": "導彈驅逐艦。美方艦級名 Luyang II。",
        "notes_en": "Luyang II-class DDG.",
        "source_authority": ["US Navy open ship-class nomenclature"],
        "source_tier": "US_DoD",
        "form_zh": "導彈驅逐艦（Luyang II 級）",
        "form_en": "DDG (Luyang II)",
        "aliases": ["052C", "蘭州艦級", "Luyang II"],
    },
    "type-054a": {
        "us_designation": "Jiangkai II-class / Type 054A",
        "dod_class": "Frigate (FFG)",
        "notes_zh": "導彈護衛艦。美方艦級名 Jiangkai II；DoD 對照 054B 為新一代、大於 054A。",
        "notes_en": "Jiangkai II FFG. DoD: Type 054B is larger next-gen vs 054A.",
        "source_authority": ["DoD CMPR 2025", "US ship-class nomenclature"],
        "source_tier": "US_DoD",
        "form_zh": "導彈護衛艦（FFG，Jiangkai II 級）",
        "form_en": "Guided-missile frigate (Jiangkai II)",
        "aliases": ["054A", "Jiangkai II"],
    },
    "type-054b": {
        "us_designation": "Type 054B",
        "dod_class": "Frigate (FFG)",
        "notes_zh": "新一代護衛艦。DoD：2025 初服役首艦；大於 054A，火力增強，可搭載 Z-20 級通用直升機。",
        "notes_en": "Next-gen frigate. DoD: first commissioned early 2025; larger than 054A; Z-20 capable.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "導彈護衛艦（新一代）",
        "form_en": "Next-generation frigate",
    },
    "type-056a": {
        "us_designation": "Jiangdao-class / Type 056A",
        "dod_class": "Corvette (FS)",
        "notes_zh": "輕型護衛艦／輕護衛（美方 Jiangdao 級）。反潛加強型 056A。",
        "notes_en": "Jiangdao-class corvette; 056A ASW-oriented.",
        "source_authority": ["US ship-class nomenclature"],
        "source_tier": "US_DoD",
        "form_zh": "輕型護衛艦（Corvette）",
        "form_en": "Corvette (Jiangdao class)",
        "aliases": ["056A", "江島級", "Jiangdao"],
    },
    "type-075": {
        "us_designation": "Yushen-class / Type 075 LHD",
        "dod_class": "Landing Helicopter Dock (LHD)",
        "notes_zh": "兩棲攻擊艦（LHD）。美方艦級名常作 Yushen。",
        "notes_en": "LHD. US open nomenclature often Yushen class.",
        "source_authority": ["US open naval analyses"],
        "source_tier": "US_open",
        "form_zh": "兩棲攻擊艦（LHD）",
        "form_en": "Landing Helicopter Dock (LHD)",
        "aliases": ["075", "海南艦級", "Yushen"],
    },
    "type-076": {
        "us_designation": "Type 076 LHA/LHD (UAV-capable)",
        "dod_class": "Amphibious assault ship with EMALS",
        "notes_zh": "兩棲攻擊艦。DoD：2024 年底下水首艘 076，具備電磁彈射，可能搭載 UAV。",
        "notes_en": "DoD: first Type 076 launched late 2024 with EMALS; likely UAV-centric air ops.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "兩棲攻擊艦（電磁彈射／無人機）",
        "form_en": "Amphibious assault ship (EMALS/UAV)",
    },
    "type-071": {
        "us_designation": "Yuzhao-class / Type 071 LPD",
        "dod_class": "Landing Platform Dock (LPD)",
        "notes_zh": "船塢登陸艦（LPD）。美方艦級名 Yuzhao。",
        "notes_en": "LPD. US nomenclature Yuzhao class.",
        "source_authority": ["US open naval analyses"],
        "source_tier": "US_open",
        "form_zh": "船塢登陸艦（LPD）",
        "form_en": "Landing Platform Dock (LPD)",
        "aliases": ["071", "崑崙山級", "Yuzhao"],
    },
    "type-094": {
        "us_designation": "Jin-class / Type 094 SSBN",
        "dod_class": "Ballistic missile submarine (SSBN)",
        "notes_zh": "彈道飛彈核潛艦。美方艦級名 Jin；FAS／DoD：升級 JL-3。",
        "notes_en": "Jin-class SSBN. Upgrading to JL-3 per FAS/DoD open reporting.",
        "source_authority": ["DoD CMPR 2025", "FAS 2024"],
        "source_tier": "US_DoD",
        "form_zh": "彈道飛彈核潛艦（SSBN，Jin 級）",
        "form_en": "SSBN (Jin class)",
        "aliases": ["094", "晉級", "Jin-class"],
    },
    "type-093": {
        "us_designation": "Shang-class / Type 093 SSN",
        "dod_class": "Nuclear attack submarine (SSN)",
        "notes_zh": "攻擊核潛艦。美方艦級名 Shang。",
        "notes_en": "Shang-class SSN.",
        "source_authority": ["US open naval analyses"],
        "source_tier": "US_DoD",
        "form_zh": "攻擊核潛艦（SSN，Shang 級）",
        "form_en": "Nuclear-powered attack submarine (Shang class)",
        "aliases": ["093", "商級", "Shang-class"],
    },
    "type-093b": {
        "us_designation": "Shang III / Type 093B",
        "dod_class": "SSN (improved)",
        "notes_zh": "攻擊核潛艦改進型。美方公開討論 093B／巡航導彈能力相關。",
        "notes_en": "Improved Shang-class SSN in open US naval discussion.",
        "source_authority": ["US open naval analyses"],
        "source_tier": "US_open",
        "form_zh": "攻擊核潛艦（改進型）",
        "form_en": "Improved SSN",
    },
    "type-039a": {
        "us_designation": "Yuan-class / Type 039A/041",
        "dod_class": "Diesel-electric submarine (SSK, AIP)",
        "notes_zh": "AIP 柴電潛艦。美方艦級名 Yuan。DoD 亦提及出口 Yuan 級進度。",
        "notes_en": "Yuan-class AIP SSK. DoD notes export Yuan delivery status in CMPR.",
        "source_authority": ["DoD CMPR 2025", "US ship-class nomenclature"],
        "source_tier": "US_DoD",
        "form_zh": "AIP 柴電潛艦（SSK，Yuan 級）",
        "form_en": "AIP diesel-electric submarine (Yuan class)",
        "aliases": ["039A", "041", "元級", "Yuan-class"],
    },
    "type-039": {
        "us_designation": "Song-class / Type 039",
        "dod_class": "Diesel-electric submarine (SSK)",
        "notes_zh": "柴電潛艦。美方艦級名 Song。",
        "notes_en": "Song-class SSK.",
        "source_authority": ["US ship-class nomenclature"],
        "source_tier": "US_DoD",
        "form_zh": "柴電潛艦（Song 級）",
        "form_en": "Diesel-electric submarine (Song class)",
        "aliases": ["039", "宋級", "Song-class"],
    },
    "type-035": {
        "us_designation": "Ming-class / Type 035",
        "dod_class": "Diesel-electric submarine (legacy)",
        "notes_zh": "舊式柴電潛艦。美方艦級名 Ming。",
        "notes_en": "Ming-class legacy SSK.",
        "source_authority": ["US ship-class nomenclature"],
        "source_tier": "US_DoD",
        "form_zh": "柴電潛艦（舊式，Ming 級）",
        "form_en": "Legacy SSK (Ming class)",
    },
    # ---- 陸裝（DoD 2025 明文）----
    "pcl-181": {
        "us_designation": "PCL-181 (export SH-15 related)",
        "dod_class": "Wheeled self-propelled howitzer",
        "caliber": "155 mm",
        "notes_zh": "輪式自走榴彈砲。DoD 2025：PLAA 部署 PCL-181 輪式自走榴彈砲；出口型常稱 SH-15。",
        "notes_en": "Wheeled SPH. DoD: PLAA fielded PCL-181; export often SH-15.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "輪式自走榴彈砲（155mm）",
        "form_en": "Wheeled self-propelled howitzer (155 mm)",
        "subcategory": "truck_howitzer",
    },
    "phl-16": {
        "us_designation": "PHL-16 / PCH-191 / AR-3",
        "dod_class": "Modular MLRS",
        "notes_zh": "模組化多管火箭系統。DoD 2025 明文：PHL-16／PCH-191／AR-3 模組火箭。",
        "notes_en": "Modular MLRS. DoD explicitly: PHL-16/PCH-191/AR-3.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "模組化多管火箭系統（MLRS）",
        "form_en": "Modular multiple rocket launcher system",
        "aliases": ["16式", "PCL-191", "PCH-191", "AR-3", "PHL-16"],
    },
    "ztz-99a": {
        "us_designation": "Type 99A / ZTZ-99A",
        "dod_class": "Main battle tank (MBT)",
        "notes_zh": "主戰坦克。美方／ODIN 風格常作 Type 99A MBT；第三代主力。",
        "notes_en": "MBT. Type 99A in US/ODIN-style nomenclature.",
        "source_authority": ["ODIN WEG style", "US open ground-force analyses"],
        "source_tier": "US_open",
        "form_zh": "主戰坦克（MBT）",
        "form_en": "Main Battle Tank (MBT)",
    },
    "ztq-15": {
        "us_designation": "Type 15 / ZTQ-15",
        "dod_class": "Light tank",
        "notes_zh": "輕型坦克。美方公開文獻 Type 15 light tank（高原／複雜地形）。",
        "notes_en": "Type 15 light tank in US open sources.",
        "source_authority": ["US open ground-force analyses"],
        "source_tier": "US_open",
        "form_zh": "輕型坦克",
        "form_en": "Light tank",
    },
    "zbd-04a": {
        "us_designation": "ZBD-04A IFV",
        "dod_class": "Infantry fighting vehicle (IFV)",
        "notes_zh": "履帶式步兵戰車（IFV）。",
        "notes_en": "Tracked IFV.",
        "source_authority": ["ODIN WEG style"],
        "source_tier": "US_open",
        "form_zh": "步兵戰車（IFV）",
        "form_en": "Infantry Fighting Vehicle (IFV)",
    },
    "zbd-05": {
        "us_designation": "ZBD-05 AAAV",
        "dod_class": "Amphibious IFV",
        "notes_zh": "高速兩棲步兵戰車。陸戰隊／兩棲合成旅關鍵裝備（美方兩棲評估常引用 05 車族）。",
        "notes_en": "High-speed amphibious IFV; PLANMC/PLAA amphib brigades.",
        "source_authority": ["DoD CMPR amphibious context", "US open analyses"],
        "source_tier": "US_open",
        "form_zh": "兩棲步兵戰車",
        "form_en": "Amphibious infantry fighting vehicle",
    },
    "hq-9": {
        "us_designation": "HQ-9 / HHQ-9 (naval)",
        "dod_class": "Long-range SAM",
        "notes_zh": "遠程地對空／艦對空飛彈系統。",
        "notes_en": "Long-range SAM; naval HHQ-9.",
        "source_authority": ["US open air-defense analyses"],
        "source_tier": "US_open",
        "form_zh": "遠程防空飛彈系統（SAM）",
        "form_en": "Long-range surface-to-air missile system",
    },
    "hq-22": {
        "us_designation": "HQ-22 (export FK-3)",
        "dod_class": "Medium/long-range SAM",
        "notes_zh": "中遠程防空飛彈。DoD：出口型 FK-3 為 HQ-22 出口型。",
        "notes_en": "SAM. DoD: FK-3 is export HQ-22.",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "form_zh": "中遠程防空飛彈系統",
        "form_en": "Medium- to long-range SAM",
    },
    "s-400": {
        "us_designation": "S-400 (imported)",
        "dod_class": "Long-range SAM (Russian)",
        "notes_zh": "進口俄製遠程防空系統。",
        "notes_en": "Imported Russian long-range SAM.",
        "source_authority": ["DoD CMPR historical", "US open analyses"],
        "source_tier": "US_open",
        "form_zh": "遠程防空飛彈系統（進口）",
        "form_en": "Imported long-range SAM",
        "origin": "Russia",
        "origin_zh": "俄羅斯",
    },
    "qbz-191": {
        "us_designation": "QBZ-191",
        "dod_class": "Assault rifle",
        "notes_zh": "5.8mm 突擊步槍（制式換裝序列）。",
        "notes_en": "5.8 mm assault rifle; modern PLA service rifle family.",
        "source_authority": ["US open small-arms analyses"],
        "source_tier": "US_open",
        "form_zh": "突擊步槍",
        "form_en": "Assault rifle",
    },
    # ==== 海軍艦艇批次（ONI／美海軍公開艦級命名；2026-07-22 Claude 核對）====
    "type-051b": {
        "us_designation": "Luhai-class / Type 051B (DDG)",
        "dod_class": "Guided-missile destroyer (DDG)",
        "notes_zh": "導彈驅逐艦（單艦 167 深圳）。1990 年代末服役，現代化後換裝 HHQ-16 垂發。美方艦級名 Luhai。",
        "notes_en": "Luhai-class DDG (single ship, Shenzhen 167). Modernized with HHQ-16 VLS. US class name Luhai.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "導彈驅逐艦（DDG，Luhai 級）",
        "form_en": "Guided-missile destroyer (Luhai class)",
        "aliases": ["051B", "深圳艦", "Luhai"],
    },
    "type-051c": {
        "us_designation": "Luzhou-class / Type 051C (DDG)",
        "dod_class": "Guided-missile destroyer (DDG)",
        "notes_zh": "導彈驅逐艦（2 艘：115 瀋陽、116 石家莊）。裝俄製 S-300FM（Rif-M）艦載遠程防空。美方艦級名 Luzhou。",
        "notes_en": "Luzhou-class DDG (2 hulls). Russian S-300FM/Rif-M area-defense SAM. US class name Luzhou.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "導彈驅逐艦（DDG，Luzhou 級）",
        "form_en": "Guided-missile destroyer (Luzhou class)",
        "aliases": ["051C", "Luzhou"],
    },
    "type-052b": {
        "us_designation": "Luyang I-class / Type 052B (DDG)",
        "dod_class": "Guided-missile destroyer (DDG)",
        "notes_zh": "導彈驅逐艦（2 艘：168 廣州、169 武漢）。俄製 Shtil（SA-N-12）防空、YJ-83 反艦。美方艦級名 Luyang I。",
        "notes_en": "Luyang I-class DDG (2 hulls). Russian Shtil/SA-N-12 SAM, YJ-83 ASCM. US class name Luyang I.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "導彈驅逐艦（DDG，Luyang I 級）",
        "form_en": "Guided-missile destroyer (Luyang I class)",
        "aliases": ["052B", "廣州艦", "Luyang I"],
    },
    "type-052dl": {
        "us_designation": "Luyang III (Mod)-class / Type 052DL (DDG)",
        "dod_class": "Guided-missile destroyer (DDG)",
        "notes_zh": "052D 延伸甲板改良型（加長機庫、新型雷達），64 單元垂發＋130mm 主砲。美方仍歸 Luyang III（改）系列。",
        "notes_en": "Stretched 052D variant (longer hangar, new radar); 64 VLS + 130mm gun. US groups under Luyang III (Mod).",
        "source_authority": ["US Navy open ship-class nomenclature", "DoD CMPR context"],
        "source_tier": "US_open",
        "form_zh": "導彈驅逐艦（DDG，Luyang III 改／延伸型）",
        "form_en": "Guided-missile destroyer (Luyang III Mod)",
        "aliases": ["052DL", "Luyang III Mod"],
    },
    "sovremenny": {
        "us_designation": "Sovremenny-class / Project 956EM (DDG)",
        "dod_class": "Guided-missile destroyer (DDG, Russian-built)",
        "notes_zh": "向俄採購 4 艘。SS-N-22 Sunburn（3M80 Moskit）超音速反艦飛彈為其標誌武裝。美方／NATO 名 Sovremenny。",
        "notes_en": "4 ships purchased from Russia. Signature SS-N-22 Sunburn (3M80 Moskit) supersonic ASCM. US/NATO name Sovremenny.",
        "source_authority": ["US/NATO open naval nomenclature"],
        "source_tier": "US_open",
        "form_zh": "導彈驅逐艦（俄製，Sovremenny 級）",
        "form_en": "Guided-missile destroyer (Sovremenny class)",
        "aliases": ["956E", "956EM", "現代級", "Sovremenny"],
    },
    "type-053h3": {
        "us_designation": "Jiangwei II-class / Type 053H3 (FFG)",
        "dod_class": "Guided-missile frigate (FFG)",
        "notes_zh": "舊型導彈護衛艦。YJ-83 反艦、HQ-7 近程防空。美方艦級名 Jiangwei II。",
        "notes_en": "Older guided-missile frigate. YJ-83 ASCM, HQ-7 point-defense SAM. US class name Jiangwei II.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "導彈護衛艦（FFG，Jiangwei II 級）",
        "form_en": "Guided-missile frigate (Jiangwei II class)",
        "aliases": ["053H3", "Jiangwei II"],
    },
    "type-054": {
        "us_designation": "Jiangkai I-class / Type 054 (FFG)",
        "dod_class": "Guided-missile frigate (FFG)",
        "notes_zh": "054A 之前型（2 艘：525 馬鞍山、526 溫州）。美方艦級名 Jiangkai I。",
        "notes_en": "Predecessor of 054A (2 hulls). US class name Jiangkai I.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "導彈護衛艦（FFG，Jiangkai I 級）",
        "form_en": "Guided-missile frigate (Jiangkai I class)",
        "aliases": ["054", "Jiangkai I"],
    },
    "type-056": {
        "us_designation": "Jiangdao-class / Type 056 (Corvette/FFL)",
        "dod_class": "Corvette (FFL)",
        "notes_zh": "輕型護衛艦基本型；反潛強化型為 056A。多數 056/056A 已移交中國海警。美方艦級名 Jiangdao。",
        "notes_en": "Base corvette; ASW variant is 056A. Many transferred to China Coast Guard. US class name Jiangdao.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "輕型護衛艦（Corvette，Jiangdao 級）",
        "form_en": "Corvette (Jiangdao class)",
        "aliases": ["056", "Jiangdao"],
    },
    "type-022": {
        "us_designation": "Houbei-class / Type 022 (PGGF missile boat)",
        "dod_class": "Guided-missile patrol boat (PTG/PGGF)",
        "notes_zh": "雙體穿浪飛彈快艇，8×YJ-83 反艦飛彈；近岸快速突擊。美方艦級名 Houbei。",
        "notes_en": "Wave-piercing catamaran missile boat, 8×YJ-83 ASCM. US class name Houbei.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "飛彈快艇（雙體穿浪，Houbei 級）",
        "form_en": "Fast missile catamaran (Houbei class)",
        "aliases": ["022", "Houbei"],
    },
    "type-072a": {
        "us_designation": "Yuting II-class / Type 072A (LST)",
        "dod_class": "Tank landing ship (LST)",
        "notes_zh": "大型戰車登陸艦，兩棲運輸主力之一。美方艦級名 Yuting II。",
        "notes_en": "Tank landing ship; mainstay amphibious lift. US class name Yuting II.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "戰車登陸艦（LST，Yuting II 級）",
        "form_en": "Tank landing ship (Yuting II class)",
        "aliases": ["072A", "Yuting II"],
    },
    "type-726": {
        "us_designation": "Yuyi-class / Type 726 (LCAC)",
        "dod_class": "Air-cushion landing craft (LCAC)",
        "notes_zh": "071/075 艦載氣墊登陸艇，運載主戰坦克搶灘。美方艦級名 Yuyi。",
        "notes_en": "Air-cushion landing craft carried by 071/075; delivers MBTs to beach. US class name Yuyi.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "氣墊登陸艇（LCAC，Yuyi 級）",
        "form_en": "Air-cushion landing craft (Yuyi class)",
        "aliases": ["726", "Yuyi"],
    },
    "type-091": {
        "us_designation": "Han-class / Type 091 (SSN)",
        "dod_class": "Nuclear-powered attack submarine (SSN)",
        "notes_zh": "中國第一代攻擊核潛艦，多數已退役。美方艦級名 Han。",
        "notes_en": "China's first-generation SSN, mostly retired. US class name Han.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "攻擊核潛艦（SSN，Han 級，舊式）",
        "form_en": "Nuclear-powered attack submarine (Han class)",
        "aliases": ["091", "漢級", "Han"],
    },
    "kilo": {
        "us_designation": "Kilo-class / Project 877/636 (SSK)",
        "dod_class": "Diesel-electric attack submarine (SSK, Russian-built)",
        "notes_zh": "向俄採購 12 艘；636M 型可發射 3M-54E Klub（SS-N-27）反艦飛彈。NATO 名 Kilo。",
        "notes_en": "12 boats purchased from Russia; 636M carries 3M-54E Klub (SS-N-27) ASCM. NATO name Kilo.",
        "source_authority": ["US/NATO open naval nomenclature"],
        "source_tier": "US_open",
        "form_zh": "柴電潛艦（俄製，Kilo 級）",
        "form_en": "Diesel-electric attack submarine (Kilo class)",
        "aliases": ["877", "636", "基洛級", "Kilo"],
    },
    "type-901": {
        "us_designation": "Fuyu-class / Type 901 (AOE)",
        "dod_class": "Fast combat support ship (AOE)",
        "notes_zh": "航母戰鬥群快速綜合補給艦，滿載約 4.5 萬噸級。美方艦級名 Fuyu。",
        "notes_en": "Fast combat support ship for carrier groups, ~45,000 t full load. US class name Fuyu.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "快速綜合補給艦（AOE，Fuyu 級）",
        "form_en": "Fast combat support ship (Fuyu class)",
        "aliases": ["901", "Fuyu"],
    },
    "type-903a": {
        "us_designation": "Fuchi II-class / Type 903A (AOR)",
        "dod_class": "Replenishment oiler (AOR)",
        "notes_zh": "遠洋綜合補給艦，護航／遠海部署主力補給。美方艦級名 Fuchi（II）。",
        "notes_en": "Ocean-going replenishment oiler. US class name Fuchi (II).",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "綜合補給艦（AOR，Fuchi II 級）",
        "form_en": "Replenishment oiler (Fuchi II class)",
        "aliases": ["903A", "Fuchi II"],
    },
    "type-815a": {
        "us_designation": "Dongdiao-class / Type 815A (AGI)",
        "dod_class": "Intelligence collection ship (AGI)",
        "notes_zh": "電子情報偵察艦，常抵近他國演習／試射區蒐情。美方艦級名 Dongdiao。",
        "notes_en": "Electronic intelligence collection ship (AGI). US class name Dongdiao.",
        "source_authority": ["ONI PLA Navy Recognition & Identification Guide", "US Navy open ship-class nomenclature"],
        "source_tier": "US_open",
        "form_zh": "電子偵察艦（AGI，Dongdiao 級）",
        "form_en": "Intelligence collection ship (Dongdiao class)",
        "aliases": ["815A", "Dongdiao"],
    },
    "type-730": {
        "us_designation": "Type 730 CIWS (H/PJ-12)",
        "dod_class": "Close-in weapon system (30mm 7-barrel Gatling)",
        "caliber": "30mm × 7 管",
        "notes_zh": "艦載近迫武器系統，7 管 30mm 轉管砲，攔截反艦飛彈與飛機。內部代號 H/PJ-12。",
        "notes_en": "Shipborne CIWS, 30mm 7-barrel Gatling, anti-missile/anti-aircraft. Internal H/PJ-12.",
        "source_authority": ["US Navy open naval-gun analyses"],
        "source_tier": "US_open",
        "form_zh": "近迫武器系統（CIWS，30mm 七管）",
        "form_en": "Close-in weapon system (30mm, 7-barrel)",
        "aliases": ["730", "H/PJ-12"],
    },
    "type-1130": {
        "us_designation": "Type 1130 CIWS (H/PJ-11)",
        "dod_class": "Close-in weapon system (30mm 11-barrel Gatling)",
        "caliber": "30mm × 11 管",
        "notes_zh": "艦載近迫武器系統，11 管 30mm 轉管砲，射速更高；055／054A／航母使用。內部代號 H/PJ-11。",
        "notes_en": "Shipborne CIWS, 30mm 11-barrel Gatling, higher rate of fire; on 055/054A/carriers. Internal H/PJ-11.",
        "source_authority": ["US Navy open naval-gun analyses"],
        "source_tier": "US_open",
        "form_zh": "近迫武器系統（CIWS，30mm 十一管）",
        "form_en": "Close-in weapon system (30mm, 11-barrel)",
        "aliases": ["1130", "H/PJ-11"],
    },
}

# 新增僅在美方報告出現、庫內缺少的關鍵系統
NEW_ITEMS = [
    {
        "id": "df-27",
        "name_zh": "東風-27 彈道飛彈",
        "name_en": "DF-27 Ballistic Missile",
        "designation": "DF-27",
        "us_designation": "CSS-X-24 (FAS)",
        "aliases": ["東風27", "DF27"],
        "category": "weapon",
        "subcategory": "ballistic",
        "dod_class": "ICBM (DoD table) / developmental",
        "origin": "China",
        "origin_zh": "中國",
        "service_zh": "解放軍火箭軍（PLARF）",
        "service": "PLARF",
        "caliber": "彈道飛彈",
        "crew": "—",
        "weight_kg": "—",
        "length_mm": "—",
        "range_m": "5,000–8,000 km（DoD CMPR 2025 表）",
        "rate_of_fire": "—",
        "capacity": "機動發射（公開）",
        "armor": "—",
        "mobility": "公路機動（公開）",
        "sensors": "—",
        "notes_zh": "DoD CMPR 2025 常規遠程打擊表將 DF-27 列為 ICBM 級（5000–8000 km），任務對陸／反艦。FAS：CSS-X-24。發展／部署狀態以美方最新報告為準。",
        "notes_en": "DoD CMPR 2025 lists DF-27 as ICBM-class 5000–8000 km land attack/anti-ship. FAS: CSS-X-24.",
        "tags": ["彈道飛彈", "ICBM", "PLARF", "DoD"],
        "odin_hint": "Missiles / Ballistic",
        "form_zh": "洲際／遠程彈道飛彈（DoD 表列）",
        "form_en": "ICBM-class ballistic missile (DoD table)",
        "source_authority": ["DoD CMPR 2025", "FAS 2024"],
        "source_tier": "US_DoD",
        "wiki": "DF-27",
        "image": "",
        "odin_url": "https://odin.t2com.army.mil/WEG",
    },
    {
        "id": "df-11a",
        "name_zh": "東風-11A 近程彈道飛彈",
        "name_en": "DF-11A SRBM",
        "designation": "DF-11A",
        "us_designation": "CSS-7 Mod",
        "aliases": ["東風11A", "DF-11"],
        "category": "weapon",
        "subcategory": "ballistic",
        "dod_class": "SRBM",
        "origin": "China",
        "origin_zh": "中國",
        "service_zh": "解放軍火箭軍",
        "service": "PLARF",
        "caliber": "SRBM",
        "crew": "—",
        "weight_kg": "—",
        "length_mm": "—",
        "range_m": "300–1,000 km（DoD SRBM 帶）",
        "rate_of_fire": "—",
        "capacity": "機動發射車",
        "armor": "—",
        "mobility": "公路機動",
        "sensors": "—",
        "notes_zh": "近程彈道飛彈。DoD 將 DF-11A 與 DF-15、DF-16 並列 SRBM 對陸。",
        "notes_en": "SRBM. DoD groups DF-11A with DF-15/DF-16.",
        "tags": ["SRBM", "PLARF", "DoD"],
        "odin_hint": "Missiles / Ballistic",
        "form_zh": "近程彈道飛彈（SRBM）",
        "form_en": "Short-Range Ballistic Missile",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "wiki": "DF-11",
        "image": "",
        "odin_url": "https://odin.t2com.army.mil/WEG",
    },
    {
        "id": "df-31b",
        "name_zh": "東風-31B 洲際彈道飛彈",
        "name_en": "DF-31B ICBM",
        "designation": "DF-31B",
        "us_designation": "CSS-10 family",
        "aliases": ["東風31B"],
        "category": "weapon",
        "subcategory": "ballistic",
        "dod_class": "ICBM",
        "origin": "China",
        "origin_zh": "中國",
        "service_zh": "解放軍火箭軍",
        "service": "PLARF",
        "caliber": "ICBM",
        "crew": "—",
        "weight_kg": "—",
        "length_mm": "—",
        "range_m": "洲際（DoD：2024 年 9 月 DF-31B 公海落點試射敘述）",
        "rate_of_fire": "—",
        "capacity": "機動發射",
        "armor": "—",
        "mobility": "公路機動",
        "sensors": "—",
        "notes_zh": "洲際彈道飛彈。DoD 2025：2024 年 9 月自海南發射未裝藥 DF-31B ICBM 進入公海。",
        "notes_en": "ICBM. DoD: Sep 2024 unarmed DF-31B open-ocean launch from Hainan.",
        "tags": ["ICBM", "PLARF", "DoD"],
        "odin_hint": "Missiles / Ballistic",
        "form_zh": "洲際彈道飛彈（ICBM）",
        "form_en": "ICBM",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "wiki": "DF-31",
        "image": "",
        "odin_url": "https://odin.t2com.army.mil/WEG",
    },
    {
        "id": "hq-19",
        "name_zh": "紅旗-19 反彈道飛彈系統",
        "name_en": "HQ-19 ABM System",
        "designation": "HQ-19",
        "us_designation": "HQ-19",
        "aliases": ["紅旗19", "HQ19"],
        "category": "equipment",
        "subcategory": "sam",
        "dod_class": "ABM / mid-course defense (public DoD)",
        "origin": "China",
        "origin_zh": "中國",
        "service_zh": "解放軍",
        "service": "PLA",
        "caliber": "反彈道／防空飛彈",
        "crew": "系統級",
        "weight_kg": "—",
        "length_mm": "—",
        "range_m": "—（DoD 未給具體射程數字）",
        "rate_of_fire": "—",
        "capacity": "陸基",
        "armor": "—",
        "mobility": "陸基",
        "sensors": "—",
        "notes_zh": "陸基反彈道飛彈系統。DoD 2025：2024 公開 HQ-19，可能具備中段與高超音速滑翔載具攔截能力。",
        "notes_en": "Land-based ABM. DoD: unveiled HQ-19 with potential mid-course and HGV intercept capability.",
        "tags": ["ABM", "防空", "DoD"],
        "odin_hint": "Air Defense / ABM",
        "form_zh": "反彈道飛彈／高層防空系統",
        "form_en": "Anti-ballistic missile / upper-tier air defense system",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "wiki": "",
        "image": "",
        "odin_url": "https://odin.t2com.army.mil/WEG",
    },
    {
        "id": "kj-3000",
        "name_zh": "空警-3000 預警機",
        "name_en": "KJ-3000 AEW&C",
        "designation": "KJ-3000",
        "us_designation": "KJ-3000",
        "aliases": ["空警3000"],
        "category": "vehicle",
        "subcategory": "aircraft_aew",
        "dod_class": "AEW&C",
        "origin": "China",
        "origin_zh": "中國",
        "service_zh": "解放軍空軍",
        "service": "PLAAF",
        "caliber": "—",
        "crew": "—",
        "weight_kg": "—",
        "length_mm": "—",
        "range_m": "—",
        "rate_of_fire": "—",
        "capacity": "—",
        "armor": "—",
        "mobility": "預警機",
        "sensors": "數位雷達（DoD 公開描述）",
        "notes_zh": "空中預警管制機。DoD 2025：KJ-3000 試飛敘述，可能為首款採用數位雷達之型號，具備抗干擾、被動探測與目標識別。",
        "notes_en": "AEW&C. DoD: KJ-3000 flight test; likely first with digital radar, anti-jamming, passive detection.",
        "tags": ["預警機", "AEW", "DoD"],
        "odin_hint": "Aircraft / AEW",
        "form_zh": "空中預警管制機（AEW&C）",
        "form_en": "Airborne Early Warning and Control",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "wiki": "",
        "image": "",
        "odin_url": "https://odin.t2com.army.mil/WEG",
    },
    {
        "id": "type-19-ifv",
        "name_zh": "19式輪式步兵戰車",
        "name_en": "Type 19 Wheeled IFV",
        "designation": "Type 19",
        "us_designation": "Type 19 wheeled IFV",
        "aliases": ["19式輪式步戰", "Type-19 IFV"],
        "category": "vehicle",
        "subcategory": "ifv",
        "dod_class": "Wheeled IFV",
        "origin": "China",
        "origin_zh": "中國",
        "service_zh": "解放軍陸軍（PLAA）",
        "service": "PLAA",
        "caliber": "30mm 機砲＋反戰車飛彈",
        "crew": "—",
        "weight_kg": "—",
        "length_mm": "—",
        "range_m": "—",
        "rate_of_fire": "—",
        "capacity": "步兵載員",
        "armor": "輪式裝甲",
        "mobility": "輪式",
        "sensors": "—",
        "notes_zh": "輪式步兵戰車。DoD 2025：自 2024 年起 PLAA 接收 Type-19 輪式 IFV，裝備 30mm 機砲與反戰車飛彈。",
        "notes_en": "Wheeled IFV. DoD: since 2024 PLAA received Type-19 with 30mm cannon and ATGMs.",
        "tags": ["IFV", "輪式", "DoD", "30mm"],
        "odin_hint": "AFV / IFV",
        "form_zh": "輪式步兵戰車（IFV）",
        "form_en": "Wheeled infantry fighting vehicle",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "wiki": "",
        "image": "",
        "odin_url": "https://odin.t2com.army.mil/WEG",
    },
    {
        "id": "wz-9",
        "name_zh": "無偵-9 神鷹 偵察無人機",
        "name_en": "WZ-9 Divine Eagle",
        "designation": "WZ-9",
        "us_designation": "WZ-9 Divine Eagle",
        "aliases": ["神鷹", "Divine Eagle"],
        "category": "vehicle",
        "subcategory": "uav",
        "dod_class": "HALE UAV (ISR)",
        "origin": "China",
        "origin_zh": "中國",
        "service_zh": "解放軍",
        "service": "PLA",
        "caliber": "—",
        "crew": "地面站",
        "weight_kg": "—",
        "length_mm": "—",
        "range_m": "—",
        "rate_of_fire": "—",
        "capacity": "—",
        "armor": "—",
        "mobility": "高空長航時偵察",
        "sensors": "雷達／ISR（公開）",
        "notes_zh": "高空偵察無人機。DoD 2025：2024 年 12 月觀察到 WZ-9 Divine Eagle 於南海基地間歇活動，暗示半作戰狀態。",
        "notes_en": "HALE ISR UAV. DoD: WZ-9 observed intermittently from SCS base Dec 2024; semi-operational.",
        "tags": ["UAV", "偵察", "DoD"],
        "odin_hint": "Aircraft / UAV",
        "form_zh": "高空長航時偵察無人機",
        "form_en": "High-altitude long-endurance ISR UAV",
        "source_authority": ["DoD CMPR 2025"],
        "source_tier": "US_DoD",
        "wiki": "Divine Eagle",
        "image": "",
        "odin_url": "https://odin.t2com.army.mil/WEG",
    },
]


# ==== 合併：重複／別名條目 -> 保留條目（2026-07-22 比對後相同者合併）====
MERGE_MAP: dict[str, str] = {
    "zlt-05": "ztd-05",               # ZLT-05 為 ZTD-05 別名
    "pll-05-alt": "pll-05",           # 「07式自行迫擊砲相關」= PLL-05 120mm 迫榴砲
    "type-05-amphib-family": "zbd-05",# 05 兩棲車族總覽 -> 併入 ZBD-05
    "mi-171": "mi-17",                # Mi-171 併入 Mi-17／171 系列
    "phz-10": "phl-03",               # 「遠程火箭（舊稱）」-> PHL-03 300mm 遠火
}


def apply_merges(items: list[dict]) -> list[dict]:
    by_id = {it["id"]: it for it in items}
    drop = set()
    for src, dst in MERGE_MAP.items():
        s, d = by_id.get(src), by_id.get(dst)
        if not s or not d:
            continue
        merged = list(d.get("aliases") or [])
        merged += [s.get("designation", ""), s.get("name_zh", "")]
        merged += list(s.get("aliases") or [])
        d["aliases"] = [a for a in dict.fromkeys(merged) if a and a != d.get("designation")]
        # 保留來源條目的本機圖片（若保留條目沒有）
        if not d.get("image") and s.get("image"):
            d["image"] = s["image"]
        drop.add(src)
    return [it for it in items if it["id"] not in drop]


# ==== 軍種（陸/海/空/火箭軍/通用）指派 ====
# 逐 id 覆蓋（跨軍種或非直覺者）
BRANCH_BY_ID: dict[str, str] = {
    # 海軍：艦載航空／海軍飛彈／陸戰隊
    "j-15": "海軍", "j-15t": "海軍", "j-15d": "海軍", "kj-600": "海軍",
    "z-9c": "海軍", "z-18f": "海軍", "z-20f": "海軍", "ka-28": "海軍", "ka-31": "海軍", "kq-200": "海軍",
    "hhq-9": "海軍", "hhq-16": "海軍", "hq-10": "海軍",
    "yj-83": "海軍", "yj-62": "海軍", "yj-12": "海軍", "yj-12b": "海軍", "yj-6": "海軍",
    "yj-18": "海軍", "yj-18a": "海軍", "yj-21": "海軍", "c-802a": "海軍", "cx-1": "海軍", "cm-401": "海軍",
    "jl-2": "海軍", "jl-3": "海軍",
    "zbd-05": "海軍", "ztd-05": "海軍", "type-63a": "海軍",  # 陸戰隊兩棲
    # 火箭軍：陸基彈道／陸射巡航
    "df-11a": "火箭軍", "df-15b": "火箭軍", "df-16": "火箭軍", "df-17": "火箭軍",
    "df-21a": "火箭軍", "df-21d": "火箭軍", "df-26": "火箭軍", "df-31ag": "火箭軍",
    "df-31b": "火箭軍", "df-41": "火箭軍", "df-5c": "火箭軍", "df-100": "火箭軍", "cj-10": "火箭軍",
    # 空軍：空降兵、空射武器、空對空、預警、戰略防空 SAM
    "zbd-03": "空軍",  # 空降兵（PLAAF 空降軍）
    "cj-20": "空軍", "kd-88": "空軍", "ls-6": "空軍", "ft-series": "空軍", "gb-series": "空軍",
    "akd-10": "空軍", "ba-9": "空軍", "yj-91": "空軍", "ld-10": "空軍", "ty-90": "空軍",
    "pl-8": "空軍", "pl-5e": "空軍", "pl-10": "空軍", "pl-12": "空軍", "pl-15": "空軍", "pl-17": "空軍",
    "hq-9": "空軍", "hq-9a": "空軍", "hq-9b": "空軍", "s-300": "空軍", "s-400": "空軍", "hq-22": "空軍",
    # 陸航（陸軍航空兵）直升機
    "z-10": "陸軍", "z-19": "陸軍", "z-9": "陸軍", "z-8": "陸軍", "z-18": "陸軍",
    "z-11": "陸軍", "mi-17": "陸軍", "z-20": "陸軍", "hj-10": "陸軍",
}
_NAVAL_SUB = {"warship", "submarine", "ciws", "torpedo"}
_AIR_SUB = {"aircraft_fighter", "aircraft_bomber", "aircraft_strike", "aircraft_aew",
            "aircraft_transport", "aircraft_trainer", "aircraft_patrol", "uav", "aam"}
_ARMY_SUB = {"mbt", "light_tank", "ifv", "apc_wheeled", "apc_tracked", "assault_gun",
             "sph", "mortar_sp", "mlrs", "spaag", "truck_howitzer", "light_vehicle",
             "engineer", "sam", "atgm", "manpads", "at_rocket", "artillery_towed", "mortar",
             "helicopter", "helicopter_attack"}
_UNIVERSAL_SUB = {"assault_rifle", "dmr", "amr", "pistol", "smg", "mg", "hmg", "agl", "individual"}


def assign_branch(it: dict) -> str:
    if it["id"] in BRANCH_BY_ID:
        return BRANCH_BY_ID[it["id"]]
    sub = it.get("subcategory", "")
    if sub in _NAVAL_SUB:
        return "海軍"
    if sub in _UNIVERSAL_SUB:
        return "通用"
    if sub in _AIR_SUB:
        return "空軍"
    if sub in _ARMY_SUB:
        return "陸軍"
    s = it.get("service_zh", "") or it.get("service", "")
    if "火箭" in s:
        return "火箭軍"
    if "海" in s or "陸戰" in s:
        return "海軍"
    if "空" in s:
        return "空軍"
    return "陸軍"


def main():
    text = DATA_JS.read_text(encoding="utf-8")
    start = text.index("[")
    end = text.rindex("]") + 1
    items = json.loads(text[start:end])
    items = apply_merges(items)
    by_id = {it["id"]: it for it in items}

    # 併入外部批次核對檔（純 JSON，便於分批擴充；來源同 US_PATCH 規則）
    extra_path = ROOT / "data" / "us_patch_extra.json"
    if extra_path.exists():
        extra = json.loads(extra_path.read_text(encoding="utf-8"))
        # 支援 {"patches": {...}} 或直接 {id: {...}}
        extra = extra.get("patches", extra) if isinstance(extra, dict) else {}
        for k, v in extra.items():
            US_PATCH.setdefault(k, v)

    patched = 0
    for eid, patch in US_PATCH.items():
        if eid not in by_id:
            continue
        it = by_id[eid]
        for k, v in patch.items():
            if k == "aliases" and isinstance(v, list):
                old = it.get("aliases") or []
                it["aliases"] = list(dict.fromkeys(list(old) + v))
            else:
                it[k] = v
        it["authority_verified"] = True
        patched += 1

    added = 0
    for ni in NEW_ITEMS:
        if ni["id"] in by_id:
            # merge patch style
            for k, v in ni.items():
                if k != "id":
                    by_id[ni["id"]][k] = v
            by_id[ni["id"]]["authority_verified"] = True
            continue
        ni = dict(ni)
        ni["authority_verified"] = True
        items.append(ni)
        by_id[ni["id"]] = ni
        added += 1

    # 諸元精修層：覆蓋特定欄位（range_m/caliber/crew…）並附引用 sources；分批擴充
    enriched = 0
    enrich_path = ROOT / "data" / "specs_enrichment.json"
    if enrich_path.exists():
        edata = json.loads(enrich_path.read_text(encoding="utf-8"))
        edata = edata.get("items", edata) if isinstance(edata, dict) else {}
        for eid, fields in edata.items():
            it = by_id.get(eid)
            if not it or not isinstance(fields, dict):
                continue
            for k, v in fields.items():
                it[k] = v
            enriched += 1

    # mark remaining as unverified open-source
    for it in items:
        if not it.get("authority_verified"):
            it.setdefault("source_tier", "open_unverified")
            it.setdefault("source_authority", ["公開來源整理（待美方權威核對）"])
            it.setdefault("form_zh", {
                "weapon": "武器系統",
                "vehicle": "載具／平台",
                "equipment": "裝備／系統",
            }.get(it.get("category"), "裝備"))
            it.setdefault("form_en", it.get("subcategory") or it.get("category") or "")

    # 指派軍種（陸/海/空/火箭軍/通用）與正規化 sources 欄位
    for it in items:
        it["branch"] = assign_branch(it)
        if "sources" in it and not isinstance(it.get("sources"), list):
            it["sources"] = []

    # write crosswalk export
    cross = {
        "meta": {
            "title": "US Authority Crosswalk for PLA Equipment Lookup",
            "primary_sources": [
                "DoD Military and Security Developments Involving the PRC 2025 (CMPR)",
                "FAS Chinese Nuclear Weapons 2024 (CSS designators)",
                "US Navy open ship-class nomenclature (Renhai/Luyang/Jiangkai/Yuan/Jin/Shang)",
                "ODIN WEG (structure/field model; live fetch may require US network)",
            ],
            "note": "Training reference only. Prefer original DoD/ODIN text for formal citation.",
        },
        "patches": US_PATCH,
        "new_items": [x["id"] for x in NEW_ITEMS],
    }
    CROSSWALK.write_text(json.dumps(cross, ensure_ascii=False, indent=2), encoding="utf-8")

    header = (
        "/**\n"
        " * 解放軍武器／裝備／載具資料庫\n"
        " * 含美方權威核對欄位：us_designation / dod_class / form_zh / source_authority\n"
        " * 主要依據：DoD CMPR 2025、FAS 2024、美軍艦級公開命名\n"
        " * 訓練參考；正式引用以原文報告／ODIN 為準。\n"
        " */\n"
        "window.EQUIPMENT_DATA = "
    )
    OUT_JS.write_text(header + json.dumps(items, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    verified = sum(1 for i in items if i.get("authority_verified"))
    with_sources = sum(1 for i in items if i.get("sources"))
    print(f"items={len(items)} patched={patched} added={added} enriched={enriched} verified={verified} with_sources={with_sources}")
    print(f"crosswalk -> {CROSSWALK}")


if __name__ == "__main__":
    main()
