#!/usr/bin/env python3
"""
重建解放軍裝備資料庫：
- 擴充條目
- 精準維基頁面取圖（禁止模糊搜尋，避免錯圖／重複）
- 下載到 assets/images/{id}.jpg 供本機顯示
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JS = ROOT / "js" / "equipment-data.js"
IMG_DIR = ROOT / "assets" / "images"
CACHE = ROOT / "data" / "rebuild_cache.json"
UA = "PLA-Equipment-Lookup/2.0 (local offline training tool; educational)"

# 手動指定已知正確的 Wikimedia 圖（優先於 API）
# 使用 Commons 檔名，經 Special:FilePath 取得
FILE_OVERRIDES = {
    "ztz-99a": "ZTZ-99A_tank_front_20170902.jpg",
    "ztz-99": "Type_99_tank_-_TankFest_China_2018.jpg",
    "ztz-96b": "TankBiathlon2017Individual-16.jpg",
    "ztq-15": "Type_15_tank_at_Tank_Biathlon_2019.jpg",
    "zbd-04a": "ZBD-04A_IFV_20170716.jpg",
    "zbd-04": "ZBD-04_IFV.jpg",
    "j-20": "J-20_at_CCAS2022_(20221112122036).jpg",
    "j-10c": "J-10C_at_2022_Zhuhai_Airshow.jpg",
    "j-16": "PLAAF_J-16_-_2.jpg",
    "j-15": "J-15_Flying_Shark_at_Zhuhai_2014.jpg",
    "h-6k": "Xian_H-6K.jpg",
    "y-20": "Y-20_at_Airshow_China_2014.jpg",
    "kj-500": "KJ-500_AEW&C.jpg",
    "type-055": "Type_055_destroyer_Nanchang_in_2021.jpg",
    "type-052d": "Type_052D_destroyer_Xining_(117)_.jpg",
    "type-054a": "Type_054A_frigate_Huanggang_(577).jpg",
    "type-075": "Type_075_LHD_Hainan_(31)_20210423.jpg",
    "type-003": "Fujian_aircraft_carrier_20220617.jpg",
    "type-002": "Chinese_aircraft_carrier_Shandong_in_2020.jpg",
    "type-001": "Liaoning_aircraft_carrier_in_Hong_Kong_2017.jpg",
    "qbz-191": "QBZ191_20250921.jpg",
    "qbz-95-1": "QBZ-95-1_automatic_rifle_20220203.jpg",
    "qsz-92": "QSZ92_-_5.8mm_Pistol_20170919.jpg",
    "hq-9": "Chinese_HQ-9_launcher.jpg",
    "plz-05": "PLZ-05_SPH.jpg",
    "df-21d": "DF-21D_missile_2015.jpg",
    "df-26": "DF-26_missile_2015.jpg",
    "df-41": "DF-41_ICBM_2019.jpg",
    "su-35": "Su-35S_at_MAKS-2015.jpg",
    "su-30mkk": "Su-30MKK.jpg",
    "z-10": "Z-10_attack_helicopter.jpg",
    "z-20": "Z-20_helicopter.jpg",
    "wing-loong-2": "Wing_Loong_II_UAV.jpg",
    "type-039a": "Yuan_class_submarine.jpg",
    "type-094": "Type_094_submarine.jpg",
}

# 條目：(id, name_zh, name_en, designation, aliases, category, subcategory,
#         service_zh, caliber, crew, weight, length, range, rof, capacity,
#         armor, mobility, sensors, notes_zh, notes_en, tags, odin_hint, wiki_en)
# wiki_en 必須是英文維基精確條目標題（空字串=不取網圖）

def item(*a):
    return a


CATALOG = [
  # ========== 輕兵器 ==========
  item("qbz-191","QBZ-191 突擊步槍","QBZ-191 Assault Rifle","QBZ-191",["191","新式步槍"],"weapon","assault_rifle","陸軍","5.8×42mm","1","約3.25kg","約950mm","400–600m","約750rpm","30發","—","攜行","光學可選","新制式步槍，逐步取代95式。","Standard service rifle.",["步槍","5.8mm"],"Small Arms","QBZ-191"),
  item("qbz-95-1","QBZ-95-1 突擊步槍","QBZ-95-1 Assault Rifle","QBZ-95-1",["95-1","95式"],"weapon","assault_rifle","解放軍","5.8×42mm","1","約3.3kg","約745mm","約400m","約650rpm","30發","—","攜行","—","無托制式步槍。","Bullpup service rifle.",["步槍","無托"],"Small Arms","QBZ-95"),
  item("qbz-95b","QBZ-95B 短突擊步槍","QBZ-95B Carbine","QBZ-95B",["95B"],"weapon","assault_rifle","解放軍","5.8×42mm","1","約2.9kg","約610mm","約300m","約650rpm","30發","—","攜行","—","短管型，車組／特種用。","Carbine variant of QBZ-95.",["步槍","短管"],"Small Arms","QBZ-95"),
  item("qbz-03","QBZ-03 突擊步槍","QBZ-03 Assault Rifle","QBZ-03",["03式"],"weapon","assault_rifle","解放軍／武警","5.8×42mm","1","約3.5kg","約950mm","約400m","約650rpm","30發","—","攜行","—","傳統布局步槍。","Conventional layout AR.",["步槍"],"Small Arms","QBZ-03"),
  item("type-56-rifle","56式自動步槍","Type 56 Assault Rifle","Type 56",["56半","AK"],"weapon","assault_rifle","後備／民兵","7.62×39mm","1","約3.8kg","約874mm","約300m","約600rpm","30發","—","攜行","—","AK系舊制式。","AK-pattern legacy rifle.",["AK","步槍"],"Small Arms","Type 56 assault rifle"),
  item("type-81-rifle","81式自動步槍","Type 81 Assault Rifle","Type 81",["81式"],"weapon","assault_rifle","後備","7.62×39mm","1","約3.4kg","約955mm","約400m","約720rpm","30發","—","攜行","—","81式系列步槍。","Type 81 family.",["步槍"],"Small Arms","Type 81 assault rifle"),
  item("qbu-191","QBU-191 精確射手步槍","QBU-191 DMR","QBU-191",["191DMR"],"weapon","dmr","陸軍","5.8×42mm","1","約4.5kg","約1080mm","600–800m","半自動","20–30發","—","攜行","光學","191族DMR。","DMR of 191 family.",["精確射手"],"Small Arms","QBZ-191"),
  item("qbu-88","QBU-88 狙擊步槍","QBU-88 Sniper Rifle","QBU-88",["88狙擊"],"weapon","dmr","解放軍","5.8×42mm","1","約4.1kg","約920mm","約800m","半自動","10發","—","攜行","光學","班用狙擊。","Squad sniper rifle.",["狙擊"],"Small Arms","QBU-88"),
  item("qbu-10","QBU-10 反器材步槍","QBU-10 AMR","QBU-10",["10式反器材"],"weapon","amr","解放軍","12.7×108mm","1","約13.3kg","約1380mm","1–1.5km","半自動","5發","—","攜行","晝夜瞄具","大口徑反器材。","12.7mm AMR.",["反器材","12.7"],"Small Arms","QBU-10"),
  item("qsz-92","QSZ-92 手槍","QSZ-92 Pistol","QSZ-92",["92式手槍"],"weapon","pistol","解放軍","5.8×21／9×19mm","1","約0.76kg","約190mm","約50m","半自動","15–20發","—","隨身","—","制式手槍。","Service pistol.",["手槍"],"Small Arms","QSZ-92"),
  item("qsw-06","QSW-06 微聲手槍","QSW-06 Suppressed Pistol","QSW-06",["06微聲"],"weapon","pistol","特種","5.8×21mm","1","約1.1kg","—","約50m","半自動","20發","—","隨身","消音","特種微聲手槍。","Suppressed pistol.",["手槍","特種"],"Small Arms","QSW-06"),
  item("qcw-05","QCW-05 衝鋒槍","QCW-05 SMG","QCW-05",["05衝鋒槍"],"weapon","smg","特種","5.8×21mm","1","約2.2kg","約500mm","約200m","約900rpm","50發","—","攜行","可消音","無托衝鋒槍。","Bullpup SMG/PDW.",["衝鋒槍"],"Small Arms","QCW-05"),
  item("qcq-171","QCQ-171 衝鋒槍","QCQ-171 SMG","QCQ-171",["CS/LS7"],"weapon","smg","解放軍","9×19mm","1","約2.8kg","—","約200m","高射速","30發","—","攜行","—","9mm衝鋒槍。","9mm SMG.",["衝鋒槍"],"Small Arms","CS/LS7"),
  item("type-79-smg","79式衝鋒槍","Type 79 SMG","Type 79",["79衝"],"weapon","smg","有限服役","7.62×25mm","1","約1.9kg","約740mm","約200m","約1000rpm","20發","—","攜行","—","舊式衝鋒槍。","Legacy SMG.",["衝鋒槍"],"Small Arms","Type 79 submachine gun"),
  item("qjy-88","QJY-88 通用機槍","QJY-88 GPMG","QJY-88",["88機槍"],"weapon","mg","解放軍","5.8×42mm","1–2","約7.6kg","約1150mm","0.8–1km","650–700rpm","彈鏈","—","三腳架","—","5.8mm通用機槍。","5.8mm GPMG.",["機槍"],"Small Arms","QJY-88"),
  item("qjy-201","QJY-201 通用機槍","QJY-201 GPMG","QJY-201",["201機槍"],"weapon","mg","陸軍","5.8／7.62mm級","1–2","—","—","約1km","—","彈鏈","—","班排","—","新一代通用機槍。","Next-gen GPMG.",["機槍"],"Small Arms",""),
  item("qjz-89","QJZ-89 重機槍","QJZ-89 HMG","QJZ-89",["89重機槍"],"weapon","hmg","解放軍","12.7×108mm","2–3","槍身約17.5kg","約1.6m","1.5–2km","450–600rpm","彈鏈","—","三腳架／車載","—","輕量化12.7重機槍。","Lightweight HMG.",["重機槍"],"Small Arms","QJZ-89"),
  item("qjz-171","QJZ-171 重機槍","QJZ-171 HMG","QJZ-171",["171重機槍"],"weapon","hmg","陸軍","12.7×108mm","2–3","—","—","約2km","—","彈鏈","—","三腳架／車載","—","新型12.7重機槍。","New 12.7 HMG.",["重機槍"],"Small Arms",""),
  item("type-67-mg","67式通用機槍","Type 67 GPMG","Type 67",["67機槍"],"weapon","mg","後備","7.62×54mmR","1–2","約11kg","—","約1km","—","彈鏈","—","三腳架","—","舊式GPMG。","Legacy GPMG.",["機槍"],"Small Arms","Type 67 machine gun"),
  item("type-80-mg","80式通用機槍","Type 80 GPMG","Type 80",["80機槍","PKM系"],"weapon","mg","解放軍","7.62×54mmR","1–2","約7.5kg","—","約1km","—","彈鏈","—","三腳架","—","PKM系通用機槍。","PKM-derived GPMG.",["機槍"],"Small Arms","Type 80 machine gun"),
  item("qlz-87","QLZ-87 自動榴彈發射器","QLZ-87 AGL","QLZ-87",["87榴彈"],"weapon","agl","解放軍","35mm","2–3","12–20kg","約970mm","0.6–1.75km","約480rpm","彈鼓","—","三腳架／車載","—","35mm自動榴彈。","35mm AGL.",["榴彈"],"Small Arms","QLZ-87"),
  item("qlz-04","QLZ-04 自動榴彈發射器","QLZ-04 AGL","QLZ-04",["04榴彈"],"weapon","agl","解放軍","35mm","2–3","約20kg","—","約1.75km","—","彈鼓","—","三腳架／車載","—","QLZ-87改進。","Improved AGL.",["榴彈"],"Small Arms","QLZ-04"),
  item("qlu-11","QLU-11 精確榴彈發射器","QLU-11 Precision GL","QLU-11",["11榴彈"],"weapon","agl","陸軍","35mm","1–2","—","—","約1km","半自動","—","—","步兵","光學","班用精確榴彈。","Precision GL.",["榴彈"],"Small Arms","QLU-11"),
  item("qjg-02","QJG-02 高射機槍","QJG-02 AAMG","QJG-02",["14.5高射機槍"],"weapon","hmg","解放軍","14.5×114mm","2–3","—","—","約2km","—","彈鏈","—","三腳架","—","14.5mm高射機槍。","14.5mm AA MG.",["高射機槍"],"Small Arms","QJG-02"),
  item("pf-98","PF-98 火箭筒","PF-98 Rocket Launcher","PF-98",["98火箭筒"],"weapon","at_rocket","陸軍","120mm","1–2","發射器約10kg","約1.19m","400–800m","—","單發","破甲依彈","攜行","光學","步兵反裝甲火箭。","120mm AT rocket.",["反裝甲"],"Anti-Armor","PF-98"),
  item("pf-98a","PF-98A 火箭筒","PF-98A","PF-98A",["98A"],"weapon","at_rocket","陸軍","120mm","1–2","—","—","約800m","—","單發","—","攜行","改進瞄具","PF-98改進型。","Improved PF-98.",["反裝甲"],"Anti-Armor","PF-98"),
  item("dzj-08","DZJ-08 單兵火箭","DZJ-08","DZJ-08",["08單兵火箭"],"weapon","at_rocket","陸軍","約80mm","1","—","—","約300m","—","一次性","—","攜行","—","一次性單兵火箭。","Disposable rocket.",["反裝甲"],"Anti-Armor","DZJ-08"),
  item("type-69-rpg","69式火箭筒","Type 69 RPG","Type 69",["69式","RPG"],"weapon","at_rocket","後備","40mm筒","1","約5.6kg","—","約300m","—","—","—","攜行","—","RPG-7系。","RPG-7 type.",["RPG"],"Anti-Armor","Type 69 RPG"),
  item("hj-8","紅箭-8 反戰車飛彈","HJ-8 ATGM","HJ-8",["紅箭8"],"weapon","atgm","陸軍","—","2–3","系統約25kg","—","3–4km","—","管射","串聯破甲","三腳架／車載","光學","有線制導ATGM。","Wire-guided ATGM.",["ATGM"],"ATGM","HJ-8"),
  item("hj-9","紅箭-9 反戰車飛彈","HJ-9 ATGM","HJ-9",["紅箭9"],"weapon","atgm","陸軍","—","2–3","—","—","約5km","—","管射","重破甲","車載","光學","重型ATGM。","Heavy ATGM.",["ATGM"],"ATGM","HJ-9"),
  item("hj-10","紅箭-10 反戰車飛彈","HJ-10 / AFT-10","HJ-10",["紅箭10","AFT-10"],"weapon","atgm","陸軍","—","—","—","—","約10km","—","箱射","—","車載／直升機","光電","遠程ATGM。","Long-range ATGM.",["ATGM"],"ATGM","HJ-10"),
  item("hj-12","紅箭-12 反戰車飛彈","HJ-12 ATGM","HJ-12",["紅箭12"],"weapon","atgm","陸軍","—","1","約22kg","—","2–4km","—","筒射","頂攻","單兵","紅外成像","火後不理ATGM。","Fire-and-forget ATGM.",["ATGM","單兵"],"ATGM","HJ-12"),
  item("fn-6","飛弩-6 便攜防空飛彈","FN-6 MANPADS","FN-6",["飛弩6"],"weapon","manpads","陸軍","—","1","約16kg","約1.5m","0.5–6km","—","單發","—","單兵","紅外","肩射防空。","MANPADS.",["MANPADS"],"Air Defense","FN-6"),
  item("fn-16","飛弩-16 便攜防空飛彈","FN-16 MANPADS","FN-16",["飛弩16"],"weapon","manpads","陸軍","—","1","—","—","約6km","—","單發","—","單兵","紅外","FN-6改進。","Improved MANPADS.",["MANPADS"],"Air Defense","FN-16"),
  item("qw-1","前衛-1 便攜防空飛彈","QW-1 MANPADS","QW-1",["前衛1"],"weapon","manpads","解放軍／出口","—","1","—","—","約5km","—","單發","—","單兵","紅外","便攜防空。","MANPADS.",["MANPADS"],"Air Defense","QW-1"),
  item("qw-2","前衛-2 便攜防空飛彈","QW-2 MANPADS","QW-2",["前衛2"],"weapon","manpads","解放軍／出口","—","1","—","—","約6km","—","單發","—","單兵","紅外","便攜防空。","MANPADS.",["MANPADS"],"Air Defense","QW-2"),
  item("pp-87","PP-87 82mm迫擊砲","PP-87 Mortar","PP-87",["87迫","82迫"],"weapon","mortar","陸軍","82mm","3–4","約40kg","—","0.1–5.6km","約20rpm","—","—","分解攜行","—","連營迫擊砲。","82mm mortar.",["迫擊砲"],"Mortars","Type 87 mortar"),
  item("pp-89","PP-89 100mm迫擊砲","PP-89 Mortar","PP-89",["100迫"],"weapon","mortar","陸軍","100mm","—","—","—","約6km","—","—","—","牽引","—","100mm迫擊砲。","100mm mortar.",["迫擊砲"],"Mortars",""),
  item("w86-120","W86 120mm迫擊砲","W86 120mm Mortar","W86",["120迫"],"weapon","mortar","陸軍","120mm","—","—","—","約8km","—","—","—","牽引","—","120mm重迫。","120mm mortar.",["迫擊砲"],"Mortars",""),
  item("qts-11","QTS-11 單兵綜合作戰系統","QTS-11","QTS-11",["11式系統"],"weapon","assault_rifle","特種／試裝","5.8mm+20mm","1","—","—","—","—","20發+榴彈","—","攜行","火控","步槍+空爆榴彈。","Rifle+airburst system.",["空爆"],"Small Arms","QTS-11"),
  item("qlg-10","QLG-10 槍榴彈發射器","QLG-10 Underbarrel GL","QLG-10",["10式槍榴"],"weapon","agl","陸軍","35mm","1","—","—","約400m","—","單發","—","掛步槍","—","下掛榴彈發射器。","Underbarrel GL.",["榴彈"],"Small Arms","QLG-10"),
  item("type-91b-gl","91B式槍榴彈","Type 91B GL","Type 91B",["91B"],"weapon","agl","陸軍","35mm","1","—","—","—","—","—","—","掛步槍","—","槍掛榴彈。","Rifle grenade launcher.",["榴彈"],"Small Arms",""),

  # ========== 裝甲 ==========
  item("ztz-99a","99A式主戰坦克","ZTZ-99A MBT","ZTZ-99A",["99A"],"vehicle","mbt","陸軍","125mm滑膛","3","約55t","約11m","砲2–3+km","自動裝填","約40發","複合+ERA","履帶70–80km/h","熱像射控","第三代改型主力坦克。","Top-tier MBT.",["坦克","MBT"],"AFV","Type 99 tank"),
  item("ztz-99","99式主戰坦克","ZTZ-99 MBT","ZTZ-99",["99式"],"vehicle","mbt","陸軍","125mm","3","約54t","約11m","約2–3km","自動裝填","約41發","複合+ERA","履帶","熱像","99系列早期型。","Type 99 base.",["坦克"],"AFV","Type 99 tank"),
  item("ztz-96b","96B式主戰坦克","ZTZ-96B MBT","ZTZ-96B",["96B"],"vehicle","mbt","陸軍","125mm","3","約42.5t","約10.3m","約2–2.5km","自動裝填","約40發","複合+ERA","履帶70+","熱像","大量裝備MBT。","Widely fielded MBT.",["坦克"],"AFV","Type 96 tank"),
  item("ztz-96a","96A式主戰坦克","ZTZ-96A MBT","ZTZ-96A",["96A"],"vehicle","mbt","陸軍","125mm","3","約41t","—","約2km","自動裝填","—","ERA","履帶","改進射控","96改進型。","Type 96A.",["坦克"],"AFV","Type 96 tank"),
  item("ztz-96","96式主戰坦克","ZTZ-96 MBT","ZTZ-96",["96式"],"vehicle","mbt","陸軍","125mm","3","約41t","—","約2km","—","—","—","履帶","—","96系列基型。","Type 96 base.",["坦克"],"AFV","Type 96 tank"),
  item("ztq-15","15式輕型坦克","ZTQ-15 Light Tank","ZTQ-15",["15式","Type15"],"vehicle","light_tank","陸軍","105mm","3","約33–36t","約9.3m","約2+km","自動裝填","—","模組化","履帶高原","現代化射控","高原山地輕坦。","Plateau light tank.",["輕坦","高原"],"AFV","Type 15 tank"),
  item("ztz-88","88式主戰坦克","Type 88 MBT","Type 88",["88式"],"vehicle","mbt","二線","105mm","4","約38t","—","約2km","—","—","—","履帶","—","舊式MBT。","Legacy MBT.",["坦克","舊式"],"AFV","Type 88 tank"),
  item("type-59d","59D式坦克","Type 59D","Type 59D",["59改"],"vehicle","mbt","後備","105mm","4","約36t","—","約1.8km","—","—","附加裝甲","履帶","—","59系改進，後備為主。","Upgraded Type 59.",["坦克","舊式"],"AFV","Type 59 tank"),
  item("zbd-04a","04A式步兵戰車","ZBD-04A IFV","ZBD-04A",["04A"],"vehicle","ifv","陸軍","100mm+30mm","3+7","約24t","約7.2m","機砲約2km","—","載員7","裝甲+ERA可選","履帶兩棲","射控","雙砲步戰車。","Tracked IFV.",["IFV"],"AFV","ZBD-04"),
  item("zbd-04","04式步兵戰車","ZBD-04 IFV","ZBD-04",["04式"],"vehicle","ifv","陸軍","100mm+30mm","3+7","約21.5t","—","—","—","載員","裝甲","履帶兩棲","—","04基型。","ZBD-04 base.",["IFV"],"AFV","ZBD-04"),
  item("zbd-03","03式空降戰車","ZBD-03 AIFV","ZBD-03",["03空降"],"vehicle","ifv","空降兵","30mm","3+5","約8t","—","—","—","載員","輕防護","履帶空投","—","空降IFV。","Airborne IFV.",["空降"],"AFV","ZBD-03"),
  item("zbd-05","05式兩棲突擊車","ZBD-05 AAAV","ZBD-05",["05兩棲"],"vehicle","ifv","陸戰隊","30mm","3+載員","約26t","—","—","—","—","裝甲","高速兩棲","—","高速兩棲步戰。","High-speed amphibious IFV.",["兩棲"],"AFV","ZBD-05"),
  item("ztd-05","05式兩棲突擊砲","ZTD-05","ZTD-05",["05突擊砲"],"vehicle","assault_gun","陸戰隊","105mm","4","約26t","—","約2km","—","—","裝甲","高速兩棲","射控","兩棲105突擊砲。","Amphib 105mm assault gun.",["兩棲","105"],"AFV","ZTD-05"),
  item("zbl-08","08式輪式裝甲運兵車","ZBL-08 APC","ZBL-08",["08運兵"],"vehicle","apc_wheeled","陸軍","12.7mm級","3+載員","約15–16t","約8m","—","—","步兵班","輪式","8×8","—","08族APC。","8x8 APC.",["輪式","APC"],"AFV","Type 08 vehicle"),
  item("zbd-08","08式輪式步戰車","ZBD-08 IFV","ZBD-08",["08步戰"],"vehicle","ifv","陸軍","30mm","3+7","約21t","—","—","—","載員","輪式","8×8","—","08族IFV。","Wheeled IFV.",["輪式","IFV"],"AFV","Type 08 vehicle"),
  item("ztl-11","11式輪式突擊車","ZTL-11","ZTL-11",["11式"],"vehicle","assault_gun","陸軍","105mm","4","約20+t","—","約2+km","—","—","輪式","8×8","射控","105輪式突擊。","Wheeled 105 assault gun.",["突擊車"],"AFV","Type 08 vehicle"),
  item("pll-09","PLL-09 122mm輪式自走砲","PLL-09","PLL-09",["09式122"],"vehicle","sph","陸軍","122mm","5","約16.5t","—","18–22km","6–8rpm","—","輕防護","8×8","數位射控","122輪式自走砲。","122mm wheeled SPH.",["自走砲"],"Artillery","Type 08 vehicle"),
  item("zsl-92","92式輪式裝甲車","ZSL-92 / WZ551","ZSL-92",["92式","WZ551"],"vehicle","apc_wheeled","陸軍","25／12.7mm","3+9","約15t","—","—","—","載員","輪式","6×6","—","舊式輪式裝甲。","Legacy 6x6 APC.",["輪式"],"AFV","Type 92 AFV"),
  item("zsl-10","10式輪式裝甲車","ZSL-10","ZSL-10",["10式輪式"],"vehicle","apc_wheeled","陸軍","—","—","—","—","—","—","載員","輪式","8×8","—","08族變型運兵。","Type 08 APC variant.",["輪式"],"AFV","Type 08 vehicle"),
  item("zsd-89","89式裝甲輸送車","ZSD-89 APC","ZSD-89",["89運兵"],"vehicle","apc_tracked","陸軍","12.7mm","2+13","約14t","—","—","—","載員","裝甲","履帶","—","履帶APC。","Tracked APC.",["APC"],"AFV","Type 89 AFV"),
  item("zsd-63","63式裝甲輸送車","Type 63 APC","Type 63",["63運兵"],"vehicle","apc_tracked","後備","12.7mm","2+13","約12.6t","—","—","—","載員","裝甲","履帶","—","舊式履帶APC。","Legacy tracked APC.",["APC","舊式"],"AFV","Type 63 (armoured personnel carrier)"),
  item("pll-05","PLL-05 120mm自行迫擊砲","PLL-05","PLL-05",["05式120迫"],"vehicle","mortar_sp","陸軍","120mm","4","約16.5t","—","約8+km","—","—","輪式","6×6","射控","120自行迫擊砲。","120mm wheeled SPM.",["迫擊砲"],"Artillery","PLL-05"),
  item("plz-05","PLZ-05 155mm自走榴彈砲","PLZ-05","PLZ-05",["05式155"],"vehicle","sph","陸軍","155mm/52","5","約35t","—","40–50km","8–10rpm","—","裝甲","履帶","自動化射控","主力155自走砲。","Primary 155 SPH.",["自走砲","155"],"Artillery","PLZ-05"),
  item("plz-07","PLZ-07 122mm自走榴彈砲","PLZ-07","PLZ-07",["07式122"],"vehicle","sph","陸軍","122mm","5","約24t","—","18–22km","—","—","裝甲","履帶","—","122履帶自走砲。","122mm tracked SPH.",["自走砲"],"Artillery","PLZ-07"),
  item("plz-89","PLZ-89 122mm自走榴彈砲","PLZ-89","PLZ-89",["89式122"],"vehicle","sph","陸軍","122mm","—","約20t","—","約15–18km","—","—","裝甲","履帶","—","舊式122自走砲。","Legacy 122 SPH.",["自走砲"],"Artillery","Type 89 self-propelled howitzer"),
  item("pcl-181","PCL-181 155mm車載加榴砲","PCL-181","PCL-181",["181","車載155"],"vehicle","truck_howitzer","陸軍","155mm","6","約25t","—","約40+km","—","—","駕駛艙防護","6×6","數位射控","高機動155車載砲。","Truck 155 howitzer.",["火砲","車載"],"Artillery","PCL-181"),
  item("pcl-171","PCL-171 輕型突擊車","PCL-171","PCL-171",["171突擊"],"vehicle","light_vehicle","陸軍","機槍／反戰車","—","—","—","—","—","—","輕防護","高機動","—","可空運輕突擊車。","Light assault vehicle.",["輕車"],"Light Vehicles",""),
  item("pcl-161","PCL-161 122mm車載砲","PCL-161","PCL-161",["161車載122"],"vehicle","truck_howitzer","陸軍","122mm","—","—","—","約20+km","—","—","—","卡車","—","122車載加農砲。","Truck 122 gun.",["火砲"],"Artillery",""),
  item("phl-03","PHL-03 300mm多管火箭","PHL-03","PHL-03",["03火箭砲"],"vehicle","mlrs","陸軍","300mm","—","—","—","70–130km","齊射","12管","卡車","輪式","射控","遠程火箭砲。","300mm MLRS.",["火箭砲"],"Artillery","PHL-03"),
  item("phl-16","PHL-16／PCL-191 模組火箭","PHL-16","PHL-16",["16火箭","PCL-191"],"vehicle","mlrs","陸軍","370／750mm模組","—","—","—","70–300+km","齊射","模組箱","卡車","輪式","射控","模組遠程火箭／飛彈。","Modular long-range MLRS.",["火箭砲","遠程"],"Artillery","PHL-16"),
  item("phz-11","PHZ-11 122mm多管火箭","PHZ-11","PHZ-11",["11火箭"],"vehicle","mlrs","陸軍","122mm","—","—","—","20–40km","齊射","多聯裝","履帶","履帶","射控","122履帶火箭。","Tracked 122 MLRS.",["火箭砲"],"Artillery",""),
  item("phz-89","PHZ-89 122mm多管火箭","Type 89 MLRS","PHZ-89",["89火箭"],"vehicle","mlrs","陸軍","122mm","—","—","—","20–40km","齊射","40管","履帶","履帶","—","舊式122火箭。","Legacy 122 MLRS.",["火箭砲"],"Artillery","Type 89 MLRS"),
  item("phl-81","PHL-81 122mm火箭砲","Type 81 MLRS","PHL-81",["81火箭"],"vehicle","mlrs","後備","122mm","—","—","—","約20km","齊射","40管","卡車","輪式","—","卡車122火箭。","Truck 122 MLRS.",["火箭砲"],"Artillery","Type 81 multiple rocket launcher"),
  item("pgz-09","PGZ-09 35mm自行高砲","PGZ-09","PGZ-09",["09高砲"],"vehicle","spaag","陸軍","35mm雙管","3","約35t","—","約4km","高射速","—","裝甲","履帶","搜索追蹤雷達","點防空高砲。","35mm SPAAG.",["高砲","防空"],"Air Defense","PGZ-09"),
  item("pgz-95","PGZ-95 25mm自行高砲","PGZ-95","PGZ-95",["95高砲"],"vehicle","spaag","陸軍","25mm四管+飛彈","3","約22t","—","約2.5km","—","—","裝甲","履帶","雷達","彈砲結合防空。","SPAAG/missile hybrid.",["高砲"],"Air Defense","Type 95 SPAAG"),
  item("pgz-04a","PGZ-04A 自行高砲","PGZ-04A","PGZ-04A",["04A高砲"],"vehicle","spaag","陸軍","25mm+飛彈","—","—","—","—","—","—","裝甲","履帶","—","彈砲結合改進型。","Improved SPAAG.",["防空"],"Air Defense","Type 95 SPAAG"),
  item("hq-17","紅旗-17 近程防空飛彈","HQ-17 SAM","HQ-17",["紅旗17"],"vehicle","sam","陸軍","地對空","—","—","—","約15km","—","多聯裝","履帶","伴隨部隊","雷達","近程野戰防空。","SHORAD SAM.",["SAM"],"Air Defense","HQ-17"),
  item("hq-17a","紅旗-17A 防空飛彈","HQ-17A","HQ-17A",["紅旗17A"],"vehicle","sam","陸軍","地對空","—","—","—","約15+km","—","多聯裝","輪式","伴隨部隊","雷達","HQ-17輪式改進。","Wheeled HQ-17.",["SAM"],"Air Defense","HQ-17"),
  item("hq-16","紅旗-16 中程防空飛彈","HQ-16","HQ-16",["紅旗16","HHQ-16"],"equipment","sam","陸／海軍","地對空／艦對空","—","—","—","40–70km","—","垂發／輪式","—","陸基／艦載","雷達","中程防空。","Medium SAM.",["SAM","中程"],"Air Defense","HQ-16"),
  item("hq-9","紅旗-9 遠程防空飛彈","HQ-9","HQ-9",["紅旗9"],"equipment","sam","空／海／陸","地對空","連級","—","—","125–300km","—","垂直／斜架","—","輪式／陣地","相控陣","遠程區域防空。","Long-range SAM.",["SAM","遠程"],"Air Defense","HQ-9"),
  item("hq-9b","紅旗-9B 遠程防空飛彈","HQ-9B","HQ-9B",["紅旗9B"],"equipment","sam","解放軍","地對空","連級","—","—","約250–300km","—","垂直","—","輪式","相控陣","HQ-9增程。","Extended HQ-9.",["SAM"],"Air Defense","HQ-9"),
  item("hq-22","紅旗-22 中遠程防空飛彈","HQ-22","HQ-22",["紅旗22"],"equipment","sam","解放軍","地對空","連級","—","—","100–170km","—","傾斜","—","輪式","相控陣","中遠程防空。","Med-long SAM.",["SAM"],"Air Defense","HQ-22"),
  item("hq-7","紅旗-7 近程防空飛彈","HQ-7","HQ-7",["紅旗7","海紅旗7"],"equipment","sam","陸／海軍","地對空","—","—","—","8–15km","—","多聯裝","—","陸／艦","雷達","近程點防空。","Point defense SAM.",["SAM","近程"],"Air Defense","HQ-7"),
  item("hq-10","海紅旗-10 近防飛彈","HQ-10 / FL-3000N","HQ-10",["海紅旗10"],"equipment","sam","海軍","近防飛彈","—","—","—","0.5–10km","—","24聯裝等","—","艦載","紅外","艦載點防空飛彈。","Ship point-defense missile.",["近防","艦載"],"Air Defense","HQ-10"),
  item("ld-2000","LD-2000 陸基近防砲","LD-2000","LD-2000",["陸盾2000"],"vehicle","spaag","陸軍","30mm轉管","—","—","—","約3km","極高射速","—","卡車","輪式","光電／雷達","陸基CIWS。","Land CIWS gun.",["近防"],"Air Defense","LD-2000"),
  item("s-300","S-300 防空系統","S-300PMU","S-300",["S300"],"equipment","sam","空軍防空","遠程地對空","連級","—","—","90–200km","—","—","—","陸基","相控陣","進口遠程防空。","Imported SAM.",["進口","SAM"],"Air Defense","S-300 missile system"),
  item("s-400","S-400 防空系統","S-400","S-400",["S400"],"equipment","sam","空軍防空","遠程地對空","連級","—","—","250–400km","—","—","—","陸基","多雷達","進口遠程防空。","Imported long-range SAM.",["進口","SAM"],"Air Defense","S-400 missile system"),
  item("mengshi","猛士高機動戰術車","Dongfeng Mengshi","EQ2050",["猛士"],"vehicle","light_vehicle","陸軍","依改裝","—","約3.5–5t","—","—","—","—","輕防護","4×4","—","輕型戰術車。","Tactical 4x4.",["輕車"],"Light Vehicles","Dongfeng EQ2050"),
  item("eq2058","猛士III／新一代高機動車","Mengshi III","EQ2058/MSCV",["猛士3"],"vehicle","light_vehicle","陸軍","依改裝","—","—","—","—","—","—","可裝甲","4×4","—","新一代猛士。","Next Mengshi.",["輕車"],"Light Vehicles","Dongfeng EQ2050"),

  # ========== 航空 ==========
  item("j-20","殲-20 戰鬥機","Chengdu J-20","J-20",["殲20","威龍"],"vehicle","aircraft_fighter","空軍","內置彈艙","1","空重約17+t","約21.2m","作戰半徑1000+km","—","內置彈艙","—","第五代","AESA/光電","匿蹤制空戰機。","5th-gen stealth fighter.",["戰鬥機","匿蹤"],"Aircraft","Chengdu J-20"),
  item("j-20s","殲-20S 雙座型","J-20S","J-20S",["殲20S"],"vehicle","aircraft_fighter","空軍","—","2","—","—","—","—","內置彈艙","—","第五代","先進航電","雙座殲-20。","Two-seat J-20.",["戰鬥機"],"Aircraft","Chengdu J-20"),
  item("j-35a","殲-35A 戰鬥機","Shenyang J-35A","J-35A",["殲35A"],"vehicle","aircraft_fighter","空軍","—","1","—","—","—","—","—","—","第五代中型","AESA","中型匿蹤多用途。","Medium stealth fighter.",["戰鬥機","匿蹤"],"Aircraft","Shenyang J-35"),
  item("j-35","殲-35 艦載戰鬥機","Shenyang J-35","J-35",["殲35艦載"],"vehicle","aircraft_fighter","海航","—","1","—","—","—","—","—","—","艦載第五代","AESA","航母艦載匿蹤戰機。","Carrier stealth fighter.",["艦載","戰鬥機"],"Aircraft","Shenyang J-35"),
  item("j-16","殲-16 多用途戰鬥機","Shenyang J-16","J-16",["殲16"],"vehicle","aircraft_fighter","空軍","多用途","2","—","約22m","遠程","—","多掛點","—","4.5代重型","AESA","重型多用途。","Heavy multirole.",["戰鬥機"],"Aircraft","Shenyang J-16"),
  item("j-16d","殲-16D 電子戰機","J-16D","J-16D",["殲16D"],"vehicle","aircraft_fighter","空軍","電戰","2","—","—","—","—","—","—","電子戰","電戰套件","電子戰專用。","EW fighter.",["電子戰"],"Aircraft","Shenyang J-16"),
  item("j-10c","殲-10C 戰鬥機","Chengdu J-10C","J-10C",["殲10C"],"vehicle","aircraft_fighter","空軍","空對空／對地","1","—","約16.9m","—","—","多掛點","—","中輕型","AESA","殲-10最新量產。","Latest J-10.",["戰鬥機"],"Aircraft","Chengdu J-10"),
  item("j-10b","殲-10B 戰鬥機","Chengdu J-10B","J-10B",["殲10B"],"vehicle","aircraft_fighter","空軍","—","1","—","—","—","—","—","—","多用途","DSI","殲-10改進。","J-10B.",["戰鬥機"],"Aircraft","Chengdu J-10"),
  item("j-10a","殲-10A 戰鬥機","Chengdu J-10A","J-10A",["殲10A"],"vehicle","aircraft_fighter","空軍","—","1","—","約16.4m","—","—","—","—","多用途","—","殲-10早期型。","Early J-10.",["戰鬥機"],"Aircraft","Chengdu J-10"),
  item("j-11b","殲-11B 戰鬥機","Shenyang J-11B","J-11B",["殲11B"],"vehicle","aircraft_fighter","空軍／海航","—","1","—","約22m","—","—","多掛點","—","制空","國產航電","蘇-27系國產。","Indigenous Flanker.",["戰鬥機"],"Aircraft","Shenyang J-11"),
  item("j-11bg","殲-11BG 戰鬥機","J-11BG","J-11BG",["殲11BG"],"vehicle","aircraft_fighter","空軍","—","1","—","—","—","—","—","—","制空","AESA升級","J-11B升級。","Upgraded J-11B.",["戰鬥機"],"Aircraft","Shenyang J-11"),
  item("j-11a","殲-11A 戰鬥機","J-11A","J-11A",["殲11A"],"vehicle","aircraft_fighter","空軍","—","1","—","—","—","—","—","—","制空","—","早期國產蘇-27。","Early J-11.",["戰鬥機"],"Aircraft","Shenyang J-11"),
  item("j-15","殲-15 艦載戰鬥機","Shenyang J-15","J-15",["飛鯊"],"vehicle","aircraft_fighter","海航","—","1","—","約22m","—","—","多掛點","—","滑躍／彈射","—","航母艦載戰機。","Carrier fighter.",["艦載"],"Aircraft","Shenyang J-15"),
  item("j-15t","殲-15T 彈射型","J-15T","J-15T",["殲15T"],"vehicle","aircraft_fighter","海航","—","1","—","—","—","—","—","—","彈射","—","CATOBAR適改装。","CATOBAR J-15.",["艦載"],"Aircraft","Shenyang J-15"),
  item("j-15d","殲-15D 電子戰艦載機","J-15D","J-15D",["殲15D"],"vehicle","aircraft_fighter","海航","電戰","2","—","—","—","—","—","—","艦載電戰","—","艦載電子戰機。","Carrier EW.",["電子戰","艦載"],"Aircraft","Shenyang J-15"),
  item("su-30mkk","蘇-30MKK 戰鬥機","Su-30MKK","Su-30MKK",["蘇30"],"vehicle","aircraft_fighter","空軍","—","2","—","約22m","—","—","多掛點","—","多用途","—","俄製重型多用途。","Russian multirole.",["俄製"],"Aircraft","Sukhoi Su-30"),
  item("su-30mk2","蘇-30MK2 戰鬥機","Su-30MK2","Su-30MK2",["蘇30MK2"],"vehicle","aircraft_fighter","海航","—","2","—","—","—","—","—","—","多用途／反艦","—","海軍型蘇-30。","Naval Su-30.",["俄製"],"Aircraft","Sukhoi Su-30"),
  item("su-35","蘇-35S 戰鬥機","Su-35S","Su-35S",["蘇35"],"vehicle","aircraft_fighter","空軍","—","1","—","約22m","—","—","多掛點","—","制空","Irbis-E","俄製超機動戰機。","Su-35S.",["俄製"],"Aircraft","Sukhoi Su-35"),
  item("su-27ubk","蘇-27UBK 雙座","Su-27UBK","Su-27UBK",["蘇27雙座"],"vehicle","aircraft_fighter","空軍","—","2","—","—","—","—","—","—","轉換訓練","—","蘇-27雙座。","Su-27 trainer.",["教練"],"Aircraft","Sukhoi Su-27"),
  item("jh-7a","殲轟-7A 戰鬥轟炸機","Xian JH-7A","JH-7A",["飛豹"],"vehicle","aircraft_strike","海／空軍","反艦／對地","2","—","約22.2m","—","—","重載","—","戰鬥轟炸機","對海對地","反艦與對地。","Fighter-bomber.",["反艦"],"Aircraft","Xian JH-7"),
  item("h-6k","轟-6K 轟炸機","Xian H-6K","H-6K",["轟6K"],"vehicle","aircraft_bomber","空軍","巡航飛彈","—","—","約34.9m","遠程","—","外掛巡航飛彈","—","戰役轟炸機","現代化航電","可掛長劍巡航飛彈。","Cruise-missile bomber.",["轟炸機"],"Aircraft","Xian H-6"),
  item("h-6n","轟-6N 轟炸機","Xian H-6N","H-6N",["轟6N"],"vehicle","aircraft_bomber","空軍","空射彈道／巡航","—","—","—","遠程+加油","—","機腹／掛點","—","可空中加油","—","可加油轟-6。","H-6 with probe.",["轟炸機"],"Aircraft","Xian H-6"),
  item("h-6j","轟-6J 海軍轟炸機","Xian H-6J","H-6J",["轟6J"],"vehicle","aircraft_bomber","海航","反艦飛彈","—","—","—","—","—","多枚反艦","—","海航轟炸機","—","遠程反艦。","PLANAF bomber.",["反艦"],"Aircraft","Xian H-6"),
  item("h-6h","轟-6H 轟炸機","Xian H-6H","H-6H",["轟6H"],"vehicle","aircraft_bomber","空軍","巡航／反艦","—","—","—","—","—","—","—","轟炸機","—","轟-6改進型。","H-6H variant.",["轟炸機"],"Aircraft","Xian H-6"),
  item("j-8f","殲-8F 攔截機","Shenyang J-8F","J-8F",["殲8"],"vehicle","aircraft_fighter","空軍汰換中","—","1","—","約21m","—","—","—","—","攔截","—","舊式攔截機。","Legacy interceptor.",["舊式"],"Aircraft","Shenyang J-8"),
  item("j-7","殲-7 戰鬥機","Chengdu J-7","J-7",["殲7"],"vehicle","aircraft_fighter","汰換中","—","1","—","—","—","—","—","—","舊式","—","米格-21系。","MiG-21 derivative.",["舊式"],"Aircraft","Chengdu J-7"),
  item("kj-500","空警-500 預警機","Shaanxi KJ-500","KJ-500",["空警500"],"vehicle","aircraft_aew","空軍","—","—","—","—","區域空情","—","—","—","預警指揮","固定陣列","主力AEW&C。","Primary AEW&C.",["預警機"],"Aircraft","Shaanxi KJ-500"),
  item("kj-200","空警-200 預警機","Shaanxi KJ-200","KJ-200",["空警200"],"vehicle","aircraft_aew","空軍／海航","—","—","—","—","—","—","—","—","預警","平衡木雷達","中型預警。","Medium AEW.",["預警機"],"Aircraft","Shaanxi KJ-200"),
  item("kj-2000","空警-2000 預警機","KJ-2000","KJ-2000",["空警2000"],"vehicle","aircraft_aew","空軍","—","—","—","—","—","—","—","—","大型預警","圓盤雷達","伊爾-76平台。","Il-76 AEW.",["預警機"],"Aircraft","KJ-2000"),
  item("kj-600","空警-600 艦載預警機","KJ-600","KJ-600",["空警600"],"vehicle","aircraft_aew","海航","—","—","—","—","—","—","—","—","艦載預警","—","航母艦載預警（公開試飛）。","Carrier AEW (public trials).",["預警機","艦載"],"Aircraft","KJ-600"),
  item("y-20","運-20 運輸機","Xian Y-20","Y-20",["運20","鯤鵬"],"vehicle","aircraft_transport","空軍","—","—","MTOW200+t級","約47m","戰略投送","—","重裝備","—","戰略運輸","—","主力戰略運輸機。","Strategic airlifter.",["運輸機"],"Aircraft","Xian Y-20"),
  item("yy-20","運油-20 加油機","YY-20A","YY-20A",["運油20"],"vehicle","aircraft_transport","空軍","—","—","—","—","空中加油","—","—","—","加油機","—","Y-20加油型。","Y-20 tanker.",["加油機"],"Aircraft","Xian Y-20"),
  item("y-9","運-9 運輸機","Shaanxi Y-9","Y-9",["運9"],"vehicle","aircraft_transport","空軍／海航","—","—","—","約36m","戰術投送","—","部隊物資","—","中型運輸","—","中型戰術運輸。","Medium transport.",["運輸機"],"Aircraft","Shaanxi Y-9"),
  item("y-8","運-8 運輸機","Shaanxi Y-8","Y-8",["運8"],"vehicle","aircraft_transport","空軍／海航","—","—","—","—","—","—","—","—","中型運輸","—","安-12系平台。","An-12 class.",["運輸機"],"Aircraft","Shaanxi Y-8"),
  item("y-8gx","運-8特種任務機族","Y-8 special mission","Y-8 GX/JZ",["運8電戰"],"vehicle","aircraft_aew","空軍／海航","—","—","—","—","—","—","—","—","電戰／偵察","—","運-8特種任務變型。","Y-8 special mission family.",["電戰","偵察"],"Aircraft","Shaanxi Y-8"),
  item("il-76","伊爾-76 運輸機","Ilyushin Il-76","Il-76",["伊爾76"],"vehicle","aircraft_transport","空軍","—","—","—","約46.6m","—","—","重載","—","運輸","—","俄製戰略運輸。","Russian airlifter.",["俄製"],"Aircraft","Ilyushin Il-76"),
  item("il-78","伊爾-78 加油機","Ilyushin Il-78","Il-78",["伊爾78"],"vehicle","aircraft_transport","空軍","—","—","—","—","空中加油","—","—","—","加油機","—","俄製加油機。","Russian tanker.",["加油機"],"Aircraft","Ilyushin Il-78"),
  item("kq-200","空潛-200 反潛機","Shaanxi KQ-200","KQ-200",["空潛200","Y-8Q"],"vehicle","aircraft_patrol","海航","魚雷／深彈","—","—","—","反潛巡邏","—","—","—","反潛","磁探／浮標","固定翼反潛機。","Fixed-wing ASW.",["反潛"],"Aircraft","Shaanxi KQ-200"),
  item("y-9jz","運-9JZ 電子偵察機","Y-9JZ","Y-9JZ",["運9JZ"],"vehicle","aircraft_patrol","海航","—","—","—","—","—","—","—","—","電偵","—","電子偵察。","ELINT aircraft.",["電偵"],"Aircraft","Shaanxi Y-9"),
  item("z-20","直-20 通用直升機","Harbin Z-20","Z-20",["直20"],"vehicle","helicopter","陸／海／空軍","依任務","2+載員","—","—","—","—","約一班","—","中型通用","—","中型通用直升機。","Medium utility helo.",["直升機"],"Aircraft","Harbin Z-20"),
  item("z-20f","直-20F 艦載反潛直升機","Z-20F","Z-20F",["直20F"],"vehicle","helicopter","海軍","魚雷等","—","—","—","—","—","—","—","艦載反潛","—","艦載反潛型直-20。","Naval ASW Z-20.",["反潛","直升機"],"Aircraft","Harbin Z-20"),
  item("z-10","直-10 武裝直升機","CAIC Z-10","Z-10",["直10"],"vehicle","helicopter_attack","陸航","機砲+ATGM","2","—","—","—","—","多掛點","座艙防護","攻擊","光電","專用攻擊直升機。","Attack helicopter.",["攻擊直升機"],"Aircraft","CAIC Z-10"),
  item("z-19","直-19 偵察攻擊直升機","Harbin Z-19","Z-19",["直19"],"vehicle","helicopter_attack","陸航","機槍／飛彈","2","—","—","—","—","輕掛載","—","武裝偵察","光電","輕型武裝偵察。","Scout/attack helo.",["直升機"],"Aircraft","Harbin Z-19"),
  item("z-9","直-9 通用直升機","Harbin Z-9","Z-9",["直9"],"vehicle","helicopter","陸／海／空軍","依型號","2+","—","—","—","—","—","—","輕中型","—","海豚系通用直升機。","Dauphin-derived.",["直升機"],"Aircraft","Harbin Z-9"),
  item("z-9c","直-9C 艦載直升機","Z-9C","Z-9C",["直9C"],"vehicle","helicopter","海軍","反潛／反艦","—","—","—","—","—","—","—","艦載","—","艦載直-9。","Naval Z-9.",["艦載","直升機"],"Aircraft","Harbin Z-9"),
  item("z-8","直-8 運輸直升機","Changhe Z-8","Z-8",["直8"],"vehicle","helicopter","陸／海／空軍","—","—","—","—","—","—","部隊物資","—","重型運輸","—","超黃蜂系。","Super Frelon-derived.",["直升機"],"Aircraft","Changhe Z-8"),
  item("z-18","直-18 運輸直升機","Changhe Z-18","Z-18",["直18"],"vehicle","helicopter","海軍／陸軍","—","—","—","—","—","—","—","—","中重型","—","直-8改進。","Improved Z-8.",["直升機"],"Aircraft","Changhe Z-18"),
  item("z-18f","直-18F 反潛直升機","Z-18F","Z-18F",["直18F"],"vehicle","helicopter","海軍","反潛","—","—","—","—","—","—","—","艦載反潛","—","反潛型直-18。","ASW Z-18.",["反潛"],"Aircraft","Changhe Z-18"),
  item("mi-17","米-17 運輸直升機","Mil Mi-17","Mi-17/171",["米17"],"vehicle","helicopter","陸航","—","—","—","—","—","—","部隊","—","中型運輸","—","俄製中型運輸。","Russian transport helo.",["俄製"],"Aircraft","Mil Mi-17"),
  item("mi-171","米-171 運輸直升機","Mil Mi-171","Mi-171",["米171"],"vehicle","helicopter","陸航","—","—","—","—","—","—","—","—","中型運輸","—","米-17系列。","Mi-171.",["俄製"],"Aircraft","Mil Mi-17"),
  item("ka-28","卡-28 反潛直升機","Kamov Ka-28","Ka-28",["卡28"],"vehicle","helicopter","海軍","魚雷／深彈","—","—","—","—","—","—","—","艦載反潛","—","艦載反潛直升機。","Ship ASW helo.",["反潛"],"Aircraft","Kamov Ka-27"),
  item("ka-31","卡-31 預警直升機","Kamov Ka-31","Ka-31",["卡31"],"vehicle","helicopter","海軍","—","—","—","—","—","—","—","—","艦載預警","旋轉雷達","艦載預警直升機。","AEW helicopter.",["預警"],"Aircraft","Kamov Ka-31"),
  item("z-11","直-11 輕型直升機","Harbin Z-11","Z-11",["直11"],"vehicle","helicopter","陸軍","—","1–2","—","—","—","—","—","—","輕型","—","輕型通用／偵察。","Light utility.",["直升機"],"Aircraft","Harbin Z-11"),
  item("jl-9","教練-9 高級教練機","Guizhou JL-9","JL-9",["山鷹"],"vehicle","aircraft_trainer","空軍／海航","—","1–2","—","—","—","—","—","—","高級教練","—","高級教練／輕攻擊。","Advanced trainer.",["教練機"],"Aircraft","Guizhou JL-9"),
  item("jl-10","教練-10 高級教練機","Hongdu JL-10","JL-10",["獵鷹","L-15"],"vehicle","aircraft_trainer","空軍","—","1–2","—","—","—","—","—","—","高級教練","—","高級教練機。","Advanced trainer.",["教練機"],"Aircraft","Hongdu L-15"),
  item("jl-8","教練-8 噴射教練機","Hongdu JL-8","JL-8",["K-8"],"vehicle","aircraft_trainer","空軍","—","2","—","—","—","—","—","—","基礎噴射","—","基礎噴射教練。","Basic jet trainer.",["教練機"],"Aircraft","Hongdu JL-8"),
  item("y-5","運-5 輕型運輸機","Shijiazhuang Y-5","Y-5",["運5"],"vehicle","aircraft_transport","空軍","—","—","—","—","近距","—","—","—","輕型","—","安-2系。","An-2 class.",["運輸機"],"Aircraft","Shijiazhuang Y-5"),
  item("y-7","運-7 運輸機","Xian Y-7","Y-7",["運7"],"vehicle","aircraft_transport","空軍","—","—","—","—","—","—","—","—","支線運輸","—","安-24系。","An-24 class.",["運輸機"],"Aircraft","Xian Y-7"),

  # ========== 無人機 ==========
  item("ch-4","彩虹-4 無人機","CASC CH-4","CH-4",["彩虹4"],"vehicle","uav","解放軍／出口","精確彈藥","地面站","—","—","資料鏈數百km","—","多掛點","—","MALE","光電","察打一體。","MALE UCAV.",["UAV"],"UAV","CASC CH-4"),
  item("ch-5","彩虹-5 無人機","CASC CH-5","CH-5",["彩虹5"],"vehicle","uav","解放軍／出口","重載","地面站","—","—","長航時","—","大載重","—","大型MALE","多感測","大型察打。","Large MALE.",["UAV"],"UAV","CASC CH-5"),
  item("wing-loong-2","翼龍-2 無人機","Wing Loong II","Wing Loong II",["翼龍2","GJ-2"],"vehicle","uav","解放軍／出口","精確彈藥","地面站","—","—","長航時","—","多掛點","—","MALE","光電","察打一體。","MALE UCAV.",["UAV"],"UAV","CAIG Wing Loong II"),
  item("wing-loong-1","翼龍-1 無人機","Wing Loong I","Wing Loong I",["翼龍1"],"vehicle","uav","解放軍／出口","輕彈藥","地面站","—","—","—","—","—","—","MALE","光電","中型察打。","Medium MALE.",["UAV"],"UAV","CAIG Wing Loong"),
  item("tb-001","雙尾蠍 TB-001","TB-001","TB-001",["雙尾蠍"],"vehicle","uav","解放軍／出口","精確彈藥","地面站","—","—","長航時","—","雙尾掛載","—","MALE","光電","雙尾樑偵打。","Twin-boom UAV.",["UAV"],"UAV","TB-001"),
  item("gj-11","攻擊-11 無人攻擊機","GJ-11 Sharp Sword","GJ-11",["利劍"],"vehicle","uav","解放軍","內置彈艙","遙控／自主","—","—","—","—","內置彈艙","—","飛翼匿蹤","—","匿蹤UCAV。","Stealth UCAV.",["UAV","匿蹤"],"UAV","GJ-11"),
  item("wz-7","無偵-7 高空偵察無人機","WZ-7 Soaring Dragon","WZ-7",["翔龍"],"vehicle","uav","解放軍","—","地面站","—","—","高空長航時","—","—","—","HALE","SAR/光電","高空偵察。","HALE recon.",["UAV","偵察"],"UAV","WZ-7"),
  item("wz-8","無偵-8 高速偵察無人機","WZ-8","WZ-8",["無偵8"],"vehicle","uav","解放軍","—","—","—","—","高速","—","—","—","高速偵察","—","高速偵察UAV（公開展示）。","High-speed recon UAV.",["UAV"],"UAV","WZ-8"),
  item("bzk-005","BZK-005 偵察無人機","BZK-005","BZK-005",["BZK005"],"vehicle","uav","解放軍","—","地面站","—","—","長航時","—","—","—","MALE偵察","光電","中高空偵察。","MALE recon.",["UAV"],"UAV","BZK-005"),
  item("asn-209","ASN-209 偵察無人機","ASN-209","ASN-209",["ASN209"],"vehicle","uav","解放軍","—","地面站","—","—","—","—","—","—","戰術偵察","—","戰術偵察UAV。","Tactical UAV.",["UAV"],"UAV","ASN-209"),
  item("ch-7","彩虹-7 匿蹤無人機","CASC CH-7","CH-7",["彩虹7"],"vehicle","uav","展示／發展","—","—","—","—","—","—","—","—","飛翼","—","匿蹤無人作戰機（公開展示）。","Stealth UCAV concept.",["UAV"],"UAV","CASC CH-7"),
  item("wj-700","無偵／攻擊高速無人機 WJ-700","WJ-700","WJ-700",["WJ700"],"vehicle","uav","出口／解放軍","對地對海","地面站","—","—","高空高速","—","—","—","噴射高速","—","高速噴射無人機。","High-speed jet UAV.",["UAV"],"UAV","WJ-700"),

  # ========== 飛彈 ==========
  item("df-21d","東風-21D 反艦彈道飛彈","DF-21D ASBM","DF-21D",["東風21D"],"weapon","ballistic","火箭軍","中程彈道","—","—","—","約1500+km","—","機動發射車","—","公路機動","末端導引","反艦彈道飛彈。","ASBM.",["彈道飛彈","反艦"],"Missiles","DF-21"),
  item("df-21a","東風-21A 中程彈道飛彈","DF-21A","DF-21A",["東風21"],"weapon","ballistic","火箭軍","中程","—","—","—","約1750–2150km","—","機動發射車","—","公路機動","—","中程彈道飛彈。","MRBM.",["彈道飛彈"],"Missiles","DF-21"),
  item("df-26","東風-26 中程彈道飛彈","DF-26","DF-26",["東風26"],"weapon","ballistic","火箭軍","中程","—","—","—","約3000–4000km","—","機動發射車","—","公路機動","對陸／反艦","中程彈道飛彈。","IRBM.",["彈道飛彈"],"Missiles","DF-26"),
  item("df-17","東風-17 高超音速飛彈","DF-17 HGV","DF-17",["東風17"],"weapon","ballistic","火箭軍","高超音速滑翔","—","—","—","約1800–2500km","—","機動發射車","—","公路機動","滑翔載具","高超音速滑翔。","HGV system.",["高超音速"],"Missiles","DF-17"),
  item("df-15b","東風-15B 近程彈道飛彈","DF-15B","DF-15B",["東風15"],"weapon","ballistic","火箭軍","近程","—","—","—","約600–900km","—","機動發射車","—","公路機動","—","近程彈道飛彈。","SRBM.",["彈道飛彈"],"Missiles","DF-15"),
  item("df-16","東風-16 近程彈道飛彈","DF-16","DF-16",["東風16"],"weapon","ballistic","火箭軍","近程","—","—","—","約800–1000km","—","機動發射車","—","公路機動","—","近程彈道飛彈。","SRBM.",["彈道飛彈"],"Missiles","DF-16"),
  item("df-31ag","東風-31AG 洲際彈道飛彈","DF-31AG","DF-31AG",["東風31AG"],"weapon","ballistic","火箭軍","洲際","—","—","—","約11000+km","—","機動發射車","—","公路機動","—","公路機動ICBM。","Road-mobile ICBM.",["ICBM"],"Missiles","DF-31"),
  item("df-41","東風-41 洲際彈道飛彈","DF-41","DF-41",["東風41"],"weapon","ballistic","火箭軍","洲際","—","—","—","約12000–15000km","—","機動發射車","—","公路機動","—","新型公路機動ICBM。","ICBM.",["ICBM"],"Missiles","DF-41"),
  item("df-5c","東風-5C 洲際彈道飛彈","DF-5C","DF-5C",["東風5"],"weapon","ballistic","火箭軍","洲際","—","—","—","約12000+km","—","井射","—","固定井","—","井基ICBM。","Silo ICBM.",["ICBM"],"Missiles","DF-5"),
  item("jl-2","巨浪-2 潛射彈道飛彈","JL-2 SLBM","JL-2",["巨浪2"],"weapon","ballistic","火箭軍／海軍","潛射彈道","—","—","—","約7000+km","—","094型","—","潛射","—","SLBM。","SLBM.",["SLBM"],"Missiles","JL-2"),
  item("jl-3","巨浪-3 潛射彈道飛彈","JL-3 SLBM","JL-3",["巨浪3"],"weapon","ballistic","火箭軍／海軍","潛射彈道","—","—","—","約10000+km","—","094A／096","—","潛射","—","新型SLBM。","New SLBM.",["SLBM"],"Missiles","JL-3"),
  item("cj-10","長劍-10 巡航飛彈","CJ-10 / DH-10","CJ-10",["長劍10"],"weapon","cruise","火箭軍／空軍","陸攻巡航","—","—","—","約1500+km","—","陸基／空射","—","亞音速","複合導航","對陸巡航飛彈。","LACM.",["巡航飛彈"],"Missiles","CJ-10"),
  item("cj-20","長劍-20 空射巡航飛彈","CJ-20","CJ-20",["長劍20"],"weapon","cruise","空軍","空射巡航","—","—","—","約1500+km","—","轟-6K等","—","亞音速","—","空射對陸巡航。","ALCM.",["巡航飛彈"],"Missiles","CJ-10"),
  item("df-100","東風-100／長劍-100","DF-100 / CJ-100","DF-100",["長劍100"],"weapon","cruise","火箭軍","高超音速巡航","—","—","—","約1000–3000km級","—","機動發射車","—","公路機動","—","高超音速巡航（公開）。","Hypersonic cruise (public).",["高超音速"],"Missiles","CJ-100"),
  item("yj-12","鷹擊-12 反艦飛彈","YJ-12","YJ-12",["鷹擊12"],"weapon","asm","海／空軍","超音速反艦","—","—","—","約300–400+km","—","空射／岸射","—","超音速","主動雷達","超音速反艦。","Supersonic AShM.",["反艦"],"Missiles","YJ-12"),
  item("yj-12b","鷹擊-12B 岸艦飛彈","YJ-12B","YJ-12B",["鷹擊12B"],"weapon","asm","岸防","超音速反艦","—","—","—","約400+km","—","岸基發射車","—","機動岸防","—","岸基超音速反艦。","Coastal YJ-12.",["岸防"],"Missiles","YJ-12"),
  item("yj-18","鷹擊-18 反艦飛彈","YJ-18","YJ-18",["鷹擊18"],"weapon","asm","海軍","反艦巡航","—","—","—","約220–540km","—","垂發／潛射","—","亞音速+末端超音速","複合","艦／潛射反艦。","AShM with sprint.",["反艦"],"Missiles","YJ-18"),
  item("yj-83","鷹擊-83 反艦飛彈","YJ-83","YJ-83",["鷹擊83","C-802"],"weapon","asm","海軍／海航","亞音速反艦","—","—","—","約180km","—","艦／空射","—","掠海","主動雷達","主力反艦飛彈。","Mainstay AShM.",["反艦"],"Missiles","YJ-83"),
  item("yj-62","鷹擊-62 反艦飛彈","YJ-62","YJ-62",["鷹擊62"],"weapon","asm","海軍／岸防","亞音速反艦","—","—","—","約280–400km","—","艦／岸","—","亞音速","—","中程反艦。","Medium AShM.",["反艦"],"Missiles","YJ-62"),
  item("yj-21","鷹擊-21 高超音速反艦飛彈","YJ-21","YJ-21",["鷹擊21"],"weapon","asm","海軍","高超音速","—","—","—","遠程（公開）","—","艦載垂發","—","高超音速","—","艦載高超音速（閱兵公開）。","Hypersonic ship missile (public).",["高超音速","反艦"],"Missiles",""),
  item("yj-6","鷹擊-6 反艦飛彈","YJ-6 / C-601","YJ-6",["鷹擊6"],"weapon","asm","海航（舊）","亞音速反艦","—","—","—","約100+km","—","空射","—","亞音速","—","舊式空射反艦。","Legacy air AShM.",["反艦","舊式"],"Missiles","YJ-6"),
  item("c-802a","C-802A 反艦飛彈","C-802A","C-802A",["鷹擊82改進"],"weapon","asm","出口／海軍","亞音速反艦","—","—","—","約180+km","—","—","—","亞音速","—","鷹擊-83相關出口型。","Export AShM.",["反艦"],"Missiles","C-802"),
  item("pl-15","霹靂-15 空對空飛彈","PL-15","PL-15",["霹靂15"],"weapon","aam","空軍／海航","遠程空對空","—","—","—","約200+km","—","機載","—","主動雷達","主動尋標","遠程AAM。","Long-range AAM.",["空對空"],"Missiles","PL-15"),
  item("pl-10","霹靂-10 空對空飛彈","PL-10","PL-10",["霹靂10"],"weapon","aam","空軍／海航","近距","—","—","—","約20km","—","機載","—","高離軸角","紅外成像","近距格鬥彈。","HOBS IR AAM.",["空對空"],"Missiles","PL-10"),
  item("pl-12","霹靂-12 空對空飛彈","PL-12","PL-12",["霹靂12","SD-10"],"weapon","aam","空軍","中遠程","—","—","—","約70–100km","—","機載","—","主動雷達","—","中遠程AAM。","BVR AAM.",["空對空"],"Missiles","PL-12"),
  item("pl-17","霹靂-17 超遠程空對空飛彈","PL-17","PL-17",["霹靂17"],"weapon","aam","空軍","超遠程","—","—","—","超遠程（估計）","—","機載","—","主動雷達","—","超遠程AAM。","VLRAAM.",["空對空"],"Missiles",""),
  item("pl-8","霹靂-8 空對空飛彈","PL-8","PL-8",["霹靂8"],"weapon","aam","空軍","近距","—","—","—","約20km","—","機載","—","紅外","—","舊式近距AAM。","Legacy IR AAM.",["空對空"],"Missiles","PL-8"),
  item("pl-5e","霹靂-5E 空對空飛彈","PL-5E","PL-5E",["霹靂5"],"weapon","aam","空軍","近距","—","—","—","—","—","機載","—","紅外","—","近距紅外彈。","IR AAM.",["空對空"],"Missiles","PL-5"),

  # ========== 海軍 ==========
  item("type-003","003型航母 福建艦","Type 003 Fujian","Type 003",["福建艦"],"vehicle","warship","海軍","艦載機","—","滿載約80000+t","約316m","遠洋","—","電磁彈射","—","常規動力航母","綜合艦島","電磁彈射航母。","CATOBAR carrier.",["航母"],"Naval","Chinese aircraft carrier Fujian"),
  item("type-002","002型航母 山東艦","Type 002 Shandong","Type 002",["山東艦"],"vehicle","warship","海軍","艦載機","—","約60–70000t","約305m","遠洋","—","滑躍","—","常規動力航母","—","國產滑躍航母。","Ski-jump carrier.",["航母"],"Naval","Chinese aircraft carrier Shandong"),
  item("type-001","001型航母 遼寧艦","Type 001 Liaoning","Type 001",["遼寧艦"],"vehicle","warship","海軍","艦載機","—","約60000t","約304m","遠洋","—","滑躍","—","常規動力航母","—","改建航母。","Refitted carrier.",["航母"],"Naval","Chinese aircraft carrier Liaoning"),
  item("type-055","055型驅逐艦","Type 055","Type 055",["南昌艦級"],"vehicle","warship","海軍","112垂發+130mm","約300+","約12–13000t","約180m","遠洋","—","防空反艦對陸","—","燃氣輪機","雙波段相控陣","大型多用途驅逐艦。","Large destroyer.",["驅逐艦"],"Naval","Type 055 destroyer"),
  item("type-052d","052D型驅逐艦","Type 052D","Type 052D",["昆明艦級"],"vehicle","warship","海軍","64垂發+130mm","約280","約7500t","約157m","遠洋","—","防空反艦","—","導彈驅逐艦","相控陣","主力驅逐艦。","Mainstay destroyer.",["驅逐艦"],"Naval","Type 052D destroyer"),
  item("type-052dl","052DL型驅逐艦","Type 052DL","Type 052DL",["052DL"],"vehicle","warship","海軍","64垂發+130mm","—","約7500+t","加長艦尾","遠洋","—","—","—","導彈驅逐艦","相控陣","052D加長型。","Lengthened 052D.",["驅逐艦"],"Naval","Type 052D destroyer"),
  item("type-052c","052C型驅逐艦","Type 052C","Type 052C",["蘭州艦級"],"vehicle","warship","海軍","48垂發+100mm","—","約7000t","約155m","遠洋","—","區域防空","—","導彈驅逐艦","相控陣","早期相控陣驅。","Early AESA DDG.",["驅逐艦"],"Naval","Type 052C destroyer"),
  item("type-052b","052B型驅逐艦","Type 052B","Type 052B",["廣州艦級"],"vehicle","warship","海軍","—","—","約6500t","—","—","—","—","—","導彈驅逐艦","—","過渡型驅逐艦。","Transitional DDG.",["驅逐艦"],"Naval","Type 052B destroyer"),
  item("type-051c","051C型驅逐艦","Type 051C","Type 051C",["瀋陽艦級"],"vehicle","warship","海軍","S-300F系","—","約7100t","—","—","—","區域防空","—","導彈驅逐艦","—","俄系防空驅。","SA-N-20 DDG.",["驅逐艦"],"Naval","Type 051C destroyer"),
  item("type-051b","051B型驅逐艦","Type 051B","Type 051B",["深圳艦"],"vehicle","warship","海軍","—","—","約6100t","—","—","—","—","—","導彈驅逐艦","—","多用途驅逐艦。","Multirole DDG.",["驅逐艦"],"Naval","Type 051B destroyer"),
  item("sovremenny","現代級驅逐艦","Sovremenny class","Project 956E/EM",["現代級"],"vehicle","warship","海軍","反艦＋防空","—","約8000t","—","—","—","—","—","導彈驅逐艦","—","俄製驅逐艦。","Russian DDG.",["俄製","驅逐艦"],"Naval","Sovremenny-class destroyer"),
  item("type-054a","054A型護衛艦","Type 054A","Type 054A",["054A"],"vehicle","warship","海軍","32垂發+76mm","約165","約4000t","約134m","遠海","—","防空反潛","—","護衛艦","拖曳聲納","主力護衛艦。","Workhorse FFG.",["護衛艦"],"Naval","Type 054A frigate"),
  item("type-054b","054B型護衛艦","Type 054B","Type 054B",["054B"],"vehicle","warship","海軍","垂發+艦砲","—","約5000+t","—","—","—","防空反潛","—","新一代護衛","—","新型護衛艦。","Next-gen FFG.",["護衛艦"],"Naval","Type 054B frigate"),
  item("type-054","054型護衛艦","Type 054","Type 054",["054"],"vehicle","warship","海軍","—","—","約3900t","—","—","—","—","—","護衛艦","—","054A前型。","Type 054 base.",["護衛艦"],"Naval","Type 054 frigate"),
  item("type-056a","056A型輕型護衛艦","Type 056A","Type 056A",["江島級"],"vehicle","warship","海軍","反艦+防空+反潛","約60","約1500t","約90m","近海","—","反潛加強","—","輕護衛","拖曳聲納","近海反潛。","ASW corvette.",["輕護衛"],"Naval","Type 056 corvette"),
  item("type-056","056型輕型護衛艦","Type 056","Type 056",["056"],"vehicle","warship","海警／移交","反艦+防空","—","約1500t","約90m","近海","—","—","—","輕護衛","—","部分移交海警。","Corvette.",["輕護衛"],"Naval","Type 056 corvette"),
  item("type-053h3","053H3型護衛艦","Type 053H3","Type 053H3",["江衛II"],"vehicle","warship","海軍（舊）","—","—","約2400t","—","—","—","—","—","護衛艦","—","舊式護衛艦。","Legacy frigate.",["護衛艦","舊式"],"Naval","Type 053H3 frigate"),
  item("type-022","022型飛彈快艇","Type 022","Type 022",["侯北級"],"vehicle","warship","海軍","YJ-83等","—","約220t","約43m","近海","—","反艦飛彈","—","雙體快艇","—","隱身飛彈快艇。","Missile FAC.",["快艇"],"Naval","Type 022 missile boat"),
  item("type-075","075型兩棲攻擊艦","Type 075 LHD","Type 075",["海南艦級"],"vehicle","warship","海軍","近防","—","約35–40000t","約232m","兩棲投送","—","直升機+登陸","—","兩棲攻擊艦","—","LHD。","Amphibious assault ship.",["兩棲"],"Naval","Type 075 landing helicopter dock"),
  item("type-076","076型兩棲攻擊艦","Type 076","Type 076",["076"],"vehicle","warship","海軍","電磁彈射（公開）","—","—","—","兩棲／無人機","—","—","—","兩棲攻擊艦","—","新一代兩攻（公開建造）。","Next LHD/UAV carrier (public).",["兩棲"],"Naval","Type 076 landing helicopter dock"),
  item("type-071","071型船塢登陸艦","Type 071 LPD","Type 071",["崑崙山級"],"vehicle","warship","海軍","近防","—","約25000t","約210m","兩棲","—","氣墊艇+部隊","—","船塢登陸艦","—","LPD。","LPD.",["兩棲"],"Naval","Type 071 amphibious transport dock"),
  item("type-072a","072A型坦克登陸艦","Type 072A LST","Type 072A",["072A"],"vehicle","warship","海軍","—","—","約4800t","約120m","近岸","—","坦克車輛","—","坦克登陸艦","—","LST。","LST.",["兩棲"],"Naval","Type 072A landing ship"),
  item("type-726","726型氣墊登陸艇","Type 726 LCAC","Type 726",["726氣墊"],"vehicle","warship","海軍","—","—","—","—","兩棲快速","—","戰車部隊","—","氣墊","—","LCAC。","LCAC.",["氣墊"],"Naval","Type 726 LCAC"),
  item("type-093","093型攻擊核潛艦","Type 093 SSN","Type 093",["商級"],"vehicle","submarine","海軍","魚雷／反艦飛彈","—","水下約6–7000t","約110m","核動力","—","魚雷管","—","核攻擊潛艦","聲納","SSN。","Nuclear SSN.",["核潛"],"Naval","Type 093 submarine"),
  item("type-093b","093B型攻擊核潛艦","Type 093B","Type 093B",["093B"],"vehicle","submarine","海軍","魚雷／巡航飛彈","—","—","—","—","—","VLS／魚雷","—","核攻擊潛艦","—","093改進型。","Improved Shang.",["核潛"],"Naval","Type 093 submarine"),
  item("type-094","094型彈道飛彈核潛艦","Type 094 SSBN","Type 094",["晉級"],"vehicle","submarine","海軍","JL-2／JL-3","—","—","約135m","核動力","—","SLBM筒","—","戰略核潛","—","SSBN。","SSBN.",["SSBN"],"Naval","Type 094 submarine"),
  item("type-091","091型攻擊核潛艦","Type 091 SSN","Type 091",["漢級"],"vehicle","submarine","海軍","魚雷","—","—","—","核動力","—","魚雷管","—","早期核潛","—","早期SSN。","Early SSN.",["核潛","舊式"],"Naval","Type 091 submarine"),
  item("type-039a","039A／041型柴電潛艦","Type 039A Yuan","Type 039A",["元級","041"],"vehicle","submarine","海軍","魚雷／反艦","約60","水下約3600t","約77.5m","AIP","—","魚雷管","—","AIP柴電","聲納","AIP主力SSK。","AIP SSK.",["潛艦","AIP"],"Naval","Type 039A submarine"),
  item("type-039","039型柴電潛艦","Type 039 Song","Type 039",["宋級"],"vehicle","submarine","海軍","魚雷／反艦","—","約2250t","約75m","—","—","魚雷管","—","柴電","—","宋級SSK。","Song-class SSK.",["潛艦"],"Naval","Type 039 submarine"),
  item("type-035","035型柴電潛艦","Type 035 Ming","Type 035",["明級"],"vehicle","submarine","海軍（舊）","魚雷","—","約2100t","—","—","—","魚雷管","—","柴電","—","舊式柴電潛艦。","Legacy SSK.",["潛艦","舊式"],"Naval","Type 035 submarine"),
  item("kilo","基洛級潛艦","Kilo class","Project 636/877",["基洛"],"vehicle","submarine","海軍","魚雷／飛彈","—","約3000t","—","—","—","魚雷管","—","柴電","—","俄製柴電潛艦。","Russian SSK.",["俄製","潛艦"],"Naval","Kilo-class submarine"),
  item("type-901","901型綜合補給艦","Type 901","Type 901",["呼倫湖級"],"vehicle","warship","海軍","—","—","約45000t","約240m","遠洋補給","—","燃油彈藥","—","快速補給","—","航母編隊補給。","Fast AOE.",["補給艦"],"Naval","Type 901 replenishment ship"),
  item("type-903a","903A型補給艦","Type 903A","Type 903A",["阜康／太湖級"],"vehicle","warship","海軍","—","—","約23000t","約179m","遠洋補給","—","油彈","—","補給艦","—","遠洋補給。","AOR.",["補給艦"],"Naval","Type 903 replenishment ship"),
  item("type-815a","815A型電子偵察艦","Type 815A","Type 815A",["天浪星"],"vehicle","warship","海軍","—","—","約6000t","約130m","遠海偵察","—","—","—","電子偵察","大型天線","AGI電偵艦。","AGI/ELINT ship.",["電偵"],"Naval","Type 815 spy ship"),
  item("type-004-rumor","下一代核動力航母（公開討論）","Next-gen carrier (public discussion)","Type 004?",["004"],"vehicle","warship","海軍","—","—","—","—","—","—","—","—","核動力（傳聞／公開討論）","—","公開媒體討論中之未來航母，非確認服役。","Future carrier under public discussion only.",["航母","未服役"],"Naval",""),
  item("type-730","730近防砲","Type 730 CIWS","Type 730",["730CIWS"],"equipment","ciws","海軍","30mm轉管","—","—","—","約3km","極高射速","—","—","艦載","光電／雷達","艦載近防砲。","Naval CIWS.",["近防"],"Naval","Type 730 CIWS"),
  item("type-1130","1130近防砲","Type 1130 CIWS","Type 1130",["1130"],"equipment","ciws","海軍","30mm十一管","—","—","—","約3km","極高射速","—","—","艦載","雷達光電","新型近防砲。","Advanced CIWS.",["近防"],"Naval","Type 1130 CIWS"),
  item("yu-6","魚-6 重型魚雷","Yu-6 Torpedo","Yu-6",["魚6"],"weapon","torpedo","海軍","重型魚雷","—","—","—","數十km級","—","潛／艦射","—","水中","主被動聲導","重型魚雷。","Heavyweight torpedo.",["魚雷"],"Naval",""),
  item("yu-7","魚-7 輕型魚雷","Yu-7 Torpedo","Yu-7",["魚7"],"weapon","torpedo","海軍","輕型魚雷","—","—","—","—","—","艦／機載","—","水中","—","輕型反潛魚雷。","Lightweight ASW torpedo.",["魚雷"],"Naval",""),
  item("yu-10","魚-10 魚雷","Yu-10","Yu-10",["魚10"],"weapon","torpedo","海軍","重型魚雷","—","—","—","—","—","—","—","水中","—","新型重型魚雷（公開報導）。","New HWT (open source).",["魚雷"],"Naval",""),

  # ========== 單兵裝備 ==========
  item("type-21-uniform","21式作戰服","Type 21 Combat Uniform","Type 21",["21式","星空迷彩"],"equipment","individual","解放軍","—","1","—","—","—","—","—","—","單兵","—","現役作戰服。","Current combat uniform.",["單兵","迷彩"],"Individual","Xingkong (camouflage)"),
  item("type-19-gear","19式單兵攜行系統","Type 19 IOTV/gear","Type 19",["19式攜行"],"equipment","individual","解放軍","—","1","—","—","—","—","插板","防彈","單兵","—","單兵防護攜行具。","Individual body armor system.",["防彈"],"Individual","Xingkong (camouflage)"),
  item("type-07-uniform","07式軍服／迷彩","Type 07 uniform","Type 07",["07式"],"equipment","individual","解放軍","—","1","—","—","—","—","—","—","單兵","—","07系列制服迷彩。","Type 07 uniforms.",["單兵"],"Individual","Type 07"),
  item("qgf-11","QGF-11 頭盔","QGF-11 Helmet","QGF-11",["新式頭盔"],"equipment","individual","解放軍","—","1","—","—","—","—","—","防彈","單兵","可掛夜視","新型戰鬥頭盔。","Modern helmet.",["頭盔"],"Individual",""),
  item("qgf-03","QGF-03 頭盔","QGF-03 Helmet","QGF-03",["03頭盔"],"equipment","individual","解放軍","—","1","—","—","—","—","—","防彈","單兵","—","制式防彈頭盔。","Service helmet.",["頭盔"],"Individual","QGF-03"),
  item("bbg011a","BBG011A 夜視儀","BBG011A NVG","BBG011A",["夜視"],"equipment","individual","解放軍","—","1","—","—","—","—","—","—","單兵","微光","單兵夜視。","NVG.",["夜視"],"Individual",""),

  # ========== 更多陸裝／工程／防化等 ==========
  item("gcl-111","GCL-111 架橋車","GCL-111 Bridgelayer","GCL-111",["架橋車"],"vehicle","engineer","陸軍","—","—","—","—","—","—","—","—","履帶","—","裝甲架橋車。","AVLB bridgelayer.",["工兵"],"Engineer",""),
  item("gcj-112","GCJ 工程車系列","Engineer vehicle family","GCJ series",["工程車"],"vehicle","engineer","陸軍","—","—","—","—","—","—","—","—","履帶／輪式","—","野戰工程車輛。","Combat engineer vehicles.",["工兵"],"Engineer",""),
  item("type-84-minelayer","84式布雷車","Type 84 Minelayer","Type 84",["布雷車"],"vehicle","engineer","陸軍","—","—","—","—","—","—","—","—","履帶","—","機械布雷。","Minelayer.",["工兵","布雷"],"Engineer",""),
  item("phz-10","PHZ-10 遠程火箭（舊稱）","PHZ-10 / related MLRS","PHZ-10",["10式火箭"],"vehicle","mlrs","陸軍","—","—","—","—","遠程","齊射","—","—","輪式","—","遠程火箭相關型號。","Long-range rocket related.",["火箭砲"],"Artillery",""),
  item("pcl-09","PCL-09 122mm車載砲","PCL-09","PCL-09",["09車載122"],"vehicle","truck_howitzer","陸軍","122mm","—","—","—","約20km","—","—","—","卡車","—","122卡車砲。","Truck 122.",["火砲"],"Artillery",""),
  item("pll-01","PLL-01 100mm突擊砲","PLL-01","PLL-01",["100突擊"],"vehicle","assault_gun","陸軍","100mm","—","—","—","—","—","—","輪式","輪式","—","輪式100突擊砲。","Wheeled 100mm.",["突擊砲"],"AFV",""),
  item("zlt-05","ZLT-05 兩棲突擊砲（別名）","ZLT-05","ZLT-05",["兩棲105別名"],"vehicle","assault_gun","陸戰隊","105mm","4","約26t","—","約2km","—","—","裝甲","高速兩棲","射控","與ZTD-05同族公開命名差異。","Amphib assault gun family.",["兩棲"],"AFV","ZTD-05"),
  item("type-63a","63A式水陸坦克","Type 63A","Type 63A",["63A水陸坦"],"vehicle","light_tank","陸戰隊（舊）","105mm","4","約20t","—","—","—","—","—","兩棲","—","舊式兩棲坦克。","Legacy amphib tank.",["兩棲","舊式"],"AFV","Type 63 (tank)"),
  item("type-62","62式輕型坦克","Type 62","Type 62",["62輕坦"],"vehicle","light_tank","後備／舊","85mm","4","約21t","—","—","—","—","—","履帶","—","舊式輕坦。","Legacy light tank.",["輕坦","舊式"],"AFV","Type 62 tank"),
  item("hq-6","紅旗-6 近程防空","HQ-6","HQ-6",["紅旗6"],"equipment","sam","空軍防空","近程","—","—","—","約10–18km","—","—","—","陸基","—","近程防空系統。","SHORAD.",["SAM"],"Air Defense","HQ-6"),
  item("fb-6c","FB-6C 便攜／車載防空","FB-6C","FB-6C",["FB6C"],"equipment","sam","陸軍","近程","—","—","—","—","—","多聯裝","—","車載","—","近程防空飛彈系統。","Short-range SAM vehicle.",["SAM"],"Air Defense",""),
  item("type-90-mlrs","90式122mm火箭砲","Type 90 MLRS","Type 90",["90火箭"],"vehicle","mlrs","陸軍","122mm","—","—","—","約20–40km","齊射","40管","卡車","輪式","—","122卡車火箭。","Truck 122 MLRS.",["火箭砲"],"Artillery","Type 90 multiple rocket launcher"),
  item("type-83-sph","83式152mm自走砲","Type 83 SPH","Type 83",["83式152"],"vehicle","sph","後備","152mm","—","約30t","—","約17km","—","—","裝甲","履帶","—","舊式152自走砲。","Legacy 152 SPH.",["自走砲","舊式"],"Artillery","Type 83 SPH"),
  item("type-66-152","66式152mm加榴砲","Type 66 howitzer","Type 66",["66式152"],"equipment","artillery_towed","後備","152mm","—","—","—","約17km","—","—","—","牽引","—","牽引152加榴。","Towed 152.",["火砲","舊式"],"Artillery","Type 66 howitzer"),
  item("pll-05-alt","07式自行迫擊砲相關","Self-propelled mortar family","SP mortar",["自行迫"],"vehicle","mortar_sp","陸軍","120mm","—","—","—","—","—","—","—","輪／履","—","自行迫擊砲族。","SP mortar family.",["迫擊砲"],"Artillery","PLL-05"),
  item("cs-sm1","CS/SM1 120mm迫擊砲系統","CS/SM1","CS/SM1",["出口120迫"],"equipment","mortar","出口／參考","120mm","—","—","—","—","—","—","—","—","—","120迫擊砲系統（公開出口型）。","Export 120 mortar.",["迫擊砲"],"Mortars",""),
  item("type-86-ifv","86式步兵戰車","Type 86 IFV","Type 86",["86步戰","BMP-1系"],"vehicle","ifv","後備","73mm+機槍","3+8","約13t","—","—","—","載員","裝甲","履帶","—","BMP-1系舊IFV。","BMP-1 derived IFV.",["IFV","舊式"],"AFV","Type 86 IFV"),
  item("type-92b","92B式輪式步戰車","Type 92B","Type 92B",["92B"],"vehicle","ifv","陸軍","30mm／25mm","—","—","—","—","—","載員","輪式","6×6","—","92系改進。","Type 92 upgrade.",["輪式"],"AFV","Type 92 AFV"),
  item("zbd-04a-at","04A反戰車飛彈車","ZBD-04A ATGM carrier","ZBD-04A AT",["04A反坦"],"vehicle","ifv","陸軍","紅箭系列","—","—","—","—","—","—","裝甲","履帶","光電","步戰底盤反坦型。","ATGM carrier on IFV.",["ATGM","IFV"],"AFV","ZBD-04"),
  item("a100","A-100 遠程火箭（出口／相關）","A-100 MLRS","A-100",["A100"],"vehicle","mlrs","出口／相關","300mm","—","—","—","約100+km","齊射","—","卡車","輪式","—","與PHL-03相關出口系統。","Related to PHL-03 export.",["火箭砲"],"Artillery","A-100"),
  item("sr5","SR-5 模組火箭系統","SR-5 MLRS","SR-5",["SR5"],"vehicle","mlrs","出口／解放軍相關","122／220mm模組","—","—","—","依彈種","齊射","模組","卡車","輪式","—","模組火箭（公開出口）。","Modular MLRS export.",["火箭砲"],"Artillery","SR-5"),
  item("pcz-171","PCZ-171 突擊車變型","PCZ-171 family","PCZ-171",["171變型"],"vehicle","light_vehicle","陸軍","依任務","—","—","—","—","—","—","輕防護","高機動","—","171族任務變型。","171 mission variants.",["輕車"],"Light Vehicles",""),
  item("type-05-amphib-family","05兩棲車族（總覽）","Type 05 amphibious family","ZBD/ZTD-05",["05車族"],"vehicle","ifv","陸戰隊","30／105mm","—","約26t","—","—","—","—","裝甲","高速滑水","—","兩棲機械化主力車族總覽。","PLANMC amphib family overview.",["兩棲"],"AFV","ZBD-05"),
  item("hq-9a","紅旗-9A 防空飛彈","HQ-9A","HQ-9A",["紅旗9A"],"equipment","sam","解放軍","地對空","連級","—","—","約200km級","—","—","—","輪式","相控陣","HQ-9改進型。","HQ-9A variant.",["SAM"],"Air Defense","HQ-9"),
  item("hhq-9","海紅旗-9 艦載防空飛彈","HHQ-9","HHQ-9",["海紅旗9"],"equipment","sam","海軍","艦對空","—","—","—","約100–200+km","—","垂發","—","艦載","相控陣","艦載遠程防空。","Naval HQ-9.",["SAM","艦載"],"Air Defense","HQ-9"),
  item("hhq-16","海紅旗-16 艦載防空飛彈","HHQ-16","HHQ-16",["海紅旗16"],"equipment","sam","海軍","艦對空","—","—","—","約40–70km","—","垂發","—","艦載","—","艦載中程防空。","Naval HQ-16.",["SAM","艦載"],"Air Defense","HQ-16"),
  item("yj-18a","鷹擊-18A 潛射反艦飛彈","YJ-18A","YJ-18A",["鷹擊18潛射"],"weapon","asm","海軍","反艦","—","—","—","約220–540km","—","潛射","—","潛射","—","潛射型鷹擊-18。","Sub-launched YJ-18.",["反艦","潛射"],"Missiles","YJ-18"),
  item("cx-1","CX-1 超音速反艦飛彈（出口）","CX-1","CX-1",["CX1"],"weapon","asm","出口","超音速反艦","—","—","—","約280km","—","—","—","超音速","—","出口超音速反艦。","Export supersonic AShM.",["反艦","出口"],"Missiles","CX-1"),
  item("cm-401","CM-401 反艦彈道飛彈（出口展示）","CM-401","CM-401",["CM401"],"weapon","ballistic","出口展示","近程彈道反艦","—","—","—","約290km","—","—","—","—","—","出口展示反艦彈道。","Export ASBM display.",["反艦","出口"],"Missiles","CM-401"),
  item("akd-10","AKD-10 空射反戰車飛彈","AKD-10","AKD-10",["AKD10"],"weapon","atgm","陸航／空軍","空射ATGM","—","—","—","約8–10km","—","直升機／UAV","—","空射","光電","空射反坦。","Air-launched ATGM.",["ATGM","空射"],"ATGM","HJ-10"),
  item("ba-9","藍箭-9 空射反戰車飛彈","Blue Arrow 9","BA-9",["藍箭9"],"weapon","atgm","陸航／UAV","空射ATGM","—","—","—","—","—","—","—","空射","—","空射反坦（公開）。","Air ATGM.",["ATGM"],"ATGM",""),
  item("ty-90","天燕-90 空對空飛彈（直升機）","TY-90","TY-90",["天燕90"],"weapon","aam","陸航","近距空對空","—","—","—","約6km","—","直升機","—","紅外","—","直升機自衛／空戰彈。","Helo AAM.",["空對空","直升機"],"Missiles","TY-90"),
  item("ls-6","雷石-6 滑翔炸彈","LS-6","LS-6",["雷石6"],"weapon","bomb","空軍","精確滑翔炸彈","—","—","—","數十km級","—","機載","—","滑翔","GPS/INS等","精確滑翔炸彈。","Glide bomb.",["炸彈","精確"],"Munitions","LS-6"),
  item("ft-series","飛騰系列精確炸彈","FT series bombs","FT-series",["飛騰炸彈"],"weapon","bomb","空軍","精確炸彈","—","—","—","—","—","機載","—","—","—","精確導引炸彈系列。","Precision bomb family.",["炸彈"],"Munitions",""),
  item("gb-series","GB系列精確炸彈","GB series","GB-series",["GB炸彈"],"weapon","bomb","空軍","精確炸彈","—","—","—","—","—","機載","—","—","—","精確炸彈。","Precision bombs.",["炸彈"],"Munitions",""),
  item("kd-88","空地-88 空地飛彈","KD-88","KD-88",["空地88"],"weapon","cruise","空軍／海航","空地飛彈","—","—","—","約180–200km","—","機載","—","亞音速","—","空地巡航飛彈。","Air-to-surface missile.",["空地"],"Missiles","KD-88"),
  item("yj-91","鷹擊-91 反輻射飛彈","YJ-91 / Kh-31P type","YJ-91",["鷹擊91"],"weapon","asm","空軍／海航","反輻射","—","—","—","約100+km","—","機載","—","超音速","被動雷達","反輻射飛彈。","ARM.",["反輻射"],"Missiles","YJ-91"),
  item("ld-10","雷霆-10 反輻射飛彈","LD-10","LD-10",["雷霆10"],"weapon","asm","空軍","反輻射","—","—","—","—","—","機載","—","—","—","反輻射飛彈（公開）。","ARM (open source).",["反輻射"],"Missiles",""),
]


def load_cache():
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(c):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")


def http_get(url: str, timeout=20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def http_json(url: str):
    return json.loads(http_get(url).decode("utf-8", errors="replace"))


def commons_thumb(filename: str, width: int = 640) -> str:
    """Get thumbnail URL via Commons API (robot-policy friendly sizes)."""
    title = "File:" + filename.replace(" ", "_")
    q = urllib.parse.urlencode({
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": str(width),
        "format": "json",
    })
    url = "https://commons.wikimedia.org/w/api.php?" + q
    try:
        d = http_json(url)
        pages = (d.get("query") or {}).get("pages") or {}
        for p in pages.values():
            infos = p.get("imageinfo") or []
            if not infos:
                continue
            # prefer scaled thumb
            return infos[0].get("thumburl") or infos[0].get("url") or ""
    except Exception as e:
        print(f"  commons fail {filename}: {e}")
    return ""


def wiki_thumb(title: str) -> str:
    if not title:
        return ""
    title = title.strip().replace(" ", "_")
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title, safe="")
    try:
        d = http_json(url)
        t = (d.get("thumbnail") or {}).get("source") or ""
        # keep API-provided size (policy-friendly); optionally bump to 640 if present pattern
        if t:
            t = re.sub(r"/\d+px-", "/640px-", t)
        return t
    except Exception:
        return ""


def http_get_retry(url: str, retries: int = 5) -> bytes:
    delay = 1.5
    last = None
    for i in range(retries):
        try:
            return http_get(url, timeout=30)
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 503):
                print(f"  rate-limit, sleep {delay:.1f}s…")
                time.sleep(delay)
                delay = min(delay * 1.8, 30)
                continue
            raise
        except Exception as e:
            last = e
            time.sleep(delay)
            delay = min(delay * 1.5, 20)
    raise last  # type: ignore


def download_image(item_id: str, url: str, url_owner: dict) -> str:
    """Download thumbnail to assets/images/{id}.*; share file if same URL already saved."""
    if not url:
        return ""
    IMG_DIR.mkdir(parents=True, exist_ok=True)

    # reuse file if same remote URL already downloaded for another id
    if url in url_owner:
        other = url_owner[url]
        for ext in (".jpg", ".png", ".webp", ".img"):
            p = IMG_DIR / f"{other}{ext}"
            if p.exists() and p.stat().st_size > 1500:
                # copy bytes under this id so each card has own path (avoids confusion)
                dest = IMG_DIR / f"{item_id}{ext}"
                if not dest.exists():
                    dest.write_bytes(p.read_bytes())
                return f"assets/images/{dest.name}"

    for ext in (".jpg", ".png", ".webp", ".img"):
        existing = IMG_DIR / f"{item_id}{ext}"
        if existing.exists() and existing.stat().st_size > 1500:
            url_owner[url] = item_id
            return f"assets/images/{existing.name}"

    try:
        data = http_get_retry(url)
        if len(data) < 1200:
            return ""
        if data[:3] == b"\xff\xd8\xff":
            dest = IMG_DIR / f"{item_id}.jpg"
        elif data[:8] == b"\x89PNG\r\n\x1a\n":
            dest = IMG_DIR / f"{item_id}.png"
        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            dest = IMG_DIR / f"{item_id}.webp"
        else:
            dest = IMG_DIR / f"{item_id}.img"
        dest.write_bytes(data)
        url_owner[url] = item_id
        return f"assets/images/{dest.name}"
    except Exception as e:
        print(f"  DL fail {item_id}: {e}")
        return ""


def main():
    cache = load_cache()
    items = []
    url_owner: dict[str, str] = {}

    print(f"Building {len(CATALOG)} items...")

    for idx, row in enumerate(CATALOG):
        (
            eid, name_zh, name_en, designation, aliases, category, subcategory,
            service_zh, caliber, crew, weight, length, range_m, rof, capacity,
            armor, mobility, sensors, notes_zh, notes_en, tags, odin_hint, wiki,
        ) = row

        image_url = ""

        # 1) Commons file override (exact file)
        if eid in FILE_OVERRIDES:
            ck = "file:" + FILE_OVERRIDES[eid]
            if ck in cache and cache[ck]:
                image_url = cache[ck]
            else:
                image_url = commons_thumb(FILE_OVERRIDES[eid], 640)
                cache[ck] = image_url
                time.sleep(0.35)
        # 2) exact wiki page thumbnail only (no fuzzy search)
        if not image_url and wiki:
            ck = "wiki:" + wiki
            if ck in cache:
                image_url = cache[ck]
            else:
                image_url = wiki_thumb(wiki)
                cache[ck] = image_url
                time.sleep(0.35)
                print(("OK" if image_url else "--"), wiki)

        origin, origin_zh = "China", "中國"
        blob = name_en + designation + name_zh
        if any(k in blob for k in ("Su-", "S-300", "S-400", "Il-", "Mi-17", "Mi-171", "Ka-28", "Ka-31", "Sovremenny", "Kilo", "Project 956", "Project 636")):
            origin, origin_zh = "Russia", "俄羅斯／蘇聯"

        local_image = ""
        remote = image_url or ""
        if remote:
            local_image = download_image(eid, remote, url_owner)
            time.sleep(0.45)

        # Prefer local; always keep remote as backup for app onerror
        display = local_image or remote

        items.append({
            "id": eid,
            "name_zh": name_zh,
            "name_en": name_en,
            "designation": designation,
            "aliases": aliases,
            "category": category,
            "subcategory": subcategory,
            "origin": origin,
            "origin_zh": origin_zh,
            "service": service_zh,
            "service_zh": service_zh,
            "caliber": caliber,
            "crew": crew,
            "weight_kg": weight,
            "length_mm": length,
            "range_m": range_m,
            "rate_of_fire": rof,
            "capacity": capacity,
            "armor": armor,
            "mobility": mobility,
            "sensors": sensors,
            "notes_zh": notes_zh,
            "notes_en": notes_en,
            "tags": tags,
            "odin_hint": odin_hint,
            "wiki": wiki,
            "image": display,
            "image_remote": remote if local_image else "",
            "odin_url": "https://odin.t2com.army.mil/WEG",
        })

        if (idx + 1) % 25 == 0:
            save_cache(cache)
            print(f"… progress {idx+1}/{len(CATALOG)}")

    # clean empty image_remote
    for it in items:
        if not it.get("image_remote"):
            it.pop("image_remote", None)

    save_cache(cache)

    js = (
        "/**\n"
        " * 解放軍武器／裝備／載具資料庫（公開來源＋本機圖片）\n"
        " * 訓練教育參考；正式以 ODIN WEG 為準。\n"
        " * 由 tools/rebuild_full.py 產生。\n"
        " */\n"
        "window.EQUIPMENT_DATA = "
        + json.dumps(items, ensure_ascii=False, indent=2)
        + ";\n"
    )
    OUT_JS.write_text(js, encoding="utf-8")

    n = len(items)
    with_img = sum(1 for i in items if i.get("image"))
    local_n = sum(1 for i in items if str(i.get("image", "")).startswith("assets/"))
    # duplicate remote analysis
    urls = {}
    for i in items:
        u = i.get("image") or ""
        if u.startswith("http"):
            urls.setdefault(u, []).append(i["id"])
    dups = {k: v for k, v in urls.items() if len(v) > 1}
    print(f"DONE items={n} with_image={with_img} local={local_n} remote_dups={len(dups)}")
    print(f"images dir: {IMG_DIR} ({len(list(IMG_DIR.glob('*')))} files)")


if __name__ == "__main__":
    main()
