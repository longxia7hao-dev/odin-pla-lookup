#!/usr/bin/env python3
"""Build expanded PLA equipment catalog with Wikimedia/Wikipedia images."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "js" / "equipment-data.js"
CACHE = Path(__file__).resolve().parents[1] / "data" / "image_cache.json"
UA = "PLA-Equipment-Lookup/1.0 (offline training tool; educational)"

# fmt: off
# Each: id, name_zh, name_en, designation, aliases, category, subcategory,
# service_zh, caliber, crew, weight, length, range, rof, capacity, armor, mobility, sensors,
# notes_zh, notes_en, tags, odin_hint, wiki
CATALOG = [
  # ===== 輕兵器 =====
  ("qbz-191","QBZ-191 突擊步槍","QBZ-191 Assault Rifle","QBZ-191",["191","Type 191","新式步槍"],"weapon","assault_rifle","解放軍陸軍","5.8×42mm","1","約 3.25 kg","約 950 mm","400–600 m","約 750 rpm","30 發","—","步兵攜行","光學瞄具可選","新制式步槍，逐步取代 QBZ-95。","Standard service rifle replacing QBZ-95.",["步槍","5.8mm","制式"],"Infantry Weapons","QBZ-191"),
  ("qbz-95-1","QBZ-95-1 突擊步槍","QBZ-95-1 Assault Rifle","QBZ-95-1",["95-1","95式","Type 95"],"weapon","assault_rifle","解放軍","5.8×42mm","1","約 3.3 kg","約 745 mm","約 400 m","約 650 rpm","30 發","—","步兵攜行","機械／光學","無托制式步槍，仍大量服役。","Bullpup service rifle still widely fielded.",["步槍","無托","5.8mm"],"Infantry Weapons","QBZ-95"),
  ("qbz-95b","QBZ-95B 短突擊步槍","QBZ-95B Carbine","QBZ-95B",["95B"],"weapon","assault_rifle","解放軍","5.8×42mm","1","約 2.9 kg","約 610 mm","約 300 m","約 650 rpm","30 發","—","步兵攜行","—","QBZ-95 短管型，特種／車組用。","Short-barrel QBZ-95 variant.",["步槍","短管"],"Infantry Weapons","QBZ-95"),
  ("qbz-03","QBZ-03 突擊步槍","QBZ-03 Assault Rifle","QBZ-03",["03式"],"weapon","assault_rifle","解放軍／武警","5.8×42mm","1","約 3.5 kg","約 950 mm","約 400 m","約 650 rpm","30 發","—","步兵攜行","—","傳統布局步槍。","Conventional-layout assault rifle.",["步槍","5.8mm"],"Infantry Weapons","QBZ-03"),
  ("qbu-191","QBU-191 精確射手步槍","QBU-191 DMR","QBU-191",["191 DMR"],"weapon","dmr","解放軍","5.8×42mm","1","約 4.5 kg","約 1080 mm","600–800 m","半自動","20–30 發","—","步兵攜行","光學瞄具","QBZ-191 族精確射手步槍。","DMR of QBZ-191 family.",["精確射手","5.8mm"],"Infantry Weapons","QBZ-191"),
  ("qbu-88","QBU-88 狙擊步槍","QBU-88 Sniper Rifle","QBU-88",["88式狙擊"],"weapon","dmr","解放軍","5.8×42mm","1","約 4.1 kg","約 920 mm","約 800 m","半自動","10 發","—","步兵攜行","光學","班用狙擊／精確射手。","Squad marksman rifle.",["狙擊","5.8mm"],"Infantry Weapons","QBU-88"),
  ("qbu-10","QBU-10 反器材步槍","QBU-10 AMR","QBU-10",["10式","Type 10"],"weapon","amr","解放軍","12.7×108mm","1","約 13.3 kg","約 1380 mm","1000–1500 m","半自動","5 發","—","步兵攜行","晝夜瞄具","12.7mm 反器材步槍。","12.7mm anti-materiel rifle.",["反器材","12.7mm"],"Infantry Weapons","QBU-10"),
  ("qsz-92","QSZ-92 手槍","QSZ-92 Pistol","QSZ-92",["92式"],"weapon","pistol","解放軍","5.8×21mm／9×19mm","1","約 0.76 kg","約 190 mm","約 50 m","半自動","15–20 發","—","隨身","—","制式手槍系列。","Service pistol family.",["手槍"],"Infantry Weapons","QSZ-92"),
  ("qsw-06","QSW-06 微聲手槍","QSW-06 Suppressed Pistol","QSW-06",["06微聲"],"weapon","pistol","特種部隊","5.8×21mm","1","約 1.1 kg","—","約 50 m","半自動","20 發","—","隨身","消音","特種部隊微聲手槍。","Suppressed special-forces pistol.",["手槍","消音","特種"],"Infantry Weapons","QSW-06"),
  ("qcw-05","QCW-05 衝鋒槍","QCW-05 SMG","QCW-05",["05式衝鋒槍"],"weapon","smg","特種部隊","5.8×21mm","1","約 2.2 kg","約 500 mm","約 200 m","約 900 rpm","50 發","—","步兵攜行","可裝消音","無托 PDW／衝鋒槍。","Bullpup PDW/SMG.",["衝鋒槍","特種"],"Infantry Weapons","QCW-05"),
  ("qcq-171","QCQ-171 衝鋒槍","QCQ-171 SMG","QCQ-171",["CS/LS7"],"weapon","smg","解放軍","9×19mm","1","約 2.8 kg","—","約 200 m","高射速","30 發","—","步兵攜行","—","9mm 衝鋒槍。","9mm submachine gun.",["衝鋒槍","9mm"],"Infantry Weapons","CS/LS7"),
  ("type-79-smg","79 式衝鋒槍","Type 79 SMG","Type 79",["79衝"],"weapon","smg","解放軍（有限）","7.62×25mm","1","約 1.9 kg","約 740 mm","約 200 m","約 1000 rpm","20 發","—","步兵攜行","—","舊式衝鋒槍，有限服役。","Legacy SMG limited service.",["衝鋒槍"],"Infantry Weapons","Type_79_submachine_gun"),
  ("qjy-88","QJY-88 通用機槍","QJY-88 GPMG","QJY-88",["88式機槍"],"weapon","mg","解放軍","5.8×42mm","1–2","約 7.6 kg","約 1150 mm","800–1000 m","650–700 rpm","彈鏈／彈鼓","—","三腳架／攜行","—","5.8mm 通用機槍。","5.8mm GPMG.",["機槍","5.8mm"],"Infantry Weapons","QJY-88"),
  ("qjy-201","QJY-201 通用機槍","QJY-201 GPMG","QJY-201",["201機槍"],"weapon","mg","解放軍","5.8×42mm","1–2","—","—","約 1000 m","—","彈鏈","—","班排","—","新一代通用機槍。","Next-gen GPMG.",["機槍","5.8mm"],"Infantry Weapons",""),
  ("qjz-89","QJZ-89 重機槍","QJZ-89 HMG","QJZ-89",["89式重機槍"],"weapon","hmg","解放軍","12.7×108mm","2–3","槍身約 17.5 kg","約 1600 mm","1500–2000 m","450–600 rpm","彈鏈","—","三腳架／車載","—","輕量化 12.7mm 重機槍。","Lightweight 12.7mm HMG.",["重機槍","12.7mm"],"Infantry Weapons","QJZ-89"),
  ("qjz-171","QJZ-171 重機槍","QJZ-171 HMG","QJZ-171",["171重機槍"],"weapon","hmg","解放軍","12.7×108mm","2–3","—","—","約 2000 m","—","彈鏈","—","三腳架／車載","—","新型 12.7mm 重機槍。","New 12.7mm HMG.",["重機槍","12.7mm"],"Infantry Weapons",""),
  ("qlz-87","QLZ-87 自動榴彈發射器","QLZ-87 AGL","QLZ-87",["87式榴彈"],"weapon","agl","解放軍","35mm","2–3","12–20 kg","約 970 mm","600–1750 m","約 480 rpm","6／15 發彈鼓","—","三腳架／車載","—","35mm 自動榴彈。","35mm automatic grenade launcher.",["榴彈","火力支援"],"Infantry Weapons","QLZ-87"),
  ("qlz-04","QLZ-04 自動榴彈發射器","QLZ-04 AGL","QLZ-04",["04式榴彈"],"weapon","agl","解放軍","35mm","2–3","約 20 kg","—","約 1750 m","—","彈鼓","—","三腳架／車載","—","QLZ-87 改進型。","Improved AGL.",["榴彈"],"Infantry Weapons","QLZ-04"),
  ("qlu-11","QLU-11 精確榴彈發射器","QLU-11 Precision GL","QLU-11",["11式榴彈"],"weapon","agl","解放軍","35mm","1–2","—","—","約 1000 m","半自動","—","—","步兵","光學","班用精確榴彈。","Precision grenade launcher.",["榴彈","精確"],"Infantry Weapons","QLU-11"),
  ("pf-98","PF-98 火箭筒","PF-98 Rocket Launcher","PF-98",["98式火箭筒"],"weapon","at_rocket","解放軍","120mm","1–2","發射器約 10 kg","約 1191 mm","400–800 m","—","單發","破甲依彈藥","步兵攜行","光學","步兵反裝甲火箭。","120mm recoilless rocket AT weapon.",["反裝甲","火箭筒"],"Infantry Weapons","PF-98"),
  ("pf-98a","PF-98A 火箭筒","PF-98A Rocket Launcher","PF-98A",["98A"],"weapon","at_rocket","解放軍","120mm","1–2","—","—","約 800 m","—","單發","—","步兵攜行","改進瞄具","PF-98 改進型。","Improved PF-98.",["反裝甲"],"Infantry Weapons","PF-98"),
  ("dzj-08","DZJ-08 火箭彈","DZJ-08 Assault Rocket","DZJ-08",["08式單兵火箭"],"weapon","at_rocket","解放軍","80mm 級","1","—","—","約 300 m","—","一次性","—","步兵","—","一次性單兵火箭。","Disposable assault rocket.",["反裝甲","一次性"],"Infantry Weapons","DZJ-08"),
  ("hj-8","紅箭-8 反戰車飛彈","HJ-8 ATGM","HJ-8 / Red Arrow-8",["紅箭8","ATGM"],"weapon","atgm","解放軍","—","2–3","系統約 25 kg","—","3000–4000 m","—","管射","串聯破甲","三腳架／車載","光學／紅外","有線制導反戰車飛彈。","Wire-guided ATGM.",["反戰車","ATGM"],"ATGM","HJ-8"),
  ("hj-9","紅箭-9 反戰車飛彈","HJ-9 ATGM","HJ-9",["紅箭9"],"weapon","atgm","解放軍","—","2–3","—","—","約 5000 m","—","管射","重破甲","車載／三腳架","光學","重型反戰車飛彈。","Heavy ATGM.",["反戰車","ATGM"],"ATGM","HJ-9"),
  ("hj-10","紅箭-10 反戰車飛彈","HJ-10 ATGM","HJ-10",["紅箭10","AFT-10"],"weapon","atgm","解放軍","—","—","—","—","約 10 km","—","箱射","—","車載／直升機","光電","遠程反戰車飛彈。","Long-range ATGM.",["反戰車","ATGM"],"ATGM","HJ-10"),
  ("hj-12","紅箭-12 反戰車飛彈","HJ-12 ATGM","HJ-12",["紅箭12"],"weapon","atgm","解放軍","—","1","約 22 kg","—","2000–4000 m","—","筒射","頂攻","單兵","紅外成像","火後不理單兵反戰車飛彈。","Fire-and-forget manpad ATGM.",["反戰車","單兵"],"ATGM","HJ-12"),
  ("fn-6","飛弩-6 便攜防空飛彈","FN-6 MANPADS","FN-6",["飛弩6"],"weapon","manpads","解放軍","—","1","系統約 16 kg","約 1495 mm","0.5–6 km","—","單發","—","單兵","紅外","肩射防空飛彈。","Man-portable IR SAM.",["防空","MANPADS"],"MANPADS","FN-6"),
  ("fn-16","飛弩-16 便攜防空飛彈","FN-16 MANPADS","FN-16",["飛弩16"],"weapon","manpads","解放軍","—","1","—","—","約 6 km","—","單發","—","單兵","紅外改進","FN-6 改進型。","Improved MANPADS.",["防空","MANPADS"],"MANPADS","FN-16"),
  ("qw-2","前衛-2 便攜防空飛彈","QW-2 MANPADS","QW-2",["前衛2"],"weapon","manpads","解放軍／出口","—","1","—","—","約 6 km","—","單發","—","單兵","紅外","便攜防空飛彈。","MANPADS.",["防空","MANPADS"],"MANPADS","QW-2"),
  ("pp-87","PP-87 迫擊砲","PP-87 Mortar","PP-87",["87式迫擊砲","82mm"],"weapon","mortar","解放軍","82mm","3–4","約 40 kg","—","100–5600 m","約 20 rpm","—","—","分解攜行","—","連營 82mm 迫擊砲。","Company/battalion 82mm mortar.",["迫擊砲"],"Mortars","Type_87_mortar"),
  ("pp-89","PP-89 迫擊砲","PP-89 Mortar","PP-89",["100mm迫"],"weapon","mortar","解放軍","100mm","—","—","—","約 6 km","—","—","—","牽引／車載","—","100mm 迫擊砲。","100mm mortar.",["迫擊砲"],"Mortars",""),
  ("w-86","W86 迫擊砲","W86 Mortar","W86",["120mm迫"],"weapon","mortar","解放軍","120mm","—","—","—","約 8 km","—","—","—","牽引","—","120mm 重迫擊砲。","120mm heavy mortar.",["迫擊砲","120mm"],"Mortars",""),
  ("type-69-rpg","69 式火箭筒","Type 69 RPG","Type 69",["69式","RPG"],"weapon","at_rocket","二線／民兵","40mm 發射筒","1","約 5.6 kg","—","約 300 m","—","—","—","步兵","—","RPG-7 系舊式火箭筒。","RPG-7 type launcher.",["反裝甲","RPG"],"Infantry Weapons","Type_69_RPG"),
  ("type-56-rifle","56 式自動步槍","Type 56 Assault Rifle","Type 56",["56半","AK"],"weapon","assault_rifle","民兵／二線","7.62×39mm","1","約 3.8 kg","約 874 mm","約 300 m","約 600 rpm","30 發","—","步兵","—","AK-47 系，後備為主。","AK-pattern legacy rifle.",["步槍","AK"],"Infantry Weapons","Type_56_assault_rifle"),

  # ===== 裝甲／載具 =====
  ("ztz-99a","99A 式主戰坦克","ZTZ-99A MBT","ZTZ-99A / Type 99A",["99A","Type 99A"],"vehicle","mbt","解放軍陸軍","125mm 滑膛","3","約 55 t","約 11 m","砲 2–3+ km","自動裝填","約 40 發","複合＋ERA","履帶 70–80 km/h","熱像射控","第三代改型主力坦克。","Top-tier PLA MBT.",["坦克","MBT","125mm"],"AFV/Tanks","Type_99_tank"),
  ("ztz-99","99 式主戰坦克","ZTZ-99 MBT","ZTZ-99 / Type 99",["99式","ZTZ99"],"vehicle","mbt","解放軍陸軍","125mm","3","約 54 t","約 11 m","約 2–3 km","自動裝填","約 41 發","複合＋ERA","履帶","熱像","99 系列早期型。","Type 99 base series.",["坦克","MBT"],"AFV/Tanks","Type_99_tank"),
  ("ztz-96b","96B 式主戰坦克","ZTZ-96B MBT","ZTZ-96B",["96B","Type 96B"],"vehicle","mbt","解放軍陸軍","125mm","3","約 42.5 t","約 10.3 m","約 2–2.5 km","自動裝填","約 40 發","複合＋ERA","履帶 70+ km/h","熱像","大量裝備主戰坦克。","Widely fielded MBT.",["坦克","MBT"],"AFV/Tanks","Type_96_tank"),
  ("ztz-96a","96A 式主戰坦克","ZTZ-96A MBT","ZTZ-96A",["96A"],"vehicle","mbt","解放軍陸軍","125mm","3","約 41 t","—","約 2 km","自動裝填","—","ERA","履帶","改進射控","96 系列改進型。","Type 96A upgrade.",["坦克"],"AFV/Tanks","Type_96_tank"),
  ("ztq-15","15 式輕型坦克","ZTQ-15 Light Tank","ZTQ-15 / Type 15",["15式","Type 15"],"vehicle","light_tank","解放軍","105mm","3","約 33–36 t","約 9.3 m","約 2+ km","自動裝填","—","模組化","履帶；高原機動","現代化射控","高原／山地輕坦。","Light tank for plateau/mountain.",["輕坦","105mm","高原"],"AFV/Tanks","Type_15_tank"),
  ("ztz-88","88 式主戰坦克","Type 88 MBT","Type 88",["88式"],"vehicle","mbt","二線","105mm","4","約 38 t","—","約 2 km","—","—","均質／附加","履帶","—","舊式主戰坦克，逐步退役。","Legacy MBT phasing out.",["坦克","舊式"],"AFV/Tanks","Type_88_tank"),
  ("zbd-04a","04A 式步兵戰車","ZBD-04A IFV","ZBD-04A",["04A","ZBD04A"],"vehicle","ifv","解放軍陸軍","100mm＋30mm","3＋7","約 24 t","約 7.2 m","機砲約 2 km","—","載員約 7","裝甲＋ERA可選","履帶／兩棲","射控","雙砲步戰車。","Tracked IFV dual armament.",["步戰車","IFV"],"AFV/IFV","ZBD-04"),
  ("zbd-04","04 式步兵戰車","ZBD-04 IFV","ZBD-04",["04式"],"vehicle","ifv","解放軍陸軍","100mm＋30mm","3＋7","約 21.5 t","—","—","—","載員","裝甲","履帶／兩棲","—","04 系列基型。","ZBD-04 base.",["步戰車"],"AFV/IFV","ZBD-04"),
  ("zbd-03","03 式空降戰車","ZBD-03 AIFV","ZBD-03",["03空降"],"vehicle","ifv","空降兵","30mm","3＋5","約 8 t","—","—","—","載員","輕防護","履帶／空投","—","空降步兵戰車。","Airborne IFV.",["空降","IFV"],"AFV/IFV","ZBD-03"),
  ("zbd-05","05 式兩棲突擊車","ZBD-05 AAAV","ZBD-05",["05兩棲"],"vehicle","ifv","海軍陸戰隊／兩棲","30mm／105mm 型","3＋載員","約 26 t","—","—","—","—","裝甲","高速兩棲","—","高速兩棲突擊車族。","High-speed amphibious assault vehicle.",["兩棲","陸戰隊"],"AFV/Amphibious","ZBD-2000"),
  ("ztd-05","05 式兩棲突擊砲","ZTD-05 Assault Gun","ZTD-05",["05突擊砲"],"vehicle","assault_gun","海軍陸戰隊","105mm","4","約 26 t","—","約 2 km","—","—","裝甲","高速兩棲","射控","兩棲 105mm 突擊砲。","Amphibious 105mm assault gun.",["兩棲","105mm"],"AFV/Amphibious","ZBD-2000"),
  ("zbl-08","08 式輪式裝甲車族","ZBL-08 8×8 Family","ZBL-08 / Type 08",["08式","Type 08"],"vehicle","apc_wheeled","解放軍","依型號","3＋載員","約 15–25 t","約 8 m","依武器","—","步兵班","輪式裝甲","8×8 高速","依型號","模組化輪式車族。","Modular 8x8 family.",["輪式","8x8"],"AFV/APC","Type_08_vehicle"),
  ("zbd-08","08 式輪式步戰車","ZBD-08 Wheeled IFV","ZBD-08",["08步戰"],"vehicle","ifv","解放軍","30mm","3＋7","約 21 t","—","—","—","載員","輪式","8×8","—","08 族步戰型。","Wheeled IFV on Type 08.",["輪式","IFV"],"AFV/IFV","Type_08_vehicle"),
  ("zsl-92","92 式輪式裝甲車","ZSL-92 APC","ZSL-92 / Type 92",["92式","WZ551"],"vehicle","apc_wheeled","解放軍","25mm／12.7mm","3＋9","約 15 t","—","—","—","載員","輪式","6×6","—","舊式輪式裝甲。","Legacy 6x6 APC.",["輪式","APC"],"AFV/APC","Type_92_AFV"),
  ("ztl-11","11 式輪式突擊車","ZTL-11 Assault Gun","ZTL-11",["11式","ZTL11"],"vehicle","assault_gun","解放軍","105mm","4","約 20+ t","—","約 2+ km","—","—","輪式","8×8","射控","105mm 輪式突擊車。","Wheeled 105mm fire support.",["突擊車","105mm"],"AFV","Type_08_vehicle"),
  ("pll-09","PLL-09 輪式自走砲","PLL-09 SPH","PLL-09",["09式122"],"vehicle","sph","解放軍","122mm","5","約 16.5 t","—","18–22 km","6–8 rpm","—","輕防護","8×8","數位射控","122mm 輪式自走砲。","122mm wheeled SPH.",["自走砲","122mm"],"Artillery","Type_08_vehicle"),
  ("plz-05","05 式 155mm 自走榴彈砲","PLZ-05 SPH","PLZ-05",["05式","PLZ05"],"vehicle","sph","解放軍陸軍","155mm/52","5","約 35 t","—","40–50 km","8–10 rpm","—","裝甲","履帶","自動化射控","主力 155mm 自走砲。","Primary 155mm tracked SPH.",["自走砲","155mm"],"Artillery","PLZ-05"),
  ("plz-07","07 式 122mm 自走榴彈砲","PLZ-07 SPH","PLZ-07",["07式122"],"vehicle","sph","解放軍","122mm","5","約 24 t","—","約 18–22 km","—","—","裝甲","履帶","—","122mm 履帶自走砲。","122mm tracked SPH.",["自走砲","122mm"],"Artillery","PLZ-07"),
  ("pcl-181","PCL-181 車載加榴砲","PCL-181 Truck Howitzer","PCL-181",["181","車載155"],"vehicle","truck_howitzer","解放軍","155mm","6","約 25 t","—","約 40+ km","—","—","駕駛艙防護","6×6 卡車","數位射控","高機動 155mm 車載砲。","Mobile truck-mounted 155mm.",["火砲","155mm","車載"],"Artillery","PCL-181"),
  ("pcl-171","PCL-171 突擊車","PCL-171 Assault Vehicle","PCL-171",["171"],"vehicle","light_vehicle","解放軍","機槍／反戰車等","—","—","—","—","—","—","輕防護","高機動輕車","—","可空運輕型突擊車。","Air-transportable light assault vehicle.",["輕型車輛"],"Light Vehicles",""),
  ("pll-05","PLL-05 自行迫擊砲","PLL-05 SPM","PLL-05",["05式120迫"],"vehicle","mortar_sp","解放軍","120mm","4","約 16.5 t","—","約 8+ km","—","—","輪式","6×6","射控","120mm 自行迫擊砲。","Wheeled 120mm SPM.",["迫擊砲","120mm"],"Artillery","PLL-05"),
  ("phl-03","PHL-03 多管火箭","PHL-03 MLRS","PHL-03",["03式火箭砲","A-100"],"vehicle","mlrs","解放軍","300mm","—","—","—","約 70–130 km","齊射","12 管","卡車","輪式","射控","300mm 遠程火箭砲。","300mm long-range MLRS.",["火箭砲","MLRS"],"Artillery","PHL-03"),
  ("phl-16","PHL-16 多管火箭","PHL-16 / PCL-191","PHL-16",["16式","PCL-191"],"vehicle","mlrs","解放軍","370／750mm 模組","—","—","—","70–300+ km","齊射","模組箱","卡車","輪式","射控","模組化遠程火箭／飛彈。","Modular long-range rocket/missile system.",["火箭砲","遠程"],"Artillery","PHL-16"),
  ("phz-11","PHZ-11 多管火箭","PHZ-11 MLRS","PHZ-11",["11式火箭"],"vehicle","mlrs","解放軍","122mm","—","—","—","20–40 km","齊射","多聯裝","履帶","履帶","射控","122mm 履帶火箭砲。","Tracked 122mm MLRS.",["火箭砲"],"Artillery",""),
  ("phz-89","PHZ-89 多管火箭","Type 89 MLRS","PHZ-89",["89式火箭"],"vehicle","mlrs","解放軍","122mm","—","—","—","約 20–40 km","齊射","40 管","履帶","履帶","—","舊式 122mm 火箭砲。","Legacy 122mm MLRS.",["火箭砲"],"Artillery","Type_89_MLRS"),
  ("pgz-09","09 式自行高砲","PGZ-09 SPAAG","PGZ-09",["09式高砲","35mm雙管"],"vehicle","spaag","解放軍","35mm 雙管","3","約 35 t","—","約 4 km","高射速","—","裝甲","履帶","搜索追蹤雷達","點防空自行高砲。","35mm twin SPAAG.",["高砲","防空"],"Air Defense","PGZ-09"),
  ("pgz-95","95 式自行高砲","PGZ-95 SPAAG","PGZ-95",["95式高砲"],"vehicle","spaag","解放軍","25mm 四管","3","約 22 t","—","約 2.5 km","—","—","裝甲","履帶","雷達","舊式彈砲結合防空。","Legacy SPAAG/missile hybrid base.",["高砲","防空"],"Air Defense","Type_95_SPAAG"),
  ("hq-17","紅旗-17 防空飛彈","HQ-17 SAM","HQ-17",["紅旗17"],"vehicle","sam","解放軍","地對空飛彈","—","—","—","約 15 km","—","多聯裝","履帶／輪式","伴隨部隊","搜索追蹤雷達","近程野戰防空。","Short-range mobile SAM.",["防空","SAM"],"Air Defense","HQ-17"),
  ("hq-17a","紅旗-17A 防空飛彈","HQ-17A SAM","HQ-17A",["紅旗17A"],"vehicle","sam","解放軍","地對空飛彈","—","—","—","約 15+ km","—","多聯裝","輪式改進","伴隨部隊","雷達","HQ-17 改進型。","Improved HQ-17.",["防空","SAM"],"Air Defense","HQ-17"),
  ("hq-16","紅旗-16 中程防空飛彈","HQ-16 SAM","HQ-16",["紅旗16","海紅旗16"],"equipment","sam","陸／海軍","地對空／艦對空","—","—","—","40–70 km","—","垂發／輪式","—","陸基／艦載","雷達導引","中程防空；艦載 HHQ-16。","Medium-range SAM; naval HHQ-16.",["防空","中程"],"Air Defense","HQ-16"),
  ("hq-9","紅旗-9 遠程防空飛彈","HQ-9 SAM","HQ-9",["紅旗9"],"equipment","sam","空／海／陸軍","地對空飛彈","連級","—","—","125–300 km","—","垂直／斜架","—","輪式／陣地","相控陣","遠程區域防空骨幹。","Long-range area SAM.",["防空","遠程"],"Air Defense","HQ-9"),
  ("hq-9b","紅旗-9B 遠程防空飛彈","HQ-9B SAM","HQ-9B",["紅旗9B"],"equipment","sam","解放軍","地對空飛彈","連級","—","—","約 250–300 km","—","垂直","—","輪式","相控陣","HQ-9 增程型。","Extended-range HQ-9.",["防空","遠程"],"Air Defense","HQ-9"),
  ("hq-22","紅旗-22 中遠程防空飛彈","HQ-22 SAM","HQ-22",["紅旗22"],"equipment","sam","解放軍","地對空飛彈","連級","—","—","100–170 km","—","傾斜發射","—","輪式","相控陣","中遠程防空。","Medium-long range SAM.",["防空","SAM"],"Air Defense","HQ-22"),
  ("hq-7","紅旗-7 近程防空飛彈","HQ-7 SAM","HQ-7",["紅旗7","海紅旗7"],"equipment","sam","解放軍","地對空飛彈","—","—","—","約 8–15 km","—","多聯裝","—","陸基／艦載","雷達","近程點防空。","Short-range point defense SAM.",["防空","近程"],"Air Defense","HQ-7"),
  ("ld-2000","LD-2000 近防系統","LD-2000 CIWS/SPAAG","LD-2000",["陸盾2000"],"vehicle","spaag","解放軍","30mm 轉管","—","—","—","約 3 km","極高射速","—","卡車","輪式","光電／雷達","陸基近防火砲。","Land-based CIWS-type gun.",["防空","近防"],"Air Defense","LD-2000"),
  ("mengshi","猛士 高機動戰術車輛","Dongfeng Mengshi","EQ2050 / Mengshi",["猛士","EQ2050"],"vehicle","light_vehicle","解放軍","依改裝","—","約 3.5–5 t","—","—","—","—","輕防護型","4×4","—","輕型戰術車輛族。","HMMWV-class tactical vehicle.",["輕型車輛","4x4"],"Light Vehicles","Dongfeng_EQ2050"),
  ("cslc-cs","CS/VP 全地形車系列","CS/VP ATV Series","CS/VP",["全地形車"],"vehicle","light_vehicle","解放軍","依改裝","—","—","—","—","—","—","—","全地形","—","輕型全地形載具。","Light ATV family.",["全地形"],"Light Vehicles",""),

  # ===== 航空 戰鬥機／轟炸機 =====
  ("j-20","殲-20 戰鬥機","Chengdu J-20","J-20",["殲20","威龍"],"vehicle","aircraft_fighter","空軍","內置彈艙彈藥","1","空重約 17+ t","約 21.2 m","作戰半徑 1000+ km","—","內置彈艙","—","第五代戰機","AESA／光電／電戰","匿蹤制空戰鬥機。","5th-gen stealth fighter.",["戰鬥機","匿蹤"],"Aircraft","Chengdu_J-20"),
  ("j-20s","殲-20S 雙座戰鬥機","J-20S Twin-seat","J-20S",["殲20S"],"vehicle","aircraft_fighter","空軍","—","2","—","—","—","—","內置彈艙","—","第五代","先進航電","雙座型殲-20。","Two-seat J-20 variant.",["戰鬥機","匿蹤"],"Aircraft","Chengdu_J-20"),
  ("j-35a","殲-35A 戰鬥機","Shenyang J-35A","J-35A",["殲35A","FC-31"],"vehicle","aircraft_fighter","空軍","—","1","—","—","—","—","—","—","第五代中型","AESA","中型匿蹤多用途戰機。","Medium stealth multirole.",["戰鬥機","匿蹤"],"Aircraft","Shenyang_J-35"),
  ("j-35","殲-35 艦載戰鬥機","Shenyang J-35","J-35",["殲35","艦載"],"vehicle","aircraft_fighter","海軍航空兵","—","1","—","—","—","—","—","—","艦載第五代","AESA","航母艦載匿蹤戰機。","Carrier-based stealth fighter.",["戰鬥機","艦載"],"Aircraft","Shenyang_J-35"),
  ("j-16","殲-16 多用途戰鬥機","Shenyang J-16","J-16",["殲16"],"vehicle","aircraft_fighter","空軍","多用途彈藥","2","—","約 22 m","遠程","—","多掛點","—","4.5 代重型","AESA","重型多用途戰機。","Heavy multirole fighter.",["戰鬥機","多用途"],"Aircraft","Shenyang_J-16"),
  ("j-16d","殲-16D 電子戰機","J-16D EW","J-16D",["殲16D"],"vehicle","aircraft_fighter","空軍","電戰吊艙","2","—","—","—","—","—","—","電子戰","電戰套件","電子戰專用型。","Electronic warfare variant.",["電子戰","戰鬥機"],"Aircraft","Shenyang_J-16"),
  ("j-10c","殲-10C 戰鬥機","Chengdu J-10C","J-10C",["殲10C"],"vehicle","aircraft_fighter","空軍","空對空／對地","1","—","約 16.9 m","—","—","多掛點","—","中輕型多用途","AESA","殲-10 最新量產型。","Latest J-10 production.",["戰鬥機"],"Aircraft","Chengdu_J-10"),
  ("j-10b","殲-10B 戰鬥機","Chengdu J-10B","J-10B",["殲10B"],"vehicle","aircraft_fighter","空軍","—","1","—","—","—","—","—","—","多用途","DSI 進氣","殲-10 改進型。","J-10B intermediate.",["戰鬥機"],"Aircraft","Chengdu_J-10"),
  ("j-10a","殲-10A 戰鬥機","Chengdu J-10A","J-10A",["殲10A"],"vehicle","aircraft_fighter","空軍","—","1","—","約 16.4 m","—","—","—","—","多用途","—","殲-10 早期量產型。","Early J-10 variant.",["戰鬥機"],"Aircraft","Chengdu_J-10"),
  ("j-11b","殲-11B 戰鬥機","Shenyang J-11B","J-11B",["殲11B"],"vehicle","aircraft_fighter","空軍／海航","—","1","—","約 22 m","—","—","多掛點","—","制空","國產航電","蘇-27 系國產改進。","Indigenous Su-27 derivative.",["戰鬥機","制空"],"Aircraft","Shenyang_J-11"),
  ("j-11bg","殲-11BG 戰鬥機","J-11BG","J-11BG",["殲11BG"],"vehicle","aircraft_fighter","空軍","—","1","—","—","—","—","—","—","制空","AESA 升級","J-11B 航電升級型。","Upgraded J-11B.",["戰鬥機"],"Aircraft","Shenyang_J-11"),
  ("j-15","殲-15 艦載戰鬥機","Shenyang J-15","J-15",["飛鯊","殲15"],"vehicle","aircraft_fighter","海軍航空兵","—","1","—","約 22 m","—","—","多掛點","—","滑躍／彈射","—","航母艦載戰機。","Carrier-borne fighter.",["戰鬥機","艦載"],"Aircraft","Shenyang_J-15"),
  ("j-15t","殲-15T 彈射艦載機","J-15T","J-15T",["殲15T"],"vehicle","aircraft_fighter","海軍航空兵","—","1","—","—","—","—","—","—","彈射適改装","—","電磁彈射適改装型。","CATOBAR-capable J-15.",["戰鬥機","艦載"],"Aircraft","Shenyang_J-15"),
  ("su-30mkk","蘇-30MKK 戰鬥機","Su-30MKK","Su-30MKK",["蘇30"],"vehicle","aircraft_fighter","空軍","—","2","—","約 22 m","—","—","多掛點","—","多用途","—","俄製重型多用途戰機。","Russian multirole fighter.",["戰鬥機","俄製"],"Aircraft","Sukhoi_Su-30"),
  ("su-35","蘇-35 戰鬥機","Su-35S","Su-35S",["蘇35"],"vehicle","aircraft_fighter","空軍","—","1","—","約 22 m","—","—","多掛點","—","制空／多用途","Irbis-E","俄製超機動戰機。","Russian supermaneuverable fighter.",["戰鬥機","俄製"],"Aircraft","Sukhoi_Su-35"),
  ("su-27ubk","蘇-27UBK 教練／戰鬥機","Su-27UBK","Su-27UBK",["蘇27雙座"],"vehicle","aircraft_fighter","空軍","—","2","—","—","—","—","—","—","轉換訓練","—","蘇-27 雙座型。","Su-27 two-seat trainer/fighter.",["戰鬥機","教練"],"Aircraft","Sukhoi_Su-27"),
  ("jh-7a","殲轟-7A 戰鬥轟炸機","Xian JH-7A","JH-7A",["飛豹","JH7A"],"vehicle","aircraft_strike","海／空軍","反艦／對地","2","—","約 22.2 m","—","—","重載掛架","—","戰鬥轟炸機","對海對地火控","反艦與對地打擊。","Fighter-bomber anti-ship/strike.",["戰鬥轟炸機","反艦"],"Aircraft","Xian_JH-7"),
  ("h-6k","轟-6K 轟炸機","Xian H-6K","H-6K",["轟6K"],"vehicle","aircraft_bomber","空軍","巡航飛彈","—","—","約 34.9 m","遠程","—","外掛巡航飛彈","—","戰役／戰略轟炸機","現代化航電","可掛長劍巡航飛彈。","Cruise-missile bomber.",["轟炸機","巡航飛彈"],"Aircraft","Xian_H-6"),
  ("h-6n","轟-6N 轟炸機","Xian H-6N","H-6N",["轟6N"],"vehicle","aircraft_bomber","空軍","空射彈道／巡航","—","—","—","遠程＋空中加油","—","機腹／掛點","—","空中加油適改装","—","可空中加油之轟-6。","H-6 with aerial refueling probe.",["轟炸機"],"Aircraft","Xian_H-6"),
  ("h-6j","轟-6J 海軍轟炸機","Xian H-6J","H-6J",["轟6J"],"vehicle","aircraft_bomber","海軍航空兵","反艦飛彈","—","—","—","—","—","多枚反艦飛彈","—","海航轟炸機","—","海軍遠程反艦打擊。","PLANAF anti-ship bomber.",["轟炸機","反艦"],"Aircraft","Xian_H-6"),
  ("j-8f","殲-8F 攔截機","Shenyang J-8F","J-8F",["殲8"],"vehicle","aircraft_fighter","空軍（汰換中）","—","1","—","約 21 m","—","—","—","—","攔截機","—","舊式攔截機，逐步退役。","Legacy interceptor phasing out.",["戰鬥機","舊式"],"Aircraft","Shenyang_J-8"),

  # ===== 特種機／運輸／直升機 =====
  ("kj-500","空警-500 預警機","Shaanxi KJ-500","KJ-500",["空警500"],"vehicle","aircraft_aew","空軍","—","—","—","—","區域空情","—","—","—","預警指揮","固定陣列雷達","主力空中預警機。","Primary AEW&C.",["預警機","C4ISR"],"Aircraft","Shaanxi_KJ-500"),
  ("kj-200","空警-200 預警機","Shaanxi KJ-200","KJ-200",["空警200","平衡木"],"vehicle","aircraft_aew","空軍／海航","—","—","—","—","—","—","—","—","預警","平衡木雷達","中型預警機。","Medium AEW&C.",["預警機"],"Aircraft","Shaanxi_KJ-200"),
  ("kj-2000","空警-2000 預警機","KJ-2000","KJ-2000",["空警2000"],"vehicle","aircraft_aew","空軍","—","—","—","—","—","—","—","—","大型預警","圓盤雷達","伊爾-76 平台預警機。","Il-76 based AEW&C.",["預警機"],"Aircraft","KJ-2000"),
  ("y-20","運-20 運輸機","Xian Y-20","Y-20",["運20","鯤鵬"],"vehicle","aircraft_transport","空軍","—","—","MTOW 200+ t 級","約 47 m","戰略投送","—","重裝備／部隊","—","戰略運輸","—","主力戰略運輸機。","Strategic airlifter.",["運輸機","投送"],"Aircraft","Xian_Y-20"),
  ("yy-20","運油-20 加油機","YY-20 Tanker","YY-20A",["運油20"],"vehicle","aircraft_transport","空軍","—","—","—","—","空中加油","—","—","—","加油機","—","Y-20 加油型。","Y-20 tanker variant.",["加油機"],"Aircraft","Xian_Y-20"),
  ("y-9","運-9 運輸機","Shaanxi Y-9","Y-9",["運9"],"vehicle","aircraft_transport","空軍／海航","—","—","—","約 36 m","戰術投送","—","部隊／物資","—","中型運輸","—","中型戰術運輸機。","Medium tactical transport.",["運輸機"],"Aircraft","Shaanxi_Y-9"),
  ("y-8","運-8 運輸機","Shaanxi Y-8","Y-8",["運8"],"vehicle","aircraft_transport","空軍／海航","—","—","—","—","—","—","—","—","中型運輸","—","安-12 系運輸／特種平台。","An-12 class transport/special mission.",["運輸機"],"Aircraft","Shaanxi_Y-8"),
  ("il-76","伊爾-76 運輸機","Ilyushin Il-76","Il-76",["伊爾76"],"vehicle","aircraft_transport","空軍","—","—","—","約 46.6 m","戰略／戰術","—","重載","—","運輸","—","俄製戰略運輸機。","Russian strategic airlifter.",["運輸機","俄製"],"Aircraft","Ilyushin_Il-76"),
  ("kq-200","空潛-200 反潛機","Shaanxi KQ-200","KQ-200",["空潛200","Y-8Q"],"vehicle","aircraft_patrol","海軍航空兵","魚雷／深彈","—","—","—","反潛巡邏","—","—","—","反潛巡邏","磁探／聲納浮標","固定翼反潛巡邏機。","Fixed-wing ASW aircraft.",["反潛","巡邏機"],"Aircraft","Shaanxi_KQ-200"),
  ("z-20","直-20 通用直升機","Harbin Z-20","Z-20",["直20"],"vehicle","helicopter","陸／海／空軍","依任務","2＋載員","—","—","—","—","約一班","—","中型通用","依型號","中型通用直升機。","Medium utility helicopter.",["直升機","通用"],"Aircraft","Harbin_Z-20"),
  ("z-10","直-10 武裝直升機","CAIC Z-10","Z-10",["直10","霹靂火"],"vehicle","helicopter_attack","陸軍航空兵","機砲＋反戰車飛彈","2","—","—","—","—","多掛點","座艙防護","攻擊直升機","光電瞄準","專用攻擊直升機。","Dedicated attack helicopter.",["攻擊直升機"],"Aircraft","CAIC_Z-10"),
  ("z-19","直-19 偵察攻擊直升機","Harbin Z-19","Z-19",["直19"],"vehicle","helicopter_attack","陸軍航空兵","機槍／飛彈","2","—","—","—","—","輕掛載","—","武裝偵察","光電／毫米波","輕型武裝偵察直升機。","Light scout/attack helicopter.",["直升機","偵察"],"Aircraft","Harbin_Z-19"),
  ("z-9","直-9 通用直升機","Harbin Z-9","Z-9",["直9"],"vehicle","helicopter","陸／海／空軍","依型號","2＋載員","—","—","—","—","—","—","輕中型","—","海豚系國產通用直升機。","Licensed Dauphin-derived utility.",["直升機"],"Aircraft","Harbin_Z-9"),
  ("z-8","直-8 運輸直升機","Changhe Z-8","Z-8",["直8"],"vehicle","helicopter","陸／海／空軍","—","—","—","—","—","—","部隊／物資","—","重型運輸","—","超黃蜂系運輸直升機。","Super Frelon-derived transport helo.",["直升機","運輸"],"Aircraft","Changhe_Z-8"),
  ("z-18","直-18 運輸／反潛直升機","Changhe Z-18","Z-18",["直18"],"vehicle","helicopter","海軍／陸軍","—","—","—","—","—","—","—","—","中重型","—","直-8 改進運輸／艦載。","Improved Z-8 family.",["直升機"],"Aircraft","Changhe_Z-18"),
  ("mi-17","米-17 運輸直升機","Mil Mi-17","Mi-17/171",["米17","米171"],"vehicle","helicopter","陸軍航空兵","—","—","—","—","—","—","部隊","—","中型運輸","—","俄製中型運輸直升機。","Russian medium transport helo.",["直升機","俄製"],"Aircraft","Mil_Mi-17"),
  ("ka-28","卡-28 反潛直升機","Kamov Ka-28","Ka-28",["卡28"],"vehicle","helicopter","海軍","魚雷／深彈","—","—","—","—","—","—","—","艦載反潛","—","艦載反潛直升機。","Shipborne ASW helicopter.",["直升機","反潛"],"Aircraft","Kamov_Ka-27"),

  # ===== 無人機 =====
  ("ch-4","彩虹-4 無人機","CASC CH-4","CH-4",["彩虹4"],"vehicle","uav","解放軍／出口","精確彈藥","地面站","—","—","資料鏈數百 km","—","多掛點","—","MALE","光電／SAR","察打一體無人機。","MALE armed UAV.",["無人機","UAV"],"UAV","CASC_CH-4"),
  ("ch-5","彩虹-5 無人機","CASC CH-5","CH-5",["彩虹5"],"vehicle","uav","解放軍／出口","重載彈藥","地面站","—","—","長航時","—","大載重","—","大型 MALE","多感測","大型察打無人機。","Larger armed UAV.",["無人機"],"UAV","CASC_CH-5"),
  ("wing-loong-2","翼龍-2 無人機","Wing Loong II","Wing Loong II",["翼龍2","GJ-2"],"vehicle","uav","解放軍／出口","精確彈藥","地面站","—","—","長航時","—","多掛點","—","MALE","光電","察打一體。","MALE UCAV.",["無人機","翼龍"],"UAV","CAIG_Wing_Loong_II"),
  ("wing-loong-1","翼龍-1 無人機","Wing Loong I","Wing Loong I",["翼龍1"],"vehicle","uav","解放軍／出口","輕彈藥","地面站","—","—","—","—","—","—","MALE","光電","中型察打無人機。","Medium MALE UAV.",["無人機"],"UAV","CAIG_Wing_Loong"),
  ("tb-001","雙尾蠍 TB-001","TB-001 Twin-Tailed Scorpion","TB-001",["雙尾蠍"],"vehicle","uav","解放軍／出口","精確彈藥","地面站","—","—","長航時","—","雙尾掛載","—","MALE","光電","雙尾樑偵打無人機。","Twin-boom MALE UAV.",["無人機"],"UAV","TB-001"),
  ("gj-11","攻擊-11 無人攻擊機","GJ-11 Sharp Sword","GJ-11",["利劍","攻擊11"],"vehicle","uav","解放軍","內置彈艙","遙控／自主","—","—","—","—","內置彈艙","—","飛翼匿蹤 UCAV","—","匿蹤無人攻擊機。","Stealth flying-wing UCAV.",["無人機","匿蹤"],"UAV","GJ-11"),
  ("wz-7","無偵-7 高空偵察無人機","WZ-7 Soaring Dragon","WZ-7",["無偵7","翔龍"],"vehicle","uav","解放軍","—","地面站","—","—","高空長航時","—","—","—","HALE","SAR／光電","高空偵察無人機。","HALE recon UAV.",["無人機","偵察"],"UAV","WZ-7"),
  ("wz-8","無偵-8 高超音速偵察無人機","WZ-8","WZ-8",["無偵8"],"vehicle","uav","解放軍","—","—","—","—","高速","—","—","—","高超／高速偵察","—","高速偵察無人機（公開展示）。","High-speed recon UAV (public display).",["無人機","高速"],"UAV","WZ-8"),
  ("bzk-005","BZK-005 偵察無人機","BZK-005","BZK-005",["BZK005"],"vehicle","uav","解放軍","—","地面站","—","—","長航時","—","—","—","MALE 偵察","光電","中高空偵察無人機。","MALE reconnaissance UAV.",["無人機","偵察"],"UAV","BZK-005"),
  ("asn-209","ASN-209 偵察無人機","ASN-209","ASN-209",["ASN209"],"vehicle","uav","解放軍","—","地面站","—","—","—","—","—","—","戰術偵察","—","戰術級偵察無人機。","Tactical recon UAV.",["無人機"],"UAV",""),

  # ===== 飛彈 =====
  ("df-21d","東風-21D 反艦彈道飛彈","DF-21D ASBM","DF-21D",["東風21D","ASBM"],"weapon","ballistic","火箭軍","中程彈道","—","—","—","約 1500+ km","—","機動發射車","—","公路機動","末端導引","反艦彈道飛彈。","Anti-ship ballistic missile.",["彈道飛彈","反艦"],"Missiles","DF-21"),
  ("df-21a","東風-21A 中程彈道飛彈","DF-21A MRBM","DF-21A",["東風21"],"weapon","ballistic","火箭軍","中程彈道","—","—","—","約 1750–2150 km","—","機動發射車","—","公路機動","—","中程彈道飛彈。","MRBM.",["彈道飛彈"],"Missiles","DF-21"),
  ("df-26","東風-26 中程彈道飛彈","DF-26 IRBM","DF-26",["東風26"],"weapon","ballistic","火箭軍","中程彈道","—","—","—","約 3000–4000 km","—","機動發射車","—","公路機動","對陸／反艦（公開）","中程彈道飛彈。","IRBM dual-capable claims.",["彈道飛彈","中程"],"Missiles","DF-26"),
  ("df-17","東風-17 高超音速飛彈","DF-17 HGV","DF-17",["東風17"],"weapon","ballistic","火箭軍","高超音速滑翔","—","—","—","約 1800–2500 km","—","機動發射車","—","公路機動","滑翔載具","高超音速滑翔彈道飛彈。","Hypersonic glide vehicle system.",["高超音速","彈道飛彈"],"Missiles","DF-17"),
  ("df-15","東風-15 近程彈道飛彈","DF-15 SRBM","DF-15",["東風15","M-9"],"weapon","ballistic","火箭軍","近程彈道","—","—","—","約 600–900 km","—","機動發射車","—","公路機動","—","近程彈道飛彈。","SRBM.",["彈道飛彈","近程"],"Missiles","DF-15"),
  ("df-16","東風-16 近程彈道飛彈","DF-16 SRBM","DF-16",["東風16"],"weapon","ballistic","火箭軍","近程彈道","—","—","—","約 800–1000 km","—","機動發射車","—","公路機動","—","近程彈道飛彈。","SRBM.",["彈道飛彈"],"Missiles","DF-16"),
  ("df-31ag","東風-31AG 洲際彈道飛彈","DF-31AG ICBM","DF-31AG",["東風31AG"],"weapon","ballistic","火箭軍","洲際彈道","—","—","—","約 11000+ km","—","機動發射車","—","公路機動","—","公路機動洲際彈道飛彈。","Road-mobile ICBM.",["ICBM","洲際"],"Missiles","DF-31"),
  ("df-41","東風-41 洲際彈道飛彈","DF-41 ICBM","DF-41",["東風41"],"weapon","ballistic","火箭軍","洲際彈道","—","—","—","約 12000–15000 km","—","機動發射車","—","公路機動","—","新型公路機動 ICBM。","Road-mobile ICBM.",["ICBM","洲際"],"Missiles","DF-41"),
  ("jl-2","巨浪-2 潛射彈道飛彈","JL-2 SLBM","JL-2",["巨浪2"],"weapon","ballistic","火箭軍／海軍","潛射彈道","—","—","—","約 7000+ km","—","094 型潛艦","—","潛射","—","潛射彈道飛彈。","SLBM.",["SLBM","核潛"],"Missiles","JL-2"),
  ("jl-3","巨浪-3 潛射彈道飛彈","JL-3 SLBM","JL-3",["巨浪3"],"weapon","ballistic","火箭軍／海軍","潛射彈道","—","—","—","約 10000+ km","—","094A／096","—","潛射","—","新型潛射彈道飛彈。","New SLBM.",["SLBM"],"Missiles","JL-3"),
  ("cj-10","長劍-10 巡航飛彈","CJ-10 / DH-10","CJ-10",["長劍10","DH-10"],"weapon","cruise","火箭軍／空軍","陸攻巡航","—","—","—","約 1500+ km","—","陸基／空射","—","亞音速巡航","複合導航","對陸巡航飛彈。","Land-attack cruise missile.",["巡航飛彈"],"Missiles","CJ-10"),
  ("cj-20","長劍-20 空射巡航飛彈","CJ-20 ALCM","CJ-20",["長劍20"],"weapon","cruise","空軍","空射巡航","—","—","—","約 1500+ km","—","轟-6K 等","—","亞音速","—","空射對陸巡航飛彈。","Air-launched cruise missile.",["巡航飛彈","空射"],"Missiles","CJ-10"),
  ("yj-12","鷹擊-12 反艦飛彈","YJ-12 AShM","YJ-12",["鷹擊12"],"weapon","asm","海／空軍","超音速反艦","—","—","—","約 300–400+ km","—","空射／岸射","—","超音速","主動雷達","超音速反艦飛彈。","Supersonic anti-ship missile.",["反艦","超音速"],"Missiles","YJ-12"),
  ("yj-18","鷹擊-18 反艦飛彈","YJ-18 AShM","YJ-18",["鷹擊18"],"weapon","asm","海軍","反艦巡航","—","—","—","約 220–540 km","—","垂發／潛射","—","亞音速＋末端超音速","複合導引","艦／潛射反艦飛彈。","AShM with supersonic terminal dash.",["反艦","垂發"],"Missiles","YJ-18"),
  ("yj-83","鷹擊-83 反艦飛彈","YJ-83 AShM","YJ-83",["鷹擊83","C-802"],"weapon","asm","海軍／海航","亞音速反艦","—","—","—","約 180 km","—","艦射／空射","—","亞音速掠海","主動雷達","主力反艦飛彈族。","Mainstay anti-ship family.",["反艦"],"Missiles","YJ-83"),
  ("yj-62","鷹擊-62 反艦飛彈","YJ-62 AShM","YJ-62",["鷹擊62"],"weapon","asm","海軍／岸防","亞音速反艦","—","—","—","約 280–400 km","—","艦／岸","—","亞音速","—","中程反艦飛彈。","Medium-range AShM.",["反艦","岸防"],"Missiles","YJ-62"),
  ("yj-21","鷹擊-21 高超音速反艦飛彈","YJ-21","YJ-21",["鷹擊21"],"weapon","asm","海軍","高超音速","—","—","—","遠程（公開展示）","—","艦載垂發","—","高超音速","—","艦載高超音速反艦／對陸（公開閱兵）。","Hypersonic ship-launched missile (public).",["反艦","高超音速"],"Missiles",""),
  ("pl-15","霹靂-15 空對空飛彈","PL-15 AAM","PL-15",["霹靂15"],"weapon","aam","空軍／海航","遠程空對空","—","—","—","約 200+ km","—","機載","—","主動雷達","主動雷達尋標","遠程空對空飛彈。","Long-range active radar AAM.",["空對空","BVR"],"Missiles","PL-15"),
  ("pl-10","霹靂-10 空對空飛彈","PL-10 AAM","PL-10",["霹靂10"],"weapon","aam","空軍／海航","近距空對空","—","—","—","約 20 km","—","機載","—","高離軸角","紅外成像","近距格鬥飛彈。","HOBS IR dogfight missile.",["空對空","近距"],"Missiles","PL-10"),
  ("pl-12","霹靂-12 空對空飛彈","PL-12 AAM","PL-12",["霹靂12","SD-10"],"weapon","aam","空軍","中遠程空對空","—","—","—","約 70–100 km","—","機載","—","主動雷達","—","中遠程空對空飛彈。","Medium-long range AAM.",["空對空"],"Missiles","PL-12"),
  ("pl-17","霹靂-17 超遠程空對空飛彈","PL-17 AAM","PL-17",["霹靂17"],"weapon","aam","空軍","超遠程空對空","—","—","—","超遠程（公開估計）","—","機載","—","主動雷達","—","超遠程空對空飛彈。","Very-long-range AAM.",["空對空","超遠程"],"Missiles",""),

  # ===== 海軍艦艇 =====
  ("type-003","003 型航空母艦（福建艦）","Type 003 Fujian","Type 003",["福建艦","003"],"vehicle","warship","海軍","艦載機聯隊","—","滿載約 80,000+ t","約 316 m","遠洋","—","電磁彈射","—","常規動力航母","綜合艦島","電磁彈射航空母艦。","CATOBAR carrier with EMALS.",["航母","軍艦"],"Naval","Chinese_aircraft_carrier_Fujian"),
  ("type-002","002 型航空母艦（山東艦）","Type 002 Shandong","Type 002",["山東艦","002"],"vehicle","warship","海軍","艦載機","—","約 60,000–70,000 t","約 305 m","遠洋","—","滑躍起飛","—","常規動力航母","—","國產滑躍航母。","Ski-jump carrier.",["航母"],"Naval","Chinese_aircraft_carrier_Shandong"),
  ("type-001","001 型航空母艦（遼寧艦）","Type 001 Liaoning","Type 001",["遼寧艦","001"],"vehicle","warship","海軍","艦載機","—","約 60,000 t","約 304 m","遠洋","—","滑躍起飛","—","常規動力航母","—","改建航母。","Refitted carrier.",["航母"],"Naval","Chinese_aircraft_carrier_Liaoning"),
  ("type-055","055 型驅逐艦","Type 055 Destroyer","Type 055",["055","南昌艦級"],"vehicle","warship","海軍","112 垂發＋130mm","約 300+","約 12–13,000 t","約 180 m","遠洋","—","防空反艦對陸","—","燃氣輪機","雙波段相控陣","大型多用途驅逐艦。","Large multi-mission destroyer.",["驅逐艦","軍艦"],"Naval","Type_055_destroyer"),
  ("type-052d","052D 型驅逐艦","Type 052D Destroyer","Type 052D",["052D","昆明艦級"],"vehicle","warship","海軍","64 垂發＋130mm","約 280","約 7,500 t","約 157 m","遠洋","—","防空反艦","—","導彈驅逐艦","相控陣","主力導彈驅逐艦。","Mainstay AEGIS-like destroyer.",["驅逐艦"],"Naval","Type_052D_destroyer"),
  ("type-052c","052C 型驅逐艦","Type 052C Destroyer","Type 052C",["052C","蘭州艦級"],"vehicle","warship","海軍","48 垂發＋100mm","—","約 7,000 t","約 155 m","遠洋","—","區域防空","—","導彈驅逐艦","相控陣","早期相控陣驅逐艦。","Early AESA destroyer class.",["驅逐艦"],"Naval","Type_052C_destroyer"),
  ("type-054a","054A 型護衛艦","Type 054A Frigate","Type 054A",["054A"],"vehicle","warship","海軍","32 垂發＋76mm","約 165","約 4,000 t","約 134 m","遠海","—","防空反潛","—","護衛艦","拖曳聲納","主力多用途護衛艦。","Workhorse multirole frigate.",["護衛艦","反潛"],"Naval","Type_054A_frigate"),
  ("type-054b","054B 型護衛艦","Type 054B Frigate","Type 054B",["054B"],"vehicle","warship","海軍","垂發＋艦砲","—","約 5,000+ t 級","—","—","—","防空反潛","—","新一代護衛","—","新型護衛艦。","Next-gen frigate.",["護衛艦"],"Naval","Type_054B_frigate"),
  ("type-056a","056A 型輕型護衛艦","Type 056A Corvette","Type 056A",["056A","江島級"],"vehicle","warship","海軍","反艦＋防空＋反潛","約 60","約 1,500 t","約 90 m","近海","—","反潛加強","—","輕型護衛","拖曳聲納","近海反潛輕護衛。","Littoral ASW corvette.",["輕護衛","反潛"],"Naval","Type_056_corvette"),
  ("type-022","022 型飛彈快艇","Type 022 Missile Boat","Type 022",["022","侯北級"],"vehicle","warship","海軍","YJ-83 等","—","約 220 t","約 43 m","近海","—","反艦飛彈","—","雙體快艇","—","隱身飛彈快艇。","Catamaran missile FAC.",["快艇","反艦"],"Naval","Type_022_missile_boat"),
  ("type-075","075 型兩棲攻擊艦","Type 075 LHD","Type 075",["075","海南艦級"],"vehicle","warship","海軍","近防／點防空","—","約 35–40,000 t","約 232 m","兩棲投送","—","直升機＋登陸載具","—","兩棲攻擊艦","—","兩棲攻擊艦。","Amphibious assault ship.",["兩棲","LHD"],"Naval","Type_075_landing_helicopter_dock"),
  ("type-071","071 型船塢登陸艦","Type 071 LPD","Type 071",["071","崑崙山級"],"vehicle","warship","海軍","近防","—","約 25,000 t","約 210 m","兩棲","—","氣墊艇＋部隊","—","船塢登陸艦","—","兩棲船塢登陸艦。","Amphibious transport dock.",["兩棲","LPD"],"Naval","Type_071_amphibious_transport_dock"),
  ("type-072a","072A 型坦克登陸艦","Type 072A LST","Type 072A",["072A"],"vehicle","warship","海軍","—","—","約 4,800 t","約 120 m","近岸登陸","—","坦克／車輛","—","坦克登陸艦","—","坦克登陸艦。","Tank landing ship.",["兩棲","LST"],"Naval","Type_072A_landing_ship"),
  ("type-093","093 型攻擊核潛艦","Type 093 SSN","Type 093",["093","商級"],"vehicle","submarine","海軍","魚雷／反艦飛彈","—","水下約 6–7,000 t","約 110 m","核動力遠航","—","魚雷管","—","核攻擊潛艦","聲納","攻擊核潛艦。","Nuclear attack submarine.",["核潛","潛艦"],"Naval","Type_093_submarine"),
  ("type-093b","093B 型攻擊核潛艦","Type 093B SSN","Type 093B",["093B"],"vehicle","submarine","海軍","魚雷／巡航飛彈","—","—","—","—","—","VLS／魚雷","—","核攻擊潛艦","—","093 改進型。","Improved Shang-class.",["核潛"],"Naval","Type_093_submarine"),
  ("type-094","094 型彈道飛彈核潛艦","Type 094 SSBN","Type 094",["094","晉級"],"vehicle","submarine","海軍","JL-2／JL-3","—","—","約 135 m","核動力","—","SLBM 發射筒","—","戰略核潛艦","—","彈道飛彈核潛艦。","Ballistic missile submarine.",["SSBN","核潛"],"Naval","Type_094_submarine"),
  ("type-039a","039A／041 型柴電潛艦","Type 039A/041 Yuan","Type 039A",["元級","041"],"vehicle","submarine","海軍","魚雷／反艦飛彈","約 60","水下約 3,600 t","約 77.5 m","AIP 潛航","—","魚雷管","—","AIP 柴電","聲納","AIP 柴電潛艦主力。","AIP diesel-electric SSK.",["潛艦","AIP"],"Naval","Type_039A_submarine"),
  ("type-039","039 型柴電潛艦","Type 039 Song","Type 039",["宋級"],"vehicle","submarine","海軍","魚雷／反艦","—","約 2,250 t","約 75 m","—","—","魚雷管","—","柴電","—","宋級柴電潛艦。","Song-class SSK.",["潛艦"],"Naval","Type_039_submarine"),
  ("type-901","901 型綜合補給艦","Type 901 AOE","Type 901",["901","呼倫湖級"],"vehicle","warship","海軍","—","—","約 45,000 t","約 240 m","遠洋補給","—","燃油彈藥","—","快速補給","—","航母編隊綜合補給艦。","Fast combat support ship.",["補給艦"],"Naval","Type_901_replenishment_ship"),
  ("type-903a","903A 型補給艦","Type 903A AOR","Type 903A",["903A","阜康級"],"vehicle","warship","海軍","—","—","約 23,000 t","約 179 m","遠洋補給","—","油彈","—","補給艦","—","遠洋補給艦。","Replenishment oiler.",["補給艦"],"Naval","Type_903_replenishment_ship"),
  ("type-815a","815A 型電子偵察艦","Type 815A AGI","Type 815A",["815A","天浪星"],"vehicle","warship","海軍","—","—","約 6,000 t","約 130 m","遠海偵察","—","—","—","電子偵察","大型天線","電子偵察艦。","ELINT/SIGINT ship.",["偵察艦","電偵"],"Naval","Type_815_spy_ship"),

  # ===== 單兵／裝備 =====
  ("type-21-uniform","21 式作戰服","Type 21 Combat Uniform","Type 21",["21式","星空迷彩"],"equipment","individual","解放軍","—","1","—","—","—","—","—","—","單兵","—","現役作戰服，星空迷彩。","Current combat uniform Xingkong camo.",["單兵","迷彩"],"Individual","Xingkong_camouflage"),
  ("type-19-uniform","19 式作戰服","Type 19 Combat Uniform","Type 19",["19式"],"equipment","individual","解放軍","—","1","—","—","—","—","—","—","單兵","—","星空迷彩作戰服。","Combat uniform with Xingkong.",["單兵"],"Individual","Xingkong_camouflage"),
  ("qgf-11","QGF-11 頭盔","QGF-11 Helmet","QGF-11",["新式頭盔"],"equipment","individual","解放軍","—","1","—","—","—","—","—","防彈","單兵","可掛夜視","新型戰鬥頭盔。","Modern combat helmet.",["頭盔","防護"],"Individual",""),
  ("qgf-03","QGF-03 頭盔","QGF-03 Helmet","QGF-03",["03頭盔"],"equipment","individual","解放軍","—","1","—","—","—","—","—","防彈","單兵","—","制式防彈頭盔。","Service ballistic helmet.",["頭盔"],"Individual","QGF-03"),
  ("type-15-vest","15 式重型防彈衣","Type 15 Heavy Vest","Type 15",["15式防彈"],"equipment","individual","解放軍","—","1","—","—","—","—","插板","防彈","單兵","—","重型防彈攜行具。","Heavy ballistic vest with plates.",["防彈","單兵"],"Individual",""),
  ("bbg011a","BBG011A 夜視儀","BBG011A NVG","BBG011A",["夜視"],"equipment","individual","解放軍","—","1","—","—","—","—","—","—","單兵","微光夜視","單兵夜視裝備。","Night vision device.",["夜視","單兵"],"Individual",""),
  ("qts-11","QTS-11 單兵綜合作戰系統","QTS-11","QTS-11",["11式榴彈步槍"],"weapon","assault_rifle","特種／試裝","5.8mm＋20mm","1","—","—","—","—","20 發＋單發榴彈","—","步兵","火控","步槍＋空爆榴彈綜合系統。","Rifle + airburst grenade system.",["步槍","空爆"],"Infantry Weapons","QTS-11"),

  # ===== 火箭軍／岸防等補充 =====
  ("yj-12b","鷹擊-12B 岸艦飛彈","YJ-12B Coastal AShM","YJ-12B",["鷹擊12B","岸防"],"weapon","asm","海軍岸防","超音速反艦","—","—","—","約 400+ km","—","岸基發射車","—","機動岸防","—","岸基超音速反艦。","Coastal defense supersonic AShM.",["岸防","反艦"],"Missiles","YJ-12"),
  ("hd-1","紅鳥／長劍岸防巡航（代表）","Coastal LACM systems","CJ/HN coastal",["岸防巡航"],"weapon","cruise","火箭軍／海軍","對陸／對海巡航","—","—","—","遠程","—","岸基","—","機動","—","岸基巡航飛彈力量（公開分類）。","Coastal cruise missile forces (public).",["岸防","巡航飛彈"],"Missiles",""),
  ("type-05-amphib-family","05 兩棲車族（概述）","Type 05 Amphibious Family","ZBD/ZTD-05",["05車族"],"vehicle","ifv","海軍陸戰隊","30／105mm","—","約 26 t","—","—","—","—","裝甲","高速滑水","—","兩棲機械化主力車族。","PLANMC high-speed amphibious family.",["兩棲","陸戰隊"],"AFV","ZBD-2000"),
  ("pzh-07","07 式 122mm 榴彈砲","PLH/PZH-07 Howitzer","Type 07 122mm",["07式牽引122"],"equipment","artillery_towed","解放軍","122mm","—","—","—","約 15–18 km","—","—","—","牽引","—","牽引 122mm 榴彈砲。","Towed 122mm howitzer.",["火砲","122mm"],"Artillery",""),
  ("pll-01","PLL-01 100mm 突擊砲","PLL-01","PLL-01",["100mm突擊"],"vehicle","assault_gun","解放軍","100mm","—","—","—","—","—","—","輪式","輪式","—","輪式 100mm 突擊砲（舊型）。","Wheeled 100mm assault gun.",["突擊砲"],"AFV",""),
  ("zsd-89","89 式裝甲輸送車","ZSD-89 APC","ZSD-89",["89式運兵","Type 89 APC"],"vehicle","apc_tracked","解放軍","12.7mm","2＋13","約 14 t","—","—","—","載員","裝甲","履帶","—","履帶裝甲輸送車。","Tracked APC.",["APC","履帶"],"AFV","Type_89_AFV"),
  ("ztd-05-overview","05 式兩棲突擊車族火力型","ZTD-05 105mm","ZTD-05",["兩棲105"],"vehicle","assault_gun","海軍陸戰隊","105mm","4","約 26 t","—","約 2 km","—","—","裝甲","高速兩棲","射控","兩棲火力支援。","Amphibious fire support.",["兩棲","105mm"],"AFV","ZBD-2000"),

  # more artillery / engineering / air defense
  ("plc-181-note","車載火砲族（PCL 系列）","PCL-series truck guns","PCL series",["PCL"],"vehicle","truck_howitzer","解放軍","122／155mm","—","—","—","依口徑","—","—","—","卡車底盤","數位化","高機動車載火砲系列。","Truck-mounted artillery family.",["火砲","車載"],"Artillery","PCL-181"),
  ("hq-10","海紅旗-10 近防飛彈","HHQ-10 / FL-3000N","HQ-10",["海紅旗10","HHQ-10"],"equipment","sam","海軍","近防飛彈","—","—","—","約 0.5–10 km","—","24 聯裝等","—","艦載","紅外／被動","艦載點防空飛彈。","Ship point-defense missile.",["近防","艦載"],"Air Defense","HQ-10"),
  ("type-730","730 近防砲","Type 730 CIWS","Type 730",["730近防"],"equipment","ciws","海軍","30mm 轉管","—","—","—","約 3 km","極高射速","—","—","艦載","光電／雷達","艦載近防火砲。","Naval CIWS gun.",["近防","CIWS"],"Naval","Type_730_CIWS"),
  ("type-1130","1130 近防砲","Type 1130 CIWS","Type 1130",["1130"],"equipment","ciws","海軍","30mm 11 管","—","—","—","約 3 km","極高射速","—","—","艦載","雷達光電","新型艦載近防砲。","Advanced naval CIWS.",["近防","CIWS"],"Naval","Type_1130_CIWS"),
  ("yu-6","魚-6 魚雷","Yu-6 Torpedo","Yu-6",["魚6"],"weapon","torpedo","海軍","重型魚雷","—","—","—","數十 km 級","—","潛／艦射","—","水中","主／被動聲導","重型反艦反潛魚雷。","Heavyweight torpedo.",["魚雷"],"Naval",""),
  ("yu-7","魚-7 魚雷","Yu-7 Torpedo","Yu-7",["魚7"],"weapon","torpedo","海軍","輕型魚雷","—","—","—","—","—","艦／機載","—","水中","—","輕型反潛魚雷。","Lightweight ASW torpedo.",["魚雷","反潛"],"Naval",""),
  ("type-726","726 型氣墊登陸艇","Type 726 LCAC","Type 726",["野牛級氣墊","726"],"vehicle","warship","海軍","—","—","—","—","兩棲快速","—","戰車／部隊","—","氣墊","—","氣墊登陸艇。","Air-cushion landing craft.",["兩棲","氣墊"],"Naval","Type_726_LCAC"),
  ("jl-9","教練-9 高級教練機","Guizhou JL-9","JL-9",["教練9","山鷹"],"vehicle","aircraft_trainer","空軍／海航","—","1–2","—","—","—","—","—","—","高級教練","—","高級教練／輕攻擊。","Advanced jet trainer.",["教練機"],"Aircraft","Guizhou_JL-9"),
  ("jl-10","教練-10 高級教練機","Hongdu JL-10 / L-15","JL-10",["教練10","獵鷹"],"vehicle","aircraft_trainer","空軍","—","1–2","—","—","—","—","—","—","高級教練","—","高級教練機。","Advanced trainer.",["教練機"],"Aircraft","Hongdu_L-15"),
  ("jl-8","教練-8 初級噴射教練機","Hongdu JL-8 / K-8","JL-8",["教練8","K-8"],"vehicle","aircraft_trainer","空軍","—","2","—","—","—","—","—","—","基礎噴射教練","—","基礎噴射教練機。","Basic jet trainer.",["教練機"],"Aircraft","Hongdu_JL-8"),
  ("j-7","殲-7 戰鬥機（教練／二線）","Chengdu J-7","J-7",["殲7"],"vehicle","aircraft_fighter","空軍（汰換）","—","1","—","—","—","—","—","—","舊式戰機","—","米格-21 系，大量退役中。","MiG-21 derivative retiring.",["戰鬥機","舊式"],"Aircraft","Chengdu_J-7"),
  ("y-5","運-5 運輸機","Shijiazhuang Y-5","Y-5",["運5"],"vehicle","aircraft_transport","空軍","—","—","—","—","近距","—","—","—","輕型運輸","—","安-2 系輕型運輸。","An-2 class light transport.",["運輸機"],"Aircraft","Shijiazhuang_Y-5"),
  ("z-11","直-11 輕型直升機","Harbin Z-11","Z-11",["直11"],"vehicle","helicopter","陸軍","—","1–2","—","—","—","—","—","—","輕型","—","輕型通用／偵察直升機。","Light utility helicopter.",["直升機"],"Aircraft","Harbin_Z-11"),
  ("s-300","S-300／紅旗-15 系防空（進口）","S-300 / HQ-15 family","S-300PMU",["S300","紅旗15"],"equipment","sam","空軍／防空","遠程地對空","連級","—","—","約 90–200 km","—","—","—","陸基","相控陣","進口遠程防空系統。","Imported long-range SAM.",["防空","進口"],"Air Defense","S-300_missile_system"),
  ("s-400","S-400 防空系統（進口）","S-400","S-400",["S400","凱旋"],"equipment","sam","空軍／防空","遠程地對空","連級","—","—","約 250–400 km","—","—","—","陸基","多雷達","進口遠程防空。","Imported long-range SAM.",["防空","進口"],"Air Defense","S-400_missile_system"),
  ("df-100","東風-100 高超音速巡航飛彈","DF-100 / CJ-100","DF-100",["東風100","長劍100"],"weapon","cruise","火箭軍","高超音速巡航","—","—","—","約 1000–3000 km 級","—","機動發射車","—","公路機動","—","高超音速巡航飛彈（公開）。","Hypersonic cruise missile (public).",["巡航飛彈","高超音速"],"Missiles","CJ-100"),
  ("yb-1","鷹擊／岸防飛彈發射車（通用）","Coastal AShM TEL","Coastal TEL",["岸艦發射車"],"vehicle","sam","海軍岸防","反艦飛彈","—","—","—","依彈種","—","箱式發射","—","輪式機動","—","岸艦飛彈機動發射車。","Coastal anti-ship TEL.",["岸防"],"Missiles",""),
]
# fmt: on


def fetch_wiki_thumb(title: str) -> str:
    if not title:
        return ""
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_"))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.load(resp)
        thumb = data.get("thumbnail") or {}
        src = thumb.get("source") or ""
        # prefer larger image
        if src and "/thumb/" in src:
            # request wider version via commons if possible
            src = src.replace("/330px-", "/640px-").replace("/320px-", "/640px-").replace("/300px-", "/640px-")
        return src
    except Exception:
        return ""


def load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: dict) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    cache = load_cache()
    items = []
    for row in CATALOG:
        (
            eid, name_zh, name_en, designation, aliases, category, subcategory,
            service_zh, caliber, crew, weight, length, range_m, rof, capacity,
            armor, mobility, sensors, notes_zh, notes_en, tags, odin_hint, wiki,
        ) = row

        image = ""
        if wiki:
            if wiki in cache:
                image = cache[wiki]
            else:
                image = fetch_wiki_thumb(wiki)
                cache[wiki] = image
                time.sleep(0.12)
                print(f"{'OK' if image else '--'} {wiki}")

        items.append({
            "id": eid,
            "name_zh": name_zh,
            "name_en": name_en,
            "designation": designation,
            "aliases": aliases,
            "category": category,
            "subcategory": subcategory,
            "origin": "China" if "俄" not in service_zh and "進口" not in "".join(tags) else ("Russia" if "俄" in name_zh or "S-" in designation or "Su-" in designation or "Il-" in designation or "Mi-" in designation or "Ka-" in designation else "China"),
            "origin_zh": "中國" if not any(x in name_en for x in ("Su-", "S-300", "S-400", "Il-", "Mi-", "Ka-")) else ("俄羅斯／蘇聯" if any(x in name_en for x in ("Su-", "S-300", "S-400", "Il-", "Mi-", "Ka-")) else "中國"),
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
            "image": image,
            "wiki": wiki,
            "odin_url": "https://odin.t2com.army.mil/WEG",
        })

    # fix origin for known foreign
    for it in items:
        n = it["name_en"] + it["designation"]
        if any(k in n for k in ("Su-", "S-300", "S-400", "Il-", "Mi-17", "Ka-28", "Ka-27")):
            it["origin"] = "Russia"
            it["origin_zh"] = "俄羅斯／蘇聯"

    save_cache(cache)

    js = """/**
 * 解放軍武器／裝備／載具資料庫（公開來源整理，含 Wikimedia 圖片）
 * 欄位對齊 ODIN WEG 風格；僅供訓練與教育參考。
 * 由 tools/build_catalog.py 產生 — 請勿手改後又覆蓋。
 */
window.EQUIPMENT_DATA = %s;
""" % json.dumps(items, ensure_ascii=False, indent=2)

    OUT.write_text(js, encoding="utf-8")
    with_img = sum(1 for i in items if i["image"])
    print(f"Wrote {len(items)} items ({with_img} with images) -> {OUT}")


if __name__ == "__main__":
    main()
