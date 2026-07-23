#!/usr/bin/env python3
"""偵測使用者放進 assets/images/ 的新圖（檔名＝裝備 id，如 type-83-sph.jpg），
壓縮後接進資料（寫入 specs_enrichment.json 的 image 欄），再跑 apply 生效。
用法：python3 tools/sync_new_images.py"""
import json, glob, subprocess, io
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "assets" / "images"
MAXPX = 1000  # 使用者原圖若過大，壓到最長邊 1000px

def load_items():
    t = (ROOT / "js" / "equipment-data.js").read_text(encoding="utf-8")
    return json.loads(t[t.index("["):t.rindex("]") + 1])

def compress_inplace(path: Path):
    """過大的圖壓縮，統一存成 <id>.jpg；回傳最終相對路徑。"""
    im = Image.open(path)
    if im.mode in ("RGBA", "P", "LA"):
        bg = Image.new("RGB", im.size, (16, 22, 34))
        im = im.convert("RGBA"); bg.paste(im, mask=im.split()[-1]); im = bg
    else:
        im = im.convert("RGB")
    if max(im.size) > MAXPX:
        im.thumbnail((MAXPX, MAXPX))
    out = IMG / (path.stem + ".jpg")
    im.save(out, "JPEG", quality=85, optimize=True)
    if out != path and path.exists():
        path.unlink()  # 移除原始（如 .png/.webp/.jpeg）
    return f"assets/images/{out.name}"

def main():
    arr = load_items()
    missing = {x["id"] for x in arr if not (x.get("image") or "").startswith("assets/")}
    # 掃描 assets/images 找檔名匹配缺圖 id 的
    found = {}
    for f in glob.glob(str(IMG / "*")):
        p = Path(f)
        if p.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"):
            continue
        if p.stem in missing:
            found[p.stem] = compress_inplace(p)
    if not found:
        print("沒有偵測到新圖（請把圖存進 assets/images/，檔名用裝備 id，見 缺圖清單.txt）")
        print(f"目前仍缺 {len(missing)} 筆。")
        return
    # 寫入精修層
    ep = ROOT / "data" / "specs_enrichment.json"
    d = json.loads(ep.read_text(encoding="utf-8"))
    for eid, path in found.items():
        d["items"].setdefault(eid, {})["image"] = path
    ep.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✔ 接上新圖 {len(found)} 筆：", ", ".join(sorted(found)))
    # 重新產生 equipment-data.js
    subprocess.run(["python3", str(ROOT / "tools" / "apply_us_authority.py")], check=True)
    still = missing - set(found)
    print(f"完成。仍缺 {len(still)} 筆。")
    print("接著我會重建離線檔並上線。")

if __name__ == "__main__":
    main()
