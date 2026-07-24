#!/usr/bin/env python3
"""把 Grok 產的清單（designation 列表）和現有資料庫正規化比對，列出缺漏。
用法：python3 tools/diff_grok.py <grok_json_file>
grok json = [{"designation":..,"name_zh":..,"subcategory":..,"status":..}, ...]"""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def norm(s):
    return re.sub(r'[^a-z0-9一-鿿]','',(s or '').lower())

def codes(s):
    """抽出型號代碼：type052d / 052dl / yj83 / hhq16 / 956em / hpj38 等。"""
    s=(s or '').lower()
    out=set()
    for m in re.findall(r'(?:type|project|hq|hhq|yj|df|cj|pl|hj|ys|yu|ch|z|j|h|q|kj|wz|zt[zqld]?|zbd?|zsl|zsd|pgz|plz|phl|phz|pll|pcl|slc|ylc|jy|c)\s*-?\s*\d{1,4}[a-z]{0,3}', s):
        out.add(norm(m))
    for m in re.findall(r'\b\d{3,4}[a-z]{0,3}\b', s):
        out.add(norm(m))
    return {c for c in out if len(c)>=3}

# 現有資料庫索引
t=(ROOT/'js'/'equipment-data.js').read_text(encoding='utf-8')
arr=json.loads(t[t.index('['):t.rindex(']')+1])
mine=set()
for x in arr:
    for f in [x.get('id'),x.get('designation'),x.get('name_zh'),x.get('name_en')]+list(x.get('aliases') or []):
        mine|=codes(f); 
        if norm(f): mine.add(norm(f))

grok=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
missing=[];matched=[]
for g in grok:
    if g.get('subcategory')=='資料說明': continue
    gc=codes(g['designation'])|codes(g.get('name_zh',''))|codes(g.get('name_en',''))
    gc|={norm(g['designation']),norm(g.get('name_zh',''))}
    gc={c for c in gc if c and len(c)>=3}
    hit = bool(gc & mine)
    (matched if hit else missing).append(g)
print(f"Grok {len(grok)} 筆｜已有 {len(matched)}｜缺漏 {len(missing)}\n")
print("=== 缺漏（Grok 有、我沒有）===")
for g in missing:
    print(f"  [{g.get('status','')}] {g['designation']}｜{g.get('name_zh','')}｜{g.get('subcategory','')}")
