#!/usr/bin/env python3
"""把整站打包成單一離線 HTML：CSS/JS 內嵌、圖片壓縮成 base64 data URI 內嵌。
產出：解放軍速查_離線版.html（可離線開、跨網路、AirDrop 分享）。"""
import json, base64, io, os
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

MAXPX = 800   # 圖片最長邊
QUALITY = 82  # JPEG 品質

def to_datauri(path):
    im = Image.open(path)
    if im.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", im.size, (16, 22, 34))  # 深色底，配合介面
        im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((MAXPX, MAXPX))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=QUALITY, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

# 1) 讀資料，換圖為 data URI、去掉遠端圖
t = open("js/equipment-data.js", encoding="utf-8").read()
arr = json.loads(t[t.index("["):t.rindex("]") + 1])
cache = {}
n_img = 0
for x in arr:
    img = x.get("image", "") or ""
    if img.startswith("assets/") and Path(img).exists():
        if img not in cache:
            cache[img] = to_datauri(img)
        x["image"] = cache[img]
        n_img += 1
    x.pop("image_remote", None)
newjs = "window.EQUIPMENT_DATA = " + json.dumps(arr, ensure_ascii=False) + ";"

# 2) 組裝單檔 HTML
html = open("index.html", encoding="utf-8").read()
css = open("css/styles.css", encoding="utf-8").read()
appjs = open("js/app.js", encoding="utf-8").read()
html = html.replace('<link rel="stylesheet" href="css/styles.css" />', f"<style>\n{css}\n</style>")
html = html.replace('<script src="js/equipment-data.js"></script>', f"<script>\n{newjs}\n</script>")
html = html.replace('<script src="js/app.js"></script>', f"<script>\n{appjs}\n</script>")

out = ROOT / "解放軍速查_離線版.html"
out.write_text(html, encoding="utf-8")
mb = out.stat().st_size / 1024 / 1024
print(f"完成：{out.name}")
print(f"內嵌圖片 {n_img} 張（不重複 {len(cache)} 檔）｜檔案大小 {mb:.1f} MB")
